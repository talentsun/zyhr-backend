import datetime
import uuid

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models

from jsonfield import JSONField


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)


class DepPos(models.Model):
    dep = models.ForeignKey(Department, on_delete=models.CASCADE)
    pos = models.ForeignKey(Position, on_delete=models.CASCADE)


# v1 权限常量
P_V1_VIEW_HOME = 'view_home'  # 浏览首页
P_V1_VIEW_HOME_MINE_AUDIT = 'view_home_mine_audit'  # 浏览我发起的
P_V1_VIEW_HOME_ASSIGNED_AUDIT = 'view_home_assigned_audit'  # 浏览待我审批

P_V1_VIEW_LAUNCH_AUDIT = 'view_launch_audit'  # 浏览发起审批页面
P_V1_LAUNCH_FIN_AUDIT = 'launch_fin_audit'  # 发起财务类审批
P_V1_LAUNCH_LAW_AUDIT = 'launch_law_audit'  # 发起法务类审批

P_V1_VIEW_ASSIGNED_AUDIT = 'view_assigned_audit'  # 浏览待我审批页面
P_V1_MGR_ASSIGNED_AUDIT = 'mgr_assigned_audit'  # 浏览待我审批页面

P_V1_VIEW_AUDIT_DETAIL = 'view_audit_detail'  # 查看审批详情
P_V1_VIEW_PROCESSED_AUDIT = 'view_processed_audit'  # 浏览我已审批页面
P_V1_VIEW_MINE_AUDIT = 'view_mine_audit'  # 浏览我发起的审批页面
P_V1_CANCEL_AUDIT = 'cancel_audit'  # 撤回审批
P_V1_EDIT_AUDIT = 'edit_audit'  # 编辑审批

P_V1_VIEW_TASKS = 'view_tasks'

P_V1_VIEW_PROFILE = 'view_profile'  # 浏览个人中心
P_V1_CHANE_PHONE = 'change_phone'  # 浏览个人中心

P_V1_VIEW_ROLE = 'view_role'  # 浏览角色配置页面
P_V1_ADD_ROLE = 'add_role'  # 添加角色
P_V1_MANAGE_ROLE = 'manage_role'  # 管理角色

P_V1_VIEW_EMP = 'view_emp'  # 浏览员工配置页面
P_V1_ADD_EMP = 'add_emp'  # 添加员工
P_V1_MANAGE_EMP = 'manage_emp'  # 管理员工
P_V1 = [
    P_V1_VIEW_HOME,
    P_V1_VIEW_HOME_MINE_AUDIT,
    P_V1_VIEW_HOME_ASSIGNED_AUDIT,

    P_V1_VIEW_LAUNCH_AUDIT,
    P_V1_LAUNCH_FIN_AUDIT,
    P_V1_LAUNCH_LAW_AUDIT,

    P_V1_VIEW_AUDIT_DETAIL,

    P_V1_VIEW_ASSIGNED_AUDIT,
    P_V1_MGR_ASSIGNED_AUDIT,

    P_V1_VIEW_PROCESSED_AUDIT,
    P_V1_VIEW_MINE_AUDIT,
    P_V1_CANCEL_AUDIT,
    P_V1_EDIT_AUDIT,

    P_V1_VIEW_TASKS,

    P_V1_VIEW_PROFILE,
    P_V1_CHANE_PHONE,

    P_V1_VIEW_EMP,
    P_V1_ADD_EMP,
    P_V1_MANAGE_EMP,

    P_V1_VIEW_ROLE,
    P_V1_ADD_ROLE,
    P_V1_MANAGE_ROLE
]


