# Generated by Django 3.2.7 on 2021-11-25 18:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FinancialReporting', '0008_auto_20211124_1652'),
    ]

    operations = [
        migrations.CreateModel(
            name='EpasCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=32, unique=True)),
                ('ts_code', models.CharField(choices=[('', 'None'), ('HO', 'Holidays'), ('MI', 'Mission'), ('IL', 'Illness')], default='', max_length=2)),
                ('description', models.CharField(max_length=256)),
            ],
        ),
    ]
