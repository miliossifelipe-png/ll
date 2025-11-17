import asyncio
import threading
from telegram import Bot
from telegram.request import HTTPXRequest
from django.conf import settings
import os
from bs4 import BeautifulSoup
from sulguk import transform_html
import logging
import requests

logger = logging.getLogger("telegram_send")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("telegram_send.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.hasHandlers():
    logger.addHandler(handler)

def enviar_mensagem_telegram(scheduled_message, return_thread=False):
    canal = scheduled_message.canal
    try:
        logger.info(f"INÍCIO DO ENVIO: '{scheduled_message.titulo}'")
        chat_id = canal.id_telegram
        bot_token = canal.bot_token
        blocos = list(scheduled_message.blocos.order_by('ordem').values(
            'tipo', 'conteudo', 'arquivo', 'arquivo_nome_original', 'caption'
        ))

        def runner():
            asyncio.run(enviar_mensagem_telegram_async(bot_token, chat_id, blocos))

        thread = threading.Thread(target=runner)
        thread.start()
        if return_thread:
            return thread
        # Se sucesso:
        logger.info(f"Mensagem enviada com sucesso: '{scheduled_message.titulo}'")
    except Exception as e:
        logger.error(f"Falha ao enviar mensagem: '{scheduled_message.titulo}' - Erro: {str(e)}")
        raise

# Converte HTML do CKEditor para HTML/texto compatível com o Telegram
def html_to_telegram_caption(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Substituir <p> por \n
    for p in soup.find_all('p'):
        p.insert_before('\n')
        p.unwrap()
    # Substituir <br> por \n
    for br in soup.find_all('br'):
        br.replace_with('\n')
    # Converter listas
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            li.insert_before('• ')
            li.insert_after('\n')
            li.unwrap()
        ul.unwrap()
    for ol in soup.find_all('ol'):
        idx = 1
        for li in ol.find_all('li'):
            li.insert_before(f'{idx}. ')
            li.insert_after('\n')
            li.unwrap()
            idx += 1
        ol.unwrap()
    # Remover tags não suportadas, mas manter o texto
    for tag in soup.find_all(True):
        if tag.name not in ['b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'span', 'a', 'code', 'pre']:
            tag.unwrap()
    # Retornar texto limpo
    return soup.get_text().strip()

async def enviar_mensagem_telegram_async(bot_token, chat_id, blocos):
    request = HTTPXRequest(connect_timeout=30, read_timeout=120)
    bot = Bot(token=bot_token, request=request)
    logger = logging.getLogger("telegram_send")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("telegram_send.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    if not logger.hasHandlers():
        logger.addHandler(handler)
    reply_markup = None
    idx = 0
    while idx < len(blocos):
        bloco = blocos[idx]
        tipo = bloco['tipo']
        caption = bloco.get('caption') or None
        result = None
        logger.info(f"Bloco {idx}: tipo={tipo}")
        logger.info(f"  arquivo: {bloco.get('arquivo')}")
        logger.info(f"  arquivo_nome_original: {bloco.get('arquivo_nome_original')}")
        if caption:
            result = transform_html(caption)
        if tipo == 'inline_keyboard':
            import json
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            botoes = []
            try:
                botoes = json.loads(bloco.get('conteudo') or '[]')
            except Exception as e:
                logger.error(f"  [inline_keyboard] Erro ao decodificar JSON: {e}")
                botoes = []
            keyboard = []
            for btn in botoes:
                if btn.get('text') and btn.get('url'):
                    keyboard.append([InlineKeyboardButton(text=btn['text'], url=btn['url'])])
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
                # Verifica se o próximo bloco é de mensagem
                prox_idx = idx + 1
                if prox_idx < len(blocos) and blocos[prox_idx]['tipo'] in ['texto', 'arquivo', 'imagem', 'video', 'audio']:
                    # Não envia mensagem agora, reply_markup será usado no próximo bloco
                    idx += 1
                    bloco = blocos[idx]
                    tipo = bloco['tipo']
                    caption = bloco.get('caption') or None
                    result = None
                    logger.info(f"Bloco {idx}: tipo={tipo} (com botões do bloco anterior)")
                    logger.info(f"  arquivo: {bloco.get('arquivo')}")
                    logger.info(f"  arquivo_nome_original: {bloco.get('arquivo_nome_original')}")
                    if caption:
                        result = transform_html(caption)
                    # Envia o bloco de mensagem com os botões
                    if tipo == 'texto':
                        if bloco['conteudo']:
                            result = transform_html(bloco['conteudo'])
                            await bot.send_message(chat_id=chat_id, text=result.text, entities=result.entities, reply_markup=reply_markup)
                        else:
                            await bot.send_message(chat_id=chat_id, text=' ', reply_markup=reply_markup)
                    elif tipo in ['arquivo', 'imagem']:
                        if bloco['arquivo']:
                            file_path = os.path.join(settings.MEDIA_ROOT, bloco['arquivo'])
                            ext = os.path.splitext(file_path)[1].lower()
                            is_image = ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
                            with open(file_path, 'rb') as f:
                                if is_image:
                                    if result:
                                        await bot.send_photo(chat_id=chat_id, photo=f, caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                                    else:
                                        await bot.send_photo(chat_id=chat_id, photo=f, reply_markup=reply_markup)
                                else:
                                    if result:
                                        await bot.send_document(chat_id=chat_id, document=f, filename=bloco['arquivo_nome_original'], caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                                    else:
                                        await bot.send_document(chat_id=chat_id, document=f, filename=bloco['arquivo_nome_original'], reply_markup=reply_markup)
                        # Se não houver arquivo, não envia nada
                    elif tipo == 'video':
                        if bloco['arquivo']:
                            file_path = os.path.join(settings.MEDIA_ROOT, bloco['arquivo'])
                            with open(file_path, 'rb') as f:
                                if result:
                                    await bot.send_video(chat_id=chat_id, video=f, filename=bloco['arquivo_nome_original'], caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                                else:
                                    await bot.send_video(chat_id=chat_id, video=f, filename=bloco['arquivo_nome_original'], reply_markup=reply_markup)
                    elif tipo == 'audio':
                        if bloco['arquivo']:
                            file_path = os.path.join(settings.MEDIA_ROOT, bloco['arquivo'])
                            with open(file_path, 'rb') as f:
                                if result:
                                    await bot.send_audio(chat_id=chat_id, audio=f, filename=bloco['arquivo_nome_original'], caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                                else:
                                    await bot.send_audio(chat_id=chat_id, audio=f, filename=bloco['arquivo_nome_original'], reply_markup=reply_markup)
                    reply_markup = None
                    idx += 1
                    continue
                else:
                    # Não há bloco de mensagem depois, envia mensagem separada com texto do bloco (caption) se houver
                    caption_text = (bloco.get('caption') or '').strip()
                    # Remove tags HTML vazias
                    caption_text_clean = BeautifulSoup(caption_text, 'html.parser').get_text().strip()
                    if caption_text_clean:
                        result = transform_html(bloco['caption'])
                        text_to_send = result.text.strip() or ' '
                        await bot.send_message(chat_id=chat_id, text=text_to_send, entities=result.entities, reply_markup=reply_markup)
                    else:
                        await bot.send_message(chat_id=chat_id, text=' ', reply_markup=reply_markup)
                    reply_markup = None
            else:
                logger.warning(f"  [inline_keyboard] Nenhum botão válido para enviar.")
            idx += 1
            continue
        # Se não for bloco de botões, envia normalmente
        if tipo == 'texto':
            if bloco['conteudo']:
                result = transform_html(bloco['conteudo'])
                await bot.send_message(chat_id=chat_id, text=result.text, entities=result.entities, reply_markup=reply_markup)
            else:
                await bot.send_message(chat_id=chat_id, text=' ', reply_markup=reply_markup)
            reply_markup = None
        elif tipo in ['arquivo', 'imagem']:
            if bloco['arquivo']:
                file_path = os.path.join(settings.MEDIA_ROOT, bloco['arquivo'])
                ext = os.path.splitext(file_path)[1].lower()
                is_image = ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
                with open(file_path, 'rb') as f:
                    if is_image:
                        if result:
                            await bot.send_photo(chat_id=chat_id, photo=f, caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                        else:
                            await bot.send_photo(chat_id=chat_id, photo=f, reply_markup=reply_markup)
                    else:
                        if result:
                            await bot.send_document(chat_id=chat_id, document=f, filename=bloco['arquivo_nome_original'], caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                        else:
                            await bot.send_document(chat_id=chat_id, document=f, filename=bloco['arquivo_nome_original'], reply_markup=reply_markup)
            reply_markup = None
        elif tipo == 'video':
            if bloco['arquivo']:
                file_path = os.path.join(settings.MEDIA_ROOT, bloco['arquivo'])
                with open(file_path, 'rb') as f:
                    if result:
                        await bot.send_video(chat_id=chat_id, video=f, filename=bloco['arquivo_nome_original'], caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                    else:
                        await bot.send_video(chat_id=chat_id, video=f, filename=bloco['arquivo_nome_original'], reply_markup=reply_markup)
            reply_markup = None
        elif tipo == 'audio':
            if bloco['arquivo']:
                file_path = os.path.join(settings.MEDIA_ROOT, bloco['arquivo'])
                with open(file_path, 'rb') as f:
                    if result:
                        await bot.send_audio(chat_id=chat_id, audio=f, filename=bloco['arquivo_nome_original'], caption=result.text, caption_entities=result.entities, reply_markup=reply_markup)
                    else:
                        await bot.send_audio(chat_id=chat_id, audio=f, filename=bloco['arquivo_nome_original'], reply_markup=reply_markup)
            reply_markup = None
        idx += 1


def verificar_conexao_telegram(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get("ok"):
            return True, None
        else:
            return False, data.get("description", "Erro desconhecido")
    except Exception as e:
        return False, str(e)


def enviar_mensagem_completo(mensagem, tipo_envio='agendado', usuario=None, tolerancia=2):
    """
    Envia uma mensagem (única, recorrente ou teste/manual), registra logs e controla ocorrências.
    tipo_envio: 'agendado', 'teste', 'manual'
    usuario: usuário responsável pelo envio (opcional)
    tolerancia: tolerância em minutos para recorrentes
    """
    from django.utils import timezone
    from django.db import transaction
    from logs.models import Log
    from scheduled_messages.models import ScheduledMessageOccurrence
    now = timezone.now()
    canal = mensagem.canal
    bot_token = canal.bot_token

    # 1. Validação de conexão
    conexao_ok, erro_conexao = verificar_conexao_telegram(bot_token)
    if not conexao_ok:
        Log.objects.create(
            tipo='erro',
            mensagem_texto=f'{tipo_envio.upper()}: Falha de conexão',
            detalhes=f'Conexão: Falha - {erro_conexao}\nTítulo: {mensagem.titulo}\nCanal: {canal}\nUsuário: {usuario or mensagem.criado_por}',
            canal=canal,
            mensagem=mensagem,
            usuario=usuario or mensagem.criado_por
        )
        return False, f'Falha de conexão: {erro_conexao}'

    # 2. Prevenção de duplicidade (recorrentes)
    if mensagem.tipo == 'recorrente':
        hoje = now.date()
        horario = mensagem.horario
        if ScheduledMessageOccurrence.objects.filter(mensagem=mensagem, data=hoje, horario=horario).exists():
            return False, 'Já enviada para este horário'
        # Tolerância de horário
        if horario:
            horario_msg_dt = timezone.make_aware(
                timezone.datetime.combine(hoje, horario),
                timezone.get_current_timezone()
            )
            delta_min = (now - horario_msg_dt).total_seconds() / 60
            if delta_min < 0 or delta_min > tolerancia:
                return False, 'Fora da tolerância de horário'

    # 3. Envio
    try:
        enviar_mensagem_telegram(mensagem)
        # Só atualiza status/ocorrência se envio for sucesso
        with transaction.atomic():
            if mensagem.tipo == 'unico':
                mensagem.enviado = True
                mensagem.enviado_em = now
                mensagem.save(update_fields=['enviado', 'enviado_em'])
            elif mensagem.tipo == 'recorrente':
                ScheduledMessageOccurrence.objects.create(mensagem=mensagem, data=now.date(), horario=mensagem.horario)
            Log.objects.create(
                tipo='info',
                mensagem_texto=f'{tipo_envio.upper()}: Mensagem enviada com sucesso',
                detalhes=f'Conexão: OK\nTítulo: {mensagem.titulo}\nCanal: {canal}\nUsuário: {usuario or mensagem.criado_por}\nData/Hora: {now}',
                canal=canal,
                mensagem=mensagem,
                usuario=usuario or mensagem.criado_por
            )
        return True, 'Mensagem enviada com sucesso'
    except Exception as e:
        Log.objects.create(
            tipo='erro',
            mensagem_texto=f'{tipo_envio.upper()}: Erro ao enviar mensagem',
            detalhes=f'Erro: {str(e)}\nTítulo: {mensagem.titulo}\nCanal: {canal}\nUsuário: {usuario or mensagem.criado_por}',
            canal=canal,
            mensagem=mensagem,
            usuario=usuario or mensagem.criado_por
        )
        return False, str(e)


def enviar_mensagem_teste(mensagem, usuario):
    """
    Envia uma mensagem de teste/manual, registra logs, mas não altera status de envio nem ocorrências.
    """
    from django.utils import timezone
    from logs.models import Log
    now = timezone.now()
    canal = mensagem.canal
    bot_token = canal.bot_token

    # Validação de conexão
    conexao_ok, erro_conexao = verificar_conexao_telegram(bot_token)
    if not conexao_ok:
        Log.objects.create(
            tipo='erro',
            mensagem_texto=f'TESTE: Falha de conexão',
            detalhes=f'Conexão: Falha - {erro_conexao}\nTítulo: {mensagem.titulo}\nCanal: {canal}\nUsuário: {usuario}',
            canal=canal,
            mensagem=mensagem,
            usuario=usuario
        )
        return False, f'Falha de conexão: {erro_conexao}'
    try:
        enviar_mensagem_telegram(mensagem)
        Log.objects.create(
            tipo='info',
            mensagem_texto=f'TESTE: Mensagem enviada com sucesso',
            detalhes=f'Conexão: OK\nTítulo: {mensagem.titulo}\nCanal: {canal}\nUsuário: {usuario}\nData/Hora: {now}',
            canal=canal,
            mensagem=mensagem,
            usuario=usuario
        )
        return True, 'Mensagem enviada com sucesso'
    except Exception as e:
        Log.objects.create(
            tipo='erro',
            mensagem_texto=f'TESTE: Erro ao enviar mensagem',
            detalhes=f'Erro: {str(e)}\nTítulo: {mensagem.titulo}\nCanal: {canal}\nUsuário: {usuario}',
            canal=canal,
            mensagem=mensagem,
            usuario=usuario
        )
        return False, str(e)




