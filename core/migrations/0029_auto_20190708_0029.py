# Generated by Django 2.0.1 on 2019-07-08 00:29

from django.db import migrations
from core.models import *


def addSelectCustomAuditFlowPermission(apps, schema_editor):
    roles = Role.objects.all()
    for role in roles:
        role.extra.append('select_custom_audit_flow')
        role.save()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0028_auto_20190504_1649'),
    ]

    operations = [
        migrations.RunPython(addSelectCustomAuditFlowPermission),
    ]
