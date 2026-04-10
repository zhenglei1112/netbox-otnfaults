from django.db import migrations

def update_business_category(apps, schema_editor):
    CircuitService = apps.get_model('netbox_otnfaults', 'CircuitService')
    
    mapping = {
        'ministry_province_transport': '01_ministry_province_transport',
        'commercial_other': '02_commercial_other',
        'maritime_service': '03_maritime_service',
        'road_network_service': '04_road_network_service',
        'legacy_ruijie_service': '05_legacy_ruijie_service',
        'travelsky': '06_travelsky',
        'jinhang': '07_jinhang',
        'lanxun': '08_lanxun',
        'commercial_100g': '09_commercial_100g',
        'changhang': '10_changhang',
        'ministry_organ': '11_ministry_organ',
    }
    
    # 批量更新数据库里的记录，避免触发任何可能验证错误
    for old_val, new_val in mapping.items():
        CircuitService.objects.filter(business_category=old_val).update(business_category=new_val)

def reverse_update_business_category(apps, schema_editor):
    CircuitService = apps.get_model('netbox_otnfaults', 'CircuitService')
    
    reverse_mapping = {
        '01_ministry_province_transport': 'ministry_province_transport',
        '02_commercial_other': 'commercial_other',
        '03_maritime_service': 'maritime_service',
        '04_road_network_service': 'road_network_service',
        '05_legacy_ruijie_service': 'legacy_ruijie_service',
        '06_travelsky': 'travelsky',
        '07_jinhang': 'jinhang',
        '08_lanxun': 'lanxun',
        '09_commercial_100g': 'commercial_100g',
        '10_changhang': 'changhang',
        '11_ministry_organ': 'ministry_organ',
    }
    
    for old_val, new_val in reverse_mapping.items():
        CircuitService.objects.filter(business_category=old_val).update(business_category=new_val)

class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0047_alter_circuitservice_options'),
    ]

    operations = [
        migrations.RunPython(update_business_category, reverse_update_business_category),
    ]
