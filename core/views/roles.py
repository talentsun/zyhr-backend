import logging
import datetime
import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import *
from core.auth import validateToken
from core.common import *
from core.exception import *

logger = logging.getLogger('app.core.views.emps')


@require_http_methods(['GET', 'POST'])
@validateToken
@catchException
@transaction.atomic
def index(request):
    if request.method == 'GET':
        roles = Role.objects \
            .filter(archived=False) \
            .order_by('-updated_at')
        return JsonResponse({
            'roles': [resolve_role(r) for r in roles]
        })
    if request.method == 'POST':
        # TODO: check profile permission

        data = json.loads(request.body.decode('utf-8'))
        extra = data.get('extra', [])
        for item in extra:
            if item not in P_V1:
                return JsonResponse({
                    'errorId': 'invalid-permission'
                }, status=400)

        data = json.loads(request.body.decode('utf-8'))
        Role.objects.create(name=data['name'],
                            desc=data.get('desc', None),
                            extra=extra)
        return JsonResponse({'ok': True})


@require_http_methods(['DELETE', 'PUT', 'GET'])
@validateToken
def detail(request, roleId):
    if request.method == 'DELETE':
        role = Role.objects.filter(pk=roleId).first()
        if role is None:
            return JsonResponse({'ok': True})

        # delete profile's role if match
        Profile.objects.filter(role=role).update(role=None)

        Role.objects.filter(pk=roleId).update(archived=True)
        return JsonResponse({'ok': True})
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        partial = {}
        for prop in ['name', 'desc', 'extra']:
            if data.get(prop, None) != None:
                partial[prop] = data.get(prop)

        partial['updated_at'] = timezone.now()

        Role.objects.filter(pk=roleId).update(**partial)
        return JsonResponse({'ok': True})
    else:
        try:
            role = Role.objects.get(pk=roleId)
        except:
            role = None
        return JsonResponse(resolve_role(role), safe=False)
