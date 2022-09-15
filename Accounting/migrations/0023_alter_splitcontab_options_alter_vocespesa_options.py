# Generated by Django 4.0.4 on 2022-09-15 09:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Accounting', '0022_alter_gae_options_alter_vocespesa_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='splitcontab',
            options={'default_permissions': (), 'ordering': ['gae', 'responsible'], 'permissions': [('splitcontab_view', 'View split accounting'), ('splitcontab_view_own', 'View own split accounting'), ('splitcontab_manage', 'Manage split accounting'), ('splitcontab_manage_own', 'Manage own split accounting')]},
        ),
        migrations.AlterModelOptions(
            name='vocespesa',
            options={'default_permissions': (), 'ordering': ['voce']},
        ),
    ]
