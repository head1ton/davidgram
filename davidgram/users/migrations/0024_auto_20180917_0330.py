# Generated by Django 2.0.4 on 2018-09-17 03:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_auto_20180917_0313'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='gender',
            field=models.CharField(choices=[('female', 'Female'), ('not-specified', 'Not specified'), ('male', 'Male')], max_length=80, null=True),
        ),
    ]
