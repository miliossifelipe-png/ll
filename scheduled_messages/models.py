from django.db import models
from ckeditor.fields import RichTextField
from channels.models import Channel
from multiselectfield import MultiSelectField
from django.utils import timezone
import os
import uuid
from django.contrib.auth import get_user_model
User = get_user_model()

def unique_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'{uuid.uuid4().hex}{ext}'

def user_directory_path(instance, filename):
    # Exemplo: user_<id>/<uuid>_<filename>
    user_id = getattr(getattr(instance, 'mensagem', None), 'criado_por_id', 'anon')
    ext = filename.split('.')[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    return f'user_{user_id}/{unique_name}'

# Create your models here.

TIPO_CHOICES = [
    ('unico', 'Único'),
    ('recorrente', 'Recorrente'),
]

DIAS_SEMANA = [
    ('mon', 'Segunda'),
    ('tue', 'Terça'),
    ('wed', 'Quarta'),
    ('thu', 'Quinta'),
    ('fri', 'Sexta'),
    ('sat', 'Sábado'),
    ('sun', 'Domingo'),
]

class ScheduledMessage(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=False, editable=False, null=True, blank=True)
    canal = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='mensagens')
    titulo = models.CharField(max_length=200, blank=True, null=True)
    texto = RichTextField(blank=True)
    arquivo = models.FileField(upload_to='mensagens/', blank=True, null=True)
    caption = models.CharField(max_length=1024, blank=True, null=True, help_text='Legenda para anexar junto ao arquivo (opcional)')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='unico')
    agendado_para = models.DateTimeField(blank=True, null=True)  # Para único
    dias_semana = MultiSelectField(choices=DIAS_SEMANA, blank=True, null=True)  # Para recorrente
    horario = models.TimeField(blank=True, null=True)  # Para recorrente
    data_inicio = models.DateField(blank=True, null=True)  # Para recorrente
    data_fim = models.DateField(blank=True, null=True)  # Para recorrente
    enviado_em = models.DateTimeField(blank=True, null=True)
    enviado = models.BooleanField(default=False)  # Novo campo para status de envio
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensagens_agendadas')

    def __str__(self):
        if self.titulo:
            return f"{self.titulo} ({self.canal})" + (f" - {self.agendado_para:%d/%m/%Y %H:%M}" if self.agendado_para else "")
        return f"Mensagem {self.id} ({self.canal})"

class MessageBlock(models.Model):
    TIPO_BLOCO = [
        ('texto', 'Texto'),
        ('emoji', 'Emoji'),
        ('arquivo', 'Arquivo'),
        ('audio', 'Áudio'),
        ('imagem', 'Imagem'),
        ('inline_keyboard', 'Teclado de Botões (Inline Keyboard)'),  # Novo tipo para botões de URL
    ]
    mensagem = models.ForeignKey(ScheduledMessage, on_delete=models.CASCADE, related_name='blocos')
    tipo = models.CharField(max_length=20, choices=TIPO_BLOCO)
    conteudo = models.TextField(blank=True, null=True)  # Para texto, emoji, ou JSON de botões para inline_keyboard
    arquivo = models.FileField(upload_to='blocos/', blank=True, null=True)  # Para arquivo, áudio, imagem
    arquivo_nome_original = models.CharField(max_length=255, blank=True, null=True)  # Nome original do arquivo enviado
    caption = models.CharField(max_length=1024, blank=True, null=True, help_text='Legenda para este arquivo (opcional)')
    ordem = models.PositiveIntegerField(default=0)
    uid = models.CharField(max_length=36, blank=True, null=True, db_index=True)  # UUID v4

    class Meta:
        ordering = ['ordem']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.conteudo or self.arquivo}"

class ScheduledMessageOccurrence(models.Model):
    mensagem = models.ForeignKey(ScheduledMessage, on_delete=models.CASCADE, related_name='ocorrencias')
    data = models.DateField()
    horario = models.TimeField()
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('mensagem', 'data', 'horario')
        verbose_name = 'Ocorrência de Mensagem Recorrente'
        verbose_name_plural = 'Ocorrências de Mensagens Recorrentes'

    def __str__(self):
        return f"{self.mensagem} - {self.data} {self.horario}"

class DraftMessage(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rascunhos')
    dados = models.JSONField()
    status = models.CharField(max_length=20, default='rascunho', choices=[('rascunho', 'Rascunho'), ('ativo', 'Ativo'), ('descartado', 'Descartado')])
    atualizado_em = models.DateTimeField(auto_now=True)
