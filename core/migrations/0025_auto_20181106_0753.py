# Generated by Django 2.0.1 on 2018-11-06 07:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_auditactivity_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerstat',
            name='dunwei',
            field=models.DecimalField(decimal_places=4, default='0.00', max_digits=19),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='customerstat',
            name='yewuliang',
            field=models.DecimalField(decimal_places=2, default='0.00', max_digits=19),
        ),
    ]