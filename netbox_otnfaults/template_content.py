from netbox.plugins import PluginTemplateExtension
from .models import OtnPath, OtnFault
from django.db.models import Q
from .tables import OtnFaultTable, ContractOtnFaultTable
from django_tables2.config import RequestConfig

class SiteOtnPaths(PluginTemplateExtension):
    """
    在站点详情页注入光缆路径统计信息。
    通过 right_page 方法在右侧面板显示。
    """
    models = ['dcim.site']  # NetBox 4.x: 使用 models (复数) 而非 model
    
    def right_page(self):
        obj = self.context['object']
        
        # 使用 Q 对象查询关联的光缆路径（A端或Z端）
        paths_count = OtnPath.objects.filter(
            Q(site_a=obj) | Q(site_z=obj)
        ).count()
        
        return self.render('netbox_otnfaults/inc/site_otn_paths.html', extra_context={
            'paths_count': paths_count,
            'site_id': obj.pk,
        })

class SiteOtnFaults(PluginTemplateExtension):
    """
    在站点详情页注入故障统计信息。
    """
    models = ['dcim.site']  # NetBox 4.x: 使用 models (复数) 而非 model
    
    def right_page(self):
        obj = self.context['object']
        
        # 统计涉及该站点的故障数量 (A端或Z端)
        faults_count = OtnFault.objects.filter(
            Q(interruption_location_a=obj) | 
            Q(interruption_location=obj)
        ).distinct().count()
        
        return self.render('netbox_otnfaults/inc/site_otn_faults.html', extra_context={
            'faults_count': faults_count,
            'site_id': obj.pk,
        })


class ContractOtnFaults(PluginTemplateExtension):
    """
    在外购合同详情页注入关联的故障列表。
    通过 right_page 方法在右侧面板显示。
    """
    models = ['netbox_contract.contract']
    
    def right_page(self):
        obj = self.context['object']
        request = self.context['request']
        
        # 获取关联该合同的故障
        faults_qs = OtnFault.objects.filter(contract=obj).prefetch_related(
            'interruption_location_a', 'interruption_location', 'tags'
        )
        faults_count = faults_qs.count()
        
        # 实例化表格
        faults_table = ContractOtnFaultTable(faults_qs)
        
        # 为表格指定前缀以区分参数冲突（虽然现在不分页了，但保留前缀是好习惯）
        faults_table.prefix = 'faults_'
        
        return self.render('netbox_otnfaults/inc/contract_otn_faults.html', extra_context={
            'faults_table': faults_table,
            'faults_count': faults_count,
            'contract_id': obj.pk,
        })

template_extensions = [SiteOtnPaths, SiteOtnFaults, ContractOtnFaults]
