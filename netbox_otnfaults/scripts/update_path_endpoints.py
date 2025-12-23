"""
NetBox Custom Script: Update path endpoints based on distance threshold
NetBox自定义脚本：根据距离阈值更新路径端点

功能：
1. 查找所有一端或两端为“未指定”站点的光缆路径（OtnPath）。
2. 根据路径的几何数据（Geometry），计算起点/终点与现有站点的距离。
3. 如果距离在设定的阈值内，自动将“未指定”更新为最近的站点。
4. 自动识别路径方向（即几何起点对应A端还是Z端）。
5. 更新路径名称。
"""

import math
import json
from decimal import Decimal
from django.db.models import Q
from extras.scripts import Script, ObjectVar, IntegerVar, BooleanVar
from dcim.models import Site
from netbox_otnfaults.models import OtnPath

class UpdatePathEndpoints(Script):
    class Meta:
        name = "更新 OtnPath 端点 (基于距离)"
        description = "根据几何路径端点的距离，自动修正为'未指定'的站点。"
        commit_default = False

    # 脚本参数
    unspecified_site = ObjectVar(
        model=Site,
        label="选择'未指定'站点对象",
        description="请选择代表'未指定'或'未知'的站点记录，脚本将查找连接到此站点的路径。",
        required=True
    )

    threshold = IntegerVar(
        label="距离阈值 (米)",
        description="如果几何端点与某站点的距离小于此数值，则认为匹配成功。",
        default=100,
        min_value=1
    )

    dry_run = BooleanVar(
        label="模拟运行",
        description="勾选后仅显示将要做的更改，不实际保存。",
        default=True
    )

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        计算两点间的 Haversine 距离 (单位: 米)
        """
        R = 6371000  # 地球半径 (米)
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def get_latest_sites_cache(self):
        """
        加载所有具有有效坐标的站点到内存列表，避免循环查询数据库
        """
        sites = []
        # exclude sites without coordinates
        valid_sites = Site.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        
        for s in valid_sites:
            sites.append({
                'id': s.id,
                'site_obj': s,
                'lat': float(s.latitude),
                'lon': float(s.longitude),
                'name': s.name
            })
        return sites

    def find_nearest_site(self, lat, lon, sites_cache):
        """
        在缓存中查找距离最近的站点
        """
        nearest_site = None
        min_dist = float('inf')

        for s_data in sites_cache:
            d = self.haversine_distance(lat, lon, s_data['lat'], s_data['lon'])
            if d < min_dist:
                min_dist = d
                nearest_site = s_data['site_obj']

        return nearest_site, min_dist

    def run(self, data, commit):
        target_unspecified_site = data['unspecified_site']
        threshold = data['threshold']
        is_dry_run = data['dry_run']

        # 1. 加载站点缓存
        sites_cache = self.get_latest_sites_cache()
        self.log_info(f"已加载 {len(sites_cache)} 个具有坐标的站点用于比对。")

        # 2. 查找所有涉及该未指定站点的路径
        paths = OtnPath.objects.filter(
            Q(site_a=target_unspecified_site) | Q(site_z=target_unspecified_site)
        )

        if not paths.exists():
            self.log_warning(f"没有找到连接到 '{target_unspecified_site.name}' 的路径。")
            return "无操作。"

        update_count = 0
        self.log_info(f"找到 {paths.count()} 条待检查的路径。")

        for path in paths:
            # 检查是否有几何数据
            if not path.geometry:
                self.log_warning(f"路径 [{path.name}] (ID: {path.id}) 没有几何数据，跳过。")
                continue

            # 解析几何数据
            # 假设 geometry 是一个 GeoJSON coordinates 数组 [[lon, lat], [lon, lat], ...]
            # 或者符合 import_otn_paths.py 中的格式
            geo_data = path.geometry
            if isinstance(geo_data, str):
                try:
                    geo_data = json.loads(geo_data)
                except json.JSONDecodeError:
                    self.log_failure(f"路径 [{path.name}] 的几何数据格式错误。")
                    continue
            
            # 简单的健壮性检查，确保它是一个列表且至少有2个点
            if not isinstance(geo_data, list) or len(geo_data) < 2:
                 self.log_warning(f"路径 [{path.name}] 的几何数据格式不符合预期 (应为坐标列表)。")
                 continue
            
            # 获取起点和终点 (注意: GeoJSON 通常是 [lon, lat])
            # 我们假设数据格式与 import_otn_paths.py 中一致: [[x, y], ...]
            # 需要判断 x, y 是否是经纬度 (-180~180, -90~90)
            
            p_start = geo_data[0]
            p_end = geo_data[-1]
            
            try:
                # 转换为 float
                lon_start, lat_start = float(p_start[0]), float(p_start[1])
                lon_end, lat_end = float(p_end[0]), float(p_end[1])
            except (IndexError, ValueError):
                self.log_warning(f"路径 [{path.name}] 坐标数据解析失败。")
                continue

            # 准备更新变量
            new_site_a = path.site_a
            new_site_z = path.site_z
            log_msgs = []
            
            # -----------------------------------------------------------
            # 核心逻辑：判断哪一头对应哪个站点
            # -----------------------------------------------------------
            
            # 情况 A: 两头都是“未指定”
            if path.site_a == target_unspecified_site and path.site_z == target_unspecified_site:
                # 直接找最近
                s_start, d_start = self.find_nearest_site(lat_start, lon_start, sites_cache)
                s_end, d_end = self.find_nearest_site(lat_end, lon_end, sites_cache)
                
                if s_start and d_start <= threshold:
                    new_site_a = s_start
                    log_msgs.append(f"起点 -> {s_start.name} (距离 {d_start:.1f}米)")
                
                if s_end and d_end <= threshold:
                    new_site_z = s_end
                    log_msgs.append(f"终点 -> {s_end.name} (距离 {d_end:.1f}米)")
            
            # 情况 B: 只有一头是“未指定” (需要判断方向)
            else:
                known_site = None
                unknown_side = None # 'site_a' or 'site_z'
                
                if path.site_a == target_unspecified_site:
                    known_site = path.site_z
                    unknown_side = 'site_a'
                else:
                    known_site = path.site_a
                    unknown_side = 'site_z'
                
                # 检查已知站点是否有坐标
                if not known_site.latitude or not known_site.longitude:
                    self.log_warning(f"路径 [{path.name}] 的已知站点 {known_site.name} 没有坐标，无法判断方向，跳过。")
                    continue
                
                # 计算已知站点到起点和终点的距离，以判断它是哪一头
                dist_known_to_start = self.haversine_distance(
                    float(known_site.latitude), float(known_site.longitude),
                    lat_start, lon_start
                )
                dist_known_to_end = self.haversine_distance(
                    float(known_site.latitude), float(known_site.longitude),
                    lat_end, lon_end
                )
                
                # 判断已知站点在哪一头
                # 如果它离起点更近，那它就是起点对应的那一端。
                # 那么“未指定”的那一端就应该去匹配终点。
                target_lat_for_unknown, target_lon_for_unknown = 0, 0
                
                if dist_known_to_start < dist_known_to_end:
                    # 已知站点在起点侧
                    # log_msgs.append(f"经判断，已知站点 {known_site.name} 位于几何路径起点侧。")
                    # 因此，我们需要为“终点”寻找匹配站点
                    target_lat_for_unknown = lat_end
                    target_lon_for_unknown = lon_end
                else:
                    # 已知站点在终点侧
                    # log_msgs.append(f"经判断，已知站点 {known_site.name} 位于几何路径终点侧。")
                    # 因此，我们需要为“起点”寻找匹配站点
                    target_lat_for_unknown = lat_start
                    target_lon_for_unknown = lon_start
                
                # 查找最近站点
                found_site, found_dist = self.find_nearest_site(target_lat_for_unknown, target_lon_for_unknown, sites_cache)
                
                if found_site and found_dist <= threshold:
                    if unknown_side == 'site_a':
                        new_site_a = found_site
                    else:
                        new_site_z = found_site
                    log_msgs.append(f"找到最近站点 {found_site.name} (距离 {found_dist:.1f}米)，替换未指定端。")

            # -----------------------------------------------------------
            # 执行更新
            # -----------------------------------------------------------
            if new_site_a != path.site_a or new_site_z != path.site_z:
                update_count += 1
                new_name = f"{new_site_a.name}-{new_site_z.name}"
                
                msg = f"路径 [{path.name}] 将更新: \n" + "\n".join(log_msgs) + f"\n新名称: {new_name}"
                
                if not is_dry_run and commit: # Script `commit` checkbox logic is usually handled by `commit` arg, but `dry_run` param adds explicit control
                    path.site_a = new_site_a
                    path.site_z = new_site_z
                    path.name = new_name
                    path.save()
                    self.log_success(msg)
                else:
                    self.log_info("[模拟] " + msg)
            else:
                # self.log_info(f"路径 [{path.name}] 无需更新 (未找到阈值内的更近站点)。")
                pass

        if update_count == 0:
            return "运行结束，没有路径需要更新。"
        else:
            return f"运行结束，共处理建议更新 {update_count} 条路径。"
