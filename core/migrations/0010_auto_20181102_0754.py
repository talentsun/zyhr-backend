# Generated by Django 2.0.1 on 2018-11-02 07:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auditactivity_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditactivity',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=32, null=True),
        ),
    ]
