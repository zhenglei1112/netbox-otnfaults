from extras.scripts import Script, IntegerVar, BooleanVar, StringVar
from netbox_otnfaults.models import OtnPath, CableTypeChoices
from dcim.models import Site
from django.db.models import Q
import requests
import math
from difflib import SequenceMatcher
from decimal import Decimal
import random
from typing import Any

class ImportOtnPaths(Script):
    DEFAULT_ARCGIS_LINE_URL = "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN2026/FeatureServer/1"

    class Meta:
        name = "Import OTN Paths from ArcGIS"
        description = "Fetch line and point data from ArcGIS and create OtnPath objects."

    arcgis_line_url = StringVar(
        default=DEFAULT_ARCGIS_LINE_URL,
        description="ArcGIS 线图层 FeatureServer Layer URL；填写图层地址，不需要包含 /query。"
    )

    distance_threshold = IntegerVar(
        default=100,
        description="路径端点匹配站点的最大合法距离范围，单位为米 (m)。超过此容差距离的端点将被抛弃并关联归为【未指定】站点。"
    )

    allow_duplicate_endpoints = BooleanVar(
        default=False,
        description="允许两端站点相同的路径重复入库。用于同一站点对存在不同实际路由走向的场景。"
    )

    dry_run = BooleanVar(
        default=True,
        description="模拟模式：仅预览导入结果，不写入数据库。"
    )

    def get_arcgis_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = False
        return session

    def haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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

    def fetch_arcgis_data(self, url: str) -> dict[str, Any] | None:
        try:
            params = {
                'f': 'json',
                'where': '1=1',
                'outFields': '*',
                'returnGeometry': 'true',
                'spatialRel': 'esriSpatialRelIntersects'
            }
            response = self.get_arcgis_session().get(f"{url}/query", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_failure(f"Failed to fetch data from {url}: {str(e)}")
            return None

    def load_netbox_site_cache(self) -> list[dict[str, Any]]:
        """Load NetBox sites with coordinates for nearest-site matching."""
        site_cache: list[dict[str, Any]] = []
        for site in Site.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            site_cache.append(
                {
                    "site": site,
                    "name": site.name,
                    "x": float(site.longitude),
                    "y": float(site.latitude),
                }
            )
        return site_cache

    def find_nearest_site(self, point_geometry: list[float] | dict[str, float], site_cache: list[dict[str, Any]]) -> tuple[str | None, float]:
        """Find the nearest NetBox site for a line endpoint."""
        try:
            target_x = point_geometry[0] if isinstance(point_geometry, list) else point_geometry['x']
            target_y = point_geometry[1] if isinstance(point_geometry, list) else point_geometry['y']
        except (IndexError, KeyError):
            self.log_warning("Invalid point geometry format.")
            return None, float('inf')

        nearest_site_name = None
        min_dist = float('inf')

        for site_data in site_cache:
            try:
                site_x = site_data["x"]
                site_y = site_data["y"]
                
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
                    nearest_site_name = site_data["name"]

            except Exception:
                continue

        return nearest_site_name, min_dist

    def normalize_site_name(self, value: str) -> str:
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def score_site_name_similarity(self, reference_name: str, site_name: str) -> float:
        reference_norm = self.normalize_site_name(reference_name)
        site_norm = self.normalize_site_name(site_name)
        if not reference_norm or not site_norm:
            return 0.0

        ratio = SequenceMatcher(None, reference_norm, site_norm).ratio()
        if reference_norm in site_norm or site_norm in reference_norm:
            ratio = max(ratio, 0.85)
        return ratio

    def build_distance_sorted_site_candidates(
        self,
        point_geometry: list[float] | dict[str, float],
        site_cache: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        try:
            target_x = point_geometry[0] if isinstance(point_geometry, list) else point_geometry["x"]
            target_y = point_geometry[1] if isinstance(point_geometry, list) else point_geometry["y"]
        except (IndexError, KeyError):
            return []

        is_geographic = abs(target_x) <= 180 and abs(target_y) <= 90
        candidates: list[dict[str, Any]] = []
        for site_data in site_cache:
            site_x = site_data["x"]
            site_y = site_data["y"]
            if is_geographic:
                distance = self.haversine(target_y, target_x, site_y, site_x)
            else:
                distance = math.sqrt((target_x - site_x) ** 2 + (target_y - site_y) ** 2)
            candidates.append(
                {
                    "site": site_data["site"],
                    "name": site_data["name"],
                    "distance": distance,
                }
            )
        candidates.sort(key=lambda item: item["distance"])
        return candidates

    def calculate_point_to_site_distance(
        self,
        point_geometry: list[float] | dict[str, float],
        site: Any,
    ) -> float:
        if getattr(site, "longitude", None) is None or getattr(site, "latitude", None) is None:
            return float("inf")

        try:
            target_x = point_geometry[0] if isinstance(point_geometry, list) else point_geometry["x"]
            target_y = point_geometry[1] if isinstance(point_geometry, list) else point_geometry["y"]
        except (IndexError, KeyError):
            return float("inf")

        site_x = float(site.longitude)
        site_y = float(site.latitude)
        is_geographic = abs(target_x) <= 180 and abs(target_y) <= 90
        if is_geographic:
            return self.haversine(target_y, target_x, site_y, site_x)
        return math.sqrt((target_x - site_x) ** 2 + (target_y - site_y) ** 2)

    def distance_to_score(self, distance_m: float, threshold_m: int) -> float:
        if math.isinf(distance_m):
            return 0.0
        threshold = max(float(threshold_m), 1.0)
        if distance_m <= threshold:
            return 1.0
        max_distance = max(threshold * 5.0, 500.0)
        if distance_m >= max_distance:
            return 0.0
        return max(0.0, 1.0 - ((distance_m - threshold) / (max_distance - threshold)))

    def audit_match_quality(
        self,
        feat_name: str,
        path_name: str,
        start_point: list[float] | dict[str, float],
        end_point: list[float] | dict[str, float],
        site_a: Any,
        site_z: Any,
        reference_a: str | None,
        reference_z: str | None,
        threshold_m: int,
        name_direction: str,
        fuzzy_used: bool,
    ) -> dict[str, str]:
        ref_a = reference_a or feat_name or site_a.name
        ref_z = reference_z or feat_name or site_z.name
        similarity_a = self.score_site_name_similarity(ref_a, site_a.name)
        similarity_z = self.score_site_name_similarity(ref_z, site_z.name)
        distance_a = self.calculate_point_to_site_distance(start_point, site_a)
        distance_z = self.calculate_point_to_site_distance(end_point, site_z)
        distance_score_a = self.distance_to_score(distance_a, threshold_m)
        distance_score_z = self.distance_to_score(distance_z, threshold_m)

        avg_similarity = (similarity_a + similarity_z) / 2.0
        avg_distance_score = (distance_score_a + distance_score_z) / 2.0
        fuzzy_penalty = 0.1 if fuzzy_used else 0.0
        total_score = max(0.0, min(100.0, ((avg_similarity * 0.7) + (avg_distance_score * 0.3) - fuzzy_penalty) * 100.0))

        reasons = []
        if avg_similarity < 0.5:
            reasons.append("名称相似度偏低")
        if avg_distance_score < 0.5:
            reasons.append("端点距离偏大")
        if fuzzy_used:
            reasons.append("依赖模糊匹配")
        if not reasons:
            reasons.append("综合匹配正常")

        return {
            "source_name": feat_name or "(无 O_NAME)",
            "path_name": path_name,
            "site_a": site_a.name,
            "site_z": site_z.name,
            "name_direction": name_direction,
            "fuzzy_used": "是" if fuzzy_used else "否",
            "score": f"{total_score:.2f}",
            "similarity_a": f"{similarity_a:.2f}",
            "similarity_z": f"{similarity_z:.2f}",
            "distance_a": "N/A" if math.isinf(distance_a) else f"{distance_a:.2f}",
            "distance_z": "N/A" if math.isinf(distance_z) else f"{distance_z:.2f}",
            "reason": "；".join(reasons),
        }

    def analyze_reference_candidates(
        self,
        point_geometry: list[float] | dict[str, float],
        site_cache: list[dict[str, Any]],
        reference_name: str | None,
        threshold_m: int,
        excluded_site_names: set[str] | None = None,
    ) -> dict[str, Any] | None:
        candidates = self.build_distance_sorted_site_candidates(point_geometry, site_cache)
        if not candidates:
            return None

        max_distance = max(float(threshold_m) * 5, 500.0)
        limited_candidates = [item for item in candidates[:5] if item["distance"] <= max_distance]
        if not limited_candidates:
            return None

        nearest_candidate = limited_candidates[0]
        analysis: dict[str, Any] = {
            "nearest_candidate": nearest_candidate["name"],
            "nearest_distance": nearest_candidate["distance"],
            "best_similarity_candidate": "(无)",
            "best_similarity": 0.0,
            "best_similarity_distance": float("inf"),
            "matched_site": None,
        }
        if not reference_name:
            return analysis

        best_candidate = None
        best_similarity = 0.0
        for candidate in limited_candidates:
            similarity = self.score_site_name_similarity(reference_name, candidate["name"])
            if similarity > best_similarity:
                best_candidate = candidate
                best_similarity = similarity

        if best_candidate is not None:
            analysis["best_similarity_candidate"] = best_candidate["name"]
            analysis["best_similarity"] = best_similarity
            analysis["best_similarity_distance"] = best_candidate["distance"]
            if best_similarity >= 0.6:
                analysis["matched_site"] = best_candidate["site"]

        return analysis

    def analyze_reference_candidates_available(
        self,
        point_geometry: list[float] | dict[str, float],
        site_cache: list[dict[str, Any]],
        reference_name: str | None,
        threshold_m: int,
        excluded_site_names: set[str] | None = None,
    ) -> dict[str, Any] | None:
        candidates = self.build_distance_sorted_site_candidates(point_geometry, site_cache)
        if not candidates:
            return None

        excluded_site_names = excluded_site_names or set()
        overall_nearest_candidate = candidates[0]
        available_candidates = [
            item
            for item in candidates[:5]
            if item["name"] not in excluded_site_names
        ]
        analysis: dict[str, Any] = {
            "nearest_candidate": overall_nearest_candidate["name"],
            "nearest_distance": overall_nearest_candidate["distance"],
            "best_similarity_candidate": "(无)",
            "best_similarity": 0.0,
            "best_similarity_distance": float("inf"),
            "matched_site": None,
            "best_available_candidate": "(无可用候选)",
        }
        if not reference_name:
            return analysis

        max_distance = max(float(threshold_m) * 5, 500.0)
        limited_candidates = [item for item in available_candidates[:5] if item["distance"] <= max_distance]
        best_candidate = None
        best_similarity = 0.0
        for candidate in candidates[:5]:
            similarity = self.score_site_name_similarity(reference_name, candidate["name"])
            if similarity > best_similarity:
                best_candidate = candidate
                best_similarity = similarity

        if best_candidate is not None:
            analysis["best_similarity_candidate"] = best_candidate["name"]
            analysis["best_similarity"] = best_similarity
            analysis["best_similarity_distance"] = best_candidate["distance"]
        if available_candidates:
            analysis["best_available_candidate"] = available_candidates[0]["name"]

        best_available_candidate = None
        best_available_similarity = 0.0
        for candidate in limited_candidates:
            similarity = self.score_site_name_similarity(reference_name, candidate["name"])
            if similarity > best_available_similarity:
                best_available_candidate = candidate
                best_available_similarity = similarity
        if best_available_candidate is not None and best_available_similarity >= 0.6:
            analysis["matched_site"] = best_available_candidate["site"]

        return analysis

    def choose_name_direction(
        self,
        start_point: list[float] | dict[str, float],
        end_point: list[float] | dict[str, float],
        fallback_left: str | None,
        fallback_right: str | None,
        site_cache: list[dict[str, Any]],
        threshold_m: int,
    ) -> tuple[str | None, str | None, str]:
        if not fallback_left or not fallback_right:
            return fallback_left, fallback_right, "AZ"

        normal_a = self.analyze_reference_candidates(start_point, site_cache, fallback_left, threshold_m)
        normal_z = self.analyze_reference_candidates(end_point, site_cache, fallback_right, threshold_m)
        reverse_a = self.analyze_reference_candidates(start_point, site_cache, fallback_right, threshold_m)
        reverse_z = self.analyze_reference_candidates(end_point, site_cache, fallback_left, threshold_m)

        def _score_pair(a_result: dict[str, Any] | None, z_result: dict[str, Any] | None) -> tuple[float, float, float]:
            a_similarity = a_result["best_similarity"] if a_result else 0.0
            z_similarity = z_result["best_similarity"] if z_result else 0.0
            a_distance = a_result["best_similarity_distance"] if a_result else float("inf")
            z_distance = z_result["best_similarity_distance"] if z_result else float("inf")
            return (a_similarity + z_similarity, -(a_distance + z_distance), -max(a_distance, z_distance))

        normal_score = _score_pair(normal_a, normal_z)
        reverse_score = _score_pair(reverse_a, reverse_z)
        if reverse_score > normal_score:
            return fallback_right, fallback_left, "ZA"
        return fallback_left, fallback_right, "AZ"

    def try_fuzzy_match_site(
        self,
        point_geometry: list[float] | dict[str, float],
        site_cache: list[dict[str, Any]],
        reference_name: str | None,
        threshold_m: int,
        side_label: str,
        feat_name: str,
        excluded_site_names: set[str] | None = None,
    ) -> tuple[Any | None, dict[str, str] | None, dict[str, str] | None]:
        analysis = self.analyze_reference_candidates_available(
            point_geometry,
            site_cache,
            reference_name,
            threshold_m,
            excluded_site_names=excluded_site_names,
        )
        if not analysis:
            return None, None, None

        unmatched_detail = {
            "source_name": feat_name or "(无 O_NAME)",
            "side": side_label,
            "reference_name": reference_name or "(无参考名)",
            "nearest_candidate": analysis["nearest_candidate"],
            "nearest_distance": "N/A" if math.isinf(analysis["nearest_distance"]) else f"{analysis['nearest_distance']:.2f}",
            "best_similarity_candidate": analysis["best_similarity_candidate"],
            "best_similarity": f"{analysis['best_similarity']:.2f}",
        }

        if analysis["matched_site"] is None:
            return None, None, unmatched_detail

        detail = {
            "source_name": feat_name or "(无 O_NAME)",
            "side": side_label,
            "reference_name": reference_name or "(无参考名)",
            "matched_site": analysis["best_similarity_candidate"],
            "distance": f"{analysis['best_similarity_distance']:.2f}",
            "similarity": f"{analysis['best_similarity']:.2f}",
        }
        return analysis["matched_site"], detail, unmatched_detail

    def run(self, data, commit):
        threshold_m = data.get('distance_threshold', 100)
        dry_run = data.get('dry_run', True)
        allow_duplicate_endpoints = data.get('allow_duplicate_endpoints', False)
        arcgis_line_url = (data.get('arcgis_line_url') or self.DEFAULT_ARCGIS_LINE_URL).rstrip('/')
        should_save = bool(commit and not dry_run)

        if dry_run:
            self.log_warning("Dry-run mode enabled: paths will be prepared but not saved.")
        
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

        # 1. Load NetBox Sites with Coordinates for Endpoint Matching
        site_cache = self.load_netbox_site_cache()
        self.log_info(f"Total NetBox reference sites loaded: {len(site_cache)}")

        unmatched_paths_count = 0
        unmatched_path_details: list[dict[str, str]] = []
        fuzzy_matched_details: list[dict[str, str]] = []
        low_quality_matches: list[dict[str, str]] = []
        total_processed_paths = 0
        skipped_duplicates = []

        # 2. Process Line Layers
        line_configs = [
            {"url": arcgis_line_url}
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
                site_a_name, dist_a = self.find_nearest_site(start_point, site_cache)
                site_z_name, dist_z = self.find_nearest_site(end_point, site_cache)

                # 从 O_NAME 解析后备站点名（格式如 "枣阳-随州"）
                fallback_a = None
                fallback_z = None
                name_direction = "AZ"
                if '-' in feat_name:
                    parts = feat_name.split('-', 1)
                    fallback_left = parts[0].strip()
                    fallback_right = parts[1].strip()
                    fallback_a, fallback_z, name_direction = self.choose_name_direction(
                        start_point,
                        end_point,
                        fallback_left,
                        fallback_right,
                        site_cache,
                        threshold_m,
                    )

                nb_site_a = None
                nb_site_z = None
                fuzzy_used_a = False
                fuzzy_used_z = False

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

                fuzzy_unmatched_a = None
                fuzzy_unmatched_z = None

                if nb_site_a == unspecified_site:
                    fuzzy_site_a, fuzzy_detail_a, fuzzy_unmatched_a = self.try_fuzzy_match_site(
                        start_point,
                        site_cache,
                        fallback_a or feat_name,
                        threshold_m,
                        "A端",
                        feat_name,
                        excluded_site_names={nb_site_z.name} if nb_site_z and nb_site_z != unspecified_site else None,
                    )
                    if fuzzy_site_a is not None:
                        nb_site_a = fuzzy_site_a
                        fuzzy_used_a = True
                        fuzzy_detail_a["name_direction"] = name_direction
                        fuzzy_matched_details.append(fuzzy_detail_a)

                if nb_site_z == unspecified_site:
                    fuzzy_site_z, fuzzy_detail_z, fuzzy_unmatched_z = self.try_fuzzy_match_site(
                        end_point,
                        site_cache,
                        fallback_z or feat_name,
                        threshold_m,
                        "Z端",
                        feat_name,
                        excluded_site_names={nb_site_a.name} if nb_site_a and nb_site_a != unspecified_site else None,
                    )
                    if fuzzy_site_z is not None:
                        nb_site_z = fuzzy_site_z
                        fuzzy_used_z = True
                        fuzzy_detail_z["name_direction"] = name_direction
                        fuzzy_matched_details.append(fuzzy_detail_z)

                # Construct OtnPath Name
                path_name = f"{nb_site_a.name}-{nb_site_z.name}"

                if nb_site_a == unspecified_site or nb_site_z == unspecified_site:
                    unmatched_paths_count += 1
                    unmatched_side_labels = []
                    if nb_site_a == unspecified_site:
                        unmatched_side_labels.append("A端")
                    if nb_site_z == unspecified_site:
                        unmatched_side_labels.append("Z端")
                    unmatched_path_details.append(
                        {
                            "source_name": feat_name or "(无 O_NAME)",
                            "path_name": path_name,
                            "site_a": nb_site_a.name,
                            "site_z": nb_site_z.name,
                            "unmatched_sides": "/".join(unmatched_side_labels),
                            "name_direction": name_direction,
                            "nearest_candidates": " | ".join(
                                filter(
                                    None,
                                    [
                                        (
                                            f"A端 待匹配端站点名称: {fuzzy_unmatched_a['reference_name']} | "
                                            f"A端 最近候选站点: {fuzzy_unmatched_a['nearest_candidate']} "
                                            f"(最近距离: {fuzzy_unmatched_a['nearest_distance']}m, "
                                            f"最佳相似候选: {fuzzy_unmatched_a['best_similarity_candidate']}, "
                                            f"最佳相似度: {fuzzy_unmatched_a['best_similarity']})"
                                            if fuzzy_unmatched_a
                                            else ""
                                        ),
                                        (
                                            f"Z端 待匹配端站点名称: {fuzzy_unmatched_z['reference_name']} | "
                                            f"Z端 最近候选站点: {fuzzy_unmatched_z['nearest_candidate']} "
                                            f"(最近距离: {fuzzy_unmatched_z['nearest_distance']}m, "
                                            f"最佳相似候选: {fuzzy_unmatched_z['best_similarity_candidate']}, "
                                            f"最佳相似度: {fuzzy_unmatched_z['best_similarity']})"
                                            if fuzzy_unmatched_z
                                            else ""
                                        ),
                                    ],
                                )
                            ),
                        }
                    )
                else:
                    match_audit = self.audit_match_quality(
                        feat_name,
                        path_name,
                        start_point,
                        end_point,
                        nb_site_a,
                        nb_site_z,
                        fallback_a,
                        fallback_z,
                        threshold_m,
                        name_direction,
                        fuzzy_used_a or fuzzy_used_z,
                    )
                    if float(match_audit["score"]) < 60.0:
                        low_quality_matches.append(match_audit)

                # Check for existing duplicate path (Bidirectional)
                # 双端均为"未指定"时跳过去重，保持入库
                if not allow_duplicate_endpoints and (nb_site_a != unspecified_site or nb_site_z != unspecified_site):
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

                if should_save:
                    self.log_success(f"Prepared OtnPath for save: {path_name} (Length: {length_m:.2f}m)")
                else:
                    self.log_info(f"[Dry-run] Prepared OtnPath: {path_name} (Length: {length_m:.2f}m)")

                if should_save:
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
            report_msg += f"注意：其中有 {unmatched_paths_count} 条光路在经过模糊匹配后仍未匹配到合适站点，因此保持关联至兜底的【未指定】站点。"
            self.log_warning(report_msg)
            detail_header = f"模糊匹配后仍未匹配、仍保持【未指定】的路径明细共 {len(unmatched_path_details)} 条："
            self.log_warning(detail_header)
            report_msg += f"\n{detail_header}"
            for index, detail in enumerate(unmatched_path_details, start=1):
                detail_line = (
                    f"{index}. 原始路径名: {detail['source_name']} | "
                    f"导入路径名: {detail['path_name']} | "
                    f"A端: {detail['site_a']} | Z端: {detail['site_z']} | "
                    f"未匹配端: {detail['unmatched_sides']} | "
                    f"名称方向: {detail['name_direction']}"
                )
                if detail.get("nearest_candidates"):
                    detail_line += f" | {detail['nearest_candidates']}"
                self.log_warning(detail_line)
                report_msg += f"\n{detail_line}"
        else:
            report_msg += "完美情况：所有光路的起始点与终点都 100% 精准匹配到了具体存在的实体站点（机房）。"
            self.log_success(report_msg)

        if fuzzy_matched_details:
            fuzzy_header = f"模糊匹配修正成功共 {len(fuzzy_matched_details)} 条："
            self.log_success(fuzzy_header)
            report_msg += f"\n{fuzzy_header}"
            for index, detail in enumerate(fuzzy_matched_details, start=1):
                fuzzy_line = (
                    f"{index}. 原始路径名: {detail['source_name']} | "
                    f"修正端: {detail['side']} | "
                    f"参考名称: {detail['reference_name']} | "
                    f"名称方向: {detail['name_direction']} | "
                    f"匹配站点: {detail['matched_site']} | "
                    f"距离: {detail['distance']}m | "
                    f"相似度: {detail['similarity']}"
                )
                self.log_success(fuzzy_line)
                report_msg += f"\n{fuzzy_line}"

        if low_quality_matches:
            quality_header = f"低匹配度路径汇总共 {len(low_quality_matches)} 条："
            self.log_warning(quality_header)
            report_msg += f"\n{quality_header}"
            for index, detail in enumerate(low_quality_matches, start=1):
                quality_line = (
                    f"{index}. 原始路径名: {detail['source_name']} | "
                    f"导入路径名: {detail['path_name']} | "
                    f"A端: {detail['site_a']} | Z端: {detail['site_z']} | "
                    f"名称方向: {detail['name_direction']} | "
                    f"是否模糊匹配: {detail['fuzzy_used']} | "
                    f"综合得分: {detail['score']} | "
                    f"A端名称分: {detail['similarity_a']} | Z端名称分: {detail['similarity_z']} | "
                    f"A端距离: {detail['distance_a']}m | Z端距离: {detail['distance_z']}m | "
                    f"原因: {detail['reason']}"
                )
                self.log_warning(quality_line)
                report_msg += f"\n{quality_line}"

        if skipped_duplicates:
            dup_list = '、'.join(skipped_duplicates)
            dup_msg = f"因查重未入库的路径共 {len(skipped_duplicates)} 条：{dup_list}"
            self.log_warning(dup_msg)
            report_msg += f"\n{dup_msg}"

        if dry_run:
            dry_run_msg = "当前为模拟模式，本次运行未写入数据库。"
            self.log_warning(dry_run_msg)
            report_msg += f"\n{dry_run_msg}"

        return report_msg
