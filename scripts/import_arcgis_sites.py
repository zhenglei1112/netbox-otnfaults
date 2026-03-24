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
from extras.scripts import Script, StringVar

class ImportArcGISSites(Script):
    class Meta:
        name = "导入 ArcGIS 站点数据"
        description = "从 ArcGIS Feature Server 批量导入点要素至 NetBox 站点对象，提取 O_NAME 并填入 GPS 坐标。"
        commit_default = True

    arcgis_url = StringVar(
        description="ArcGIS FeatureServer Layer URL",
        default="http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN2026/FeatureServer/0"
    )

    def run(self, data, commit):
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
        skipped_count = 0
        
        # 3. 遍历提取数据并同步至 NetBox
        for feature in features:
            attrs = feature.get("attributes", {})
            geom = feature.get("geometry", {})
            
            o_name = attrs.get("O_NAME")
            if not o_name:
                self.log_warning("跳过一条记录：缺少 O_NAME")
                skipped_count += 1
                continue
                
            latitude = geom.get("y")
            longitude = geom.get("x")
            
            if latitude is None or longitude is None:
                self.log_warning(f"跳过站点 {o_name}: 缺少有效经纬度信息 (y 或 x 为空)")
                skipped_count += 1
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
                # 尝试根据名称获取现有的站点，如果不存在则按 defaults 创建
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
                    self.log_success(f"[新建] 站点: {site.name} (坐标: {longitude}, {latitude})")
                else:
                    # 站点已存在，检查并更新经纬度
                    coords_changed = False
                    
                    if site.latitude != latitude or site.longitude != longitude:
                        site.latitude = latitude
                        site.longitude = longitude
                        site.save()
                        coords_changed = True
                        
                    if coords_changed:
                        updated_count += 1
                        self.log_success(f"[更新] 站点坐标: {site.name} 更新为坐标({longitude}, {latitude})")
                    else:
                        self.log_debug(f"[保持] 站点 {site.name} 坐标无变化。")
                        
            except Exception as e:
                self.log_failure(f"处理站点 {o_name} 时发生数据库错误: {e}")
                skipped_count += 1
                
        # 输出统计汇总
        self.log_info(
            f"导入完成！汇总报告 — "
            f"新建数: {created_count}, 更新数: {updated_count}, 跳过/失败数: {skipped_count} (总记录: {len(features)})"
        )
