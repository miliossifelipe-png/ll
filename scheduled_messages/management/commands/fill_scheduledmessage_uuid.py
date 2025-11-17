from django.core.management.base import BaseCommand
from scheduled_messages.models import ScheduledMessage
import uuid

class Command(BaseCommand):
    help = 'Preenche o campo uuid de ScheduledMessage para registros que ainda não têm valor.'

    def handle(self, *args, **options):
        count = 0
        for msg in ScheduledMessage.objects.filter(uuid__isnull=True):
            msg.uuid = uuid.uuid4()
            msg.save(update_fields=['uuid'])
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Atualizados {count} registros de ScheduledMessage com uuid.')) 