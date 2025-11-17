from django.contrib import admin
from .models import ScheduledMessage, MessageBlock, ScheduledMessageOccurrence

class MessageBlockInline(admin.TabularInline):
    model = MessageBlock
    extra = 0
    fields = ('tipo', 'conteudo', 'arquivo', 'ordem')
    ordering = ('ordem',)

@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'canal', 'tipo', 'status_display', 'agendado_para', 'enviado_em')
    inlines = [MessageBlockInline]
    search_fields = ('titulo',)
    list_filter = ('canal', 'tipo', 'agendado_para')

    def status_display(self, obj):
        if hasattr(obj, 'tipo') and obj.tipo == 'recorrente':
            return 'Recorrente'
        if obj.enviado_em:
            return 'Enviada'
        return 'Pendente'
    status_display.short_description = 'Status'

@admin.register(MessageBlock)
class MessageBlockAdmin(admin.ModelAdmin):
    list_display = ('mensagem', 'tipo', 'ordem')
    list_filter = ('tipo',)

@admin.register(ScheduledMessageOccurrence)
class ScheduledMessageOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('mensagem', 'data', 'horario', 'enviado_em')
    list_filter = ('data', 'mensagem__canal')
    search_fields = ('mensagem__titulo',)
