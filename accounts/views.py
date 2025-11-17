from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django import forms
from django.contrib.auth import get_user_model
from scheduled_messages.models import ScheduledMessage, DraftMessage, ScheduledMessageOccurrence
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from channels.models import Channel
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.db.models import Case, When, F, Value, DateTimeField
from django.db.models.functions import Coalesce
from collections import Counter, defaultdict
from logs.models import Log

# Create your views here.

@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()
    today = now.date()
    # Mensagens
    if user.is_staff or user.is_superuser:
        total_mensagens = ScheduledMessage.objects.count()
        total_rascunhos = DraftMessage.objects.filter(status='rascunho').count()
        # Únicas para hoje
        total_unicas_hoje = ScheduledMessage.objects.filter(tipo='unico', enviado=False, agendado_para__date=today).count()
        # Recorrentes para hoje
        total_recorrentes_hoje = ScheduledMessage.objects.filter(
            tipo='recorrente',
            data_inicio__lte=today
        ).exclude(data_fim__lt=today).filter(
            Q(dias_semana__icontains=today.strftime('%a').lower()[:3])
        ).count()
    else:
        total_mensagens = ScheduledMessage.objects.filter(criado_por=user).count()
        total_rascunhos = DraftMessage.objects.filter(criado_por=user, status='rascunho').count()
        total_unicas_hoje = ScheduledMessage.objects.filter(
            criado_por=user, tipo='unico', enviado=False, agendado_para__date=today
        ).count()
        total_recorrentes_hoje = ScheduledMessage.objects.filter(
            criado_por=user, tipo='recorrente', data_inicio__lte=today
        ).exclude(data_fim__lt=today).filter(
            Q(dias_semana__icontains=today.strftime('%a').lower()[:3])
        ).count()
    # Logs para a tabela do dashboard
    from logs.models import Log
    logs = Log.objects.all().order_by('-criado_em')[:20]
    page_obj = logs  # para compatibilidade com o template
    total_logs = Log.objects.count()
    # Parse campos extras igual à tela de logs
    import pytz
    tz_sp = pytz.timezone('America/Sao_Paulo')
    from django.utils import timezone as djtz
    for log in page_obj:
        detalhes = log.detalhes or ''
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
                    log.erro = log.status_conexao_msg
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
        if not log.origem:
            log.origem = 'Automação'
        if not log.tipo_execucao:
            log.tipo_execucao = 'Automático'
        if not log.canal_nome and log.canal:
            log.canal_nome = str(log.canal)
        if not log.usuario_nome and log.usuario:
            log.usuario_nome = str(log.usuario)
        try:
            if log.data_hora:
                dt = djtz.datetime.fromisoformat(log.data_hora.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=djtz.utc)
                dt_sp = dt.astimezone(tz_sp)
                log.data_evento_br = dt_sp.strftime('%d/%m/%Y')
                log.hora_evento_br = dt_sp.strftime('%H:%M:%S')
            else:
                log.data_evento_br = ''
                log.hora_evento_br = ''
        except Exception:
            log.data_evento_br = log.data_hora
            log.hora_evento_br = ''
    return render(request, 'accounts/dashboard.html', {
        'total_mensagens': total_mensagens,
        'total_rascunhos': total_rascunhos,
        'total_unicas_hoje': total_unicas_hoje,
        'total_recorrentes_hoje': total_recorrentes_hoje,
        'page_obj': page_obj,
        'total_logs': total_logs,
        'dashboard_logs': True,
    })

