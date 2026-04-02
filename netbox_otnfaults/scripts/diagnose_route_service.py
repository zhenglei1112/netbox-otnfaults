import math
from extras.scripts import Script
from netbox_otnfaults.models import OtnPath
from dcim.models import Site

def calculate_distance(lon1, lat1, lon2, lat2):
    """计算两个经纬度坐标之间的球面距离（单位：公里）使用 Haversine 公式"""
    if None in (lon1, lat1, lon2, lat2):
        return float('inf')
        
    try:
        lon1, lat1, lon2, lat2 = map(float, [lon1, lat1, lon2, lat2])
        # 将十进制度数转化为弧度
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
        
        # haversine公式
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # 地球平均半径，单位为公里
        return c * r
    except (ValueError, TypeError):
        return float('inf')


class CheckUnknownSitesScript(Script):
    class Meta:
        name = "诊断未指定站点的光缆路径"
        description = "检查光缆路径中端点(A端/Z端)被标记为'未指定'的数据，并根据空间几何坐标推荐最近的真实物理站点。"

    def run(self, data, commit):
        # 1. 查询所有A端或Z端名字包含'未指定'的光缆路径
        paths = OtnPath.objects.filter(site_a__name__contains='未指定') | OtnPath.objects.filter(site_z__name__contains='未指定')
        paths = paths.distinct()
        
        total = paths.count()
        if total == 0:
            self.log_success("恭喜！系统中当前未发现包含 '未指定' 站点的光缆路径。")
            return
            
        self.log_info(f"== 开始诊断：共发现 {total} 条 A端或Z端为 '未指定' 的光缆路径 ==")
        
        # 2. 获取所有的正常的带有效经纬度的候选站点
        all_sites = Site.objects.exclude(name__contains='未指定').exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        all_sites_list = list(all_sites) # 转换为列表，避免循环中重复读库
        
        if not all_sites_list:
            self.log_warning("系统中没有找到任何包含有效经纬度的候选物理站点，无法进行最近距离辅助判断！")
            return

        within_1km_count = 0

        for path in paths:
            has_endpoint_within_1km = False
            need_save = False
            # 3. 提取每条路线的 geometry 属性
            geom = path.geometry
            coords = None
            
            # 支持标准的 GeoJSON { "type": "LineString", "coordinates": [...] }
            if isinstance(geom, dict) and 'coordinates' in geom:
                coords = geom['coordinates']
            # 或者直接是由经纬度对构成的纯数组 [[lon, lat], [lon, lat], ...]
            elif isinstance(geom, list) and len(geom) > 0 and isinstance(geom[0], list):
                coords = geom
                
            if not coords or len(coords) < 1:
                self.log_warning(f"⚠️ 路径 [{path.name}] 的空间几何数据无效或为空，无法为其寻找最近站点！ (描述: {path.description})")
                continue
            
            # 检查 A 端是否未指定
            if '未指定' in path.site_a.name:
                start_coord = coords[0] # 取首个点坐标 [lon, lat]
                closest_site_a = None
                min_dist_a = float('inf')
                
                # 枚举库中所有站点找最小距离
                for site in all_sites_list:
                    dist = calculate_distance(start_coord[0], start_coord[1], site.longitude, site.latitude)
                    if dist < min_dist_a:
                        min_dist_a = dist
                        closest_site_a = site
                
                if closest_site_a:
                    self.log_success(
                        f"🔹 路径 [{path.name}] (描述: {path.description}) A端当前为未指定 - "
                        f"起点坐标({start_coord[0]}, {start_coord[1]}), 推荐最近站点: "
                        f"【{closest_site_a.name}】 (距离: {min_dist_a:.2f} km)"
                    )
                    if min_dist_a <= 1.0:
                        has_endpoint_within_1km = True
                        path.site_a = closest_site_a
                        need_save = True
                else:
                    self.log_warning(f"⚠️ 路径 [{path.name}] (描述: {path.description}) 无法为其A端坐标找到具备有效经纬度的最近物理站点。")
            
            # 检查 Z 端是否未指定
            if '未指定' in path.site_z.name:
                end_coord = coords[-1] # 取最后一个点坐标 [lon, lat]
                closest_site_z = None
                min_dist_z = float('inf')
                
                # 枚举库中所有站点找最小距离
                for site in all_sites_list:
                    dist = calculate_distance(end_coord[0], end_coord[1], site.longitude, site.latitude)
                    if dist < min_dist_z:
                        min_dist_z = dist
                        closest_site_z = site
                
                if closest_site_z:
                    self.log_success(
                        f"🔸 路径 [{path.name}] (描述: {path.description}) Z端当前为未指定 - "
                        f"终点坐标({end_coord[0]}, {end_coord[1]}), 推荐最近站点: "
                        f"【{closest_site_z.name}】 (距离: {min_dist_z:.2f} km)"
                    )
                    if min_dist_z <= 1.0:
                        has_endpoint_within_1km = True
                        path.site_z = closest_site_z
                        need_save = True
                else:
                    self.log_warning(f"⚠️ 路径 [{path.name}] (描述: {path.description}) 无法为其Z端坐标找到具备有效经纬度的最近物理站点。")
            
            if need_save:
                path.save()
                self.log_success(f"✅ 自动修正成功: 路径 [{path.name}] 的未指定站点已被替换并更新到数据库！")
            
            if has_endpoint_within_1km:
                within_1km_count += 1
        
        self.log_info(f"== 当次针对未指定站点路径及坐标位置的智能诊断与修正完成。其中距离真实物理站点在 1km 以内被修正的路径共计: {within_1km_count} 条 ==")
