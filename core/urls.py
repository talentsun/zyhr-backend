from django.urls import path

from core.views import upload
from core.views import session
from core.views import audit
from core.views import auditCategory
from core.views import auditExport
from core.views import emps
from core.views import organization
from core.views import roles
from core.views import message
from core.views import customer
from core.views import finCustomer
from core.views import finAccount
from core.views import stats
from core.views import taizhang
from core.views import charts
from core.views import profile
from core.views import notification
from core.views import dev

urlpatterns = [
    path(r'upload', upload.upload),
    path(r'assets/<str:path>', upload.assets),

    # session api
    path(r'login', session.login),
    path(r'login-with-code', session.loginWithCode),
    path(r'send-code', session.sendCode),
    path(r'change-phone', session.changePhone),
    path(r'profile', session.profile),
    path(r'bind-device-id', session.bindDeviceId),
    path(r'unbind-device-id', session.unbindDeviceId),

    # audit-categories api
    path(r'audit-categories', auditCategory.categories),
    path(r'audit-categories/<str:subtype>', auditCategory.category),
    path(r'audit-categories/<str:subtype>/actions/disable', auditCategory.disableAudit),
    path(r'audit-categories/<str:subtype>/actions/enable', auditCategory.enableAudit),
    path(r'audit-categories/<str:subtype>/actions/move', auditCategory.moveAudit),
    path(r'audit-categories/<str:subtype>/actions/update-flow', auditCategory.updateAuditFlow),
    path(r'audit-categories/<str:subtype>/actions/create-flow', auditCategory.createAuditFlow),
    path(r'audit-categories/<str:subtype>/actions/stick-flow', auditCategory.stickAuditFlow),
    path(r'audit-categories/<str:subtype>/actions/delete-flow', auditCategory.deleteAuditFlow),
    path(r'audit-categories/<str:subtype>/actions/get-flow', auditCategory.getAuditFlow),
    path(r'audit-categories/<str:subtype>/actions/update-fallback-flow', auditCategory.updateFallbackAuditFlow),

    # audit api
    path(r'audit-activities', audit.activities),
    path(r'audit-activities/<uuid:activityId>', audit.activity),
    path(r'audit-activities/<str:activityId>/actions/cancel', audit.cancel),
    path(r'export-audit', auditExport.batchExport),
    path(r'audit-activities/<str:activityId>/actions/export', auditExport.export),
    path(r'audit-activities/<str:activityId>/actions/update-data', audit.updateData),
    path(r'audit-activities/<str:activityId>/actions/submit-audit', audit.submitAudit),
    path(r'audit-activities/<str:activityId>/actions/relaunch', audit.relaunch),
    path(r'audit-activities/<uuid:activityId>/actions/hurryup', audit.hurryup),
    path(r'audit-activities/<uuid:activityId>/actions/mark-task-finished', audit.markTaskFinished),
    path(r'audit-activities/<uuid:activityId>/actions/mark-task-obsolete', audit.markTaskObsolete),

    path(r'audit-steps/<uuid:stepId>/actions/approve', audit.approveStep),
    path(r'audit-steps/<uuid:stepId>/actions/reject', audit.rejectStep),

    path(r'mine-audit-activities', audit.mineActivities),
    path(r'assigned-audit-activities', audit.assignedActivities),
    path(r'processed-audit-activities', audit.processedActivities),
    path(r'related-audit-activities', audit.relatedActivities),
    path(r'audit-tasks', audit.auditTasks),

    # message api
    path(r'messages/<uuid:messageId>/actions/mark-read', message.markRead),

    # emps api
    path(r'emps', emps.index),
    path(r'emps/<uuid:empId>', emps.detail),
    path(r'emps/<uuid:empId>/actions/update-state', emps.updateState),
    path(r'emps/<uuid:empId>/actions/update-password', emps.updatePassword),

    # org/profile api
    path(r'departments', organization.departments),
    path(r'departments/<uuid:dep>', organization.department),
    path(r'positions', organization.positions),
    path(r'positions/<uuid:pos>', organization.position),
    path(r'profiles', profile.profiles),
    path(r'profiles/<uuid:profileId>', profile.profile),
    path(r'profiles/actions/export', profile.export),

    # customers api
    path(r'customers', customer.index),
    path(r'customer-stats', customer.stats),
    path(r'customers/<int:customerId>', customer.customer),
    path(r'customers/actions/import', customer.importCustomers),
    path(r'customers/actions/export', customer.exportCustomers),

    # fin customers api
    path(r'fin-customers', finCustomer.index),
    path(r'fin-customers/actions/import', finCustomer.importCustomers),
    path(r'fin-customers/actions/delete', finCustomer.deleteCustomers),
    path(r'fin-customers/actions/export', finCustomer.exportCustomers),
    path(r'fin-customers/<int:customerId>', finCustomer.customer),

    # finAccount api
    path(r'fin-accounts', finAccount.index),
    path(r'fin-accounts/<int:accountId>', finAccount.account),
    path(r'fin-accounts/actions/import', finAccount.importAccounts),
    path(r'fin-accounts/actions/export', finAccount.exportAccounts),

    # transactionRecord api
    path(r'transaction-records', stats.transactionRecords),
    path(r'transaction-records/<int:recordId>', stats.transactionRecord),
    path(r'transaction-records/actions/import', stats.importTransactionRecords),
    path(r'transaction-records/actions/export', stats.exportRecords),
    path(r'transaction-record-ops', stats.ops),
    path(r'transaction-record-stats', stats.stats),

    # taizhang api
    path(r'taizhang', taizhang.taizhang),
    path(r'taizhang/<int:id>', taizhang.taizhangDetail),
    path(r'taizhang-ops', taizhang.ops),
    path(r'taizhang-stats', taizhang.stats),
    path(r'taizhang/actions/export', taizhang.exportRecords),

    # charts api
    path(r'charts/taizhang/line', charts.taizhang_line),
    path(r'charts/taizhang/bar', charts.taizhang_bar),
    path(r'charts/taizhang/pie', charts.taizhang_pie),
    path(r'charts/taizhang/companies', charts.taizhang_companies),
    path(r'charts/funds/line', charts.funds_line),
    path(r'charts/funds/bar', charts.funds_bar),
    path(r'charts/customers/line', charts.customers_line),
    path(r'charts/customers/bar', charts.customers_bar),
    path(r'charts/app/home', charts.app_home),
    path(r'charts/app/taizhang', charts.app_taizhang),
    path(r'charts/app/funds', charts.app_funds),
    path(r'charts/app/customers', charts.app_customers),
    path(r'charts/home/taizhang', charts.home_taizhang),
    path(r'charts/home/funds', charts.home_funds),
    path(r'charts/home/customer', charts.home_customer),

    # roles api
    path(r'roles', roles.index),
    path(r'roles/<uuid:roleId>', roles.detail),

    # notifications api
    path(r'notifications', notification.notifications),
    path(r'view_notifications', notification.view_notifications),
    path(r'notifications/<int:id>', notification.notification),

    # stats task trigger api
    path(r'dev/trigger-stats', dev.trigger_stats)
]
