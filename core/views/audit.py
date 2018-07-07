import logging
import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import *
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.audit')


@transaction.atomic
def createActivity(profile, data):
    # TODO: validate user permission
    configId = data['config']  # audit acitivity config
    config = AuditActivityConfig.objects.get(pk=configId)
    configSteps = AuditActivityConfigStep.objects \
        .filter(config=config) \
        .order_by('position')

    activity = AuditActivity.objects \
        .create(config=config,
                creator=profile,
                extra=data['extra'])
    for step in configSteps:
        profiles = Profile.objects \
            .filter(department=step.assigneeDepartment,
                    position=step.assigneePosition)
        if profiles.count() != 1:
            raise Exception('Can not resolve assignee')

        assignee = profiles[0]
        AuditStep.objects \
            .create(activity=activity,
                    assignee=assignee,
                    assigneeDepartment=step.assigneeDepartment,
                    assigneePosition=step.assigneePosition,
                    position=step.position)


@require_http_methods(['POST', 'GET'])
@validateToken
def activities(request):
    # TODO: validate user permission
    profile = request.profile
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        createActivity(profile, data)
        return JsonResponse({'ok': True})
    else:
        # TODO
        return JsonResponse({'ok': True})


@require_http_methods(['POST', 'GET'])
@validateToken
def activity(request, activityId):
    # TODO: validate user permission
    activity = AuditActivity.objects.get(pk=activityId)
    return JsonResponse(resolve_activity(activity))


@require_http_methods(['POST'])
@validateToken
def cancel(request, activityId):
    # TODO: validate user permission
    try:
        activity = AuditActivity.objects.get(pk=activityId)
        if activity.isCancellable():
            activity.state = AuditActivity.StateCancelled
            activity.save()
            return JsonResponse({'ok': True})
        else:
            return JsonResponse({
                'errorId': 'invalid-state',
                'errorMsg': 'Activity state is not processing or some step has been approved or rejected.'
            }, status=400)
    except:
        return JsonResponse({
            'errorId': 'activity-not-found'
        }, status=400)


def validateStepState(step, profile):
    if step.state != AuditStep.StatePending:
        return {
            'errorId': 'invalid-step-state',
            'errorMsg': 'Current step state is {}. Can not change current step state.'.format(step.state)
        }

    prevStep = step.prevStep()
    if prevStep != None and \
                    prevStep.state != AuditStep.StateApproved:
        return {
            'errorId': 'invalid-step-state',
            'errorMsg': 'Prev step state is {}. Can not change current step state.'.format(prevStep.state)
        }

    if step.assignee.pk != profile.pk:
        return {
            'errorId': 'invalid-assignee'
        }

    return None


@require_http_methods(['POST'])
@validateToken
def approveStep(request, stepId):
    # TODO: validate user permission
    profile = request.profile
    try:
        step = AuditStep.objects.get(pk=stepId)
        err = validateStepState(step, profile)
        if err != None:
            return JsonResponse(err, status=400)

        step.state = AuditStep.StateApproved
        step.save()
        if step.nextStep() == None:
            activity = step.activity
            activity.state = AuditActivity.StateApproved
            activity.save()
        return JsonResponse({'ok': True})
    except:
        return JsonResponse({
            'errorId': 'step-not-found'
        }, status=400)


@require_http_methods(['POST'])
@validateToken
def rejectStep(request, stepId):
    # TODO: validate user permission
    profile = request.profile
    try:
        step = AuditStep.objects.get(pk=stepId)
        err = validateStepState(step, profile)
        if err != None:
            return JsonResponse(err, status=400)

        step.state = AuditStep.StateRejected
        step.save()
        activity = step.activity
        activity.state = AuditActivity.StateRejected
        activity.save()
        return JsonResponse({'ok': True})
    except:
        return JsonResponse({
            'errorId': 'step-not-found'
        }, status=400)
