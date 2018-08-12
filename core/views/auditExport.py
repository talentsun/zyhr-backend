import os
import re
import json
import logging
import datetime

import iso8601
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile
from openpyxl import load_workbook
from openpyxl.styles import Border, Side, Alignment

from core.models import *
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.auditExport')
thin = Side(border_style="thin", color="000000")
empty = Side(border_style=None, color=None)
medium = Side(border_style="medium", color="000000")


# FIXME: 获取审批流当中负责审批的各个职位的人员信息


def style_range(ws, cell_range, border=Border(), fill=None, font=None, alignment=None):
    """
    Apply styles to a range of cells as if they were a single cell.

    :param ws:  Excel worksheet instance
    :param range: An excel range to style (e.g. A1:F20)
    :param border: An openpyxl Border
    :param fill: An openpyxl PatternFill or GradientFill
    :param font: An openpyxl Font object
    """

    top = Border(top=border.top)
    left = Border(left=border.left)
    right = Border(right=border.right)
    bottom = Border(bottom=border.bottom)

    first_cell = ws[cell_range.split(":")[0]]
    if alignment:
        ws.merge_cells(cell_range)
        first_cell.alignment = alignment

    rows = ws[cell_range]
    if font:
        first_cell.font = font

    for cell in rows[0]:
        cell.border = cell.border + top
    for cell in rows[-1]:
        cell.border = cell.border + bottom

    for row in rows:
        l = row[0]
        r = row[-1]
        l.border = l.border + left
        r.border = r.border + right
        if fill:
            for c in row:
                c.fill = fill


def amountFixed(amount):
    return "{:.2f}".format(amount)


def paddingAmount(amount):
    return "{:10.2f}".format(amount).replace('.', '')


def daxie(n):
    if n == ' ':
        return ' '

    return ' ' + '零壹贰叁肆伍陆柒捌玖'[int(n)] + ' '


daxieUnit = ['佰', '拾', '万', '仟', '佰', '拾', '元', '角', '分']


def convertToDaxieAmount(amount):
    first = True
    text = ''

    for index, ch in enumerate(paddingAmount(amount)):
        dx = daxie(ch)
        if first and dx == ' ':
            continue

        first = False
        text = text + dx + daxieUnit[index]

    return text


def inBounds(range, cell):
    start, end = range.split(':')
    start_col = ord(start[0]) - ord('A') + 1
    start_row = int(start[1:])
    end_col = ord(end[0]) - ord('A') + 1
    end_row = int(end[1:])
    bounds = [start_col, start_row, end_col, end_row]

    return bounds[0] <= cell.bounds[0] and bounds[1] <= cell.bounds[1] \
           and bounds[2] >= cell.bounds[2] and bounds[3] >= cell.bounds[3]


def exportOpenAccountAuditDoc(activity):
    account = activity.extra['account']

    cwd = os.getcwd()
    wb = load_workbook(cwd + '/xlsx-templates/open_account.xlsx')
    ws = wb.active

    ws['B2'].value = '厘米脚印（北京）科技有限公司'
    ws['B2'].value = account['name']

    ws['B3'].value = account['bank']
    ws['E3'].value = account.get('time', '')

    ws['B4'].value = account['reason']

    ws['B5'].value = activity.creator.name
    owner = activity.creator.owner
    ceo = Profile.objects.filter(position__code='ceo').first()
    ws['D5'].value = owner.name if owner is not None else ''
    ws['F5'].value = ceo.name if ceo is not None else ''

    ws['B6'].value = activity.created_at.strftime('%Y-%m-%d')
    ws['B7'].value = account.get('desc', '')

    # fix border style
    style_range(ws, 'B2:F2', border=Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'B3:C3', border=Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'E3:F3', border=Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'B4:F4', border=Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'B6:F6', border=Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'B7:F7', border=Border(top=thin, left=thin, right=thin, bottom=thin))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


