from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ScheduledMessage, MessageBlock, DraftMessage
from .forms import ScheduledMessageForm
from channels.models import Channel
from django.views.generic import TemplateView
from django.forms import modelformset_factory, inlineformset_factory
from django.utils.decorators import method_decorator
import json
from django.core.files.uploadedfile import UploadedFile
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .utils import enviar_mensagem_telegram, verificar_conexao_telegram, enviar_mensagem_completo, enviar_mensagem_teste
from django.db.models import Q
import datetime
from django.views import View
import uuid
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import File, ContentFile
import logging
from django.conf import settings
import os
import time
from logs.models import Log
from django.utils import timezone
from django.core.paginator import Paginator

# Create your views here.

@method_decorator(login_required, name='dispatch')
class ScheduledMessageListView(TemplateView):
    template_name = 'scheduled_messages/scheduled_message_list.html'
    def get(self, request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            mensagens = ScheduledMessage.objects.all().order_by('-id')
            canais = Channel.objects.all()
            rascunhos = DraftMessage.objects.filter(status='rascunho').order_by('-atualizado_em')
        else:
            mensagens = ScheduledMessage.objects.filter(criado_por=request.user).order_by('-id')
            canais = Channel.objects.filter(criado_por=request.user)
            rascunhos = DraftMessage.objects.filter(criado_por=request.user, status='rascunho').order_by('-atualizado_em')
        titulo = request.GET.get('titulo')
        status = request.GET.get('status')
        canal = request.GET.get('canal')
        agendado_para = request.GET.get('agendado_para')
        ultima_execucao = request.GET.get('ultima_execucao')
        falha = request.GET.get('falha')
        dias_semana = request.GET.get('dias_semana')

        if titulo:
            mensagens = mensagens.filter(titulo__icontains=titulo)
        if status:
            if status == 'pendente':
                mensagens = mensagens.filter(tipo='unico', enviado=False)
            elif status == 'enviada':
                mensagens = mensagens.filter(tipo='unico', enviado=True)
            elif status == 'recorrente':
                mensagens = mensagens.filter(tipo='recorrente')
        if canal:
            mensagens = mensagens.filter(canal_id=canal)
        if agendado_para:
            try:
                agendado_para_date = datetime.datetime.strptime(agendado_para, '%Y-%m-%d').date()
                mensagens = mensagens.filter(agendado_para__date=agendado_para_date)
            except Exception:
                pass
        if ultima_execucao:
            try:
                ultima_execucao_date = datetime.datetime.strptime(ultima_execucao, '%Y-%m-%d').date()
                mensagens = mensagens.filter(
                    Q(tipo='unico', enviado_em__date=ultima_execucao_date) |
                    Q(tipo='recorrente', ocorrencias__enviado_em__date=ultima_execucao_date)
                ).distinct()
            except Exception:
                pass
        if falha:
            if falha == 'sim':
                mensagens = mensagens.exclude(erro_ultimo_envio__isnull=True).exclude(erro_ultimo_envio='')
            elif falha == 'nao':
                mensagens = mensagens.filter(Q(erro_ultimo_envio__isnull=True) | Q(erro_ultimo_envio=''))
        if dias_semana:
            dias = [d.strip().lower() for d in dias_semana.split(',') if d.strip()]
            if dias:
                q = Q()
                for d in dias:
                    q |= Q(dias_semana__icontains=d)
                mensagens = mensagens.filter(tipo='recorrente').filter(q)

        total_mensagens = mensagens.count()
        paginator = Paginator(mensagens, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return self.render_to_response({
            'page_obj': page_obj,
            'total_mensagens': total_mensagens,
            'rascunhos': rascunhos,
            'canais': canais,
            'request': request,
            'titulo': titulo,
            'status': status,
            'canal': canal,
            'agendado_para': agendado_para,
            'ultima_execucao': ultima_execucao,
            'falha': falha,
            'dias_semana': dias_semana,
        })

    def post(self, request, *args, **kwargs):
        ids = request.POST.getlist('ids')
        if ids:
            if request.user.is_staff or request.user.is_superuser:
                ScheduledMessage.objects.filter(id__in=ids).delete()
            else:
                ScheduledMessage.objects.filter(criado_por=request.user, id__in=ids).delete()
        return redirect('scheduled_message_list')

@method_decorator(login_required, name='dispatch')
class ScheduledMessageCreateView(TemplateView):
    template_name = 'scheduled_messages/scheduled_message_form_blocks.html'
    def get(self, request, *args, **kwargs):
        form = ScheduledMessageForm()
        return self.render_to_response({'form': form})
    def post(self, request, *args, **kwargs):
        form = ScheduledMessageForm(request.POST, request.FILES)

        print(" ------------------------------ ")
        print(request.POST)
        print(request.FILES)
        # print(form)

        blocos_json = request.POST.get('blocos_json')
        if not blocos_json or len(json.loads(blocos_json)) == 0:
            form.add_error(None, 'Adicione pelo menos um bloco à mensagem.')
            return self.render_to_response({'form': form})

        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.criado_por = request.user
            # Na criação e edição de ScheduledMessage, converter agendado_para para UTC antes de salvar
            if mensagem.agendado_para:
                if timezone.is_naive(mensagem.agendado_para):
                    mensagem.agendado_para = timezone.make_aware(mensagem.agendado_para, timezone.get_current_timezone())
                mensagem.agendado_para = mensagem.agendado_para.astimezone(datetime.timezone.utc)
            mensagem.save()
            # Processar blocos
            logger = logging.getLogger(__name__)
            logger.info(f"Salvando mensagem nova: id={mensagem.id}, titulo={mensagem.titulo}")
            if blocos_json:
                blocos = json.loads(blocos_json)
                logger.info(f"Blocos recebidos: {blocos}")
                for idx, bloco in enumerate(blocos):
                    arquivo = None
                    arquivo_nome_original = None
                    # Se veio de rascunho, não haverá request.FILES, mas haverá arquivo_nome
                    if bloco.get('arquivo_name') and bloco.get('arquivo_name') in request.FILES:
                        arquivo = request.FILES.get(bloco['arquivo_name'])
                        if arquivo:
                            arquivo_nome_original = arquivo.name
                    elif bloco.get('arquivo_nome'):
                        arquivo_nome_path = bloco['arquivo_nome']
                        if default_storage.exists(arquivo_nome_path):
                            with default_storage.open(arquivo_nome_path, 'rb') as f:
                                file_content = f.read()
                            arquivo = ContentFile(file_content, name=os.path.basename(arquivo_nome_path))
                        else:
                            logger.warning(f"Arquivo não encontrado no storage: {arquivo_nome_path}")
                            arquivo = None
                        arquivo_nome_original = bloco.get('arquivo_nome_original') or os.path.basename(arquivo_nome_path)
                    mb = MessageBlock.objects.create(
                        mensagem=mensagem,
                        tipo=bloco['tipo'],
                        conteudo=bloco['conteudo'],
                        arquivo=arquivo,
                        arquivo_nome_original=arquivo_nome_original,
                        caption=bloco.get('caption', ''),
                        ordem=idx,
                        uid=bloco.get('uid')
                    )
                    logger.info(f"Bloco salvo: id={mb.id}, tipo={mb.tipo}, conteudo={mb.conteudo}, caption={mb.caption}, arquivo={mb.arquivo}, arquivo_nome_original={mb.arquivo_nome_original}")
            else:
                logger.warning("Nenhum bloco recebido no POST!")
            # Se veio de um draft, marque como 'descartado' (NÃO exclua arquivos do storage)
            draft_uuid = request.GET.get('draft') or request.POST.get('draft')
            if draft_uuid:
                try:
                    draft = DraftMessage.objects.get(uuid=draft_uuid, criado_por=request.user)
                    draft.status = 'descartado'
                    draft.save()
                except DraftMessage.DoesNotExist:
                    pass
            return redirect('scheduled_message_list')
        return self.render_to_response({'form': form})

@method_decorator(login_required, name='dispatch')
class ScheduledMessageEditView(TemplateView):
    template_name = 'scheduled_messages/scheduled_message_form_blocks.html'
    def get(self, request, pk, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk)
        else:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk, criado_por=request.user)
        form = ScheduledMessageForm(instance=mensagem)
        blocos_qs = mensagem.blocos.order_by('ordem')
        blocos = []
        for idx, b in enumerate(blocos_qs):
            arquivo_nome = None
            arquivo_nome_original = None
            if b.arquivo:
                try:
                    arquivo_nome = b.arquivo.name
                except Exception as e:
                    print(f"[DEBUG] Erro ao acessar b.arquivo.name: {e}")
                if hasattr(b, 'arquivo_nome_original') and b.arquivo_nome_original:
                    arquivo_nome_original = b.arquivo_nome_original
                else:
                    # fallback: nome do arquivo salvo
                    arquivo_nome_original = os.path.basename(arquivo_nome) if arquivo_nome else None
            print(f"[DEBUG] bloco {idx} - tipo: {b.tipo} - arquivo: {b.arquivo} - arquivo_nome: {arquivo_nome} - arquivo_nome_original: {arquivo_nome_original}")
            bloco_dict = {
                'id': idx,
                'tipo': b.tipo,
                'conteudo': b.conteudo,
                'arquivo_nome': arquivo_nome,
                'arquivo_nome_original': arquivo_nome_original,
                'caption': b.caption if hasattr(b, 'caption') else '',
                'editandoArquivo': False,
                'uid': b.uid if hasattr(b, 'uid') else None
            }
            # Para blocos de botões, garantir que conteudo seja string JSON
            if b.tipo == 'inline_keyboard' and isinstance(b.conteudo, list):
                bloco_dict['conteudo'] = json.dumps(b.conteudo)
            blocos.append(bloco_dict)
        return self.render_to_response({'form': form, 'mensagem': mensagem, 'blocos': blocos})
    def post(self, request, pk, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk)
        else:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk, criado_por=request.user)
        form = ScheduledMessageForm(request.POST, request.FILES, instance=mensagem)
        blocos_json = request.POST.get('blocos_json')
        if not blocos_json or len(json.loads(blocos_json)) == 0:
            form.add_error(None, 'Adicione pelo menos um bloco à mensagem.')
            blocos = mensagem.blocos.order_by('ordem')
            return self.render_to_response({'form': form, 'mensagem': mensagem, 'blocos': blocos})
        if form.is_valid():
            mensagem = form.save(commit=False)
            # Na ScheduledMessageEditView.post:
            if mensagem.agendado_para:
                if timezone.is_naive(mensagem.agendado_para):
                    mensagem.agendado_para = timezone.make_aware(mensagem.agendado_para, timezone.get_current_timezone())
                mensagem.agendado_para = mensagem.agendado_para.astimezone(datetime.timezone.utc)
            mensagem.save()
            # Buscar blocos antigos por uid ANTES de deletar
            antigos_map = {b.uid: b for b in mensagem.blocos.all() if hasattr(b, 'uid') and b.uid}
            novos_uids = set()
            if blocos_json:
                blocos = json.loads(blocos_json)
                novos_uids = set(b.get('uid') for b in blocos if b.get('uid'))
            # Identificar blocos removidos
            removidos = [b for uid, b in antigos_map.items() if uid not in novos_uids]
            # Deletar arquivos dos blocos removidos
            for bloco in removidos:
                if bloco.arquivo and bloco.arquivo.name:
                    try:
                        if default_storage.exists(bloco.arquivo.name):
                            default_storage.delete(bloco.arquivo.name)
                    except Exception as e:
                        print(f"[WARN] Erro ao deletar arquivo do bloco removido: {e}")
            # Agora sim, deletar todos os blocos antigos
            mensagem.blocos.all().delete()
            if blocos_json:
                blocos = json.loads(blocos_json)
                for idx, bloco in enumerate(blocos):
                    arquivo = None
                    arquivo_nome_original = None
                    if bloco.get('arquivo_name') and bloco.get('arquivo_name') in request.FILES:
                        arquivo = request.FILES.get(bloco['arquivo_name'])
                        if arquivo:
                            arquivo_nome_original = arquivo.name
                    elif bloco.get('arquivo_nome'):
                        arquivo_nome_path = bloco['arquivo_nome']
                        if default_storage.exists(arquivo_nome_path):
                            with default_storage.open(arquivo_nome_path, 'rb') as f:
                                file_content = f.read()
                            arquivo = ContentFile(file_content, name=os.path.basename(arquivo_nome_path))
                        else:
                            arquivo = None
                        arquivo_nome_original = bloco.get('arquivo_nome_original') or os.path.basename(arquivo_nome_path)
                    # Se não houver novo arquivo nem referência, buscar pelo uid
                    if not arquivo and bloco.get('uid') and bloco['uid'] in antigos_map:
                        antigo = antigos_map[bloco['uid']]
                        arquivo = antigo.arquivo
                        arquivo_nome_original = antigo.arquivo_nome_original
                    conteudo = bloco['conteudo']
                    if bloco['tipo'] == 'inline_keyboard' and isinstance(conteudo, list):
                        conteudo = json.dumps(conteudo)
                    MessageBlock.objects.create(
                        mensagem=mensagem,
                        tipo=bloco['tipo'],
                        conteudo=conteudo,
                        arquivo=arquivo,
                        arquivo_nome_original=arquivo_nome_original,
                        caption=bloco.get('caption', ''),
                        ordem=idx,
                        uid=bloco.get('uid')
                    )
            # Na ScheduledMessageEditView.post:
            campos_alterados = form.changed_data
            if mensagem.tipo == 'unico':
                # Resetar status apenas se 'agendado_para' foi alterado
                if 'agendado_para' in campos_alterados:
                    mensagem.enviado = False
                    mensagem.enviado_em = None
            elif mensagem.tipo == 'recorrente':
                # Resetar ocorrências apenas se algum campo de data/hora foi alterado
                campos_relevantes = {'horario', 'data_inicio', 'data_fim', 'dias_semana'}
                if campos_relevantes.intersection(campos_alterados):
                    from scheduled_messages.models import ScheduledMessageOccurrence
                    ScheduledMessageOccurrence.objects.filter(mensagem=mensagem).delete()
            mensagem.save()
            return redirect('scheduled_message_list')
        blocos = mensagem.blocos.order_by('ordem')
        return self.render_to_response({'form': form, 'mensagem': mensagem, 'blocos': blocos})

