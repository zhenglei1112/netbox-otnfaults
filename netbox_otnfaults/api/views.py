from netbox.api.viewsets import NetBoxModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q
from datetime import timedelta
import json
import logging
from ..models import OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup, OtnPathGroupSite, BareFiberService, CircuitService
from .serializers import OtnFaultSerializer, OtnFaultImpactSerializer, OtnPathSerializer, OtnPathGroupSerializer, OtnPathGroupSiteSerializer, BareFiberServiceSerializer, CircuitServiceSerializer
from ..filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet, OtnPathFilterSet, OtnPathGroupFilterSet, BareFiberServiceFilterSet, CircuitServiceFilterSet
from dcim.models import Site
from dcim.api.serializers import SiteSerializer

logger = logging.getLogger(__name__)


def get_plugin_settings():
    """获取插件配置"""
    return settings.PLUGINS_CONFIG.get('netbox_otnfaults', {})


class OtnFaultViewSet(NetBoxModelViewSet):
    queryset = OtnFault.objects.all()
    serializer_class = OtnFaultSerializer
    filterset_class = OtnFaultFilterSet


class OtnFaultImpactViewSet(NetBoxModelViewSet):
    queryset = OtnFaultImpact.objects.all()
    serializer_class = OtnFaultImpactSerializer
    filterset_class = OtnFaultImpactFilterSet


class OtnPathViewSet(NetBoxModelViewSet):
    queryset = OtnPath.objects.all()
    serializer_class = OtnPathSerializer
    filterset_class = OtnPathFilterSet


class OtnPathGroupViewSet(NetBoxModelViewSet):
    """路径组 API ViewSet"""
    queryset = OtnPathGroup.objects.all()
    serializer_class = OtnPathGroupSerializer
    filterset_class = OtnPathGroupFilterSet



class OtnPathGroupSiteViewSet(NetBoxModelViewSet):
    """路径组站点关联 API ViewSet"""
    queryset = OtnPathGroupSite.objects.all()
    serializer_class = OtnPathGroupSiteSerializer


class BareFiberServiceViewSet(NetBoxModelViewSet):
    """裸纤业务 API ViewSet"""
    queryset = BareFiberService.objects.all()
    serializer_class = BareFiberServiceSerializer
    filterset_class = BareFiberServiceFilterSet


class CircuitServiceViewSet(NetBoxModelViewSet):
    """电路业务 API ViewSet"""
    queryset = CircuitService.objects.all()
    serializer_class = CircuitServiceSerializer
    filterset_class = CircuitServiceFilterSet

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def connected_sites_view(request):
    """
    Z端站点自定义查询接口
    如果传了 q，则全局搜索所有站点
    如果传了 connected_to_a 且没有 q，则只返回与 A 站点连通的站点
    """
    site_a_id = request.GET.get('connected_to_a')
    q = request.GET.get('q', '')
    
    queryset = Site.objects.all()
    
    if q:
        # 用户输入了内容，执行全局模糊搜索
        queryset = queryset.filter(Q(name__icontains=q) | Q(facility__icontains=q))
    elif site_a_id:
        # 用户只是点开了下拉列表，默认只展示连通的站点
        from ..models import OtnPath
        paths = OtnPath.objects.filter(Q(site_a_id=site_a_id) | Q(site_z_id=site_a_id))
        connected_site_ids = set()
        for p in paths:
            if p.site_a_id and str(p.site_a_id) != str(site_a_id):
                connected_site_ids.add(p.site_a_id)
            if p.site_z_id and str(p.site_z_id) != str(site_a_id):
                connected_site_ids.add(p.site_z_id)
        queryset = queryset.filter(id__in=connected_site_ids)
        
    queryset = queryset[:50]
    # 使用 Base Serializer 的 request context，Netbox 自动追加 display 字段供 Select2 使用
    serializer = SiteSerializer(queryset, many=True, context={'request': request})
    
    # 按照 Netbox 选择器所需的格式返回
    return Response({'results': serializer.data})


