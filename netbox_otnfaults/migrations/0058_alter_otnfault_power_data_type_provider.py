from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0057_alter_otnfault_recovery_mode_response_measures'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otnfault',
            name='power_data_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('owned_equipment', '自有设备'),
                    ('phase_one_supporting', '一期配套'),
                    ('third_party_provided', '三方提供'),
                ],
                max_length=20,
                null=True,
                verbose_name='供电设备提供方',
            ),
        ),
        migrations.RunSQL(
            sql="""
                UPDATE netbox_otnfaults_otnfault
                SET power_data_type = NULL
                WHERE power_data_type IS NOT NULL
                  AND power_data_type NOT IN (
                    'owned_equipment',
                    'phase_one_supporting',
                    'third_party_provided'
                  );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
