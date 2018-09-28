import json
from django.test import TestCase
from django.test import Client

from core import specs_v3
from core.models import *
from core.auth import generateToken
from core.tests import helpers
from core.views.audit import _compareValue


class AuditV3TestCase(TestCase):
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

    def audit_activity_normal_lifecycle(self,
                                        actions=[],
                                        subtype=None,
                                        submit=True,
                                        creator=None,
                                        auditData=None,
                                        prepare=True):
        if prepare:
            self.prepareData()
            self.prepareAuditConfig()

        if subtype is None:
            subtype = 'baoxiao'

        if creator is not None:
            creator = Profile.objects.get(name=creator)
        else:
            creator = self.jack

        token = generateToken(creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities',
            json.dumps({
                'code': subtype,
                'submit': submit,
                'extra': auditData
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )

        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)

        activity = AuditActivity.objects.first()
        self.assertEqual(activity.creator, creator)
        if submit:
            self.assertEqual(activity.state, AuditActivity.StateProcessing)
        else:
            self.assertEqual(activity.state, AuditActivity.StateDraft)
            self.assertEqual(len(activity.steps()), 0)

        if not submit:
            response = client.post(
                '/api/v1/audit-activities/{}/actions/submit-audit'.format(
                    str(activity.pk)),
                HTTP_AUTHORIZATION=token
            )
            self.assertEquals(response.status_code, 200)
            result = json.loads(response.content.decode('utf-8'))
            self.assertEqual(result['ok'], True)
            activity = AuditActivity.objects.all()[0]
            self.assertEqual(activity.state, AuditActivity.StateProcessing)

        # test query api
        r = client.get(
            '/api/v1/audit-activities/{}'.format(str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(r.status_code, 200)
        result = json.loads(r.content.decode('utf-8'))
        self.assertEqual(result['id'], str(activity.pk))

        for action in actions:
            if action == 'cancel':
                r = client.post(
                    '/api/v1/audit-activities/{}/actions/cancel'.format(
                        activity.pk),
                    content_type='application/json',
                    HTTP_AUTHORIZATION=token
                )
                self.assertEquals(r.status_code, 200)
            if action == 'approve':
                step = activity.currentStep()
                token = generateToken(step.assignee)
                r = client.post(
                    '/api/v1/audit-steps/{}/actions/approve'.format(step.pk),
                    content_type='application/json',
                    HTTP_AUTHORIZATION=token
                )
                self.assertEquals(r.status_code, 200)
            if action == 'reject':
                step = activity.currentStep()
                token = generateToken(step.assignee)
                r = client.post(
                    '/api/v1/audit-steps/{}/actions/reject'.format(step.pk),
                    content_type='application/json',
                    HTTP_AUTHORIZATION=token
                )
                self.assertEquals(r.status_code, 200)

    def assert_audit_steps(self, activity, expected):
        actual = [{
            'assignee': s.assignee.name,
            'state': s.state,
            'active': s.active,
            'position': s.position
        } for s in activity.steps()]
        self.assertListEqual(actual, expected)

    def test_create_audit_activity(self):
        self.audit_activity_normal_lifecycle(auditData={'amount': 2000})
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': True, 'state': AuditStep.StatePending, 'position': 0},
            {'assignee': 'lucy', 'active': False, 'state': AuditStep.StatePending, 'position': 1}
        ])

    def test_create_audit_activity_hit_conditions_1(self):
        self.audit_activity_normal_lifecycle(auditData={'amount': 8000, 'category': 'hotel'})
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': True, 'state': AuditStep.StatePending, 'position': 0},
            {'assignee': 'lucy', 'active': False, 'state': AuditStep.StatePending, 'position': 1},
            {'assignee': 'neo', 'active': False, 'state': AuditStep.StatePending, 'position': 2},
            {'assignee': 'ceo', 'active': False, 'state': AuditStep.StatePending, 'position': 3},
        ])

    def test_create_audit_activity_hit_creator_condition(self):
        self.audit_activity_normal_lifecycle(
            subtype='cost',
            creator='lee',
            auditData={
                'amount': 8000,
                'category': 'hotel'
            }
        )
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lucy', 'active': True, 'state': AuditStep.StatePending, 'position': 0}
        ])

    def test_create_audit_activity_hit_creator_condition_2(self):
        self.audit_activity_normal_lifecycle(
            subtype='cost',
            creator='lucy',
            auditData={
                'amount': 8000,
                'category': 'hotel'
            }
        )
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'ceo', 'active': True, 'state': AuditStep.StatePending, 'position': 0}
        ])

    def test_create_audit_activity_hit_conditions_2(self):
        self.audit_activity_normal_lifecycle(auditData={'amount': 8000})
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': True, 'state': AuditStep.StatePending, 'position': 0},
            {'assignee': 'lucy', 'active': False, 'state': AuditStep.StatePending, 'position': 1},
            {'assignee': 'ceo', 'active': False, 'state': AuditStep.StatePending, 'position': 2},
        ])

    def test_create_audit_activity_with_same_assignee_in_some_steps(self):
        self.audit_activity_normal_lifecycle(subtype='duplicate', creator='lucy', auditData={})
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lucy', 'active': True, 'state': AuditStep.StatePending, 'position': 0},
            {'assignee': 'neo', 'active': False, 'state': AuditStep.StatePending, 'position': 1},
        ])

    def test_create_audit_activity_with_no_candidates_in_some_step(self):
        self.audit_activity_normal_lifecycle(creator='ceo', auditData={'amount': 2000})
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lucy', 'active': True, 'state': AuditStep.StatePending, 'position': 0}
        ])

    def test_submit_draft_audit_activity(self):
        self.audit_activity_normal_lifecycle(creator='ceo', auditData={'amount': 2000}, submit=False)
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lucy', 'active': True, 'state': AuditStep.StatePending, 'position': 0}
        ])

    def test_submit_again_hit_different_workflow(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'reject'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/relaunch'.format(
                str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        activity = AuditActivity.objects.get(pk=result['id'])

        response = client.post(
            '/api/v1/audit-activities/{}/actions/update-data'.format(str(activity.pk)),
            json.dumps({
                'amount': 8000
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)

        r = client.post(
            '/api/v1/audit-activities/{}/actions/submit-audit'.format(str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(r.status_code, 200)
        activity = AuditActivity.objects.get(pk=activity.pk)
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': True, 'state': AuditStep.StatePending, 'position': 0},
            {'assignee': 'lucy', 'active': False, 'state': AuditStep.StatePending, 'position': 1},
            {'assignee': 'ceo', 'active': False, 'state': AuditStep.StatePending, 'position': 2},
        ])

    def test_submit_audit_activity_with_invalid_state(self):
        self.audit_activity_normal_lifecycle(auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/submit-audit'.format(
                str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 400)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-state')

    def test_query_mine_activities(self):
        self.audit_activity_normal_lifecycle(auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()

        response = client.get(
            '/api/v1/mine-audit-activities?type=baoxiao&state=processing',
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['activities']), 1)

        response = client.get(
            '/api/v1/mine-audit-activities?start=20',
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['activities']), 0)

    def test_cancel_audit_activity(self):
        self.audit_activity_normal_lifecycle(actions=['cancel'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()
        self.assertEqual(activity.state, AuditActivity.StateCancelled)
        steps = activity.steps()
        self.assertEqual(len(steps), 0)

    def test_cancel_audit_activity_with_approved_steps(self):
        self.audit_activity_normal_lifecycle(['approve'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/cancel'.format(activity.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 400)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-state')

    def test_query_assigned_activities(self):
        self.audit_activity_normal_lifecycle(auditData={'amount': 2000})

        token = generateToken(self.lee)
        client = Client()
        response = client.get(
            '/api/v1/assigned-audit-activities?type=baoxiao&creator=jack',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['activities']), 1)

        client = Client()
        response = client.get(
            '/api/v1/assigned-audit-activities?type=baoxiao&creator=jack&start=20',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['activities']), 0)

    def test_query_processed_activities(self):
        self.audit_activity_normal_lifecycle(actions=['approve'], auditData={'amount': 2000})

        token = generateToken(self.lee)
        client = Client()
        response = client.get(
            '/api/v1/processed-audit-activities?type=baoxiao&creator=jack',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['activities']), 1)

        client = Client()
        response = client.get(
            '/api/v1/processed-audit-activities?type=baoxiao&creator=jack&start=20',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['activities']), 0)

    def test_approve_audit_step(self):
        self.audit_activity_normal_lifecycle(actions=['approve'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': False, 'state': AuditStep.StateApproved, 'position': 0},
            {'assignee': 'lucy', 'active': True, 'state': AuditStep.StatePending, 'position': 1}
        ])

    def test_reject_audit_step(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'reject'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        currentStep = activity.currentStep()
        self.assertEqual(currentStep, None)
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': False, 'state': AuditStep.StateApproved, 'position': 0},
            {'assignee': 'lucy', 'active': False, 'state': AuditStep.StateRejected, 'position': 1}
        ])
        activity = AuditActivity.objects.first()
        self.assertEqual(activity.state, AuditActivity.StateRejected)

    def test_relaunch_activity(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'reject'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/relaunch'.format(
                str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))

        activity = AuditActivity.objects.get(pk=activity.pk)
        self.assertEqual(activity.archived, True)

        activity = AuditActivity.objects.get(pk=result['id'])
        self.assertEqual(activity.state, AuditActivity.StateDraft)
        self.assert_audit_steps(activity, [])

    def test_approve_rejected_step(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'reject'], auditData={'amount': 2000})

        activity = AuditActivity.objects.first()
        self.assertEqual(activity.state, AuditActivity.StateRejected)

        steps = activity.steps()
        step = steps[1]
        token = generateToken(step.assignee)
        client = Client()
        response = client.post(
            '/api/v1/audit-steps/{}/actions/approve'.format(step.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 400)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-step-state')

    def test_steps_all_approved(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'approve'], auditData={'amount': 2000})

        activity = AuditActivity.objects.first()
        self.assertEqual(activity.state, AuditActivity.StateApproved)
        self.assert_audit_steps(activity, [
            {'assignee': 'lee', 'active': False, 'state': AuditStep.StateApproved, 'position': 0},
            {'assignee': 'lucy', 'active': False, 'state': AuditStep.StateApproved, 'position': 1}
        ])

    def test_send_message_when_activity_approved(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'approve'], auditData={'amount': 2000})

        activity = AuditActivity.objects.first()
        message = Message.objects.get(activity=activity,
                                      profile=activity.creator)
        self.assertEqual(message.read, False)
        self.assertEqual(message.category, 'finish')
        self.assertEqual(message.extra['state'], 'approved')

    def test_send_message_when_activity_rejected(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'reject'], auditData={'amount': 2000})

        activity = AuditActivity.objects.first()
        message = Message.objects.get(activity=activity,
                                      profile=activity.creator)
        self.assertEqual(message.read, False)
        self.assertEqual(message.category, 'finish')
        self.assertEqual(message.extra['state'], 'rejected')

    def test_reject_step_has_been_approved(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'approve'], auditData={'amount': 2000})

        activity = AuditActivity.objects.first()
        self.assertEqual(activity.state, AuditActivity.StateApproved)

        steps = activity.steps()
        step = steps[1]
        token = generateToken(step.assignee)
        client = Client()
        response = client.post(
            '/api/v1/audit-steps/{}/actions/approve'.format(step.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 400)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-step-state')

    def test_approve_step_with_invalid_profile(self):
        self.audit_activity_normal_lifecycle(actions=['approve'], auditData={'amount': 2000})

        activity = AuditActivity.objects.first()
        steps = activity.steps()
        step = steps[1]
        token = generateToken(self.lee)
        client = Client()
        response = client.post(
            '/api/v1/audit-steps/{}/actions/reject'.format(step.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )
        self.assertEquals(response.status_code, 400)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-assignee')

    def test_hurryup(self):
        self.audit_activity_normal_lifecycle(actions=['approve'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()

        response = client.get(
            '/api/v1/mine-audit-activities',
            content_type='application/json',
            HTTP_AUTHORIZATION=token)
        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        item = result['activities'][0]
        self.assertEqual(item['canHurryup'], True)

        response = client.post(
            '/api/v1/audit-activities/{}/actions/hurryup'.format(activity.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token)

        self.assertEquals(response.status_code, 200)
        step = activity.currentStep()
        message = Message.objects.get(profile=step.assignee,
                                      category='hurryup',
                                      activity=activity)
        self.assertEqual(message.read, False)

        response = client.get(
            '/api/v1/mine-audit-activities',
            content_type='application/json',
            HTTP_AUTHORIZATION=token)
        result = json.loads(response.content.decode('utf-8'))
        item = result['activities'][0]
        self.assertEqual(item['canHurryup'], False)

    def test_hurryup_twice_one_day(self):
        self.audit_activity_normal_lifecycle(actions=['approve'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/hurryup'.format(activity.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token)

        self.assertEquals(response.status_code, 200)
        step = activity.currentStep()
        message = Message.objects.get(profile=step.assignee,
                                      category='hurryup',
                                      activity=activity)
        self.assertEqual(message.read, False)

        response = client.post(
            '/api/v1/audit-activities/{}/actions/hurryup'.format(activity.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token)
        self.assertEquals(response.status_code, 200)
        msgs = Message.objects \
            .filter(profile=step.assignee,
                    category='hurryup',
                    activity=activity) \
            .count()
        self.assertEqual(msgs, 1)

    def test_mark_task_finished(self):
        self.audit_activity_normal_lifecycle(actions=['approve', 'approve'], auditData={'amount': 2000})
        activity = AuditActivity.objects.first()

        token = generateToken(activity.creator)
        client = Client()
        r = client.post(
            '/api/v1/audit-activities/{}/actions/mark-task-finished'.format(activity.pk),
            content_type='application/json',
            HTTP_AUTHORIZATION=token)
        self.assertEquals(r.status_code, 200)

        activity = AuditActivity.objects.first()
        self.assertEqual(activity.taskState, 'finished')

    def test_record_memo(self):
        self.audit_activity_normal_lifecycle(
            actions=['approve', 'approve'],
            subtype='biz',
            auditData={
                'base': {
                    'company': 'foobar'
                },
                'info': {
                    'upstream': 'up',
                    'downstream': 'down',
                    'asset': 'iron',
                    'tonnage': '1000',
                    'buyPrice': '1000',
                    'sellPrice': '1000'
                }
            })
        upstream = Memo.objects.filter(category='upstream').first()
        self.assertEqual(upstream.value, 'up')
        downstream = Memo.objects.filter(category='downstream').first()
        self.assertEqual(downstream.value, 'down')
        asset = Memo.objects.filter(category='asset').first()
        self.assertEqual(asset.value, 'iron')
        company = Company.objects.first()
        self.assertEqual(company.name, 'foobar')

    def test_record_bank_account(self):
        self.audit_activity_normal_lifecycle(
            subtype='cost',
            auditData={
                'amount': 2000,
                'account': {
                    'name': 'foobar',
                    'bank': 'foobar',
                    'number': '123456'
                }
            })
        count = BankAccount.objects.filter(name='foobar', bank='foobar', number='123456').count()
        self.assertEqual(count, 1)

        self.audit_activity_normal_lifecycle(
            prepare=False,
            subtype='cost',
            auditData={
                'amount': 2000,
                'account': {
                    'name': 'foobar',
                    'bank': 'foobar',
                    'number': '123456'
                }
            })
        count = BankAccount.objects.filter(name='foobar', bank='foobar', number='123456').count()
        self.assertEqual(count, 1)

    def test_compare_value(self):
        self.assertEqual(_compareValue('eq', ['caigou', 'other'], 'other'), True)
        self.assertEqual(_compareValue('eq', ['caigou', 'other'], 'foobar'), False)
        self.assertEqual(_compareValue('eq', 1000, 1000), True)
        self.assertEqual(_compareValue('eq', 1000, 2000), False)

        self.assertEqual(_compareValue('lt', 1000, 500), True)
        self.assertEqual(_compareValue('lt', 1000, 2000), False)

        self.assertEqual(_compareValue('lte', 1000, 500), True)
        self.assertEqual(_compareValue('lte', 1000, 100), True)
        self.assertEqual(_compareValue('lt', 1000, 2000), False)

        self.assertEqual(_compareValue('gt', 1000, 2000), True)
        self.assertEqual(_compareValue('gt', 1000, 500), False)

        self.assertEqual(_compareValue('gt', 1000, 2000), True)
        self.assertEqual(_compareValue('gte', 1000, 1000), True)
        self.assertEqual(_compareValue('gt', 1000, 500), False)
