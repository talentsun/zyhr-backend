import logging
import django.dispatch
from core.models import *

logger = logging.getLogger('core.signals')

org_update = django.dispatch.Signal(providing_args=['dep', 'pos'])


@django.dispatch.receiver(org_update)
def check_audit_on_urg_update(sender, dep=None, pos=None, **kwargs):
    logger.info('check audit config on organization update')
    check_audit(sender, dep=None, pos=None)


def check_step(step):
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


def check_audit(sender, dep=None, pos=None):
    """
    当部门和岗位关系恢复的时候，应该自动恢复异常的审批配置
    如果某些审批环节的配置恢复但是整个审批配置没有恢复的话，需要将恢复正常的环节的 abnormal flag 更新回来
    """
    configs = AuditActivityConfig.objects.filter(archived=False, abnormal=True)
    for config in configs:
        steps = AuditActivityConfigStep.objects \
            .select_related('assigneeDepartment', 'assigneePosition') \
            .filter(config=config) \
            .order_by('position')

        abnormal = False
        for step in steps:
            if not check_step(step):
                abnormal = True
            else:
                step.abnormal = False
                step.save()

        if not abnormal:
            config.abnormal = False
            config.save()
            AuditActivityConfigStep.objects \
                .filter(config=config) \
                .update(abnormal=False)

    """
    检查现有的审批流配置是否受影响，有以下几种情况：
    1. 审批配置流程配置的岗位被删除
    2. 部门被删除
    3. 岗位和部门之间的关联关系被取消

    以上几种情况都会导致该受影响的审批环节不可能存在负责的审批人
    """
    configs = AuditActivityConfig.objects.filter(archived=False)
    for config in configs:
        steps = AuditActivityConfigStep.objects \
            .select_related('assigneeDepartment', 'assigneePosition') \
            .filter(config=config) \
            .order_by('position')

        affected = False
        for step in steps:
            if not check_step(step):
                affected = True
                step.abnormal = True
                step.save()

        if affected:
            config.abnormal = True
            config.save()
