from django.core.management.base import BaseCommand
from scheduled_messages.models import ScheduledMessage
from django.utils import timezone

class Command(BaseCommand):
    help = 'Preenche enviado_em nas mensagens enviadas que estão com enviado_em nulo.'

    def handle(self, *args, **options):
        msgs = ScheduledMessage.objects.filter(enviado=True, enviado_em__isnull=True)
        count = 0
        for msg in msgs:
            if msg.agendado_para:
                msg.enviado_em = msg.agendado_para
            elif msg.data_inicio:
                msg.enviado_em = timezone.make_aware(timezone.datetime.combine(msg.data_inicio, timezone.datetime.min.time()))
            else:
                msg.enviado_em = timezone.now()
            msg.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Atualizadas {count} mensagens.')) 