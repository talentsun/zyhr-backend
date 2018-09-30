import os
import re
import json
import logging
import datetime

import iso8601
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from sendfile import sendfile

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

    # if step.assignee.pk == activity.creator.pk:
    #     # 发起人和第一位审批人相同
    #     step.state = AuditStep.StateApproved
    #     step.active = False
    #     step.finished_at = datetime.datetime.now(tz=timezone.utc)
    #     step.save()
    #
    #     step = steps[1]
    #     step.active = True
    #     step.activated_at = datetime.datetime.now(tz=timezone.utc)
    #     step.save()

    Message.objects.create(activity=activity,
                           category='progress',
                           extra={},
                           profile=step.assignee)


def recordBankAccountIfNeed(profile, code, data):
    accounts = []
    if re.match('cost|loan', code):
        accounts = [data['account']]
    if re.match('money', code):
        accounts = [data['inAccount'], data['outAccount']]

    for account in accounts:
        name = account.get('name', None)
        bank = account.get('bank', None)
        number = account.get('number', None)
        if name is None or bank is None or number is None:
            continue

        if BankAccount.objects. \
                filter(name=name,
                       bank=bank,
                       number=number).count() == 0:
            BankAccount.objects. \
                create(profile=profile,
                       name=name,
                       bank=bank,
                       number=number)


def recordCompanyIfNeed(profile, code, data):
    if re.match('biz', code):
        company = data['base'].get('company')
        count = Company.objects.filter(name=company).count()
        if count == 0:
            Company.objects.create(profile=profile, name=company)


def recordMemo(profile, code, data):
    if re.match('biz', code):
        props = ['upstream', 'downstream', 'asset']
        for prop in props:
            value = data['info'].get(prop, None)
            if value is not None and value != '':
                count = Memo.objects.filter(category=prop, value=value).count()
                if count == 0:
                    Memo.objects.create(category=prop, value=value, profile=profile)


def generateActivitySN():
    now = datetime.datetime.now()
    now = now + datetime.timedelta(hours=8)
    start = now.date()
    end = start + datetime.timedelta(days=1)
    count = AuditActivity.objects \
        .filter(created_at__gte=start, created_at__lt=end) \
        .count()
    sn = now.strftime('%Y%m%d') + str(count + 1).zfill(4)
    return sn


