# Generated by Django 4.0.4 on 2022-06-02 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Projects', '0009_auto_20220422_1837'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='depreciation',
            field=models.IntegerField(default=0),
        ),
    ]
