# Generated by Django 2.0.1 on 2019-04-26 00:20

from django.db import migrations
from core import specs
from core.models import *


def update_biz_audit_flow(apps, schema_editor):
    pos_law_mgr = Position.objects.filter(code='law_mgr').first()
    if pos_law_mgr is None:
        pos_law_mgr = Position.objects.create(name='投资法务顾问', code='law_mgr')

    dep_dichan = Department.objects.filter(code='dichan').first()
    if dep_dichan is None:
        dep_dichan = Department.objects.create(code='dichan', name='地产事业部')

    if DepPos.objects.filter(pos=pos_law_mgr, dep=dep_dichan).count() == 0:
        DepPos.objects.create(pos=pos_law_mgr, dep=dep_dichan)

    specs.updateAuditConfig(spec='law.biz_contract_no_risk:\
                            fin.fin_accountant->\
                            dichan.law_mgr->\
                            _.owner...')

    specs.updateAuditConfig(spec='law.biz_contract_risk:\
                            fin.fin_accountant->\
                            dichan.law_mgr->\
                            _.owner->\
                            root.ceo...')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0017_auto_20190426_0000'),
    ]

    operations = [
        migrations.RunPython(update_biz_audit_flow),
    ]
