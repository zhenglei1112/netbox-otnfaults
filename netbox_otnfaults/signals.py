from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import OtnFault, OtnFaultImpact, BareFiberService, CircuitService

VERSION_KEY = "otnfaults:stats:version"

def increment_stats_version(*args, **kwargs):
    """递增全局统计缓存版本号，使旧缓存失效。"""
    try:
        current_version = cache.get(VERSION_KEY)
        if current_version is None:
            cache.set(VERSION_KEY, 2, timeout=None)
        else:
            cache.set(VERSION_KEY, int(current_version) + 1, timeout=None)
    except Exception:
        pass

# 注册 post_save / post_delete 信号
for model in [OtnFault, OtnFaultImpact, BareFiberService, CircuitService]:
    post_save.connect(increment_stats_version, sender=model)
    post_delete.connect(increment_stats_version, sender=model)

# 注册 m2m_changed 信号以监听 Z 端站点关联的变化
m2m_changed.connect(increment_stats_version, sender=OtnFault.interruption_location.through)
m2m_changed.connect(increment_stats_version, sender=OtnFaultImpact.service_site_z.through)
