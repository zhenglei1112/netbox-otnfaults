from django.db import migrations, models


def copy_name_to_special_line_name(apps, schema_editor):
    CircuitService = apps.get_model('netbox_otnfaults', 'CircuitService')
    for service in CircuitService.objects.all():
        service.special_line_name = service.name
        service.save(update_fields=['special_line_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0045_circuitservice_business_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='special_line_name',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='专线名称'),
            preserve_default=False,
        ),
        migrations.RunPython(copy_name_to_special_line_name, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='circuitservice',
            name='special_line_name',
            field=models.CharField(max_length=100, verbose_name='专线名称'),
        ),
    ]
