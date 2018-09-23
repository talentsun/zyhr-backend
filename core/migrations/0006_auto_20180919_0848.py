# Generated by Django 2.0.1 on 2018-09-19 08:48

from django.db import migrations, models, transaction
import jsonfield.fields

from core.models import *
from core.management.commands.prepareData import Command


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_auto_20180821_0252'),
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=255, unique=True)),
                ('value', jsonfield.fields.JSONField()),
            ],
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='conditions',
            field=jsonfield.fields.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='default',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='priority',
            field=models.IntegerField(default=0),
        ),
    ]
