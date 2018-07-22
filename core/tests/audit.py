import json
from django.test import TestCase
from django.test import Client

from core.models import *
from core.auth import generateToken
from core.tests import helpers


class AuditTestCase(TestCase):
    def setUp(self):
        self.profile = helpers.prepareProfile('root', 'root', '13333333333')
        self.generateToken = generateToken(self.profile)

    def perpareData(self):
        pos_member = Position.objects.create(name='member')
        pos_owner = Position.objects.create(name='owner')
        pos_accountant = Position.objects.create(name='accountant')
        pos_cashier = Position.objects.create(name='cashier')
        pos_ceo = Position.objects.create(name='ceo')
        self.pos_member = pos_member
        self.pos_owner = pos_owner
        self.pos_accountant = pos_accountant
        self.pos_ceo = pos_ceo

        root = Department.objects.create(name='root')
        biz = Department.objects.create(name='biz', parent=root)
        fin = Department.objects.create(name='fin', parent=root)
        self.root = root
        self.biz = biz
        self.fin = fin

        lee = helpers.prepareProfile('lee', 'lee', '18888888880')
        lee.department = biz
        lee.position = pos_owner
        lee.save()
        self.lee = lee

        jack = helpers.prepareProfile('jack', 'jack', '18888888881')
        jack.department = biz
        jack.position = pos_member
        jack.save()
        self.jack = jack

        ceo = helpers.prepareProfile('ceo', 'ceo', '18888888888')
        ceo.department = root
        ceo.position = pos_ceo
        ceo.save()
        self.ceo = ceo

        lucy = helpers.prepareProfile('lucy', 'lucy', '18888888889')
        lucy.department = fin
        lucy.position = pos_accountant
        lucy.save()
        self.lucy = lucy

    def audit_activity_normal_lifecycle(self, actions, submitDirectly=True):
        self.perpareData()
        config = AuditActivityConfig.objects \
            .create(category='fin',
                    subtype='baoxiao')
        AuditActivityConfigStep.objects \
            .create(config=config,
                    assigneeDepartment=self.biz,
                    assigneePosition=self.pos_owner,
                    position=0)
        AuditActivityConfigStep.objects \
            .create(config=config,
                    assigneeDepartment=self.fin,
                    assigneePosition=self.pos_accountant,
                    position=1)
        AuditActivityConfigStep.objects \
            .create(config=config,
                    assigneeDepartment=self.root,
                    assigneePosition=self.pos_ceo,
                    position=2)

        client = Client()
        token = generateToken(self.jack)
        response = client.post(
            '/api/v1/audit-activities',
            json.dumps({
                'config': str(config.pk),
                'submit': submitDirectly,
                'extra': {}
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=token
        )

        self.assertEquals(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['ok'], True)

        activity = AuditActivity.objects.all()[0]
        self.assertEqual(activity.creator, self.jack)
        if submitDirectly:
            self.assertEqual(activity.state, AuditActivity.StateProcessing)
        else:
            self.assertEqual(activity.state, AuditActivity.StateDraft)

        if not submitDirectly:
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

        steps = AuditStep.objects \
            .filter(activity=activity) \
            .order_by('position')
        expect_steps = [
            {'assignee': self.lee},
            {'assignee': self.lucy},
            {'assignee': self.ceo}
        ]
        for step in steps:
            es = expect_steps[step.position]
            self.assertEqual(es['assignee'], step.assignee)
            self.assertEqual(step.state, AuditStep.StatePending)

        for action in actions:
            if action == 'cancel':
                response = client.post(
                    '/api/v1/audit-activities/{}/actions/cancel'.format(
                        activity.pk),
                    content_type='application/json',
                    HTTP_AUTHORIZATION=token
                )
                self.assertEquals(response.status_code, 200)
            if action == 'approve':
                step = activity.currentStep()
                token = generateToken(step.assignee)
                response = client.post(
                    '/api/v1/audit-steps/{}/actions/approve'.format(step.pk),
                    content_type='application/json',
                    HTTP_AUTHORIZATION=token
                )
                self.assertEquals(response.status_code, 200)
            if action == 'reject':
                step = activity.currentStep()
                token = generateToken(step.assignee)
                response = client.post(
                    '/api/v1/audit-steps/{}/actions/reject'.format(step.pk),
                    content_type='application/json',
                    HTTP_AUTHORIZATION=token
                )
                self.assertEquals(response.status_code, 200)

    def test_query_configs(self):
        self.audit_activity_normal_lifecycle([])
        activity = AuditActivity.objects.all()[0]

        token = generateToken(activity.creator)
        client = Client()
        response = client.get(
            '/api/v1/audit-configs',
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result['configs']), 1)

    def test_create_audit_activity(self):
        self.audit_activity_normal_lifecycle([])
        activity = AuditActivity.objects.all()[0]
        steps = activity.steps()
        self.assertEqual(steps[0].active, True)
        self.assertEqual(steps[1].active, False)
        self.assertEqual(steps[2].active, False)

    def test_submit_draft_audit_activity(self):
        self.audit_activity_normal_lifecycle([], submitDirectly=False)
        activity = AuditActivity.objects.all()[0]
        steps = activity.steps()
        self.assertEqual(steps[0].active, True)
        self.assertEqual(steps[1].active, False)
        self.assertEqual(steps[2].active, False)

    def test_submit_audit_activity_with_invalid_state(self):
        self.audit_activity_normal_lifecycle([])
        activity = AuditActivity.objects.all()[0]

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/submit-audit'.format(str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 400)
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(result['errorId'], 'invalid-state')

    def test_query_mine_activities(self):
        self.audit_activity_normal_lifecycle([])
        activity = AuditActivity.objects.all()[0]

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
        self.audit_activity_normal_lifecycle(['cancel'])
        activity = AuditActivity.objects.all()[0]
        self.assertEqual(activity.state, AuditActivity.StateCancelled)

    def test_cancel_audit_activity_with_approved_steps(self):
        self.audit_activity_normal_lifecycle(['approve'])
        activity = AuditActivity.objects.all()[0]

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
        self.audit_activity_normal_lifecycle([])

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
        self.audit_activity_normal_lifecycle(['approve'])

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
        self.audit_activity_normal_lifecycle(['approve'])
        activity = AuditActivity.objects.all()[0]

        steps = activity.steps()
        stepActive = [step.active for step in steps]
        self.assertListEqual(stepActive, [False, True, False])

        currentStep = activity.currentStep()
        self.assertEqual(currentStep.position, 1)
        self.assertEqual(currentStep.state, AuditStep.StatePending)

        prevStep = currentStep.prevStep()
        self.assertEqual(prevStep.state, AuditStep.StateApproved)

    def test_reject_audit_step(self):
        self.audit_activity_normal_lifecycle(['approve', 'reject'])
        activity = AuditActivity.objects.all()[0]

        currentStep = activity.currentStep()
        self.assertEqual(currentStep, None)

        steps = activity.steps()
        stepStates = [step.state for step in steps]
        self.assertListEqual(stepStates, [
            AuditStep.StateApproved,
            AuditStep.StateRejected,
            AuditStep.StatePending
        ])

        stepActive = [step.active for step in steps]
        self.assertListEqual(stepActive, [False, False, False])

    def test_relaunch_activity(self):
        self.audit_activity_normal_lifecycle(['approve', 'reject'])
        activity = AuditActivity.objects.all()[0]

        token = generateToken(activity.creator)
        client = Client()
        response = client.post(
            '/api/v1/audit-activities/{}/actions/relaunch'.format(str(activity.pk)),
            HTTP_AUTHORIZATION=token
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))

        activity = AuditActivity.objects.get(pk=activity.pk)
        self.assertEqual(activity.archived, True)

        activity = AuditActivity.objects.get(pk=result['id'])
        self.assertEqual(activity.state, AuditActivity.StateDraft)

    def test_approve_rejected_step(self):
        self.audit_activity_normal_lifecycle(['approve', 'reject'])

        activity = AuditActivity.objects.all()[0]
        self.assertEqual(activity.state, AuditActivity.StateRejected)

        steps = activity.steps()
        step = steps[2]
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
        self.audit_activity_normal_lifecycle(['approve', 'approve', 'approve'])

        activity = AuditActivity.objects.all()[0]
        self.assertEqual(activity.state, AuditActivity.StateApproved)

        steps = activity.steps()
        stepStates = [step.state for step in steps]
        self.assertListEqual(stepStates, [
            AuditStep.StateApproved,
            AuditStep.StateApproved,
            AuditStep.StateApproved
        ])

    def test_reject_step_has_been_approved(self):
        self.audit_activity_normal_lifecycle(['approve', 'approve', 'approve'])

        activity = AuditActivity.objects.all()[0]
        self.assertEqual(activity.state, AuditActivity.StateApproved)

        steps = activity.steps()
        step = steps[2]
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
        self.audit_activity_normal_lifecycle(['approve', 'approve'])

        activity = AuditActivity.objects.all()[0]
        steps = activity.steps()
        step = steps[2]
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
