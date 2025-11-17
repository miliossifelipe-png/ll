from django.db import models
from scheduled_messages.models import ScheduledMessage

class Schedule(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviado', 'Enviado'),
        ('falha', 'Falha'),
    ]
    mensagem = models.ForeignKey(ScheduledMessage, on_delete=models.CASCADE, related_name='agendamentos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    proxima_tentativa = models.DateTimeField()
    tentativas = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.mensagem} - {self.status}"
