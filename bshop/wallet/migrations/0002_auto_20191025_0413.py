# Generated by Django 2.2.6 on 2019-10-25 04:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundtransfer',
            name='order_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='fundtransfer',
            unique_together={('type', 'order_id')},
        ),
    ]