class HeatmapDataView(APIView):
    """热力图数据API视图（优化版）"""
    
    def get(self, request):
        try:
            # 获取时间范围参数（默认为'year'，即本年）
            time_range = request.GET.get('time_range', 'year')
            logger.info(f"热力图数据请求，时间范围: {time_range}")
            
            # 尝试从缓存获取
            cache_key = f'heatmap_data_{time_range}'
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"从缓存返回热力图数据，key: {cache_key}")
                return Response(cached_data)
            
            now = timezone.localtime()
            
            # 根据时间范围计算起始时间
            if time_range == 'month':
                start_date = now - timedelta(days=30)
            elif time_range == 'three_months':
                start_date = now - timedelta(days=90)
            elif time_range == 'year':
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                time_range = 'year'
            
            logger.info(f"计算起始时间: {start_date}")
            
            # 使用 .values() 优化查询，减少内存占用
            faults = OtnFault.objects.filter(
                interruption_longitude__isnull=False,
                interruption_latitude__isnull=False,
                fault_occurrence_time__gte=start_date
            ).values(
                'fault_number', 'fault_category',
                'interruption_longitude', 'interruption_latitude'
            )
            
            logger.info(f"查询到 {faults.count()} 条故障记录")
            
            # 使用列表推导式替代循环，更高效
            features = [
                {
                    'type': 'Feature',
                    'properties': {
                        'count': 1,
                        'fault_number': f['fault_number'],
                        'fault_category': f['fault_category'] or 'other'
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [
                            float(f['interruption_longitude']),
                            float(f['interruption_latitude'])
                        ]
                    }
                }
                for f in faults
                if f['interruption_longitude'] is not None and f['interruption_latitude'] is not None
            ]
            
            logger.info(f"成功构建 {len(features)} 个GeoJSON特征")
            
            response_data = {
                'type': 'FeatureCollection',
                'features': features,
                'time_range': time_range,
                'count': len(features)
            }
            
            # 缓存数据，使用插件配置的超时时间（默认 300 秒）
            plugin_settings = get_plugin_settings()
            cache_timeout = plugin_settings.get('heatmap_cache_timeout', 300)
            cache.set(cache_key, response_data, cache_timeout)
            logger.info(f"热力图数据已缓存，key: {cache_key}, timeout: {cache_timeout}s")
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"热力图数据API异常: {e}", exc_info=True)
            return Response(
                {'error': '服务器内部错误', 'detail': str(e)},
                status=500
            )


@method_decorator(csrf_exempt, name='dispatch')
class RouteSnapperView(APIView):
    """路径吸附计算 API"""
    # 内部工具，禁用权限和 CSRF 检查
    permission_classes = []
    authentication_classes = []
    
    def post(self, request):
        """
        计算沿高速公路的路径
        
        Request Body:
            {
                "waypoints": [
                    {"lng": 121.47, "lat": 31.23},
                    {"lng": 120.62, "lat": 31.30}
                ]
            }
            
        Response:
            {
                "success": true,
                "route": {
                    "geometry": {"type": "LineString", "coordinates": [...]},
                    "length_meters": 85230.5
                }
            }
        """
        try:
            from ..services.otn_path_graph import get_otn_path_graph_service
            
            # 解析请求
            waypoints = request.data.get('waypoints', [])
            
            if not waypoints or len(waypoints) < 2:
                return Response({
                    'success': False,
                    'error': '至少需要两个途经点'
                }, status=400)
            
            # 验证途经点格式
            for i, wp in enumerate(waypoints):
                if 'lng' not in wp or 'lat' not in wp:
                    return Response({
                        'success': False,
                        'error': f'途经点 {i} 缺少 lng 或 lat 字段'
                    }, status=400)
            
            # 获取服务并计算路径
            service = get_otn_path_graph_service()
            
            if not service.is_available():
                logger.warning('OTN 路径图服务不可用，返回直线路径')
                # 降级为直线连接
                return Response({
                    'success': True,
                    'route': {
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': [[wp['lng'], wp['lat']] for wp in waypoints]
                        },
                        'length_meters': self._calculate_straight_distance(waypoints)
                    },
                    'fallback': True,
                    'message': 'OTN 路径图服务不可用，使用直线连接'
                })
            
            result = service.calculate_route(waypoints)
            return Response(result)
            
        except Exception as e:
            logger.error(f'路径计算异常: {e}', exc_info=True)
            return Response({
                'success': False,
                'error': f'服务器错误: {str(e)}'
            }, status=500)
    
    def _calculate_straight_distance(self, waypoints):
        """计算直线距离（降级方案）"""
        import math
        
        total = 0
        R = 6371000
        
        for i in range(len(waypoints) - 1):
            lat1 = math.radians(waypoints[i]['lat'])
            lat2 = math.radians(waypoints[i+1]['lat'])
            dlat = math.radians(waypoints[i+1]['lat'] - waypoints[i]['lat'])
            dlng = math.radians(waypoints[i+1]['lng'] - waypoints[i]['lng'])
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            total += R * c
        
        return total


