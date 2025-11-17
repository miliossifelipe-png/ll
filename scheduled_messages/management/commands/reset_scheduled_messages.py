from django.core.management.base import BaseCommand
from django.utils import timezone
from scheduled_messages.models import ScheduledMessage, ScheduledMessageOccurrence
import datetime

class Command(BaseCommand):
    help = 'Padroniza datas para UTC, reseta status de envio de mensagens únicas e limpa ocorrências de recorrentes (opcional).'

    def add_arguments(self, parser):
        parser.add_argument('--limpar-ocorrencias', action='store_true', help='Limpa todas as ocorrências de mensagens recorrentes.')

    def handle(self, *args, **options):
        count_unicas = 0
        count_datas = 0
        # Padronizar agendado_para para UTC e resetar status de envio de únicas
        for m in ScheduledMessage.objects.filter(agendado_para__isnull=False):
            original = m.agendado_para
            if timezone.is_naive(m.agendado_para):
                m.agendado_para = timezone.make_aware(m.agendado_para, timezone.get_current_timezone())
            m.agendado_para = m.agendado_para.astimezone(datetime.timezone.utc)
            if m.tipo == 'unico':
                m.enviado = False
                m.enviado_em = None
            m.save()
            count_unicas += 1
            self.stdout.write(f"Mensagem {m.id} ajustada: {original} -> {m.agendado_para} (UTC)")
        # Padronizar datas de recorrentes (data_inicio, data_fim não precisam de timezone, mas horario pode ser naive)
        for m in ScheduledMessage.objects.filter(tipo='recorrente'):
            # Nenhuma ação para data_inicio/data_fim (são DateField)
            if m.horario and isinstance(m.horario, datetime.time):
                # Não há timezone em TimeField, mas pode ajustar se necessário
                pass
            count_datas += 1
        # Limpar ocorrências se solicitado
        if options['limpar_ocorrencias']:
            ScheduledMessageOccurrence.objects.all().delete()
            self.stdout.write(self.style.WARNING('Todas as ocorrências de mensagens recorrentes foram removidas!'))
        self.stdout.write(self.style.SUCCESS(f'Ajustadas {count_unicas} mensagens únicas e {count_datas} recorrentes.')) 