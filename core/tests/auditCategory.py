import json
from django.test import TestCase
from django.test import Client

from core import specs
from core.models import *
from core.auth import generateToken
from core.tests import helpers


class AuditCategoryTestCase(TestCase):
    def setUp(self):
        self.profile = helpers.prepareProfile('root', 'root', '13333333333')
        self.generateToken = generateToken(self.profile)
        self.auditConfiguration = {
            'categories': ['fin', 'law', 'hr'],
            'audits': [
                {'subtype': 'cost', 'name': '费用报销', 'category': 'fin', 'hasTask': True, 'enabled': True},
                {'subtype': 'loan', 'name': '借款申请', 'category': 'fin', 'hasTask': True, 'enabled': True},
                {'subtype': 'money', 'name': '用款申请', 'category': 'fin', 'hasTask': True, 'enabled': True},
                {'subtype': 'open_account', 'name': '银行开户', 'category': 'fin', 'hasTask': True, 'enabled': True},
                {'subtype': 'travel', 'name': '差旅报销', 'category': 'fin', 'hasTask': True, 'enabled': True},

                {'subtype': 'biz', 'name': '业务合同会签', 'category': 'law', 'hasTask': True, 'enabled': True},
                {'subtype': 'fn', 'name': '职能合同会签', 'category': 'law', 'hasTask': True, 'enabled': True}
            ]
        }
        Configuration.objects.create(
            key='audits',
            value=self.auditConfiguration
        )

        positions = [
            {'name': '总裁', 'code': 'ceo'},
            {'name': '负责人', 'code': 'owner'},  # 每个部门都也负责人

            # 财务中心
            {'name': '会计', 'code': 'fin_accountant'},
            {'name': '出纳', 'code': 'fin_cashier'},

            # 行政中心
            {'name': '行政专员', 'code': 'hr_admin_member'},  # 行政专员
            {'name': '人事经理', 'code': 'hr_mgr'},  # 人事经理
            {'name': '人事专员', 'code': 'hr_member'},  # 人事专员

            # 大宗事业部岗位
            {'name': '业务经理', 'code': 'dazong_mgr'},  # 业务经理
            {'name': '业务专员', 'code': 'dazong_member'},  # 业务专员
        ]
        for pos in positions:
            Position.objects.create(**pos)

        departments = [
            {'name': '总部', 'code': 'root', 'positions': ['ceo']},
            {'name': '大宗商品事业部', 'code': 'dazong',
             'positions': ['owner', 'dazong_mgr', 'dazong_member']
             },
            {'name': '财务中心', 'code': 'fin',
             'positions': ['owner', 'fin_accountant', 'fin_cashier']
             },
            {'name': '人力行政中心', 'code': 'hr',
             'positions': ['owner', 'hr_mgr', 'hr_admin_member', 'hr_member']
             },
            {'name': '地产事业部', 'code': 'dichan', 'positions': ['owner']},
            {'name': '金融事业部', 'code': 'jinrong', 'positions': []},
        ]

        for dep in departments:
            positions = dep['positions']
            del dep['positions']

            department = Department.objects.create(**dep)
            for pos in positions:
                position = Position.objects.get(code=pos)
                DepPos.objects.create(pos=position, dep=department)

    def pos_pk(self, code):
        return str(Position.objects.get(code=code).pk)

    def dep_pk(self, code):
        return str(Department.objects.get(code=code).pk)

    def test_query_categories(self):
        client = Client()
        r = client.get('/api/v1/audit-categories', HTTP_AUTHORIZATION=self.generateToken)
        self.assertEqual(r.status_code, 200)

    def test_move_audit(self):
        client = Client()
        r = client.post(
            '/api/v1/audit-categories/cost/actions/move',
            json.dumps({'category': 'law'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken)
        self.assertEqual(r.status_code, 200)

        c = Configuration.objects.get(key='audits')
        for audit in c.value['audits']:
            if audit['subtype'] == 'cost':
                self.assertEqual(audit['category'], 'law')

    def test_disable_audit(self):
        client = Client()
        r = client.post(
            '/api/v1/audit-categories/cost/actions/disable',
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken)
        self.assertEqual(r.status_code, 200)

        c = Configuration.objects.get(key='audits')
        for audit in c.value['audits']:
            if audit['subtype'] == 'cost':
                self.assertEqual(audit['enabled'], False)

    def test_enable_audit(self):
        client = Client()
        r = client.post(
            '/api/v1/audit-categories/cost/actions/disable',
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken)
        self.assertEqual(r.status_code, 200)

        c = Configuration.objects.get(key='audits')
        for audit in c.value['audits']:
            if audit['subtype'] == 'cost':
                self.assertEqual(audit['enabled'], False)

        r = client.post(
            '/api/v1/audit-categories/cost/actions/enable',
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken)
        self.assertEqual(r.status_code, 200)

        c = Configuration.objects.get(key='audits')
        for audit in c.value['audits']:
            if audit['subtype'] == 'cost':
                self.assertEqual(audit['enabled'], True)

    def assert_config_steps(self, config, expected):
        steps = AuditActivityConfigStep.objects.filter(config=config)
        actual = [{
            'dep': getattr(s.assigneeDepartment, 'code', None),
            'pos': getattr(s.assigneePosition, 'code', None),
            'position': s.position
        } for s in steps]
        self.assertListEqual(actual, expected)

    def _create_audit_flow(self):
        count = AuditActivityConfig.objects \
            .filter(subtype='cost', archived=False, fallback=False) \
            .count()

        client = Client()
        r = client.post(
            '/api/v1/audit-categories/cost/actions/create-flow',
            json.dumps({
                'conditions': [{'prop': 'amount', 'condition': 'lte', 'value': 2000}],
                'steps': [
                    {'dep': None, 'pos': self.pos_pk('owner')},
                    {'dep': self.dep_pk('fin'), 'pos': self.pos_pk('owner')},
                    {'dep': self.dep_pk('root'), 'pos': self.pos_pk('ceo')}
                ]
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken
        )
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))

        config = AuditActivityConfig.objects.get(pk=result['id'])
        self.assert_config_steps(config, [
            {'dep': None, 'pos': 'owner', 'position': 0},
            {'dep': 'fin', 'pos': 'owner', 'position': 1},
            {'dep': 'root', 'pos': 'ceo', 'position': 2},
        ])
        self.assertEqual(config.priority, count + 1)
        return config

    def test_create_audit_flow(self):
        self._create_audit_flow()

    def test_update_audit_flow(self):
        config = self._create_audit_flow()

        client = Client()
        r = client.post(
            '/api/v1/audit-categories/cost/actions/update-flow',
            json.dumps({
                'config': str(config.pk),
                'conditions': [{'prop': 'amount', 'condition': 'lte', 'value': 4000}],
                'steps': [
                    {'dep': self.dep_pk('fin'), 'pos': self.pos_pk('owner')},
                    {'dep': self.dep_pk('root'), 'pos': self.pos_pk('ceo')}
                ]
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken
        )
        self.assertEqual(r.status_code, 200)

        config = AuditActivityConfig.objects.get(pk=config.pk)
        self.assert_config_steps(config, [
            {'dep': 'fin', 'pos': 'owner', 'position': 0},
            {'dep': 'root', 'pos': 'ceo', 'position': 1},
        ])
        self.assertListEqual(
            config.conditions,
            [{'prop': 'amount', 'condition': 'lte', 'value': 4000}]
        )

    def test_stick_audit_flow(self):
        config = self._create_audit_flow()
        config2 = self._create_audit_flow()
        config3 = self._create_audit_flow()

        client = Client()
        r = client.post(
            '/api/v1/audit-categories/cost/actions/stick-flow',
            json.dumps({'config': str(config3.pk)}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken
        )
        self.assertEqual(r.status_code, 200)

        config = AuditActivityConfig.objects.get(pk=config.pk)
        self.assertEqual(config.priority, 2)
        config2 = AuditActivityConfig.objects.get(pk=config2.pk)
        self.assertEqual(config2.priority, 3)
        config3 = AuditActivityConfig.objects.get(pk=config3.pk)
        self.assertEqual(config3.priority, 1)

    def test_query_category(self):
        config = self._create_audit_flow()

        client = Client()
        r = client.get(
            '/api/v1/audit-categories/cost',
            HTTP_AUTHORIZATION=self.generateToken
        )
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        configs = result['configs']
        self.assertEqual(len(configs), 1)

    def test_delete_audit_flow(self):
        config = self._create_audit_flow()
        config2 = self._create_audit_flow()
        config3 = self._create_audit_flow()

        client = Client()
        r = client.delete(
            '/api/v1/audit-categories/cost/actions/delete-flow',
            json.dumps({'config': str(config.pk)}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.generateToken
        )
        self.assertEqual(r.status_code, 200)

        config = AuditActivityConfig.objects.get(pk=config.pk)
        self.assertEqual(config.archived, True)
        config2 = AuditActivityConfig.objects.get(pk=config2.pk)
        self.assertEqual(config2.priority, 1)
        config3 = AuditActivityConfig.objects.get(pk=config3.pk)
        self.assertEqual(config3.priority, 2)
