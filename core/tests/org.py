import json
import uuid

from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import *
from core.tests import helpers

from core.tests.audit_v3 import AuditV3TestCase


class OrgTestCase(AuditV3TestCase):
    def test_create_org(self):
        self.prepareData()
        self.prepareAuditConfig()