from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """禁用 CSRF 检查的 Session 认证类"""
    def enforce_csrf(self, request):
        return  # 跳过 CSRF 检查

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def path_group_batch_add(request, pk):
    """
    批量添加站点和路径到路径组
    
    POST /api/plugins/netbox_otnfaults/path-groups/{id}/batch-add/
    """
    from dcim.models import Site
    
    try:
        path_group = OtnPathGroup.objects.get(pk=pk)
    except OtnPathGroup.DoesNotExist:
        return Response({
            'success': False,
            'error': f'路径组 {pk} 不存在'
        }, status=404)
    
    site_ids = request.data.get('site_ids', [])
    path_ids = request.data.get('path_ids', [])
    
    added_sites = 0
    added_paths = 0
    skipped_sites = 0
    skipped_paths = 0
    
    # 批量添加站点
    for site_id in site_ids:
        try:
            site = Site.objects.get(pk=site_id)
            if not OtnPathGroupSite.objects.filter(path_group=path_group, site=site).exists():
                max_pos = OtnPathGroupSite.objects.filter(path_group=path_group).count()
                OtnPathGroupSite.objects.create(
                    path_group=path_group,
                    site=site,
                    role='ola',
                    position=max_pos + 1
                )
                added_sites += 1
            else:
                skipped_sites += 1
        except Site.DoesNotExist:
            logger.warning(f'站点 {site_id} 不存在，跳过')
    
    # 批量添加路径
    for path_id in path_ids:
        try:
            path = OtnPath.objects.get(pk=path_id)
            if path not in path_group.paths.all():
                path_group.paths.add(path)
                added_paths += 1
            else:
                skipped_paths += 1
        except OtnPath.DoesNotExist:
            logger.warning(f'路径 {path_id} 不存在，跳过')
    
    return Response({
        'success': True,
        'added_sites': added_sites,
        'added_paths': added_paths,
        'skipped_sites': skipped_sites,
        'skipped_paths': skipped_paths
    })


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def path_group_clear_paths(request, pk):
    """
    清除路径组中的所有路径
    
    POST /api/plugins/otnfaults/path-groups/{id}/clear-paths/
    """
    try:
        path_group = OtnPathGroup.objects.get(pk=pk)
    except OtnPathGroup.DoesNotExist:
        return Response({
            'success': False,
            'error': f'路径组 {pk} 不存在'
        }, status=404)
    
    count = path_group.paths.count()
    path_group.paths.clear()
    
    return Response({
        'success': True,
        'cleared_paths': count
    })


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def path_group_clear_sites(request, pk):
    """
    清除路径组中的所有站点
    
    POST /api/plugins/otnfaults/path-groups/{id}/clear-sites/
    """
    try:
        path_group = OtnPathGroup.objects.get(pk=pk)
    except OtnPathGroup.DoesNotExist:
        return Response({
            'success': False,
            'error': f'路径组 {pk} 不存在'
        }, status=404)
    
    count = OtnPathGroupSite.objects.filter(path_group=path_group).count()
    OtnPathGroupSite.objects.filter(path_group=path_group).delete()
    
    return Response({
        'success': True,
        'cleared_sites': count
    })
