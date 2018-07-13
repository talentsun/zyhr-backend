from core.models import *


def resolve_config(config):
    return {
        'id': str(config.pk),
        'category': config.category,
        'subtype': config.subtype
    }


def resolve_department(dep):
    if dep is None:
        return None

    return {
        'id': str(dep.pk),
        'code': dep.code,
        'name': dep.name
    }


def resolve_position(pos):
    if pos is None:
        return None

    return {
        'id': str(pos.pk),
        'name': pos.name
    }


def resolve_profile(profile):
    return {
        'id': str(profile.pk),
        'name': profile.name,
        'email': profile.email,
        'phone': profile.phone,
        'desc': profile.desc,
        'blocked': profile.blocked,

        'department': resolve_department(profile.department),
        'position': resolve_position(profile.position),

        'created_at': profile.created_at.isoformat(),
        'updated_at': profile.updated_at.isoformat(),
    }


def resolve_activity(activity):
    steps = AuditStep.objects.filter(activity=activity).order_by('position')

    return {
        'id': str(activity.pk),
        'creator': resolve_profile(activity.creator),
        'type': activity.config.subtype,
        'state': activity.state,
        'extra': activity.extra,
        'created_at': activity.created_at.isoformat(),
        'updated_at': activity.updated_at.isoformat(),
        'steps': [resolve_step(step) for step in steps]
    }


def resolve_step(step):
    return {
        'id': str(step.pk),
        'active': step.active,
        'state': step.state,
        'assignee': resolve_profile(step.assignee),
        'assigneeDepartment': resolve_department(step.assigneeDepartment),
        'assigneePosition': resolve_position(step.assigneePosition),
        'position': step.position,
        'desc': step.desc,

        'activated_at': step.activated_at.isoformat() if step.activated_at else None,
        'finished_at': step.finished_at.isoformat() if step.finished_at else None,

        'created_at': step.created_at.isoformat(),
        'updated_at': step.updated_at.isoformat()
    }
