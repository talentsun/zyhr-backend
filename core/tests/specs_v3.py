from django.test import TestCase

from core.models import *
from core import specs_v3


class SpecsV3TestCase(TestCase):
    def assert_audit_steps(self, config, deps=[], pos=[]):
        steps = AuditActivityConfigStep.objects \
            .filter(config=config) \
            .order_by('position')

        stepDeps = [getattr(s.assigneeDepartment, 'code', None) for s in steps]
        self.assertListEqual(stepDeps, deps)

        stepPos = [getattr(s.assigneePosition, 'code', None) for s in steps]
        self.assertListEqual(stepPos, pos)

    def test_create_audit_config(self):
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

        config = specs_v3.createAuditConfig(spec='fin.cost:fin.accountant->fin.owner...', fallback=True)
        self.assertEqual(config.category, 'fin')
        self.assertEqual(config.subtype, 'cost')
        self.assertListEqual(config.conditions, [])
        self.assertEqual(config.fallback, True)
        self.assertEqual(config.priority, 0)
        self.assert_audit_steps(
            config,
            deps=['fin', 'fin'],
            pos=['accountant', 'owner']
        )

        config = specs_v3.createAuditConfig(spec='fin.cost(amount<=5000):\
                                fin.accountant->\
                                _.owner->\
                                hr.owner->\
                                fin.owner->\
                                fin.cashier...')
        self.assertEqual(config.category, 'fin')
        self.assertEqual(config.subtype, 'cost')
        self.assertListEqual(config.conditions, [
            {'prop': 'amount', 'condition': 'lte', 'value': 5000}
        ])
        self.assertEqual(config.fallback, False)
        self.assertEqual(config.priority, 1)
        self.assert_audit_steps(
            config,
            deps=['fin', None, 'hr', 'fin', 'fin'],
            pos=['accountant', 'owner', 'owner', 'owner', 'cashier']
        )
