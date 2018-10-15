import json
from django.test import TestCase
from django.test import Client

from core import specs_v3
from core.models import *
from core.auth import generateToken
from core.tests import helpers
from core.views.audit import _compareValue


class AuditTestMixin:
    def prepareData(self):
        self.pos_biz_member = Position.objects.create(name='member', code='member')
        pos_fin_member = Position.objects.create(name='member', code='member')
        self.pos_biz_owner = Position.objects.create(name='owner', code='owner')
        pos_fin_owner = Position.objects.create(name='owner', code='owner')
        pos_accountant = Position.objects.create(name='accountant', code='accountant')
        pos_cashier = Position.objects.create(name='cashier', code='cashier')
        pos_ceo = Position.objects.create(name='ceo', code='ceo')
        self.pos_accountant = pos_accountant
        self.pos_ceo = pos_ceo

        root = Department.objects.create(name='root', code='root')
        biz = Department.objects.create(name='biz', parent=root, code='biz')
        fin = Department.objects.create(name='fin', parent=root, code='fin')
        self.root = root
        self.biz = biz
        self.fin = fin

        DepPos.objects.create(dep=root, pos=pos_ceo)
        DepPos.objects.create(dep=biz, pos=self.pos_biz_member)
        DepPos.objects.create(dep=biz, pos=self.pos_biz_owner)

        DepPos.objects.create(dep=fin, pos=pos_accountant)
        DepPos.objects.create(dep=fin, pos=pos_fin_owner)
        DepPos.objects.create(dep=fin, pos=pos_cashier)
        DepPos.objects.create(dep=fin, pos=pos_fin_member)

        # biz.owner: lee
        lee = helpers.prepareProfile('lee', 'lee', '18888888880')
        lee.department = biz
        lee.position = self.pos_biz_owner
        lee.save()
        self.lee = lee

        # biz.member jack
        jack = helpers.prepareProfile('jack', 'jack', '18888888881')
        jack.department = biz
        jack.position = self.pos_biz_member
        jack.save()
        self.jack = jack

        # root.ceo: ceo
        ceo = helpers.prepareProfile('ceo', 'ceo', '18888888888')
        ceo.department = root
        ceo.position = pos_ceo
        ceo.save()
        self.ceo = ceo

        # fin.accountant lucy
        lucy = helpers.prepareProfile('lucy', 'lucy', '18888888889')
        lucy.department = fin
        lucy.position = pos_accountant
        lucy.save()
        self.lucy = lucy

        # fin.owner: neo
        neo = helpers.prepareProfile('neo', 'neo', '13333333338')
        neo.department = fin
        neo.position = pos_fin_owner
        neo.save()
        self.neo = neo

    def prepareAuditConfig(self):
        self.baoxiao_gt_5k_hotel = specs_v3.createAuditConfig(
            spec='fin.baoxiao(amount>5000,category=hotel):_.owner->fin.accountant->fin.owner->root.ceo')
        self.baoxiao_gt_5k = specs_v3.createAuditConfig(
            spec='fin.baoxiao(amount>5000):_.owner->fin.accountant->root.ceo')
        self.baoxiao_fallback = specs_v3.createAuditConfig(
            spec='fin.baoxiao:_.owner->fin.accountant',
            fallback=True)

        self.biz_fallback = specs_v3.createAuditConfig(
            spec='fin.biz:_.owner->fin.accountant',
            fallback=True)

        self.cost_biz_owner = specs_v3.createAuditConfig(
            spec='fin.cost:fin.accountant',
            fallback=False)
        self.cost_biz_owner.conditions = [
            {
                'prop': 'creator',
                'condition': 'eq',
                'value': {
                    'department': str(self.biz.pk),
                    'position': str(self.pos_biz_owner.pk)
                }
            }
        ]
        self.cost_biz_owner.save()

        self.cost_fin = specs_v3.createAuditConfig(
            spec='fin.cost:root.ceo',
            fallback=False)
        self.cost_fin.conditions = [
            {
                'prop': 'creator',
                'condition': 'eq',
                'value': {
                    'department': str(self.fin.pk)
                }
            }
        ]
        self.cost_fin.save()

        self.cost_fallback = specs_v3.createAuditConfig(
            spec='fin.cost:_.owner->fin.accountant',
            fallback=True)

        self.duplicate = specs_v3.createAuditConfig(
            spec='test.duplicate:_.owner->fin.accountant->fin.owner',
            fallback=True)
