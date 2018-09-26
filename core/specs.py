from django.db import transaction
from core.models import *


def createAuditConfig(spec=None):
    '''
    spec format: {category}.{subtype}:dep.pos->dep.pos->...
    '''
    hasTask = spec.endswith('...')
    if hasTask:
        spec = spec[0:-3]

    categorySpecs, flowSpecs = spec.split(':')
    categorySpecs, flowSpecs = categorySpecs.strip(), flowSpecs.strip()
    category, subtype = categorySpecs.split('.')

    config = AuditActivityConfig.objects \
        .create(category=category,
                hasTask=hasTask,
                subtype=subtype)

    stepSpecs = flowSpecs.split('->')
    for index, step in enumerate(stepSpecs):
        dep, pos = step.split('.')
        dep, pos = dep.strip(), pos.strip()
        pos = Position.objects.get(code=pos)
        if dep == '_':
            dep = None
        else:
            dep = Department.objects.get(code=dep)

        AuditActivityConfigStep.objects \
            .create(config=config,
                    assigneeDepartment=dep,
                    assigneePosition=pos,
                    position=index)
    return config


def updateAuditConfig(spec=None):
    hasTask = spec.endswith('...')
    if hasTask:
        spec = spec[0:-3]

    with transaction.atomic():
        categorySpecs, flowSpecs = spec.split(':')
        categorySpecs, flowSpecs = categorySpecs.strip(), flowSpecs.strip()
        category, subtype = categorySpecs.split('.')

        config = AuditActivityConfig.objects \
            .filter(category=category, subtype=subtype) \
            .first()
        if config == None:
            print('Warning!! config not found')

        AuditActivityConfigStep.objects.filter(config=config).delete()
        stepSpecs = flowSpecs.split('->')
        for index, step in enumerate(stepSpecs):
            dep, pos = step.split('.')
            dep, pos = dep.strip(), pos.strip()
            pos = Position.objects.get(code=pos)
            if dep == '_':
                dep = None
            else:
                dep = Department.objects.get(code=dep)

            AuditActivityConfigStep.objects \
                .create(config=config,
                        assigneeDepartment=dep,
                        assigneePosition=pos,
                        position=index)
    return config
