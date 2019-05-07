# Generated by Django 2.0.1 on 2019-05-04 16:49

from django.db import migrations
from core.models import *


def addProfileInfo(apps, schema_editor):
    profiles = Profile.objects.all()
    for profile in profiles:
        pi = ProfileInfo(profile=profile, realname=profile.name)

        if profile.archived or profile.blocked:
            pi.state = ProfileInfo.StateLeft

        pi.save()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0023_auto_20190504_1602'),
    ]

    operations = [
        migrations.RunPython(addProfileInfo),
    ]