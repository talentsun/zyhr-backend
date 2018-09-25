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
