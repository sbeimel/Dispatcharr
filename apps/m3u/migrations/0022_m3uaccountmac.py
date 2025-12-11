# Generated manually for M3UAccountMac model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0021_add_mac_support'),
    ]

    operations = [
        migrations.CreateModel(
            name='M3UAccountMac',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(help_text='MAC address in format AA:BB:CC:DD:EE:FF', max_length=17)),
                ('priority', models.PositiveIntegerField(default=0, help_text='Priority order for failover (0 = highest priority)')),
                ('status', models.CharField(
                    choices=[
                        ('unknown', 'Unknown'),
                        ('valid', 'Valid'),
                        ('expired', 'Expired'),
                        ('error', 'Error'),
                    ],
                    default='unknown',
                    help_text='Current validation status of this MAC address',
                    max_length=20,
                )),
                ('expires_at', models.DateTimeField(blank=True, help_text='When this MAC address expires (if known)', null=True)),
                ('expires_text', models.CharField(blank=True, help_text='Raw expiry text from portal for display', max_length=255, null=True)),
                ('last_checked', models.DateTimeField(blank=True, help_text='When this MAC was last validated', null=True)),
                ('last_error', models.TextField(blank=True, help_text='Last error message if validation failed', null=True)),
                ('account', models.ForeignKey(
                    help_text='The M3U account this MAC belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='macs',
                    to='m3u.m3uaccount',
                )),
            ],
            options={
                'verbose_name': 'MAC Address',
                'verbose_name_plural': 'MAC Addresses',
                'ordering': ['priority', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='m3uaccountmac',
            constraint=models.UniqueConstraint(fields=('account', 'address'), name='unique_account_mac'),
        ),
    ]