@method_decorator(login_required, name='dispatch')
class ScheduledMessageDeleteView(TemplateView):
    template_name = 'scheduled_messages/scheduled_message_confirm_delete.html'
    def get(self, request, pk, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk)
        else:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk, criado_por=request.user)
        return self.render_to_response({'mensagem': mensagem})
    def post(self, request, pk, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk)
        else:
            mensagem = get_object_or_404(ScheduledMessage, pk=pk, criado_por=request.user)
        mensagem.delete()
        return redirect('scheduled_message_list')

class MessageBlocksPrototypeView(TemplateView):
    template_name = 'scheduled_messages/blocks_prototype.html'

@csrf_exempt
def ajax_upload_block_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        from .models import unique_file_path
        file_path = 'blocos/' + unique_file_path(None, file.name)
        saved_path = default_storage.save(file_path, file)
        file_url = default_storage.url(saved_path)
        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'file_name': saved_path,
            'original_name': file.name
        })
    return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

@login_required
def testar_envio_mensagem(request, pk):
    if request.user.is_staff or request.user.is_superuser:
        mensagem = ScheduledMessage.objects.get(pk=pk)
    else:
        mensagem = ScheduledMessage.objects.get(pk=pk, criado_por=request.user)
    sucesso, info = enviar_mensagem_teste(mensagem, request.user)
    return HttpResponseRedirect(reverse('scheduled_message_list'))

