from decimal import Decimal
import re
import json
import logging
import random
import pandas
import xlwt

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.cache import cache
from sendfile import sendfile

from core.auth import generateToken
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.stats')


def resolve_transaction_record(record):
    account = FinAccount.objects.filter(number=record.number).first()

    return {
        'id': record.pk,
        'date': record.date,
        'number': record.number,
        'accountName': getattr(account, 'name', None),
        'income': record.income,
        'outcome': record.outcome,
        'balance': record.balance,
        'desc': record.desc or '-',
        'other': record.other
    }


@require_http_methods(["GET", "DELETE"])
def transactionRecords(request):
    if request.method == 'GET':
        number = request.GET.get('number', None)
        date = request.GET.get('date', None)
        other = request.GET.get('other', None)
        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        records = StatsTransactionRecord.objects.filter(archived=False)
        if number is not None and number != '':
            records = records.filter(number__contains=number)
        if date is not None and date != '':
            start_date, end_date = date.split(',')
            records = records.filter(date__gte=start_date, date__lte=end_date)
        if other is not None and other != '':
            records = records.filter(other__contains=other)

        records = records.order_by('-id')
        total = records.count()
        records = records[start:start + limit]
        return JsonResponse({
            'total': total,
            'records': [resolve_transaction_record(r) for r in records]
        })
    else:
        # delete
        data = json.loads(request.body.decode('utf-8'))
        idx = data['idx']
        StatsTransactionRecord.objects.filter(pk__in=idx).update(archived=True)
        return JsonResponse({
            'ok': True
        })


# 修改记录：
# 1. 导入
# 2. 修改
# 3. 删除

def createTransactionRecordByTuple(tuple, profile):
    logger.info(tuple)

    data = {}
    props = ['date', 'number', 'income', 'outcome', 'balance', 'desc', 'other']
    for index, prop in enumerate(props):
        value = tuple[index + 1]
        if pandas.isna(value):
            value = None

        data[prop] = value

    # process date
    date = data['date']
    if date is None:
        raise Exception('invalid date')
    date = str(date).strip()
    if re.match('^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d$', date):
        date = date.split(' ')[0]
    if not re.match('^\d\d\d\d-\d\d-\d\d$', date):
        raise Exception('invalid date')
    data['date'] = date

    if data['number'] is None:
        raise Exception('number shoud not be empty')

    if data['income'] is None and data['outcome'] is None:
        raise Exception("income or outcome should not be empty")

    if data['balance'] is None:
        raise Exception("balance should not be empty")

    if data['other'] is None:
        raise Exception("other should not be empty")

    data['creator'] = profile
    r = StatsTransactionRecord.objects.create(**data)

    SRO = StatsTransactionRecordOps
    SRO.objects.create(record=r, profile=profile, op='create')


@require_http_methods(['POST'])
@validateToken
def importTransactionRecords(request):
    profile = request.profile
    data = json.loads(request.body.decode('utf-8'))
    fileId = data['file']
    f = File.objects.get(pk=fileId)
    ex_data = pandas.read_excel('{}/{}'.format(settings.DATA_DIR, f.path))
    total, success = 0, 0
    for t in ex_data.itertuples():
        total = total + 1
        try:
            createTransactionRecordByTuple(t, profile)
            success = success + 1
        except:
            # 出现异常的数据，就终止导入
            logger.exception("fail to import customer, stop")
            break

    if success > 0:
        StatsEvent.objects.create(source='funds', event='invalidate')

    return JsonResponse({'success': success, 'fail': total - success})


