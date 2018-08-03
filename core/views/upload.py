import re
import logging
import uuid
import qiniu
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile

from core.exception import catchException
from core.models import *
from core.auth import validateToken
from core.common import *


logger = logging.getLogger('app.core.views.upload')


@require_http_methods(["POST"])
@validateToken
@catchException
@transaction.atomic
def upload(request):
    f = request.FILES.get('file', None)
    if f is None:
        return JsonResponse({
            'errorId': 'invalid-parameters',
            'errorMsg': 'File is empty'
        }, status=400)

    path = str(uuid.uuid4())
    file = File.objects.create(path=path, name=f.name, size=f.size)

    filepath = '{}/{}'.format(settings.DATA_DIR, file.path)
    with open(filepath, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    return JsonResponse({
        'id': file.pk,
        'url': 'http://{}/api/v1/assets/{}'.format(settings.HOST, path),
        'name': file.name,
        'size': file.size
    })


@require_http_methods(["GET"])
def assets(request, path):
    file = File.objects.get(path=path)
    response = sendfile(request,
                        '{}/{}'.format(settings.DATA_DIR, file.path))
    # response['Content-Disposition'] = "inline; filename={}".format(file.name)
    del response['Content-Disposition']

    if re.match('.*\.(jpg|jpeg)', file.name):
        response['Content-Type'] = 'image/jpeg'
    if re.match('.*\.png', file.name):
        response['Content-Type'] = 'image/png'
    if re.match('.*\.pdf', file.name):
        response['Content-Type'] = 'application/pdf'
    return response
