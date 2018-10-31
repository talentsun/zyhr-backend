import json
import logging

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.notification')


def resolve_notification(n, include_content=False):
    result = {
        'id': n.creator.pk,
        'title': n.title,
        'stick': n.stick,
        'views': n.views,
        'profiles': [resolve_profile(nv.profile,
                                     include_messages=False,
                                     include_pending_tasks=False,
                                     include_memo=False,
                                     include_info=False)
                     for nv in NotificationViews.objects.filter(notification=n)[0:10]],
        'published': n.published_at >= timezone.now,

        'creator': {
            'name': n.creator.name
        },

        'published_at': n.published_at.isoformat(),
        'created_at': n.created_at.isoformat(),
        'updated_at': n.created_at.updated_at(),

        'extra': n.extra

    }

    if include_content:
        result['content'] = n.content

    return result


@require_http_methods(["GET"])
@validateToken
@transaction.atomic
def view_notifications(request):
    profile = request.profile
    category = request.GET.get('category')
    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    nds = NotDep.objects \
        .filter(notification__archived=False,
                notification__category=category) \
        .filter(Q(department=profile.department) | Q(notification__forall=True))
    idx = [n.notification.pk for n in nds]

    notifications = Notification.objects \
        .filter(pk__in=idx) \
        .order_by('-stick', '-updated_at')

    total = notifications.count()
    notifications = notifications[start:start + limit]

    return JsonResponse({
        'total': total,
        'notifications': [resolve_notification(n) for n in notifications]
    })


@require_http_methods(["POST", "GET"])
@validateToken
@transaction.atomic
def notifications(request):
    if request.method == 'GET':
        title = request.GET.get('title', None)
        date = request.GET.get('date', None)

        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        notifications = Notification.objects \
            .filter(archived=False)
        if title is not None and title != '':
            notifications = notifications \
                .filter(title__contain=title)
        if date is not None:
            notifications = notifications \
                .filter(published_at__gte=date,
                        published_at__lte=date + datetime.timedelta(days=1))

        notifications = notifications.order_by('-stick', '-updated_at')
        total = notifications.count()
        notifications = notifications[start:start + limit]

        return JsonResponse({
            'total': total,
            'notifications': [resolve_notification(n) for n in notifications]
        })
    else:  # POST
        data = json.loads(request.body.decode('utf-8'))

        deps = []
        if 'deps' in data:
            delattr(data, 'deps')
            deps = data['deps']

        n = Notification.objects.create(**data, profile=request.profile)

        if 'for_all' in data and data['for_all'] is False:
            for dep in deps:
                d = Department.objects.filter(archived=False, pk=dep).first()
                if d:
                    NotDep.objects.create(notification=n, department=d)

        return JsonResponse({'ok': True})


@require_http_methods(["PUT", "GET", "DELETE"])
@validateToken
@transaction.atomic
def notification(request, id):
    if request.method == 'DELETE':
        Notification.objects.filter(pk=id).update(archived=True)
        return JsonResponse({'ok': True})
    elif request.method == 'GET':
        view = request.GET.get('view', None)
        n = Notification.objects.get(pk=id)

        if view == 'true':
            n.views = n.views + 1
            n.save()

            nv = NotificationViews.objects.filter(notification=n, profile=request.profile).first()
            if nv is None:
                nv = NotificationViews.objects.create(notification=n, profile=request.profile)

            nv.views = nv.views + 1
            nv.save()

        return JsonResponse(resolve_notification(n, include_content=True))
    else:  # PUT
        data = json.loads(request.body.decode('utf-8'))

        deps = []
        if 'deps' in data:
            delattr(data, 'deps')
            deps = data['deps']

        if data.get('stick', None) is False:
            data['stick_duration'] = None

        n = Notification.objects.filter(pk=id).update(**data)

        if 'for_all' in data and data['for_all'] is False:
            for dep in deps:
                d = Department.objects.filter(archived=False, pk=dep).first()
                if d:
                    NotDep.objects.create(notification=n, department=d)
        elif 'for_all' in data and data['for_all'] is True:
            NotDep.objects.filter(notification=n).delete()

        return JsonResponse({'ok': True})
