from django.core.exceptions import ObjectDoesNotExist
from extras.scripts import Script
from netbox_otnfaults.models import OtnPath, CableTypeChoices
from dcim.models import Site
from django.db.models import Q
import requests
import math
from decimal import Decimal
import random
import json

class ImportOtnPaths(Script):
    class Meta:
        name = "Import OTN Paths from ArcGIS"
        description = "Fetch line and point data from ArcGIS and create OtnPath objects."

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371e3  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def fetch_arcgis_data(self, url):
        try:
            params = {
                'f': 'json',
                'where': '1=1',
                'outFields': '*',
                'returnGeometry': 'true',
                'spatialRel': 'esriSpatialRelIntersects'
            }
            response = requests.get(f"{url}/query", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_failure(f"Failed to fetch data from {url}: {str(e)}")
            return None

    def find_nearest_site(self, point_geometry, point_features_list):
        """
        Find nearest site from the loaded point features list.
        point_geometry: [x, y] or {x, y} from line endpoint
        point_features_list: list of dicts [{'geometry': {'x':..., 'y':...}, 'attributes': {'O_NAME': ...}}]
        """
        try:
            target_x = point_geometry[0] if isinstance(point_geometry, list) else point_geometry['x']
            target_y = point_geometry[1] if isinstance(point_geometry, list) else point_geometry['y']
        except (IndexError, KeyError):
            self.log_warning("Invalid point geometry format.")
            return None, float('inf')

        nearest_site_name = None
        min_dist = float('inf')

        for feature in point_features_list:
            try:
                geom = feature.get('geometry')
                if not geom:
                    continue
                site_x = geom['x']
                site_y = geom['y']
                
                # Assuming simple Euclidean for short distances or strictly matching coordinate systems (Web Mercator usually)
                # If coordinates are lat/lon (WKID 4326), haversine is better.
                # ArcGIS defaults often to Web Mercator (102100) or local constant.
                # If the user says "spatial distance < 100m", and if coordinates are lat/lon, we use haversine.
                # If coordinates are projected (meters), we use euclidean.
                # Without knowing WKID, check magnitude. Lat < 90, Lon < 180.
                
                is_geographic = abs(target_x) <= 180 and abs(target_y) <= 90
                
                if is_geographic:
                    dist = self.haversine(target_y, target_x, site_y, site_x)
                else:
                    dist = math.sqrt((target_x - site_x)**2 + (target_y - site_y)**2)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_site_name = feature.get('attributes', {}).get('O_NAME')

            except Exception:
                continue

        return nearest_site_name, min_dist

    def run(self, data, commit):
        # Ensure 'Unspecified' site exists
        unspecified_site, _ = Site.objects.get_or_create(
            slug='unspecified',
            defaults={
                'name': '未指定',
                'status': 'active'
            }
        )
        if unspecified_site.name != '未指定':
             # If it existed but with different name (unlikely if slug matched), just use it. 
             # Or if we want to enforce the name, we could update it, but let's leave it.
             pass

        # 1. Fetch Point Data (Sites)
        point_urls = [
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/0",
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/1"
        ]
        
        all_point_features = []
        for url in point_urls:
            self.log_info(f"Fetching point data from {url}...")
            res = self.fetch_arcgis_data(url)
            if res and 'features' in res:
                all_point_features.extend(res['features'])
            else:
                self.log_warning(f"No features found or error for {url}")

        self.log_info(f"Total reference points loaded: {len(all_point_features)}")

        # 2. Process Line Layers
        line_configs = [
            {"url": "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/2", "desc": "8800"},
            {"url": "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/3", "desc": "9800"}
        ]

        for config in line_configs:
            url = config['url']
            desc_val = config['desc']
            self.log_info(f"Processing line layer: {desc_val}")

            res = self.fetch_arcgis_data(url)
            if not res or 'features' not in res:
                continue

            for feature in res['features']:
                geometry = feature.get('geometry')
                if not geometry or 'paths' not in geometry:
                    continue

                paths = geometry['paths']
                # Usually paths is [[[x1,y1], [x2,y2], ...]] specific for multiline, but often just one path
                for path in paths:
                    if not path or len(path) < 2:
                        continue
                    
                    start_point = path[0]
                    end_point = path[-1]

                    # Find nearest sites
                    site_a_name, dist_a = self.find_nearest_site(start_point, all_point_features)
                    site_z_name, dist_z = self.find_nearest_site(end_point, all_point_features)

                    nb_site_a = None
                    nb_site_z = None

                    # Resolve Site A
                    if dist_a > 100 or not site_a_name:
                        nb_site_a = unspecified_site
                    else:
                        try:
                            nb_site_a = Site.objects.get(name=site_a_name)
                        except Site.DoesNotExist:
                            nb_site_a = unspecified_site
                        except Site.MultipleObjectsReturned:
                            self.log_warning(f"Multiple NetBox Sites found for name: {site_a_name}, defaulting to Unspecified")
                            nb_site_a = unspecified_site

                    # Resolve Site Z
                    if dist_z > 100 or not site_z_name:
                        nb_site_z = unspecified_site
                    else:
                        try:
                            nb_site_z = Site.objects.get(name=site_z_name)
                        except Site.DoesNotExist:
                            nb_site_z = unspecified_site
                        except Site.MultipleObjectsReturned:
                            self.log_warning(f"Multiple NetBox Sites found for name: {site_z_name}, defaulting to Unspecified")
                            nb_site_z = unspecified_site
                    
                    # Construct OtnPath Name
                    # Use site A and Z names, which might be '未指定'
                    path_name = f"{nb_site_a.name}-{nb_site_z.name}"

                    # Check for existing duplicate path (Bidirectional)
                    # A-Z or Z-A should be considered same path logic
                    existing_path = OtnPath.objects.filter(
                        Q(site_a=nb_site_a, site_z=nb_site_z) | 
                        Q(site_a=nb_site_z, site_z=nb_site_a)
                    ).first()

                    if existing_path:
                        self.log_warning(f"Path already exists between {nb_site_a.name} and {nb_site_z.name} (ID: {existing_path.pk}). Skipping.")
                        continue
                    
                    # Calculate Length
                    length_m = 0.0
                    for i in range(len(path) - 1):
                        p1 = path[i]
                        p2 = path[i+1]
                        # Check coordinate system again for path calc
                        is_geo = abs(p1[0]) <= 180 and abs(p1[1]) <= 90
                        if is_geo:
                            length_m += self.haversine(p1[1], p1[0], p2[1], p2[0])
                        else:
                            length_m += math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

                    cable_type_choice = random.choice([CableTypeChoices.TYPE_96, CableTypeChoices.TYPE_114])

                    otn_path = OtnPath(
                        name=path_name,
                        site_a=nb_site_a,
                        site_z=nb_site_z,
                        cable_type=cable_type_choice,
                        description=desc_val,
                        calculated_length=Decimal(str(length_m)).quantize(Decimal("0.00")),
                        geometry=path  # Save the single path array [coord, coord, ...]
                    )
                    
                    self.log_success(f"Prepared OtnPath: {path_name} (Length: {length_m:.2f}m)")
                    
                    if commit:
                        try:
                            otn_path.full_clean()
                            otn_path.save()
                            self.log_success(f"Saved OtnPath: {path_name}")
                        except Exception as e:
                            self.log_failure(f"Failed to save {path_name}: {str(e)}")

