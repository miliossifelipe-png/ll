from django.contrib import admin
from .models import Channel

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'id_telegram', 'bot_token', 'criado_por', 'criado_em')
    search_fields = ('nome', 'id_telegram')
    list_filter = ('criado_por',)
    fields = ('nome', 'id_telegram', 'bot_token', 'criado_por', 'criado_em')
