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
        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))
        profiles = Profile.objects \
            .filter(archived=False) \
            .order_by('-updated_at')
        total = profiles.count()
        profiles = profiles[start:start + limit]
        return JsonResponse({
            'total': total,
            'emps': [resolve_profile(p) for p in profiles]
        })
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))

        username = data['name']
        counter = 1
        while User.objects.filter(username=username).count() > 0:
            username = username + str(counter)
        user = User.objects.create(username=username)
        user.set_password(data['password'])
        user.save()

        role = data.get('role', None)
        if role is not None:
            try:
                role = Role.objects.get(pk=role)
            except:
                role = None

        department = Department.objects.get(pk=data['department'])
        position = Position.objects.get(pk=data['position'])
        Profile.objects.create(user=user,
                               name=username,
                               role=role,
                               department=department,
                               position=position,
                               phone=data['phone'],
                               desc=data.get('desc', None))
        return JsonResponse({'ok': True})


@require_http_methods(['DELETE', 'PUT', 'GET'])
@validateToken
@transaction.atomic
def detail(request, empId):
    if request.method == 'DELETE':
        profile = Profile.objects.get(pk=empId)
        Profile.objects \
            .filter(pk=empId) \
            .update(phone=None, archived=True, name='已删除-{}'.format(profile.name))
        return JsonResponse({'ok': True})
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        emp = None
        try:
            emp = Profile.objects.get(pk=empId)
        except:
            return JsonResponse({'errorId': 'emp-not-found'}, status=400)

        partial = {}
        for prop in ['department', 'position', 'phone', 'desc', 'role']:
            if data.get(prop, None) != None:
                partial[prop] = data.get(prop)
        partial['updated_at'] = timezone.now()
        Profile.objects.filter(pk=empId).update(**partial)
        if 'password' in prop:
            user = emp.user
            user.set_password(prop['password'])
            user.save()
        return JsonResponse({'ok': True})
    else:
        try:
            profile = Profile.objects.get(pk=empId)
        except:
            profile = None
        return JsonResponse(resolve_profile(profile))


@require_http_methods(['POST'])
@validateToken
def updateState(request, empId):
    data = json.loads(request.body.decode('utf-8'))
    Profile.objects.filter(pk=empId).update(blocked=data['blocked'])
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def updatePassword(request, empId):
    data = json.loads(request.body.decode('utf-8'))
    profile = Profile.objects.get(pk=empId)
    user = profile.user
    user.set_password(data['password'])
    user.save()
    return JsonResponse({'ok': True})
