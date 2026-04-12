from django.db import migrations, models


def populate_default_fault_category(apps, schema_editor):
    OtnFault = apps.get_model("netbox_otnfaults", "OtnFault")
    OtnFault.objects.filter(fault_category__isnull=True).update(fault_category="fiber_break")
    OtnFault.objects.filter(fault_category="").update(fault_category="fiber_break")


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_otnfaults", "0052_circuitservice_sla_level"),
    ]

    operations = [
        migrations.RunPython(populate_default_fault_category, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="otnfault",
            name="fault_category",
            field=models.CharField(
                choices=[
                    ("fiber_break", "光缆中断"),
                    ("ac_fault", "空调故障"),
                    ("fiber_degradation", "光缆劣化"),
                    ("fiber_jitter", "光缆抖动"),
                    ("device_fault", "设备故障"),
                    ("power_fault", "供电故障"),
                ],
                default="fiber_break",
                max_length=20,
                verbose_name="故障类型",
            ),
        ),
    ]
