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

    accounts = tss.values('account__pk', 'account__name').distinct()
    accountNames = [a['account__name'] for a in accounts]
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
            'avg_price': '0.00'
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