def exportCostAuditDoc(activity):
    items = activity.extra['items']
    template = ''
    rows = [3, 5, 7, 9, 11, 13, 15]
    for row in rows:
        if len(items) <= row:
            template = 'cost-{}.xlsx'.format(row)
            break

    wb = load_workbook(os.getcwd() + '/xlsx-templates/{}'.format(template))
    ws = wb.active

    # cost items
    first_item_row = 5
    totalAmount = 0
    for i in range(len(items)):
        item = items[i]

        r = str(first_item_row + i)
        ws['B' + r] = item['name']
        ws['B' + r].alignment = Alignment(horizontal='center', vertical='center')
        ws['C' + r] = item['desc']
        ws['B' + r].alignment = Alignment(horizontal='center', vertical='center')

        amount = float(item['amount'])
        totalAmount = amount + totalAmount

        amount = paddingAmount(float(item['amount']))
        for j, ch in enumerate(amount):
            col = chr(ord('E') + j)
            ws[col + r] = ch

    # 统计
    r = 5 + row
    for j, ch in enumerate(paddingAmount(totalAmount)):
        col = chr(ord('E') + j)
        ws[col + str(r)] = ch

    # 大写金额
    r = r + 1
    first = True
    daxieText = '金额大写：'
    for index, ch in enumerate(paddingAmount(totalAmount)):
        dx = daxie(ch)
        if first and dx == ' ':
            continue

        first = False
        daxieText = daxieText + dx + daxieUnit[index]
    ws['B' + str(r)] = daxieText

    # FIXME: 原借款/退补款
    ws['D' + str(r)] = '原借款：{} 元'.format('')
    ws['D' + str(r)].alignment = Alignment(horizontal='left', vertical='center')
    ws['N' + str(r)] = '退（补）款：{} 元'.format('')

    creator = activity.creator
    owner = creator.owner
    finOwner = Profile.objects.filter(department__code='fin', position__code='owner').first()
    finAccountant = Profile.objects.filter(department__code='fin', position__code='accountant').first()
    hrOwner = Profile.objects.filter(department__code='hr', position__code='owner').first()
    ceo = Profile.objects.filter(department__code='root', position__code='ceo').first()

    # 报销人/部分负责人/财务负责人
    ws['C' + str(r + 1)] = '报销人：{}'.format(getattr(creator, 'name', ''))
    ws['C' + str(r + 2)] = '部门负责人：{}'.format(getattr(owner, 'name', ''))
    ws['C' + str(r + 3)] = '财务负责人：{}'.format(getattr(finOwner, 'name'))

    ## 财务会计/人力行政负责人/公司负责人
    ws['D' + str(r + 1)] = '财务会计：{}'.format(getattr(finAccountant, 'name', ''))
    ws['D' + str(r + 2)] = '人力行政负责人：{}'.format(getattr(hrOwner, 'name', ''))
    ws['D' + str(r + 3)] = '公司负责人：{}'.format(getattr(ceo, 'name', ''))

    ## 表头信息
    dp = creator.department.name if creator.department is not None else ''
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    ws['B2'] = '报销部门：{}                        {}                      单据及附件共 {} 页' \
        .format(dp, date, str(len(items)))

    ## 账号信息系
    account = activity.extra['account']
    ws['O3'] = '户名：{}\n收款账号:{} \n开户行：{}' \
        .format(account['name'], account['number'], account['bank'])
    ws['O3'].alignment = Alignment(vertical='center', wrapText=True)

    # fix border tyle
    style_range(ws, 'B3:B4', Border(top=medium, left=medium, right=thin, bottom=thin))
    style_range(ws, 'C3:C4', Border(top=medium, left=thin, right=thin, bottom=thin))
    style_range(ws, 'E3:M3', Border(top=medium, left=thin, right=thin, bottom=thin))

    style_range(ws, 'N3:N' + str(5 + row), Border(top=medium, left=thin, right=thin, bottom=thin))
    style_range(ws, 'O3:O' + str(5 + row), Border(top=medium, left=thin, right=medium, bottom=thin))

    style_range(ws, 'D{}:M{}'.format(r, r), Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'N{}:O{}'.format(r, r), Border(top=thin, left=thin, right=medium, bottom=thin))

    style_range(ws, 'D{}:O{}'.format(r + 1, r + 1), Border(top=thin, left=thin, right=medium, bottom=thin))
    style_range(ws, 'D{}:O{}'.format(r + 2, r + 2), Border(top=thin, left=thin, right=medium, bottom=thin))
    style_range(ws, 'D{}:O{}'.format(r + 3, r + 3), Border(top=thin, left=thin, right=medium, bottom=medium))

    style_range(ws, 'B{}:B{}'.format(r + 1, r + 3), Border(top=thin, left=medium, right=thin, bottom=medium))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


