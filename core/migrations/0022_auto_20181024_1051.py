# Generated by Django 2.0.1 on 2018-10-24 10:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_asynctask'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='capital',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
