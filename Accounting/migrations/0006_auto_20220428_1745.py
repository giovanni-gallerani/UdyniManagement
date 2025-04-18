# Generated by Django 3.2.5 on 2022-04-28 15:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Accounting', '0005_auto_20220428_1707'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='impegno',
            options={'ordering': ['gae', 'esercizio', 'pg_impegno']},
        ),
        migrations.RemoveConstraint(
            model_name='impegno',
            name='accounting_impegno_unique',
        ),
        migrations.AlterField(
            model_name='impegno',
            name='pg_impegno',
            field=models.BigIntegerField(),
        ),
        migrations.AddConstraint(
            model_name='impegno',
            constraint=models.UniqueConstraint(fields=('gae', 'esercizio', 'pg_impegno'), name='accounting_impegno_unique'),
        ),
    ]