def exportLoanAuditDoc(activity):
    wb = load_workbook(os.getcwd() + '/xlsx-templates/loan.xlsx')
    ws = wb.active

    auditData = activity.extra
    creator = activity.creator
    ws['B3'] = '部门:{}                {}                      编号:{}'. \
        format(getattr(creator.department, 'name', ''),
               datetime.datetime.now().strftime('%Y-%m-%d'),
               activity.sn)
    # FIXME: 今借到

    # 人民币大写
    amount = float(auditData['loan']['amount'])
    ws['B5'] = '人民币（大写） {}  此据'.format(convertToDaxieAmount(amount))
    ws['B5'].alignment = Alignment(vertical='center', wrapText=True)

    # 人民币小写
    ws['B6'] = '（小写）￥ {}'.format(amountFixed(float(auditData['loan']['amount'])))
    ws['B6'].alignment = Alignment(vertical='center', wrapText=True)

    # 借款用途说明
    ws['C7'] = auditData['loan']['application']
    ws['C7'].alignment = Alignment(vertical='center', wrapText=True)

    # 付款信息
    account = auditData['account']
    ws['C8'] = '户名：{}\n收款账号:{} \n开户行：{}' \
        .format(account['name'], account['number'], account['bank'])
    ws['C8'].alignment = Alignment(vertical='center', wrapText=True)

    # 借款人、部门负责人、财务负责人、公司负责人
    ws['C11'] = creator.name
    ws['C11'].alignment = Alignment(vertical='center', horizontal='center')

    ws['F11'] = getattr(creator.owner, 'name', '')
    ws['F11'].alignment = Alignment(vertical='center', horizontal='center')

    finOwner = Profile.objects.filter(department__code='fin', position__code='owner').first()
    ws['I11'] = getattr(finOwner, 'name', '')
    ws['I11'].alignment = Alignment(vertical='center', horizontal='center')

    ceo = Profile.objects.filter(department__code='root', position__code='ceo').first()
    ws['M11'] = getattr(ceo, 'name', '')
    ws['M11'].alignment = Alignment(vertical='center', horizontal='center')

    # fix border style
    style_range(ws, 'B4:P4', Border(top=medium, left=medium, right=medium, bottom=thin))
    style_range(ws, 'B5:P5', Border(top=thin, left=medium, right=medium, bottom=thin))
    style_range(ws, 'B6:P6', Border(top=thin, left=medium, right=medium, bottom=thin))
    style_range(ws, 'C7:P7', Border(top=thin, left=thin, right=medium, bottom=thin))
    style_range(ws, 'B8:B9', Border(top=thin, left=medium, right=thin, bottom=thin))
    style_range(ws, 'C8:P9', Border(top=thin, left=thin, right=medium, bottom=thin))

    style_range(ws, 'B10:B11', Border(top=thin, left=medium, right=thin, bottom=medium))

    style_range(ws, 'C10:E10', Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'C11:E11', Border(top=thin, left=thin, right=thin, bottom=medium))
    style_range(ws, 'F10:H10', Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'F11:H11', Border(top=thin, left=thin, right=thin, bottom=medium))
    style_range(ws, 'I10:L10', Border(top=thin, left=thin, right=thin, bottom=thin))
    style_range(ws, 'I11:L11', Border(top=thin, left=thin, right=thin, bottom=medium))
    style_range(ws, 'M10:P10', Border(top=thin, left=thin, right=medium, bottom=thin))
    style_range(ws, 'M11:P11', Border(top=thin, left=thin, right=medium, bottom=medium))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


