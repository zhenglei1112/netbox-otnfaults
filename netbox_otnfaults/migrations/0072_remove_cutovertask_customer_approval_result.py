from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0071_cutoverimpact'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cutovertask',
            name='customer_approval_result',
        ),
    ]
