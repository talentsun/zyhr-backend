import json
from django.test import TestCase
from django.test import Client

from core import specs
from core.models import *
from core.auth import generateToken
from core.tests import helpers
from core.views.auditExport import convertToDaxieAmountV2


class AuditExportTestCase(TestCase):

    def test_convert_to_daxie(self):
        result = convertToDaxieAmountV2(1000)
        print(result)