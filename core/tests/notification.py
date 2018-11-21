import json
import uuid

from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import *
from core.tests import helpers
from core.management.commands.stats import Command
from core.tests.audit_test_mixin import AuditTestMixin

from freezegun import freeze_time


class NotificationTestCase(TestCase, AuditTestMixin):
    def _test_create_notification(self, creator, **params):
        token = generateToken(creator)

        client = Client()
        r = client.post('/api/v1/notifications',
                        json.dumps({
                            'title': 'hello world',
                            'content': 'foobar',
                            'category': 'tongzhi',
                            'scope': params.get('scope', None),
                            'for_all': params.get('for_all', True),
                            'stick': params.get('stick', False),
                            'stick_duration': params.get('stick_duration', None),
                            'published_at': timezone.now().isoformat()
                        }),
                        content_type='application/json',
                        HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)

    def test_create_notification(self):
        self.prepareData()
        self._test_create_notification(self.jack)

    def test_query_notifications(self):
        self.prepareData()
        self._test_create_notification(self.jack)

        token = generateToken(self.jack)
        client = Client()
        r = client.get('/api/v1/notifications?category=tongzhi', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['notifications']), 1)

    def test_query_notification(self):
        self.prepareData()
        self._test_create_notification(self.jack)

        n = Notification.objects.all().first()

        token = generateToken(self.jack)
        client = Client()
        r = client.get('/api/v1/notifications/{}'.format(n.pk), HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        r = client.get('/api/v1/notifications/{}?view=true'.format(n.pk), HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)

        n = Notification.objects.get(pk=n.pk)
        self.assertEqual(n.views, 1)

    def test_unstick_notification(self):
        with freeze_time('2018-01-01'):
            self.prepareData()
            self._test_create_notification(self.jack, stick=True, stick_duration='24')
            n = Notification.objects.all().first()
            self.assertEqual(n.stick, True)

        with freeze_time('2018-01-02'):
            AsyncTask.objects.create(category='unstick_notifications', exec_at=timezone.now(), data={})
            Command().handleAsyncTasks()
            n = Notification.objects.all().first()
            self.assertEqual(n.stick, False)
            self.assertEqual(n.stick_duration, None)

    def test_query_notifications_within_scope(self):
        self.prepareData()
        biz_1 = Department.objects.create(parent=self.biz, name='biz.1')
        biz_1_1 = Department.objects.create(parent=biz_1, name='biz.1.1')
        self._test_create_notification(self.jack, for_all=False, scope=[str(self.biz.pk), str(biz_1.pk)])

        n = Notification.objects.all().first()
        nds = NotDep.objects.filter(notification=n)
        self.assertEqual(nds.count(), 3)
        self.assertSetEqual(set([nd.department.pk for nd in nds]), set([self.biz.pk, biz_1.pk, biz_1_1.pk]))

        client = Client()
        token = generateToken(self.jack)
        r = client.get('/api/v1/view_notifications?category=tongzhi', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['notifications']), 1)

        token = generateToken(self.lucy)
        r = client.get('/api/v1/view_notifications?category=tongzhi', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 0)

        r = client.put('/api/v1/notifications/{}'.format(n.pk),
                       json.dumps({'scope': [str(biz_1.pk)]}),
                       content_type='application/json',
                       HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        nds = NotDep.objects.filter(notification=n)
        self.assertEqual(nds.count(), 2)
        self.assertSetEqual(set([nd.department.pk for nd in nds]), set([biz_1_1.pk, biz_1.pk]))

        token = generateToken(self.jack)
        r = client.get('/api/v1/view_notifications?category=tongzhi', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 0)
