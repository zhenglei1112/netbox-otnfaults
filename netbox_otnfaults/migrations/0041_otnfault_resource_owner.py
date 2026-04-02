from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0040_otnfaultimpact_service_site_a_service_site_z'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='resource_owner',
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                verbose_name='资源所有者',
            ),
        ),
    ]
