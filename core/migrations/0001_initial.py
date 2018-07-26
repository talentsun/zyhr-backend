# Generated by Django 2.0.1 on 2018-07-26 15:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditActivity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('sn', models.CharField(max_length=255)),
                ('state', models.CharField(choices=[('draft', 'draft'), ('processing', 'processing'), ('approved', 'approved'), ('rejected', 'rejected'), ('rejected', 'cancelled')], default='draft', max_length=20)),
                ('extra', jsonfield.fields.JSONField()),
                ('finished_at', models.DateTimeField(null=True)),
                ('archived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AuditActivityConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('category', models.CharField(max_length=255)),
                ('subtype', models.CharField(max_length=255, unique=True)),
                ('hasTask', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='AuditActivityConfigStep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('position', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='AuditStep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('active', models.BooleanField(default=False)),
                ('state', models.CharField(choices=[('pending', 'pending'), ('approved', 'approved'), ('rejected', 'rejected')], default='pending', max_length=20)),
                ('position', models.IntegerField()),
                ('desc', models.TextField(null=True)),
                ('activated_at', models.DateTimeField(null=True)),
                ('finished_at', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AuditActivity')),
            ],
        ),
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('number', models.CharField(max_length=255)),
                ('bank', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Department')),
            ],
        ),
        migrations.CreateModel(
            name='DepPos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dep', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Department')),
            ],
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('path', models.CharField(max_length=255)),
                ('size', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('read', models.BooleanField(default=False)),
                ('category', models.CharField(max_length=255)),
                ('extra', jsonfield.fields.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('activity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.AuditActivity')),
            ],
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('email', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=255, unique=True)),
                ('blocked', models.BooleanField(default=False)),
                ('desc', models.TextField(default='', null=True)),
                ('archived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Department')),
                ('position', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Position')),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('desc', models.CharField(max_length=255, null=True)),
                ('version', models.CharField(default='v1', max_length=10)),
                ('archived', models.BooleanField(default=False)),
                ('extra', jsonfield.fields.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Role'),
        ),
        migrations.AddField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='message',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='deppos',
            name='pos',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Position'),
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='auditstep',
            name='assignee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='auditstep',
            name='assigneeDepartment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Department'),
        ),
        migrations.AddField(
            model_name='auditstep',
            name='assigneePosition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Position'),
        ),
        migrations.AddField(
            model_name='auditactivityconfigstep',
            name='assigneeDepartment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Department'),
        ),
        migrations.AddField(
            model_name='auditactivityconfigstep',
            name='assigneePosition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Position'),
        ),
        migrations.AddField(
            model_name='auditactivityconfigstep',
            name='config',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AuditActivityConfig'),
        ),
        migrations.AddField(
            model_name='auditactivity',
            name='config',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.AuditActivityConfig'),
        ),
        migrations.AddField(
            model_name='auditactivity',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
    ]