def setupSteps(activity, taskId=None):
    profile = activity.creator

    if taskId is None:
        taskId = uuid.uuid4()

    logger.info('{} create steps'.format(taskId))

    configSteps = AuditActivityConfigStep.objects \
        .filter(config=activity.config) \
        .order_by('position')

    logger.info('{} resolve assignee for every step'.format(taskId))
    stepAssigneeTuples = []
    for index, step in enumerate(configSteps):
        logger.info('{} resolve assignee for step#{}'.format(
            taskId, step.position))

        assigneeDepartment = step.assigneeDepartment
        if assigneeDepartment is None:
            # 如果部门没有配置，那么就设置为发起者所在部门
            assigneeDepartment = profile.department

        logger.info('{} resolve assignee for step#{}, dep: {}, pos: {}'.format(
            taskId, step.position, assigneeDepartment.code, step.assigneePosition.code))

        profiles = Profile.objects \
            .filter(archived=False,
                    department=assigneeDepartment,
                    position=step.assigneePosition)

        if profiles.count() == 0:
            logger.info('{} no candidates, skip'.format(taskId))
            continue

        names = ', '.join([p.name for p in profiles])
        logger.info('{} candidates: {}'.format(taskId, names))
        assignee = profiles[0]
        logger.info('{} assignee: {}'.format(taskId, assignee.name))

        stepAssigneeTuples.append((step, assignee,))

    logger.info('{} filter steps with the same assignee'.format(taskId))
    mapping = {}
    stepAssigneeTuples.reverse()
    filteredTuples = []
    for t in stepAssigneeTuples:
        step, assignee = t
        key = str(assignee.pk)
        if key in mapping:
            logger.info('{} remove step#{}'.format(taskId, step.position))
            continue

        mapping[key] = True
        filteredTuples.append(t)

    filteredTuples.reverse()
    pos = 0
    for t in filteredTuples:
        step, assignee = t

        assigneeDepartment = step.assigneeDepartment
        if assigneeDepartment is None:
            # 如果部门没有配置，那么就设置为发起者所在部门
            assigneeDepartment = profile.department

        AuditStep.objects \
            .create(activity=activity,
                    active=False,
                    assignee=assignee,
                    assigneeDepartment=assigneeDepartment,
                    assigneePosition=step.assigneePosition,
                    position=pos)
        pos = pos + 1


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

    activity = AuditActivity.objects \
        .create(config=config,
                sn=generateActivitySN(),
                state=AuditActivity.StateDraft,
                creator=profile,
                extra=data['extra'])

    if submit:
        setupSteps(activity, taskId=taskId)
        submitActivityAudit(activity)

    recordBankAccountIfNeed(profile, activity.config.subtype, activity.extra)
    recordCompanyIfNeed(profile, activity.config.subtype, activity.extra)
    recordMemo(profile, activity.config.subtype, activity.extra)

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
    # TODO: delete steps
    try:
        activity = AuditActivity.objects.get(pk=activityId)
        if activity.isCancellable():
            activity.state = AuditActivity.StateCancelled
            AuditStep.objects.filter(activity=activity).delete()
            activity.finished_at = datetime.datetime.now(tz=timezone.utc)
            activity.save()

            # delete messages
            Message.objects.filter(activity=activity).delete()
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
    # TODO: if audit type change, rebuild audit workflow
    data = json.loads(request.body.decode('utf-8'))
    activity = AuditActivity.objects.get(pk=activityId)
    activity.extra = data
    activity.save()

    recordBankAccountIfNeed(request.profile, activity.config.subtype, data)
    recordCompanyIfNeed(request.profile, activity.config.subtype, activity.extra)

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def submitAudit(request, activityId):
    # TODO: validate user permission
    activity = AuditActivity.objects.get(pk=activityId)
    if activity.state != AuditActivity.StateDraft \
            and activity.state != AuditActivity.StateCancelled:
        return JsonResponse({'errorId': 'invalid-state'}, status=400)

    setupSteps(activity, taskId=uuid.uuid4())
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

        # delete hurry up message
        Message.objects \
            .filter(activity=step.activity,
                    profile=step.assignee,
                    category='hurryup') \
            .delete()
        Message.objects \
            .filter(activity=step.activity,
                    profile=step.assignee,
                    category='progress') \
            .delete()

        step.save()
        if step.nextStep() == None:
            activity = step.activity
            activity.state = AuditActivity.StateApproved
            if activity.config.hasTask:
                activity.taskState = 'pending'
            activity.save()

            if activity.config.subtype == 'biz_contract':
                info = activity.extra['info']
                Taizhang.objects.create(
                    auditId=activity.pk,
                    date=activity.created_at.strftime('%Y-%m'),
                    asset=info['asset'],
                    upstream=info['upstream'],
                    upstream_dunwei=info['tonnage'],
                    buyPrice=info['buyPrice'],

                    downstream=info.get('downstream', ''),
                    downstream_dunwei=info['tonnage'],
                    sellPrice=info['sellPrice'],
                )
                StatsEvent.objects.create(source='taizhang', event='invalidate')

            Message.objects.create(profile=activity.creator,
                                   activity=activity,
                                   category='finish',
                                   extra={'state': 'approved'})
        else:
            nextStep = step.nextStep()
            nextStep.active = True
            nextStep.activated_at = datetime.datetime.now(tz=timezone.utc)
            nextStep.save()
            Message.objects.create(activity=step.activity,
                                   category='progress',
                                   extra={},
                                   profile=nextStep.assignee)
        return JsonResponse({'ok': True})
    except:
        logger.exception("fail to approve step")
        return JsonResponse({
            'errorId': 'approve-step-error'
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

        # delete hurry up message
        Message.objects \
            .filter(activity=step.activity,
                    profile=step.assignee,
                    category='hurryup') \
            .delete()
        Message.objects \
            .filter(activity=step.activity,
                    profile=step.assignee,
                    category='progress') \
            .delete()

        activity = step.activity
        activity.finished_at = datetime.datetime.now(tz=timezone.utc)
        activity.state = AuditActivity.StateRejected
        activity.save()

        Message.objects.create(profile=activity.creator,
                               activity=activity,
                               category='finish',
                               extra={'state': 'rejected'})
        return JsonResponse({'ok': True})
    except:
        return JsonResponse({
            'errorId': 'step-not-found'
        }, status=400)


def searchActivities(activities, search):
    parts = search.split(' ')
    keywords = []
    for part in parts:
        if part != '':
            keywords.append(part)

    result = []
    for activity in activities:
        n = activity.appDisplayName
        t = activity.appDisplayType
        if any([k in t for k in keywords]):
            result.append(activity)
        elif any([k in n for k in keywords]):
            result.append(activity)

    return result, len(result)


@require_http_methods(['GET'])
@validateToken
def mineActivities(request):
    auditType = request.GET.get('type', None)
    state = request.GET.get('state', None)
    search = request.GET.get('search', None)
    created_at_start = request.GET.get('created_at_start', None)
    created_at_end = request.GET.get('created_at_end', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    activities = AuditActivity.objects \
        .select_related('creator', 'config') \
        .filter(creator=request.profile,
                archived=False)
    if notEmpty(auditType):
        activities = activities.filter(
            config__subtype__in=auditType.split(','))

    if notEmpty(state):
        activities = activities.filter(state=state)

    if notEmpty(created_at_start):
        date = iso8601.parse_date(created_at_start)
        activities = activities.filter(created_at__gte=date)
    if notEmpty(created_at_end):
        date = iso8601.parse_date(created_at_end)
        activities = activities.filter(created_at__lt=date)

    if notEmpty(search):
        activities = activities.order_by('-updated_at')
        activities, total = searchActivities(activities, search)
        activities = activities[start:start + limit]
        return JsonResponse({
            'total': total,
            'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
        })

    activities = activities.order_by('-updated_at')
    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
    })


def notEmpty(value):
    return value is not None and value != ''


# 被分配给用户的所有审批（包含未审批和已审批的）
@require_http_methods(['GET'])
@validateToken
def relatedActivities(request):
    auditType = request.GET.get('type', None)
    creator_name = request.GET.get('creator', None)
    search = request.GET.get('search', None)
    created_at_start = request.GET.get('created_at_start', None)
    created_at_end = request.GET.get('created_at_end', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    # TODO: 处理职位变更问题
    steps = AuditStep.objects \
        .select_related('creator', 'config') \
        .filter(assignee=request.profile,
                activity__archived=False)
    steps = steps.filter(Q(active=True) |
                         Q(state__in=[
                             AuditStep.StateApproved,
                             AuditStep.StateRejected
                         ]))

    if notEmpty(auditType):
        steps = steps.filter(
            activity__config__subtype__in=auditType.split(','))
    if notEmpty(creator_name):
        steps = steps.filter(activity__creator__name=creator_name)

    if notEmpty(created_at_start):
        date = iso8601.parse_date(created_at_start)
        steps = steps.filter(activity__created_at__gte=date)
    if notEmpty(created_at_end):
        date = iso8601.parse_date(created_at_end)
        steps = steps.filter(created_at__lt=date)

    activityIdx = [s.activity.pk for s in steps]
    activities = AuditActivity.objects.filter(pk__in=activityIdx)
    activities = activities.order_by('-updated_at')

    if notEmpty(search):
        activities, total = searchActivities(activities, search)
        activities = activities[start:start + limit]
        return JsonResponse({
            'total': total,
            'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
        })

    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
    })


