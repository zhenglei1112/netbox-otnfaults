from netbox.plugins import PluginTemplateExtension
from .models import OtnPath
from django.db.models import Q

class SiteOtnPaths(PluginTemplateExtension):
    """
    在站点详情页注入光缆路径统计信息。
    通过 right_page 方法在右侧面板显示。
    """
    model = 'dcim.site'
    
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

template_extensions = [SiteOtnPaths]
