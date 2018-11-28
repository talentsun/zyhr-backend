import logging
import time
import datetime
import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import *
from core.auth import validateToken
from core.common import *
from core.exception import *
from core.signals import *

logger = logging.getLogger('app.core.views.org')


class OrgView:
    def __init__(self):
        self.source = 'organization'

    def send_org_update(self, dep=None, pos=None):
        org_update.send(sender=self, dep=dep, pos=pos)


def createOrUpdateDepartment(data, dep=None):
    dirty = False

    parent = data.get('parent', None)
    name = data.get('name', None)

    if name is None or name == '':
        return 'invalid-parameters', dirty
        # return JsonResponse({'errorId': 'invalid-parameters'}, status=400)

    parentDep = None
    if parent is not None:
        parentDep = Department.objects.filter(pk=parent).first()
        if parentDep is None:
            return 'parent-not-found', dirty
            # return JsonResponse({'errorId': 'parent-not-found'}, status=400)

    count = Department.objects.filter(parent=parentDep, name=name).count()
    if dep is not None and dep.name == name:
        count = count - 1

    if count > 0:
        return 'department-name-duplicate', dirty
        # return JsonResponse({'errorId': 'department-name-duplicate'}, status=400)

    if dep is None:
        # create new department
        Department.objects.create(parent=parentDep, name=name)
    else:
        # update department
        if parentDep is not None and \
                (dep.isAncestorOf(parentDep) or dep.pk == parentDep.pk):
            return 'parent-cycle', dirty

        dep.name = name
        if dep.parent != parentDep:
            dep.parent = parentDep
            dirty = True

        dep.save()

    return None, dirty


@require_http_methods(['GET', 'POST'])
@validateToken
def departments(request):
    if request.method == 'GET':
        deps = Department.objects.filter(archived=False)
        return JsonResponse({
            'departments': [resolve_department(d) for d in deps]
        })
    else:  # POST
        data = json.loads(request.body.decode('utf-8'))
        error, dirty = createOrUpdateDepartment(data)

        if error is not None:
            return JsonResponse({"errorId": error}, status=400)

        if dirty:
            OrgView().send_org_update()

        return JsonResponse({'ok': True})


def archiveDepartment(dep):
    if dep is None:
        return

    for d in dep.children:
        archiveDepartment(d)

    dep.archived = True
    dep.name = 'deleted-' + str(time.time()) + dep.name
    dep.save()
    DepPos.objects.filter(dep=dep).delete()


@require_http_methods(['PUT', 'DELETE'])
@validateToken
def department(request, dep):
    department = Department.objects.filter(pk=dep).first()
    if department is None:
        return JsonResponse({'errorId': 'department-not-found'}, status=400)

    if request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        error, dirty = createOrUpdateDepartment(data, dep=department)

        if error is not None:
            return JsonResponse({"errorId": error}, status=400)

        if dirty:
            OrgView().send_org_update()

        return JsonResponse({'ok': True})

    else:  # DELETE
        if department.profiles > 0:
            return JsonResponse({'errorId': 'profiles-exist'}, status=400)

        archiveDepartment(department)

        logger.info("department deleted, dep: {}".format(department.pk))
        OrgView().send_org_update(dep=department.pk)
        return JsonResponse({'ok': True})


@require_http_methods(['GET', 'POST'])
@validateToken
def positions(request):
    if request.method == 'GET':
        positions = Position.objects.all()
        return JsonResponse({
            'positions': [resolve_position(p, include_departments=True) for p in positions]
        })
    else:  # POST
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name', None)
        departments = data.get('departments', [])

        if name is None or name == '':
            return JsonResponse({'errorId': 'invalid-parameters'}, status=400)

        pos = Position.objects.create(name=name)
        for dep in departments:
            department = Department.objects.get(pk=dep)
            DepPos.objects.create(dep=department, pos=pos)

        return JsonResponse({'ok': True})


@require_http_methods(['PUT', 'DELETE'])
@validateToken
def position(request, pos):
    position = Position.objects.filter(pk=pos).first()
    if not position:
        return JsonResponse({'errorId': 'position-not-found'}, status=400)

    if request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name', None)
        departments = data.get('departments', [])

        if name is None or name == '':
            return JsonResponse({'errorId': 'invalid-parameters'}, status=400)

        # 检查某些部门和岗位下是否还存在正常状态下的员工，如果存在那么不应该更新部门和岗位之间的关系
        items = DepPos.objects.filter(pos=position)
        for item in items:
            if str(item.dep.pk) not in departments:
                count = Profile.objects \
                    .filter(department=item.dep, position=position, archived=False) \
                    .count()
                if count > 0:
                    return JsonResponse({
                        'errorId': 'profiles-exist',
                        'department': resolve_department(item.dep)
                    }, status=400)

        position.name = name
        position.save()

        DepPos.objects.filter(pos=position).delete()
        for dep in departments:
            department = Department.objects.filter(pk=dep).first()
            if department is not None:
                DepPos.objects.create(dep=department, pos=position)

        OrgView().send_org_update(pos=position.pk)
        return JsonResponse({'ok': True})
    else:  # DELETE
        count = Profile.objects \
            .filter(position=position, archived=False) \
            .count()
        if count > 0:
            return JsonResponse({'errorId': 'profiles-exist'}, status=400)

        position.archived = True
        position.save()
        DepPos.objects.filter(pos=position).delete()

        OrgView().send_org_update(pos=position.pk)
        return JsonResponse({'ok': True})
