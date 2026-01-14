from netbox.views import generic
from django.shortcuts import render
from utilities.views import register_model_view, ViewTab
from django_tables2 import RequestConfig
from .models import OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup, FaultCategoryChoices, FaultStatusChoices
from dcim.models import Site
from .forms import (
    OtnFaultForm, OtnFaultImpactForm, OtnFaultFilterForm, OtnFaultImpactFilterForm, 
    OtnFaultBulkEditForm, OtnFaultImpactBulkEditForm, OtnFaultImportForm, OtnFaultImpactImportForm,
    OtnPathForm, OtnPathFilterForm, OtnPathImportForm, OtnPathBulkEditForm,
    OtnPathGroupForm, OtnPathGroupFilterForm
)
from .filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet, OtnPathFilterSet, OtnPathGroupFilterSet
from .tables import OtnFaultTable, OtnFaultImpactTable, OtnPathTable, OtnPathGroupTable
from django.utils import timezone
from datetime import timedelta
from django.views.generic import View
from django.contrib.auth.mixins import PermissionRequiredMixin
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.urls import reverse
from .map_modes import get_mode_config


def get_plugin_settings():
    """获取插件配置"""
    return settings.PLUGINS_CONFIG.get('netbox_otnfaults', {})

class OtnFaultListView(generic.ObjectListView):
    """OTN故障列表视图"""
    queryset = OtnFault.objects.all()
    table = OtnFaultTable
    filterset = OtnFaultFilterSet
    filterset_form = OtnFaultFilterForm
    template_name = 'netbox_otnfaults/otnfault_list.html'

class OtnFaultBulkImportView(generic.BulkImportView):
    """OTN故障批量导入视图"""
    queryset = OtnFault.objects.all()
    model = OtnFault
    model_form = OtnFaultImportForm
    table = OtnFaultTable

from django.http import JsonResponse