class ScheduledMessageBulkDeleteView(TemplateView):
    template_name = 'scheduled_messages/scheduled_message_bulk_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        ids = request.POST.getlist('ids')
        if request.user.is_staff or request.user.is_superuser:
            mensagens = ScheduledMessage.objects.filter(id__in=ids)
        else:
            mensagens = ScheduledMessage.objects.filter(criado_por=request.user, id__in=ids)
        if 'confirm' in request.POST:
            mensagens.delete()
            return redirect('scheduled_message_list')
        return self.render_to_response({'mensagens': mensagens, 'ids': ids})

@csrf_exempt
def api_draftmessage(request):
    user = request.user if request.user.is_authenticated else None
    if request.method == 'POST':
        # Criar novo rascunho
        data = json.loads(request.body.decode())
        draft_uuid = data.get('uuid') or str(uuid.uuid4())
        dados = data.get('dados', {})
        draft, created = DraftMessage.objects.get_or_create(uuid=draft_uuid, criado_por=user, defaults={'dados': dados})
        if not created:
            draft.dados = dados
            draft.save()
        return JsonResponse({'uuid': str(draft.uuid), 'dados': draft.dados, 'status': draft.status})
    elif request.method == 'PUT':
        # Atualizar rascunho existente
        data = json.loads(request.body.decode())
        draft_uuid = data.get('uuid')
        dados = data.get('dados', {})
        try:
            draft = DraftMessage.objects.get(uuid=draft_uuid, criado_por=user)
            draft.dados = dados
            draft.save()
            return JsonResponse({'uuid': str(draft.uuid), 'dados': draft.dados, 'status': draft.status})
        except DraftMessage.DoesNotExist:
            return JsonResponse({'error': 'Draft not found'}, status=404)
    elif request.method == 'GET':
        # Buscar rascunho por uuid
        draft_uuid = request.GET.get('uuid')
        try:
            draft = DraftMessage.objects.get(uuid=draft_uuid, criado_por=user)
            return JsonResponse({'uuid': str(draft.uuid), 'dados': draft.dados, 'status': draft.status})
        except DraftMessage.DoesNotExist:
            return JsonResponse({'error': 'Draft not found'}, status=404)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@require_POST
