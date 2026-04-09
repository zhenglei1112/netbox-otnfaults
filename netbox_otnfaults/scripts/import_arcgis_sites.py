import math
import requests
import hashlib
from django.utils.text import slugify

try:
    from pypinyin import lazy_pinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
from dcim.models import Site
from dcim.choices import SiteStatusChoices
from extras.scripts import Script, StringVar, BooleanVar


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间的球面距离（米），基于 Haversine 公式。"""
    R = 6371000  # 地球平均半径（米）
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_nearby_duplicate_pairs(
    site_coords: list[tuple[str, object, object]],
    threshold_m: float = 100.0,
) -> list[tuple[str, str, float]]:
    geo_sites = [
        (name, float(latitude), float(longitude))
        for name, latitude, longitude in site_coords
        if latitude is not None and longitude is not None
    ]
    geo_sites.sort(key=lambda item: item[1])

    nearby_pairs: list[tuple[str, str, float]] = []
    latitude_window = max(threshold_m / 111000.0, 0.001)

    for index, (name_a, lat_a, lon_a) in enumerate(geo_sites):
        for name_b, lat_b, lon_b in geo_sites[index + 1 :]:
            if (lat_b - lat_a) > latitude_window:
                break

            distance = _haversine(lat_a, lon_a, lat_b, lon_b)
            if distance < threshold_m:
                nearby_pairs.append((name_a, name_b, distance))

    return nearby_pairs


def _log_existing_nearby_duplicates(
    script: Script,
    site_coords: list[tuple[str, object, object]],
    threshold_m: float = 100.0,
) -> None:
    nearby_pairs = _find_nearby_duplicate_pairs(site_coords, threshold_m=threshold_m)
    threshold_label = f"{threshold_m:.0f}m"

    if not nearby_pairs:
        script.log_info(f"导入前检查完成：未发现 NetBox 站点存在 {threshold_label} 近邻重复。")
        return

    script.log_warning(
        f"导入前检查发现 {len(nearby_pairs)} 组 NetBox 站点存在 {threshold_label} 近邻重复，请先人工确认。"
    )
    for name_a, name_b, distance in nearby_pairs:
        script.log_warning(f"  · {name_a} <-> {name_b}，距离 {distance:.1f}m")


def _classify_nearby_duplicate(
    name: str,
    latitude: float,
    longitude: float,
    existing_site_coords: list[tuple[str, object, object]],
    batch_site_coords: list[tuple[str, object, object]],
    threshold_m: float = 100.0,
) -> tuple[str, str, float] | None:
    for nearby_name, nearby_latitude, nearby_longitude in existing_site_coords:
        distance = _haversine(latitude, longitude, float(nearby_latitude), float(nearby_longitude))
        if distance < threshold_m:
            return ("existing", nearby_name, distance)

    for nearby_name, nearby_latitude, nearby_longitude in batch_site_coords:
        if nearby_name == name:
            continue
        distance = _haversine(latitude, longitude, float(nearby_latitude), float(nearby_longitude))
        if distance < threshold_m:
            return ("batch", nearby_name, distance)

    return None


class ImportArcGISSites(Script):
    class Meta:
        name = "导入 ArcGIS 站点数据"
        description = "从 ArcGIS Feature Server 批量导入点要素至 NetBox 站点对象，提取 O_NAME 并填入 GPS 坐标。"
        commit_default = True

    arcgis_url = StringVar(
        description="ArcGIS FeatureServer Layer URL",
        default="http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN2026/FeatureServer/0"
    )

    dry_run = BooleanVar(
        description="模拟模式：仅预览导入结果，不写入数据库",
        default=False
    )

    def run(self, data, commit):
        dry_run = data['dry_run']
        if dry_run:
            self.log_warning("⚡ 模拟模式已启用，本次运行不会写入任何数据。")

        base_url = data['arcgis_url'].rstrip('/')
        query_url = f"{base_url}/query"
        
        # 1. 构造请求参数
        params = {
            "where": "1=1",               # 获取所有数据
            "outFields": "O_NAME",        # 仅请求必须属性 O_NAME 
            "returnGeometry": "true",     # 请求拉取几何坐标
            "outSR": "4326",              # 返回 EPSG:4326 经纬度坐标 (WGS84)，供 NetBox GPS 字段使用
            "f": "json"                   # 返回 JSON 格式
        }

        self.log_info(f"正在从 ArcGIS 接口获取数据：{query_url}")
        
        # 2. 发起 HTTP GET 请求获取数据
        try:
            response = requests.get(query_url, params=params, timeout=15)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            self.log_failure(f"请求 ArcGIS 接口失败: {e}")
            return
            
        if "error" in result:
            self.log_failure(f"ArcGIS 服务返回异常: {result['error']}")
            return
            
        features = result.get("features", [])
        if not features:
            self.log_warning("未能获取到任何要素信息 (features 为空)")
            return
            
        self.log_info(f"成功获取 {len(features)} 条节点要素记录。开始同步...")
        
        created_count = 0
        updated_count = 0
        
        # 查重明细记录
        skip_no_field: list[str] = []       # 缺少 O_NAME 或坐标
        skip_has_coords: list[str] = []     # 同名站点已有坐标
        skip_nearby_existing: list[str] = []  # 100m 内命中 NetBox 原有站点
        skip_nearby_batch: list[str] = []     # 100m 内命中本次导入记录
        skip_error: list[str] = []          # 数据库异常
        detail_created: list[str] = []      # 新建明细
        detail_updated: list[str] = []      # 补全明细
        
        # 预加载所有有坐标的站点，用于距离查重
        existing_site_coords = list(
            Site.objects.filter(
                latitude__isnull=False, longitude__isnull=False
            ).values_list('name', 'latitude', 'longitude')
        )
        batch_site_coords: list[tuple[str, object, object]] = []
        self.log_info(f"已加载 {len(existing_site_coords)} 个有坐标的站点用于距离查重 (阈值: 100m)")
        _log_existing_nearby_duplicates(self, existing_site_coords, threshold_m=100.0)
        
        # 3. 遍历提取数据并同步至 NetBox
        for feature in features:
            attrs = feature.get("attributes", {})
            geom = feature.get("geometry", {})
            
            o_name = attrs.get("O_NAME")
            if not o_name:
                skip_no_field.append("(无名记录) — 缺少 O_NAME")
                continue
                
            latitude = geom.get("y")
            longitude = geom.get("x")
            
            if latitude is None or longitude is None:
                skip_no_field.append(f"{o_name} — 缺少经纬度")
                continue
            
            # 使用 django 内置方法生成 slug 唯一标识符
            slug = slugify(o_name)
            
            # 如果 o_name 仅包含中文字符，默认 slugify 会返回空字符串
            if not slug:
                if HAS_PYPINYIN:
                    slug = slugify('-'.join(lazy_pinyin(o_name)))
                
                # 如果依然无法生成，或者未安装 pypinyin，则采用哈希降级
                if not slug:
                    hash_str = hashlib.md5(o_name.encode('utf-8')).hexdigest()[:8]
                    slug = f"site-{hash_str}"
            
            # 检测：防止多个只含极少拼音或英文的不同站点（如"福州CDN"与"厦门CDN"）退化为同样的 slug (如"cdn")
            # 如果该 slug 已经被其他不同名字的站点占用，则在末尾自增数字进行补偿
            original_slug = slug
            counter = 1
            while Site.objects.filter(slug=slug).exclude(name=o_name).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            
            # 4. 执行创建或更新逻辑
            try:
                if dry_run:
                    # 模拟模式：仅查询并预览，不写库
                    existing = Site.objects.filter(name=o_name).first()
                    if existing:
                        if existing.latitude is not None and existing.longitude is not None:
                            skip_has_coords.append(
                                f"{existing.name} — 已有坐标 ({existing.longitude}, {existing.latitude})"
                            )
                        else:
                            updated_count += 1
                            detail_updated.append(f"{existing.name} — 将填入 ({longitude}, {latitude})")
                    else:
                        nearby = _classify_nearby_duplicate(
                            name=o_name,
                            latitude=float(latitude),
                            longitude=float(longitude),
                            existing_site_coords=existing_site_coords,
                            batch_site_coords=batch_site_coords,
                            threshold_m=100.0,
                        )
                        if nearby:
                            duplicate_type, nearby_name, distance = nearby
                            if duplicate_type == "existing":
                                skip_nearby_existing.append(
                                    f"{o_name} — 与 NetBox 原有站点 {nearby_name} 相距 {distance:.1f}m"
                                )
                            else:
                                skip_nearby_batch.append(
                                    f"{o_name} — 与本次导入记录 {nearby_name} 相距 {distance:.1f}m"
                                )
                        else:
                            created_count += 1
                            detail_created.append(f"{o_name} (slug: {slug}, 坐标: {longitude}, {latitude})")
                            batch_site_coords.append((o_name, latitude, longitude))
                else:
                    existing_by_name = Site.objects.filter(name=o_name).first()
                    if not existing_by_name:
                        nearby = _classify_nearby_duplicate(
                            name=o_name,
                            latitude=float(latitude),
                            longitude=float(longitude),
                            existing_site_coords=existing_site_coords,
                            batch_site_coords=batch_site_coords,
                            threshold_m=100.0,
                        )
                        if nearby:
                            duplicate_type, nearby_name, distance = nearby
                            if duplicate_type == "existing":
                                skip_nearby_existing.append(
                                    f"{o_name} — 与 NetBox 原有站点 {nearby_name} 相距 {distance:.1f}m"
                                )
                            else:
                                skip_nearby_batch.append(
                                    f"{o_name} — 与本次导入记录 {nearby_name} 相距 {distance:.1f}m"
                                )
                            continue

                    # 正式模式：执行数据库写入
                    site, created = Site.objects.get_or_create(
                        name=o_name,
                        defaults={
                            'slug': slug,
                            'status': SiteStatusChoices.STATUS_ACTIVE,
                            'latitude': latitude,
                            'longitude': longitude,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        detail_created.append(f"{site.name} (坐标: {longitude}, {latitude})")
                        batch_site_coords.append((o_name, latitude, longitude))
                    else:
                        # 站点已存在：有坐标则跳过，无坐标则补全
                        if site.latitude is not None and site.longitude is not None:
                            skip_has_coords.append(
                                f"{site.name} — 已有坐标 ({site.longitude}, {site.latitude})"
                            )
                        else:
                            site.latitude = latitude
                            site.longitude = longitude
                            site.save()
                            updated_count += 1
                            detail_updated.append(f"{site.name} — 填入 ({longitude}, {latitude})")
                        
            except Exception as e:
                skip_error.append(f"{o_name} — {e}")
                
        # ── 输出汇总报告 ──
        prefix = "预计" if dry_run else ""
        mode_label = "模拟" if dry_run else "导入"
        total_skipped = (
            len(skip_no_field)
            + len(skip_has_coords)
            + len(skip_nearby_existing)
            + len(skip_nearby_batch)
            + len(skip_error)
        )
        
        self.log_info(
            f"{'═' * 40}\n"
            f"  {mode_label}完成！汇总统计\n"
            f"{'─' * 40}\n"
            f"  {prefix}新建: {created_count}\n"
            f"  {prefix}补全坐标: {updated_count}\n"
            f"  跳过 - 缺少字段: {len(skip_no_field)}\n"
            f"  跳过 - 已有坐标: {len(skip_has_coords)}\n"
            f"  跳过 - 近邻查重(NetBox 原有站点): {len(skip_nearby_existing)}\n"
            f"  跳过 - 近邻查重(本次导入记录): {len(skip_nearby_batch)}\n"
            f"  跳过 - 数据库异常: {len(skip_error)}\n"
            f"  跳过合计: {total_skipped}\n"
            f"  总记录: {len(features)}\n"
            f"{'═' * 40}"
        )
        
        # ── 输出各类明细 ──
        if detail_created:
            self.log_success(f"▶ {prefix}新建站点明细 ({len(detail_created)} 条):")
            for item in detail_created:
                self.log_success(f"  · {item}")
        
        if detail_updated:
            self.log_success(f"▶ {prefix}补全坐标明细 ({len(detail_updated)} 条):")
            for item in detail_updated:
                self.log_success(f"  · {item}")
        
        if skip_has_coords:
            self.log_info(f"▶ 跳过 - 已有坐标明细 ({len(skip_has_coords)} 条):")
            for item in skip_has_coords:
                self.log_info(f"  · {item}")
        
        if skip_nearby_existing:
            self.log_warning(f"▶ 跳过 - 近邻查重(NetBox 原有站点)明细 ({len(skip_nearby_existing)} 条):")
            for item in skip_nearby_existing:
                self.log_warning(f"  · {item}")

        if skip_nearby_batch:
            self.log_warning(f"▶ 跳过 - 近邻查重(本次导入记录)明细 ({len(skip_nearby_batch)} 条):")
            for item in skip_nearby_batch:
                self.log_warning(f"  · {item}")
        
        if skip_no_field:
            self.log_warning(f"▶ 跳过 - 缺少字段明细 ({len(skip_no_field)} 条):")
            for item in skip_no_field:
                self.log_warning(f"  · {item}")
        
        if skip_error:
            self.log_failure(f"▶ 跳过 - 数据库异常明细 ({len(skip_error)} 条):")
            for item in skip_error:
                self.log_failure(f"  · {item}")
