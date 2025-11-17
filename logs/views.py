from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from .models import Log
from django.db.models import Q
import pytz
from django.utils import timezone
tz_sp = pytz.timezone('America/Sao_Paulo')

# Create your views here.

@staff_member_required
def log_list(request):
    tipo = request.GET.get('tipo', '')
    busca = request.GET.get('q', '')
    logs = Log.objects.all().order_by('-criado_em')
    if tipo:
        logs = logs.filter(tipo=tipo)
    if busca:
        logs = logs.filter(
            Q(mensagem_texto__icontains=busca) |
            Q(detalhes__icontains=busca) |
            Q(tipo__icontains=busca) |
            Q(canal__nome__icontains=busca) |
            Q(usuario__username__icontains=busca)
        )
    paginator = Paginator(logs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Após obter page_obj:
    for log in page_obj:
        detalhes = log.detalhes or ''
        # Inicializa campos
        log.titulo = ''
        log.data_hora = ''
        log.erro = ''
        log.observacao = ''
        log.origem = ''
        log.canal_nome = ''
        log.usuario_nome = ''
        log.tipo_execucao = ''
        log.data_evento_br = ''
        log.hora_evento_br = ''
        log.status_conexao = None
        log.status_conexao_msg = ''
        # Parse simples por linhas
        for linha in detalhes.split('\n'):
            l = linha.strip()
            l_lower = l.lower()
            if l_lower.startswith('conexão:'):
                if 'ok' in l_lower:
                    log.status_conexao = True
                    log.status_conexao_msg = 'OK'
                else:
                    log.status_conexao = False
                    log.status_conexao_msg = l[9:].strip()
                    log.erro = log.status_conexao_msg  # Exibir motivo da falha na coluna Erro
            elif l_lower.startswith('título:'):
                log.titulo = l.split(':',1)[-1].strip()
            elif l_lower.startswith('data/hora:'):
                log.data_hora = l.split(':',1)[-1].strip()
            elif l_lower.startswith('erro:'):
                log.erro = l.split(':',1)[-1].strip()
            elif l_lower.startswith('canal:'):
                log.canal_nome = l.split(':',1)[-1].strip()
            elif l_lower.startswith('usuário:'):
                log.usuario_nome = l.split(':',1)[-1].strip()
            elif l_lower.startswith('teste de envio manual') or l_lower.startswith('teste:'):
                log.origem = 'Teste Manual'
                log.tipo_execucao = 'Teste'
        # Se não for teste manual, considerar automação
        if not log.origem:
            log.origem = 'Automação'
        if not log.tipo_execucao:
            log.tipo_execucao = 'Automático'
        # Fallbacks para canal/usuário se não vierem em detalhes
        if not log.canal_nome and log.canal:
            log.canal_nome = str(log.canal)
        if not log.usuario_nome and log.usuario:
            log.usuario_nome = str(log.usuario)
        # Converter data_hora para o timezone de SP e formatar
        try:
            if log.data_hora:
                dt = timezone.datetime.fromisoformat(log.data_hora.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_sp = dt.astimezone(tz_sp)
                log.data_evento_br = dt_sp.strftime('%d/%m/%Y')
                log.hora_evento_br = dt_sp.strftime('%H:%M:%S')
            else:
                log.data_evento_br = ''
                log.hora_evento_br = ''
        except Exception:
            log.data_evento_br = log.data_hora
            log.hora_evento_br = ''
    total_logs = logs.count()
    return render(request, 'logs/log_list.html', {
        'page_obj': page_obj,
        'tipo': tipo,
        'busca': busca,
        'total_logs': total_logs,
    })
