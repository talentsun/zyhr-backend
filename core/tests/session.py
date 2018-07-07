import json
from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import generateToken
from core.views import session
from core.tests import helpers


class SessionTestCase(TestCase):
    def setUp(self):
        self.profile = helpers.prepareProfile('张三', 'root', '18888888888')
        self.generateToken = generateToken(self.profile)

    def test_login(self):
        client = Client()
        response = client.post(
            '/api/v1/login',
            json.dumps({
                'name': '张三',
                'password': 'root'
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(result['token'] is not None)

    def test_profile_blocked(self):
        self.profile.blocked = True
        self.profile.save()

        client = Client()
        response = client.post(
            '/api/v1/login',
            json.dumps({
                'name': '张三',
                'password': 'root'
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_profile_not_found(self):
        client = Client()
        response = client.post(
            '/api/v1/login',
            json.dumps({
                'name': 'Lee',
                'password': 'root'
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_login_with_code(self):
        code = session.generateCode()
        session.cacheCode(self.profile.phone, code)

        client = Client()
        response = client.post(
            '/api/v1/login-with-code',
            json.dumps({
                'phone': self.profile.phone,
                'code': code
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)

        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(result['token'] is not None)

    def test_login_with_code_proile_blocked(self):
        self.profile.blocked = True
        self.profile.save()

        code = session.generateCode()
        session.cacheCode(self.profile.phone, code)

        client = Client()
        response = client.post(
            '/api/v1/login-with-code',
            json.dumps({
                'phone': self.profile.phone,
                'code': code
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_login_with_code_proile_not_found(self):
        self.profile.blocked = True
        self.profile.save()

        code = session.generateCode()
        phone = '16666666666'
        session.cacheCode(phone, code)

        client = Client()
        response = client.post(
            '/api/v1/login-with-code',
            json.dumps({
                'phone': phone,
                'code': code
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_get_profile(self):
        client = Client()
        response = client.post(
            '/api/v1/login',
            json.dumps({
                'name': self.profile.name,
                'password': 'root'
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        token = result['token']

        response = client.get(
            '/api/v1/profile',
            content_type='application/json',
            HTTP_AUTHORIZATION=token)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['name'], self.profile.name)
