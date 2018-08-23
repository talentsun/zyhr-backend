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


@require_http_methods(['GET'])
def exportRecords(request):
    records = Taizhang.objects.filter(archived=False)

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    props = {
        "id": "编号",
        "company": "公司名称",
        "asset": "货物标的",
        "upstream": "上游客户",
        "upstream_dunwei": "上游合同吨位",
        "buyPrice": "采购单价",
        "upstream_hetongjine": "合同金额",
        "kaipiao_dunwei": "开票吨位",
        "upstream_jiesuan_price": "上游单价",
        "yingye_chengben": "不含税采购额（营业成本）",
        "jinxiang_shuie": "进项税额",
        "caigou_jine": "采购金额",
        "fukuan_jine": "付款金额",
        "shangyou_weijiesuan_jine": "上游未结算金额",
        "downstream": "下游客户",
        "downstream_dunwei": "下游合同吨位",
        "sellPrice": "销售单价",
        "xiayou_hetong_jine": "下游合同金额",
        "kaipiao_dunwei_trade": "开票吨位（贸易量）",
        "downstream_jiesuan_price": "下游结算单价",
        "xiayou_buhanshui_jine": "不含税销售额（贸易额）",
        "xiaoxiang_shuie": "销项税额",
        "xiaoshou_jine": "销售金额",
        "shoukuan_jine": "收款金额",
        "xiayou_weijiesuan_jine": "下游未结算金额",
        "maolirun": "毛利润",
        "zengzhishui": "增值税",
        "yinhuashui": "印花税",
        "fujiashui": "附加税",
        "yugu_cangchufei": "预估仓储费",
        "jinglirun": "净利润",
        "tongdaofei": "通道费",
        "shangyou_zijin_zhanya": "上游供方资金占压",
        "shangyou_kuchun_liang": "上游库存数量",
        "shangyou_kuchun_yuji_danjia": "上游库存预计单价",
        "shangyou_kuchun_jine": "上游库存金额"
    }

    for index, key in enumerate(props):
        sheet.write(0, index, props[key].strip())

    calPaths = [
        "upstream_hetongjine=upstream_dunwei*buyPrice",
        "upstream_hetongjine=upstream_dunwei*buyPrice",
        "fukuan_jine=upstream_dunwei*buyPrice",
        "yingye_chengben=kaipiao_dunwei*upstream_jiesuan_price/Decimal(1.16)",
        "jinxiang_shuie=yingye_chengben*Decimal(0.16)",
        "caigou_jine=yingye_chengben+jinxiang_shuie",
        "shangyou_weijiesuan_jine=fukuan_jine-caigou_jine",
        "xiayou_hetong_jine=downstream_dunwei*sellPrice",
        "xiayou_buhanshui_jine=kaipiao_dunwei_trade*downstream_jiesuan_price/Decimal(1.16)",
        "xiaoxiang_shuie=xiayou_buhanshui_jine*Decimal(0.16)",
        "xiaoshou_jine=xiayou_buhanshui_jine+xiaoxiang_shuie",
        "shoukuan_jine=xiaoshou_jine*1",
        "xiayou_weijiesuan_jine=0",
        "maolirun=xiayou_buhanshui_jine - yingye_chengben",
        "zengzhishui=xiaoxiang_shuie - jinxiang_shuie",
        "yinhuashui=(xiayou_buhanshui_jine + yingye_chengben)*Decimal(0.0003)",
        "fujiashui=zengzhishui*Decimal(0.12)",
        "yugu_cangchufei=kaipiao_dunwei*Decimal(3)",
        "jinglirun=maolirun-yinhuashui-fujiashui-yugu_cangchufei",
        'tongdaofei=xiayou_hetong_jine*Decimal(0.002)',
        "shangyou_kuchun_jine=shangyou_kuchun_liang*shangyou_kuchun_yuji_danjia"
    ];

    calPathMapping = {}
    calProps = []
    for path in calPaths:
        prop, exp = path.split('=')
        calPathMapping[prop] = exp
        calProps.append(prop)

    for row, r in enumerate(records):
        data = {}
        for _, prop in enumerate(props):
            if prop not in calProps:
                data[prop] = getattr(r, prop)
            else:
                exp = calPathMapping[prop]
                value = eval(exp, {'Decimal': Decimal}, data)
                data[prop] = value

        for col, prop in enumerate(props):
            sheet.write(row + 1, col, data.get(prop, ''))

    xf.save(f)
    return sendfile(request, f, attachment=True, attachment_filename='export.xls')
