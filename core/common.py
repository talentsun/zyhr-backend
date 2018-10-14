from django.utils import timezone

from core.models import *


def resolve_department(dep):
    if dep is None:
        return None

    dps = DepPos.objects.filter(dep=dep)
    positions = [i.pos for i in dps]

    return {
        'parent': str(dep.parent.pk) if dep.parent else None,
        'id': str(dep.pk),
        'code': dep.code,
        'name': dep.name,
        'displayName': dep.displayName,
        'archived': dep.archived,
        'positions': [{
            'id': str(p.pk),
            'name': p.name,
            'code': p.code
        } for p in positions]
    }


def resolve_position(pos):
    if pos is None:
        return None

    return {
        'id': str(pos.pk),
        'archived': pos.archived,
        'name': pos.name
    }


def resolve_profile(profile,
                    orgs=False,
                    include_messages=True,
                    include_pending_tasks=True,
                    include_memo=True):
    result = {
        'id': str(profile.pk),
        'name': profile.name,
        'email': profile.email,
        'phone': profile.phone,
        'desc': profile.desc,
        'blocked': profile.blocked,
        'role': resolve_role(profile.role),
        'department': resolve_department(profile.department),
        'position': resolve_position(profile.position),

        'created_at': profile.created_at.isoformat(),
        'updated_at': profile.updated_at.isoformat(),
    }

    if include_messages:
        messages = Message.objects \
            .filter(profile=profile, read=False) \
            .order_by('-updated_at')
        result['messages'] = [{
            'id': str(m.pk),
            'read': m.read,
            'activity': {
                'id': str(m.activity.pk),
                'type': str(m.activity.config.subtype),
                'creator': {
                    'id': str(m.activity.creator.pk),
                    'name': m.activity.creator.name
                }
            },
            'category': m.category,
            'extra': m.extra
        } for m in messages]

    if include_pending_tasks:
        pendingTasks = AuditActivity.objects \
            .filter(state=AuditActivity.StateApproved,
                    archived=False,
                    taskState='pending')
        if profile.department is not None and profile.department.code == 'hr':
            pendingTasks = pendingTasks.filter(config__category='law')
        elif profile.department is not None and profile.department.code == 'fin':
            pendingTasks = pendingTasks.filter(config__category='fin')

        pendingTasks = pendingTasks.count()
        result['pendingTasks'] = pendingTasks

    if orgs:
        deps = Department.objects.all()
        result['departments'] = [resolve_department(d) for d in deps]

    if include_memo:
        accounts = BankAccount.objects.all()
        companies = Company.objects.all()
        memo = Memo.objects.all()

        result['accounts'] = [{
            'name': account.name,
            'bank': account.bank,
            'number': account.number
        } for account in accounts]

        result['companies'] = [{
            'name': c.name,
        } for c in companies]

        result['memo'] = [{
            'category': m.category,
            'value': m.value
        } for m in memo]

        return result


def resolve_activity(activity, include_steps=True):
    result = {
        'id': str(activity.pk),
        'sn': activity.sn,
        'creator': resolve_profile(activity.creator,
                                   include_memo=False,
                                   include_messages=False,
                                   include_pending_tasks=False),
        'type': activity.config.subtype,
        'state': activity.state,
        'taskState': activity.taskState,
        'extra': activity.extra,
        'canHurryup': activity.canHurryup,
        'created_at': activity.created_at.isoformat(),
        'updated_at': activity.updated_at.isoformat()
    }

    if include_steps:
        steps = AuditStep.objects.filter(activity=activity).order_by('position')
        result['steps'] = [resolve_step(step) for step in steps]

    return result


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


def resolve_role(r):
    if r is None:
        return None

    return {
        'id': str(r.pk),
        'name': r.name,
        'profiles': r.profiles,
        'version': r.version,
        'desc': r.desc,
        'extra': r.extra
    }


def resolve_customer(c):
    return {
        'id': c.pk,
        'name': c.name,
        'rating': c.rating,
        'shareholder': c.shareholder,
        'faren': c.faren,
        'capital': c.capital,
        'year': c.year,
        'category': c.category,
        'nature': c.nature,
        'address': c.address,
        'desc': c.desc,

        'creator': resolve_profile(c.creator) if c.creator is not None else None,

        'created_at': c.created_at.isoformat(),
        'updated_at': c.updated_at.isoformat()
    }


def resolve_account(a):
    return {
        'id': a.pk,
        'name': a.name,
        'bank': a.bank,
        'number': a.number,
        'currency': a.currency,

        'creator': resolve_profile(a.creator) if a.creator is not None else None,

        'created_at': a.created_at.isoformat(),
        'updated_at': a.updated_at.isoformat()
    }


def resolve_config_step(step):
    return {
        'pk': str(step.pk),
        'department': resolve_department(step.assigneeDepartment),
        'position': resolve_position(step.assigneePosition)
    }


def resolve_config(config):
    steps = AuditActivityConfigStep.objects.filter(config=config).order_by('position')

    return {
        'id': str(config.pk),
        'priority': config.priority,
        'fallback': config.fallback,
        'conditions': config.conditions,
        'steps': [resolve_config_step(s) for s in steps]
    }
