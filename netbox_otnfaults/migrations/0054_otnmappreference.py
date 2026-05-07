from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_otnfaults", "0053_otnfault_fault_category_required"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OtnMapPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("comments", models.TextField(blank=True, verbose_name="评论")),
                ("map_mode", models.CharField(max_length=64, verbose_name="地图模式")),
                ("style_config", models.JSONField(blank=True, default=dict, verbose_name="样式配置")),
                ("schema_version", models.PositiveSmallIntegerField(default=1, verbose_name="配置版本")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="otn_map_preferences",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "地图偏好",
                "verbose_name_plural": "地图偏好",
                "ordering": ("user", "map_mode"),
            },
        ),
        migrations.AddConstraint(
            model_name="otnmappreference",
            constraint=models.UniqueConstraint(
                fields=("user", "map_mode"),
                name="unique_otn_map_preference_user_mode",
            ),
        ),
    ]
