from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('channels', '0001_initial'),
        ('scheduled_messages', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='usuario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user'),
        ),
        migrations.AddField(
            model_name='log',
            name='canal',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='channels.channel'),
        ),
        migrations.AddField(
            model_name='log',
            name='mensagem',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='scheduled_messages.scheduledmessage'),
        ),
        migrations.RenameField(
            model_name='log',
            old_name='mensagem',
            new_name='mensagem_texto',
        ),
    ] 