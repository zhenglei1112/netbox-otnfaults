from netbox.plugins import PluginTemplateExtension
from .models import OtnPath, OtnFault
from django.http import HttpRequest
from django.utils.dateparse import parse_date
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


def build_contract_fault_context(request: HttpRequest, contract_id: int) -> dict[str, object]:
    """Build the related-fault table context for a contract."""
    faults_qs = (
        OtnFault.objects.restrict(request.user, 'view')
        .filter(contract_id=contract_id)
        .select_related('duty_officer')
        .prefetch_related('tags')
    )
    fault_start_date = parse_date(
        request.GET.get('fault_occurrence_time_after', '')
    )
    fault_end_date = parse_date(
        request.GET.get('fault_occurrence_time_before', '')
    )
    fault_tag_ids = [
        int(tag_id)
        for tag_id in request.GET.getlist('fault_tag')
        if tag_id.isdigit()
    ]
    if fault_start_date:
        faults_qs = faults_qs.filter(
            fault_occurrence_time__date__gte=fault_start_date
        )
    if fault_end_date:
        faults_qs = faults_qs.filter(
            fault_occurrence_time__date__lte=fault_end_date
        )
    if fault_tag_ids:
        faults_qs = faults_qs.filter(tags__pk__in=fault_tag_ids).distinct()

    faults_table = ContractOtnFaultTable(faults_qs)
    faults_table.prefix = 'faults_'

    return {
        'faults_table': faults_table,
        'fault_start_date': fault_start_date,
        'fault_end_date': fault_end_date,
        'fault_tag_ids': fault_tag_ids,
        'contract_id': contract_id,
    }


class ContractOtnFaults(PluginTemplateExtension):
    """在外购合同详情页注入关联故障列表。"""
    models = ['netbox_contract.contract']

    def right_page(self) -> str:
        obj = self.context['object']
        request = self.context['request']
        context = build_contract_fault_context(request, obj.pk)
        return self.render(
            'netbox_otnfaults/inc/contract_otn_faults.html',
            extra_context=context,
        )

template_extensions = [SiteOtnPaths, SiteOtnFaults, ContractOtnFaults]
