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
        ]
        for pos in positions:
            Position.objects.create(**pos)

        departments = [
            {'name': '总部', 'code': 'root', 'pos': ['ceo']},
            {'name': '财务中心', 'code': 'fin', 'pos': ['owner', 'accountant', 'cashier']},
            {'name': '人力行政中心', 'code': 'hr', 'pos': ['owner']},
        ]
        for dep in departments:
            dep_ = Department.objects.create(name=dep['name'], code=dep['code'])
            for code in dep['pos']:
                pos = Position.objects.get(code=code)
                DepPos.objects.create(dep=dep_, pos=pos)

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
            pos=['accountant', None, 'owner', 'owner', 'cashier']
        )
