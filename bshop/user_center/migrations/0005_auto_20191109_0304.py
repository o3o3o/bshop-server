# Generated by Django 2.2.6 on 2019-11-09 03:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_center', '0004_auto_20191024_0351'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='shopuser',
            options={'verbose_name': 'Shop user', 'verbose_name_plural': 'Shop users'},
        ),
        migrations.AlterField(
            model_name='shopuser',
            name='avatar_url',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='Avatar URL'),
        ),
        migrations.AlterField(
            model_name='shopuser',
            name='nickname',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name='Nickname'),
        ),
        migrations.AlterField(
            model_name='shopuser',
            name='phone',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Phone'),
        ),
        migrations.AlterField(
            model_name='shopuser',
            name='wechat_id',
            field=models.CharField(blank=True, max_length=512, null=True, unique=True, verbose_name='Wechat ID'),
        ),
    ]
