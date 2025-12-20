"""
NetBox自定义脚本：清理光缆路径的重复数据

功能：
1. 查找重复的 OtnPath 数据（基于 name, site_a, site_z 判断）
2. 只保留一条，删除其余重复记录
3. 将保留记录的描述字段修改为 "8800,9800"

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.remove_duplicate_paths
2. 选择脚本类：RemoveDuplicatePaths
3. 运行脚本
"""

from django.db import transaction
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnPath


class RemoveDuplicatePaths(Script):
    """
    清理重复的光缆路径数据
    """
    
    class Meta:
        name = "清理重复的光缆路径"
        description = "检查并删除重复的光缆路径记录（同一名称、A端站点、Z端站点），每组只保留一条，并将描述修改为8800,9800"
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
        
        self.log_info("开始检查光缆路径重复数据...")
        
        # 1. 查找所有记录
        all_paths = OtnPath.objects.all()
        total_count = all_paths.count()
        self.log_info(f"总计扫描到 {total_count} 条光缆路径记录")
        
        # 2. 分组查找重复
        # 使用字典来分组：key = (name, site_a_id, site_z_id), value = [path对象列表]
        path_groups = {}
        
        for path in all_paths:
            key = (path.name, path.site_a_id, path.site_z_id)
            if key not in path_groups:
                path_groups[key] = []
            path_groups[key].append(path)
            
        # 3. 识别出有重复的组
        duplicate_groups = {k: v for k, v in path_groups.items() if len(v) > 1}
        
        if not duplicate_groups:
            self.log_success("未发现任何重复数据！")
            return "检查完成，无重复数据。"
            
        self.log_warning(f"发现 {len(duplicate_groups)} 组重复数据")
        
        ids_to_delete = []
        paths_to_update = []
        kept_count = 0
        
        for key, paths in duplicate_groups.items():
            name, site_a_id, site_z_id = key
            
            # 选择第一个保留（按ID排序，保留最早创建的）
            paths_sorted = sorted(paths, key=lambda x: x.id)
            path_to_keep = paths_sorted[0]
            
            # 其余的添加到删除列表
            paths_to_delete = paths_sorted[1:]
            current_delete_ids = [p.id for p in paths_to_delete]
            ids_to_delete.extend(current_delete_ids)
            
            # 将保留的路径添加到更新列表
            paths_to_update.append(path_to_keep)
            kept_count += 1
            
            # 获取站点名称用于日志
            site_a_name = path_to_keep.site_a.name if path_to_keep.site_a else "未知"
            site_z_name = path_to_keep.site_z.name if path_to_keep.site_z else "未知"
            
            self.log_info(
                f"路径 '{name}' ({site_a_name} -> {site_z_name}): "
                f"发现 {len(paths)} 条重复记录. "
                f"保留 ID {path_to_keep.id}, 计划删除 IDs {current_delete_ids}"
            )
            
        delete_count = len(ids_to_delete)
        
        # 4. 执行删除和更新
        if dry_run:
            self.log_warning(
                f"预览模式：将删除 {delete_count} 条重复记录，"
                f"保留并更新 {kept_count} 条有效记录的描述为 '8800,9800'。"
                f"未实际执行操作。"
            )
        else:
            try:
                with transaction.atomic():
                    # 批量删除重复记录
                    if ids_to_delete:
                        deleted_count, _ = OtnPath.objects.filter(id__in=ids_to_delete).delete()
                        self.log_success(f"成功删除了 {deleted_count} 条重复记录！")
                    
                    # 更新保留记录的描述字段
                    for path in paths_to_update:
                        path.description = "8800,9800"
                        path.save()
                    
                    self.log_success(f"成功更新了 {len(paths_to_update)} 条记录的描述为 '8800,9800'！")
                    
            except Exception as e:
                self.log_failure(f"操作失败: {str(e)}")
                raise
        
        return (
            f"检查完成。发现 {len(duplicate_groups)} 组重复，"
            f"涉及 {delete_count + kept_count} 条记录。"
            f"{'计划' if dry_run else '已'}删除 {delete_count} 条，"
            f"{'计划' if dry_run else '已'}更新 {kept_count} 条描述。"
        )