@login_required
def excluir_rascunho(request, uuid):
    draft = get_object_or_404(DraftMessage, uuid=uuid, criado_por=request.user)
    draft.delete()
    return redirect('scheduled_message_list')

@method_decorator(login_required, name='dispatch')
class DraftMessageDeleteView(TemplateView):
    template_name = 'scheduled_messages/draftmessage_confirm_delete.html'
    def get(self, request, uuid, *args, **kwargs):
        draft = get_object_or_404(DraftMessage, uuid=uuid, criado_por=request.user)
        return self.render_to_response({'draft': draft})
    def post(self, request, uuid, *args, **kwargs):
        draft = get_object_or_404(DraftMessage, uuid=uuid, criado_por=request.user)
        draft.delete()
        return redirect('scheduled_message_list')

@csrf_exempt
@require_POST
@login_required
def excluir_arquivo_bloco(request):
    try:
        data = json.loads(request.body.decode())
        file_name = data.get('file_name')
        if not file_name:
            return JsonResponse({'success': False, 'error': 'Nome do arquivo não informado.'}, status=400)
        from django.core.files.storage import default_storage
        if default_storage.exists(file_name):
            try:
                default_storage.delete(file_name)
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Erro ao deletar arquivo: {str(e)}'}, status=500)
        return JsonResponse({'success': False, 'error': 'Arquivo não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro inesperado: {str(e)}'}, status=500)