class OtnFaultMapDataView(PermissionRequiredMixin, View):
    """OTN故障地图数据视图 (Async API)"""
    permission_required = 'netbox_otnfaults.view_otnfault'
    
    def _get_hex_color(self, color_name):
        """Map standard NetBox/Bootstrap color names to Hex values."""
        COLOR_MAP = {
            'dark': '#343a40',
            'gray': '#6c757d',
            'light-gray': '#aaacae',
            'blue': '#0d6efd',
            'indigo': '#6610f2',
            'purple': '#6f42c1',
            'pink': '#d63384',
            'red': '#dc3545',
            'orange': '#f5a623', # Using the project's preferred orange
            'yellow': '#ffc107',
            'green': '#198754',
            'teal': '#20c997',
            'cyan': '#0dcaf0',
            'white': '#ffffff',
            'secondary': '#6c757d',
        }
        return COLOR_MAP.get(color_name, '#6c757d') # Default to gray
    
    def _get_sites_data(self):
        """获取站点数据 (所有地图模式共享)"""
        sites_data = [
            {
                'id': site.pk,
                'name': site.name,
                'latitude': float(site.latitude),
                'longitude': float(site.longitude),
                'url': site.get_absolute_url(),
                'status': site.get_status_display(),
                'status_color': site.get_status_color(),
                'tenant': site.tenant.name if site.tenant else None,
                'region': site.region.name if site.region else None,
                'group': site.group.name if site.group else None,
                'facility': site.facility,
                'description': site.description
            }
            for site in Site.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related('tenant', 'region', 'group')
        ]
        return sites_data

    def get(self, request):
        # 检查请求模式
        mode = request.GET.get('mode', 'fault')
        
        # 获取站点数据 (所有模式都需要)
        sites_data = self._get_sites_data()
        
        # 根据模式返回不同数据
        if mode != 'fault':
            # 路径、路径组、位置模式只需要站点数据
            return JsonResponse({
                'sites_data': sites_data
            })
        
        # 故障模式需要额外的热力图和标记点数据
        now = timezone.now()
        # 改为最近12个月，避免跨年时数据为空
        twelve_months_ago = now - timedelta(days=365)
        
        # 获取最近12个月的所有故障
        all_faults = OtnFault.objects.filter(fault_occurrence_time__gte=twelve_months_ago)
        
        # 热力图数据
        heatmap_faults = all_faults.exclude(
            interruption_longitude__isnull=True
        ).exclude(
            interruption_latitude__isnull=True
        )
        heatmap_data = []
        for fault in heatmap_faults:
            fault_category = fault.fault_category
            category_key = 'other'
            if fault_category:
                category_mapping = {
                    'power': 'power', 'fiber': 'fiber', 'pigtail': 'pigtail', 
                    'device': 'device', 'other': 'other'
                }
                category_key = category_mapping.get(fault_category, 'other')
            
            heatmap_data.append({
                'lat': float(fault.interruption_latitude),
                'lng': float(fault.interruption_longitude),
                'count': 1,
                'occurrence_time': fault.fault_occurrence_time.isoformat() if fault.fault_occurrence_time else None,
                'category': category_key
            })

        # 标记点数据
        marker_faults = all_faults.select_related(
            'province', 'interruption_location_a', 'handling_unit'
        ).prefetch_related(
            'interruption_location', 'images', 'impacts', 'impacts__impacted_service'
        )
        
        marker_data = []
        for fault in marker_faults:
            fault_category = fault.fault_category
            category_key = 'other'
            if fault_category:
                category_mapping = {
                    'power': 'power', 'fiber': 'fiber', 'pigtail': 'pigtail',
                    'device': 'device', 'other': 'other'
                }
                category_key = category_mapping.get(fault_category, 'other')
            
            z_sites = [s.name for s in fault.interruption_location.all()]
            z_sites_str = '、'.join(z_sites) if z_sites else '未指定'

            impacted_businesses = [impact.impacted_service.name for impact in fault.impacts.all() if impact.impacted_service]
            impacted_business_str = '、'.join(impacted_businesses) if impacted_businesses else '无重保/影响业务'
            
            impacts_details = []
            for impact in fault.impacts.all():
                if impact.impacted_service:
                    impacts_details.append({
                        'name': impact.impacted_service.name,
                        'duration_hours': impact.service_duration_hours
                    })
            
            # 简化逻辑：直接获取属性
            occurrence_time_str = fault.fault_occurrence_time.strftime('%Y-%m-%d %H:%M:%S') if fault.fault_occurrence_time else '未记录'
            recovery_time_str = fault.fault_recovery_time.strftime('%Y-%m-%d %H:%M:%S') if fault.fault_recovery_time else '未恢复'
            fault_duration_str = fault.fault_duration if hasattr(fault, 'fault_duration') and fault.fault_duration else '无法计算'

            if fault.interruption_latitude is not None and fault.interruption_longitude is not None:
                lat = float(fault.interruption_latitude)
                lng = float(fault.interruption_longitude)
                coords_from_site = False
            elif fault.interruption_location_a and fault.interruption_location_a.latitude and fault.interruption_location_a.longitude:
                lat = float(fault.interruption_location_a.latitude)
                lng = float(fault.interruption_location_a.longitude)
                coords_from_site = True
            else:
                continue
            
            marker_data.append({
                'lat': lat,
                'lng': lng,
                'coords_from_site': coords_from_site,
                'number': fault.fault_number,
                'url': fault.get_absolute_url(),
                'details': f"{fault.fault_number}: {fault.get_fault_category_display() or '未知类型'}",
                'category': category_key,
                'category_display': fault.get_fault_category_display() or '未知类型',
                'province': fault.province.name if fault.province else '未指定',
                'a_site': fault.interruption_location_a.name if fault.interruption_location_a else '未指定',
                'a_site_id': fault.interruption_location_a.pk if fault.interruption_location_a else None,
                'z_sites': z_sites_str,
                'z_site_ids': [s.pk for s in fault.interruption_location.all()],
                'impacted_business': impacted_business_str,
                'impacts_details': impacts_details,
                'status': fault.get_fault_status_display() or '未知状态',
                'status_key': fault.fault_status or 'processing',
                'status_color': fault.get_fault_status_color(),
                'occurrence_time': occurrence_time_str,
                'recovery_time': recovery_time_str,
                'fault_duration': fault_duration_str,
                'reason': fault.get_interruption_reason_display() or '-',
                'fault_details': fault.fault_details or '无详细描述',
                'process': fault.fault_details or '无处理过程',
                'resource_type': fault.get_resource_type_display() or '-',
                'cable_route': fault.get_cable_route_display() or '-',
                'cable_break_location': fault.get_cable_break_location_display() or '-',
                'recovery_mode': fault.get_recovery_mode_display() or '-',
                'maintenance_mode': fault.get_maintenance_mode_display() or '-',
                'handling_unit': fault.handling_unit.name if fault.handling_unit else '-',
                'handler': fault.handler or '-',
                'images': [{'name': img.name, 'url': img.image.url} for img in fault.images.all()] if hasattr(fault, 'images') else [],
                'has_images': fault.images.exists() if hasattr(fault, 'images') else False,
                'image_count': fault.images.count() if hasattr(fault, 'images') else 0
            })

        # 站点数据已在方法开始时获取
        # 返回故障模式的完整数据
        return JsonResponse({
            'sites_data': sites_data,
            'heatmap_data': heatmap_data,
            'marker_data': marker_data
        })


