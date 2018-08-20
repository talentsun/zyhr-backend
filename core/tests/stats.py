from decimal import Decimal
import json

from freezegun import freeze_time
from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User

from core import specs
from core.models import *
from core.auth import generateToken
from core.tests import helpers
from core.management.commands import stats


class StatsTestCase(TestCase):
    def test_stop_month(self):
        cmd = stats.Command()
        with freeze_time('2018-12-31'):
            month = cmd.calStopMonth()
            s = month.strftime('%Y-%m')
            self.assertEqual(s, '2019-01')
        with freeze_time('2018-08-31'):
            month = cmd.calStopMonth()
            s = month.strftime('%Y-%m')
            self.assertEqual(s, '2018-09')

    def test_stop_date(self):
        cmd = stats.Command()
        with freeze_time('2018-08-31'):
            date = cmd.calStopDate()
            s = date.strftime('%Y-%m-%d')
            self.assertEqual(s, '2018-09-03')

    def test_cal_next_month(self):
        cmd = stats.Command()
        with freeze_time('2018-12-31'):
            now = timezone.now()
            month = cmd.calNextMonth(now)
            s = month.strftime('%Y-%m-%d')
            self.assertEqual(s, '2019-01-01')

    def _test_transaction_stat(self):
        user = User.objects.create(username='foobar')
        profile = Profile.objects.create(name='foobar', user=user)
        f1 = FinAccount.objects.create(name='fin1', number='95551', bank='招商银行', currency='rmb', creator=profile)
        f2 = FinAccount.objects.create(name='fin2', number='95552', bank='招商银行', currency='dollar', creator=profile)
        f3 = FinAccount.objects.create(name='fin3', number='95553', bank='招商银行', currency='rmb', creator=profile)

        cmd = stats.Command()
        cmd.calTransactionStats()
        tss = TransactionStat.objects.filter(category='week')
        self.assertEqual(tss.count(), 0)

        STR = StatsTransactionRecord
        STR.objects.create(date='2018-07-01', number='95551', income=1000, balance=1000, creator=profile)
        STR.objects.create(date='2018-07-01', number='95551', outcome=100, balance=900, creator=profile)
        STR.objects.create(date='2018-07-21', number='95551', outcome=300, balance=600, creator=profile)
        STR.objects.create(date='2018-08-15', number='95551', income=10000, balance=10600, creator=profile)

        STR.objects.create(date='2018-07-01', number='95552', income=1000, balance=1000, creator=profile)
        STR.objects.create(date='2018-07-04', number='95552', outcome=100, balance=900, creator=profile)

        cmd = stats.Command()
        cmd.calTransactionStats()

        ts = TransactionStat.objects.get(category='total', account=f1)
        self.assertEqual(ts.income, 11000)
        self.assertEqual(ts.outcome, 400)
        self.assertEqual(ts.balance, 10600)

        ts = TransactionStat.objects.get(category='total', account=f2)
        self.assertEqual(ts.income, 1000)
        self.assertEqual(ts.outcome, 100)
        self.assertEqual(ts.balance, 900)

        # 2018-07-01 - 2018-08-19: 8 weeks
        tss = TransactionStat.objects.filter(category='week', account=f1).order_by('startDayOfWeek')
        expected = [
            ('2018-06-25', Decimal(1000), Decimal(100), Decimal(900)),
            ('2018-07-02', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-07-09', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-07-16', Decimal(0), Decimal(300), Decimal(600)),
            ('2018-07-23', Decimal(0), Decimal(0), Decimal(600)),
            ('2018-07-30', Decimal(0), Decimal(0), Decimal(600)),
            ('2018-08-06', Decimal(0), Decimal(0), Decimal(600)),
            ('2018-08-13', Decimal(10000), Decimal(0), Decimal(10600)),
        ]
        actual = [(t.startDayOfWeek, t.income, t.outcome, t.balance) for t in tss]
        self.assertListEqual(actual, expected)
        tss = TransactionStat.objects.filter(category='week', account=f2).order_by('startDayOfWeek')
        expected = [
            ('2018-06-25', Decimal(1000), Decimal(0), Decimal(1000)),
            ('2018-07-02', Decimal(0), Decimal(100), Decimal(900)),
            ('2018-07-09', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-07-16', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-07-23', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-07-30', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-08-06', Decimal(0), Decimal(0), Decimal(900)),
            ('2018-08-13', Decimal(0), Decimal(0), Decimal(900)),
        ]
        actual = [(t.startDayOfWeek, t.income, t.outcome, t.balance) for t in tss]
        self.assertListEqual(actual, expected)
        tss = TransactionStat.objects.filter(category='week', account=f3).order_by('startDayOfWeek')
        expected = [
            ('2018-06-25', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-07-02', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-07-09', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-07-16', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-07-23', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-07-30', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-08-06', Decimal(0), Decimal(0), Decimal(0)),
            ('2018-08-13', Decimal(0), Decimal(0), Decimal(0)),
        ]
        actual = [(t.startDayOfWeek, t.income, t.outcome, t.balance) for t in tss]
        self.assertListEqual(actual, expected)

    @freeze_time('2018-08-18')
    def test_transaction_stat(self):
        self._test_transaction_stat()

    @freeze_time('2018-08-18')
    def test_query_transaction_stat(self):
        self._test_transaction_stat()

        user = User.objects.create(username='jack')
        profile = Profile.objects.create(name='jack', user=user, phone='foobar')
        token = generateToken(profile)

        client = Client()
        r = client.get('/api/v1/transaction-record-stats', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 3)
        records = result['records']
        actual = [{
            'name': r['name'],
            'income': r['income'],
            'outcome': r['outcome'],
            'balance': r['balance']
        } for r in records]
        expected = [
            {'name': 'fin1', 'income': '11000.00', 'outcome': '400.00', 'balance': '10600.00'},
            {'name': 'fin2', 'income': '1000.00', 'outcome': '100.00', 'balance': '900.00'},
            {'name': 'fin3', 'income': '0.00', 'outcome': '0.00', 'balance': '0.00'}
        ]
        self.assertListEqual(actual, expected)

    def _test_taizhang_stat_and_customer_stat(self):
        customer_data = [{
            'name': '公司1', 'rating': 'A',
            'shareholder': 'foobar', 'faren': 'foobar', 'capital': 2000, 'year': '2000', 'category': 'c1',
            'nature': 'guoqi', 'address': 'foobar', 'desc': 'foobar'
        }, {
            'name': '公司2', 'rating': 'A',
            'shareholder': 'foobar', 'faren': 'foobar', 'capital': 2000, 'year': '2000', 'category': 'c1',
            'nature': 'guoqi', 'address': 'foobar', 'desc': 'foobar'
        }]
        for c in customer_data:
            Customer.objects.create(**c)

        # 合同金额=上游合同吨位*采购价格, 采购金额=开票吨位*上游结算单价，销售金额=开票吨位（贸易量）*下游结算单价，库存金额=库存数量*库存预计单价
        data = [{
            'date': '2018-05', 'asset': '螺纹钢', 'upstream': '公司1', 'downstream': '公司2',
            'upstream_dunwei': 200, 'buyPrice': 50000,  # 合同金额: 10000000
            'downstream_dunwei': 100, 'sellPrice': 100,
            'kaipiao_dunwei': 199.275, 'upstream_jiesuan_price': 50000,  # 采购金额=9963750
            "kaipiao_dunwei_trade": 199.275, "downstream_jiesuan_price": 50010,  # 销售金额=9965742.75，利润额=1992.75
            "shangyou_kuchun_liang": 190, "shangyou_kuchun_yuji_danjia": 500, 'shangyou_zijin_zhanya': 1000  # 库存量=95000
        }, {
            'date': '2018-05', 'asset': '电解铜', 'upstream': '公司1', 'downstream': '公司2',
            'upstream_dunwei': 200, 'buyPrice': 30000,  # 合同金额: 6000000
            'downstream_dunwei': 100, 'sellPrice': 100,
            'kaipiao_dunwei': 199.275, 'upstream_jiesuan_price': 3000,  # 采购金额=597825
            "kaipiao_dunwei_trade": 199.275, "downstream_jiesuan_price": 3010,  # 销售金额=599817.75，利润额=1992.75
            "shangyou_kuchun_liang": 190, "shangyou_kuchun_yuji_danjia": 20, 'shangyou_zijin_zhanya': 200  # 库存量=3800
        }, {
            'date': '2018-05', 'asset': '电解铜', 'upstream': '公司1', 'downstream': '公司2',
            'upstream_dunwei': 300, 'buyPrice': 30000,  # 合同金额: 9000000
            'downstream_dunwei': 100, 'sellPrice': 100,
            'kaipiao_dunwei': 299.275, 'upstream_jiesuan_price': 3000,  # 采购金额=897825
            "kaipiao_dunwei_trade": 299.275, "downstream_jiesuan_price": 3010,  # 销售金额=900817.75，利润额=2992.75
            "shangyou_kuchun_liang": 290, "shangyou_kuchun_yuji_danjia": 20, 'shangyou_zijin_zhanya': 2000  # 库存量=5800
        }, {
            'date': '2018-06', 'asset': '电解铜', 'upstream': '公司3',
            'upstream_dunwei': 200, 'buyPrice': 30000,  # 合同金额: 6000000
            'downstream_dunwei': 100, 'sellPrice': 100,
            'kaipiao_dunwei': 199.275, 'upstream_jiesuan_price': 3000,  # 采购金额=597825
            "kaipiao_dunwei_trade": 199.275, "downstream_jiesuan_price": 3010,  # 销售金额=599817.75，利润额=1992.75
            "shangyou_kuchun_liang": 190, "shangyou_kuchun_yuji_danjia": 20, 'shangyou_zijin_zhanya': 2000  # 库存量=3800
        }, {
            'date': '2018-07', 'asset': '螺纹钢', 'upstream': '公司1', 'downstream': '公司2',
            'upstream_dunwei': 200, 'buyPrice': 50000,  # 合同金额: 10000000
            'downstream_dunwei': 100, 'sellPrice': 100,
            'kaipiao_dunwei': 199.275, 'upstream_jiesuan_price': 50000,  # 采购金额=9963750
            "kaipiao_dunwei_trade": 199.275, "downstream_jiesuan_price": 50010,  # 销售金额=9965742.75，利润额=1992.75
            "shangyou_kuchun_liang": 190, "shangyou_kuchun_yuji_danjia": 500, 'shangyou_zijin_zhanya': 1000  # 库存量=95000
        }]

        for item in data:
            Taizhang.objects.create(**item)

        cmd = stats.Command()
        cmd._stats()

        tss = TaizhangStat.objects.filter(category='total')
        expect = [
            {'company': '公司1', 'asset': '电解铜', 'xiaoshoue': Decimal('1500635.5'), 'lirune': Decimal('4985.5'),
             'kuchun_liang': Decimal('9600'), 'zijin_zhanya': Decimal('2200')},
            {'company': '公司1', 'asset': '螺纹钢', 'xiaoshoue': Decimal('19931485.5'), 'lirune': Decimal('3985.5'),
             'kuchun_liang': Decimal('190000'), 'zijin_zhanya': Decimal('2000')},

            {'company': '公司2', 'asset': '电解铜', 'xiaoshoue': Decimal('1500635.5'), 'lirune': Decimal('4985.5'),
             'kuchun_liang': Decimal('9600'), 'zijin_zhanya': Decimal('2200')},
            {'company': '公司2', 'asset': '螺纹钢', 'xiaoshoue': Decimal('19931485.5'), 'lirune': Decimal('3985.5'),
             'kuchun_liang': Decimal('190000'), 'zijin_zhanya': Decimal('2000')},

            {'company': '公司3', 'asset': '电解铜', 'xiaoshoue': Decimal('599817.75'), 'lirune': Decimal('1992.75'),
             'kuchun_liang': Decimal('3800'), 'zijin_zhanya': Decimal('2000')},
            {'company': '公司3', 'asset': '螺纹钢', 'xiaoshoue': Decimal('0'), 'lirune': Decimal('0'),
             'kuchun_liang': Decimal('0'), 'zijin_zhanya': Decimal('0')},
        ]
        expect.sort(key=lambda x: x['company'] + x['asset'])
        actual = [{
            'company': t.company,
            'asset': t.asset,
            'xiaoshoue': t.xiaoshoue,
            'lirune': t.lirune,
            'kuchun_liang': t.kuchun_liang,
            'zijin_zhanya': t.zijin_zhanya
        } for t in tss]
        actual.sort(key=lambda x: x['company'] + x['asset'])
        self.assertListEqual(expect, actual)

        tss = TaizhangStat.objects.filter(category='month', company='公司1')
        expect = [
            {'month': '2018-05', 'company': '公司1', 'asset': '螺纹钢', 'xiaoshoue': Decimal('9965742.75'),
             'lirune': Decimal('1992.75'), 'kuchun_liang': Decimal('95000'), 'zijin_zhanya': Decimal('1000')},
            {'month': '2018-05', 'company': '公司1', 'asset': '电解铜', 'xiaoshoue': Decimal('1500635.5'),
             'lirune': Decimal('4985.5'), 'kuchun_liang': Decimal('9600'), 'zijin_zhanya': Decimal('2200')},
            {'month': '2018-06', 'company': '公司1', 'asset': '电解铜', 'xiaoshoue': Decimal('0'),
             'lirune': Decimal('0'), 'kuchun_liang': Decimal('0'), 'zijin_zhanya': Decimal('0')},
            {'month': '2018-06', 'company': '公司1', 'asset': '螺纹钢', 'xiaoshoue': Decimal('0'),
             'lirune': Decimal('0'), 'kuchun_liang': Decimal('0'), 'zijin_zhanya': Decimal('0')},
            {'month': '2018-07', 'company': '公司1', 'asset': '螺纹钢', 'xiaoshoue': Decimal('9965742.75'),
             'lirune': Decimal('1992.75'), 'kuchun_liang': Decimal('95000'), 'zijin_zhanya': Decimal('1000')},
            {'month': '2018-07', 'company': '公司1', 'asset': '电解铜', 'xiaoshoue': Decimal('0'),
             'lirune': Decimal('0'), 'kuchun_liang': Decimal('0'), 'zijin_zhanya': Decimal('0')},
            {'month': '2018-08', 'company': '公司1', 'asset': '螺纹钢', 'xiaoshoue': Decimal('0'),
             'lirune': Decimal('0'), 'kuchun_liang': Decimal('0'), 'zijin_zhanya': Decimal('0')},
            {'month': '2018-08', 'company': '公司1', 'asset': '电解铜', 'xiaoshoue': Decimal('0'),
             'lirune': Decimal('0'), 'kuchun_liang': Decimal('0'), 'zijin_zhanya': Decimal('0')},
        ]
        expect.sort(key=lambda x: x['month'] + x['company'] + x['asset'])
        actual = [{
            'month': t.month,
            'company': t.company,
            'asset': t.asset,
            'xiaoshoue': t.xiaoshoue,
            'lirune': t.lirune,
            'kuchun_liang': t.kuchun_liang,
            'zijin_zhanya': t.zijin_zhanya
        } for t in tss]
        actual.sort(key=lambda x: x['month'] + x['company'] + x['asset'])
        self.assertListEqual(expect, actual)

        css = CustomerStat.objects.filter(category='total')
        expect = [
            {'customer': '公司1', 'yewuliang': Decimal('35000000')},
            {'customer': '公司2', 'yewuliang': Decimal('35000000')},
        ]
        expect.sort(key=lambda x: x['customer'])
        actual = [{
            'customer': c.customer.name,
            'yewuliang': c.yewuliang
        } for c in css]
        actual.sort(key=lambda x: x['customer'])
        self.assertListEqual(expect, actual)

        css = CustomerStat.objects.filter(category='month')
        expect = [
            {'customer': '公司1', 'month': '2018-05', 'yewuliang': Decimal('25000000')},
            {'customer': '公司2', 'month': '2018-05', 'yewuliang': Decimal('25000000')},
            {'customer': '公司1', 'month': '2018-06', 'yewuliang': Decimal('0')},
            {'customer': '公司2', 'month': '2018-06', 'yewuliang': Decimal('0')},
            {'customer': '公司1', 'month': '2018-07', 'yewuliang': Decimal('10000000')},
            {'customer': '公司2', 'month': '2018-07', 'yewuliang': Decimal('10000000')},
            {'customer': '公司1', 'month': '2018-08', 'yewuliang': Decimal('0')},
            {'customer': '公司2', 'month': '2018-08', 'yewuliang': Decimal('0')},
        ]
        expect.sort(key=lambda x: x['customer'])
        actual = [{
            'month': c.month,
            'customer': c.customer.name,
            'yewuliang': c.yewuliang
        } for c in css]
        actual.sort(key=lambda x: x['customer'])
        self.assertListEqual(expect, actual)

    @freeze_time('2018-08-18')
    def test_taizhang_stat_and_customer_stat(self):
        self._test_taizhang_stat_and_customer_stat()

    @freeze_time('2018-08-18')
    def test_query_taizhang_stats(self):
        self._test_taizhang_stat_and_customer_stat()

        user = User.objects.create(username='jack')
        profile = Profile.objects.create(name='jack', user=user, phone='foobar')
        token = generateToken(profile)

        client = Client()
        r = client.get('/api/v1/taizhang-stats', HTTP_AUTHORIZATION=token)
        self.assertEqual(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['total'], 6)
        stats = result['stats']
        expect = [
            {'company': '公司1', 'asset': '电解铜', 'xiaoshoue': '1500635.50', 'lirune': '4985.50',
             'kuchun_liang': '9600.00', 'zijin_zhanya': '2200.00'},
            {'company': '公司1', 'asset': '螺纹钢', 'xiaoshoue': '19931485.50', 'lirune': '3985.50',
             'kuchun_liang': '190000.00', 'zijin_zhanya': '2000.00'},

            {'company': '公司2', 'asset': '电解铜', 'xiaoshoue': '1500635.50', 'lirune': '4985.50',
             'kuchun_liang': '9600.00', 'zijin_zhanya': '2200.00'},
            {'company': '公司2', 'asset': '螺纹钢', 'xiaoshoue': '19931485.50', 'lirune': '3985.50',
             'kuchun_liang': '190000.00', 'zijin_zhanya': '2000.00'},

            {'company': '公司3', 'asset': '电解铜', 'xiaoshoue': '599817.75', 'lirune': '1992.75',
             'kuchun_liang': '3800.00', 'zijin_zhanya': '2000.00'},
            {'company': '公司3', 'asset': '螺纹钢', 'xiaoshoue': '0.00', 'lirune': '0.00',
             'kuchun_liang': '0.00', 'zijin_zhanya': '0.00'},
        ]
        self.assertListEqual(stats, expect)