class DraftMessageBulkDeleteView(TemplateView):
    template_name = 'scheduled_messages/draftmessage_bulk_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        uuids = request.POST.getlist('uuids')
        drafts = DraftMessage.objects.filter(criado_por=request.user, uuid__in=uuids)
        if 'confirm' in request.POST:
            from django.conf import settings
            for draft in drafts:
                blocos = draft.dados.get('blocos', [])
                for bloco in blocos:
                    arquivo_nome = bloco.get('arquivo_nome')
                    if arquivo_nome:
                        if default_storage.exists(arquivo_nome):
                            default_storage.delete(arquivo_nome)
            drafts.delete()
            return redirect('scheduled_message_list')
        return self.render_to_response({'drafts': drafts, 'uuids': uuids})

@require_POST
@login_required
def remover_bloco(request):
    import json
    data = json.loads(request.body.decode())
    uid = data.get('uid')
    if not uid:
        return JsonResponse({'success': False, 'error': 'UID não informado.'}, status=400)
    try:
        bloco = MessageBlock.objects.get(uid=uid, mensagem__criado_por=request.user)
        # Deletar arquivo do storage, se houver
        if bloco.arquivo and bloco.arquivo.name:
            if default_storage.exists(bloco.arquivo.name):
                for tentativa in range(3):
                    try:
                        default_storage.delete(bloco.arquivo.name)
                        break
                    except PermissionError as e:
                        if tentativa < 2:
                            time.sleep(1)  # Aguarda 1 segundo e tenta de novo
                        else:
                            return JsonResponse({'success': False, 'error': f'Não foi possível deletar o arquivo. Ele pode estar aberto em outro programa. Feche qualquer player, explorer ou editor que esteja usando o arquivo e tente novamente.'}, status=423)
        bloco.delete()
        return JsonResponse({'success': True})
    except MessageBlock.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Bloco não encontrado.'}, status=404)

@login_required
def novo_draft(request):
    draft = DraftMessage.objects.create(criado_por=request.user, dados={})
    return redirect(f"{reverse('scheduled_message_create')}?draft={draft.uuid}")
