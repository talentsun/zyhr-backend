from django.urls import path

from core.views import upload
from core.views import session
from core.views import audit
from core.views import emps
from core.views import organization


urlpatterns = [
    path(r'upload', upload.upload),
    path(r'assets/<str:path>', upload.assets),


    # session api
    path(r'login', session.login),
    path(r'login-with-code', session.loginWithCode),
    path(r'send-code', session.sendCode),
    path(r'profile', session.profile),


    # audit api
    path(r'audit-configs', audit.configs),
    path(r'audit-activities', audit.activities),
    path(r'audit-activities/<uuid:activityId>', audit.activity),
    path(r'audit-activities/<str:activityId>/actions/cancel', audit.cancel),
    path(r'audit-steps/<uuid:stepId>/actions/approve', audit.approveStep),
    path(r'audit-steps/<uuid:stepId>/actions/reject', audit.rejectStep),

    path(r'mine-audit-activities', audit.mineActivities),
    path(r'assigned-audit-activities', audit.assignedActivities),
    path(r'processed-audit-activities', audit.processedActivities),


    # emps/deps/positions api
    path(r'emps', emps.index),
    path(r'emps/<uuid:empId>', emps.detail),
    path(r'emps/<uuid:empId>/actions/update-state', emps.updateState),
    path(r'emps/<uuid:empId>/actions/update-password', emps.updatePassword),
    path(r'departments', organization.departments),
    path(r'positions', organization.positions),
]
