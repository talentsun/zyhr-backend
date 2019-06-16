from decimal import Decimal

from core.common import *


def try_convert_float(s):
    if s[-1] == '元':
        return float(s[0:-1])
    else:
        return float(s)


def paddingAmount(amount):
    return "{:10.2f}".format(amount).replace('.', '')


def daxie(n):
    if n == ' ':
        return ' '

    return ' ' + '零壹贰叁肆伍陆柒捌玖'[int(n)] + ' '


daxieUnit = ['佰', '拾', '万', '仟', '佰', '拾', '元', '角', '分']


def convertToDaxieAmountV2(amount):
    pass


def convertToDaxieAmount(amount):
    return convertToDaxieAmountV2(amount)


def convertToDaxieAmountV2(n):
    units = ['', '万', '亿']
    nums = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
    decimal_label = ['角', '分']
    small_int_label = ['', '拾', '佰', '仟']
    int_part, decimal_part = str(int(n)), str(n - int(n))[2:]  # 分离整数和小数部分

    res = []
    if decimal_part:
        res.append(''.join([nums[int(x)] + y for x, y in list(zip(decimal_part, decimal_label)) if x != '0']))

    if int_part != '0':
        res.append('元')
        while int_part:
            small_int_part, int_part = int_part[-4:], int_part[:-4]
            tmp = ''.join([nums[int(x)] + (y if x != '0' else '') for x, y in
                           list(zip(small_int_part[::-1], small_int_label))[::-1]])
            tmp = tmp.rstrip('零').replace('零零零', '零').replace('零零', '零')
            unit = units.pop(0)
            if tmp:
                tmp += unit
                res.append(tmp)
    r = ''.join(res[::-1])

    if not decimal_part or decimal_part == '0':
        r = r + '整'

    return r


def convertToDaxieAmountV1(amount):
    first = True
    text = ''

    for index, ch in enumerate(paddingAmount(amount)):
        dx = daxie(ch)
        if first and dx == ' ':
            continue

        first = False
        text = text + dx + daxieUnit[index]

    return text


def amountFixed(amount):
    return "{0:,.2f}".format(amount)


def exportOpenAccountPDF(activity):
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    natures = [
        {'value': "basic", 'label': "基本账户"},
        {'value': "normal", 'label': "一般账户"},
        {'value': "temporary", 'label': "临时账户"},
        {'value': "special", 'label': "专用账户"}
    ]
    account = ret['extra']['account']
    nature = account.get('nature', '')
    for n in natures:
        if n['value'] == nature:
            account['nature_text'] = n['label']
    return ret


def exportCostAuditPDF(activity):
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')
    items = ret['extra'].get('items', [])

    totalAmount = 0
    tuibukuan = Decimal('0')
    yuanjiekuan = Decimal('0')
    for item in items:
        tuibukuan = tuibukuan + Decimal(item['tuibukuan'])
        yuanjiekuan = yuanjiekuan + Decimal(item['yuanjiekuan'])

        amount = try_convert_float(item['amount'])
        totalAmount = amount + totalAmount

        amount = paddingAmount(try_convert_float(item['amount']))
        item['numbers'] = []
        for j, ch in enumerate(amount):
            item['numbers'].append(ch)

    heji_numbers = []
    for j, ch in enumerate(paddingAmount(totalAmount)):
        heji_numbers.append(ch)
    ret['extra']['heji_numbers'] = heji_numbers
    ret['extra']['daxie_jine'] = '金额大写：' + convertToDaxieAmount(totalAmount)
    ret['extra']['yuanjiekuan'] = '原借款：{} 元'.format(amountFixed(yuanjiekuan))
    ret['extra']['tuibukuan'] = '退（补）款：{} 元'.format(amountFixed(tuibukuan))

    account = ret['extra']['account']
    ret['extra']['zhanghu_xinxi'] = '户名：{}\n收款账号:{} \n开户行：{}'. \
        format(account['name'], account['number'], account['bank'])

    return ret


