from netbox.views import generic
from django.shortcuts import render
from utilities.views import register_model_view
from .models import OtnFault, OtnFaultImpact, OtnPath, FaultCategoryChoices, FaultStatusChoices
from dcim.models import Site
from .forms import (
    OtnFaultForm, OtnFaultImpactForm, OtnFaultFilterForm, OtnFaultImpactFilterForm, 
    OtnFaultBulkEditForm, OtnFaultImpactBulkEditForm, OtnFaultImportForm, OtnFaultImpactImportForm,
    OtnPathForm, OtnPathFilterForm, OtnPathImportForm, OtnPathBulkEditForm
)
from .filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet, OtnPathFilterSet
from .tables import OtnFaultTable, OtnFaultImpactTable, OtnPathTable
from django.utils import timezone
from datetime import timedelta
from django.views.generic import View
from django.contrib.auth.mixins import PermissionRequiredMixin
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings


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

class OtnFaultGlobeMapView(PermissionRequiredMixin, View):
    """OTN故障分布图（地球模式）视图"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        # 获取时间范围参数（默认为'year'，即本年），仅用于设置按钮初始状态
        time_range = request.GET.get('time_range', 'year')
        
        now = timezone.now()
        
        # 计算本年度起始时间（1月1日）
        current_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_week_start = now - timedelta(days=7)

        # 获取本年度所有故障（不再限制必须有经纬度）
        all_faults = OtnFault.objects.filter(fault_occurrence_time__gte=current_year_start)
        
        # 热力图数据：只包含有真实经纬度的故障
        heatmap_faults = all_faults.exclude(
            interruption_longitude__isnull=True
        ).exclude(
            interruption_latitude__isnull=True
        )
        heatmap_data = []
        for fault in heatmap_faults:
            # 获取故障分类，转换为前端可识别的键
            fault_category = fault.fault_category
            category_key = 'other'  # 默认值
            
            # 将数据库中的分类值映射到前端可识别的键
            if fault_category:
                category_mapping = {
                    'power': 'power',      # 电力故障 -> power
                    'fiber': 'fiber',      # 光缆故障 -> fiber
                    'pigtail': 'pigtail',  # 空调故障 -> pigtail
                    'device': 'device',    # 设备故障 -> device
                    'other': 'other'       # 其他故障 -> other
                }
                
                category_key = category_mapping.get(fault_category, 'other')
            
            heatmap_data.append({
                'lat': float(fault.interruption_latitude),
                'lng': float(fault.interruption_longitude),
                'count': 1,  # 简单计数，也可以根据紧急程度加权
                'occurrence_time': fault.fault_occurrence_time.isoformat() if fault.fault_occurrence_time else None,
                'category': category_key  # 新增：故障分类
            })

        # 标记点数据：包含所有本年度故障，无经纬度时使用A端站点坐标
        marker_faults = all_faults.select_related(
            'province', 'interruption_location_a'
        ).prefetch_related(
            'interruption_location', 'images', 'impacts', 'impacts__impacted_service'
        )
        
        marker_data = []
        for fault in marker_faults:
            # 获取故障分类，转换为前端可识别的键
            fault_category = fault.fault_category
            category_key = 'other'  # 默认值
            
            # 将数据库中的分类值映射到前端可识别的键
            if fault_category:
                category_mapping = {
                    'power': 'power',      # 电力故障 -> power
                    'fiber': 'fiber',      # 光缆故障 -> fiber
                    'pigtail': 'pigtail',  # 空调故障 -> pigtail
                    'device': 'device',    # 设备故障 -> device
                    'other': 'other'       # 其他故障 -> other
                }
                
                category_key = category_mapping.get(fault_category, 'other')
            
            # 获取Z端站点名称列表（ManyToMany关系）
            z_sites = list(fault.interruption_location.all().values_list('name', flat=True))
            z_sites_str = '、'.join(z_sites) if z_sites else '未指定'

            # 获取影响业务（从 OtnFaultImpact 反向查询）
            impacted_businesses = [impact.impacted_service.name for impact in fault.impacts.all() if impact.impacted_service]
            impacted_business_str = '、'.join(impacted_businesses) if impacted_businesses else '无重保/影响业务'
            
            # 获取影响业务详情（包含业务名称和中断历时）
            impacts_details = []
            for impact in fault.impacts.all():
                if impact.impacted_service:
                    impacts_details.append({
                        'name': impact.impacted_service.name,
                        'duration_hours': impact.service_duration_hours  # 格式为 "xx.xx" 或 None
                    })
            
            # 格式化时间
            occurrence_time_str = fault.fault_occurrence_time.strftime('%Y-%m-%d %H:%M:%S') if fault.fault_occurrence_time else '未记录'
            recovery_time_str = fault.fault_recovery_time.strftime('%Y-%m-%d %H:%M:%S') if fault.fault_recovery_time else '未恢复'
            
            # 获取故障历时（使用模型的计算属性）
            fault_duration_str = fault.fault_duration if hasattr(fault, 'fault_duration') and fault.fault_duration else '无法计算'
            
            # 计算经纬度：优先使用故障自身的经纬度，否则使用A端站点的经纬度
            if fault.interruption_latitude is not None and fault.interruption_longitude is not None:
                lat = float(fault.interruption_latitude)
                lng = float(fault.interruption_longitude)
                coords_from_site = False
            elif fault.interruption_location_a and fault.interruption_location_a.latitude and fault.interruption_location_a.longitude:
                lat = float(fault.interruption_location_a.latitude)
                lng = float(fault.interruption_location_a.longitude)
                coords_from_site = True
            else:
                # 既无故障经纬度也无A端站点经纬度，跳过此故障
                continue
            
            marker_data.append({
                'lat': lat,
                'lng': lng,
                'coords_from_site': coords_from_site,  # 标记坐标是否来自站点
                'number': fault.fault_number,
                'url': fault.get_absolute_url(),
                'details': f"{fault.fault_number}: {fault.get_fault_category_display() or '未知类型'}",
                'category': category_key,  # 添加分类字段
                'category_display': fault.get_fault_category_display() or '未知类型', # 分类显示名

                # 新增字段：省份、A端站点、Z端站点
                'province': fault.province.name if fault.province else '未指定',
                'a_site': fault.interruption_location_a.name if fault.interruption_location_a else '未指定',
                'a_site_id': fault.interruption_location_a.pk if fault.interruption_location_a else None,
                'z_sites': z_sites_str,
                'z_site_ids': list(fault.interruption_location.all().values_list('pk', flat=True)),
                'impacted_business': impacted_business_str,
                'impacts_details': impacts_details,  # 包含业务名称和中断历时的详细列表
                
                # 新增字段：状态
                'status': fault.get_fault_status_display() or '未知状态',
                'status_key': fault.fault_status or 'processing',  # 状态键值，用于前端图标匹配
                'status_color': fault.get_fault_status_color(), # 也可以传颜色

                # 新增字段：时间信息
                'occurrence_time': occurrence_time_str,
                'recovery_time': recovery_time_str,
                'fault_duration': fault_duration_str,
                
                # 新增字段：故障原因
                'reason': fault.get_interruption_reason_display() or '-',

                # 新增字段：故障详情和处理过程
                'fault_details': fault.fault_details or '无详细描述',
                'process': fault.fault_details or '无处理过程', # 为了兼容前端请求的"处理过程"，暂用fault_details，如果未来有单独字段可分离

                # 新增字段：光缆故障特定信息
                'resource_type': fault.get_resource_type_display() or '-',
                'cable_route': fault.get_cable_route_display() or '-',
                'cable_break_location': fault.get_cable_break_location_display() or '-',
                'recovery_mode': fault.get_recovery_mode_display() or '-',
                'maintenance_mode': fault.get_maintenance_mode_display() or '-',
                'handling_unit': fault.handling_unit.name if fault.handling_unit else '-',
                'handler': fault.handler or '-',

                # 新增字段：照片信息
                'images': [{'name': img.name, 'url': img.image.url} for img in fault.images.all()] if hasattr(fault, 'images') else [],
                'has_images': fault.images.exists() if hasattr(fault, 'images') else False,
                'image_count': fault.images.count() if hasattr(fault, 'images') else 0
            })

        # 获取插件配置
        plugin_settings = get_plugin_settings()
        
        return render(request, 'netbox_otnfaults/otnfault_map_globe.html', {
            'heatmap_data': json.dumps(heatmap_data, cls=DjangoJSONEncoder),
            'marker_data': json.dumps(marker_data, cls=DjangoJSONEncoder),
            'sites_data': json.dumps([
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
                for site in Site.objects.filter(latitude__isnull=False, longitude__isnull=False)
            ], cls=DjangoJSONEncoder),
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(plugin_settings.get('map_default_center', [112.53, 33.00])),
            'map_zoom': plugin_settings.get('map_default_zoom', 4.2),
            'use_local_basemap': plugin_settings.get('use_local_basemap', False),
            'local_tiles_url': plugin_settings.get('local_tiles_url', ''),
            'local_glyphs_url': plugin_settings.get('local_glyphs_url', ''),
            'otn_paths_pmtiles_url': plugin_settings.get('otn_paths_pmtiles_url', ''), # 传递 OTN 路径 PMTiles URL
            'current_time_range': time_range,  # 传递给模板，用于显示当前选择
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
                    for key in ['orange', 'blue', 'yellow', 'green', 'gray', 'red', 'secondary']
                }
            }, cls=DjangoJSONEncoder)
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
    """光缆路径批量编辑视图"""
    queryset = OtnPath.objects.all()
    filterset = OtnPathFilterSet
    table = OtnPathTable
    form = OtnPathBulkEditForm


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
        
        # 解析 ?path_id=xxx 参数（用于路径高亮显示）
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
        
        # 获取所有有经纬度的站点
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
            for site in Site.objects.filter(latitude__isnull=False, longitude__isnull=False)
        ]

        # 获取插件配置
        plugin_settings = get_plugin_settings()
        
        # 确定地图中心和缩放级别
        if target_lat is not None and target_lng is not None:
            map_center = [target_lng, target_lat]
            map_zoom = 10 if highlight_path_data else 12  # 路径使用较小缩放
        else:
            map_center = plugin_settings.get('map_default_center', [112.53, 33.00])
            map_zoom = plugin_settings.get('map_default_zoom', 4.2)
        
        return render(request, 'netbox_otnfaults/location_map.html', {
            'sites_data': json.dumps(sites_data, cls=DjangoJSONEncoder),
            'target_lat': target_lat,
            'target_lng': target_lng,
            'highlight_path_data': json.dumps(highlight_path_data, cls=DjangoJSONEncoder) if highlight_path_data else 'null',
            'path_name': path_name,
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(map_center),
            'map_zoom': map_zoom,
            'use_local_basemap': plugin_settings.get('use_local_basemap', False),
            'local_tiles_url': plugin_settings.get('local_tiles_url', ''),
            'local_glyphs_url': plugin_settings.get('local_glyphs_url', ''),
            'otn_paths_pmtiles_url': plugin_settings.get('otn_paths_pmtiles_url', ''),
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
