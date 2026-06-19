from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0086_circuitservice_is_important_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='otnfault',
            index=models.Index(
                fields=['fault_category', 'fault_occurrence_time'],
                name='otnfault_cat_occ_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='otnfault',
            index=models.Index(
                fields=['is_suspended', 'fault_status', 'fault_occurrence_time'],
                name='otnfault_susp_stat_occ_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='otnfaultimpact',
            index=models.Index(
                fields=['service_type', 'business_impact', 'service_interruption_time'],
                name='otnimpact_type_biz_time_idx',
            ),
        ),
    ]