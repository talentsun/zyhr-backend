import time
import logging

from django.http import JsonResponse

from core.common import *

logger = logging.getLogger('app.core.views.dev')


def trigger_stats(request):
    task = AsyncTask.objects.create(category='stats', exec_at=timezone.now(), data={})

    while not task.finished:
        task = AsyncTask.objects.get(pk=task.pk)
        time.sleep(1)

    return JsonResponse({'ok': True})

