from django.db import models
from django.contrib.auth import get_user_model
from scheduled_messages.utils import verificar_conexao_telegram

User = get_user_model()

class Channel(models.Model):
    nome = models.CharField(max_length=100)
    id_telegram = models.CharField(max_length=64, unique=True)
    bot_token = models.CharField(max_length=100, help_text='Token do Bot do Telegram para este canal', null=True, blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='channels')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

    def get_status_conexao(self):
        if not self.bot_token:
            return False, 'Sem token'
        ok, erro = verificar_conexao_telegram(self.bot_token)
        if ok:
            return True, 'OK'
        return False, erro or 'Falha'
