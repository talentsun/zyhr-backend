# Generated by Django 2.0.1 on 2018-09-19 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20180919_0848'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditactivityconfig',
            name='subtype',
            field=models.CharField(max_length=255),
        ),
    ]