@require_http_methods(['GET'])
@validateToken
def assignedActivities(request):
    auditType = request.GET.get('type', None)
    creator_name = request.GET.get('creator', None)
    created_at_start = request.GET.get('created_at_start', None)
    created_at_end = request.GET.get('created_at_end', None)

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

    if notEmpty(created_at_start):
        date = iso8601.parse_date(created_at_start)
        steps = steps.filter(activity__created_at__gte=date)
    if notEmpty(created_at_end):
        date = iso8601.parse_date(created_at_end)
        steps = steps.filter(created_at__lt=date)

    activityIdx = [s.activity.pk for s in steps]
    activities = AuditActivity.objects \
        .select_related('creator', 'config') \
        .filter(pk__in=activityIdx)
    activities = activities.order_by('-updated_at')

    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
    })


@require_http_methods(['GET'])
@validateToken
def processedActivities(request):
    auditType = request.GET.get('type', None)
    creator_name = request.GET.get('creator', None)
    created_at_start = request.GET.get('created_at_start', None)
    created_at_end = request.GET.get('created_at_end', None)

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

    if notEmpty(created_at_start):
        date = iso8601.parse_date(created_at_start)
        steps = steps.filter(activity__created_at__gte=date)
    if notEmpty(created_at_end):
        date = iso8601.parse_date(created_at_end)
        steps = steps.filter(created_at__lt=date)

    activityIdx = [s.activity.pk for s in steps]
    activities = AuditActivity.objects \
        .select_related('creator', 'config') \
        .filter(pk__in=activityIdx)
    activities = activities.order_by('-updated_at')

    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
    })


