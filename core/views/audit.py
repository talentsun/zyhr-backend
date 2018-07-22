import logging
import datetime
import json

from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import *
from core.auth import validateToken
from core.common import *

logger = logging.getLogger('app.core.views.audit')


@require_http_methods(['GET'])
@validateToken
def configs(request):
    configs = AuditActivityConfig.objects.all()
    return JsonResponse({
        'configs': [resolve_config(config) for config in configs]
    })


def submitActivityAudit(activity):
    activity.state = AuditActivity.StateProcessing
    activity.save()

    steps = activity.steps()
    step = steps[0]
    step.active = True
    step.activated_at = datetime.datetime.now(tz=timezone.utc)
    step.save()


@transaction.atomic
def createActivity(profile, data):
    # TODO: validate user permission
    configId = data.get('config', None)  # audit acitivity config id
    configCode = data.get('code', None)  # audit acitivity config code
    submit = data.get('submit', False)  # 是否提交审核
    if configId is not None:
        config = AuditActivityConfig.objects.get(pk=configId)
    else:
        config = AuditActivityConfig.objects.get(subtype=configCode)

    taskId = uuid.uuid4()
    logger.info('{} create activity base on config: {}'.format(
        taskId, config.subtype))

    configSteps = AuditActivityConfigStep.objects \
        .filter(config=config) \
        .order_by('position')

    activity = AuditActivity.objects \
        .create(config=config,
                state=AuditActivity.StateDraft,
                creator=profile,
                extra=data['extra'])

    logger.info('{} create steps'.format(taskId))
    for index, step in enumerate(configSteps):
        logger.info('{} resolve assignee for step#{}'.format(
            taskId, step.position))

        assigneeDepartment = step.assigneeDepartment
        if assigneeDepartment is None:
            # 如果部门没有配置，那么就设置为发起者所在部门
            assigneeDepartment = profile.department

        profiles = Profile.objects \
            .filter(department=assigneeDepartment,
                    position=step.assigneePosition)
        if profiles.count() != 1:
            names = ', '.join([p.name for p in profiles])
            logger.info('{} fail to resolve assignee for step#{}, dep: {}, pos: {}, candidates: {}'.format(taskId,
                                                                                                           step.position,
                                                                                                           assigneeDepartment.code,
                                                                                                           step.assigneePosition.code,
                                                                                                           names))
            raise Exception('Can not resolve assignee')

        assignee = profiles[0]
        logger.info('{} assignee for step#{} resolved, dep: {}, pos: {}, assignee: {}'.format(taskId,
                                                                                              step.position,
                                                                                              assigneeDepartment.code,
                                                                                              step.assigneePosition.code,
                                                                                              assignee.name))

        step = AuditStep.objects \
            .create(activity=activity,
                    active=False,
                    assignee=assignee,
                    assigneeDepartment=assigneeDepartment,
                    assigneePosition=step.assigneePosition,
                    position=step.position)

    if submit:
        submitActivityAudit(activity)

    return activity


@require_http_methods(['POST'])
@validateToken
def activities(request):
    # TODO: validate user permission
    profile = request.profile
    data = json.loads(request.body.decode('utf-8'))
    createActivity(profile, data)
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
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
            activity.finished_at = datetime.datetime.now(tz=timezone.utc)
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


@require_http_methods(['POST'])
@validateToken
def updateData(request, activityId):
    # TODO: validate user permission
    data = json.loads(request.body.decode('utf-8'))
    activity = AuditActivity.objects.get(pk=activityId)
    activity.extra = data
    activity.save()
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def submitAudit(request, activityId):
    # TODO: validate user permission
    activity = AuditActivity.objects.get(pk=activityId)
    if activity.state != AuditActivity.StateDraft:
        return JsonResponse({'errorId': 'invalid-state'}, status=400)

    submitActivityAudit(activity)
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
@transaction.atomic
def relaunch(request, activityId):
    activity = AuditActivity.objects.get(pk=activityId)
    activity.archived = True
    activity.save()

    data = {
        'code': activity.config.subtype,
        'submit': False,
        'extra': activity.extra
    }
    activity = createActivity(request.profile, data)
    return JsonResponse({'id': str(activity.pk)})


