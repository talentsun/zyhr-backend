from decimal import Decimal
import re
import json
import logging
import random
import pandas
import xlwt

from django.db import transaction
from django.db.models import Q
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
        asset = request.GET.get('asset', None)
        company = request.GET.get('company', None)
        date = request.GET.get('date', None)
        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        records = Taizhang.objects.filter(archived=False)
        if asset is not None and asset != '':
            records = records.filter(asset__contains=asset)
        if company is not None and company != '':
            records = records.filter(company__contains=company)
        if date is not None and date != '':
            records = records.filter(date=date)

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

        props = [
            'company',
            'asset',
            'upstream',
            'downstream',
            'upstream_dunwei',
            'buyPrice',

            'kaipiao_dunwei',
            'upstream_jiesuan_price',
            'kaipiao_dunwei_trade',
            'downstream_jiesuan_price',
            'shangyou_zijin_zhanya',
            'shangyou_kuchun_liang',
            'shangyou_kuchun_yuji_danjia'
        ]
        partial = {}
        modifiedProps = []
        for prop in props:
            value = getattr(r, prop, None)

            if type(value) is Decimal:
                value = str(value)

            if value != data.get(prop, None):
                modifiedProps.append({'prop': prop, 'value': value})

            partial[prop] = data.get(prop, None)

        partial['updated_at'] = timezone.now()
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
        if len(modifiedProps) > 0:
            StatsEvent.objects.create(source='taizhang', event='invalidate')
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
    id = request.GET.get('id', None)
    company = request.GET.get('company', None)
    other = request.GET.get('other', None)
    prop = request.GET.get('prop', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    ops = TaizhangOps.objects.filter(op='modify')

    if name is not None and name != '':
        ops = ops.filter(profile__name__contains=name)
    if other is not None and other != '':
        ops = ops.filter(record__other__contains=other)
    if company is not None and company != '':
        ops = ops.filter(Q(upstream__contains=company) | Q(downstream__contains=company))
    if prop is not None and prop != '':
        ops = ops.filter(prop=prop)
    if id is not None and id != '':
        ops = ops.filter(record__pk=id)

    ops = ops.order_by('-updated_at')
    total = ops.count()
    ops = ops[start:start + limit]
    return JsonResponse({
        'total': total,
        'ops': [resolve_op(op) for op in ops]
    })


@require_http_methods(['GET'])
def stats(request):
    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    company_param = request.GET.get('company', '')
    asset_param = request.GET.get('asset', '')

    records = TaizhangStat.objects.filter(category='total')
    if company_param is not None and company_param != '':
        records = records.filter(company__contains=company_param)
    if asset_param:
        records = records.filter(asset__contains=asset_param)

    records = records.order_by('company', 'asset')
    total = records.count()
    records = records[start:start + limit]
    records = [{
        'company': r.company,
        'asset': r.asset,
        'xiaoshoue': r.xiaoshoue,
        'lirune': r.lirune,
        'kuchun_liang': r.kuchun_liang,
        'zijin_zhanya': r.zijin_zhanya
    } for r in records]

    return JsonResponse({
        'total': total,
        'stats': records
    })
