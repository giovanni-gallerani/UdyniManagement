# Generated by Django 3.2.9 on 2022-06-29 13:07

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Accounting', '0016_alter_variazione_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mandato',
            name='data',
            field=models.DateField(default=datetime.date(2022, 6, 29)),
            preserve_default=False,
        ),
    ]
