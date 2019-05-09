# Generated by Django 2.0.1 on 2019-05-08 23:59

import logging
from django.db import migrations
from core.models import *
from core import specs


def transfer(apps, schema_editor):
    print("\n")
    print("\n")
    print("=======transfer fin.owner to fin.fin_manager======")
    print("")
    pos_fin_manager = Position.objects.create(code='fin_manager', name='财务经理')
    department = Department.objects.get(code='fin')
    DepPos.objects.create(dep=department, pos=pos_fin_manager)

    pos_owner = Position.objects.get(code='owner')
    steps = AuditActivityConfigStep.objects.filter(assigneeDepartment=department, assigneePosition=pos_owner)
    for step in steps:
        config = AuditActivityConfig.objects.get(pk=step.config.pk)
        print('  Update audit flow {}.{}'.format(step.config.category, step.config.subtype))
        print('    previous:', specs.auditFlowToString(config))
        step.assigneePosition = pos_fin_manager
        step.save()
        config = AuditActivityConfig.objects.get(pk=step.config.pk)
        print('     current:', specs.auditFlowToString(config))
    print("")
    print("=======transfer fin.owner to fin.fin_manager======")
    print("\n")
    print("\n")


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0021_update_audit_flow_20190508_2315'),
    ]

    operations = [
        migrations.RunPython(transfer)
    ]
