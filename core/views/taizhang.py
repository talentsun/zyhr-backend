from decimal import Decimal
import re
import json
import logging
import random
import pandas
import xlwt

from django.db import transaction
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.cache import cache
from sendfile import sendfile

from core.auth import generateToken
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.taizhang')


def resolve_taizhang(t):
    d = model_to_dict(t)
    return d


@require_http_methods(["GET", "DELETE"])
def taizhang(request):
    if request.method == 'GET':
        # number = request.GET.get('number', None)
        # date = request.GET.get('date', None)
        # other = request.GET.get('other', None)
        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        records = Taizhang.objects.filter(archived=False)
        # if number is not None and number != '':
        #     records = records.filter(number=number)
        # if date is not None and date != '':
        #     records = records.filter(date=date)
        # if other is not None and other != '':
        #     records = records.filter(other=other)

        records = records.order_by('-id')
        total = records.count()
        records = records[start:start + limit]
        return JsonResponse({
            'total': total,
            'records': [resolve_taizhang(r) for r in records]
        })
    else:
        # delete
        data = json.loads(request.body.decode('utf-8'))
        idx = data['idx']
        Taizhang.objects.filter(pk__in=idx).update(archived=True)
        return JsonResponse({
            'ok': True
        })


@require_http_methods(["PUT"])
@validateToken
def taizhangDetail(request, id):
    data = json.loads(request.body.decode('utf-8'))
    del data['id']
    if 'creator' in data:
        del data['creator']

    try:
        r = Taizhang.objects.get(pk=id)

        props = ['kaipiao_dunwei',
                 'upstream_jiesuan_price',
                 'kaipiao_dunwei_trade',
                 'downstream_jiesuan_price',
                 'shangyou_zijin_zhanya',
                 'shangyou_kuchun_liang',
                 'shangyou_kuchun_yuji_danjia']
        partial = {}
        modifiedProps = []
        for prop in props:
            value = getattr(r, prop, None)
            if value != data.get(prop, None):
                modifiedProps.append({'prop': prop, 'value': value})

            partial[prop] = data.get(prop, None)

        Taizhang.objects.filter(pk=id).update(**partial)

        r = Taizhang.objects.get(pk=id)
        for item in modifiedProps:
            prop, prev = item['prop'], item['value']
            TaizhangOps.objects.create(record=r,
                                       prop=prop,
                                       extra={
                                           'prev': prev,
                                           'cur': getattr(r, prop, None)
                                       },
                                       profile=request.profile,
                                       op='modify')
    except:
        logger.exception("fail to modify record")
        return JsonResponse({'errorId': 'internal-server-error'}, status=500)

    return JsonResponse({'ok': True})


def resolve_op(op):
    return {
        'id': op.pk,
        'profile': {
            'pk': str(op.profile.pk),
            'name': str(op.profile.name)
        },
        'record': resolve_taizhang(op.record),
        'prop': op.prop,
        'extra': op.extra,
        'created_at': op.created_at
    }


@require_http_methods(['GET'])
def ops(request):
    name = request.GET.get('name', None)
    other = request.GET.get('other', None)
    prop = request.GET.get('prop', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    ops = TaizhangOps.objects.filter(op='modify')

    if name is not None and name != '':
        ops = ops.filter(profile__name__contains=name)
    if other is not None and other != '':
        ops = ops.filter(record__other__contains=other)
    if prop is not None and prop != '':
        ops = ops.filter(prop=prop)

    total = ops.count()
    ops = ops[start:start + limit]
    return JsonResponse({
        'total': total,
        'ops': [resolve_op(op) for op in ops]
    })
