# Generated by Django 3.2.7 on 2022-01-24 11:28

from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('FinancialReporting', '0017_auto_20220124_1218'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='personnelcost',
            name='unique_cost',
        ),
        migrations.RemoveConstraint(
            model_name='presencedata',
            name='unique_day',
        ),
        migrations.RemoveConstraint(
            model_name='project',
            name='unique_project',
        ),
        migrations.RemoveConstraint(
            model_name='reporting',
            name='financialreporting_unique_report',
        ),
        migrations.RemoveConstraint(
            model_name='reporting',
            name='financialreporting_rp_start_lt_rp_end',
        ),
        migrations.RemoveConstraint(
            model_name='researcher',
            name='unique_researcher',
        ),
        migrations.RemoveConstraint(
            model_name='timesheethint',
            name='unique_hint',
        ),
        migrations.RemoveConstraint(
            model_name='timesheethours',
            name='unique_ts_hours',
        ),
        migrations.RemoveConstraint(
            model_name='workpackage',
            name='unique_wp',
        ),
        migrations.AddConstraint(
            model_name='bankholiday',
            constraint=models.UniqueConstraint(fields=('year', 'month', 'day'), name='financialreporting_bankholiday_unique'),
        ),
        migrations.AddConstraint(
            model_name='epascode',
            constraint=models.UniqueConstraint(fields=('code',), name='financialreporting_epascode_unique'),
        ),
        migrations.AddConstraint(
            model_name='personnelcost',
            constraint=models.UniqueConstraint(fields=('year', 'researcher'), name='financialreporting_personnelcost_unique'),
        ),
        migrations.AddConstraint(
            model_name='presencedata',
            constraint=models.UniqueConstraint(fields=('researcher', 'day'), name='financialreporting_presencedata_unique'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('name',), name='financialreporting_project_unique'),
        ),
        migrations.AddConstraint(
            model_name='reporting',
            constraint=models.UniqueConstraint(fields=('researcher', 'project', 'wp', 'rp_start', 'rp_end'), name='financialreporting_reporting_unique'),
        ),
        migrations.AddConstraint(
            model_name='reporting',
            constraint=models.CheckConstraint(check=models.Q(('rp_start__lt', django.db.models.expressions.F('rp_end'))), name='financialreporting_reporting_start_lt_end'),
        ),
        migrations.AddConstraint(
            model_name='researcher',
            constraint=models.UniqueConstraint(fields=('name', 'surname'), name='financialreporting_researcher_unique'),
        ),
        migrations.AddConstraint(
            model_name='timesheethint',
            constraint=models.UniqueConstraint(fields=('reporting_period', 'year', 'month'), name='financialreporting_timesheethint_unique'),
        ),
        migrations.AddConstraint(
            model_name='timesheethours',
            constraint=models.UniqueConstraint(fields=('reporting_period', 'day'), name='financialreporting_timesheethours_unique'),
        ),
        migrations.AddConstraint(
            model_name='workpackage',
            constraint=models.UniqueConstraint(fields=('project', 'name'), name='financialreporting_workpackage_unique'),
        ),
    ]