@login_required
def dashboard_data(request):
    user = request.user
    usuario_id = request.GET.get('usuario')
    canal_id = request.GET.get('canal')
    tipo = request.GET.get('tipo')
    periodo = request.GET.get('periodo', '7d')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    from django.utils import timezone
    from datetime import datetime, timedelta, date, time as dtime
    hoje = timezone.now().date()
    # Determinar intervalo de datas
    if periodo == 'hoje':
        inicio = hoje
        fim = hoje
    elif periodo == '7d':
        inicio = hoje - timedelta(days=6)
        fim = hoje
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        fim = hoje
    elif periodo == 'personalizado' and data_inicio and data_fim:
        try:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except Exception:
            inicio = hoje - timedelta(days=6)
            fim = hoje
    else:
        inicio = hoje - timedelta(days=6)
        fim = hoje
    # Filtros base
    mensagens_unicas = ScheduledMessage.objects.filter(tipo='unico')
    mensagens_recorrentes = ScheduledMessage.objects.filter(tipo='recorrente')
    if not (user.is_staff or user.is_superuser):
        mensagens_unicas = mensagens_unicas.filter(criado_por=user)
        mensagens_recorrentes = mensagens_recorrentes.filter(criado_por=user)
    if usuario_id:
        mensagens_unicas = mensagens_unicas.filter(criado_por_id=usuario_id)
        mensagens_recorrentes = mensagens_recorrentes.filter(criado_por_id=usuario_id)
    if canal_id:
        mensagens_unicas = mensagens_unicas.filter(canal_id=canal_id)
        mensagens_recorrentes = mensagens_recorrentes.filter(canal_id=canal_id)
    if tipo:
        mensagens_unicas = mensagens_unicas.filter(tipo=tipo)
        mensagens_recorrentes = mensagens_recorrentes.filter(tipo=tipo)
    # Mensagens únicas: previsão
    unicas_previstas = []
    for m in mensagens_unicas:
        if m.agendado_para and inicio <= m.agendado_para.date() <= fim:
            unicas_previstas.append({
                'data_envio': m.agendado_para.date(),
                'criado_por__username': m.criado_por.get_username() if m.criado_por else None,
                'canal__nome': m.canal.nome if m.canal else None,
                'tipo': m.tipo,
            })
    # Mensagens recorrentes: previsão
    recorrentes_previstas = []
    dias_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
    for m in mensagens_recorrentes:
        if not m.data_inicio or (m.data_fim and m.data_fim < inicio):
            continue
        data_ini = max(m.data_inicio, inicio)
        data_fim = min(m.data_fim, fim) if m.data_fim else fim
        dias_semana = m.dias_semana or []
        dias_semana_idx = [dias_map[d] for d in dias_semana if d in dias_map]
        d = data_ini
        while d <= data_fim:
            if not dias_semana_idx or d.weekday() in dias_semana_idx:
                recorrentes_previstas.append({
                    'data_envio': d,
                    'criado_por__username': m.criado_por.get_username() if m.criado_por else None,
                    'canal__nome': m.canal.nome if m.canal else None,
                    'tipo': m.tipo,
                })
            d += timedelta(days=1)
    # Unificar dados
    dados = unicas_previstas + recorrentes_previstas
    # Agrupamento por dia
    from collections import Counter
    por_dia_counter = Counter()
    for d in dados:
        if d['data_envio']:
            por_dia_counter[d['data_envio']] += 1
    por_dia = [
        {'data_envio__date': str(d), 'qtd': qtd}
        for d, qtd in sorted(por_dia_counter.items())
    ]
    # Agrupamento por usuário
    por_usuario_counter = Counter()
    for d in dados:
        if d['criado_por__username']:
            por_usuario_counter[d['criado_por__username']] += 1
    por_usuario = [
        {'criado_por__username': u, 'qtd': qtd}
        for u, qtd in sorted(por_usuario_counter.items(), key=lambda x: -x[1])
    ]
    top_usuarios = por_usuario[:5]
    # Agrupamento por canal
    por_canal_counter = Counter()
    for d in dados:
        if d['canal__nome']:
            por_canal_counter[d['canal__nome']] += 1
    por_canal = [
        {'canal__nome': c, 'qtd': qtd}
        for c, qtd in sorted(por_canal_counter.items(), key=lambda x: -x[1])
    ]
    # Agrupamento por tipo
    por_tipo_counter = Counter()
    for d in dados:
        if d['tipo']:
            por_tipo_counter[d['tipo']] += 1
    por_tipo = [
        {'tipo': t, 'qtd': qtd}
        for t, qtd in sorted(por_tipo_counter.items(), key=lambda x: -x[1])
    ]
    return JsonResponse({
        'por_dia': list(por_dia),
        'por_usuario': list(por_usuario),
        'top_usuarios': top_usuarios,
        'por_canal': list(por_canal),
        'por_tipo': list(por_tipo),
    })

@login_required
def dashboard_logs_data(request):
    # Filtros opcionais
    periodo = request.GET.get('periodo', '7d')
    tipo = request.GET.get('tipo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    logs = Log.objects.all()
    if tipo:
        logs = logs.filter(tipo=tipo)
    from django.utils import timezone
    from datetime import datetime, timedelta
    hoje = timezone.now().date()
    if periodo == 'hoje':
        logs = logs.filter(criado_em__date=hoje)
    elif periodo == '7d':
        inicio = hoje - timedelta(days=6)
        logs = logs.filter(criado_em__date__gte=inicio, criado_em__date__lte=hoje)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        logs = logs.filter(criado_em__date__gte=inicio, criado_em__date__lte=hoje)
    elif periodo == 'personalizado' and data_inicio and data_fim:
        try:
            di = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            df = datetime.strptime(data_fim, '%Y-%m-%d').date()
            logs = logs.filter(criado_em__date__gte=di, criado_em__date__lte=df)
        except Exception:
            pass
    # Gráfico: erros por dia
    from collections import Counter
    por_dia_counter = Counter()
    for l in logs:
        dia = l.criado_em.date()
        por_dia_counter[dia] += 1
    por_dia = [
        {'criado_em__date': str(d), 'qtd': qtd}
        for d, qtd in sorted(por_dia_counter.items())
    ]
    # Gráfico: erros por mensagem
    por_mensagem = logs.values('mensagem').annotate(qtd=Count('id')).order_by('-qtd')[:10]
    # Gráfico: erros por tipo
    por_tipo = logs.values('tipo').annotate(qtd=Count('id')).order_by('-qtd')
    return JsonResponse({
        'por_dia': list(por_dia),
        'por_mensagem': list(por_mensagem),
        'por_tipo': list(por_tipo),
    })

@login_required
def canais_list(request):
    user = request.user
    if user.is_staff or user.is_superuser:
        canais = Channel.objects.all()
    else:
        canais = Channel.objects.filter(criado_por=user)
    return JsonResponse([{'id': c.id, 'nome': c.nome} for c in canais], safe=False)

@login_required
def usuarios_list(request):
    User = get_user_model()
    usuarios = User.objects.all()
    return JsonResponse([{'id': u.id, 'username': u.get_username()} for u in usuarios], safe=False)

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label='E-mail')
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            raise forms.ValidationError('E-mail ou senha inválidos.')
        self.user_cache = authenticate(username=user.username, password=password)
        if self.user_cache is None:
            raise forms.ValidationError('E-mail ou senha inválidos.')
        return self.cleaned_data

    def get_user(self):
        return self.user_cache

def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    form = EmailAuthenticationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('/')
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')
