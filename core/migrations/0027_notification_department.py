# Generated by Django 2.0.1 on 2018-11-20 11:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_auto_20181115_0923'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='department',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='core.Department'),
        ),
    ]