from django.db import migrations, models
import django.db.models.deletion
import netbox.models.deletion
import taggit.managers
import utilities.json


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0001_initial'),
        ('extras', '0001_initial'),
        ('netbox_otnfaults', '0019_modify_first_report_source_cable_route'),
    ]

    operations = [
        migrations.CreateModel(
            name='OtnPath',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('name', models.CharField(max_length=100)),
                ('cable_type', models.CharField(max_length=20)),
                ('geometry', models.JSONField(blank=True, null=True)),
                ('calculated_length', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.TextField(blank=True)),
                ('comments', models.TextField(blank=True)),
                ('site_a', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='otn_paths_a', to='dcim.site')),
                ('site_z', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='otn_paths_z', to='dcim.site')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': '光缆路径',
                'verbose_name_plural': '光缆路径',
                'ordering': ('name',),
            },
            bases=(netbox.models.deletion.DeleteMixin, models.Model),
        ),
    ]
