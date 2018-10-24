import datetime
import uuid

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models

from jsonfield import JSONField


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50, null=True)
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    archived = models.BooleanField(default=False)

    def resolvePosition(self, code):
        for item in DepPos.objects.filter(dep=self):
            if item.pos.code == code:
                return item.pos

        return None

    @property
    def identity(self):
        if self.code:
            return self.code
        else:
            return str(self.pk)

    @property
    def displayName(self):
        nodes = []

        node = self
        while node is not None:
            nodes.append(node.name)
            node = node.parent

        nodes.reverse()
        return '-'.join(nodes)

    def isAncestorOf(self, dep):
        parents = []

        p = dep.parent
        while p is not None:
            parents.append(p.pk)
            p = p.parent

        return self.pk in parents

    @property
    def children(self):
        return Department.objects.filter(parent=self, archived=False)

    @property
    def profiles(self):
        result = 0
        p1 = Profile.objects \
            .filter(department=self, archived=False) \
            .count()

        result = result + p1

        children = Department.objects.filter(archived=False, parent=self)
        for c in children:
            result = result + c.profiles

        return result


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50, null=True)
    name = models.CharField(max_length=255)

    archived = models.BooleanField(default=False)

    @property
    def identity(self):
        if self.code:
            return self.code
        else:
            return str(self.pk)


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
P_V1_MARK_TASK_FINISHED = 'mark_task_finished'

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
    P_V1_MARK_TASK_FINISHED,

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
    email = models.CharField(max_length=255, null=True, default='')
    phone = models.CharField(max_length=255, unique=True, null=True)
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

    deviceId = models.CharField(max_length=255, null=True)

    @property
    def owner(self):
        if self.department is None:
            return None

        return Profile.objects \
            .filter(department=self.department,
                    position__code='owner',
                    archived=False) \
            .first()


