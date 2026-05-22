from django.db import migrations


DROP_LEGACY_REMARKS = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'netbox_otnfaults_cutovertask'
          AND column_name = 'remarks'
    ) THEN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'netbox_otnfaults_cutovertask'
              AND column_name = 'comments'
        ) THEN
            EXECUTE $sql$
                UPDATE netbox_otnfaults_cutovertask
                SET comments = CASE
                    WHEN comments IS NULL OR comments = '' THEN remarks
                    ELSE comments || E'\n' || remarks
                END
                WHERE remarks IS NOT NULL
                  AND remarks <> ''
            $sql$;
        END IF;

        ALTER TABLE netbox_otnfaults_cutovertask DROP COLUMN remarks;
    END IF;
END $$;
"""


RESTORE_LEGACY_REMARKS = """
ALTER TABLE netbox_otnfaults_cutovertask
ADD COLUMN IF NOT EXISTS remarks text NOT NULL DEFAULT '';
"""


class Migration(migrations.Migration):
    dependencies = [
        ('netbox_otnfaults', '0069_cutovertask_province_text_nullable'),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_LEGACY_REMARKS,
            reverse_sql=RESTORE_LEGACY_REMARKS,
        ),
    ]
