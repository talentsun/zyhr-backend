# Generated by Django 2.0.1 on 2019-01-18 07:16

from django.db import migrations

from pypinyin import pinyin, lazy_pinyin, Style
from core.models_v1 import *


def add_positions(app, schema_editor):
    dichan = DepartmentLegacy.objects.filter(code='dichan').first()
    if dichan is None:
        dichan = DepartmentLegacy.objects.create(name='地产事业部', code='dichan')

    positions = [
        '投资测算经理',
        '投资测算经理',
        '设计经理',
        '成本经理',
        '营销经理',
        '工程经理'
    ]
    for pos in positions:
        position = PositionLegacy.objects.filter(name=pos).first()
        if position is None:
            position = PositionLegacy.objects.create(name=pos, code='_'.join(lazy_pinyin(pos)))
            DepPosLegacy.objects.create(dep=dichan, pos=position)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0011_rename_dep_pos'),
    ]

    operations = [
        migrations.RunPython(add_positions)
    ]
