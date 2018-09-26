from django.test import TestCase

from core.models import *
from core import specs


class SpecsTestCase(TestCase):
    def test_create_and_update_audit_config(self):
        positions = [
            {'name': '总裁', 'code': 'ceo'},
            {'name': '负责人', 'code': 'owner'},
            {'name': '会计', 'code': 'accountant'},
            {'name': '出纳', 'code': 'cashier'},
            {'name': '组员', 'code': 'member'},  # 各部门一般成员职位
            {'name': '业务经理', 'code': 'mgr'}  # 只在大宗商品事业部
        ]
        for pos in positions:
            Position.objects.create(**pos)

        departments = [
            {'name': '总部', 'code': 'root'},
            {'name': '大宗商品事业部', 'code': 'dazong'},
            {'name': '财务中心', 'code': 'fin'},
            {'name': '人力行政中心', 'code': 'hr'},
        ]
        for dep in departments:
            Department.objects.create(**dep)

        specs.createAuditConfig(spec='fin.cost_lte_5000:\
                                fin.accountant->\
                                _.owner->\
                                hr.owner->\
                                fin.owner->\
                                fin.cashier')

        config = AuditActivityConfig.objects.all()[0]
        self.assertEqual(config.category, 'fin')
        self.assertEqual(config.subtype, 'cost_lte_5000')
        steps = AuditActivityConfigStep.objects.filter(
            config=config).order_by('position')
        self.assertEqual(steps.count(), 5)
        stepDeps = [
            s.assigneeDepartment.code if s.assigneeDepartment else None for s in steps]
        stepPos = [
            s.assigneePosition.code if s.assigneePosition else None for s in steps]
        self.assertListEqual(stepDeps, ['fin', None, 'hr', 'fin', 'fin'])
        self.assertListEqual(
            stepPos, ['accountant', 'owner', 'owner', 'owner', 'cashier'])

        specs.updateAuditConfig(spec='fin.cost_lte_5000:fin.accountant->_.owner->hr.owner')
        config = AuditActivityConfig.objects.first()
        self.assertEqual(config.category, 'fin')
        self.assertEqual(config.subtype, 'cost_lte_5000')
        steps = AuditActivityConfigStep.objects.filter(
            config=config).order_by('position')
        self.assertEqual(steps.count(), 3)
        stepDeps = [
            s.assigneeDepartment.code if s.assigneeDepartment else None for s in steps]
        stepPos = [
            s.assigneePosition.code if s.assigneePosition else None for s in steps]
        self.assertListEqual(stepDeps, ['fin', None, 'hr'])
        self.assertListEqual(
            stepPos, ['accountant', 'owner', 'owner'])
