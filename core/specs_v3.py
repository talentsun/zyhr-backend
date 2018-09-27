from core.models import *


def parseCondition(s):
    ops = ['>=', '<=', '>', '<', '=']
    conds = ['gte', 'lte', 'gt', 'lt', 'eq']
    for i, op in enumerate(ops):
        if op in s:
            index = s.index(op)
            left = s[0:index]

            right = s[index + len(op):]
            if right.isdigit():
                right = int(right)

            cond = conds[i]
            return {
                'prop': left,
                'value': right,
                'condition': cond
            }

    return None


def createAuditConfig(spec=None, fallback=False):
    """
    spec v3 format: {category}.{subtype}(condition1,condition2...):dep.pos->dep.pos->...
    """

    hasTask = spec.endswith('...')
    if hasTask:
        spec = spec[0:-3]

    categorySpecs, flowSpecs = spec.split(':')
    categorySpecs, flowSpecs = categorySpecs.strip(), flowSpecs.strip()

    if '(' not in categorySpecs:
        conditions = []
    else:
        i1 = categorySpecs.index('(')
        i2 = categorySpecs.index(')')
        conditions = categorySpecs[i1 + 1:i2]
        conditions = conditions.split(',')
        conditions = [parseCondition(c) for c in conditions]
        categorySpecs = categorySpecs[:i1]

    category, subtype = categorySpecs.split('.')

    if fallback:
        priority = 0
    else:
        priority = 1
        lastConfig = AuditActivityConfig.objects \
            .filter(category=category, subtype=subtype, archived=False) \
            .order_by('-priority') \
            .first()
        if lastConfig is not None:
            priority = lastConfig.priority + 1

    config = AuditActivityConfig.objects \
        .create(category=category,
                conditions=conditions,
                fallback=fallback,
                priority=priority,
                hasTask=hasTask,
                subtype=subtype)

    stepSpecs = flowSpecs.split('->')
    for index, step in enumerate(stepSpecs):
        dep, pos = step.split('.')
        dep, pos = dep.strip(), pos.strip()
        if dep == '_':
            dep = None
            pos = None
        else:
            dep = Department.objects.get(code=dep)
            pos = dep.resolvePosition(pos)

        AuditActivityConfigStep.objects \
            .create(config=config,
                    assigneeDepartment=dep,
                    assigneePosition=pos,
                    position=index)
    return config
