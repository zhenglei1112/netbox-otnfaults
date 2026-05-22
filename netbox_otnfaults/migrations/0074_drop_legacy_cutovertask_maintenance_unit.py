from django.db import migrations


DROP_LEGACY_MAINTENANCE_UNIT = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'netbox_otnfaults_cutovertask'
          AND column_name = 'maintenance_unit'
    ) THEN
        ALTER TABLE netbox_otnfaults_cutovertask DROP COLUMN maintenance_unit;
    END IF;
END $$;
"""


RESTORE_LEGACY_MAINTENANCE_UNIT = """
ALTER TABLE netbox_otnfaults_cutovertask
ADD COLUMN IF NOT EXISTS maintenance_unit varchar(100) NOT NULL DEFAULT '';
"""


class Migration(migrations.Migration):
    dependencies = [
        ('netbox_otnfaults', '0073_remove_cutovertask_maintenance_unit'),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_LEGACY_MAINTENANCE_UNIT,
            reverse_sql=RESTORE_LEGACY_MAINTENANCE_UNIT,
        ),
    ]
