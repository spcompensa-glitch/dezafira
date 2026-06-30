import os
import threading
import telebot
from modules.database import get_db_channels

# 1. Carregar variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = None

def init_telegram_bot(on_chat_message_cb, on_produce_command_cb):
    """
    Inicializa o bot em segundo plano (background thread).
    Recebe dois callbacks do server.py para processar o chat do Hermes e disparar a esteira.
    """
    global bot
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram Bot] ⚠️ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não definidos nas variáveis. Bot inativo.")
        return

    try:
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        print(f"[Telegram Bot] Bot inicializado com sucesso para o Chat ID: {TELEGRAM_CHAT_ID}")
        
        # Filtro de segurança para responder apenas ao dono (Jonatas)
        def is_owner(message):
            return str(message.chat.id) == str(TELEGRAM_CHAT_ID)

        @bot.message_handler(commands=['start', 'ajuda'])
        def send_welcome(message):
            if not is_owner(message):
                return
            welcome_text = (
                "🤖 *Olá, Jonatas! Eu sou o Hermes, seu assistente da Dezafira.*\n\n"
                "Estou pronto para gerenciar a Fábrica de Canais direto do seu Telegram. Comandos disponíveis:\n"
                "👉 `/canais` - Lista todos os seus canais e status de monetização.\n"
                "👉 `/produzir [tema]` - Dispara a esteira de IA e gera um vídeo automático.\n"
                "👉 Qualquer texto - Conversa direto comigo usando inteligência artificial."
            )
            bot.reply_to(message, welcome_text, parse_mode="Markdown")

        @bot.message_handler(commands=['canais'])
        def list_channels(message):
            if not is_owner(message):
                return
            try:
                channels = get_db_channels()
                if not channels:
                    bot.reply_to(message, "ℹ️ Nenhum canal cadastrado no momento.")
                    return
                
                response = "📈 *Canais Dezafira Ativos:*\n\n"
                for idx, c in enumerate(channels, 1):
                    emoji = "📈" if c['monetization_step'] == "publishing" else "🔥" if c['monetization_step'] == "viral" else "⚙️"
                    response += f"{idx}. *{c['name']}* ({c['lang']}) - {c['nicho']}\n"
                    response += f"   Status: `{c['status']}` | Progresso: `{c['monetization_step'].upper()}`\n\n"
                bot.reply_to(message, response, parse_mode="Markdown")
            except Exception as e:
                bot.reply_to(message, f"❌ Erro ao buscar canais: {str(e)}")

        @bot.message_handler(commands=['produzir'])
        def produce_campaign(message):
            if not is_owner(message):
                return
            # Extrair o tema do comando (ex: /produzir Como vender na internet)
            parts = message.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(message, "⚠️ Por favor, especifique um tema. Exemplo: `/produzir Como monetizar no Youtube`", parse_mode="Markdown")
                return
            
            theme = parts[1]
            bot.reply_to(message, f"🚀 *Disparando a Esteira Dezafira!*\nTema: `{theme}`\nIniciando Trend Hunting...", parse_mode="Markdown")
            
            # Executar callback de produção passado pelo server.py em segundo plano
            threading.Thread(target=on_produce_command_cb, args=(theme,)).start()

        @bot.message_handler(func=lambda message: True)
        def handle_chat(message):
            if not is_owner(message):
                return
            
            user_text = message.text
            bot.send_chat_action(message.chat.id, 'typing')
            
            # Processar chat com o Hermes usando o callback
            reply_text = on_chat_message_cb(user_text)
            bot.reply_to(message, reply_text)

        # Iniciar polling em uma thread separada para não bloquear o startup do FastAPI
        def run_polling():
            bot.infinity_polling()
            
        polling_thread = threading.Thread(target=run_polling, daemon=True)
        polling_thread.start()
        
        # Enviar mensagem de ativação
        bot.send_message(TELEGRAM_CHAT_ID, "🟢 *Hermes conectado com sucesso!* Digite `/ajuda` para ver os comandos de controle da Fábrica.", parse_mode="Markdown")

    except Exception as e:
        print(f"[Telegram Bot] ❌ Falha ao iniciar bot: {str(e)}")

def send_telegram_notification(text: str):
    """
    Envia uma notificação direta no Telegram do Jonatas a partir de qualquer ponto do sistema.
    """
    global bot
    if bot and TELEGRAM_CHAT_ID:
        try:
            bot.send_message(TELEGRAM_CHAT_ID, text, parse_mode="Markdown")
        except Exception as e:
            print(f"[Telegram Bot] Falha ao enviar notificação: {str(e)}")
