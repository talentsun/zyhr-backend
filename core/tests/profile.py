import json
import uuid

from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import *
from core.tests import helpers
from core.tests.audit_test_mixin import AuditTestMixin


class ProfileTestCase(TestCase, AuditTestMixin):
    def test_query_profiles(self):
        self.prepareData()

        client = Client()
        token = generateToken(self.jack)
        r = client.get('/api/v1/profiles?start=0&limit=1', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 5)
        self.assertEqual(len(result['profiles']), 1)

        r = client.get('/api/v1/profiles?start=0&limit=1&name=neo', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['profiles']), 1)

        r = client.get('/api/v1/profiles?start=0&limit=1&department={}&position={}' \
                       .format(str(self.fin.pk), str(self.pos_accountant.pk)),
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['profiles']), 1)

    def test_create_profile(self):
        self.prepareData()

        client = Client()
        token = generateToken(self.jack)
        r = client.post('/api/v1/profiles',
                        json.dumps({
                            'department': str(self.fin.pk),
                            'position': str(self.pos_accountant.pk),
                            'realname': 'neo'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        profile = Profile.objects.get(name='neo1')
        profileInfo = ProfileInfo.objects.get(profile=profile)
        self.assertEqual(profile.blocked, True)
        self.assertEqual(profileInfo.realname, 'neo')
        self.assertEqual(profileInfo.state, ProfileInfo.StateTesting)

    def test_delete_profile(self):
        self.prepareData()

        client = Client()
        token = generateToken(self.jack)
        r = client.delete('/api/v1/profiles/{}'.format(self.neo.pk),
                          HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        profile = Profile.objects.get(pk=self.neo.pk)
        self.assertEqual(profile.archived, True)
        self.assertEqual(profile.name, 'deleted-neo')
        profileInfo = ProfileInfo.objects.get(profile=profile)
        self.assertEqual(profileInfo.state, ProfileInfo.StateLeft)
        self.assertEqual(profileInfo.archived, True)

    def test_update_profile(self):
        self.prepareData()

        client = Client()
        token = generateToken(self.jack)
        r = client.put('/api/v1/profiles/{}'.format(self.neo.pk),
                       json.dumps({
                           'department': str(self.fin.pk),
                           'position': str(self.pos_accountant.pk),
                           'gender': 2,
                           'email': 'foobar@gmail.com'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        profile = Profile.objects.get(pk=self.neo.pk)
        self.assertEqual(profile.department.pk, self.fin.pk)
        self.assertEqual(profile.position.pk, self.pos_accountant.pk)
        self.assertEqual(profile.email, 'foobar@gmail.com')
        profileInfo = ProfileInfo.objects.get(profile=profile)
        self.assertEqual(profileInfo.gender, 2)

    def test_profile_left(self):
        self.prepareData()

        client = Client()
        token = generateToken(self.jack)
        r = client.put('/api/v1/profiles/{}'.format(self.neo.pk),
                       json.dumps({
                           'department': str(self.fin.pk),
                           'position': str(self.pos_accountant.pk),
                           'state': 'left'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        profile = Profile.objects.get(pk=self.neo.pk)
        profileInfo = ProfileInfo.objects.get(profile=self.neo)
        self.assertEqual(profile.blocked, True)
        self.assertEqual(profileInfo.state, ProfileInfo.StateLeft)

    def test_update_affected_activities(self):
        """
        当用户离职、所属部门职位变更、新入职用户时:
        1. 原来由于某些审批环节找不到负责人的异常审批，先重新找到了负责人，应该恢复
        2.a 受用户离职、职位变更影响的审批，应该更换审批人
        2.b 找不到审批人的审批，应该标记为异常状态，审批流程强制中断
        """

        self.prepareData()
        self.prepareAuditConfig()

        client = Client()
        token = generateToken(self.jack)

        # 创建报销审批
        r = client.post('/api/v1/audit-activities',
                        json.dumps({
                            'code': 'baoxiao',
                            'submit': True,
                            'extra': {
                                'amount': 2000
                            }
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        # 财务会计离职
        r = client.put('/api/v1/profiles/{}'.format(self.lucy.pk),
                       json.dumps({
                           'department': str(self.fin.pk),
                           'position': str(self.pos_accountant.pk),
                           'state': 'left'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        activity = AuditActivity.objects.filter(config__subtype='baoxiao').first()
        self.assertEqual(activity.state, AuditActivity.StateAborted)
        step = activity.steps()[1]
        self.assertEqual(step.abnormal, True)

        # 新财务会计入职，中断的审批应该恢复
        r = client.post('/api/v1/profiles',
                        json.dumps({
                            'department': str(self.fin.pk),
                            'position': str(self.pos_accountant.pk),
                            'realname': 'jacob'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        jacob = Profile.objects.get(name='jacob')

        activity = AuditActivity.objects.filter(config__subtype='baoxiao').first()
        self.assertEqual(activity.state, AuditActivity.StateProcessing)
        step = activity.steps()[1]
        self.assertEqual(step.abnormal, False)
        self.assertEqual(step.assignee.name, 'jacob')

        # 新财务会计入职
        r = client.post('/api/v1/profiles',
                        json.dumps({
                            'department': str(self.fin.pk),
                            'position': str(self.pos_accountant.pk),
                            'realname': 'fiber'
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        # jacob 离职，审批的负责人应该换成其他人
        r = client.put('/api/v1/profiles/{}'.format(jacob.pk),
                       json.dumps({
                           'department': str(self.fin.pk),
                           'position': str(self.pos_accountant.pk),
                           'state': 'left'
                       }),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        activity = AuditActivity.objects.filter(config__subtype='baoxiao').first()
        self.assertEqual(activity.state, AuditActivity.StateProcessing)
        step = activity.steps()[1]
        self.assertEqual(step.abnormal, False)
        self.assertEqual(step.assignee.name, 'fiber')
