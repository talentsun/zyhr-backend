# Generated by Django 2.0.1 on 2018-09-20 07:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20180821_0252'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bankaccount',
            name='profile',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
        migrations.AlterField(
            model_name='company',
            name='profile',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Profile'),
        ),
    ]
