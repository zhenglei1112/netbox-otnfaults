import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0001_initial'),
        ('netbox_otnfaults', '0039_alter_otnfault_first_report_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfaultimpact',
            name='service_site_a',
            field=models.ForeignKey(
                blank=True,
                help_text='仅裸纤业务时使用',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='impact_service_site_a',
                to='dcim.site',
                verbose_name='业务站点A',
            ),
        ),
        migrations.AddField(
            model_name='otnfaultimpact',
            name='service_site_z',
            field=models.ForeignKey(
                blank=True,
                help_text='仅裸纤业务时使用',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='impact_service_site_z',
                to='dcim.site',
                verbose_name='业务站点Z',
            ),
        ),
    ]
