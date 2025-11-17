from django import forms
from .models import ScheduledMessage
from django.utils import timezone
import datetime

class ScheduledMessageForm(forms.ModelForm):
    caption = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Legenda para anexar junto ao arquivo (opcional)',
            'rows': 2
        })
    )
    agendado_para = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'})
    )
    horario = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    dias_semana = forms.MultipleChoiceField(
        required=False,
        choices=[('mon', 'Segunda'), ('tue', 'Terça'), ('wed', 'Quarta'), ('thu', 'Quinta'), ('fri', 'Sexta'), ('sat', 'Sábado'), ('sun', 'Domingo')],
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = ScheduledMessage
        fields = ['canal', 'titulo', 'tipo', 'agendado_para', 'dias_semana', 'horario', 'data_inicio', 'data_fim', 'caption']

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        if tipo == 'recorrente':
            if not cleaned_data.get('data_inicio'):
                cleaned_data['data_inicio'] = timezone.now().date()
            if not cleaned_data.get('data_fim') or cleaned_data['data_fim'] < cleaned_data['data_inicio']:
                cleaned_data['data_fim'] = cleaned_data['data_inicio'] + datetime.timedelta(days=365)
        return cleaned_data 