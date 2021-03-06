# Generated by Django 2.0.1 on 2019-05-08 23:15

from django.db import migrations
from core import specs


def update_audit_flow(apps, schema_editor):
    specs.updateAuditConfig(spec='law.biz_contract_no_risk:\
                            fin.fin_accountant->\
                            hr-risk.fuzongjian->\
                            _.owner...')
    specs.updateAuditConfig(spec='law.biz_contract_risk:\
                            fin.fin_accountant->\
                            hr-risk.fuzongjian->\
                            _.owner->\
                            root.ceo...')
    specs.updateAuditConfig(spec='law.fn_contract:\
                            _.owner->\
                            hr-risk.fuzongjian->\
                            fin.fin_accountant->\
                            root.ceo...')
    specs.updateAuditConfig(spec='law.fn_contract_zero:\
                            _.owner->\
                            hr-risk.fuzongjian->\
                            root.ceo...')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0020_add_hr_risk_department'),
    ]

    operations = [
        migrations.RunPython(update_audit_flow)
    ]