@require_http_methods(['GET'])
@validateToken
def auditTasks(request):
    auditType = request.GET.get('type', None)
    state = request.GET.get('state', None)
    created_at_start = request.GET.get('created_at_start', None)
    created_at_end = request.GET.get('created_at_end', None)

    start = int(request.GET.get('start', '0'))
    limit = int(request.GET.get('limit', '20'))

    activities = AuditActivity.objects \
        .select_related('creator', 'config') \
        .filter(state=AuditActivity.StateApproved,
                config__hasTask=True,
                archived=False)
    if notEmpty(auditType):
        activities = activities.filter(
            config__subtype__in=auditType.split(','))
    if notEmpty(state):
        activities = activities.filter(taskState=state)

    if notEmpty(created_at_start):
        date = iso8601.parse_date(created_at_start)
        activities = activities.filter(created_at__gte=date)
    if notEmpty(created_at_end):
        date = iso8601.parse_date(created_at_end)
        activities = activities.filter(created_at__lt=date)

    profile = request.profile
    if profile.department.code == 'hr':
        activities = activities.filter(config__category='law')
    elif profile.department.code == 'fin':
        activities = activities.filter(config__category='fin')

    activities = activities.order_by('-updated_at')
    total = activities.count()
    activities = activities[start:start + limit]
    return JsonResponse({
        'total': total,
        'activities': [resolve_activity(activity, include_steps=False) for activity in activities]
    })


@require_http_methods(['POST'])
@validateToken
def hurryup(request, activityId):
    profile = request.profile
    activity = AuditActivity.objects.get(pk=activityId)

    if activity.creator.pk != profile.pk:
        # nothing to do
        return JsonResponse({'ok': True})
    if activity.state != AuditActivity.StateProcessing:
        # nothing to do
        return JsonResponse({'ok': True})

    step = activity.currentStep()
    if activity.canHurryup \
            and step is not None \
            and step.assignee is not None:
        Message.objects.create(activity=activity,
                               category='hurryup',
                               extra={},
                               profile=step.assignee)

    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@validateToken
def markTaskFinished(request, activityId):
    activity = AuditActivity.objects.get(pk=activityId)
    activity.taskState = 'finished'
    activity.save()
    return JsonResponse({'ok': True})
