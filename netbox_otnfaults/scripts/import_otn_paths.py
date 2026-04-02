from django.core.exceptions import ObjectDoesNotExist
from extras.scripts import Script, IntegerVar
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

    distance_threshold = IntegerVar(
        default=100,
        description="路径端点匹配站点的最大合法距离范围，单位为米 (m)。超过此容差距离的端点将被抛弃并关联归为【未指定】站点。"
    )

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
        threshold_m = data.get('distance_threshold', 100)
        
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
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN2026/FeatureServer/0"
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

        unmatched_paths_count = 0
        total_processed_paths = 0
        skipped_duplicates = []

        # 2. Process Line Layers
        line_configs = [
            {"url": "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN2026/FeatureServer/1"}
        ]

        for config in line_configs:
            url = config['url']
            self.log_info(f"Processing line layer from: {url}")

            res = self.fetch_arcgis_data(url)
            if not res or 'features' not in res:
                continue

            for feature in res['features']:
                geometry = feature.get('geometry')
                attributes = feature.get('attributes', {})
                feat_name = attributes.get('O_Name') or attributes.get('O_NAME') or ''

                if not geometry or 'paths' not in geometry:
                    continue

                paths = geometry['paths']

                # 过滤掉空的或过短的子路径
                valid_paths = [p for p in paths if p and len(p) >= 2]
                if not valid_paths:
                    continue

                total_processed_paths += 1

                # 将 Multipart 视为一个整体：取第一段起点和最后一段终点
                start_point = valid_paths[0][0]
                end_point = valid_paths[-1][-1]

                # 合并所有子路径的坐标用于长度计算和几何存储
                merged_coords = []
                for p in valid_paths:
                    merged_coords.extend(p)

                # Find nearest sites
                site_a_name, dist_a = self.find_nearest_site(start_point, all_point_features)
                site_z_name, dist_z = self.find_nearest_site(end_point, all_point_features)

                # 从 O_NAME 解析后备站点名（格式如 "枣阳-随州"）
                fallback_a = None
                fallback_z = None
                if '-' in feat_name:
                    parts = feat_name.split('-', 1)
                    fallback_a = parts[0].strip()
                    fallback_z = parts[1].strip()

                nb_site_a = None
                nb_site_z = None

                # Resolve Site A：空间匹配优先，失败则用 O_NAME 后备
                if dist_a > threshold_m or not site_a_name:
                    if fallback_a:
                        try:
                            nb_site_a = Site.objects.get(name=fallback_a)
                        except (Site.DoesNotExist, Site.MultipleObjectsReturned):
                            nb_site_a = unspecified_site
                    else:
                        nb_site_a = unspecified_site
                else:
                    try:
                        nb_site_a = Site.objects.get(name=site_a_name)
                    except Site.DoesNotExist:
                        nb_site_a = unspecified_site
                    except Site.MultipleObjectsReturned:
                        self.log_warning(f"Multiple NetBox Sites found for name: {site_a_name}, defaulting to Unspecified")
                        nb_site_a = unspecified_site

                # Resolve Site Z：空间匹配优先，失败则用 O_NAME 后备
                if dist_z > threshold_m or not site_z_name:
                    if fallback_z:
                        try:
                            nb_site_z = Site.objects.get(name=fallback_z)
                        except (Site.DoesNotExist, Site.MultipleObjectsReturned):
                            nb_site_z = unspecified_site
                    else:
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
                path_name = f"{nb_site_a.name}-{nb_site_z.name}"

                if nb_site_a == unspecified_site or nb_site_z == unspecified_site:
                    unmatched_paths_count += 1

                # Check for existing duplicate path (Bidirectional)
                # 双端均为"未指定"时跳过去重，保持入库
                if nb_site_a != unspecified_site or nb_site_z != unspecified_site:
                    existing_path = OtnPath.objects.filter(
                        Q(site_a=nb_site_a, site_z=nb_site_z) |
                        Q(site_a=nb_site_z, site_z=nb_site_a)
                    ).first()

                    if existing_path:
                        skipped_duplicates.append(feat_name or path_name)
                        self.log_warning(f"Path already exists between {nb_site_a.name} and {nb_site_z.name} (ID: {existing_path.pk}). Skipping. O_Name: {feat_name}")
                        continue

                # 使用合并后的坐标计算总长度
                length_m = 0.0
                for i in range(len(merged_coords) - 1):
                    p1 = merged_coords[i]
                    p2 = merged_coords[i+1]
                    is_geo = abs(p1[0]) <= 180 and abs(p1[1]) <= 90
                    if is_geo:
                        length_m += self.haversine(p1[1], p1[0], p2[1], p2[0])
                    else:
                        length_m += math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

                cable_type_choice = random.choice([
                    CableTypeChoices.SELF_BUILT,
                    CableTypeChoices.COORDINATED,
                    CableTypeChoices.LEASED
                ])

                o_name = attributes.get('O_Name') or attributes.get('O_NAME') or ''
                o_com = attributes.get('O_Com') or attributes.get('O_COM') or ''

                otn_path = OtnPath(
                    name=path_name,
                    site_a=nb_site_a,
                    site_z=nb_site_z,
                    cable_type=cable_type_choice,
                    description=o_name[:200],
                    comments=o_com,
                    calculated_length=Decimal(str(length_m)).quantize(Decimal("0.00")),
                    geometry=merged_coords
                )

                self.log_success(f"Prepared OtnPath: {path_name} (Length: {length_m:.2f}m)")

                if commit:
                    try:
                        otn_path.full_clean()
                        otn_path.save()
                        self.log_success(f"Saved OtnPath: {path_name}")
                    except Exception as e:
                        self.log_failure(f"Failed to save {path_name}: {str(e)}")

        # 最终审查报告输出
        report_msg = (
            f"运行完毕！共处理了 {total_processed_paths} 条目标路径。\n"
        )
        if unmatched_paths_count > 0:
            report_msg += f"注意：其中有 {unmatched_paths_count} 条光路因为找不到相距 {threshold_m} 米内的归属机房实体，由于规则已被妥协关联至兜底的【未指定】站点中。"
            self.log_warning(report_msg)
        else:
            report_msg += "完美情况：所有光路的起始点与终点都 100% 精准匹配到了具体存在的实体站点（机房）。"
            self.log_success(report_msg)

        if skipped_duplicates:
            dup_list = '、'.join(skipped_duplicates)
            dup_msg = f"因查重未入库的路径共 {len(skipped_duplicates)} 条：{dup_list}"
            self.log_warning(dup_msg)
            report_msg += f"\n{dup_msg}"

        return report_msg