@require_http_methods(['GET', 'PUT'])
@validateToken
def transactionRecord(request, recordId):
    SRO = StatsTransactionRecordOps

    if request.method == 'GET':
        try:
            record = StatsTransactionRecord.objects.get(pk=recordId)
        except:
            record = None
        return JsonResponse(resolve_transaction_record(record))
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        del data['id']
        if 'creator' in data:
            del data['creator']

        try:
            r = StatsTransactionRecord.objects.get(pk=recordId)

            props = ['date', 'number', 'income', 'outcome', 'desc', 'balance', 'other']
            partial = {}
            modifiedProps = []
            for prop in props:
                value = getattr(r, prop, None)
                v = data.get(prop, None)

                if v is None and value is None:
                    continue

                if prop in ['outcome', 'income', 'balance']:
                    if v is None or value is None:
                        modifiedProps.append({'prop': prop, 'value': value})
                    elif Decimal(value) != Decimal(v):
                        modifiedProps.append({'prop': prop, 'value': value})
                else:
                    if v != value:
                        modifiedProps.append({'prop': prop, 'value': value})

                partial[prop] = data.get(prop, None)

            StatsTransactionRecord.objects.filter(pk=recordId).update(**partial)

            r = StatsTransactionRecord.objects.get(pk=recordId)
            for item in modifiedProps:
                prop, prev = item['prop'], item['value']
                SRO.objects.create(record=r,
                                   prop=prop,
                                   extra={
                                       'prev': prev,
                                       'cur': getattr(r, prop, None)
                                   },
                                   profile=request.profile,
                                   op='modify')
            if len(modifiedProps) > 0:
                StatsEvent.objects.create(source='funds', event='invalidate')
        except:
            logger.exception("fail to modify record")
            return JsonResponse({'errorId': 'internal-server-error'}, status=500)

        return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def exportRecords(request):
    records = StatsTransactionRecord.objects.filter(archived=False).order_by('date', 'pk')

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    titles = ['交易日期', '账号', '收款', '支出', '账号余额', '摘要', '对方账户名称']
    for index, title in enumerate(titles):
        sheet.write(0, index, title)

    props = ['date', 'number', 'income', 'outcome', 'balance', 'desc', 'other']
    for row, r in enumerate(records):
        for col, prop in enumerate(props):
            sheet.write(row + 1, col, getattr(r, prop, ''))

    xf.save(f)

    filename = '资金信息{}.xls'.format(timezone.now().strftime('%Y%m%d'))
    return sendfile(request, f, attachment=True, attachment_filename=filename)


def resolve_op(op):
    return {
        'id': op.pk,
        'profile': {
            'pk': str(op.profile.pk),
            'name': str(op.profile.name)
        },
        'record': resolve_transaction_record(op.record),
        'prop': op.prop,
        'extra': op.extra,
        'created_at': op.created_at
    }


@require_http_methods(['GET'])
def ops(request):
    name = request.GET.get('name', None)
    other = request.GET.get('other', None)
    prop = request.GET.get('prop', None)
    id = request.GET.get('id', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    SRO = StatsTransactionRecordOps
    ops = SRO.objects.filter(op='modify')

    if name is not None and name != '':
        ops = ops.filter(profile__name__contains=name)
    if other is not None and other != '':
        ops = ops.filter(record__other__contains=other)
    if prop is not None and prop != '':
        ops = ops.filter(prop=prop)
    if id is not None and id != '':
        ops = ops.filter(record=id)

    ops = ops.order_by('-created_at')
    total = ops.count()
    ops = ops[start:start + limit]
    return JsonResponse({
        'total': total,
        'ops': [resolve_op(op) for op in ops]
    })


def resolve_ts(r):
    return {
        'id': r.account.pk,
        'name': r.account.name,
        'number': r.account.number,
        'currency': r.account.currency,
        'bank': r.account.bank,
        'balance': r.balance,
        'income': r.income,
        'outcome': r.outcome
    }


@require_http_methods(['GET'])
def stats(request):
    name = request.GET.get('name', None)
    number = request.GET.get('number', None)

    tss = TransactionStat.objects.filter(category='total')
    if name is not None and name != '':
        tss = tss.filter(account__name__contains=name)
    if number is not None and number != '':
        tss = tss.filter(account__number__contains=number)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    total = tss.count()
    records = tss[start:start + limit]
    records = [resolve_ts(r) for r in records]
    return JsonResponse({
        'records': records,
        'total': total
    })
