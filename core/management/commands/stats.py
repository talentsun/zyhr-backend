import json
import time
import schedule
import logging
from decimal import Decimal
from pytz import timezone as tz
import requests
from requests.auth import HTTPBasicAuth

from django.db.models import Q
from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import *
from core.signals import *
from core.common import resolveCategoryForAudit

logger = logging.getLogger('app.core.views.stats')


# TODO: rename stats.py to tasks.py
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def calTransactionStatsForAccountTotal(self, account, startDate=None, endDate=None):
        # calculate balance
        records = StatsTransactionRecord.objects.filter(number=account.number, archived=False)
        if endDate is not None:
            records = records.filter(date__lt=endDate.strftime('%Y-%m-%d'))

        lastRecord = records.order_by('-date', '-pk').first()
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
        records = Taizhang.objects.filter(archived=False).values('asset').distinct()
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
            s = r.shangyou_zijin_zhanya
            if s is None:
                s = 0
            zijin_zhanya = s + zijin_zhanya

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
            logger.info("calTaizhangStats for month: {}".format(monthText))
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

        logger.info("calCustomerStatsByCustomer customer: {}, month: {}, record count: {}".format(customer.name, month,
                                                                                                  records.count()))
        yewuliang = Decimal('0.00')
        dunwei = Decimal('0.00')
        for r in records:
            yewuliang = yewuliang + r.hetong_jine
            dunwei = dunwei + r.upstream_dunwei

        r = {'yewuliang': yewuliang, 'dunwei': dunwei}
        if dunwei != 0:
            r['avg_price'] = yewuliang / dunwei
        else:
            r['avg_price'] = 0
        return r

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

            for c in customers:
                try:
                    logger.info(
                        "calculate customer stats by month: {} for customer {}".format(monthText, c.name))
                    data = self.calCustomerStatsByCustomer(c, month=monthText)
                    CustomerStat.objects.create(category='month',
                                                customer=c,
                                                month=monthText,
                                                **data)
                    logger.info(
                        "calculate customer stats by month: {} for customer {}, data: {}".format(monthText, c.name,
                                                                                                 data))
                except:
                    logger.exception("fail to calculate customer stats")

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
            logger.exception("some error happened")

    def resolveNotification(self, msg):
        activity = msg.activity
        categoryName = resolveCategoryForAudit(activity)
        auditCreatedAt = activity.created_at.strftime('%Y-%m-%d')

        if msg.category == 'hurryup':
            title = '催一下'
            content = '您有一笔{}提交的{}审批未处理，请及时审批！'.format(activity.creator.name, categoryName)
        elif msg.category == 'progress':
            title = '审批提醒'
            content = '您有一笔{}提交的{}审批待处理，请及时审批！'.format(activity.creator.name, categoryName)
        else:  # finish
            state = msg.extra['state']
            if state == 'approved':
                title = '审批通过'
                content = '您于 {} 提交的审批单审批通过'.format(auditCreatedAt)
            else:  # rejected
                title = '审批失败'
                content = '您于 {} 提交的审批单审批未通过'.format(auditCreatedAt)

        return {
            'android': {
                'title': title,
                'alert': content,
                'extras': {
                    'category': msg.category,
                    'activity': str(msg.activity.pk)
                }
            },
            'ios': {
                'alert': {
                    'title': title,
                    'body': content
                },
                'extras': {
                    'category': msg.category,
                    'activity': str(msg.activity.pk)
                }
            }
        }

    def sendAPN(self, message):
        try:
            profile = message.profile

            if profile is None or \
                    profile.archived or \
                    profile.blocked or \
                    profile.deviceId is None or \
                    profile.deviceId == '':
                message.apn_sent = True
                message.save()
                return

            r = requests.post('https://api.jpush.cn/v3/push',
                              auth=HTTPBasicAuth(settings.JPUSH_APP_KEY, settings.JPUSH_APP_SECRET),
                              data=json.dumps({
                                  "platform": "all",
                                  "audience": {
                                      "registration_id": [profile.deviceId]
                                  },
                                  "notification": self.resolveNotification(message),
                                  "options": {
                                      "apns_production": settings.JPUSH_APNS_PRODUCTION
                                  }
                              }))
            result = r.json()
            if 'error' not in result:
                message.apn_sent = True
                message.save()
                logger.info("send message activity: {}, profile: {} done".format(str(message.activity.pk),
                                                                                 str(message.profile.pk)))
                return
            else:
                raise Exception(str(result['error']))
        except:
            logger.exception("fail to send message activity: {}, profile: {}".format(str(message.activity.pk),
                                                                                     str(message.profile.pk)))

    def sendAPNIfNeed(self):
        try:
            # 既没有被阅读，有没有被推送的消息
            messages = Message.objects \
                .filter(apn_sent=False,
                        read=False,
                        category__in=['hurryup', 'progress', 'finish'])
            for msg in messages:
                self.sendAPN(msg)
        except:
            logger.exception("some error happens while sending push notifications.")

    def handleAsyncTasks(self):
        tasks = AsyncTask.objects.filter(finished=False, exec_at__lte=timezone.now())

        for task in tasks:
            try:
                if task.category == 'transfer':
                    profileId = task.data['profile']
                    to_department = task.data['to_department']
                    to_position = task.data['to_position']

                    profile = Profile.objects.get(pk=profileId)
                    origin_department = profile.department
                    origin_position = profile.position
                    if not profile.archived:
                        profile.department = Department.objects.get(pk=to_department['id'])
                        profile.position = Position.objects.get(pk=to_position['id'])
                        profile.save()

                    logger.info(
                        "profile transfer, dep: {}, pos: {} to_dep: {}, to_pos: {}".format(
                            origin_department.pk,
                            origin_position.pk,
                            to_department['id'],
                            to_position['id']))
                    user_org_update.send(sender=self, profile=profile)
                    task.finished = True
                    task.save()
                elif task.category == 'stats':
                    self._stats()
                    task.finished = True
                    task.save()
                elif task.category == 'unstick_notifications':
                    logger.info("unstick notifications if need")
                    ns = Notification.objects \
                        .filter(archived=False, stick=True) \
                        .exclude(stick_duration='forever')
                    for n in ns:
                        expired_at = n.published_at + datetime.timedelta(hours=int(n.stick_duration or '0'))
                        if expired_at < timezone.now():
                            logger.info("unstick notification {}".format(n.pk))
                            n.stick = False
                            n.stick_duration = None
                            n.save()
                    task.finished = True
                    task.save()
                    logger.info("unstick notifications if need done")
            except:
                logger.exception("fail to handle task: {}".format(task.pk))

    def handle(self, *args, **kwargs):
        logger.info("stats launched, handle tasks")

        def job():
            AsyncTask.objects.create(category='stats', exec_at=timezone.now(), data={})

        def job2():
            AsyncTask.objects.create(category='unstick_notifications', exec_at=timezone.now(), data={})

        if kwargs["once"]:
            job2()

            self._stats()
            self.handleAsyncTasks()
            return

        schedule.every(20).minutes.do(job)
        schedule.every(5).minutes.do(job2)

        while True:
            schedule.run_pending()
            self.sendAPNIfNeed()
            self.handleAsyncTasks()
            time.sleep(1)
