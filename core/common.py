from core.models import *


def resolve_department(dep):
    return dep.__dict__


def resolve_position(pos):
    return pos.__dict__


def resolve_profile(profile):
    return {
        'id': str(profile.pk),
        'name': profile.name,
        'email': profile.email,
        'phone': profile.phone,
        'desc': profile.desc
    }


def resolve_activity(activity):
    steps = AuditStep.objects.filter(activity=activity).order_by('position')

    return {
        'id': str(activity.pk),
        'creator': resolve_profile(activity.creator),
        'state': activity.state,
        'extra': activity.extra,
        'created_at': activity.created_at.isoformat(),
        'updated_at': activity.updated_at.isoformat(),
        'steps': [resolve_step(step) for step in steps]
    }


def resolve_step(step):
    return {
        'id': str(step.pk),
        'state': step.state,
        'assignee': resolve_profile(step.profile),
        'assigneeDepartment': resolve_department(step.asigneeDepartment),
        'assigneePosition': resolve_position(step.asigneePosition),
        'position': step.position,
        'created_at': step.created_at.isoformat(),
        'updated_at': step.updated_at.isoformat()
    }
