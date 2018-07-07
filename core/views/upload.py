import logging
import uuid
import qiniu
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

from core.exception import catchException
from core.models import *
from core.auth import validateToken
from core.common import *


logger = logging.getLogger('app.core.views.upload')


@require_http_methods(["POST"])
@transaction.atomic
@catchException
def upload(request):
    f = request.FILES.get('file', None)
    if f is None:
        return JsonResponse({
            'errorId': 'invalid-parameters',
            'errorMsg': 'File is empty'
        }, status=400)

    q = qiniu.Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = q.upload_token(settings.QINIU_BUCKET)
    key = 'hauser-wirth/' + str(uuid.uuid4())
    ret, info = qiniu.put_data(token, key, f.read())

    if ret is not None:
        return JsonResponse({
            'url': 'http://{}/{}'.format(settings.QINIU_DOMAIN, key)
        })
    else:
        return JsonResponse({
            'errorId': 'upload-file-failed',
            'qiniu-error': info
        }, status=500)
