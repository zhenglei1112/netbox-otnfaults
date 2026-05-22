from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0072_remove_cutovertask_customer_approval_result'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cutovertask',
            name='maintenance_unit',
        ),
    ]
