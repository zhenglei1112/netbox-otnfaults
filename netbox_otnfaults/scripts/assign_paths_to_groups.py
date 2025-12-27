"""
NetBox自定义脚本：根据路径描述中的关键字批量分配路径组

功能：
1. 遍历所有 OtnPath 路径
2. 如果描述中包含 "8800"，将其加入"大网一期"路径组
3. 如果描述中包含 "9800"，将其加入"未来网络"路径组
4. 一条路径可以同时属于多个路径组

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.assign_paths_to_groups
2. 选择脚本类：AssignPathsToGroups
3. 运行脚本
"""

from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnPath, OtnPathGroup


class AssignPathsToGroups(Script):
    """
    根据路径描述中的关键字批量分配路径组
    """
    
    class Meta:
        name = "根据描述分配路径组"
        description = "根据路径描述中的关键字（8800/9800）批量分配路径到对应路径组"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际修改数据库（默认：True）",
        default=True
    )
    
    # 关键字与路径组映射
    KEYWORD_GROUP_MAP = {
        '8800': '大网一期',
        '9800': '未来网络',
    }
    
    def run(self, data, commit):
        """脚本主入口"""
        dry_run = data['dry_run']
        
        # 获取或验证路径组是否存在
        groups = {}
        for keyword, group_name in self.KEYWORD_GROUP_MAP.items():
            try:
                group = OtnPathGroup.objects.get(name=group_name)
                groups[keyword] = group
                self.log_info(f"找到路径组：{group_name} (ID: {group.pk})")
            except OtnPathGroup.DoesNotExist:
                self.log_failure(f"路径组 '{group_name}' 不存在，请先创建")
                return f"错误：路径组 '{group_name}' 不存在"
        
        # 获取所有路径
        all_paths = OtnPath.objects.all()
        total_paths = all_paths.count()
        self.log_info(f"共找到 {total_paths} 条路径")
        
        # 统计
        stats = {keyword: {'matched': 0, 'added': 0} for keyword in self.KEYWORD_GROUP_MAP}
        
        # 遍历所有路径
        for path in all_paths:
            description = path.description or ''
            
            for keyword, group in groups.items():
                if keyword in description:
                    stats[keyword]['matched'] += 1
                    
                    # 检查是否已在该组中
                    if path in group.paths.all():
                        self.log_info(f"路径 '{path.name}' 已在 '{group.name}' 中，跳过")
                        continue
                    
                    # 添加到路径组
                    if not dry_run and commit:
                        group.paths.add(path)
                        self.log_success(f"已将路径 '{path.name}' 添加到 '{group.name}'")
                    else:
                        self.log_info(f"[模拟] 将路径 '{path.name}' 添加到 '{group.name}'")
                    
                    stats[keyword]['added'] += 1
        
        # 汇总结果
        result = "处理完成！\n\n"
        for keyword, group_name in self.KEYWORD_GROUP_MAP.items():
            result += f"关键字 '{keyword}' -> 路径组 '{group_name}':\n"
            result += f"  • 匹配路径数: {stats[keyword]['matched']}\n"
            result += f"  • 新增关联数: {stats[keyword]['added']}\n\n"
        
        if dry_run or not commit:
            result += "⚠️ 当前为模拟模式，数据未实际保存。\n"
            result += "如需实际保存，请取消勾选'模拟运行'并勾选'提交更改'。"
        else:
            result += "✅ 数据已保存到数据库。"
        
        return result
