import logging
import datetime
import json
import pandas
import xlwt
import xlrd

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile

from core.models import *
from core.auth import validateToken
from core.common import *
from core.exception import *

logger = logging.getLogger('app.core.views.finAccounts')


@require_http_methods(['GET', 'POST'])
@validateToken
def index(request):
    profile = request.profile

    if request.method == 'GET':
        name = request.GET.get('name', None)
        number = request.GET.get('number', None)
        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        accounts = FinAccount.objects.all()
        if name is not None and name != '':
            accounts = accounts.filter(name__contains=name)
        if number is not None and number != '':
            accounts = accounts.filter(number__contains=number)

        accounts = accounts.order_by('-id')
        total = accounts.count()
        accounts = accounts[start:start + limit]
        return JsonResponse({
            'total': total,
            'accounts': [resolve_account(a) for a in accounts]
        })
    elif request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        data['creator'] = profile
        FinAccount.objects.create(**data)
        return JsonResponse({'ok': True})


@require_http_methods(['GET', 'PUT', 'DELETE'])
@validateToken
def account(request, accountId):
    if request.method == 'DELETE':
        FinAccount.objects.filter(pk=accountId).delete()
        return JsonResponse({'ok': True})
    elif request.method == 'GET':
        try:
            account = FinAccount.objects.get(pk=accountId)
        except:
            account = None
        return JsonResponse(resolve_account(account))
    elif request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        del data['id']
        del data['creator']
        del data['created_at']
        del data['updated_at']
        FinAccount.objects.filter(pk=accountId).update(**data)
        return JsonResponse({'ok': True})


def createAccountByTuple(tuple, profile):
    logger.info(tuple)

    name = tuple[1]
    number = tuple[2]
    bank = tuple[3]
    currency = tuple[4]

    if currency not in ['人民币', '港币', '美元']:
        raise Exception('invalid currency')
    if currency == '人民币':
        currency = 'rmb'
    if currency == '港币':
        currency = 'hkd'
    if currency == '美元':
        currency = 'dollar'

    FinAccount.objects.create(
        creator=profile,
        name=name,
        number=number,
        currency=currency,
        bank=bank
    )


@require_http_methods(['POST'])
@validateToken
def importAccounts(request):
    profile = request.profile
    data = json.loads(request.body.decode('utf-8'))
    fileId = data['file']
    f = File.objects.get(pk=fileId)
    ex_data = pandas.read_excel('{}/{}'.format(settings.DATA_DIR, f.path))
    total, success = 0, 0
    for t in ex_data.itertuples():
        total = total + 1
        try:
            createAccountByTuple(t, profile)
            success = success + 1
        except:
            logger.exception("fail to import customer")
            pass

    return JsonResponse({'success': success, 'fail': total - success})


@require_http_methods(['GET'])
def exportAccounts(request):
    accounts = FinAccount.objects.all()

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    titles = ['账户名称', '账号', '开户机构', '币种']
    for index, title in enumerate(titles):
        sheet.write(0, index, title)

    props = ['name', 'number', 'bank', 'displayCurrency']
    for row, account in enumerate(accounts):
        for col, prop in enumerate(props):
            sheet.write(row + 1, col, getattr(account, prop))

    xf.save(f)
    filename = '财务账号{}.xls'.format(timezone.now().strftime('%Y%m%d'))
    return sendfile(request, f, attachment=True, attachment_filename=filename)
