import os
import re
import json
import logging
import datetime
from collections import Iterable

import iso8601
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile

from core.models import *
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.auditConfig')


@require_http_methods(['GET'])
@validateToken
def categories(request):
    config = Configuration.objects.get(key='audits')
    data = config.value
    for audit in data['audits']:
        config = AuditActivityConfig.objects \
            .filter(subtype=audit['subtype']) \
            .order_by('priority') \
            .first()

        if config == None:
            continue

        steps = AuditActivityConfigStep.objects.filter(config=config)
        steps = [{
            'dep': getattr(s.assigneeDepartment, 'name', None),
            'pos': getattr(s.assigneePosition, 'name', None)
        } for s in steps]
        audit['flow'] = steps

    audits = data['audits']
    audits = sorted(audits, key=lambda audit: audit.get('updated_at', ''))
    audits.reverse()
    data['audits'] = audits

    return JsonResponse(data)


@require_http_methods(['POST'])
@validateToken
def disableAudit(request, subtype):
    config = Configuration.objects.get(key='audits')
    data = config.value
    for audit in data['audits']:
        if audit['subtype'] == subtype:
            audit['enabled'] = False
            audit['updated_at'] = timezone.now()

    config.value = data
    config.save()
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def enableAudit(request, subtype):
    config = Configuration.objects.get(key='audits')
    data = config.value
    for audit in data['audits']:
        if audit['subtype'] == subtype:
            audit['enabled'] = True
            audit['updated_at'] = timezone.now()

    config.value = data
    config.save()
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def moveAudit(request, subtype):
    config = Configuration.objects.get(key='audits')
    category = json.loads(request.body.decode('utf-8'))['category']

    data = config.value
    for audit in data['audits']:
        if audit['subtype'] == subtype:
            audit['category'] = category
            audit['updated_at'] = timezone.now()

    config.value = data
    config.save()
    return JsonResponse({'ok': True})
