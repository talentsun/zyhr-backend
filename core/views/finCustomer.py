import logging
import datetime
import json
import pandas
import xlwt
import xlrd
from decimal import Decimal
from math import isnan

from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile

from core.models import *
from core.auth import validateToken
from core.common import *
from core.exception import *

logger = logging.getLogger('app.core.views.finCustomer')


def resolve_fin_customer(fc):
    return {
        'id': fc.pk,
        'org': fc.org,
        'layer': fc.layer,
        'owner': fc.owner,
        'interface': fc.interface,
        'interfacePosition': fc.interfacePosition,
        'interfacePhone': fc.interfacePhone,
        'meetTime': fc.meetTime.isoformat(),
        'meetPlace': fc.meetPlace,
        'member': fc.member,
        'otherMember': fc.otherMember,
        'otherMemberPosition': fc.otherMemberPosition,
        'desc': fc.desc,
        'next': fc.next,
        'note': fc.note,

        'creator': resolve_profile(fc.creator) if fc.creator is not None else None,

        'created_at': fc.created_at.isoformat(),
        'updated_at': fc.updated_at.isoformat()
    }


@require_http_methods(['GET'])
@validateToken
def index(request):
    org = request.GET.get('org', None)
    interface = request.GET.get('interface', None)
    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    customers = FinCustomer.objects.filter(archived=False)
    if org is not None and org != '':
        customers = customers.filter(org__contains=org)
    if interface is not None and interface != '':
        customers = customers.filter(interface__contains=interface)

    customers = customers.order_by('-id')
    total = customers.count()
    customers = customers[start:start + limit]
    return JsonResponse({
        'total': total,
        'customers': [resolve_fin_customer(c) for c in customers]
    })


def createCustomerByTuple(tuple, profile):
    # logger.info(tuple)

    t = []
    for i in tuple:
        if isinstance(i, str):
            t.append(i)
            continue

        if pandas.isna(i):
        # if isnan(i):
            t.append('')
        else:
            t.append(i)

    data = {
        'org': t[1],
        'layer': t[2],
        'owner': t[3],
        'interface': t[4],
        'interfacePosition': t[5],
        'interfacePhone': t[6],
        'meetTime': t[7],
        'meetPlace': t[8],
        'member': t[9],
        'otherMember': t[10],
        'otherMemberPosition': t[11],
        'desc': t[12],
        'next': t[13],
        'note': t[14] if len(t) >= 15 else None, # 备注可能不在 excel 文档当中
        'creator': profile
    }
    # logger.info(data)
    FinCustomer.objects.create(**data)


@require_http_methods(['POST'])
@validateToken
def importCustomers(request):
    profile = request.profile
    data = json.loads(request.body.decode('utf-8'))
    fileId = data['file']
    f = File.objects.get(pk=fileId)
    ex_data = pandas.read_excel('{}/{}'.format(settings.DATA_DIR, f.path))
    total, success = 0, 0
    for t in ex_data.itertuples():
        total = total + 1
        try:
            createCustomerByTuple(t, profile)
            success = success + 1
        except:
            logger.exception("fail to import customer")
            pass

    return JsonResponse({'success': success, 'fail': total - success})


@require_http_methods(['POST'])
@validateToken
def deleteCustomers(request):
    data = json.loads(request.body.decode('utf-8'))
    idx = data['idx']
    FinCustomer.objects.filter(pk__in=idx).update(archived=True)
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def exportCustomers(request):
    customers = FinCustomer.objects.filter(archived=False)

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    titles = ['对接银行/机构', '银行/机构层级', '我方负责人', '对方对接人',
              '对接人职位', '对接人联系方式', '见面时间', '见面地点', '我方参与人员', '对方参与人员', '对方参与人员职务',
              '沟通情况', '后续工作安排', '备注']
    for index, title in enumerate(titles):
        sheet.write(0, index, title)

    props = ['org', 'layer', 'owner', 'interface', 'interfacePosition',
             'interfacePhone', 'meetTime', 'meetPlace', 'member', 'otherMember', 'otherMemberPosition',
             'desc', 'next', 'note']
    for row, customer in enumerate(customers):
        for col, prop in enumerate(props):
            attr = getattr(customer, prop)
            if prop == 'meetTime':
                attr = attr.strftime('%Y-%m-%d')
            sheet.write(row + 1, col, attr)

    xf.save(f)
    filename = '融资客户信息{}.xls'.format(timezone.now().strftime('%Y%m%d'))
    return sendfile(request, f, attachment=True, attachment_filename=filename)


@require_http_methods(['GET', 'PUT'])
@validateToken
def customer(request, customerId):
    if request.method == 'GET':
        try:
            customer = FinCustomer.objects.get(pk=customerId)
        except:
            customer = None
        return JsonResponse(resolve_fin_customer(customer))
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        del data['id']
        del data['creator']
        FinCustomer.objects.filter(pk=customerId).update(**data)
        return JsonResponse({'ok': True})
