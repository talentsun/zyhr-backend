# Generated by Django 2.0.1 on 2018-08-27 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20180821_0252'),
    ]

    operations = [
        migrations.AddField(
            model_name='taizhang',
            name='avg_price',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=32),
            preserve_default=False,
        ),
    ]
