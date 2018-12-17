import json
import uuid

from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import *
from core.tests import helpers


class RolesTestCase(TestCase):

    def setUp(self):
        self.profile = helpers.prepareProfile('root', 'root', '13333333333')
        self.token = generateToken(self.profile)

    def test_create_role(self):
        client = Client()
        response = client.post('/api/v1/roles',
                               json.dumps({
                                   'name': 'test',
                                   'extra': [
                                       P_V1_VIEW_EMP,
                                       P_V1_ADD_EMP,
                                       P_V1_MANAGE_EMP
                                   ]
                               }),
                               content_type='application/json',
                               HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        role = Role.objects.all()[0]
        self.assertEqual(role.name, 'test')
        self.assertListEqual(role.extra,
                             [P_V1_VIEW_EMP, P_V1_ADD_EMP, P_V1_MANAGE_EMP])

    # def test_create_role_with_invalid_permission(self):
    #     client = Client()
    #     response = client.post('/api/v1/roles',
    #                            json.dumps({
    #                                'name': 'test',
    #                                'extra': [
    #                                    'wtf'
    #                                ]
    #                            }),
    #                            content_type='application/json',
    #                            HTTP_AUTHORIZATION=self.token)
    #     self.assertEqual(response.status_code, 400)
    #     result = json.loads(response.content.decode('utf-8'))
    #     self.assertEqual(result['errorId'], 'invalid-permission')

    def test_query_roles(self):
        Role.objects.create(name='r1', extra={})
        Role.objects.create(name='r2', extra={})

        client = Client()
        response = client.get('/api/v1/roles?start=1',
                              HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)

        result = json.loads(response.content.decode('utf-8'))
        roles = result['roles']
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0]['name'], 'r2')

    def test_delete_role(self):
        role = Role.objects.create(name='r1', extra={})

        client = Client()
        response = client.delete('/api/v1/roles/{}'.format(str(role.pk)),
                                 HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        count = Role.objects.filter(archived=False).count()
        self.assertEqual(count, 0)

    def test_query_role_detail(self):
        role = Role.objects.create(name='r1', extra={})

        client = Client()
        response = client.get('/api/v1/roles/{}'.format(str(role.pk)),
                              HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['id'], str(role.pk))
        self.assertEqual(result['name'], 'r1')

    def test_query_role_not_exists(self):
        client = Client()
        roleId = uuid.uuid4()
        response = client.get('/api/v1/roles/{}'.format(str(roleId)),
                              HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result, None)

    def test_modify_role(self):
        role = Role.objects.create(name='r1', extra={})

        client = Client()
        response = client.put('/api/v1/roles/{}'.format(str(role.pk)),
                              json.dumps({
                                  'name': 'r1_modified'
                              }),
                              content_type='application/json',
                              HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        role = Role.objects.get(pk=str(role.pk))
        self.assertEqual(role.name, 'r1_modified')