class ProfileInfo(models.Model):
    StateTesting = "testing"  # 试用期
    StateNormal = "normal"  # 转正
    StateLeft = "left"  # 离职
    StateChoices = (
        (StateTesting, StateTesting),
        (StateNormal, StateNormal),
        (StateLeft, StateLeft)
    )

    """
    员工档案表
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.OneToOneField(Profile, null=True, on_delete=models.CASCADE)
    state = models.CharField(max_length=20, choices=StateChoices, default=StateTesting)  # 员工状态，默认是试用期
    realname = models.CharField(max_length=255, null=True)  # 姓名，可重复
    archived = models.BooleanField(default=False)

    # 基本信息，电话/邮件/部门/职位在 profile 表当中
    gender = models.IntegerField(default=0)  # 0：未知，1：男，2：女
    nation = models.CharField(max_length=255, null=True)  # 民族
    jiguan = models.CharField(max_length=255, null=True)  # 籍贯
    education = models.CharField(max_length=255, null=True)  # 最高学历

    # 人事档案信息
    join_at = models.DateTimeField(null=True)  # 入职时间
    positive_at = models.DateTimeField(null=True)  # 转正时间
    contract = models.CharField(max_length=255, null=True)  # 劳动合同
    shebao = models.CharField(max_length=255, null=True)  # 社保缴纳

    contact_name = models.CharField(max_length=255, null=True)  # 紧急联系人姓名
    contact_phone = models.CharField(max_length=255, null=True)  # 紧急联系人电话
    desc = models.CharField(max_length=255)  # 备注

    attachments = JSONField(null=True)  # 相关附件

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AuditActivityConfig(models.Model):
    '''
    conditions 结构设计：
    [{prop: "xxxx", compare: "eq/lt/gte", value: ""}...]
    prop 常见取值 amount/creator.department/creator.position
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    category = models.CharField(max_length=255, null=True)  # fin/law/hr
    subtype = models.CharField(max_length=255)  # cost/loan/money/open_account/travel/biz/fn
    hasTask = models.BooleanField(default=False)  # hasTask 在 v3 版本已经废弃

    fallback = models.BooleanField(default=False)  # 是否是默认审批流
    priority = models.IntegerField(default=0)  # 只有默认审批流为 0
    conditions = JSONField(null=True)  # 审批流激活条件

    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    abnormal = models.BooleanField(default=False)  # 审批流配置是否异常


class AuditActivityConfigStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    config = models.ForeignKey(AuditActivityConfig, on_delete=models.CASCADE)
    assigneeDepartment = models.ForeignKey(Department,
                                           null=True,
                                           on_delete=models.CASCADE)
    assigneePosition = models.ForeignKey(Position,
                                         null=True,
                                         on_delete=models.CASCADE)
    position = models.IntegerField()
    abnormal = models.BooleanField(default=False)  # 审批环节是否异常

    def candidates(self, profile):
        if self.assigneeDepartment is not None:
            return resolveCandidates(self.assigneeDepartment, self.assigneePosition)

        # 适配 v1 自动找发起人部门负责人的情况
        department = profile.department
        position = department.resolvePosition('owner')
        return resolveCandidates(department, position)


class AuditActivity(models.Model):
    StateDraft = 'draft'
    StateProcessing = 'processing'
    StateApproved = 'approved'
    StateRejected = 'rejected'
    StateCancelled = 'cancelled'
    StateAborted = 'aborted'  # v3 当中的新状态，表示审批由于审批流中负责人员无法正确更换而导致的审批异常中断
    StateChoices = (
        (StateDraft, StateDraft),
        (StateProcessing, StateProcessing),
        (StateApproved, StateApproved),
        (StateRejected, StateRejected),
        (StateRejected, StateCancelled),
        (StateAborted, StateAborted),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    sn = models.CharField(max_length=255)
    config = models.ForeignKey(AuditActivityConfig, on_delete=models.CASCADE)
    config_data = JSONField(null=True)  # 对审批配置数据进行备份
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

    def isAbnormal(self):
        """
        检查审批当中是否有某些审批环节是无法找到正确的负责人的
        """

        abnormal = False
        for step in self.steps():
            if step.candidates.count() == 0:
                abnormal = True
                break

        return abnormal


def resolveCandidates(department, position):
    pis = ProfileInfo.objects \
        .exclude(state=ProfileInfo.StateLeft) \
        .filter(profile__archived=False,
                profile__department=department,
                profile__position=position)
    profile_pks = [p.profile.pk for p in pis]
    profiles = Profile.objects.filter(pk__in=profile_pks)
    return profiles


class AuditStep(models.Model):
    """
    AuditStep 表示已发起审批的其中一个审批环节
    """
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

    abnormal = models.BooleanField(default=False)  # 异常标记
    extra = JSONField(null=True)  # v3 之后有些审批流程当中需要自定义的数据

    activated_at = models.DateTimeField(null=True)  # 开始时间
    finished_at = models.DateTimeField(null=True)  # 结束时间

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def candidates(self):
        return resolveCandidates(self.assigneeDepartment, self.assigneePosition)

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
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=255)
    bank = models.CharField(max_length=255)


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255)


# 记忆数据
class Memo(models.Model):
    category = models.CharField(max_length=255)  # upstream/downstream/asset...
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    value = models.CharField(max_length=255, null=True)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    read = models.BooleanField(default=False)  # 是否已读
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)  # 消息接受者
    activity = models.ForeignKey(AuditActivity,
                                 on_delete=models.CASCADE,
                                 null=True)
    category = models.CharField(max_length=255)  # hurryup/finish/progress
    apn_sent = models.BooleanField(default=False)
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
    archived = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    rating = models.CharField(max_length=50)
    shareholder = models.CharField(max_length=255)
    faren = models.CharField(max_length=255)
    capital = models.CharField(max_length=255, null=True)
    year = models.CharField(max_length=10)
    category = models.CharField(max_length=255, choices=CustomerCatgetories)
    nature = models.CharField(max_length=255)  # 公司性质
    address = models.CharField(max_length=255)
    desc = models.CharField(max_length=255)  # 备注

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def displayCategory(self):
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


class FinCustomer(models.Model):
    org = models.CharField(max_length=255)  # 对接银行/机构
    layer = models.CharField(max_length=255)  # 银行/机构层级
    owner = models.CharField(max_length=255)  # 负责人
    interface = models.CharField(max_length=255)
    interfacePosition = models.CharField(max_length=255)
    interfacePhone = models.CharField(max_length=255)
    meetTime = models.DateTimeField()
    meetPlace = models.CharField(max_length=255)
    member = models.CharField(max_length=255, null=True)
    otherMember = models.CharField(max_length=255, null=True)
    otherMemberPosition = models.CharField(max_length=255, null=True)
    desc = models.TextField(null=True)  # 沟通情况
    next = models.TextField(null=True)  # 后续工作安排
    note = models.TextField(null=True) # 备注

    creator = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True)
    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FinCustomerOps(models.Model):
    record = models.ForeignKey(FinCustomer, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    op = models.CharField(max_length=50)  # create/modify/delete
    prop = models.CharField(max_length=50, null=True)
    extra = JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


CurrencyChoices = (
    ('rmb', '人民币'),
    ('hkd', '港币'),
    ('dollar', '人民币'),
)


class FinAccount(models.Model):
    archived = models.BooleanField(default=False)
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


class StatsTransactionRecord(models.Model):
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE)

    date = models.CharField(max_length=50)
    number = models.CharField(max_length=255)
    income = models.FloatField(null=True)
    outcome = models.FloatField(null=True)
    desc = models.CharField(max_length=255, default='', null=True)
    balance = models.FloatField()
    other = models.CharField(max_length=255)  # 对方账号名称
    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StatsTransactionRecordOps(models.Model):
    record = models.ForeignKey(StatsTransactionRecord, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    op = models.CharField(max_length=50)  # create/modify/delete
    prop = models.CharField(max_length=50, null=True)
    extra = JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Taizhang(models.Model):
    auditId = models.UUIDField(null=True)
    archived = models.BooleanField(default=False)

    date = models.CharField(max_length=255)  # 月份 YYYY-MM
    company = models.CharField(null=True, default='中阅和瑞', max_length=255)  # 公司名称
    asset = models.CharField(max_length=255)  # 货物标的
    upstream = models.CharField(max_length=255)  # 上游供方
    upstream_dunwei = models.DecimalField(max_digits=32, decimal_places=4)  # 上游合同吨位
    buyPrice = models.DecimalField(max_digits=32, decimal_places=4)  # 采购单价

    kaipiao_dunwei = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 开票吨位，用户填写
    upstream_jiesuan_price = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 上游结算价格，用户填写

    downstream = models.CharField(max_length=255, null=True)  # 现有单位
    downstream_dunwei = models.DecimalField(max_digits=32, decimal_places=4)  # 下游合同吨位
    sellPrice = models.DecimalField(max_digits=32, decimal_places=4)  # 销售价格

    kaipiao_dunwei_trade = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 开票吨位（贸易量），用户填写
    downstream_jiesuan_price = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 下游结算价格，用户填写

    shangyou_zijin_zhanya = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 上游资金占压
    shangyou_kuchun_liang = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 上游库存量
    shangyou_kuchun_yuji_danjia = models.DecimalField(null=True, max_digits=32, decimal_places=4)  # 上游库存预计单价

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def xiaoshou_jine(self):
        if self.kaipiao_dunwei_trade is None or \
                        self.downstream_jiesuan_price is None:
            return 0
        else:
            return self.kaipiao_dunwei_trade * self.downstream_jiesuan_price

    @property
    def caigou_jine(self):
        if self.kaipiao_dunwei is None or \
                        self.upstream_jiesuan_price is None:
            return 0
        else:
            return self.kaipiao_dunwei * self.upstream_jiesuan_price

    @property
    def kuchun_jine(self):
        if self.shangyou_kuchun_liang is None or \
                        self.shangyou_kuchun_yuji_danjia is None:
            return 0
        else:
            return self.shangyou_kuchun_liang * self.shangyou_kuchun_yuji_danjia

    @property
    def hetong_jine(self):
        if self.upstream_dunwei is None or \
                        self.buyPrice is None:
            return 0
        else:
            return self.buyPrice * self.upstream_dunwei


class TaizhangOps(models.Model):
    record = models.ForeignKey(Taizhang, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    op = models.CharField(max_length=50)  # create/modify/delete
    prop = models.CharField(max_length=50, null=True)
    extra = JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StatsEvent(models.Model):
    source = models.CharField(max_length=255)  # customer/taizhang/funds
    event = models.CharField(max_length=255)  # invalidate

    created_at = models.DateTimeField(auto_now_add=True)


# 资金信息统计数据
class TransactionStat(models.Model):
    account = models.ForeignKey(FinAccount, on_delete=models.CASCADE)

    category = models.CharField(max_length=255)  # week / total
    startDayOfWeek = models.CharField(max_length=255, null=True)

    income = models.DecimalField(decimal_places=2, max_digits=19)
    outcome = models.DecimalField(decimal_places=2, max_digits=19)
    balance = models.DecimalField(decimal_places=2, max_digits=19)


class TaizhangStat(models.Model):
    category = models.CharField(max_length=255)  # month / total

    month = models.CharField(max_length=255, null=True)
    company = models.CharField(max_length=255)
    asset = models.CharField(max_length=255, null=True)

    xiaoshoue = models.DecimalField(decimal_places=2, max_digits=19)
    lirune = models.DecimalField(decimal_places=2, max_digits=19)
    kuchun_liang = models.DecimalField(decimal_places=2, max_digits=19)
    zijin_zhanya = models.DecimalField(decimal_places=2, max_digits=19)


class CustomerStat(models.Model):
    category = models.CharField(max_length=255)  # month / total
    month = models.CharField(max_length=255, null=True)

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    yewuliang = models.DecimalField(decimal_places=2, max_digits=19)
    avg_price = models.DecimalField(max_digits=32, decimal_places=4)  # 平均结算价格


class Configuration(models.Model):
    key = models.CharField(unique=True, max_length=255)  # audits
    value = JSONField()


class AsyncTask(models.Model):
    finished = models.BooleanField(default=False)
    category = models.CharField(max_length=255)
    exec_at = models.DateTimeField()
    data = JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
