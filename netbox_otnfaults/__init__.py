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
        # 是否使用本地底图（默认 False 使用网络底图）
        'use_local_basemap': False,
        # 本地瓦片服务地址（仅 use_local_basemap=True 时生效）
        'local_tiles_url': 'http://192.168.30.177:8080/maps/china.pmtiles',
        # 本地字体服务地址（仅 use_local_basemap=True 时生效）
        'local_glyphs_url': 'http://192.168.30.177:8080/maps/fonts/{fontstack}/{range}.pbf',
        'otn_paths_pmtiles_url': 'http://192.168.30.177:8080/maps/otn_paths.pmtiles', # OTN路径PMTiles服务URL
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

