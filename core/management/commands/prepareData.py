from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from core.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        departments = [{
            'code': 'root',
            'name': 'root'
        }, {
            'code': 'dazong',
            'name': '大宗事业部'
        }, {
            'code': 'dichan',
            'name': '地产事业部'
        }, {
            'code': 'jinrong',
            'name': '金融事业部'
        }, {
            'code': 'caiwu',
            'name': '财务中心'
        }, {
            'code': 'hr',
            'name': '人力行政中心'
        }]

    for d in departments:
        Department.objects.get_or_create(code=d['code'],
                                         defaults=d)
