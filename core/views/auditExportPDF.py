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


def exportPDFData(activity):
    payload = None
    if activity.config.subtype == 'open_account':
        payload = exportOpenAccountPDF(activity)
    elif re.match('cost', activity.config.subtype):
        payload = exportCostAuditPDF(activity)
    # elif re.match('loan', activity.config.subtype):
    #    payload = exportLoanAuditDoc(activity)
    #    filename = '借款审批单.xlsx'
    # elif re.match('money', activity.config.subtype):
    #    payload = exportMoneyAuditDoc(activity)
    #    filename = '用款审批单.xlsx'
    # elif re.match('biz', activity.config.subtype):
    #    path = exportBizContractAuditDoc(activity)
    #    filename = '业务合同会签审批.xlsx'
    # elif re.match('fn', activity.config.subtype):
    #    path = exportFnContractAuditDoc(activity)
    #    filename = '职能合同会签审批.xlsx'
    # elif re.match('travel', activity.config.subtype):
    #    # travel
    #    path = exportTravelAuditDoc(activity)
    #    filename = '差旅费用报销审批单.xlsx'
    # elif activity.config.subtype == 'yongren':
    #    # yongren
    #    path = exportYongrenAuditDoc(activity)
    #    filename = '用人需求审批单.xlsx'
    # elif activity.config.subtype == 'qingjia':
    #    path = exportQingjiaAuditDoc(activity)
    #    filename = '请假申请审批单.xlsx'
    # elif activity.config.subtype == 'chuchai':
    #    path = exportChuchaiAuditDoc(activity)
    #    filename = '出差申请审批单.xlsx'
    # elif activity.config.subtype == 'kaoqin_yichang':
    #    path = exportKaoqinyichangAuditDoc(activity)
    #    filename = '考勤异常申请审批单.xlsx'
    # elif activity.config.subtype == 'zizhi_shiyong':
    #    path = exportZizhishiyongAuditDoc(activity)
    #    filename = '资质使用申请审批单.xlsx'
    # elif activity.config.subtype == 'yinjian_kezhi':
    #    path = exportYinjiankezhiAuditDoc(activity)
    #    filename = '印鉴刻制申请审批单.xlsx'
    # elif activity.config.subtype == 'dangan_jiechu':
    #    path = exportDanganjiechuAuditDoc(activity)
    #    filename = '业务档案原件借出申请审批单.xlsx'
    # elif activity.config.subtype == 'zichan_baofei':
    #    path = exportZichanbaofeiAuditDoc(activity)
    #    filename = '资产报废申请审批单.xlsx'
    # elif activity.config.subtype == 'zichan_caigou':
    #    path = exportZichancaigouAuditDoc(activity)
    #    filename = '资产购置申请审批单.xlsx'
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
    # elif re.match('rongzitikuan', activity.config.subtype):
    #    path = exportRongzitikuanAudit(activity)
    #    filename = '融资提款申请.xlsx'
    else:
        pass

    return payload
