# Generated by Django 2.2.6 on 2019-10-05 06:44

import common.base_models
from decimal import Decimal
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FundAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('extra_info', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('amount', common.base_models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=65)),
                ('note', models.CharField(blank=True, max_length=128, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RenameField(
            model_name='fund',
            old_name='amount',
            new_name='cash',
        ),
        migrations.AddField(
            model_name='fund',
            name='currency',
            field=models.CharField(default='CNY', max_length=8),
        ),
        migrations.DeleteModel(
            name='FundTransfer',
        ),
        migrations.AddField(
            model_name='fundaction',
            name='from_fund',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transfer_as_from', to='wallet.Fund'),
        ),
        migrations.AddField(
            model_name='fundaction',
            name='to_fund',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transfer_as_to', to='wallet.Fund'),
        ),
    ]
