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
        'id': n.pk,
        'no': n.no,
        'title': n.title,
        'category': n.category,
        'stick': n.stick,
        'stick_duration': n.stick_duration,
        'views': n.views,
        'profiles': [resolve_profile(nv.profile,
                                     include_messages=False,
                                     include_pending_tasks=False,
                                     include_memo=False,
                                     include_info=False)
                     for nv in NotificationViews.objects.filter(notification=n)],
        'published': n.published_at <= timezone.now(),

        'creator': {
            'name': n.creator.name
        },
        'department': {
            'id': str(n.department.pk),
            'archived': n.department.archived,
            'name': n.department.name
        } if n.department else None,

        'published_at': n.published_at.isoformat(),
        'created_at': n.created_at.isoformat(),
        'updated_at': n.updated_at.isoformat(),

        'extra': n.extra,
        'for_all': n.for_all,
        'scope': n.scope,
        'attachments': n.attachments
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

    if ',' in category:
        category = category.split(',')
    else:
        category = [category]

    nds = NotDep.objects \
        .filter(notification__archived=False) \
        .filter(notification__category__in=category) \
        .filter(notification__published_at__lte=timezone.now()) \
        .filter(Q(department=profile.department) | Q(notification__for_all=True)) \
        .order_by('-notification__stick', '-notification__updated_at')

    total = nds.count()
    nds = nds[start:start + limit]

    return JsonResponse({
        'total': total,
        'notifications': [resolve_notification(nd.notification) for nd in nds]
    })


@require_http_methods(["POST", "GET"])
@validateToken
@transaction.atomic
def notifications(request):
    if request.method == 'GET':
        title = request.GET.get('title', None)
        category = request.GET.get('category')
        published = request.GET.get('published', None)

        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        notifications = Notification.objects.filter(archived=False, category=category)

        if title is not None and title != '':
            notifications = notifications.filter(title__contains=title)

        if published is not None and published != '':
            if published == 'true':
                notifications = notifications.filter(published_at__lte=timezone.now())
            else:
                notifications = notifications.filter(published_at__gt=timezone.now())

        notifications = notifications.order_by('-updated_at')
        total = notifications.count()
        notifications = notifications[start:start + limit]

        return JsonResponse({
            'total': total,
            'notifications': [resolve_notification(n) for n in notifications]
        })
    else:  # POST
        data = json.loads(request.body.decode('utf-8'))
        n = Notification.objects.create(**data, creator=request.profile, department=request.profile.department)
        generateNotDepByScope(n)

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

            nv.times = nv.times + 1
            nv.save()

        return JsonResponse(resolve_notification(n, include_content=True))
    else:  # PUT
        data = json.loads(request.body.decode('utf-8'))
        if data.get('stick', None) is False:
            data['stick_duration'] = None

        partial = {}
        props = ['title', 'content', 'stick', 'stick_duration', 'published_at',
                 'extra', 'attachments', 'scope', 'for_all']
        for prop in props:
            if prop in data:
                partial[prop] = data[prop]

        Notification.objects.filter(pk=id).update(**partial)
        n = Notification.objects.get(pk=id)
        generateNotDepByScope(n)

        return JsonResponse({'ok': True})
