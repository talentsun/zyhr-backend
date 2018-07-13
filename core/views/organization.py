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


@require_http_methods(['GET'])
@validateToken
def departments(request):
    deps = Department.objects.all()
    return JsonResponse({
        'departments': [resolve_department(d) for d in deps]
    })


@require_http_methods(['GET'])
@validateToken
def positions(request):
    positions = Position.objects.all()
    return JsonResponse({
        'positions': [resolve_position(p) for p in positions]
    })
