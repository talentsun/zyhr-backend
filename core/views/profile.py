import pandas
import json
import logging
import xlwt

from django.db import transaction
from django.conf import settings
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


def createProfileInfo(data):
    dep = data['department']
    pos = data['position']

    with transaction.atomic():
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

        pi = ProfileInfo.objects.create(profile=profile, **data)
        return profile, pi


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
            profiles = profiles.filter(email__contains=email)

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
        profile, pi = createProfileInfo(data)

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


def map_dep(data, value):
    if pandas.isnull(value):
        value = None

    dep = Department.objects.filter(name=value, archived=False).first()
    data['department'] = dep.pk if dep else None


def map_pos(data, value):
    if pandas.isnull(value):
        value = None

    pos = Position.objects.filter(name=value, archived=False).first()
    data['position'] = pos.pk if pos else None


def map_prop(prop):
    def fn(data, value):
        if pandas.isnull(value):
            value = None

        data[prop] = value

    return fn


def map_arr(prop, arr):
    def fn(data, value):
        if pandas.isnull(value):
            value = None

        if value in arr:
            data[prop] = str(arr.index(value))
        else:
            data[prop] = None

    return fn


def map_dict(prop, d):
    def fn(data, value):
        if pandas.isnull(value):
            value = None

        target = None
        for k in d:
            v = d[k]
            if v == value:
                target = k
                break

        data[prop] = target

    return fn


excel_props = [
    {'title': '姓名', 'prop': 'realname'},
    {'title': '身份证号', 'prop': 'id_number'},
    {'title': '部门', 'prop': lambda p: p.profile.department.name, 'mapper': map_dep},
    {'title': '职位', 'prop': lambda p: p.profile.position.name, 'mapper': map_pos},
    {'title': '生日', 'prop': 'birthday'},
    {'title': '性别', 'prop': lambda p: ['未知', '男', '女'][p.gender],
     'mapper': map_arr('gender', ['未知', '男', '女'])},
    {'title': '民族', 'prop': 'nation'},
    {'title': '邮箱', 'prop': lambda p: p.profile.email, 'mapper': map_prop('email')},
    {'title': '手机', 'prop': lambda p: p.profile.phone, 'mapper': map_prop('phone')},
    {'title': '身高', 'prop': 'height'},
    {'title': '体重', 'prop': 'weight'},
    {'title': '血型', 'prop': 'blood'},
    {'title': '政治面貌',
     'prop': lambda p: ['群众', '共产党员', '民主党院', '民进党员'][int(p.zhengzhimianmao)] \
         if p.zhengzhimianmao is not None and p.zhengzhimianmao != '' else '',
     'mapper': map_arr('zhengzhimianmao', ['群众', '共产党员', '民主党院', '民进党员'])
     },
    {'title': '入党时间', 'prop': lambda p: p.rudang_date if p.zhengzhimianmao is not None else '',
     'mapper': map_prop('rudang_date')},
    {'title': '籍贯', 'prop': 'jiguan'},
    {'title': '户口所在地', 'prop': 'hukou_location'},

    {'title': '岗位类别',
     'prop': lambda p: ['前台', '中台', '后台', '待定'][int(p.work_category)] \
         if p.work_category is not None and p.work_category != '' else '',
     'mapper': map_arr('work_category', ['前台', '中台', '后台', '待定'])},
    {'title': '就职状态',
     'prop': lambda p: {'testing': '试用', 'normal': '正式员工', 'left': '离职'}[p.state],
     'mapper': map_dict('state', {'testing': '试用', 'normal': '正式员工', 'left': '离职'})},
    {'title': '入司日期', 'prop': lambda p: p.join_at.strftime('%Y-%m-%d') if p.join_at else '',
     'mapper': map_prop('join_at')},
    {'title': '入司日期（合同）', 'prop': lambda p: p.join_at_contract.strftime('%Y-%m-%d') if p.join_at_contract else '',
     'mapper': map_prop('join_at_contract')},
    {'title': '转正日期', 'prop': lambda p: p.positive_at.strftime('%Y-%m-%d') if p.positive_at else '',
     'mapper': map_prop('positive_at')},
    {'title': '转正日期（合同）',
     'prop': lambda p: p.positive_at_contract.strftime('%Y-%m-%d') if p.positive_at_contract else '',
     'mapper': map_prop('positive_at_contract')},
    {'title': '转正情况', 'prop': 'positive_desc'},
    {'title': '合同到期时间', 'prop': 'contract_due'},
    {'title': '其他工作情况', 'prop': 'work_desc'},
    {'title': '其他工作变动', 'prop': 'work_transfer_desc'},

    {'title': '最高学历', 'prop': 'education'},
    {'title': '最高学历毕业时间', 'prop': 'graduation_date'},
    {'title': '最高学历毕业学校', 'prop': 'school'},
    {'title': '最高学历专业', 'prop': 'spec'},
    {'title': '最高学位',
     'prop': lambda p: ['本科', '硕士', '博士', '专科'][int(p.education)] \
         if p.education is not None and p.education != '' else '',
     'mapper': map_arr('education', ['本科', '硕士', '博士', '专科'])},
    {'title': '驾驶证',
     'prop': lambda p: '有' if p.driving == '1' else '无',
     'mapper': map_arr('driving', ['无', '有'])},
    {'title': '外语等级及语种',
     'prop': lambda p: ['CET4', 'CET6', '英语专八', '英语专四', '雅思', '托福', '日语', '阿拉伯语', '法语'][int(p.language)] \
         if p.language is not None and p.language != '' else '无',
     'mapper': map_arr('language', ['CET4', 'CET6', '英语专八', '英语专四', '雅思', '托福', '日语', '阿拉伯语', '法语'])},
    {'title': '其他教育经历', 'prop': 'education_desc'},
    {'title': '职业技能证书', 'prop': 'skill_certs'},

    {'title': '通讯地址', 'prop': 'contact_address'},
    {'title': '紧急联系人姓名', 'prop': 'contact_name'},
    {'title': '紧急联系人电话', 'prop': 'contact_phone'},
    {'title': '紧急联系人与本人关系',
     'prop': lambda p: {'father': '父子/父女', 'mother': '母子/母女', 'other': '夫妻/朋友'}[p.contact_relation] \
         if p.contact_relation is not None and p.contact_relation != '' else '',
     'mapper': map_dict('contact_relation', {'father': '父子/父女', 'mother': '母子/母女', 'other': '夫妻/朋友'})}
]


