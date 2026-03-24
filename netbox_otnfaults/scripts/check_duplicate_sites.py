import re
from collections import defaultdict
from dcim.models import Site
from extras.scripts import Script

class CheckDuplicateSites(Script):
    class Meta:
        name = "站点查重（相似名与机房后缀）"
        description = "检查站点模型中高度相似或重复命名的站点，例如带有'(机房)'、'节点'等后缀的重复项以及名称前缀包含关系的情况。"
        commit_default = False

    def run(self, data, commit):
        sites = Site.objects.all().order_by('name')
        sites_list = list(sites)
        
        # 常见冗余后缀正则
        # 匹配结尾处的 "机房", "节点", "中心"，且可能被中文或英文的括号包裹
        redundant_pattern = re.compile(r'[(（]?(机房|节点)[)）]?$')
        
        normalized_map = defaultdict(list)
        
        # 第一阶段：正则归一化探测法
        # 针对 "中国科技网上海分中心" 与 "中国科技网上海分中心（机房）" 这样的模式
        for site in sites_list:
            base_name = site.name.strip()
            # 剥离典型后缀
            norm_name = redundant_pattern.sub('', base_name).strip()
            
            # 如果剥离之后成了空字符串，说明它自己本身就只有后缀名，保留原名
            if not norm_name:
                norm_name = base_name
                
            normalized_map[norm_name].append(site)
            
        duplicate_groups = []
        for norm_name, site_group in normalized_map.items():
            if len(site_group) > 1:
                duplicate_groups.append((norm_name, site_group))
                
        # 第二阶段：前缀包含探测法
        # 针对排序后，名称相似度极高且存在包含关系的（如 A 与 AB）
        # 且没有被第一阶段抓到的情况
        prefix_duplicates = []
        for i in range(len(sites_list) - 1):
            s1 = sites_list[i]
            s2 = sites_list[i+1]
            n1 = s1.name.strip()
            n2 = s2.name.strip()
            
            # 判断较短的站名是否构成了相邻下一个站点名的绝对前缀，并且字数相差不大（比如仅多出 1-5 个字）
            if n2.startswith(n1) and 0 < len(n2) - len(n1) <= 5:
                # 确认这两者有没有已经在第一阶段的正则检测同组中被抛出
                norm1 = redundant_pattern.sub('', n1).strip()
                norm2 = redundant_pattern.sub('', n2).strip()
                if norm1 != norm2:
                    prefix_duplicates.append((s1, s2))

        # 第三阶段：空间地理位置极近探测法（小于 100 米）
        import math
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371000 # 地球半径，单位米
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance_threshold = 100 # 米
        geo_sites = [s for s in sites_list if s.latitude is not None and s.longitude is not None]
        # 按纬度排序，为了优化双层循环计算
        geo_sites.sort(key=lambda s: float(s.latitude))
        
        geo_duplicates = []
        for i in range(len(geo_sites)):
            s1 = geo_sites[i]
            lat1, lon1 = float(s1.latitude), float(s1.longitude)
            for j in range(i+1, len(geo_sites)):
                s2 = geo_sites[j]
                lat2, lon2 = float(s2.latitude), float(s2.longitude)
                
                # 纬度相差 0.002度 (约220米)，由于纬度已递增排序，后续所有的距离只会越来越远，提前跳出内层循环
                if (lat2 - lat1) > 0.002:
                    break
                    
                dist = haversine(lat1, lon1, lat2, lon2)
                if dist <= distance_threshold:
                    geo_duplicates.append((s1, s2, dist))

        # 日志输出报告
        self.log_info(f"全网共扫描了 {len(sites_list)} 个站点。正在输出查重报告...")
        
        total_issues = 0
        
        if duplicate_groups:
            self.log_info("========== 阶段一：基于特定后缀（机房/节点）的重复审查结果 ==========")
            for norm_name, group in duplicate_groups:
                names_fmt = " | ".join([f"{s.name} (ID:{s.id})" for s in group])
                self.log_warning(f"发现多身同源 -> 标准主体定名为【{norm_name}】：包含 => {names_fmt}")
                total_issues += 1
                
        if prefix_duplicates:
            self.log_info("========== 阶段二：基于相邻长短名的包含重复审查结果 ==========")
            for s1, s2 in prefix_duplicates:
                self.log_warning(f"发现相互包含 -> 【{s1.name}】 (ID:{s1.id}) 与更长的 【{s2.name}】 (ID:{s2.id})")
                total_issues += 1
                
        if geo_duplicates:
            self.log_info(f"========== 阶段三：基于空间极近距离（<{distance_threshold}米）的重复审查结果 ==========")
            for s1, s2, dist in geo_duplicates:
                self.log_warning(f"发现坐标重合/极近 -> 【{s1.name}】(ID:{s1.id}) 与 【{s2.name}】(ID:{s2.id}) 相距仅 {dist:.1f} 米")
                total_issues += 1
                
        # 最终汇报总结
        if total_issues == 0:
            self.log_success("检查完毕！所有站点非常标准，未检测出疑似复用的机房。")
        else:
            self.log_info(f"检查完毕！共计抛出了 {total_issues} 组预警！")
