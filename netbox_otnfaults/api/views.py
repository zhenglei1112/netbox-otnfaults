from netbox.api.viewsets import NetBoxModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta
import json
import logging
from ..models import OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup
from .serializers import OtnFaultSerializer, OtnFaultImpactSerializer, OtnPathSerializer, OtnPathGroupSerializer
from ..filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet, OtnPathFilterSet, OtnPathGroupFilterSet

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
            
            now = timezone.now()
            
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

