# Generated by Django 3.2.5 on 2022-04-28 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Accounting', '0004_auto_20220428_1240'),
    ]

    operations = [
        migrations.AddField(
            model_name='stanziamento',
            name='var_meno',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='stanziamento',
            name='var_piu',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='mandato',
            name='pg_mandato',
            field=models.IntegerField(unique=True),
        ),
        migrations.AddConstraint(
            model_name='impegno',
            constraint=models.UniqueConstraint(fields=('gae', 'pg_impegno'), name='accounting_impegno_unique'),
        ),
        migrations.AddConstraint(
            model_name='stanziamento',
            constraint=models.UniqueConstraint(fields=('gae', 'esercizio', 'voce'), name='accounting_stanziamento_unique'),
        ),
        migrations.AddConstraint(
            model_name='variazione',
            constraint=models.UniqueConstraint(fields=('gae', 'numero'), name='accounting_variazione_unique'),
        ),
    ]