def validateStepState(step, profile):
    if step.state != AuditStep.StatePending:
        return {
            'errorId': 'invalid-step-state',
            'errorMsg': 'Current step state is {}. Can not change current step state.'.format(step.state)
        }

    if step.active is not True:
        return {
            'errorId': 'invalid-step-state',
            'errorMsg': 'not current step'
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
    data = json.loads(request.body.decode('utf-8'))
    desc = data.get('desc', None)
    try:
        step = AuditStep.objects.get(pk=stepId)
        err = validateStepState(step, profile)
        if err != None:
            return JsonResponse(err, status=400)

        step.state = AuditStep.StateApproved
        step.active = False
        step.finished_at = datetime.datetime.now(tz=timezone.utc)
        step.desc = desc
        step.save()
        if step.nextStep() == None:
            activity = step.activity
            activity.state = AuditActivity.StateApproved
            activity.save()
        else:
            nextStep = step.nextStep()
            nextStep.active = True
            nextStep.activated_at = datetime.datetime.now(tz=timezone.utc)
            nextStep.save()
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
    data = json.loads(request.body.decode('utf-8'))
    desc = data.get('desc', None)
    try:
        step = AuditStep.objects.get(pk=stepId)
        err = validateStepState(step, profile)
        if err != None:
            return JsonResponse(err, status=400)

        step.state = AuditStep.StateRejected
        step.finished_at = datetime.datetime.now(tz=timezone.utc)
        step.active = False
        step.desc = desc
        step.save()
        activity = step.activity
        activity.finished_at = datetime.datetime.now(tz=timezone.utc)
        activity.state = AuditActivity.StateRejected
        activity.save()
        return JsonResponse({'ok': True})
    except:
        return JsonResponse({
            'errorId': 'step-not-found'
        }, status=400)


def resolveDateRange(created_at):
    start = datetime.datetime.strptime(created_at, '%Y-%m-%d')
    # start = start - datetime.timedelta(days=1) - datetime.timedelta(hours=8)
    start = start - datetime.timedelta(hours=8)
    to = start + datetime.timedelta(days=1)
    return start, to


@require_http_methods(['GET'])
@validateToken
def mineActivities(request):
    auditType = request.GET.get('type', None)
    state = request.GET.get('state', None)
    created_at = request.GET.get('created_at', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    activities = AuditActivity.objects.filter(creator=request.profile,
                                              archived=False)
    if notEmpty(auditType):
        activities = activities.filter(
            config__subtype__in=auditType.split(','))
    if notEmpty(state):
        activities = activities.filter(state=state)
    if notEmpty(created_at):
        _start, _to = resolveDateRange(created_at)
        activities = activities.filter(created_at__gte=_start,
                                       created_at__lt=_to)
    activities = activities.order_by('-updated_at')
    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity) for activity in activities]
    })


def notEmpty(value):
    return value is not None and value != ''


@require_http_methods(['GET'])
@validateToken
def assignedActivities(request):
    auditType = request.GET.get('type', None)
    creator_name = request.GET.get('creator', None)
    created_at = request.GET.get('created_at', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    # TODO: 处理职位变更问题
    steps = AuditStep.objects.filter(assignee=request.profile,
                                     activity__archived=False,
                                     active=True)
    if notEmpty(auditType):
        steps = steps.filter(
            activity__config__subtype__in=auditType.split(','))
    if notEmpty(creator_name):
        steps = steps.filter(activity__creator__name=creator_name)
    if notEmpty(created_at):
        _start, _to = resolveDateRange(created_at)
        steps = steps.filter(activity__created_at__gte=_start,
                             activity__created_at__lt=_to)

    steps.order_by('-activity__updated_at')
    total = steps.count()
    steps = steps[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(step.activity) for step in steps]
    })


@require_http_methods(['GET'])
@validateToken
def processedActivities(request):
    auditType = request.GET.get('type', None)
    creator_name = request.GET.get('creator', None)
    created_at = request.GET.get('created_at', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    # TODO: 处理职位变更问题
    steps = AuditStep.objects.filter(assignee=request.profile,
                                     activity__archived=False,
                                     state__in=[
                                         AuditStep.StateApproved,
                                         AuditStep.StateRejected
                                     ])
    if notEmpty(auditType):
        steps = steps.filter(
            activity__config__subtype__in=auditType.split(','))
    if notEmpty(creator_name):
        steps = steps.filter(activity__creator__name=creator_name)
    if notEmpty(created_at):
        _start, _to = resolveDateRange(created_at)
        steps = steps.filter(activity__created_at__gte=_start,
                             activity__created_at__lt=_to)

    steps.order_by('-activity__updated_at')
    total = steps.count()
    steps = steps[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(step.activity) for step in steps]
    })


@require_http_methods(['GET'])
@validateToken
def auditTasks(request):
    auditType = request.GET.get('type', None)
    state = request.GET.get('state', None)
    created_at = request.GET.get('created_at', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    activities = AuditActivity.objects.filter(state=AuditActivity.StateApproved,
                                              activity__archived=False,
                                              config__hasTask=True)
    if notEmpty(auditType):
        activities = activities.filter(
            config__subtype__in=auditType.split(','))
    if notEmpty(state):
        activities = activities.filter(state=state)
    if notEmpty(created_at):
        _start, _to = resolveDateRange(created_at)
        activities = activities.filter(created_at__gte=_start,
                                       created_at__lt=_to)

    activities = activities.order_by('-updated_at')
    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity) for activity in activities]
    })
