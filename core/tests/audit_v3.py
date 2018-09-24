import json
from django.test import TestCase
from django.test import Client

from core import specs_v3
from core.models import *
from core.auth import generateToken
from core.tests import helpers


class AuditV3TestCase(TestCase):
    def setUp(self):
        pass

    def prepareData(self):
        pos_member = Position.objects.create(name='member', code='member')
        pos_owner = Position.objects.create(name='owner', code='owner')
        pos_accountant = Position.objects.create(name='accountant', code='accountant')
        pos_cashier = Position.objects.create(name='cashier', code='cashier')
        pos_ceo = Position.objects.create(name='ceo', code='ceo')
        self.pos_member = pos_member
        self.pos_owner = pos_owner
        self.pos_accountant = pos_accountant
        self.pos_ceo = pos_ceo

        root = Department.objects.create(name='root', code='root')
        biz = Department.objects.create(name='biz', parent=root, code='biz')
        fin = Department.objects.create(name='fin', parent=root, code='fin')
        self.root = root
        self.biz = biz
        self.fin = fin

        # biz.owner: lee
        lee = helpers.prepareProfile('lee', 'lee', '18888888880')
        lee.department = biz
        lee.position = pos_owner
        lee.save()
        self.lee = lee

        # biz.member jack
        jack = helpers.prepareProfile('jack', 'jack', '18888888881')
        jack.department = biz
        jack.position = pos_member
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
        neo.position = pos_owner
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

        self.duplicate = specs_v3.createAuditConfig(
            spec='test.duplicate:_.owner->fin.accountant->fin.owner',
            fallback=True)

    def audit_activity_normal_lifecycle(self,
                                        actions=[],
                                        subtype=None,
                                        submit=True,
                                        creator=None,
                                        auditData=None):
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

        activity = AuditActivity.objects.all()[0]
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

    # TODO: test case: set up audit workflow again on resubmit

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
                    'asset': 'iron'
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
        # TODO: test case: record bank account
        pass

    def test_compare_value(self):
        # TODO: test case: compareValue eq/lt/lte/gt/gte
        pass
