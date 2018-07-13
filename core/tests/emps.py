import json
from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import generateToken
from core.tests import helpers


class EmpsTestCase(TestCase):
    def setUp(self):
        self.profile = helpers.prepareProfile('root', 'root', '13333333333')
        self.generateToken = generateToken(self.profile)

    def test_query_emps(self):
        p1 = helpers.prepareProfile('p1', 'p1', '18800000001')
        p2 = helpers.prepareProfile('p2', 'p2', '18800000002')
        p3 = helpers.prepareProfile('p3', 'p3', '18800000003')

        client = Client()
        response = client.get('/api/v1/emps?start=1&limit=1',
                              HTTP_AUTHORIZATION=self.generateToken)
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 4)
        self.assertEqual(len(result['emps']), 1)
        emp = result['emps'][0]
        self.assertEqual(emp['name'], 'p2')

    def test_create_emp(self):
        dep = Department.objects.create(code='dep', name='dep')
        pos = Position.objects.create(name='pos')

        client = Client()
        response = client.post('/api/v1/emps',
                               json.dumps({
                                   'name': 'foobar',
                                   'department': str(dep.pk),
                                   'position': str(pos.pk),
                                   'phone': '18888888888',
                                   'password': '123456',
                                   'desc': 'hello'
                               }),
                               content_type='application/json',
                               HTTP_AUTHORIZATION=self.generateToken)

        self.assertEquals(response.status_code, 200)
        profile = Profile.objects.get(name='foobar')
        self.assertEqual(profile.phone, '18888888888')

    def test_delete_emp(self):
        client = Client()
        response = client.delete('/api/v1/emps/{}'.format(self.profile.pk),
                                 HTTP_AUTHORIZATION=self.generateToken)

        self.assertEquals(response.status_code, 200)
        count = Profile.objects.filter(archived=False).count()
        self.assertEqual(count, 0)

    def test_modify_emp(self):
        client = Client()
        response = client.put('/api/v1/emps/{}'.format(self.profile.pk),
                              json.dumps({
                                  'phone': '10000000000'
                              }),
                              content_type='application/json',
                              HTTP_AUTHORIZATION=self.generateToken)

        self.assertEquals(response.status_code, 200)
        profile = Profile.objects.get(pk=self.profile.pk)
        self.assertEqual(profile.phone, '10000000000')

    def test_create_emp_with_same_name(self):
        jack = helpers.prepareProfile('jack', 'jack', '18800000001')
        dep = Department.objects.create(code='dep', name='dep')
        pos = Position.objects.create(name='pos')

        client = Client()
        response = client.post('/api/v1/emps',
                               json.dumps({
                                   'name': 'jack',
                                   'department': str(dep.pk),
                                   'position': str(pos.pk),
                                   'phone': '18888888888',
                                   'password': '123456',
                                   'desc': 'hello'
                               }),
                               content_type='application/json',
                               HTTP_AUTHORIZATION=self.generateToken)

        self.assertEquals(response.status_code, 200)
        profile = Profile.objects.get(name='jack1')
        self.assertEqual(profile.phone, '18888888888')
