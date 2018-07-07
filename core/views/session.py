import json
import logging
import random
import uuid

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.cache import cache

from core.exception import catchException
from core.models import *
from core.auth import generateToken
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.session')


@require_http_methods(["POST"])
@transaction.atomic
def login(request):
    data = json.loads(request.body.decode('utf-8'))
    try:
        profile = Profile.objects.get(name=data['name'])
        if profile.user.check_password(data['password']) and \
                not profile.blocked:
            return JsonResponse({
                'token': generateToken(profile)
            })
        else:
            return JsonResponse({
                'errorId': 'unauthorized'
            }, status=401)
    except:
        logger.exception('fail to login')
        return JsonResponse({
            'errorId': 'unauthorized'
        }, status=401)


def generateCode():
    code = ''
    for i in range(4):
        code = code + str(random.randint(0, 9))
    return code


def checkCode(phone, code):
    codeCached = cache.get('code-{}'.format(phone))
    return codeCached == code


def cacheCode(phone, code):
    cache.set('code-{}'.format(phone), code, 60)


@require_http_methods(["POST"])
@transaction.atomic
def loginWithCode(request):
    data = json.loads(request.body.decode('utf-8'))
    try:
        profile = Profile.objects.get(phone=data['phone'])
        if checkCode(profile.phone, data['code']) and \
                not profile.blocked:
            return JsonResponse({
                'token': generateToken(profile)
            })
        else:
            return JsonResponse({
                'errorId': 'unauthorized'
            }, status=401)
    except:
        logger.exception('fail to login')
        return JsonResponse({
            'errorId': 'unauthorized'
        }, status=401)


@require_http_methods(["POST"])
@transaction.atomic
def sendCode(request):
    data = json.loads(request.body.decode('utf-8'))
    # TODO: call http api to send code
    cacheCode(data['phone'], generateCode())
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
@transaction.atomic
@validateToken
def profile(request):
    profile = request.profile
    return JsonResponse(resolve_profile(profile))
