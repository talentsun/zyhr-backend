import logging
import django.dispatch
from core.models import *

logger = logging.getLogger('core.signals')

# TODO: 暂时把各种数据处理逻辑写在一起，有需要的时候再进行拆分

# 部门、职位放生变化的时候发出这个信号
org_update = django.dispatch.Signal(providing_args=['dep', 'pos'])
# 用户离职或者所属的部门岗位发生变化的时候发出这个信号
user_org_update = django.dispatch.Signal(providing_args=['profile'])
audit_config_change = django.dispatch.Signal(providing_args=['subtype'])


@django.dispatch.receiver(org_update)
def on_org_update(sender, dep=None, pos=None, **kwargs):
    logger.info('check audit config on organization update')
    check_audit_configs(sender, dep=None, pos=None)
    check_notification()


def check_notification():
    """
    当组织机构结构发生变化的时候，需要对动态文章的阅读范围重新计算
    组织机构可能发生的变化：
    1. 组织机构重命名
    2. 部门层级被修改
    3. 部门被删除
    """
    ns = Notification.objects.filter(archived=False)
    for n in ns:
        generateNotDepByScope(n)


def check_config_step(step):
    if step.assigneeDepartment is not None and \
            step.assigneeDepartment.archived:
        return False

    if step.assigneePosition is not None and \
            step.assigneePosition.archived:
        return False

    if step.assigneePosition is not None and \
                    step.assigneeDepartment is not None:
        count = DepPos.objects \
            .filter(dep=step.assigneeDepartment, pos=step.assigneePosition) \
            .count()
        if count == 0:
            return False

    return True


def check_audit_configs(sender, dep=None, pos=None):
    """
    当部门和岗位关系恢复的时候，应该自动恢复异常的审批配置
    如果某些审批环节的配置恢复但是整个审批配置没有恢复的话，需要将恢复正常的环节的 abnormal flag 更新回来
    """
    taskId = uuid.uuid4()
    logger.info("{} check audit config".format(taskId))
    logger.info("{} check whether there are some configs which should be reset abnormal flag.".format(taskId))

    configs = AuditActivityConfig.objects.filter(archived=False, abnormal=True)
    for config in configs:
        try_restore_audit_config(config, taskId=taskId)

    """
    检查现有的审批流配置是否受影响，有以下几种情况：
    1. 审批配置流程配置的岗位被删除
    2. 部门被删除
    3. 岗位和部门之间的关联关系被取消

    以上几种情况都会导致该受影响的审批环节不可能存在负责的审批人
    """

    logger.info("{} check whether there are some configs which should be abnormal.".format(taskId))
    configs = AuditActivityConfig.objects.filter(archived=False)
    for config in configs:
        check_audit_config(config, taskId=taskId)


def check_audit_config(config, taskId=None):
    if taskId is None:
        taskId = uuid.uuid4()

    logger.info("{} check audit config:, config: {}".format(taskId, str(config.pk)))

    steps = AuditActivityConfigStep.objects \
        .select_related('assigneeDepartment', 'assigneePosition') \
        .filter(config=config) \
        .order_by('position')

    affected = False
    for step in steps:
        if not check_config_step(step):
            affected = True
            step.abnormal = True
            logger.info("{} set step abnormal, step: {}".format(taskId, str(step.pk)))
            step.save()

    if affected:
        logger.info("{} set config abnormal, config: {}".format(taskId, str(config.pk)))
        config.abnormal = True
        config.save()


def try_restore_audit_config(config, taskId=None):
    if taskId is None:
        taskId = uuid.uuid4()

    logger.info('{} try to restore audit config if it is not abnormal, config: {}'.format(taskId, str(config.pk)))

    steps = AuditActivityConfigStep.objects \
        .select_related('assigneeDepartment', 'assigneePosition') \
        .filter(config=config) \
        .order_by('position')

    abnormal = False
    for step in steps:
        if not check_config_step(step):
            abnormal = True
        else:
            step.abnormal = False
            step.save()
            logger.info("{} reset step abnormal flag, step: {}".format(taskId, str(step.pk)))

    if not abnormal:
        config.abnormal = False
        config.save()
        AuditActivityConfigStep.objects \
            .filter(config=config) \
            .update(abnormal=False)
        logger.info("{} reset config abnormal flag, config: {}".format(taskId, str(config.pk)))


