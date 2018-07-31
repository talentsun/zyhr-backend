from django.urls import path

from core.views import upload
from core.views import session
from core.views import audit
from core.views import emps
from core.views import organization
from core.views import roles
from core.views import message
from core.views import customer

urlpatterns = [
    path(r'upload', upload.upload),
    path(r'assets/<str:path>', upload.assets),

    # session api
    path(r'login', session.login),
    path(r'login-with-code', session.loginWithCode),
    path(r'send-code', session.sendCode),
    path(r'change-phone', session.changePhone),
    path(r'profile', session.profile),

    # audit api
    path(r'audit-configs', audit.configs),
    path(r'audit-activities', audit.activities),
    path(r'audit-activities/<uuid:activityId>', audit.activity),
    path(r'audit-activities/<str:activityId>/actions/cancel', audit.cancel),
    path(r'audit-activities/<str:activityId>/actions/update-data', audit.updateData),
    path(r'audit-activities/<str:activityId>/actions/submit-audit', audit.submitAudit),
    path(r'audit-activities/<str:activityId>/actions/relaunch', audit.relaunch),
    path(r'audit-activities/<uuid:activityId>/actions/hurryup', audit.hurryup),

    path(r'audit-steps/<uuid:stepId>/actions/approve', audit.approveStep),
    path(r'audit-steps/<uuid:stepId>/actions/reject', audit.rejectStep),

    path(r'mine-audit-activities', audit.mineActivities),
    path(r'assigned-audit-activities', audit.assignedActivities),
    path(r'processed-audit-activities', audit.processedActivities),
    path(r'related-audit-activities', audit.relatedActivities),
    path(r'audit-tasks', audit.auditTasks),

    # message api
    path(r'messages/<uuid:messageId>/actions/mark-read', message.markRead),

    # emps/deps/positions api
    path(r'emps', emps.index),
    path(r'emps/<uuid:empId>', emps.detail),
    path(r'emps/<uuid:empId>/actions/update-state', emps.updateState),
    path(r'emps/<uuid:empId>/actions/update-password', emps.updatePassword),
    path(r'departments', organization.departments),
    path(r'positions', organization.positions),


    # customers api
    path(r'customers', customer.index),
    path(r'customers/<int:customerId>', customer.customer),
    path(r'customers/actions/import', customer.importCustomers),
    path(r'customers/actions/export', customer.exportCustomers),

    # roles api
    path(r'roles', roles.index),
    path(r'roles/<uuid:roleId>', roles.detail),
]
