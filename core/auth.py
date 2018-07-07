import logging
from django.http import JsonResponse
from django.core.cache import cache

from core.models import *

logger = logging.getLogger('app.core.auth')


def validateToken(fn):
    def wrapper(request, *args, **kwargs):
        token = request.META.get('HTTP_AUTHORIZATION', None)
        if not token:
            return JsonResponse({
                'errorId': 'unauthorized'
            }, status=401)

        try:
            profileId = cache.get('token-' + token)
            profile = Profile.objects.get(pk=profileId)
            request.profile = profile
        except:
            logger.exception("Token is invalid")
            return JsonResponse({
                'errorId': 'unauthorized'
            }, status=401)

        return fn(request, *args, **kwargs)

    return wrapper


def generateToken(profile):
    token = str(uuid.uuid4())
    cache.set('token-' + token, profile.pk, 3600 * 24 * 7)
    return token
