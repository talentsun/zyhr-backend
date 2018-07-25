import json
import logging
import random

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache

from core.auth import generateToken
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.session')


@require_http_methods(["POST"])
@transaction.atomic
def markRead(request, messageId):
    Message.objects\
        .filter(pk=messageId)\
        .update(read=True)
    return JsonResponse({'ok': True})
