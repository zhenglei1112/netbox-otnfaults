from netbox.plugins import PluginConfig

class OtnFaultsConfig(PluginConfig):
    name = 'netbox_otnfaults'
    verbose_name = '故障管理'
    description = '网络故障登记系统'
    version = '0.1.0'
    base_url = 'otnfaults'
    author = 'OTN Faults Team'
    author_email = 'otnfaults@example.com'
    required_settings = []
    default_settings = {
        # Stadia Maps API 密钥（请在 configuration.py 中配置实际值）
        'map_api_key': '',
        # 地图默认中心点 [经度, 纬度]
        'map_default_center': [112.53, 33.00],
        # 地图默认缩放级别
        'map_default_zoom': 4.2,
        # 热力图数据缓存时间（秒）
        'heatmap_cache_timeout': 300,
    }
    
    # Netbox 4.x compatibility
    min_version = '4.0'
    max_version = '4.99'
    
    # API configuration
    def ready(self):
        super().ready()
        
        # Register API URLs
        from . import api

config = OtnFaultsConfig

