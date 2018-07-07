import logging

from django.contrib.auth.models import *
from django.http import JsonResponse

logger = logging.getLogger('app.core.catchException')


def catchException(fn):
    def wrapper(request, *args, **kwargs):

        try:
            return fn(request, *args, **kwargs)
        except:
            logger.exception('internal-server-error')
            return JsonResponse({
                'errorId': 'internal-server-error'
            }, status=500)

    return wrapper
