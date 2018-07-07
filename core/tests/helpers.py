from django.contrib.auth.models import User

from core.models import *


def prepareProfile(name, password, phone):
    user = User.objects.create(username=name)
    user.set_password(password)
    user.save()
    profile = Profile.objects.create(user=user,
                                     name=name,
                                     phone=phone)
    return profile
