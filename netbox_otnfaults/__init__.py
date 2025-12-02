from netbox.plugins import PluginConfig

class OtnFaultsConfig(PluginConfig):
    name = 'netbox_otnfaults'
    verbose_name = '故障管理'
    description = '网络故障登记系统'
    version = '0.1'
    base_url = 'otnfaults'
    author = '您的姓名'
    author_email = 'your.email@example.com'
    required_settings = []
    default_settings = {}
    
    # Netbox 4.x compatibility
    min_version = '4.0'
    max_version = '4.99'
    
    # API configuration
    def ready(self):
        super().ready()
        
        # Register API URLs
        from . import api

config = OtnFaultsConfig
