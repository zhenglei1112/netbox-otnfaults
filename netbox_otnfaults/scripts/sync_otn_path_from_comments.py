import re
from decimal import Decimal
from extras.scripts import Script
from netbox_otnfaults.models import OtnPath, CableTypeChoices

class SyncOtnPathFromComments(Script):
    class Meta:
        name = "根据评论清洗并更新光路属性"
        description = "查阅所有光路的评论（comments）字段：提取包含'项目距离：xxKM'或'线路长度：xxKM'的字样自动覆盖计算长度；提取含有'路由属性：xx'的字样覆盖光缆类型，提取失败项执行清空或自建兜底。"
        commit_default = False

    def run(self, data, commit):
        paths = OtnPath.objects.all()
        
        # 正则表达式：兼容"项目距离"与"线路长度"、全角/半角冒号、不限大小写的KM/km以及可能不规范的空格
        distance_pattern = re.compile(r'(?:项目距离|线路长度)[：:]\s*([\d\.]+)\s*[Kk][Mm]')
        
        stats = {
            'total_paths': paths.count(),
            'changed_paths': 0,                 
            'length_found': 0,               
            'length_cleared': 0,                
            'length_parse_errors': 0,           
            'type_leased': 0,          
            'type_coord': 0,           
            'type_self': 0,            
            'type_defaulted': 0,       
        }
        
        self.log_info(f"开始全局扫描 {stats['total_paths']} 条光路系统...")
        
        for path in paths:
            changed = False
            comments = path.comments or ""
            
            # ==========================
            # 第一部分：清洗并覆盖计算长度
            # ==========================
            match_dist = distance_pattern.search(comments)
            if match_dist:
                dist_val_str = match_dist.group(1)
                try:
                    # 按照要求，查阅到 58KM，我们直接将 58 写入算术长度字段
                    new_length = Decimal(dist_val_str).quantize(Decimal("0.00"))
                    if path.calculated_length != new_length:
                        path.calculated_length = new_length
                        changed = True
                    stats['length_found'] += 1
                except Exception:
                    self.log_warning(f"警告：无法将提取到的距离值 '{dist_val_str}' 转化为有效数字 (Path ID:{path.pk})")
                    stats['length_parse_errors'] += 1
            else:
                # 没找到相关“项目距离/线路长度”字眼，依据要求强制清空该条计算字段
                if path.calculated_length is not None:
                    path.calculated_length = None
                    changed = True
                stats['length_cleared'] += 1
                    
            # ==========================
            # 第二部分：清洗并覆盖路由属性（光缆类型）
            # ==========================
            new_cable_type = CableTypeChoices.SELF_BUILT  # '自建' 亦是本项探测不到时的默认兜底行为
            cable_type_found = False
            
            # 使用兼容包含查找（防止人工输入时大小写、中英文冒号或打错空格的不规整错别字）
            if "路由属性：租赁" in comments or "路由属性:租赁" in comments or "路由属性: 租赁" in comments:
                new_cable_type = CableTypeChoices.LEASED
                stats['type_leased'] += 1
                cable_type_found = True
            elif "路由属性：协调" in comments or "路由属性:协调" in comments or "路由属性: 协调" in comments:
                new_cable_type = CableTypeChoices.COORDINATED
                stats['type_coord'] += 1
                cable_type_found = True
            elif "路由属性：自建" in comments or "路由属性:自建" in comments or "路由属性: 自建" in comments:
                new_cable_type = CableTypeChoices.SELF_BUILT
                stats['type_self'] += 1
                cable_type_found = True
                
            if not cable_type_found:
                stats['type_defaulted'] += 1
                
            # 当从评论区提炼出的配置和现有系统持久层存的不一致时，标记需要修改动作
            if path.cable_type != new_cable_type:
                path.cable_type = new_cable_type
                changed = True
                
            # ==========================
            # 判断持久化并记账
            # ==========================
            if changed:
                try:
                    if commit:
                        path.full_clean()
                        path.save()
                    stats['changed_paths'] += 1
                except Exception as e:
                    self.log_failure(f"保存更新失败 [{path.name}]: {str(e)}")
                    
        # ==========================
        # 总结汇报与修改指标分类清单
        # ==========================
        self.log_info("========== 扫描执行完毕 ==========")
        
        msg = (
            f"大体总览：全网共 {stats['total_paths']} 条光路，本次脚本实际变更（系统中有旧数据被覆盖改写）的光路包含 {stats['changed_paths']} 条。\n\n"
            f"【所有 1070 条光路当前的属性特征大盘分布】：\n"
            f" > 长度字段（calculated_length）识别分布 <\n"
            f"   - 具备合法的距离标签： {stats['length_found']} 条\n"
            f"   - 没有找到标签（从而确立/保持置空状态）： {stats['length_cleared']} 条\n"
        )
        if stats['length_parse_errors'] > 0:
            msg += f"   - 具有标签但由于格式异常而跳过： {stats['length_parse_errors']} 条\n"
            
        msg += (
            f"\n > 属性字段（cable_type）识别分布 <\n"
            f"   - 含有明确的文本标签【租赁】： {stats['type_leased']} 条\n"
            f"   - 含有明确的文本标签【协调】： {stats['type_coord']} 条\n"
            f"   - 含有明确的文本标签【自建】： {stats['type_self']} 条\n"
            f"   - 无明确文本标签，从而套用兜底模式【自建】： {stats['type_defaulted']} 条\n"
        )
        
        self.log_success(msg)
        return msg
