# Generated by Django 2.2.7 on 2020-01-31 02:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_hostkeys_keys_sshkeys'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationpreferences',
            name='announcements',
            field=models.BooleanField(default=True, verbose_name='Receive occasional announcements from Frontera'),
        ),
    ]