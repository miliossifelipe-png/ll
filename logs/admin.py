from django.contrib import admin
from .models import Log

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'mensagem_texto', 'canal', 'usuario', 'criado_em')
    search_fields = ('mensagem_texto', 'detalhes')
    list_filter = ('tipo', 'canal', 'usuario')