class OtnFaultGlobeMapView(PermissionRequiredMixin, View):
    """OTN故障分布图（地球模式）视图"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        # 获取插件配置
        plugin_settings = get_plugin_settings()
        
        # 获取模式配置
        mode_config = get_mode_config('fault')
        
        # 构建 header_actions 的实际 URL
        for action in mode_config.get('header_actions', []):
            action['url'] = reverse(action['url_name'])
        
        return render(request, 'netbox_otnfaults/unified_map.html', {
            # 模式配置
            'map_mode': 'fault',
            'mode_config': mode_config,
            'header_info': None,
            'layers_config': json.dumps(mode_config.get('layers', {})),
            'projection': mode_config.get('projection', 'mercator'),
            
            # 基础配置 (API Key, Center, etc.)
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(plugin_settings.get('map_default_center', [112.53, 33.00])),
            'map_zoom': plugin_settings.get('map_default_zoom', 4.2),
            'use_local_basemap': plugin_settings.get('use_local_basemap', False),
            'local_tiles_url': plugin_settings.get('local_tiles_url', ''),
            'local_glyphs_url': plugin_settings.get('local_glyphs_url', ''),
            'otn_paths_pmtiles_url': plugin_settings.get('otn_paths_pmtiles_url', ''),
            
            # 动态数据 URL
            'map_data_url': reverse('plugins:netbox_otnfaults:otnfault_map_data'),

            # 辅助数据
            'fault_list_url': reverse('plugins:netbox_otnfaults:otnfault_list'),
            'colors_config': json.dumps({
                'category_colors': {
                    val: self._get_hex_color(color)
                    for val, label, color in FaultCategoryChoices.CHOICES
                },
                'category_names': {val: label for val, label, color in FaultCategoryChoices.CHOICES},
                'status_colors': {
                    val: self._get_hex_color(color)
                    for val, label, color in FaultStatusChoices.CHOICES
                },
                'status_names': {val: label for val, label, color in FaultStatusChoices.CHOICES},
                'popup_status_colors': {
                    key: self._get_hex_color(key) 
                    for key in ['orange', 'blue', 'yellow', 'green', 'gray', 'red', 'secondary', 'purple']
                }
            }, cls=DjangoJSONEncoder),

            # 调试模式参数
            'debug_mode': True,
            'show_debug_panel': False,
            'debug_date': '2025-12-05 00:00:00',
        })

    def _get_hex_color(self, color_name):
        """Map standard NetBox/Bootstrap color names to Hex values."""
        COLOR_MAP = {
            'dark': '#343a40',
            'gray': '#6c757d',
            'light-gray': '#aaacae',
            'blue': '#0d6efd',
            'indigo': '#6610f2',
            'purple': '#6f42c1',
            'pink': '#d63384',
            'red': '#dc3545',
            'orange': '#f5a623', # Using the project's preferred orange
            'yellow': '#ffc107',
            'green': '#198754',
            'teal': '#20c997',
            'cyan': '#0dcaf0',
            'white': '#ffffff',
            'secondary': '#6c757d',
        }
        return COLOR_MAP.get(color_name, '#6c757d') # Default to gray


@register_model_view(OtnFault)
class OtnFaultView(generic.ObjectView):
    """OTN故障详情视图"""
    queryset = OtnFault.objects.all()

    def get_extra_context(self, request, instance):
        table = OtnFaultImpactTable(instance.impacts.all())
        table.configure(request)
        return {
            'impacts_table': table,
        }

class OtnFaultEditView(generic.ObjectEditView):
    """OTN故障编辑视图"""
    queryset = OtnFault.objects.all()
    form = OtnFaultForm
    template_name = 'netbox_otnfaults/otnfault_edit.html'

    def get(self, request, *args, **kwargs):
        """
        GET request handler
            Overrides the ObjectEditView function to include form initialization
            with default duty officer as current user

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        obj = self.alter_object(obj, request, args, kwargs)
        model = self.queryset.model

        initial_data = {}
        # 如果是创建新记录，设置默认值守人员为当前登录用户
        if not obj.pk and request.user.is_authenticated:
            initial_data['duty_officer'] = request.user

        form = self.form(instance=obj, initial=initial_data)

        return render(
            request,
            self.template_name,
            {
                'model': model,
                'object': obj,
                'form': form,
                'return_url': self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )

class OtnFaultDeleteView(generic.ObjectDeleteView):
    """OTN故障删除视图"""
    queryset = OtnFault.objects.all()

class OtnFaultBulkDeleteView(generic.BulkDeleteView):
    """OTN故障批量删除视图"""
    queryset = OtnFault.objects.all()
    table = OtnFaultTable

# 使用装饰器注册批量编辑视图
# path='edit' 告诉 NetBox 这是批量编辑视图
# detail=False 表示这不是针对单个对象的视图
@register_model_view(OtnFault, 'bulk_edit', path='edit', detail=False)
class OtnFaultBulkEditView(generic.BulkEditView):
    """OTN故障批量编辑视图"""
    queryset = OtnFault.objects.all()
    filterset = OtnFaultFilterSet
    table = OtnFaultTable
    form = OtnFaultBulkEditForm
    
    def get_required_permission(self):
        return 'netbox_otnfaults.change_otnfault'
    
    def get_object(self, **kwargs):
        """批量编辑不需要单个对象，返回 None"""
        return None
    
    def get_return_url(self, request, obj=None):
        """返回故障列表页的 URL"""
        from django.urls import reverse
        return reverse('plugins:netbox_otnfaults:otnfault_list')

class OtnFaultImpactListView(generic.ObjectListView):
    """故障影响业务列表视图"""
    queryset = OtnFaultImpact.objects.all()
    table = OtnFaultImpactTable
    filterset = OtnFaultImpactFilterSet
    filterset_form = OtnFaultImpactFilterForm

class OtnFaultImpactBulkImportView(generic.BulkImportView):
    """故障影响业务批量导入视图"""
    queryset = OtnFaultImpact.objects.all()
    model = OtnFaultImpact
    model_form = OtnFaultImpactImportForm
    table = OtnFaultImpactTable

@register_model_view(OtnFaultImpact)
class OtnFaultImpactView(generic.ObjectView):
    """故障影响业务详情视图"""
    queryset = OtnFaultImpact.objects.all()

class OtnFaultImpactEditView(generic.ObjectEditView):
    """故障影响业务编辑视图"""
    queryset = OtnFaultImpact.objects.all()
    form = OtnFaultImpactForm

    def get_return_url(self, request, obj=None):
        # 首先尝试从对象获取故障信息
        if obj and hasattr(obj, 'otn_fault') and obj.otn_fault:
            return obj.otn_fault.get_absolute_url()
            
        # 如果是创建新对象，检查查询参数
        otn_fault_id = request.GET.get('otn_fault')
        if otn_fault_id:
            try:
                return OtnFault.objects.get(pk=otn_fault_id).get_absolute_url()
            except OtnFault.DoesNotExist:
                pass
                
        return super().get_return_url(request, obj)

    def get(self, request, *args, **kwargs):
        """
        GET request handler
            Overrides the ObjectEditView function to include form initialization
            with data from the parent fault object

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        obj = self.alter_object(obj, request, args, kwargs)
        model = self.queryset.model

        # 从URL参数获取初始数据
        initial_data = {}
        otn_fault_id = request.GET.get('otn_fault')
        if otn_fault_id:
            try:
                fault = OtnFault.objects.get(pk=otn_fault_id)
                initial_data['otn_fault'] = otn_fault_id
                
                # 设置时间字段的默认值
                if fault.fault_occurrence_time:
                    initial_data['service_interruption_time'] = fault.fault_occurrence_time
                if fault.fault_recovery_time:
                    initial_data['service_recovery_time'] = fault.fault_recovery_time
                    
            except (OtnFault.DoesNotExist, ValueError):
                pass

        form = self.form(instance=obj, initial=initial_data)

        return render(
            request,
            self.template_name,
            {
                'model': model,
                'object': obj,
                'form': form,
                'return_url': self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 302:
            if '_addanother' in request.POST:
                otn_fault_id = request.POST.get('otn_fault')
                if otn_fault_id:
                    location = response['Location']
                    delimiter = '&' if '?' in location else '?'
                    response['Location'] = f"{location}{delimiter}otn_fault={otn_fault_id}"
            else:
                # 如果不是添加另一个，重定向到父故障对象（如果存在）
                if hasattr(self, 'object') and hasattr(self.object, 'otn_fault') and self.object.otn_fault:
                    response['Location'] = self.object.otn_fault.get_absolute_url()
                
        return response

class OtnFaultImpactBulkDeleteView(generic.BulkDeleteView):
    """故障影响业务批量删除视图"""
    queryset = OtnFaultImpact.objects.all()
    table = OtnFaultImpactTable

@register_model_view(OtnFaultImpact, 'bulk_edit', path='edit', detail=False)
class OtnFaultImpactBulkEditView(generic.BulkEditView):
    """故障影响业务批量编辑视图"""
    queryset = OtnFaultImpact.objects.all()
    filterset = OtnFaultImpactFilterSet
    table = OtnFaultImpactTable
    form = OtnFaultImpactBulkEditForm
    
    def get_required_permission(self):
        return 'netbox_otnfaults.change_otnfaultimpact'
    
    def get_object(self, **kwargs):
        return None
    
    def get_return_url(self, request, obj=None):
        from django.urls import reverse
        return reverse('plugins:netbox_otnfaults:otnfaultimpact_list')

class OtnFaultImpactDeleteView(generic.ObjectDeleteView):
    """故障影响业务删除视图"""
    queryset = OtnFaultImpact.objects.all()

class OtnPathListView(generic.ObjectListView):
    """光缆路径列表视图"""
    queryset = OtnPath.objects.all()
    table = OtnPathTable
    filterset = OtnPathFilterSet
    filterset_form = OtnPathFilterForm

@register_model_view(OtnPath)
class OtnPathView(generic.ObjectView):
    """光缆路径详情视图"""
    queryset = OtnPath.objects.all()

class OtnPathEditView(generic.ObjectEditView):
    """光缆路径编辑视图"""
    queryset = OtnPath.objects.all()
    form = OtnPathForm

class OtnPathDeleteView(generic.ObjectDeleteView):
    """光缆路径删除视图"""
    queryset = OtnPath.objects.all()

class OtnPathBulkImportView(generic.BulkImportView):
    """光缆路径批量导入视图"""
    queryset = OtnPath.objects.all()
    model = OtnPath
    model_form = OtnPathImportForm
    table = OtnPathTable

class OtnPathBulkDeleteView(generic.BulkDeleteView):
    """光缆路径批量删除视图"""
    queryset = OtnPath.objects.all()
    table = OtnPathTable

@register_model_view(OtnPath, 'bulk_edit', path='edit', detail=False)
class OtnPathBulkEditView(generic.BulkEditView):
    """光缆路径批量编辑视图 - 支持路径组的批量添加/移除"""
    queryset = OtnPath.objects.all()
    filterset = OtnPathFilterSet
    table = OtnPathTable
    form = OtnPathBulkEditForm

    def post_save_operations(self, form, obj):
        """在对象保存后处理多对多关系的批量添加/移除"""
        # 处理添加到路径组
        add_groups = form.cleaned_data.get('add_groups')
        if add_groups:
            for group in add_groups:
                group.paths.add(obj)

        # 处理从路径组移除
        remove_groups = form.cleaned_data.get('remove_groups')
        if remove_groups:
            for group in remove_groups:
                group.paths.remove(obj)


# ========== 路径组视图 ==========

class OtnPathGroupListView(generic.ObjectListView):
    """路径组列表视图"""
    queryset = OtnPathGroup.objects.all()
    table = OtnPathGroupTable
    filterset = OtnPathGroupFilterSet
    filterset_form = OtnPathGroupFilterForm


@register_model_view(OtnPathGroup)
class OtnPathGroupView(generic.ObjectView):
    """路径组详情视图"""
    queryset = OtnPathGroup.objects.all()

    def get_extra_context(self, request, instance):
        # 显示该路径组下的所有路径（只读模式，不显示操作按钮）
        paths_table = OtnPathTable(instance.paths.all())
        # 排除复选框和操作按钮列，使表格只读
        paths_table.columns.hide('pk')
        paths_table.columns.hide('actions')
        
        # 获取每页数量，默认25
        per_page = request.GET.get('per_page', 25)
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 25
        
        # 配置分页
        RequestConfig(request, paginate={'per_page': per_page}).configure(paths_table)
        
        return {
            'paths_table': paths_table,
            'per_page': per_page,
        }


class OtnPathGroupEditView(generic.ObjectEditView):
    """路径组编辑视图"""
    queryset = OtnPathGroup.objects.all()
    form = OtnPathGroupForm


class OtnPathGroupDeleteView(generic.ObjectDeleteView):
    """路径组删除视图"""
    queryset = OtnPathGroup.objects.all()


class OtnPathGroupBulkDeleteView(generic.BulkDeleteView):
    """路径组批量删除视图"""
    queryset = OtnPathGroup.objects.all()
    table = OtnPathGroupTable


class LocationMapView(PermissionRequiredMixin, View):
    """位置地图视图 - 接受 ?q=lat,lng 参数在地图上显示指定位置
    
    用于替代外部地图链接（如 Apple Maps），在系统内部展示站点、故障等位置。
    支持网络版底图和本地底图两种模式。
    """
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        # 解析 ?q=lat,lng 参数
        q = request.GET.get('q', '')
        target_lat, target_lng = self._parse_coordinates(q)
        
        # 解析 ?path_id=xxx 参数（用于单条路径高亮显示）
        path_id = request.GET.get('path_id', '')
        highlight_path_data = None
        path_name = None
        
        if path_id:
            try:
                path = OtnPath.objects.get(pk=int(path_id))
                path_name = path.name
                if path.geometry:
                    # 检查 geometry 是纯坐标数组还是 GeoJSON 对象
                    geom = path.geometry
                    if isinstance(geom, list):
                        # 纯坐标数组格式，转换为 GeoJSON
                        coords = geom
                        geometry_obj = {
                            'type': 'LineString',
                            'coordinates': coords
                        }
                    else:
                        # GeoJSON 格式
                        geometry_obj = geom
                        coords = geom.get('coordinates', [])
                    
                    # 构建 GeoJSON Feature
                    highlight_path_data = {
                        'type': 'Feature',
                        'properties': {
                            'id': path.pk,
                            'name': path.name,
                            'url': path.get_absolute_url()
                        },
                        'geometry': geometry_obj
                    }
                    # 计算路径中心用于自动缩放
                    if coords:
                        lngs = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                        center_lng = sum(lngs) / len(lngs)
                        center_lat = sum(lats) / len(lats)
                        target_lat, target_lng = center_lat, center_lng
            except (OtnPath.DoesNotExist, ValueError):
                pass
        
        # 解析 ?path_group_id=xxx 参数（用于路径组下所有路径高亮显示）
        path_group_id = request.GET.get('path_group_id', '')
        highlight_paths_data = None
        path_group_name = None
        
        if path_group_id:
            try:
                path_group = OtnPathGroup.objects.get(pk=int(path_group_id))
                path_group_name = path_group.name
                # 优化查询：只获取必要的 geometry 字段，避免加载过多无关字段
                # 注意：geometry 是必须的，但我们可以尝试优化查询方式
                paths_with_geom = path_group.paths.exclude(geometry__isnull=True).exclude(geometry=[])
                
                if paths_with_geom.exists():
                    features = []
                    all_lngs = []
                    all_lats = []
                    
                    for path in paths_with_geom:
                        geom = path.geometry
                        if isinstance(geom, list):
                            coords = geom
                            geometry_obj = {'type': 'LineString', 'coordinates': coords}
                        else:
                            geometry_obj = geom
                            coords = geom.get('coordinates', [])
                        
                        features.append({
                            'type': 'Feature',
                            'properties': {
                                'id': path.pk,
                                'name': path.name,
                                'url': path.get_absolute_url()
                            },
                            'geometry': geometry_obj
                        })
                        
                        # 收集所有坐标用于计算边界
                        for c in coords:
                            all_lngs.append(c[0])
                            all_lats.append(c[1])
                    
                    highlight_paths_data = {
                        'type': 'FeatureCollection',
                        'features': features
                    }
                    
                    # 计算所有路径的中心
                    if all_lngs and all_lats:
                        center_lng = (min(all_lngs) + max(all_lngs)) / 2
                        center_lat = (min(all_lats) + max(all_lats)) / 2
                        target_lat, target_lng = center_lat, center_lng
                    
                    path_name = f"路径组: {path_group_name} ({len(features)} 条路径)"
                    # 使用 FeatureCollection 作为高亮数据
                    highlight_path_data = highlight_paths_data
            except (OtnPathGroup.DoesNotExist, ValueError):
                pass
        
        # 获取插件配置
        plugin_settings = get_plugin_settings()
        
        # 确定地图中心和缩放级别
        if target_lat is not None and target_lng is not None:
            map_center = [target_lng, target_lat]
            map_zoom = 10 if highlight_path_data else 12  # 路径使用较小缩放
        else:
            map_center = plugin_settings.get('map_default_center', [112.53, 33.00])
            map_zoom = plugin_settings.get('map_default_zoom', 4.2)
        
        # 根据参数确定子模式
        if path_group_id:
            map_mode = 'pathgroup'
        elif path_id:
            map_mode = 'path'
        else:
            map_mode = 'location'
        
        # 获取模式配置
        mode_context = {
            'path_name': path_name,
            'group_name': path_group_name,
            'path_count': len(highlight_paths_data.get('features', [])) if highlight_paths_data else 0
        }
        mode_config = get_mode_config(map_mode, mode_context)
        
        # 确定 header_info 和返回链接
        header_info = mode_config.get('header_info')
        return_url = None
        return_label = None

        if map_mode == 'path' and path_name:
            header_info = path_name
            # 构建返回链接
            if path_id:
                try:
                    p = OtnPath.objects.get(pk=int(path_id))
                    return_url = p.get_absolute_url()
                    return_label = "返回路径详情"
                except:
                    pass
        elif map_mode == 'pathgroup' and path_group_name:
            header_info = f"路径组: {path_group_name} ({len(highlight_paths_data.get('features', []))} 条路径)" if highlight_paths_data else None
             # 构建返回链接
            if path_group_id:
                try:
                    pg = OtnPathGroup.objects.get(pk=int(path_group_id))
                    return_url = pg.get_absolute_url()
                    return_label = "返回路径组详情"
                except:
                    pass
        
        # 构建地图数据 API URL
        map_data_url = self._build_map_data_url(request, map_mode, path_id, path_group_id)
        
        return render(request, 'netbox_otnfaults/unified_map.html', {
            # 模式配置
            'map_mode': map_mode,
            'mode_config': mode_config,
            'header_info': header_info,
            'return_url': return_url,
            'return_label': return_label,
            'layers_config': json.dumps(mode_config.get('layers', {})),
            'projection': mode_config.get('projection', 'mercator'),
            
            # 共享数据 - 通过 API 动态加载
            'map_data_url': map_data_url,
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(map_center),
            'map_zoom': map_zoom,
            'use_local_basemap': plugin_settings.get('use_local_basemap', False),
            'local_tiles_url': plugin_settings.get('local_tiles_url', ''),
            'local_glyphs_url': plugin_settings.get('local_glyphs_url', ''),
            'otn_paths_pmtiles_url': plugin_settings.get('otn_paths_pmtiles_url', ''),
            
            # 位置/路径模式特定数据
            'target_lat': target_lat,
            'target_lng': target_lng,
            'highlight_path_data': json.dumps(highlight_path_data, cls=DjangoJSONEncoder) if highlight_path_data else 'null',
            'path_name': path_name,
        })

    def _parse_coordinates(self, q_param):
        """解析坐标参数 (格式: lat,lng)
        
        Args:
            q_param: 查询参数字符串，如 "26.461652,106.980645"
            
        Returns:
            (lat, lng) 元组，解析失败则返回 (None, None)
        """
        if not q_param:
            return None, None
        
        try:
            parts = q_param.split(',')
            if len(parts) >= 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                # 验证坐标范围
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
        except (ValueError, IndexError):
            pass
        
        return None, None
    
    def _build_map_data_url(self, request, mode, path_id=None, path_group_id=None):
        """构建地图数据 API URL
        
        Args:
            request: Django request 对象
            mode: 地图模式 ('path', 'pathgroup', 'location')
            path_id: 路径 ID (可选)
            path_group_id: 路径组 ID (可选)
            
        Returns:
            str: 完整的 API URL 带查询参数
        """
        from urllib.parse import urlencode
        
        base_url = reverse('plugins:netbox_otnfaults:otnfault_map_data')
        params = {'mode': mode}
        
        if path_id:
            params['path_id'] = path_id
        if path_group_id:
            params['path_group_id'] = path_group_id
        
        return f"{base_url}?{urlencode(params)}"


class RouteEditorView(PermissionRequiredMixin, View):
    """OTN线路设计器视图"""
    permission_required = 'netbox_otnfaults.view_otnpath'

    def get(self, request):
        plugin_settings = get_plugin_settings()
        mode_config = get_mode_config('route_editor')
        
        return render(request, 'netbox_otnfaults/unified_map.html', {
            # 模式配置
            'map_mode': 'route_editor',
            'mode_config': mode_config,
            'header_info': 'OTN线路设计器',
            'layers_config': json.dumps(mode_config.get('layers', {})),
            'projection': mode_config.get('projection', 'mercator'),
            
            # 基础配置
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(plugin_settings.get('map_default_center', [112.53, 33.00])),
            'map_zoom': plugin_settings.get('map_default_zoom', 4.2),
            'use_local_basemap': plugin_settings.get('use_local_basemap', False),
            'local_tiles_url': plugin_settings.get('local_tiles_url', ''),
            'local_glyphs_url': plugin_settings.get('local_glyphs_url', ''),
            'otn_paths_pmtiles_url': plugin_settings.get('otn_paths_pmtiles_url', ''),
            
            # 数据 API
            'map_data_url': reverse('plugins:netbox_otnfaults:otnfault_map_data') + '?mode=route_editor',
        })

