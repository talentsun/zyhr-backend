# Generated by Django 2.0.1 on 2019-01-18 07:16

from django.db import migrations
from core.models import *


def add_positions(app, schema_editor):
    dichan = Department.objects.filter(code='dichan').first()

    if dichan is not None:
        pos1 = Position.objects.create(name='投资测算经理')
        pos2 = Position.objects.create(name='设计经理')
        pos3 = Position.objects.create(name='成本经理')
        pos4 = Position.objects.create(name='营销经理')
        pos5 = Position.objects.create(name='工程经理')

        for p in [pos1, pos2, pos3, pos4, pos5]:
            DepPos.objects.create(dep=dichan, pos=p)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0011_rename_dep_pos'),
    ]

    operations = [
        migrations.RunPython(add_positions)
    ]
