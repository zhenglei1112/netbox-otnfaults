from extras.scripts import Script
from netbox_otnfaults.models import OtnFault, FaultCategoryChoices

class UpdateFaultTypesEnToZh(Script):
    class Meta:
        name = "故障分类中英文映射(数据清洗)"
        description = "将历史存在的英文故障分类(power, device, fiber, other, pigtail)转换为现有的中文枚举关键字。"
        commit_default = False

    def run(self, data, commit):
        mapping = {
            'power': FaultCategoryChoices.POWER_FAULT,
            'device': FaultCategoryChoices.DEVICE_FAULT,
            'fiber': FaultCategoryChoices.FIBER_BREAK,  # 默认归入光缆中断
            'pigtail': FaultCategoryChoices.AC_FAULT,   # 依据原有报表逻辑，pigtail对应空调
            'other': None,                              # 无对应分类，置空
        }
        
        faults_to_update = OtnFault.objects.filter(fault_category__in=mapping.keys())
        total_count = faults_to_update.count()
        
        self.log_info(f"找到 {total_count} 条需要更新分类的历史故障记录。")
        
        updated_count = 0
        for fault in faults_to_update:
            old_cat = fault.fault_category
            new_cat = mapping.get(old_cat)
            
            self.log_info(f"故障 {fault.fault_number} 分类转换：[{old_cat}] -> [{new_cat}]")
            
            fault.fault_category = new_cat
            if commit:
                try:
                    fault.save()
                    updated_count += 1
                except Exception as e:
                    self.log_failure(f"故障 {fault.fault_number} 保存失败: {str(e)}")
            else:
                updated_count += 1
                
        if commit:
            self.log_success(f"成功提交并更新 {updated_count} 条记录到数据库。")
        else:
            self.log_success(f"模拟运行完毕（未勾选Commit）。预览可更新 {updated_count} 条记录。")
