import uuid

from django.contrib.auth.models import User
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


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=255, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True)
    blocked = models.BooleanField(default=False)
    desc = models.TextField(default='', null=True)
    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# TODO: 支持待处理任务的生成
class AuditActivityConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    category = models.CharField(max_length=255)
    subtype = models.CharField(max_length=255, unique=True)


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
    StateProcessing = 'processing'
    StateApproved = 'approved'
    StateRejected = 'rejected'
    StateCancelled = 'cancelled'
    StateChoices = (
        (StateProcessing, StateProcessing),
        (StateApproved, StateApproved),
        (StateRejected, StateRejected),
        (StateRejected, StateCancelled),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    config = models.ForeignKey(AuditActivityConfig, on_delete=models.CASCADE)
    creator = models.ForeignKey(Profile, on_delete=models.CASCADE)
    state = models.CharField(
        max_length=20, choices=StateChoices, default=StateProcessing)
    extra = JSONField()  # 审批相关数据，不同类型的审批，相关数据不一样，暂时使用 json 保存

    finished_at = models.DateTimeField(null=True)
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

        return AuditStep.objects\
            .filter(activity=self,
                    active=True)\
            .first()

    def steps(self):
        return AuditStep.objects \
            .filter(activity=self) \
            .order_by('position')


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
