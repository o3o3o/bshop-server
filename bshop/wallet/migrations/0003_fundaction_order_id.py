# Generated by Django 2.2.6 on 2019-10-18 02:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0002_auto_20191005_0644'),
    ]

    operations = [
        migrations.AddField(
            model_name='fundaction',
            name='order_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]