def exportLoanAuditPDF(activity):
    auditData = activity.extra
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')
    amount = try_convert_float(auditData['loan']['amount'])
    ret['extra']['rmb_big_text'] = '人民币（大写） {}  此据'.format(convertToDaxieAmount(amount))
    ret['extra']['rmb_normal_text'] = '（小写）￥ {}'.format(amountFixed(try_convert_float(auditData['loan']['amount'])))
    account = auditData['account']
    ret['extra']['fukuan_text'] = '户名：{}\n收款账号:{} \n开户行：{}' \
        .format(account['name'], account['number'], account['bank'])
    return ret


def exportMoneyAuditPDF(activity):
    auditData = activity.extra
    info = auditData['info']

    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    ret['extra']['daxie_yingfu'] = '（大写）{}'.format(convertToDaxieAmount(try_convert_float(info['amount'])))
    ret['extra']['xiaoxie_yingfu'] = '￥' + amountFixed(try_convert_float(info['amount']))
    outAccount = auditData['outAccount']
    ret['extra']['fukuan_fangshi'] = '现金' if outAccount['type'] == 'cash' else '转账'

    return ret


def exportRongzitikuanPDF(activity):
    # auditData = activity.extra
    # info = auditData['info']

    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    return ret


def exportFnContractAuditPDF(activity):
    auditData = activity.extra
    info = auditData['info']

    ret = resolve_activity(activity)
    ret['extra']['hetong_jine'] = try_convert_float(info['amount'])

    return ret


def exportBizContractAuditPDF(activity):
    auditData = activity.extra
    base = auditData['base']
    info = auditData['info']

    ret = resolve_activity(activity)
    ret['extra']['hetong_leixing'] = '大宗类' if base['type'] == 'dazong' else '其他类'
    ret['extra']['hetong_shuliang'] = amountFixed(try_convert_float(info['tonnage'])) + '吨'
    ret['extra']['caigou_jiage'] = amountFixed(try_convert_float(info['buyPrice'])) + '元/吨'

    ret['extra']['jiesuan_fangshi'] = '现金' if info['settlementType'] == 'cash' else '转账'
    ret['extra']['xiaoshou_jiage'] = amountFixed(try_convert_float(info['sellPrice'])) + '元/吨'

    return ret


def exportZizhishiyongAuditPDF(activity):
    auditData = activity.extra

    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    usage = activity.extra['usage']
    auditData['shifoudaichu'] = '是否带出：{}'.format('是' if usage['out'] == '1' else '否')

    date = usage['date'] if 'date' in usage else '无'
    member = usage['member'] if 'member' in usage else '无'
    desc = usage['desc'] if 'desc' in usage else '无'
    auditData['yujiguihuan'] = '1.预计归还时间：{}             2. 陪同人员：{}\n3.其他说明事项：{}'.format(date, member, desc)

    return ret


def exportZichancaigouAuditPDF(activity):
    auditData = activity.extra

    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    items = auditData['items']
    for index, item in enumerate(items):
        item['jine'] = amountFixed(try_convert_float(item['price']) * try_convert_float(item['num']))

    return ret


def exportZichanbaofeiAuditPDF(activity):
    auditData = activity.extra

    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    return ret


def exportDanganjiechuAuditPDF(activity):
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    return ret


def exportYinjiankezhiAuditPDF(activity):
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    return ret