def exportMoneyAuditDoc(activity):
    wb = load_workbook(os.getcwd() + '/xlsx-templates/money.xlsx')
    ws = wb.active

    auditData = activity.extra
    creator = activity.creator
    ws['A2'] = '   用款部门:{}                                                       {}'. \
        format(getattr(creator.department, 'name', ''),
               datetime.datetime.now().strftime('%Y-%m-%d'))

    # 收款信息
    info = auditData['info']
    inAccount = auditData['inAccount']
    ws['B3'] = inAccount['name']
    ws['B4'] = inAccount['bank']
    ws['H4'] = inAccount['number']
    ws['B5'] = '（大写）{}'.format(convertToDaxieAmount(float(info['amount'])))
    ws['J5'] = '￥{}'.format(amountFixed(float(info['amount'])))

    # 出款信息
    outAccount = auditData['outAccount']
    ws['B6'] = outAccount['name']
    ws['k6'] = '现金' if outAccount['type'] == 'cash' else '转账'
    ws['B7'] = outAccount['bank']
    ws['H7'] = outAccount['number']

    ws['B8'] = info['desc']

    # 借款人、部门负责人、财务负责人、公司负责人
    ws['B10'] = creator.name
    ws['B10'].alignment = Alignment(vertical='center', horizontal='center')

    ws['H10'] = getattr(creator.owner, 'name', '')
    ws['H10'].alignment = Alignment(vertical='center', horizontal='center')

    finOwner = Profile.objects.filter(department__code='fin', position__code='owner').first()
    ws['B12'] = getattr(finOwner, 'name', '')
    ws['B12'].alignment = Alignment(vertical='center', horizontal='center')

    ceo = Profile.objects.filter(department__code='root', position__code='ceo').first()
    ws['H12'] = getattr(ceo, 'name', '')
    ws['H12'].alignment = Alignment(vertical='center', horizontal='center')

    # A3:M3
    for cell in ws.merged_cells:
        if not inBounds('A3:M12', cell):
            logger.info('ignore cell: {}'.format(cell.coord))
            continue

        logger.info('fix border style {}'.format(cell.coord))
        style_range(ws, cell.coord, Border(top=thin, left=thin, right=thin, bottom=thin))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


def exportBizContractAuditDoc(activity):
    wb = load_workbook(os.getcwd() + '/xlsx-templates/biz_contract.xlsx')
    ws = wb.active

    creator = activity.creator
    auditData = activity.extra
    base = auditData['base']
    info = auditData['info']

    ws['A3'] = '合同类型：{}                                                    {}'.format(
        '大宗类' if base['type'] == 'dazong' else '其他类',
        datetime.datetime.now().strftime('%Y-%m-%d'))
    # FIXME 签订公司名称
    ws['B4'] = base['name']

    ws['B5'] = info['upstream']
    ws['F5'] = info['downstream']
    ws['B6'] = info['asset']
    ws['F6'] = info['tonnage']
    ws['B7'] = info['proportion']
    ws['F7'] = info['profitsPerTon'] + '%'
    ws['B8'] = info['buyPrice']
    ws['F8'] = info['sellPrice']
    ws['B9'] = '现金' if info['settlementType'] == 'cash' else '转账'
    ws['B10'] = info['grossMargin'] + '%'
    ws['B11'] = info.get('desc', '')
    ws['B12'] = creator.name
    ws['E12'] = getattr(creator.owner, 'name', '')
    # TODO: 法务负责人
    finOwner = Profile.objects.filter(department__code='fin', position__code='owner').first()
    ws['E13'] = getattr(finOwner, 'name', '')
    ceo = Profile.objects.filter(department__code='root', position__code='ceo').first()
    ws['E14'] = getattr(ceo, 'name', '')

    for cell in ws.merged_cells:
        if not inBounds('A4:F19', cell):
            logger.info('ignore cell: {}'.format(cell.coord))
            continue

        logger.info('fix border style {}'.format(cell.coord))
        style_range(ws, cell.coord, Border(top=thin, left=thin, right=thin, bottom=thin))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


