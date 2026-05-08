import django.contrib.postgres.fields
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0056_otnfault_cutover_report_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        DROP DEFAULT;
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        TYPE varchar(40)[]
                        USING CASE
                            WHEN recovery_mode IS NULL OR recovery_mode = ''
                                THEN ARRAY[]::varchar(40)[]
                            ELSE string_to_array(recovery_mode, ',')::varchar(40)[]
                        END;
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        SET DEFAULT ARRAY[]::varchar(40)[];
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        SET NOT NULL;
                        CREATE INDEX netbox_otnf_recovery_732470_gin
                        ON netbox_otnfaults_otnfault
                        USING gin (recovery_mode);
                        UPDATE netbox_otnfaults_otnfault
                        SET recovery_mode = array_remove(ARRAY[
                            CASE WHEN recovery_mode @> ARRAY['emergency_generation']::varchar(40)[]
                                THEN 'emergency_generation'::varchar(40) END,
                            CASE WHEN recovery_mode @> ARRAY['battery_power']::varchar(40)[]
                                THEN 'battery_power'::varchar(40) END,
                            CASE WHEN recovery_mode @> ARRAY['utility_power_restored']::varchar(40)[]
                                THEN 'utility_power_restored'::varchar(40) END,
                            CASE WHEN recovery_mode @> ARRAY['onsite_handling']::varchar(40)[]
                                THEN 'onsite_handling'::varchar(40) END
                        ], NULL)::varchar(40)[];
                    """,
                    reverse_sql="""
                        DROP INDEX IF EXISTS netbox_otnf_recovery_732470_gin;
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        DROP DEFAULT;
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        DROP NOT NULL;
                        ALTER TABLE netbox_otnfaults_otnfault
                        ALTER COLUMN recovery_mode
                        TYPE varchar(120)
                        USING array_to_string(recovery_mode, ',');
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='otnfault',
                    name='recovery_mode',
                    field=django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(
                            choices=[
                                ('emergency_generation', '应急发电'),
                                ('battery_power', '电池供电'),
                                ('utility_power_restored', '市电恢复'),
                                ('onsite_handling', '现场处置'),
                            ],
                            max_length=40,
                        ),
                        blank=True,
                        default=list,
                        size=None,
                        verbose_name='应对措施',
                    ),
                ),
                migrations.AddIndex(
                    model_name='otnfault',
                    index=GinIndex(fields=['recovery_mode'], name='netbox_otnf_recovery_732470_gin'),
                ),
            ],
        ),
    ]
