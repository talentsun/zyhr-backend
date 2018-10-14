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


def updateCategoryUpdatedAt(subtype):
    configuration = Configuration.objects.get(key='audits')
    for audit in configuration.value['audits']:
        if audit['subtype'] == subtype:
            audit['updated_at'] = timezone.now()
    configuration.save()


@require_http_methods(['GET'])
@validateToken
def category(request, subtype):
    configs = AuditActivityConfig.objects \
        .filter(subtype=subtype, archived=False) \
        .order_by('priority')
    return JsonResponse({
        'configs': [resolve_config(c) for c in configs]
    })


def check_steps(steps):
    for index, step in enumerate(steps):
        pos = step.get('pos', None)
        dep = step.get('dep', None)
        if dep is None:
            continue

        dep = Department.objects.get(pk=dep)
        pos = Position.objects.get(pk=pos)

        if dep.archived or pos.archived:
            return False, index, step

        if DepPos.objects.filter(dep=dep, pos=pos).count() == 0:
            return False, index, step

    return True, None, None


def reset_steps(config, steps):
    AuditActivityConfigStep.objects.filter(config=config).delete()
    for index, step in enumerate(steps):
        pos = None
        dep = step.get('dep', None)
        if dep != None:
            dep = Department.objects.get(pk=dep)
            pos = Position.objects.get(pk=step['pos'])

        AuditActivityConfigStep.objects.create(
            config=config,
            position=index,
            assigneeDepartment=dep,
            assigneePosition=pos
        )


@require_http_methods(['POST'])
@validateToken
def updateAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))
    configId = data['config']
    steps = data['steps']
    conditions = data.get('conditions', None)

    with transaction.atomic():
        valid, idx, step = check_steps(steps)
        if not valid:
            return JsonResponse({
                'errorId': 'some-step-abnormal',
                'step': step,
                'index': idx
            }, status=400)

        config = AuditActivityConfig.objects.get(pk=configId)
        config.conditions = conditions
        config.abnormal = False
        config.save()

        reset_steps(config, steps)
        updateCategoryUpdatedAt(config.subtype)

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def getAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))
    configId = data['config']
    config = AuditActivityConfig.objects.get(pk=configId)
    return JsonResponse(resolve_config(config))


@require_http_methods(['POST'])
@validateToken
def updateFallbackAuditFlow(request, subtype):
    configData = json.loads(request.body.decode('utf-8'))
    with transaction.atomic():
        config = AuditActivityConfig.objects \
            .filter(subtype=subtype, archived=False, fallback=True) \
            .first()

        if config is None:
            config = AuditActivityConfig(subtype=subtype, fallback=True, priority=0)

        config.save()
        reset_steps(config, configData['steps'])

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def createAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))
    steps = data['steps']
    conditions = data.get('conditions', None)

    with transaction.atomic():
        valid, idx, step = check_steps(steps)
        if not valid:
            return JsonResponse({
                'errorId': 'some-step-abnormal',
                'step': step,
                'index': idx
            }, status=400)

        count = AuditActivityConfig.objects \
            .filter(subtype=subtype, archived=False, fallback=False) \
            .count()
        config = AuditActivityConfig(subtype=subtype)
        config.conditions = conditions
        config.priority = count + 1
        config.save()

        reset_steps(config, steps)
        updateCategoryUpdatedAt(config.subtype)

    return JsonResponse({'ok': True, 'id': str(config.pk)})


@require_http_methods(['POST'])
@validateToken
def deleteAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))

    with transaction.atomic():
        # delete config
        AuditActivityConfig.objects \
            .filter(pk=data['config']) \
            .update(archived=True)

        # update audit category updated_at
        updateCategoryUpdatedAt(subtype)

        # update priority
        configs = AuditActivityConfig.objects \
            .filter(subtype=subtype, archived=False, fallback=False) \
            .order_by('priority')
        for index, config in enumerate(configs):
            config.priority = index + 1
            config.save()

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def stickAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))
    configId = data['config']

    with transaction.atomic():
        config = AuditActivityConfig.objects.get(pk=configId)
        config.priority = -1
        config.save()

        configs = AuditActivityConfig.objects \
            .filter(subtype=subtype, fallback=False, archived=False) \
            .order_by('priority')
        for index, config in enumerate(configs):
            config.priority = index + 1
            config.save()

        updateCategoryUpdatedAt(subtype)

    return JsonResponse({'ok': True})


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
