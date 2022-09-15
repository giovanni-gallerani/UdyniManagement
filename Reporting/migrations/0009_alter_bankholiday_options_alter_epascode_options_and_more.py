# Generated by Django 4.0.4 on 2022-08-24 09:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Reporting', '0008_alter_epascode_ts_code_alter_presencedata_ts_code'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bankholiday',
            options={'default_permissions': (), 'ordering': ['year', 'month', 'day'], 'permissions': [('view', 'View list of bank holidays'), ('manage', 'Manage list of bank holidays')]},
        ),
        migrations.AlterModelOptions(
            name='epascode',
            options={'default_permissions': (), 'ordering': ['code'], 'permissions': [('view', 'View list of EPAS codes'), ('manage', 'Manage list of EPAS codes')]},
        ),
        migrations.AlterModelOptions(
            name='personnelcost',
            options={'default_permissions': (), 'ordering': ['year', 'researcher'], 'permissions': [('view', 'View personnel costs'), ('manage', 'Manage personnel costs')]},
        ),
        migrations.AlterModelOptions(
            name='presencedata',
            options={'default_permissions': (), 'ordering': ['researcher', 'day'], 'permissions': [('view', 'View presences'), ('view_own', 'View own presences'), ('manage', 'Manage presences'), ('manage_own', 'Manage own presences')]},
        ),
        migrations.AlterModelOptions(
            name='reportedmission',
            options={'default_permissions': (), 'ordering': ['period', 'day__researcher', 'day__day'], 'permissions': [('view', 'View reported missions'), ('view_own', 'View own reported missions'), ('manage', 'Manage reported missions'), ('manage_own', 'Manage own reported missions')]},
        ),
        migrations.AlterModelOptions(
            name='reportedwork',
            options={'default_permissions': (), 'ordering': ['period', 'year', 'month', 'researcher'], 'permissions': [('view', 'View reported work'), ('view_own', 'View own reported work'), ('manage', 'Manage reported work'), ('manage_own', 'Manage own reported work')]},
        ),
        migrations.AlterModelOptions(
            name='reportedworkworkpackage',
            options={'default_permissions': (), 'ordering': ['report', 'workpackage']},
        ),
        migrations.AlterModelOptions(
            name='reportingperiod',
            options={'default_permissions': (), 'ordering': ['project', 'rp_start'], 'permissions': [('view', 'View reporting periods'), ('manage', 'Manage reporting periods'), ('manage_own', 'Manage reporting periods of own projects')]},
        ),
        migrations.AlterModelOptions(
            name='timesheethours',
            options={'default_permissions': (), 'permissions': [('view', 'View timesheets'), ('view_own', 'View own timesheets'), ('manage', 'Manage timesheets'), ('manage_own', 'Manage own timesheets')]},
        ),
    ]
