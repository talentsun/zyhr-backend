import time
import schedule
import logging
from decimal import Decimal
from pytz import timezone as tz

from django.db.models import Q
from django.core.management.base import BaseCommand

from core.models import *

logger = logging.getLogger('app.core.views.stats')


class Command(BaseCommand):
    def calTransactionStatsForAccountTotal(self, account, startDate=None, endDate=None):
        # calculate balance
        records = StatsTransactionRecord.objects.filter(number=account.number, archived=False)
        if endDate is not None:
            records = records.filter(date__lt=endDate.strftime('%Y-%m-%d'))

        lastRecord = records.order_by('-pk').first()
        balance = Decimal(0)
        if lastRecord is not None:
            balance = Decimal(lastRecord.balance)

        # calculate income / outcome
        records = StatsTransactionRecord.objects \
            .filter(number=account.number, archived=False)
        if startDate is not None and endDate is not None:
            records = records \
                .filter(date__gte=startDate.strftime('%Y-%m-%d'),
                        date__lt=endDate.strftime('%Y-%m-%d'))

        income = Decimal(0.0)
        outcome = Decimal(0.0)
        for r in records:
            if r.income is not None:
                income = income + Decimal(r.income)
            if r.outcome is not None:
                outcome = outcome + Decimal(r.outcome)

        return balance, income, outcome

    def resolveFirstWeekdayForTransaction(self):
        r = StatsTransactionRecord.objects \
            .filter(archived=False) \
            .order_by('date') \
            .first()

        if r is None:
            return None

        d = datetime.datetime.strptime(r.date, '%Y-%m-%d')
        d = d - datetime.timedelta(days=d.weekday())
        d = d.replace(tzinfo=tz('Asia/Shanghai'))
        return d

    def calTransactionStats(self):
        TransactionStat.objects.all().delete()

        accounts = FinAccount.objects.filter(archived=False)
        for account in accounts:
            balance, income, outcome = self.calTransactionStatsForAccountTotal(account)
            TransactionStat.objects.create(account=account,
                                           balance=balance,
                                           income=income,
                                           outcome=outcome,
                                           category='total')

        date = self.resolveFirstWeekdayForTransaction()
        if date is None:
            # no record just now
            return

        nextDate = date + datetime.timedelta(days=7)
        stopDate = self.calStopDate()
        while nextDate < stopDate:
            for account in accounts:
                balance, income, outcome = \
                    self.calTransactionStatsForAccountTotal(account,
                                                            startDate=date,
                                                            endDate=nextDate)
                TransactionStat.objects.create(account=account,
                                               balance=balance,
                                               income=income,
                                               outcome=outcome,
                                               startDayOfWeek=date.strftime('%Y-%m-%d'),
                                               category='week')
            date = nextDate
            nextDate = date + datetime.timedelta(days=7)

    def resolveCompaniesAndAssets(self):
        companies = set()
        records = Taizhang.objects.filter(archived=False).values('upstream').distinct()
        for r in records:
            companies.add(r['upstream'])
        records = Taizhang.objects.filter(archived=False).values('downstream').distinct()
        for r in records:
            downstream = r.get('downstream', None)
            if downstream is not None and downstream != '':
                companies.add(downstream)

        companies = list(companies)

        assets = set()
        records = Taizhang.objects.all().values('asset').distinct()
        for r in records:
            assets.add(r['asset'])
        assets = list(assets)

        return companies, assets

    def calTaizhangStateByCompanyAndAsset(self, company, asset=None, month=None):
        xiaoshoue = Decimal(0.0)
        caigoue = Decimal(0.0)
        lirune = Decimal(0.0)
        kuchun_liang = Decimal(0.0)
        zijin_zhanya = Decimal(0.0)

        commonParams = {'archived': False}
        if asset is not None:
            commonParams['asset'] = asset
        if month is not None:
            commonParams['date'] = month

        records = Taizhang.objects \
            .filter(Q(upstream=company) | Q(downstream=company), **commonParams)

        # 销售金额
        for r in records:
            xiaoshoue = r.xiaoshou_jine + xiaoshoue

        # 采购金额
        caigoue = Decimal(0.0)
        for r in records:
            caigoue = r.caigou_jine + caigoue

        # 利润额
        lirune = xiaoshoue - caigoue

        # 库存量
        for r in records:
            kuchun_liang = r.kuchun_jine + kuchun_liang

        # 资金占压
        for r in records:
            zijin_zhanya = r.shangyou_zijin_zhanya + zijin_zhanya

        return {
            'xiaoshoue': xiaoshoue,
            'lirune': lirune,
            'kuchun_liang': kuchun_liang,
            'zijin_zhanya': zijin_zhanya
        }

    def resolveFirstMonthForTaizhang(self):
        r = Taizhang.objects.filter(archived=False).order_by('date').first()
        if r is None:
            return None
        else:
            d = datetime.datetime.strptime(r.date, '%Y-%m')
            return d

    def calStopDate(self):
        now = timezone.now()
        nextWeek = now + datetime.timedelta(days=7)
        return nextWeek - datetime.timedelta(days=nextWeek.weekday())

    def calStopMonth(self):
        now = timezone.now()
        if now.month == 12:
            nextMonth = datetime.datetime(year=now.year + 1, month=1, day=1)
        else:
            nextMonth = datetime.datetime(year=now.year, month=now.month + 1, day=1)
        return nextMonth

    def calNextMonth(self, month):
        if month.month == 12:
            nextMonth = datetime.datetime(year=month.year + 1, month=1, day=1)
        else:
            nextMonth = datetime.datetime(year=month.year, month=month.month + 1, day=1)
        return nextMonth

    def calTaizhangStats(self):
        TaizhangStat.objects.all().delete()

        companies, assets = self.resolveCompaniesAndAssets()
        for company in companies:
            for asset in assets:
                data = self.calTaizhangStateByCompanyAndAsset(company, asset=asset)
                TaizhangStat.objects.create(category='total',
                                            company=company,
                                            asset=asset,
                                            **data)

        month = self.resolveFirstMonthForTaizhang()
        if month is None:
            return

        nextMonth = self.calNextMonth(month)
        stopMonth = self.calStopMonth()
        while month < stopMonth:
            monthText = month.strftime('%Y-%m')
            for company in companies:
                for asset in assets:
                    data = self.calTaizhangStateByCompanyAndAsset(
                        company, asset=asset, month=monthText)
                    TaizhangStat.objects.create(category='month',
                                                company=company,
                                                asset=asset,
                                                month=monthText,
                                                **data)
            month = nextMonth
            nextMonth = self.calNextMonth(month)

    def calCustomerStatsByCustomer(self, customer, month=None):
        records = Taizhang.objects.filter(Q(upstream=customer.name) | Q(downstream=customer.name),
                                          archived=False)
        if month is not None:
            records = records.filter(date=month)

        yewuliang = Decimal('0.00')
        for r in records:
            yewuliang = yewuliang + r.hetong_jine

        return {'yewuliang': yewuliang}

    def calCustomerStats(self):
        CustomerStat.objects.all().delete()

        customers = Customer.objects.filter(archived=False)
        for c in customers:
            data = self.calCustomerStatsByCustomer(c)
            CustomerStat.objects.create(category='total',
                                        customer=c,
                                        **data)

        month = self.resolveFirstMonthForTaizhang()
        if month is None:
            return

        nextMonth = self.calNextMonth(month)
        stopMonth = self.calStopMonth()
        while month < stopMonth:
            monthText = month.strftime('%Y-%m')
            for customer in customers:
                data = self.calCustomerStatsByCustomer(c, month=monthText)
                CustomerStat.objects.create(category='month',
                                            customer=customer,
                                            month=monthText,
                                            **data)
            month = nextMonth
            nextMonth = self.calNextMonth(month)

    def _stats(self):
        try:
            logger.info('cal stats')
            self.calTransactionStats()
            self.calTaizhangStats()
            self.calCustomerStats()
            logger.info('cal stats done')
        except:
            logger.exception("some error happend")

    def handle(self, *args, **kwargs):
        def job():
            self._stats()

        schedule.every().hour().do(job)

        while True:
            schedule.run_pending()
            time.sleep(1)
