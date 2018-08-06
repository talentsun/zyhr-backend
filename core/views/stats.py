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
    return {
        'id': record.pk,
        'date': record.date,
        'number': record.number,
        'income': record.income,
        'outcome': record.outcome,
        'balance': record.balance,
        'other': record.other
    }


@require_http_methods(["GET"])
def transactionRecords(request):
    number = request.GET.get('number', None)
    date = request.GET.get('date', None)
    other = request.GET.get('other', None)
    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    records = StatsTransactionRecord.objects.filter(archived=False)
    if number is not None and number != '':
        records = records.filter(number=number)
    if date is not None and date != '':
        records = records.filter(date=date)
    if other is not None and other != '':
        records = records.filter(other=other)

    records = records.order_by('-id')
    total = records.count()
    records = records[start:start + limit]
    return JsonResponse({
        'total': total,
        'records': [resolve_transaction_record(r) for r in records]
    })


# 修改记录：
# 1. 导入
# 2. 修改
# 3. 删除

def createTransactionRecordByTuple(tuple, profile):
    logger.info(tuple)

    date = tuple[1].strip()
    if not re.match('^\d\d\d\d-\d\d-\d\d$', date):
        raise Exception('invalid date')

    number = tuple[2]
    income = tuple[3]
    outcome = tuple[4]

    balance = tuple[5]
    desc = tuple[6]
    other = tuple[7]

    if other == '':
        raise Exception('other should not be empty')

    r = StatsTransactionRecord.objects.create(
        creator=profile,
        date=date,
        number=number,
        income=income,
        outcome=outcome,
        balance=balance,
        desc=desc,
        other=other,
    )

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
            logger.exception("fail to import customer")
            pass

    return JsonResponse({'success': success, 'fail': total - success})


@require_http_methods(['GET', 'PUT', 'DELETE'])
@validateToken
def transactionRecord(request, recordId):
    SRO = StatsTransactionRecordOps

    if request.method == 'DELETE':
        try:
            r = StatsTransactionRecord.objects.get(pk=recordId)
            StatsTransactionRecord.objects.filter(pk=recordId).update(archived=True)
            SRO.objects \
                .create(record=r,
                        profile=request.profile,
                        op='delete')
        except:
            pass
        return JsonResponse({'ok': True})
    elif request.method == 'GET':
        try:
            record = StatsTransactionRecord.objects.get(pk=recordId)
        except:
            record = None
        return JsonResponse(resolve_transaction_record(record))
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        del data['id']
        del data['creator']
        try:
            r = StatsTransactionRecord.objects.get(pk=recordId)
            prev = resolve_transaction_record(r)
            StatsTransactionRecord.objects.filter(pk=recordId).update(**data)
            r = StatsTransactionRecord.objects.get(pk=recordId)
            cur = resolve_transaction_record(r)
            SRO.objects.create(record=r,
                               extra={
                                   'prev': prev,
                                   'cur': cur
                               },
                               profile=request.profile,
                               op='modify')
        except:
            pass
        return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def exportRecords(request):
    records = StatsTransactionRecord.objects.all()

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
    return sendfile(request, f, attachment=True, attachment_filename='export.xls')
