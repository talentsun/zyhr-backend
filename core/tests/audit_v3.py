import json
from django.test import TestCase
from django.test import Client

from core import specs
from core.models import *
from core.auth import generateToken
from core.tests import helpers


class AuditV3TestCase(TestCase):
    def setUp(self):
        pass
