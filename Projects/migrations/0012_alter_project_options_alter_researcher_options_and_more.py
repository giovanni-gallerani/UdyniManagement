# Generated by Django 4.0.4 on 2022-08-24 09:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Projects', '0011_alter_project_agency'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'default_permissions': (), 'ordering': ['name'], 'permissions': [('view', 'View list of projects'), ('manage', 'Manage list of projects')]},
        ),
        migrations.AlterModelOptions(
            name='researcher',
            options={'default_permissions': (), 'ordering': ['surname', 'name'], 'permissions': [('view', 'View list of researchers'), ('manage', 'Manage list of researchers')]},
        ),
        migrations.AlterModelOptions(
            name='researcherrole',
            options={'default_permissions': (), 'ordering': ['researcher', 'start_date'], 'permissions': [('view', 'View researchers roles'), ('manage_own', 'Modify own role'), ('manage', 'Manage researchers roles')]},
        ),
        migrations.AlterModelOptions(
            name='workpackage',
            options={'default_permissions': (), 'ordering': ['project__name', 'name']},
        ),
    ]
