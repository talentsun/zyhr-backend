import uuid
from django.db import models
from django.contrib.auth.models import User

from jsonfield import JSONField

'''
v1 版本中一些 model 的定义, 只有少数 v1 组件可以使用,其他地方不允许引用这些 model
'''

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


class DepartmentLegacy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50, null=True)
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_department'
        managed = False


class PositionLegacy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.CharField(max_length=50, null=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'core_position'
        managed = False


class DepPosLegacy(models.Model):
    dep = models.ForeignKey(DepartmentLegacy, on_delete=models.CASCADE)
    pos = models.ForeignKey(PositionLegacy, on_delete=models.CASCADE)

    class Meta:
        db_table = 'core_deppos'
        managed = False


class RoleLegacy(models.Model):
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
        return ProfileLegacy.objects.filter(role=self).count()

    class Meta:
        db_table = 'core_role'
        managed = False


class ProfileLegacy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=255, unique=True, null=True)
    department = models.ForeignKey(DepartmentLegacy,
                                   on_delete=models.CASCADE,
                                   null=True)
    position = models.ForeignKey(PositionLegacy, on_delete=models.CASCADE, null=True)
    blocked = models.BooleanField(default=False)
    desc = models.TextField(default='', null=True)
    archived = models.BooleanField(default=False)
    role = models.ForeignKey(RoleLegacy, null=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    deviceId = models.CharField(max_length=255, null=True)

    @property
    def owner(self):
        if self.department is None:
            return None

        return ProfileLegacy.objects \
            .filter(department=self.department,
                    position__code='owner',
                    archived=False) \
            .first()

    class Meta:
        db_table = 'core_profile'
        managed = False


class AuditActivityConfigLegacy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    category = models.CharField(max_length=255)
    subtype = models.CharField(max_length=255, unique=True)
    hasTask = models.BooleanField(default=False)

    class Meta:
        db_table = 'core_auditactivityconfig'
        managed = False


class AuditActivityConfigStepLegacy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    config = models.ForeignKey(AuditActivityConfigLegacy, on_delete=models.CASCADE)
    assigneeDepartment = models.ForeignKey(DepartmentLegacy,
                                           null=True,
                                           on_delete=models.CASCADE)
    assigneePosition = models.ForeignKey(PositionLegacy,
                                         on_delete=models.CASCADE)
    position = models.IntegerField()

    class Meta:
        db_table = 'core_auditactivityconfigstep'
        managed = False
