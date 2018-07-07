from django.urls import path

from core.views import upload
from core.views import session
from core.views import audit

urlpatterns = [
    path(r'upload', upload.upload),

    path(r'login', session.login),
    path(r'login-with-code', session.loginWithCode),
    path(r'send-code', session.sendCode),
    path(r'profile', session.profile),

    path(r'audit-activities', audit.activities),
    path(r'audit-activities/<uuid:activityId>', audit.activity),
    path(r'audit-activities/<str:activityId>/actions/cancel', audit.cancel),
    path(r'audit-steps/<uuid:stepId>/actions/approve', audit.approveStep),
    path(r'audit-steps/<uuid:stepId>/actions/reject', audit.rejectStep),
]
