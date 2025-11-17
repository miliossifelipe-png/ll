from django.core.management.base import BaseCommand
from django.utils import timezone
from scheduled_messages.models import ScheduledMessage, ScheduledMessageOccurrence
from scheduled_messages.utils import enviar_mensagem_completo
import time
from logs.models import Log
import datetime
from django.db.models import Q, F
import pytz

class Command(BaseCommand):
    help = 'Processa e envia mensagens agendadas para o Telegram em loop contínuo'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=5, help='Intervalo em segundos entre verificações')
        parser.add_argument('--tolerancia', type=int, default=2, help='Tolerância em minutos para envio de recorrentes')

    def handle(self, *args, **options):
        interval = options['interval']
        tolerancia = options['tolerancia']
        self.stdout.write(self.style.WARNING(f'Iniciando worker de mensagens agendadas (intervalo: {interval}s, tolerância: {tolerancia}min)...'))
        try:
            while True:
                now = timezone.now().astimezone(pytz.UTC)
                # Mensagens únicas
                tolerancia_delta = datetime.timedelta(minutes=tolerancia)
                mensagens_unicas = ScheduledMessage.objects.filter(
                    enviado_em__isnull=True,
                    tipo='unico',
                    agendado_para__lte=now,
                    agendado_para__gte=now - tolerancia_delta
                ).order_by('agendado_para')

                # if mensagens_unicas:
                    # self.stdout.write(f"Encontradas {mensagens_unicas.count()} mensagens únicas para envio ({now})")

                threads = []
                for mensagem in mensagens_unicas:
                    # Envio centralizado
                    sucesso, info = enviar_mensagem_completo(mensagem, tipo_envio='agendado', usuario=mensagem.criado_por, tolerancia=tolerancia)
                    if sucesso:
                        print(f"[UNICA] Mensagem {mensagem.id} enviada com sucesso.")
                    # else:
                    #     print(f"[UNICA] Falha ao enviar mensagem {mensagem.id}: {info}")

                # Mensagens recorrentes previstas (ainda não enviadas hoje para o horário)
                mensagens_recorrentes_previstas = ScheduledMessage.objects.filter(
                    tipo='recorrente',
                    data_inicio__lte=now.date(),
                ).exclude(data_fim__lt=now.date()).exclude(
                    Q(horario__isnull=True) |
                    Q(id__in=ScheduledMessageOccurrence.objects.filter(
                        data=now.date(),
                        horario=F('horario')
                    ).values_list('mensagem_id', flat=True))
                )

                total_previstas = mensagens_unicas.count() + mensagens_recorrentes_previstas.count()
                now_utc = now.astimezone(datetime.timezone.utc)
                print(f">>>> [UTC {now_utc.strftime('%H:%M:%S')}] previsto {total_previstas} mensagens | recorrentes: {mensagens_recorrentes_previstas.count()} | únicas: {mensagens_unicas.count()}")

                for mensagem in mensagens_recorrentes_previstas:
                    # Verifica se hoje é um dos dias selecionados
                    if mensagem.dias_semana and now.strftime('%a').lower()[:3] not in [d.lower() for d in mensagem.dias_semana]:
                        continue
                    # Verifica se o horário bate (com tolerância)
                    if not mensagem.horario:
                        continue
                    # Envio centralizado
                    sucesso, info = enviar_mensagem_completo(mensagem, tipo_envio='agendado', usuario=mensagem.criado_por, tolerancia=tolerancia)
                    if sucesso:
                        print(f"[RECORRENTE] Mensagem {mensagem.id} enviada com sucesso.")
                    # else:
                    #     print(f"[RECORRENTE] Falha ao enviar mensagem {mensagem.id}: {info}")

                # Remover uso de threads.join(), pois o envio já é síncrono na função centralizada
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Worker interrompido pelo usuário.')) 

# Utilitário para corrigir datas naive já salvas (rodar no shell do Django):
def corrigir_agendado_para_naive():
    from django.utils import timezone
    from scheduled_messages.models import ScheduledMessage
    count = 0
    for m in ScheduledMessage.objects.filter(agendado_para__isnull=False):
        if timezone.is_naive(m.agendado_para):
            m.agendado_para = timezone.make_aware(m.agendado_para, timezone.get_current_timezone())
            m.save()
            count += 1
    print(f"Corrigidas {count} mensagens com agendado_para naive.") 