def exportKaoqinyichangAuditPDF(activity):
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    info = activity.extra
    startDate = datetime.datetime.strptime(info['date'][0], "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)
    endDate = datetime.datetime.strptime(info['date'][1], "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)
    dayStr = '自' + startDate.strftime('%Y-%m-%d %H:%M') + '到' + endDate.strftime('%Y-%m-%d %H:%M')
    info['daterange'] = dayStr

    return ret


def exportChuchaiAuditPDF(activity):
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    return ret


def exportQingjiaAuditPDF(activity):
    info = activity.extra
    ret = resolve_activity(activity)
    ret['createdAt'] = activity.created_at.strftime('%Y-%m-%d')

    typeOptions = [
        {'id': 1, 'name': "事假"},
        {'id': 2, 'name': "病假"},
        {'id': 3, 'name': "工伤假"},
        {'id': 4, 'name': "年休假"},
        {'id': 5, 'name': "婚假"},
        {'id': 6, 'name': "产假"},
        {'id': 7, 'name': "产检假"},
        {'id': 8, 'name': "看护假"},
        {'id': 9, 'name': "哺乳假"},
        {'id': 10, 'name': "丧假"},
        {'id': 11, 'name': "考试假"},
        {'id': 100, 'name': "其他"}
    ]
    for o in typeOptions:
        if info['type'] == o['id']:
            info['typeName'] = o['name']

    startDate = datetime.datetime.strptime(info['date'][0], "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)
    endDate = datetime.datetime.strptime(info['date'][1], "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)
    dateStr = startDate.strftime('%Y-%m-%d %H:%M') + ' - ' + endDate.strftime('%Y-%m-%d %H:%M')
    if 'days' in info:
        dateStr = dateStr + '   ' + '共 {} 天'.format(info['days'])
    info['datestr'] = dateStr

    return ret


def exportPDFData(activity):
    payload = None
    if activity.config.subtype == 'open_account':
        payload = exportOpenAccountPDF(activity)
    elif re.match('cost', activity.config.subtype):
        payload = exportCostAuditPDF(activity)
    elif re.match('loan', activity.config.subtype):
        payload = exportLoanAuditPDF(activity)
    elif re.match('money', activity.config.subtype):
        payload = exportMoneyAuditPDF(activity)
    elif re.match('biz', activity.config.subtype):
        payload = exportBizContractAuditPDF(activity)
    elif re.match('fn', activity.config.subtype):
        payload = exportFnContractAuditPDF(activity)
    # elif re.match('travel', activity.config.subtype):
    #    # travel
    #    path = exportTravelAuditDoc(activity)
    #    filename = '差旅费用报销审批单.xlsx'
    # elif activity.config.subtype == 'yongren':
    #    # yongren
    #    path = exportYongrenAuditDoc(activity)
    #    filename = '用人需求审批单.xlsx'
    elif activity.config.subtype == 'qingjia':
        payload = exportQingjiaAuditPDF(activity)
    elif activity.config.subtype == 'chuchai':
        payload = exportChuchaiAuditPDF(activity)
    elif activity.config.subtype == 'kaoqin_yichang':
        payload = exportKaoqinyichangAuditPDF(activity)
    elif activity.config.subtype == 'zizhi_shiyong':
        payload = exportZizhishiyongAuditPDF(activity)
    elif activity.config.subtype == 'yinjian_kezhi':
        payload = exportYinjiankezhiAuditPDF(activity)
    elif activity.config.subtype == 'dangan_jiechu':
        payload = exportDanganjiechuAuditPDF(activity)
    elif activity.config.subtype == 'zichan_baofei':
        payload = exportZichanbaofeiAuditPDF(activity)
    elif activity.config.subtype == 'zichan_caigou':
        payload = exportZichancaigouAuditPDF(activity)
    # elif activity.config.subtype == 'zhuanzheng':
    #    path = exportZhuanzhengAuditDoc(activity)
    #    filename = '员工转正评定审批单.xlsx'
    # elif activity.config.subtype == 'leave':
    #    path = exportLeaveAuditDoc(activity)
    #    filename = '离职申请审批单.xlsx'
    # elif activity.config.subtype == 'leave_handover':
    #    path = exportLeaveHandoverAuditDoc(activity)
    #    filename = '离职交接审批单.xlsx'
    # elif activity.config.subtype == 'transfer':
    #    path = exportTransferAudit(activity)
    #    filename = '内部调动审批单.xlsx'
    elif re.match('rongzitikuan', activity.config.subtype):
        payload = exportRongzitikuanPDF(activity)
    else:
        pass

    return payload