def createProfileByTuple(t):
    logger.info(t)

    data = {}
    for index, item in enumerate(excel_props):
        value = t[index + 1]
        if 'mapper' not in item:
            if pandas.isnull(value):
                value = None
            data[item['prop']] = value
        else:
            mapper = item['mapper']
            mapper(data, value)

    return createProfileInfo(data)


@require_http_methods(['POST'])
@validateToken
def importProfiles(request):
    data = json.loads(request.body.decode('utf-8'))
    fileId = data['file']
    f = File.objects.get(pk=fileId)
    ex_data = pandas.read_excel('{}/{}'.format(settings.DATA_DIR, f.path))
    total, success = 0, 0
    for t in ex_data.itertuples():
        total = total + 1
        profile = None
        try:
            profile, _ = createProfileByTuple(t)
            success = success + 1
        except:
            logger.exception("fail to import profile info")

        if profile is not None:
            PView().send_user_org_update(profile=profile)

    return JsonResponse({'success': success, 'fail': total - success})


@require_http_methods(['GET'])
def export(request):
    pis = ProfileInfo.objects.exclude(state=ProfileInfo.StateLeft)

    f = '/tmp/{}.xls'.format(str(uuid.uuid4()))
    xf = xlwt.Workbook()
    sheet = xf.add_sheet('sheet1')

    for index, prop in enumerate(excel_props):
        sheet.write(0, index, prop['title'])

    for row, pi in enumerate(pis):
        for col, prop in enumerate(excel_props):
            logger.info('col {}'.format(prop))
            if type(prop['prop']) == str:
                sheet.write(row + 1, col, getattr(pi, prop['prop']))
            else:
                sheet.write(row + 1, col, prop['prop'](pi))

    xf.save(f)

    return sendfile(request, f, attachment=True,
                    attachment_filename='员工档案{}.xls'.format(timezone.now().strftime('%Y%m%d')))
