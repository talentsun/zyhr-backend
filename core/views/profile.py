import json
import logging
import xlwt

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from sendfile import sendfile

from core.auth import validateToken
from core.common import *
from core.signals import *

logger = logging.getLogger('app.core.views.profile')


def getLoginName(username):
    counter = 1

    while User.objects.filter(username=username).count() > 0:
        username = username + str(counter)

    return username


class PView:
    def __init__(self):
        self.source = 'profile'

    def send_user_org_update(self, profile=None):
        user_org_update.send(sender=self, profile=profile)


@require_http_methods(['POST', 'GET'])
@validateToken
@transaction.atomic
def profiles(request):
    if request.method == 'GET':
        dep = request.GET.get('department', None)
        pos = request.GET.get('position', None)
        name = request.GET.get('name', None)
        phone = request.GET.get('phone', None)
        email = request.GET.get('email', None)

        start = int(request.GET.get('start', '0'))
        limit = int(request.GET.get('limit', '20'))

        profiles = Profile.objects \
            .filter(archived=False) \
            .order_by('-updated_at')

        # filter by department
        if dep is not None and dep != '':
            department = Department.objects.filter(pk=dep).first()
            if department is not None:
                profiles = profiles.filter(department=department)

        # by position
        if pos is not None and pos != '':
            position = Position.objects.filter(pk=pos).first()
            if position is not None:
                profiles = profiles.filter(position=position)

        # by name
        if name is not None and name != '':
            profiles = profiles.filter(name__contains=name)

        # by phone
        if phone is not None and phone != '':
            profiles = profiles.filter(phone=phone)

        # by email
        if email is not None and email != '':
            profiles = profiles.filter(email=email)

        total = profiles.count()
        profiles = profiles[start:start + limit]

        return JsonResponse({
            'total': total,
            'profiles': [
                resolve_profile(profile,
                                include_messages=False,
                                include_pending_tasks=False,
                                include_memo=False)
                for profile in profiles
            ]
        })
    else:  # POST
        data = json.loads(request.body.decode('utf-8'))

        dep = data['department']
        pos = data['position']

        department = Department.objects.get(pk=dep)
        position = Position.objects.get(pk=pos)
        email = data.get('email', None)
        phone = data.get('phone', None)

        for prop in ['department', 'position', 'email', 'phone']:
            if prop in data:
                data.pop(prop)

        realname = data['realname']
        login_name = getLoginName(realname)

        user = User.objects.create(username=login_name)
        user.set_password('123456')
        user.save()

        profile = Profile.objects.create(**{
            'blocked': True,
            'user': user,
            'name': login_name,
            'role': None,
            'department': department,
            'position': position,
            'phone': phone,
            'email': email
        })

        ProfileInfo.objects.create(profile=profile, **data)

        logger.info("profile added, profile: {}".format(profile.pk))
        PView().send_user_org_update(profile=profile)
        return JsonResponse({'ok': True})


@require_http_methods(['GET', 'DELETE', 'PUT'])
@validateToken
@transaction.atomic
def profile(request, profileId):
    if request.method == 'GET':
        profile = Profile.objects.get(pk=profileId)
        return JsonResponse(resolve_profile(profile))
    elif request.method == 'DELETE':
        profile = Profile.objects.get(pk=profileId)
        profileInfo = ProfileInfo.objects.get(profile=profile)

        user = profile.user
        user.username = 'deleted-{}'.format(profile.name)
        user.save()

        profileInfo.archived = True
        profileInfo.state = ProfileInfo.StateLeft
        profileInfo.save()

        profile.name = 'deleted-{}'.format(profile.name)
        profile.archived = True
        profile.save()

        profile = Profile.objects.get(pk=profile.pk)
        PView().send_user_org_update(profile=profile)

        return JsonResponse({'ok': True})
    else:  # PUT
        data = json.loads(request.body.decode('utf-8'))

        profile = Profile.objects.get(pk=profileId)
        profileInfo = ProfileInfo.objects.get(profile=profile)

        user_left = False
        if 'state' in data and data['state'] != profileInfo.state:
            if data['state'] != ProfileInfo.StateLeft:
                return JsonResponse({'errorId': 'invalid-profile-state'})

            user_left = True

        dep = data['department']
        pos = data['position']

        department = Department.objects.get(pk=dep)
        position = Position.objects.get(pk=pos)
        email = data.get('email', None)
        phone = data.get('phone', None)

        for prop in ['department', 'position', 'email', 'phone']:
            if prop in data:
                data.pop(prop)

        profile_org_change = False
        if profile.department != department or profile.position != position:
            profile_org_change = True

        partial = {
            'department': department,
            'position': position,
            'email': email,
            'phone': phone
        }
        if user_left:
            partial = {'blocked': True}
        Profile.objects.filter(pk=profile.pk).update(**partial)
        ProfileInfo.objects.filter(pk=profileInfo.pk).update(**data)

        if profile_org_change or user_left:
            profile = Profile.objects.get(pk=profile.pk)
            PView().send_user_org_update(profile=profile)

        return JsonResponse({'ok': True})


@require_http_methods(['GET'])
def export(request):
    pis = ProfileInfo.objects.exclude(state=ProfileInfo.StateLeft)

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    props = [
        {'title': '姓名', 'prop': 'realname'},
        {'title': '部门', 'prop': lambda p: p.profile.department.name},
        {'title': '职位', 'prop': lambda p: p.profile.position.name},
        {'title': '性别', 'prop': 'gender'},
        {'title': '民族', 'prop': 'nation'},
        {'title': '籍贯', 'prop': 'jiguan'},
        {'title': '最高学历', 'prop': 'education'},
        {'title': '手机', 'prop': lambda p: p.profile.phone},
        {'title': '邮箱', 'prop': lambda p: p.profile.email},
        {'title': '入职时间', 'prop': lambda p: p.join_at.strftime('%Y-%m-%d') if p.join_at else ''},
        {'title': '转正时间', 'prop': lambda p: p.positive_at.strftime('%Y-%m-%d') if p.positive_at else ''},
        {'title': '社保', 'prop': 'shebao'},
        {'title': '最高学历', 'prop': 'education'},
        {'title': '紧急联系人姓名', 'prop': 'contact_name'},
        {'title': '紧急联系人电话', 'prop': 'contact_phone'},
        {'title': '备注', 'prop': 'desc'}
    ]
    for index, prop in enumerate(props):
        sheet.write(0, index, prop['title'])

    for row, pi in enumerate(pis):
        for col, prop in enumerate(props):
            if type(prop['prop']) == str:
                sheet.write(row + 1, col, getattr(pi, prop['prop']))
            else:
                sheet.write(row + 1, col, prop['prop'](pi))

    xf.save(f)
    return sendfile(request, f, attachment=True, attachment_filename='export.xls')
