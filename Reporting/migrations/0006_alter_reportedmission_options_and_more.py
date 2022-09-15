# Generated by Django 4.0.4 on 2022-07-18 10:26
# Modified to correcly delete day and rename day_pk to day

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Projects', '0010_project_depreciation'),
        ('Reporting', '0005_auto_20220718_1112'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reportedmission',
            options={'ordering': ['period', 'day__researcher', 'day__day']},
        ),
        migrations.RemoveConstraint(
            model_name='reportedmission',
            name='reporting_reportedmission_unique',
        ),
        migrations.RemoveField(
            model_name='reportedmission',
            name='day',
        ),
        migrations.RemoveField(
            model_name='reportedmission',
            name='researcher',
        ),
        migrations.RenameField(
            model_name='reportedmission',
            old_name='day_pk',
            new_name='day',
        ),
        migrations.AlterField(
            model_name='reportedmission',
            name='workpackage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reported_missions', to='Projects.workpackage'),
        ),
        migrations.AddConstraint(
            model_name='reportedmission',
            constraint=models.UniqueConstraint(fields=('period', 'day'), name='reporting_reportedmission_unique'),
        ),
    ]
