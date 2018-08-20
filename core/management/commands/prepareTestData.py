import random
import string

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from core.models import *
from core import specs


class Command(BaseCommand):
    def handle(self, *args, **options):
        profile = Profile.objects.get(name='ceo')
        f1 = FinAccount.objects.create(name='fin1', number='95551', bank='招商银行', currency='rmb', creator=profile)
        f2 = FinAccount.objects.create(name='fin2', number='95552', bank='招商银行', currency='dollar', creator=profile)
        f3 = FinAccount.objects.create(name='fin3', number='95553', bank='招商银行', currency='rmb', creator=profile)

        STR = StatsTransactionRecord
        STR.objects.create(date='2018-07-01', number='95551', income=1000, balance=1000, creator=profile)
        STR.objects.create(date='2018-07-01', number='95551', outcome=100, balance=900, creator=profile)
        STR.objects.create(date='2018-07-21', number='95551', outcome=300, balance=600, creator=profile)
        STR.objects.create(date='2018-08-15', number='95551', income=10000, balance=10600, creator=profile)

        STR.objects.create(date='2018-07-01', number='95552', income=1000, balance=1000, creator=profile)
        STR.objects.create(date='2018-07-04', number='95552', outcome=100, balance=900, creator=profile)

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