def exportFnContractAuditDoc(activity):
    auditData = activity.extra
    info = auditData['info']
    base = auditData['base']
    template = 'fn_contract'
    if float(info['amount']) == 0:
        template = 'fn_contract_zero'

    wb = load_workbook(os.getcwd() + '/xlsx-templates/{}.xlsx'.format(template))
    ws = wb.active

    ws['B3'] = base['name']
    ws['D3'] = base['other']

    ws['B4'] = amountFixed(float(info['amount']))
    ws['D4'] = info.get('date', '')
    ws['B5'] = info['count']
    ws['D5'] = info['sn']
    ws['B6'] = info.get('desc', '')

    # FIXME: 法务负责人
    steps = activity.steps()
    for step in steps:
        dp = None
        if step.assigneeDepartment is not None:
            dp = step.assigneeDepartment.code
        pos = step.assigneePosition.code

        if dp is None and pos == 'owner':
            ws['B7'] = step.desc if step.desc is not None else ''

        if template == 'fn_contract':
            if dp == 'fin' and pos == 'owner':
                ws['B9'] = step.desc if step.desc is not None else ''
            if dp == 'root' and pos == 'ceo':
                ws['B10'] = step.desc if step.desc is not None else ''
        else:
            if dp == 'root' and pos == 'ceo':
                ws['B9'] = step.desc if step.desc is not None else ''

    for cell in ws.merged_cells:
        if not inBounds('A3:D11', cell):
            logger.info('ignore cell: {}'.format(cell.coord))
            continue

        logger.info('fix border style {}'.format(cell.coord))
        style_range(ws, cell.coord, Border(top=thin, left=thin, right=thin, bottom=thin))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


