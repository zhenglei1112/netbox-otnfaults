from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0044_circuitservice_is_external_business'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='business_category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('ministry_province_transport', '部省传输'),
                    ('commercial_other', '商业其他'),
                    ('maritime_service', '海事业务'),
                    ('road_network_service', '路网业务'),
                    ('legacy_ruijie_service', '老锐捷业务'),
                    ('travelsky', '航信'),
                    ('jinhang', '金航'),
                    ('lanxun', '缆讯'),
                    ('commercial_100g', '商业百G'),
                    ('changhang', '长航'),
                ],
                max_length=40,
                verbose_name='业务门类',
            ),
        ),
    ]
