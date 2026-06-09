from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0077_heavyduty_comments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cutovertask',
            name='related_customers',
            field=models.JSONField(blank=True, default=list, verbose_name='关联业务'),
        ),
    ]
