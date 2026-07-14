from telethon import TelegramClient, events
import asyncio
import os
from datetime import datetime, timedelta
from aiohttp import web

# Данные из переменных окружения
api_id = int(os.getenv('API_ID', '22376342'))
api_hash = os.getenv('API_HASH', 'f623dc4ae2b015463cfde7874ab0f270')
bot_token = os.getenv('BOT_TOKEN', '8993460481:AAF_v-ivofnXgweAoItsefcLxoMgxClzOJA')
phone = os.getenv('PHONE')
session_string = os.getenv('SESSION_STRING')
PORT = int(os.getenv('PORT', 10000))

# Клиенты
client = TelegramClient('user_session', api_id, api_hash)
bot = TelegramClient('bot_session', api_id, api_hash)

# Хранилище активных задач
active_tasks = {}

# HTTP сервер для Render Web Service
async def handle_health(request):
    return web.Response(text="Bot is running!")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP сервер запущен на порту {PORT}")

async def send_message_to_chat(chat_id, message):
    """Отправляет одно сообщение в чат"""
    try:
        chat = await client.get_entity(chat_id.strip())
        await client.send_message(chat, message)
        return True, f"✅ Отправлено в {chat_id}"
    except Exception as e:
        return False, f"❌ Ошибка {chat_id}: {e}"

async def send_multiple_messages(chat_ids, messages, interval=0):
    """Отправляет несколько сообщений в чаты с интервалом"""
    results = []
    
    if interval > 0:
        for msg in messages:
            for chat_id in chat_ids:
                success, result = await send_message_to_chat(chat_id, msg)
                results.append(result)
            if msg != messages[-1]:
                await asyncio.sleep(interval)
    else:
        for chat_id in chat_ids:
            for msg in messages:
                success, result = await send_message_to_chat(chat_id, msg)
                results.append(result)
    
    return "\n".join(results)

async def scheduled_task(task_id, chat_ids, messages, interval, repeat_count=None):
    """Задача для периодической отправки"""
    count = 0
    while True:
        if repeat_count and count >= repeat_count:
            break
        
        count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        for msg in messages:
            for chat_id in chat_ids:
                await send_message_to_chat(chat_id, f"{msg}")
                await asyncio.sleep(0.5)
        
        if repeat_count and count >= repeat_count:
            break
            
        await asyncio.sleep(interval)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    help_text = """
👋 **Юзербот для рассылки сообщений**

**Основные команды:**
• `/send чаты | сообщение` - Одиночная отправка
• `/multi чаты | сообщение1 ;; сообщение2 ;; сообщение3` - Несколько сообщений
• `/interval чаты | интервал_сек | сообщение1 ;; сообщение2` - С интервалом
• `/repeat чаты | интервал_сек | повторы | сообщение1 ;; сообщение2` - Повторять
• `/stop task_id` - Остановить задачу
• `/tasks` - Список активных задач
• `/help` - Подробная справка

**Примеры:**
`/send @user1 @user2 | Привет!`
`/multi @user1 | Сообщение 1 ;; Сообщение 2 ;; Сообщение 3`
`/interval @user1 | 5 | Сообщение 1 ;; Сообщение 2`
`/repeat @user1 | 60 | 10 | Привет ;; Как дела?`
    """
    await event.reply(help_text)

@bot.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    help_text = """
📚 **Подробная справка**

**1. /send - Отправка одного сообщения**