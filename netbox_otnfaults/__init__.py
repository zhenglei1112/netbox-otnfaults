from netbox.plugins import PluginConfig

class OtnFaultsConfig(PluginConfig):
    name = 'netbox_otnfaults'
    verbose_name = 'OTN Faults'
    description = 'OTN Network Fault Registration'
    version = '0.1'
    base_url = 'otnfaults'
    author = 'Your Name'
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