def exportTravelAuditDoc(activity):
    auditData = activity.extra
    creator = activity.creator

    wb = load_workbook(os.getcwd() + '/xlsx-templates/travel.xlsx')
    ws = wb.active
    ws['C3'] = '姓名: {}                 部门: {}                    {}'.format(
        creator.name,
        getattr(creator.department, 'name', ''),
        datetime.datetime.now().strftime('%Y-%m-%d')
    )

    firstItemRow = 8
    items = auditData['items']
    total = {
        'normal': 0,
        'train': 0,
        'car': 0,
        'ship': 0,
        'plane': 0,
        'traffic': 0,
        'other': 0,
        'amount2': 0
    }
    t = 0
    for index, item in enumerate(items):
        def parseDate(str):
            return datetime.datetime.strptime(str, '%Y-%m-%d')

        startDate, endDate = parseDate(item['startTime']), parseDate(item['endTime'])
        row = str(firstItemRow + index)
        ws['C' + row] = startDate.month
        ws['D' + row] = startDate.day
        ws['E' + row] = startDate.year
        ws['F' + row] = endDate.month
        ws['G' + row] = endDate.day
        ws['H' + row] = endDate.year
        days = (endDate - startDate).days + 1
        ws['I' + row] = days

        ws['J' + row] = item['place']
        ws['K' + row] = days
        ws['L' + row] = item['spec']

        normal = float(item['spec']) * days
        total['normal'] = total['normal'] + normal
        ws['M' + row] = normal

        train = float(item.get('train', '0'))
        total['train'] = total['train'] + train
        ws['N' + row] = amountFixed(train)

        car = float(item.get('car', '0'))
        total['car'] = total['car'] + car
        ws['O' + row] = amountFixed(car)

        ship = float(item.get('ship', '0'))
        total['ship'] = total['ship'] + ship
        ws['P' + row] = amountFixed(ship)

        plane = float(item.get('plane', '0'))
        total['plane'] = total['plane'] + plane
        ws['Q' + row] = amountFixed(plane)

        ws['R' + row] = '0.00'

        traffic = float(item.get('traffic', '0'))
        total['traffic'] = total['traffic'] + traffic
        ws['S' + row] = amountFixed(traffic)

        other = float(item.get('other', '0'))
        total['other'] = total['other'] + other
        ws['T' + row] = amountFixed(other)

        # FIXME: 单据张数
        amount1 = train + car + ship + plane + traffic + other
        ws['V' + row] = amountFixed(amount1)

        amount2 = normal + amount1
        total['amount2'] = amount2 + total['amount2']
        ws['W' + row] = amountFixed(amount2)

        t = amount2 + t

    ws['k16'] = amountFixed(total['normal'])
    ws['N16'] = amountFixed(total['train'])
    ws['O16'] = amountFixed(total['car'])
    ws['P16'] = amountFixed(total['ship'])
    ws['Q16'] = amountFixed(total['plane'])
    ws['R16'] = '0.00'
    ws['S16'] = amountFixed(total['traffic'])
    ws['T16'] = amountFixed(total['other'])
    ws['U16'] = '0'
    ws['V16'] = amountFixed(total['amount2'])
    ws['W16'] = amountFixed(t)

    ws['C17'] = '合计人民币（大写）    {}'.format(convertToDaxieAmount(t))
    info = auditData['info']
    ws['C18'] = '原借差旅费 {} 元                 剩余交回 {} 元'.format(
        amountFixed(float(info['yuanjiekuan'])),
        amountFixed(float(info.get('shengyu', '0')))
    )
    ws['D19'] = info.get('reason', '')
    ws['X4'] = '附件共（{}）张'.format(len(auditData.get('attachments', [])))

    for cell in ws.merged_cells:
        if not inBounds('C4:W20', cell):
            logger.info('ignore cell: {}'.format(cell.coord))
            continue

        logger.info('fix border style {}'.format(cell.coord))
        style_range(ws, cell.coord, Border(top=thin, left=thin, right=thin, bottom=thin))

    path = '/tmp/{}.xlsx'.format(str(uuid.uuid4()))
    wb.save(path)
    return path


@require_http_methods(['GET'])
def export(request, activityId):
    # TODO: travel audit
    activity = AuditActivity.objects.get(pk=activityId)
    path, filename = None, None
    if activity.config.subtype == 'open_account':
        path = exportOpenAccountAuditDoc(activity)
        account = activity.extra['account']
        filename = '开户申请审批单_{}_{}.xlsx'.format(account['name'], account['bank'])
    elif re.match('cost', activity.config.subtype):
        path = exportCostAuditDoc(activity)
        filename = '费用报销审批单.xlsx'
    elif re.match('loan', activity.config.subtype):
        path = exportLoanAuditDoc(activity)
        filename = '借款审批单.xlsx'
    elif re.match('money', activity.config.subtype):
        path = exportMoneyAuditDoc(activity)
        filename = '用款审批单.xlsx'
    elif re.match('biz', activity.config.subtype):
        path = exportBizContractAuditDoc(activity)
        filename = '业务合同会签审批.xlsx'
    elif re.match('fn', activity.config.subtype):
        path = exportFnContractAuditDoc(activity)
        filename = '职能合同会签审批.xlsx'
    else:
        # travel
        path = exportTravelAuditDoc(activity)
        filename = '差旅费用报销审批单.xlsx'

    activity.taskState = 'finished'
    activity.save()

    return sendfile(request, path,
                    attachment=True,
                    attachment_filename=filename)