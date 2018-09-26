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


def resolve_step(step):
    return {
        'pk': str(step.pk),
        'department': resolve_department(step.assigneeDepartment),
        'position': resolve_department(step.assigneePosition),
        'position': step.position
    }


def resolve_config(config):
    steps = AuditActivityConfigStep.objects.filter(config=config).order_by('position')

    return {
        'pk': str(config.pk),
        'priority': config.priority,
        'fallback': config.fallback,
        'conditions': config.conditions,
        'steps': [resolve_step(s) for s in steps]
    }


def updateCategoryUpdatedAt(subtype):
    configuration = Configuration.objects.get(key='audits')
    for audit in configuration['audit']:
        if audit['subtype'] == subtype:
            audit['updated_at'] = timezone.now()
    configuration.save()


@require_http_methods(['GET', 'DELETE'])
@validateToken
def category(request, subtype):
    if request.method == 'GET':
        configs = AuditActivityConfig.objects \
            .filter(subtype=subtype, archived=False) \
            .order_by('priority')
        return JsonResponse({
            'configs': [resolve_config(c) for c in configs]
        })
    elif request.method == 'DELETE':
        data = json.loads(request.body.decode('utf-8'))
        # delete config
        AuditActivityConfig.objects \
            .filter(pk=data['config']) \
            .update(archived=True)

        # update audit category updated_at
        updateCategoryUpdatedAt(subtype)

        # update priority
        configs = AuditActivityConfig.objects \
            .filter(subtype=subtype, archived=False) \
            .order_by('priority')
        for index, config in enumerate(configs):
            config.priority = index
            config.save()

        return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def updateAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))
    configId = data['config']
    steps = data['steps']
    conditions = data.get('conditions', None)

    with transaction.atomic():
        config = AuditActivityConfig.objects.get(pk=configId)
        config.conditions = conditions
        config.save()

        AuditActivityConfigStep.objects.filter(config=config).delete()
        for index, step in enumerate(steps):
            pos = Position.objects.get(pk=step['pos'])
            dep = step.get('dep', None)
            if dep != None:
                dep = Department.objects.get(pk=dep)

            AuditActivityConfigStep.objects.create(
                config=config,
                position=index + 1,
                assigneeDepartment=dep,
                assigneePosition=pos
            )

        updateCategoryUpdatedAt(config.subtype)

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def createAuditFlow(request, subtype):
    data = json.loads(request.body.decode('utf-8'))
    steps = data['steps']
    conditions = data.get('conditions', None)

    with transaction.atomic():
        config = AuditActivityConfig(subtype=subtype)
        config.conditions = conditions
        config.save()

        for index, step in enumerate(steps):
            pos = Position.objects.get(pk=step['pos'])
            dep = step.get('dep', None)
            if dep != None:
                dep = Department.objects.get(pk=dep)

            AuditActivityConfigStep.objects.create(
                config=config,
                position=index + 1,
                assigneeDepartment=dep,
                assigneePosition=pos
            )

        updateCategoryUpdatedAt(config.subtype)

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def stickAuditFlow(request):
    data = json.loads(request.body.decode('utf-8'))
    configId = data['config']

    with transaction.atomic():
        config = AuditActivityConfig.objects.get(pk=configId)
        config.priority = -1
        config.save()

        configs = AuditActivityConfig.objects \
            .filter(subtype=config.subtype, fallback=False, archived=False) \
            .order_by('priority')
        for index, config in enumerate(configs):
            config.priority = index + 1
            config.save()

        updateCategoryUpdatedAt(config.subtype)

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
