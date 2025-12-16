"""
NetBox自定义脚本：清理故障影响业务的重复数据

功能：
1. 查找重复的 OtnFaultImpact 数据（基于 otn_fault 和 impacted_service 判断）
2. 随机保留一条，删除其余重复记录

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.remove_duplicate_impacts
2. 选择脚本类：RemoveDuplicateImpacts
3. 运行脚本
"""

import random
from django.db import transaction
from django.db.models import Count
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnFaultImpact

class RemoveDuplicateImpacts(Script):
    """
    清理重复的故障影响业务数据
    """
    
    class Meta:
        name = "清理重复的故障业务影响"
        description = "检查并删除重复的故障影响业务记录（同一故障和同一业务），每组重复数据只保留一条"
        commit_default = True
    
    # 脚本参数
    dry_run = BooleanVar(
        label="预览模式",
        description="仅预览将要删除的数据，不实际执行删除",
        default=True
    )
    
    def run(self, data, commit):
        """脚本主入口"""
        dry_run = data['dry_run']
        
        self.log_info("开始检查重复数据...")
        
        # 1. 查找所有记录
        all_impacts = OtnFaultImpact.objects.all()
        total_count = all_impacts.count()
        self.log_info(f"总计扫描到 {total_count} 条记录")
        
        # 2. 分组查找重复
        # 使用字典来分组：key = (fault_id, service_id), value = [id1, id2, ...]
        impact_groups = {}
        
        for impact in all_impacts:
            key = (impact.otn_fault_id, impact.impacted_service_id)
            if key not in impact_groups:
                impact_groups[key] = []
            impact_groups[key].append(impact.id)
            
        # 3. 识别出有重复的组
        duplicate_groups = {k: v for k, v in impact_groups.items() if len(v) > 1}
        
        if not duplicate_groups:
            self.log_success("未发现任何重复数据！")
            return "检查完成，无重复数据。"
            
        self.log_warning(f"发现 {len(duplicate_groups)} 组重复数据")
        
        ids_to_delete = []
        kept_count = 0
        
        for key, ids in duplicate_groups.items():
            fault_id, service_id = key
            
            # 随机选择一个保留
            id_to_keep = random.choice(ids)
            
            # 其余的添加到删除列表
            current_group_delete = [i for i in ids if i != id_to_keep]
            ids_to_delete.extend(current_group_delete)
            kept_count += 1
            
            self.log_info(f"故障ID {fault_id} - 业务ID {service_id}: 发现 {len(ids)} 条记录. 保留 ID {id_to_keep}, 计划删除 IDs {current_group_delete}")
            
        delete_count = len(ids_to_delete)
        
        # 4. 执行删除
        if ids_to_delete:
            if dry_run:
                self.log_warning(f"预览模式：将删除 {delete_count} 条重复记录，保留 {kept_count} 条有效记录。未实际执行删除。")
            else:
                try:
                    with transaction.atomic():
                        # 使用 filter(id__in=...) 批量删除
                        OtnFaultImpact.objects.filter(id__in=ids_to_delete).delete()
                    self.log_success(f"成功删除了 {delete_count} 条重复记录！")
                except Exception as e:
                    self.log_failure(f"删除失败: {str(e)}")
                    raise
        
        return f"检查完成。发现 {len(duplicate_groups)} 组重复，涉及 {delete_count + kept_count} 条记录。{'计划' if dry_run else '已'}删除 {delete_count} 条。"
