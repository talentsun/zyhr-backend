import random
import string

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from core.models import *
from core import specs


def random_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class Command(BaseCommand):
    def createProfile(self, name, dep, pos):
        user = User.objects.create(username=name)
        user.set_password('123456')
        user.save()
        return Profile.objects.create(user=user,
                                      name=name,
                                      phone=random_generator(),
                                      position=pos,
                                      department=dep)

    def handle(self, *args, **options):
        positions = [
            {'name': '总裁', 'code': 'ceo'},
            {'name': '负责人', 'code': 'owner'},
            {'name': '会计', 'code': 'accountant'},
            {'name': '出纳', 'code': 'cashier'},
            {'name': '组员', 'code': 'member'},  # 各部门一般成员职位
            {'name': '业务经理', 'code': 'mgr'}  # 只在大宗商品事业部
        ]
        for pos in positions:
            Position.objects.create(**pos)

        departments = [
            {'name': '总部', 'code': 'root'},
            {'name': '大宗商品事业部', 'code': 'dazong'},
            {'name': '财务中心', 'code': 'fin'},
            {'name': '人力行政中心', 'code': 'hr'},
        ]
        for dep in departments:
            Department.objects.create(**dep)

        profiles = [
            {'name': 'ceo', 'dep': 'root', 'pos': 'ceo'},
            {'name': 'jack', 'dep': 'dazong', 'pos': 'owner'},
            {'name': 'mike', 'dep': 'dazong', 'pos': 'mgr'},
            {'name': 'tez', 'dep': 'dazong', 'pos': 'member'},

            {'name': 'tom', 'dep': 'fin', 'pos': 'owner'},
            {'name': 'telez', 'dep': 'fin', 'pos': 'accountant'},
            {'name': 'messi', 'dep': 'fin', 'pos': 'cashier'},

            {'name': 'jarvis', 'dep': 'hr', 'pos': 'owner'},
            {'name': 'young', 'dep': 'hr', 'pos': 'member'},
        ]
        for profile in profiles:
            dep = Department.objects.get(code=profile['dep'])
            pos = Position.objects.get(code=profile['pos'])
            self.createProfile(profile['name'], dep, pos)

        # 费用报销流程（总额<=5000）
        specs.createAuditConfig(spec='fin.cost_lte_5000:\
                                fin.accountant->\
                                _.owner->\
                                hr.owner->\
                                fin.owner')
        # 费用报销流程（总额>5000）
        specs.createAuditConfig(spec='fin.cost_gt_5000:\
                                fin.accountant->\
                                _.owner->\
                                hr.owner->\
                                fin.owner->\
                                root.ceo')

        # 差旅报销流程（总额<=5000）
        specs.createAuditConfig(spec='fin.travel_lte_5000:\
                                fin.accountant->\
                                _.owner->\
                                hr.owner->\
                                fin.owner')
        # 差旅报销流程（总额>5000）
        specs.createAuditConfig(spec='fin.travel_gt_5000:\
                                fin.accountant->\
                                _.owner->\
                                hr.owner->\
                                fin.owner->\
                                root.ceo')

        # 借款申请
        specs.createAuditConfig(spec='fin.loan_lte_5000:\
                                _.owner->\
                                fin.owner')
        specs.createAuditConfig(spec='fin.loan_gt_5000:\
                                _.owner->\
                                fin.owner->\
                                root.ceo')

        # 采购申请
        specs.createAuditConfig(
            spec='fin.purchase_lte_5000:_.owner->fin.owner')
        specs.createAuditConfig(
            spec='fin.purchase_gt_5000:_.owner->fin.owner->root.ceo')

        # 用款申请
        specs.createAuditConfig(spec='fin.money_lte_50k:_.owner->fin.owner')
        specs.createAuditConfig(
            spec='fin.money_gt_50k:_.owner->fin.owner->root.ceo')

        # 开户
        specs.createAuditConfig(
            spec='fin.open_account:_.owner->fin.owner->root.ceo')

        # 业务合同会签
        specs.createAuditConfig(
            spec='law.biz_contract:_.owner->fin.accountant->fin.owner->root.ceo')

        # 职能类合同会签
        specs.createAuditConfig(
            spec='law.fn_contract_zero:_.owner->root.ceo')
        specs.createAuditConfig(
            spec='law.fn_contract:_.owner->fin.owner->root.ceo')

        # 测试用的审批流程
        specs.createAuditConfig(spec='test.test:root.ceo->root.ceo->root.ceo')
