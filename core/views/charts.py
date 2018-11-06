import logging
import datetime
import json
import pandas
import xlwt
import xlrd
from decimal import Decimal

from django.db.models import Q
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile

from core.models import *
from core.auth import validateToken
from core.common import *
from core.exception import *


@require_http_methods(['GET'])
@validateToken
def taizhang_companies(request):
    companies = TaizhangStat.objects.all().values('company').distinct()
    companies = [c['company'] for c in companies]

    return JsonResponse(companies, safe=False)


@require_http_methods(['GET', 'POST'])
@validateToken
def taizhang_line(request):
    company = request.GET.get('company', None)
    prop = request.GET.get('prop', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    tss = TaizhangStat.objects.filter(category='month', company=company)
    if fromMonth is not None and fromMonth != '':
        tss = tss.filter(month__gte=fromMonth)
    if toMonth is not None and toMonth != '':
        tss = tss.filter(month__lte=toMonth)

    months = tss.values('month').distinct().order_by('month')
    months = [w['month'] for w in months]

    assets = tss.values('asset').distinct()
    assets = [a['asset'] for a in assets]

    series = []
    for asset in assets:
        tss_by_asset = tss.filter(asset=asset)
        tss_by_asset = tss_by_asset.order_by('month')
        s = [getattr(t, prop) for t in tss_by_asset]
        series.append(s)

    return JsonResponse({
        'months': months,
        'assets': assets,
        'series': series
    })


@require_http_methods(['GET'])
@validateToken
def taizhang_bar(request):
    company = request.GET.get('company', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    tss = TaizhangStat.objects.filter(category='month', company=company)
    if fromMonth is not None and fromMonth != '':
        tss = tss.filter(month__gte=fromMonth)
    if toMonth is not None and toMonth != '':
        tss = tss.filter(month__lte=toMonth)

    months = tss.values('month').distinct().order_by('month')
    months = [w['month'] for w in months]

    series = []
    for prop in ['xiaoshoue', 'lirune', 'kuchun_liang', 'zijin_zhanya']:
        p = 'sum_' + prop
        d = {p: Sum(prop)}
        tss_by_prop = tss.values('month').annotate(**d)
        tss_by_prop = tss_by_prop.order_by('month')
        s = [t.get(p, '0.00') for t in tss_by_prop]
        series.append(s)

    return JsonResponse({
        'months': months,
        'series': series
    })


@require_http_methods(['GET'])
@validateToken
def taizhang_pie(request):
    company = request.GET.get('company', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    tss = TaizhangStat.objects.filter(category='month', company=company)
    if fromMonth is not None and fromMonth != '':
        tss = tss.filter(month__gte=fromMonth)
    if toMonth is not None and toMonth != '':
        tss = tss.filter(month__lte=toMonth)

    assets = tss.values('asset').distinct()
    assets = [a['asset'] for a in assets]

    total = Decimal(0.0)
    assetData = []
    for asset in assets:
        t = tss \
            .filter(asset=asset) \
            .values('asset') \
            .annotate(sum_xiaoshoue=Sum('xiaoshoue'))[0]
        assetData.append({'name': asset, 'value': t['sum_xiaoshoue']})
        total = total + t['sum_xiaoshoue']

    for index, asset in enumerate(assets):
        if total == Decimal(0.0):
            assetData[index]['percent'] = 0.0
        else:
            value = assetData[index]['value']
            assetData[index]['percent'] = value / total * 100

    return JsonResponse(assetData, safe=False)


def last_day_of_month(date):
    if date.month == 12:
        return date.replace(day=31)
    return date.replace(month=date.month + 1, day=1) - datetime.timedelta(days=1)


@require_http_methods(['GET'])
@validateToken
def funds_line(request):
    name = request.GET.get('name', None)
    number = request.GET.get('number', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    tss = TransactionStat.objects.filter(category='week')
    if name is not None and name != '':
        tss = tss.filter(account__name__contains=name)
    if number is not None and number != '':
        tss = tss.filter(account__number__contains=number)
    if toMonth is not None and toMonth != '':
        originMonth = toMonth
        d = datetime.datetime.strptime(toMonth, '%Y-%m')
        d = last_day_of_month(d)
        toMonth = d.strftime('%Y-%m-%d')
        logger.info('filter funds line data by toMonth: {} origin: {}'.format(toMonth, originMonth))
        tss = tss.filter(startDayOfWeek__lte=toMonth)
    if fromMonth is not None and fromMonth != '':
        fromMonth = fromMonth + '-01'
        logger.info('filter funds line data by fromMonth: {} '.format(fromMonth))
        tss = tss.filter(startDayOfWeek__gte=fromMonth)

    accounts = tss.values('account__pk', 'account__name', 'account__number').distinct()
    accountNames = [a['account__name'] + '(' + a['account__number'] + ')' for a in accounts]
    accounts = [a['account__pk'] for a in accounts]

    weeks = tss.values('startDayOfWeek').distinct().order_by('startDayOfWeek')
    weeks = [w['startDayOfWeek'] for w in weeks]

    series = []
    for account in accounts:
        tss_by_account = tss.filter(account__pk=account)
        s = [{
            'income': t.income,
            'outcome': t.outcome,
            'balance': t.balance
        } for t in tss_by_account]
        series.append(s)

    return JsonResponse({
        'weeks': weeks,
        'accounts': accountNames,
        'series': series
    })


@require_http_methods(['GET'])
@validateToken
def funds_bar(request):
    name = request.GET.get('name', None)
    number = request.GET.get('number', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    tss = TransactionStat.objects.filter(category='week')
    if name is not None and name != '':
        tss = tss.filter(account__name__contains=name)
    if number is not None and number != '':
        tss = tss.filter(account__number__contains=number)
    if toMonth is not None and toMonth != '':
        originMonth = toMonth
        d = datetime.datetime.strptime(toMonth, '%Y-%m')
        d = last_day_of_month(d)
        toMonth = d.strftime('%Y-%m-%d')
        logger.info('filter funds bar data by toMonth: {} origin: {}'.format(toMonth, originMonth))
        tss = tss.filter(startDayOfWeek__lte=toMonth)
    if fromMonth is not None and fromMonth != '':
        fromMonth = fromMonth + '-01'
        logger.info('filter funds bar data by fromMonth: {} '.format(fromMonth))
        tss = tss.filter(startDayOfWeek__gte=fromMonth)

    weeks = tss.values('startDayOfWeek').distinct().order_by('startDayOfWeek')
    weeks = [w['startDayOfWeek'] for w in weeks]

    ag = {
        'sum_income': Sum('income'),
        'sum_outcome': Sum('outcome'),
        'sum_balance': Sum('balance')
    }
    tss = tss.values('startDayOfWeek').annotate(**ag)
    data = [{
        'startDayOfWeek': t['startDayOfWeek'],
        'income': t['sum_income'],
        'outcome': t['sum_outcome'],
        'balance': t['sum_balance']
    } for t in tss]

    return JsonResponse({
        'weeks': weeks,
        'data': data
    })


@require_http_methods(['GET'])
@validateToken
def customers_line(request):
    name = request.GET.get('name', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    css = CustomerStat.objects.filter(category='month')
    if name is not None and name != '':
        css = css.filter(customer__name__contains=name)
    if fromMonth is not None and fromMonth != '':
        css = css.filter(month__gte=fromMonth)
    if toMonth is not None and toMonth != '':
        css = css.filter(month__lte=toMonth)

    months = css.values('month').distinct().order_by('month')
    months = [w['month'] for w in months]

    customers = css.values('customer__pk', 'customer__name').distinct()
    customerNames = [c['customer__name'] for c in customers]
    customers = [c['customer__pk'] for c in customers]

    series = []
    for c in customers:
        css_by_customer = css.filter(customer=c)
        css_by_customer = css_by_customer.order_by('month')
        s = [{
            'yewuliang': c.yewuliang,
            'avg_price': c.avg_price
        } for c in css_by_customer]
        series.append(s)

    return JsonResponse({
        'months': months,
        'customers': customerNames,
        'series': series
    })


@require_http_methods(['GET'])
@validateToken
def customers_bar(request):
    name = request.GET.get('name', None)
    fromMonth = request.GET.get('fromMonth', None)
    toMonth = request.GET.get('toMonth', None)

    css = CustomerStat.objects.filter(category='month')
    if name is not None and name != '':
        css = css.filter(customer__name__contains=name)
    if fromMonth is not None and fromMonth != '':
        css = css.filter(month__gte=fromMonth)
    if toMonth is not None and toMonth != '':
        css = css.filter(month__lte=toMonth)

    months = css.values('month').distinct().order_by('month')
    months = [w['month'] for w in months]

    d = {
        'sum_yewuliang': Sum('yewuliang')
    }
    css = css.values('month').annotate(**d)
    css = css.order_by('month')
    data = [{
        'yewuliang': c.get('sum_yewuliang', '0.00'),
        'avg_price': c.get('sum_avg_price', '0.00')
    } for c in css]

    return JsonResponse({
        'months': months,
        'data': data
    })


def resolve_prev_month(d):
    if d.month == 1:
        prevMonth = datetime.datetime(year=d.year - 1, month=12, day=1)
    else:
        prevMonth = datetime.datetime(year=d.year, month=d.month - 1, day=1)

    return prevMonth


def resolve_recent_months(date=None):
    if date == None:
        d = timezone.now()
    else:
        d = datetime.datetime.strptime(date, '%Y-%m')
    m1 = resolve_prev_month(d)
    m2 = resolve_prev_month(m1)
    return [m2.strftime('%Y-%m'), m1.strftime('%Y-%m'), d.strftime('%Y-%m')]


def resolve_recent_weeks():
    now = timezone.now()
    w = now - datetime.timedelta(days=now.weekday())
    w2 = w - datetime.timedelta(days=7)
    w3 = w2 - datetime.timedelta(days=7)
    w4 = w3 - datetime.timedelta(days=7)
    return [
        w4.strftime('%Y-%m-%d'),
        w3.strftime('%Y-%m-%d'),
        w2.strftime('%Y-%m-%d'),
        w.strftime('%Y-%m-%d')
    ]


@require_http_methods(['GET'])
@validateToken
def app_home(request):
    result = {}
    months = resolve_recent_months()
    weeks = resolve_recent_weeks()

    # taizhang
    taizhangData = {
        'months': months,
        'xiaoshoue': [],
        'lirune': [],
        'zijin_zhanya': [],
        'kuchun_liang': [],
        'empty': True
    }
    for month in months:
        tss = TaizhangStat.objects.filter(category='month', month=month)
        data = tss.aggregate(sum_xiaoshoue=Sum('xiaoshoue'),
                             sum_lirune=Sum('lirune'),
                             sum_zijin_zhanya=Sum('zijin_zhanya'),
                             sum_kuchun_liang=Sum('kuchun_liang'))
        for p in ['sum_xiaoshoue', 'sum_lirune', 'sum_zijin_zhanya', 'sum_kuchun_liang']:
            if data[p] is None:
                data[p] = Decimal(0)
        taizhangData['xiaoshoue'].append(data['sum_xiaoshoue'] / Decimal(100000000))
        taizhangData['lirune'].append(data['sum_lirune'] / Decimal(10000))
        taizhangData['zijin_zhanya'].append(data['sum_zijin_zhanya'] / Decimal(10000))
        taizhangData['kuchun_liang'].append(data['sum_kuchun_liang'] / Decimal(10000))
        if tss.count() > 0:
            taizhangData['empty'] = False
    result['taizhang'] = taizhangData

    # funds
    fundsData = {
        'weeks': weeks,
        'income': [],
        'outcome': [],
        'balance': [],
        'empty': True
    }
    for week in weeks:
        tss = TransactionStat.objects.filter(category='week', startDayOfWeek=week)
        data = tss.aggregate(sum_income=Sum('income'),
                             sum_outcome=Sum('outcome'),
                             sum_balance=Sum('balance'))
        for p in ['sum_income', 'sum_outcome', 'sum_balance']:
            if data[p] is None:
                data[p] = Decimal(0)
        fundsData['income'].append(data['sum_income'] / Decimal(10000))
        fundsData['outcome'].append(data['sum_outcome'] / Decimal(10000))
        fundsData['balance'].append(data['sum_balance'] / Decimal(10000))
        if tss.count() > 0:
            fundsData['empty'] = False
    result['funds'] = fundsData

    # customers
    customersData = {
        'months': months,
        'yewuliang': [],
        'avg_price': [],
        'empty': []
    }
    for month in months:
        css = CustomerStat.objects.filter(category='month', month=month)
        data = css.aggregate(sum_yewuliang=Sum('yewuliang'),
                             sum_avg_price=Sum('avg_price'))
        for p in ['sum_yewuliang', 'sum_avg_price']:
            if data[p] is None:
                data[p] = Decimal(0)
        customersData['yewuliang'].append(data['sum_yewuliang'] / Decimal(100000000))
        customersData['avg_price'].append(data['sum_avg_price'] / Decimal(10000))
        if css.count() > 0:
            customersData['empty'] = False
    result['customers'] = customersData

    return JsonResponse(result)


@require_http_methods(['GET'])
@validateToken
def app_taizhang(request):
    time = request.GET.get('time', None)

    result = {}
    date = datetime.datetime.strptime(time, '%Y-%m') if time is not None else timezone.now()
    months = TaizhangStat.objects \
        .filter(category='month', month__lte=date) \
        .values('month') \
        .distinct() \
        .order_by('month')
    months = [w['month'] for w in months]
    # months = resolve_recent_months(date=time)
    result['months'] = months

    tss = TaizhangStat.objects.filter(category='month', month__in=months)
    if tss.count() == 0:
        result['empty'] = True
        result['companies'] = []
        result['companyData'] = []
        return JsonResponse(result)

    result['empty'] = False
    companies = tss.values('company').distinct()
    companies = [c['company'] for c in companies]
    result['companies'] = [{'id': c, 'name': c} for c in companies]

    companyData = []
    for company in result['companies']:
        data = {'id': company['id']}

        # values
        values = []
        for month in months:
            tss = TaizhangStat.objects.filter(category='month', month=month, company=company['name'])
            if tss.count() == 0:
                valueItem = {
                    'xiaoshoue': 0,
                    'lirune': 0,
                    'zijin_zhanya': 0,
                    'kuchun)liang': 0,
                }
            else:
                s = tss.aggregate(
                    sum_xiaoshoue=Sum('xiaoshoue'),
                    sum_lirune=Sum('lirune'),
                    sum_zijin_zhanya=Sum('zijin_zhanya'),
                    sum_kuchun_liang=Sum('kuchun_liang'),
                )
                valueItem = {
                    'xiaoshoue': s['sum_xiaoshoue'] / Decimal(10000),
                    'lirune': s['sum_lirune'] / Decimal(10000),
                    'zijin_zhanya': s['sum_zijin_zhanya'] / Decimal(10000),
                    'kuchun_liang': s['sum_kuchun_liang'] / Decimal(10000),
                }
            values.append(valueItem)
        data['values'] = values

        # assetValues
        assetValues = []
        tss = TaizhangStat.objects \
            .filter(category='month',
                    month__in=months,
                    company=company['name'])
        tss = tss.values('asset') \
            .annotate(sum_xiaoshoue=Sum('xiaoshoue'))
        for t in tss:
            assetValues.append({
                'name': t['asset'],
                'value': t['sum_xiaoshoue'] / Decimal(10000)
            })
        data['assetValues'] = assetValues

        companyData.append(data)

    result['companyData'] = companyData

    return JsonResponse(result)


@require_http_methods(['GET'])
@validateToken
def app_funds(request):
    result = {}

    weeks = TransactionStat.objects \
        .filter(category='week') \
        .values('startDayOfWeek') \
        .distinct() \
        .order_by('startDayOfWeek')
    weeks = [w['startDayOfWeek'] for w in weeks]
    result['weeks'] = weeks

    tss = TransactionStat.objects.filter(category='week', startDayOfWeek__in=weeks)
    if tss.count() == 0:
        result['empty'] = True
        result['accounts'] = []
        result['accountData'] = []
        return JsonResponse(result)

    result['empty'] = False
    accounts = tss.values('account__pk', 'account__name', 'account__number').distinct()
    accounts = [{
        'id': a['account__pk'],
        'name': a['account__name'],
        'number': a['account__number'],
    } for a in accounts]
    result['accounts'] = accounts

    accountData = []
    for account in result['accounts']:
        data = {'id': account['id']}

        # values
        values = []
        for week in weeks:
            tss = TransactionStat.objects \
                .filter(category='week',
                        startDayOfWeek=week,
                        account=account['id'])
            t = tss.first()
            if t is None:
                valueItem = {
                    'income': '0',
                    'outcome': '0',
                    'balance': '0'
                }
            else:
                valueItem = {
                    'income': t.income / Decimal(10000),
                    'outcome': t.outcome / Decimal(10000),
                    'balance': t.balance / Decimal(10000)
                }
            values.append(valueItem)
        data['values'] = values

        accountData.append(data)

    result['accountData'] = accountData

    return JsonResponse(result)


@require_http_methods(['GET'])
@validateToken
def app_customers(request):
    result = {}

    time = request.GET.get('time', None)
    date = datetime.datetime.strptime(time, '%Y-%m') if time is not None else timezone.now()
    months = CustomerStat.objects \
        .filter(category='month', month__lte=date) \
        .values('month') \
        .distinct() \
        .order_by('month')
    months = [w['month'] for w in months]
    # months = resolve_recent_months(date=time)
    result['months'] = months

    css = CustomerStat.objects.filter(category='month', month__in=months)
    if css.count() == 0:
        result['empty'] = True
        result['companies'] = []
        result['companyData'] = []
        return JsonResponse(result)

    result['empty'] = False
    customers = css.values('customer__pk', 'customer__name').distinct()
    customers = [{
        'id': a['customer__pk'],
        'name': a['customer__name'],
    } for a in customers]
    result['companies'] = customers

    companyData = []
    for company in result['companies']:
        data = {'id': company['id']}

        # values
        values = []
        for month in months:
            tss = CustomerStat.objects \
                .filter(category='month',
                        month=month,
                        customer=company['id'])
            t = tss.first()
            if t is None:
                valueItem = {
                    'yewuliang': Decimal('0'),
                    'avg_price': Decimal('0')
                }
            else:
                valueItem = {
                    'yewuliang': t.yewuliang / Decimal(10000),
                    'avg_price': t.avg_price / Decimal(10000)
                }
            values.append(valueItem)
        data['values'] = values

        companyData.append(data)

    result['companyData'] = companyData

    return JsonResponse(result)


@require_http_methods(['GET'])
@validateToken
def home_taizhang(request):
    tss = TaizhangStat.objects.filter(category='month')

    # resolve months
    months = resolve_recent_months()

    # resolve companies
    companies = tss.values('company').distinct()
    companies = [c['company'] for c in companies]
    companies = [{'id': c, 'name': c} for c in companies]

    # resolve companyData
    companyData = []
    for company in companies:
        # id
        data = {'id': company['id']}

        # values
        values = []
        for month in months:
            tss = TaizhangStat.objects.filter(category='month', month=month, company=company['name'])
            if tss.count() == 0:
                valueItem = {
                    'xiaoshoue': 0,
                    'lirune': 0,
                    'zijin_zhanya': 0,
                    'kuchun_liang': 0,
                }
            else:
                s = tss.aggregate(
                    sum_xiaoshoue=Sum('xiaoshoue'),
                    sum_lirune=Sum('lirune'),
                    sum_zijin_zhanya=Sum('zijin_zhanya'),
                    sum_kuchun_liang=Sum('kuchun_liang'),
                )
                valueItem = {
                    'xiaoshoue': s['sum_xiaoshoue'],
                    'lirune': s['sum_lirune'],
                    'zijin_zhanya': s['sum_zijin_zhanya'],
                    'kuchun_liang': s['sum_kuchun_liang'],
                }
            values.append(valueItem)
        data['values'] = values

        companyData.append(data)

    result = {
        'months': months,
        'companies': companies,
        'companyData': companyData
    }
    return JsonResponse(result)


@require_http_methods(['GET'])
@validateToken
def home_customer(request):
    css = CustomerStat.objects.filter(category='month')

    # resolve months
    months = resolve_recent_months()

    # resolve customers
    customers = css.values('customer__pk', 'customer__name').distinct()
    customers = [{
        'id': a['customer__pk'],
        'name': a['customer__name'],
    } for a in customers]

    customerData = []
    for customer in customers:
        data = {'id': customer['id']}

        # values
        values = []
        for month in months:
            tss = CustomerStat.objects \
                .filter(category='month',
                        month=month,
                        customer=customer['id'])
            t = tss.first()
            if t is None:
                valueItem = {
                    'yewuliang': Decimal('0'),
                    'avg_price': Decimal('0')
                }
            else:
                valueItem = {
                    'yewuliang': t.yewuliang,
                    'avg_price': t.avg_price,
                }
            values.append(valueItem)
        data['values'] = values

        customerData.append(data)

    result = {
        'months': months,
        'customers': customers,
        'customerData': customerData
    }
    return JsonResponse(result)


@require_http_methods(['GET'])
@validateToken
def home_funds(request):
    tss = TransactionStat.objects.filter(category='week')

    # resolve weeks
    weeks = resolve_recent_weeks()

    # resolve accounts
    accounts = tss.values('account__pk', 'account__name').distinct()
    accounts = [{
        'id': a['account__pk'],
        'name': a['account__name'],
    } for a in accounts]

    # resolve account data
    accountData = []
    for account in accounts:
        # id
        data = {'id': account['id']}

        # values
        values = []
        for week in weeks:
            tss = TransactionStat.objects \
                .filter(category='week',
                        startDayOfWeek=week,
                        account=account['id'])
            t = tss.first()
            if t is None:
                valueItem = {
                    'income': '0',
                    'outcome': '0',
                    'balance': '0'
                }
            else:
                valueItem = {
                    'income': t.income,
                    'outcome': t.outcome,
                    'balance': t.balance,
                }
            values.append(valueItem)
        data['values'] = values

        accountData.append(data)

    result = {
        'weeks': weeks,
        'accounts': accounts,
        'accountData': accountData
    }
    return JsonResponse(result)
