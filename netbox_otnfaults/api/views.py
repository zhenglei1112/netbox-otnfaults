from netbox.api.viewsets import NetBoxModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import json
from ..models import OtnFault, OtnFaultImpact
from .serializers import OtnFaultSerializer, OtnFaultImpactSerializer
from ..filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet

class OtnFaultViewSet(NetBoxModelViewSet):
    queryset = OtnFault.objects.all()
    serializer_class = OtnFaultSerializer
    filterset_class = OtnFaultFilterSet

class OtnFaultImpactViewSet(NetBoxModelViewSet):
    queryset = OtnFaultImpact.objects.all()
    serializer_class = OtnFaultImpactSerializer
    filterset_class = OtnFaultImpactFilterSet

import logging

logger = logging.getLogger(__name__)

class HeatmapDataView(APIView):
    """热力图数据API视图"""
    # 使用NetBox默认的API权限
    # 通常NetBox API使用TokenAuthentication和SessionAuthentication
    # 这里不设置permission_classes，使用默认设置
    
    def get(self, request):
        try:
            # 获取时间范围参数（默认为'year'，即本年）
            time_range = request.GET.get('time_range', 'year')
            logger.info(f"热力图数据请求，时间范围: {time_range}")
            
            now = timezone.now()
            
            # 根据时间范围计算起始时间
            if time_range == 'month':
                start_date = now - timedelta(days=30)
            elif time_range == 'three_months':
                start_date = now - timedelta(days=90)
            elif time_range == 'year':
                # 本年起始时间（与现有逻辑一致）
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                # 默认使用本年（保持向后兼容）
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                time_range = 'year'
            
            logger.info(f"计算起始时间: {start_date}")
            
            # 获取所有有经纬度的故障
            faults = OtnFault.objects.exclude(
                interruption_longitude__isnull=True
            ).exclude(
                interruption_latitude__isnull=True
            )
            
            logger.info(f"总故障数量（有经纬度）: {faults.count()}")
            
            # 根据时间范围筛选
            heatmap_faults = faults.filter(fault_occurrence_time__gte=start_date)
            logger.info(f"时间范围筛选后故障数量: {heatmap_faults.count()}")
            
            # 构建GeoJSON格式数据
            features = []
            for fault in heatmap_faults:
                try:
                    features.append({
                        'type': 'Feature',
                        'properties': {
                            'count': 1,
                            'fault_number': fault.fault_number,
                            'fault_category': fault.fault_category or 'other'
                        },
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [
                                float(fault.interruption_longitude),
                                float(fault.interruption_latitude)
                            ]
                        }
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"故障数据格式错误，跳过故障 {fault.fault_number}: {e}")
                    continue
            
            logger.info(f"成功构建 {len(features)} 个GeoJSON特征")
            
            return Response({
                'type': 'FeatureCollection',
                'features': features,
                'time_range': time_range,
                'count': len(features)
            })
            
        except Exception as e:
            logger.error(f"热力图数据API异常: {e}", exc_info=True)
            return Response(
                {'error': '服务器内部错误', 'detail': str(e)},
                status=500
            )
