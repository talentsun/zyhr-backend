import logging
import datetime
import json
import pandas
import xlwt
import xlrd
from decimal import Decimal

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

logger = logging.getLogger('app.core.views.emps')


@require_http_methods(['GET', 'POST'])
@validateToken
def index(request):
    if request.method == 'GET':
        name = request.GET.get('name', None)
        rating = request.GET.get('rating', None)
        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        customers = Customer.objects.all()
        if name is not None and name != '':
            customers = customers.filter(name__contains=name)
        if rating is not None and rating != '':
            customers = customers.filter(rating=rating)

        customers = customers.order_by('-id')
        total = customers.count()
        customers = customers[start:start + limit]
        return JsonResponse({
            'total': total,
            'customers': [resolve_customer(c) for c in customers]
        })
    elif request.method == 'POST':
        profile = request.profile
        data = json.loads(request.body.decode('utf-8'))
        data['creator'] = profile
        Customer.objects.create(**data)
        return JsonResponse({'ok': True})


@require_http_methods(['GET', 'PUT', 'DELETE'])
@validateToken
def customer(request, customerId):
    if request.method == 'DELETE':
        Customer.objects.filter(pk=customerId).delete()
        return JsonResponse({'ok': True})
    elif request.method == 'GET':
        try:
            customer = Customer.objects.get(pk=customerId)
        except:
            customer = None
        return JsonResponse(resolve_customer(customer))
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        del data['id']
        del data['creator']
        Customer.objects.filter(pk=customerId).update(**data)
        return JsonResponse({'ok': True})


def createCustomerByTuple(tuple, profile):
    logger.info(tuple)

    name = tuple[1]
    rating = tuple[2]
    shareholder = tuple[3]
    faren = tuple[4]
    capital = tuple[5]
    year = int(tuple[6])
    category = tuple[8]
    nature = tuple[9]
    address = tuple[10]
    desc = tuple[11]
    creator = profile

    if rating not in ['A+', 'A', 'B', 'C']:
        raise Exception('invalid rating')

    now = datetime.datetime.now(tz=timezone.utc)
    if year > now.year or year < 1949:
        raise Exception('invalid year')

    validNatures = [cn[1] for cn in CustomerNatures]
    if nature not in validNatures:
        raise Exception('invalid nature')
    cni = validNatures.index(nature)
    nature = CustomerNatures[cni][0]

    validCategories = [cc[1] for cc in CustomerCatgetories]
    if category not in validCategories:
        raise Exception('invalid category')
    cci = validCategories.index(category)
    category = CustomerCatgetories[cci][0]

    Customer.objects.create(
        creator=creator,
        name=name,
        rating=rating,
        shareholder=shareholder,
        faren=faren,
        capital=capital,
        year=year,
        category=category,
        nature=nature,
        address=address,
        desc=desc
    )


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


@require_http_methods(['GET'])
def exportCustomers(request):
    customers = Customer.objects.all()

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    titles = ['客户名称', '评级', '主要股东信息', '法人',
              '注册资本(万元)', '成立年份', '成立年限', '公司类型', '公司性质', '地址信息', '备注']
    for index, title in enumerate(titles):
        sheet.write(0, index, title)

    props = ['name', 'rating', 'shareholder', 'faren', 'capital',
             'year', 'nianxian', 'displayCategory', 'displayNature', 'address', 'desc']
    for row, customer in enumerate(customers):
        for col, prop in enumerate(props):
            sheet.write(row + 1, col, getattr(customer, prop))

    xf.save(f)
    filename = '客户信息{}.xls'.format(timezone.now().strftime('%Y%m%d'))
    return sendfile(request, f, attachment=True, attachment_filename=filename)


@require_http_methods(['GET'])
def stats(request):
    name = request.GET.get('name', None)
    rating = request.GET.get('rating', None)
    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    stats = CustomerStat.objects.filter(category='total')
    if name is not None and name != '':
        stats = stats.filter(customer__name__contains=name)
    if rating is not None and rating != '':
        stats = stats.filter(customer__rating=rating)

    stats = stats.order_by('customer__name')
    total = stats.count()
    stats = stats[start:start + limit]

    def resolveStat(s):
        d = resolve_customer(s.customer)
        d['yewuliang'] = s.yewuliang
        # TODO: 本月业务量还是平均价格
        d['month_yewuliang'] = s.yewuliang
        return d

    stats = [resolveStat(s) for s in stats]
    return JsonResponse({
        'total': total,
        'customers': stats
    })