class Role(models.Model):
    '''
    v1 中 extra 字段格式：Array<Permission>
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    desc = models.CharField(max_length=255, null=True)
    version = models.CharField(max_length=10, default='v1')
    archived = models.BooleanField(default=False)
    extra = JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def profiles(self):
        return Profile.objects.filter(role=self).count()


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=255, unique=True)
    department = models.ForeignKey(Department,
                                   on_delete=models.CASCADE,
                                   null=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True)
    blocked = models.BooleanField(default=False)
    desc = models.TextField(default='', null=True)
    archived = models.BooleanField(default=False)
    role = models.ForeignKey(Role, null=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def owner(self):
        if self.department is None:
            return None

        return Profile.objects \
            .filter(department=self.department,
                    position__code='owner') \
            .first()


# TODO: 支持待处理任务的生成
class AuditActivityConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    category = models.CharField(max_length=255)
    subtype = models.CharField(max_length=255, unique=True)
    hasTask = models.BooleanField(default=False)


class AuditActivityConfigStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    config = models.ForeignKey(AuditActivityConfig, on_delete=models.CASCADE)
    assigneeDepartment = models.ForeignKey(Department,
                                           null=True,
                                           on_delete=models.CASCADE)
    assigneePosition = models.ForeignKey(Position,
                                         on_delete=models.CASCADE)
    position = models.IntegerField()


class AuditActivity(models.Model):
    StateDraft = 'draft'
    StateProcessing = 'processing'
    StateApproved = 'approved'
    StateRejected = 'rejected'
    StateCancelled = 'cancelled'
    StateChoices = (
        (StateDraft, StateDraft),
        (StateProcessing, StateProcessing),
        (StateApproved, StateApproved),
        (StateRejected, StateRejected),
        (StateRejected, StateCancelled),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    sn = models.CharField(max_length=255)
    config = models.ForeignKey(AuditActivityConfig, on_delete=models.CASCADE)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE)
    state = models.CharField(
        max_length=20, choices=StateChoices, default=StateDraft)
    extra = JSONField()  # 审批相关数据，不同类型的审批，相关数据不一样，暂时使用 json 保存
    finished_at = models.DateTimeField(null=True)
    archived = models.BooleanField(default=False)  # 逻辑删除标志
    taskState = models.CharField(null=True, max_length=255)  # None or (pending / finished)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def isCancellable(self):
        if self.state != self.StateProcessing:
            return False

        steps = AuditStep.objects.filter(activity=self)
        pendingSteps = AuditStep.objects.filter(activity=self,
                                                state=AuditStep.StatePending)
        return steps.count() == pendingSteps.count()

    def currentStep(self):
        if self.state != self.StateProcessing:
            return None

        return AuditStep.objects \
            .filter(activity=self, active=True) \
            .order_by('position') \
            .first()

    def steps(self):
        return AuditStep.objects \
            .filter(activity=self) \
            .order_by('position')

    @property
    def canHurryup(self):
        now = datetime.datetime.now(tz=timezone.utc)
        start = now - datetime.timedelta(days=1)
        hurryupMsgs = Message.objects \
            .filter(activity=self,
                    category='hurryup',
                    created_at__gte=start,
                    created_at__lt=now)
        return hurryupMsgs.count() == 0

    @property
    def appDisplayName(self):
        creatorName = self.creator.name
        subtype = self.config.subtype

        category = ''
        if any([k in subtype for k in ['cost', 'money', 'loan', 'open_account', 'travel']]):
            category = '财务类'
        if 'contract' in subtype:
            category = '法务类'

        return '{}的{}审批'.format(creatorName, category)

    @property
    def appDisplayType(self):
        r = ''
        subtype = self.config.subtype
        if 'cost' in subtype:
            r = '费用报销'
        elif 'loan' in subtype:
            r = '借款申请'
        elif 'money' in subtype:
            r = '用款申请'
        elif 'open_account' in subtype:
            r = '银行开户'
        elif 'travel' in subtype:
            r = '差旅报销'
        elif 'biz' in subtype:
            r = '业务合同会签'
        elif 'fn' in subtype:
            r = '职能合同会签'

        return r


class AuditStep(models.Model):
    StatePending = 'pending'
    StateApproved = 'approved'
    StateRejected = 'rejected'
    StateChoices = (
        (StatePending, StatePending),
        (StateApproved, StateApproved),
        (StateRejected, StateRejected),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    activity = models.ForeignKey(AuditActivity, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    assignee = models.ForeignKey(Profile, on_delete=models.CASCADE)
    assigneeDepartment = models.ForeignKey(
        Department, on_delete=models.CASCADE)
    assigneePosition = models.ForeignKey(Position, on_delete=models.CASCADE)
    state = models.CharField(
        max_length=20, choices=StateChoices, default=StatePending)
    position = models.IntegerField()
    desc = models.TextField(null=True)

    activated_at = models.DateTimeField(null=True)  # 开始时间
    finished_at = models.DateTimeField(null=True)  # 结束时间

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def prevStep(self):
        if self.position == 0:
            return None
        else:
            return AuditStep.objects.get(activity=self.activity,
                                         position=self.position - 1)

    def nextStep(self):
        try:
            return AuditStep.objects.get(activity=self.activity,
                                         position=self.position + 1)
        except:
            return None


class File(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    size = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    read = models.BooleanField(default=False)  # 是否已读
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)  # 消息接受者
    activity = models.ForeignKey(AuditActivity,
                                 on_delete=models.CASCADE,
                                 null=True)
    category = models.CharField(max_length=255)  # hurryup/finish
    extra = JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


CustomerCatgetories = (
    ('c1', '大型生产商/终端用户'),
    ('c2', '中型生产商/终端、大型生产商直属贸易商、大型贸易商'),
    ('c3', '小型生产商/终端、实体贸易商'),
    ('c4', '中小型纯贸易商'),
)

CustomerNatures = (
    ('yangqi', '央企'),
    ('guoqi', '国企'),
    ('siqi', '私企'),
    ('waiqi', '外企'),
)


class Customer(models.Model):
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    rating = models.CharField(max_length=50)
    shareholder = models.CharField(max_length=255)
    faren = models.CharField(max_length=255)
    capital = models.FloatField()
    year = models.CharField(max_length=10)
    category = models.CharField(max_length=255, choices=CustomerCatgetories)
    nature = models.CharField(max_length=255)  # 公司性质
    address = models.CharField(max_length=255)
    desc = models.CharField(max_length=255)  # 备注

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def displayCategory(self):
        # TODO: refine category
        return self.category
        categories = [cc[0] for cc in CustomerCatgetories]
        index = categories.index(self.category)
        return CustomerCatgetories[index][1]

    @property
    def displayNature(self):
        natures = [cn[0] for cn in CustomerNatures]
        index = natures.index(self.nature)
        return CustomerNatures[index][1]

    @property
    def nianxian(self):
        r = datetime.datetime.now(tz=timezone.utc).year - int(self.year)
        return r


CurrencyChoices = (
    ('rmb', '人民币'),
    ('hkd', '港币'),
    ('dollar', '人民币'),
)


class FinAccount(models.Model):
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    number = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)
    currency = models.CharField(max_length=255, choices=CurrencyChoices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def displayCurrency(self):
        if self.currency == 'rmb':
            return '人民币'
        elif self.currency == 'hkd':
            return '港币'
        else:
            return '美元'
