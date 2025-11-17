from django import forms
from .models import Channel
 
class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ['nome', 'id_telegram', 'bot_token']
        error_messages = {
            'nome': {
                'required': 'O nome do canal é obrigatório.',
                'max_length': 'O nome do canal deve ter no máximo 100 caracteres.'
            },
            'id_telegram': {
                'required': 'O ID do Telegram é obrigatório.',
                'unique': 'Já existe um canal com este ID do Telegram.',
                'max_length': 'O ID do Telegram deve ter no máximo 64 caracteres.'
            },
            'bot_token': {
                'max_length': 'O token do bot deve ter no máximo 100 caracteres.'
            }
        } 