@django.dispatch.receiver(audit_config_change)
def on_audit_config_change(sender, subtype=None, **kwargs):
    taskId = uuid.uuid4()

    logger.info("{} try to restore configs if some config of the subtype changed, subtype: {}", subtype)

    configs = AuditActivityConfig.objects.filter(subtype=subtype, archived=False)
    for config in configs:
        try_restore_audit_config(config, taskId=taskId)


@django.dispatch.receiver(user_org_update)
def on_profile_org_update(sender, **kwargs):
    """
    用户离职或者所属部门和职位发生变化的时候：
    1. 检查用户参与的审批，如果没有审批完成，应该找到替换者来替换该用户
    2. 找不到替换者的话，应该标记当前的审批为中断，禁止审批继续进行下去

    如果用户是职位发生了变化，也要检查被中断的审批是不是可以恢复
    """

    taskId = uuid.uuid4()
    profile = kwargs['profile']
    logger.info("{}: profile left or profile's org changed, profile: {}".format(taskId, profile.pk))

    # 检查中断的审批是否可以由于人员部门职位变化而恢复回来
    logger.info("{}: try to reopen some abnormal audit activity".format(taskId))

    activities = AuditActivity.objects \
        .filter(state=AuditActivity.StateAborted, archived=False)
    for activity in activities:
        logger.info("{}: check activity, activity: {}".format(taskId, activity.pk))

        if activity.isAbnormal():
            logger.info("{}: activity is still abnormal, activity: {}".format(taskId, activity.pk))
            continue

        # 恢复 activity
        logger.info("{}: reopen activity, activity: {}".format(taskId, activity.pk))
        steps = AuditStep.objects.filter(activity=activity, abnormal=True)
        for step in steps:
            assignee = step.candidates[0]
            step.assignee = assignee
            step.abnormal = False
            step.save()

        activity.state = AuditActivity.StateProcessing
        activity.save()
        logger.info("{}: reopen activity {} done".format(taskId, activity.pk))

    # 检查是否有审批由于用户离职或者部门职位变化而异常
    logger.info("{}: check audit activities that profile joined".format(taskId))

    dirty_steps = AuditStep.objects \
        .filter(assignee=profile,
                activity__archived=False,
                activity__state=AuditActivity.StateProcessing,
                state=AuditStep.StatePending)
    for step in dirty_steps:
        logger.info("{}: check step, step: {}".format(taskId, step.pk))

        candidate_pks = [c.pk for c in step.candidates]
        if profile.pk in candidate_pks:
            logger.info("{}: step is not affected, step: {}".format(taskId, step.pk))
            continue

        logger.info("{}: step is affected, step: {}".format(taskId, step.pk))
        if len(candidate_pks) > 0:
            logger.info("{}: update step assignee, step: {}".format(taskId, step.pk))
            assignee = step.candidates[0]
            step.assignee = assignee
            step.save()
            logger.info("{}: update step assignee done, step: {}, assignee: {}".format(taskId, step.pk, assignee.pk))
            continue

        logger.info(
            "{}: step has no candidates and abort audit activity, step: {}, activity: {}".format(taskId, step.pk,
                                                                                                 step.activity.pk))
        activity = step.activity
        logger.info("{}: abort audit activity, activity: {}".format(taskId, activity.pk))
        activity.state = AuditActivity.StateAborted
        activity.save()
        steps = AuditStep.objects.filter(activity=activity, state=AuditStep.StatePending)
        for step in steps:
            if step.candidates.count() == 0:
                step.abnormal = True
                step.save()
        logger.info("{}: abort audit activity done, activity: {}".format(taskId, activity.pk))

    logger.info("{}: task done".format(taskId))