from django.db import models

# Create your models here.

class Log(models.Model):
    TIPO_CHOICES = [
        ('erro', 'Erro'),
        ('info', 'Info'),
        ('warning', 'Warning'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    # Campos extras para rastreabilidade
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    canal = models.ForeignKey('channels.Channel', on_delete=models.SET_NULL, null=True, blank=True)
    mensagem = models.ForeignKey('scheduled_messages.ScheduledMessage', on_delete=models.SET_NULL, null=True, blank=True)
    mensagem_texto = models.CharField(max_length=255)
    detalhes = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo.upper()}: {self.mensagem_texto[:50]}"
