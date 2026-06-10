from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0080_cutover_impact_integration'),
    ]

    operations = [
        migrations.AddField(
            model_name='cutovertask',
            name='re_cutover',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='previous_cutovers',
                to='netbox_otnfaults.cutovertask',
                verbose_name='再次割接',
                help_text='本次割接未完成或效果不理想时，可选择下一次再次割接的任务'
            ),
        ),
    ]
