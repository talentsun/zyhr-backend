# Generated by Django 2.0.1 on 2019-05-04 14:41

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_revert_audit_flow_transfer_20190510_0303'),
    ]

    operations = [
        migrations.CreateModel(
            name='AsyncTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('finished', models.BooleanField(default=False)),
                ('category', models.CharField(max_length=255)),
                ('exec_at', models.DateTimeField()),
                ('data', jsonfield.fields.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=255, unique=True)),
                ('value', jsonfield.fields.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='FinCustomer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('org', models.CharField(max_length=255)),
                ('layer', models.CharField(max_length=255)),
                ('owner', models.CharField(max_length=255)),
                ('interface', models.CharField(max_length=255)),
                ('interfacePosition', models.CharField(max_length=255)),
                ('interfacePhone', models.CharField(max_length=255)),
                ('meetTime', models.DateTimeField()),
                ('meetPlace', models.CharField(max_length=255)),
                ('member', models.CharField(max_length=255, null=True)),
                ('otherMember', models.CharField(max_length=255, null=True)),
                ('otherMemberPosition', models.CharField(max_length=255, null=True)),
                ('desc', models.TextField(null=True)),
                ('next', models.TextField(null=True)),
                ('note', models.TextField(null=True)),
                ('archived', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='FinCustomerOps',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('op', models.CharField(max_length=50)),
                ('prop', models.CharField(max_length=50, null=True)),
                ('extra', jsonfield.fields.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='NotDep',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('category', models.CharField(max_length=50)),
                ('for_all', models.BooleanField(default=True)),
                ('stick', models.BooleanField(default=False)),
                ('stick_duration', models.CharField(max_length=255, null=True)),
                ('attachments', jsonfield.fields.JSONField(null=True)),
                ('extra', jsonfield.fields.JSONField(null=True)),
                ('scope', jsonfield.fields.JSONField(null=True)),
                ('views', models.IntegerField(default=0)),
                ('archived', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='NotificationViews',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('times', models.IntegerField(default=0)),
                ('notification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Notification')),
            ],
        ),
        migrations.CreateModel(
            name='ProfileInfo',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('avatar', models.CharField(max_length=255, null=True)),
                ('state', models.CharField(choices=[('testing', 'testing'), ('normal', 'normal'), ('left', 'left')], default='testing', max_length=20)),
                ('realname', models.CharField(max_length=255, null=True)),
                ('archived', models.BooleanField(default=False)),
                ('gender', models.IntegerField(default=0)),
                ('id_number', models.CharField(max_length=255, null=True)),
                ('birthday', models.CharField(max_length=255, null=True)),
                ('nation', models.CharField(max_length=255, null=True)),
                ('hunyin', models.CharField(max_length=255, null=True)),
                ('height', models.CharField(max_length=255, null=True)),
                ('weight', models.CharField(max_length=255, null=True)),
                ('blood', models.CharField(max_length=255, null=True)),
                ('zhengzhimianmao', models.CharField(max_length=255, null=True)),
                ('rudang_date', models.CharField(max_length=255, null=True)),
                ('jiguan', models.CharField(max_length=255, null=True)),
                ('hukou_location', models.CharField(max_length=255, null=True)),
                ('education', models.CharField(max_length=255, null=True)),
                ('school', models.CharField(max_length=255, null=True)),
                ('spec', models.CharField(max_length=255, null=True)),
                ('graduation_date', models.CharField(max_length=255, null=True)),
                ('language', models.CharField(max_length=255, null=True)),
                ('driving', models.CharField(max_length=255, null=True)),
                ('education_desc', models.TextField(null=True)),
                ('skill_certs', models.TextField(null=True)),
                ('work_category', models.CharField(max_length=255, null=True)),
                ('join_at', models.DateTimeField(null=True)),
                ('join_at_contract', models.DateTimeField(null=True)),
                ('positive_at', models.DateTimeField(null=True)),
                ('positive_at_contract', models.DateTimeField(null=True)),
                ('positive_desc', models.CharField(max_length=255, null=True)),
                ('contract_due', models.CharField(max_length=255, null=True)),
                ('leave_at', models.CharField(max_length=255, null=True)),
                ('leave_reason', models.CharField(max_length=255, null=True)),
                ('work_desc', models.CharField(max_length=255, null=True)),
                ('work_transfer_desc', models.TextField(null=True)),
                ('contact_address', models.CharField(max_length=255, null=True)),
                ('contact_name', models.CharField(max_length=255, null=True)),
                ('contact_relation', models.CharField(max_length=255, null=True)),
                ('contact_phone', models.CharField(max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='auditactivity',
            name='config_data',
            field=jsonfield.fields.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='abnormal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='conditions',
            field=jsonfield.fields.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='fallback',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='priority',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='auditactivityconfig',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='auditactivityconfigstep',
            name='abnormal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='auditstep',
            name='abnormal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='auditstep',
            name='extra',
            field=jsonfield.fields.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='customerstat',
            name='avg_price',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customerstat',
            name='dunwei',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=19),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='department',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='position',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='auditactivity',
            name='state',
            field=models.CharField(choices=[('draft', 'draft'), ('processing', 'processing'), ('approved', 'approved'), ('rejected', 'rejected'), ('rejected', 'cancelled'), ('aborted', 'aborted')], default='draft', max_length=20),
        ),
        migrations.AlterField(
            model_name='auditactivityconfig',
            name='category',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='auditactivityconfig',
            name='subtype',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='auditactivityconfigstep',
            name='assigneePosition',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Position'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='capital',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='customerstat',
            name='yewuliang',
            field=models.DecimalField(decimal_places=2, default='0.00', max_digits=19),
        ),
        migrations.AlterField(
            model_name='department',
            name='code',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='code',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='email',
            field=models.CharField(default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='profileinfo',
            name='profile',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='notificationviews',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='notification',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='notification',
            name='department',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Department'),
        ),
        migrations.AddField(
            model_name='notdep',
            name='department',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Department'),
        ),
        migrations.AddField(
            model_name='notdep',
            name='notification',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Notification'),
        ),
        migrations.AddField(
            model_name='fincustomerops',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AddField(
            model_name='fincustomerops',
            name='record',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.FinCustomer'),
        ),
        migrations.AddField(
            model_name='fincustomer',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
    ]