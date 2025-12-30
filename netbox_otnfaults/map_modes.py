from django.urls import reverse

MAP_MODE_DEFAULTS = {
    'basemap': 'network',
    'projection': 'globe',
    'layers': {},
    'controls': ['navigation', 'fullscreen', 'scale'],
    'js_files': [],
    'plugin_file': 'unified_map_core.js' # Fallback
}

MAP_MODES = {
    'fault': {
        'title': '故障分布图',
        'plugin_file': 'fault_mode.js',
        'projection': 'globe',
        'header_actions': [
            {
                'label': '查看列表',
                'url_name': 'plugins:netbox_otnfaults:otnfault_list',
                'icon': 'mdi-format-list-bulleted'
            }
        ],
        'layers': {},
        'js_files': [
            'core/config.js',
            'utils/api.js',
            'services/FaultDataService.js',
            'controls/LayerToggleControl.js',
            'controls/FaultStatisticsControl.js',
            'controls/FaultLegendControl.js',
            'controls/SearchControl.js'
        ]
    },
    'location': {
        'title': '位置地图',
        'plugin_file': 'location_mode.js',
        'projection': 'mercator',
        'controls': ['navigation', 'fullscreen', 'measures'],
        'layers': {},
        'js_files': []
    },
    'path': {
        'title': '路径地图',
        'plugin_file': 'location_mode.js',
        'projection': 'mercator',
        'controls': ['navigation', 'fullscreen', 'measures'],
        'layers': {},
        'js_files': []
    },
    'pathgroup': {
        'title': '路径组地图',
        'plugin_file': 'location_mode.js',
        'projection': 'mercator',
        'controls': ['navigation', 'fullscreen', 'measures'],
        'layers': {},
        'js_files': []
    }
}

def get_mode_config(mode_name, context=None):
    """
    获取合并后的模式配置
    
    Args:
        mode_name (str): 模式名称
        context (dict): 用于格式化动态字符串的上下文
        
    Returns:
        dict: 合并默认值后的完整配置
    """
    context = context or {}
    mode_config = MAP_MODES.get(mode_name, {}).copy()
    
    # 合并默认值
    config = MAP_MODE_DEFAULTS.copy()
    config.update(mode_config)
    
    # 直接设置模式名称
    config['name'] = mode_name
    
    # 动态处理 header_info (如果定义为格式化字符串)
    # 这里留给视图层处理，但在配置中可以定义模板
    
    return config
