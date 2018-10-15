import json
import uuid

from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import *
from core.tests import helpers

from core.tests.audit_test_mixin import AuditTestMixin


class OrgTestCase(TestCase, AuditTestMixin):
    def test_create_org(self):
        self.prepareData()
        self.prepareAuditConfig()

        # invalid name
        token = generateToken(self.jack)
        client = Client()
        r = client.post('/api/v1/departments',
                        json.dumps({
                            'parent': None,
                            'name': ''
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-parameters')

        # invalid parent
        r = client.post('/api/v1/departments',
                        json.dumps({
                            'parent': str(uuid.uuid4()),
                            'name': 'foobar'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'parent-not-found')

        r = client.post('/api/v1/departments',
                        json.dumps({
                            'parent': None,
                            'name': 'foobar'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)

        dep = Department.objects.get(name='foobar')
        root = Department.objects.get(name='root')
        self.assertEqual(dep.parent, root)

    def test_create_department_with_same_name(self):
        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()
        r = client.post('/api/v1/departments',
                        json.dumps({
                            'parent': None,
                            'name': 'biz'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'department-name-duplicate')

    def test_update_department(self):
        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()
        r = client.put('/api/v1/departments/{}'.format(str(self.biz.pk)),
                       json.dumps({
                           'parent': None,
                           'name': 'biz2'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        self.biz = Department.objects.get(pk=self.biz.pk)
        self.assertEqual(self.biz.name, 'biz2')

    def test_update_department_cycle(self):
        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()

        r = client.put('/api/v1/departments/{}'.format(str(self.biz.pk)),
                       json.dumps({
                           'parent': str(self.biz.pk),
                           'name': 'biz'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'parent-cycle')

        r = client.post('/api/v1/departments',
                        json.dumps({
                            'parent': str(self.biz.pk),
                            'name': 'biz-child'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        biz_child = Department.objects.get(name='biz-child')
        r = client.put('/api/v1/departments/{}'.format(str(self.biz.pk)),
                       json.dumps({
                           'parent': str(biz_child.pk),
                           'name': 'biz'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'parent-cycle')

    def test_delete_department_with_profiles(self):
        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()

        r = client.delete('/api/v1/departments/{}'.format(str(self.biz.pk)),
                          HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'profiles-exist')

    def test_delete_department(self):
        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()

        Profile.objects.filter(department=self.biz).update(archived=True)
        r = client.delete('/api/v1/departments/{}'.format(str(self.biz.pk)),
                          HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        self.biz = Department.objects.get(pk=self.biz.pk)
        self.assertEqual(self.biz.archived, True)

    def test_check_audit_on_department_delete(self):
        """
        部门被删除的时候，应该检查审批配置，将流程当中包含该部门的审批配置标记为异常状态
        """

        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()

        Profile.objects.filter(department=self.fin).update(archived=True)
        r = client.delete('/api/v1/departments/{}'.format(str(self.fin.pk)),
                          HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        self.fin = Department.objects.get(pk=self.fin.pk)
        self.assertEqual(self.fin.archived, True)

        config = AuditActivityConfig.objects.get(subtype='baoxiao', fallback=True)
        self.assertEqual(config.abnormal, True)
        step = AuditActivityConfigStep.objects.filter(config=config)[1]
        self.assertEqual(step.abnormal, True)

    def _create_position(self):
        token = generateToken(self.jack)
        client = Client()
        r = client.post('/api/v1/positions',
                        json.dumps({
                            'departments': [str(self.biz.pk), str(self.fin.pk)],
                            'name': 'foobar'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)

        position = Position.objects.get(name='foobar')
        deps = [d.dep.pk for d in DepPos.objects.filter(pos=position)]
        self.assertSetEqual(set(deps), set([self.biz.pk, self.fin.pk]))

    def test_create_position(self):
        self.prepareData()
        self.prepareAuditConfig()
        self._create_position()

    def test_update_position_with_profile_exists(self):
        """
        如果职位和部门的关系被修改，但是还存在部门和职位下有员工，那么更新功能应该失败
        """
        self.prepareData()
        self.prepareAuditConfig()

        token = generateToken(self.jack)
        client = Client()
        r = client.put('/api/v1/positions/{}'.format(self.pos_accountant.pk),
                       json.dumps({
                           'departments': [str(self.biz.pk)],
                           'name': 'foobar2'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 400)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'profiles-exist')

    def test_update_position(self):
        """
        如果部门和职位的关系被修改，那么应该检查是否有审批配置受到了影响
        如果部门和职位的关系恢复了，那么被标记异常的审批需要重置异常标记
        """
        self.prepareData()
        self.prepareAuditConfig()

        Profile.objects.filter(position=self.pos_accountant).update(archived=True)
        token = generateToken(self.jack)
        client = Client()
        r = client.put('/api/v1/positions/{}'.format(self.pos_accountant.pk),
                       json.dumps({
                           'departments': [str(self.biz.pk)],
                           'name': 'foobar2'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)
        self.assertEqual(r.status_code, 200)

        pos = Position.objects.get(pk=self.pos_accountant.pk)
        self.assertEqual(pos.name, 'foobar2')
        deps = [i.dep.pk for i in DepPos.objects.filter(pos=pos)]
        self.assertSetEqual(set(deps), set([self.biz.pk]))

        configs = AuditActivityConfig.objects.filter(subtype='baoxiao')
        for config in configs:
            self.assertEqual(config.abnormal, True)

        # 修改职位，恢复和原来部门之间的关联
        r = client.put('/api/v1/positions/{}'.format(self.pos_accountant.pk),
                       json.dumps({
                           'departments': [str(self.biz.pk), str(self.fin.pk)],
                           'name': 'foobar'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        pos = Position.objects.get(pk=self.pos_accountant.pk)
        self.assertEqual(pos.name, 'foobar')
        deps = [i.dep.pk for i in DepPos.objects.filter(pos=pos)]
        self.assertSetEqual(set(deps), set([self.biz.pk, self.fin.pk]))

        configs = AuditActivityConfig.objects.filter(subtype='baoxiao')
        for config in configs:
            self.assertEqual(config.abnormal, False)

    def test_archive_position(self):
        """
        如果要删除的职位下，还有正常状态的用户，那么删除操作应该失败

        如果职位被删除
        1. 职位和部门之间的关联也应该删掉
        2. 同时应该检查哪些审批受到影响
        """
        self.prepareData()
        self.prepareAuditConfig()

        client = Client()
        token = generateToken(self.jack)

        r = client.delete('/api/v1/positions/{}'.format(self.pos_accountant.pk),
                          content_type='application/json',
                          HTTP_AUTHORIZATION=token)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'profiles-exist')
        self.assertEqual(r.status_code, 400)

        Profile.objects.filter(position=self.pos_accountant).update(archived=True)
        r = client.delete('/api/v1/positions/{}'.format(self.pos_accountant.pk),
                          content_type='application/json',
                          HTTP_AUTHORIZATION=token)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)
        self.assertEqual(r.status_code, 200)

        pos = Position.objects.get(pk=self.pos_accountant.pk)
        deps = [i.dep.pk for i in DepPos.objects.filter(pos=pos)]
        self.assertSetEqual(set(deps), set())

        configs = AuditActivityConfig.objects.filter(subtype='baoxiao')
        for config in configs:
            self.assertEqual(config.abnormal, True)
