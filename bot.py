from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
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

# Для веб-авторизации
auth_code = None
auth_password = None
code_event = asyncio.Event()
password_event = asyncio.Event()

# HTML страница для ввода кода
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auth</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; background: #1a1a2e; color: white; }
        input { padding: 15px; font-size: 20px; width: 300px; margin: 10px; border-radius: 10px; border: none; }
        button { padding: 15px 30px; font-size: 20px; background: #00d2ff; color: white; border: none; border-radius: 10px; cursor: pointer; }
        button:hover { background: #0088cc; }
    </style>
</head>
<body>
    <h1>🤖 Telegram Auth</h1>
    <h2 id="status">Введите код подтверждения</h2>
    <input type="text" id="code" placeholder="Код из Telegram">
    <br>
    <button onclick="submitCode()">Отправить код</button>
    <script>
        async function submitCode() {
            const code = document.getElementById('code').value;
            const response = await fetch('/code?code=' + code);
            const text = await response.text();
            document.getElementById('status').innerText = text;
            if (text.includes('успешно') || text.includes('Waiting')) {
                document.getElementById('status').style.color = '#00ff00';
            }
        }
    </script>
</body>
</html>
"""

HTML_PASSWORD = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Auth</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; background: #1a1a2e; color: white; }
        input { padding: 15px; font-size: 20px; width: 300px; margin: 10px; border-radius: 10px; border: none; }
        button { padding: 15px 30px; font-size: 20px; background: #00d2ff; color: white; border: none; border-radius: 10px; cursor: pointer; }
        button:hover { background: #0088cc; }
    </style>
</head>
<body>
    <h1>🔐 Облачный пароль</h1>
    <h2 id="status">Введите ваш облачный пароль</h2>
    <input type="password" id="password" placeholder="Пароль">
    <br>
    <button onclick="submitPassword()">Отправить</button>
    <script>
        async function submitPassword() {
            const password = document.getElementById('password').value;
            const response = await fetch('/password?password=' + password);
            const text = await response.text();
            document.getElementById('status').innerText = text;
        }
    </script>
</body>
</html>
"""

async def handle_health(request):
    return web.Response(text="Bot is running!")

async def handle_code(request):
    global auth_code
    code = request.query.get('code', '')
    if code:
        auth_code = code
        code_event.set()
        return web.Response(text="✅ Код получен! Можно закрыть страницу.")
    return web.Response(text="❌ Код не указан")

async def handle_password(request):
    global auth_password
    password = request.query.get('password', '')
    if password:
        auth_password = password
        password_event.set()
        return web.Response(text="✅ Пароль получен! Можно закрыть страницу.")
    return web.Response(text="❌ Пароль не указан")

async def auth_page(request):
    if 'password' in request.url.path:
        return web.Response(text=HTML_PASSWORD, content_type='text/html')
    return web.Response(text=HTML_PAGE, content_type='text/html')

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/code', handle_code)
    app.router.add_get('/password', handle_password)
    app.router.add_get('/auth', auth_page)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP сервер запущен на порту {PORT}")
    print(f"🌐 Страница авторизации: http://0.0.0.0:{PORT}/auth")

async def phone_code_callback():
    """Кастомная функция для получения кода через веб"""
    global code_event
    code_event.clear()
    print("⏳ Ожидание кода через веб-интерфейс...")
    print(f"🌐 Откройте /auth на вашем сервере и введите код")
    await code_event.wait()
    return auth_code

async def password_callback():
    """Кастомная функция для получения пароля через веб"""
    global password_event
    password_event.clear()
    print("⏳ Ожидание облачного пароля через веб-интерфейс...")
    await password_event.wait()
    return auth_password

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
    await event.reply(
        "👋 **Юзербот для рассылки сообщений**\n\n"
        "**Основные команды:**\n"
        "• `/send чаты | сообщение` - Одиночная отправка\n"
        "• `/multi чаты | сообщение1 ;; сообщение2` - Несколько сообщений\n"
        "• `/interval чаты | интервал_сек | сообщение1 ;; сообщение2` - С интервалом\n"
        "• `/repeat чаты | интервал_сек | повторы | сообщение1 ;; сообщение2` - Повторять\n"
        "• `/stop task_id` - Остановить задачу\n"
        "• `/tasks` - Список активных задач\n"
        "• `/help` - Подробная справка\n\n"
        "**Примеры:**\n"
        "`/send @user1 @user2 | Привет!`\n"
        "`/multi @user1 | Сообщение 1 ;; Сообщение 2 ;; Сообщение 3`\n"
        "`/interval @user1 | 5 | Сообщение 1 ;; Сообщение 2`\n"
        "`/repeat @user1 | 60 | 10 | Привет ;; Как дела?`"
    )

@bot.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    await event.reply(
        "📚 **Подробная справка**\n\n"
        "**1. /send - Отправка одного сообщения**\n"
        "`/send @user1 @user2 | Привет всем!`\n"
        "Отправляет одно сообщение во все указанные чаты\n\n"
        "**2. /multi - Несколько сообщений подряд**\n"
        "`/multi @user1 @user2 | Сообщение 1 ;; Сообщение 2 ;; Сообщение 3`\n"
        "Отправляет все сообщения в каждый чат. Разделитель `;;`\n\n"
        "**3. /interval - Сообщения с паузой**\n"
        "`/interval @user1 | 10 | Сообщение 1 ;; Сообщение 2 ;; Сообщение 3`\n"
        "Пауза 10 секунд между отправкой каждого сообщения\n\n"
        "**4. /repeat - Периодическая отправка**\n"
        "`/repeat @user1 @user2 | 3600 | 5 | Привет ;; Как дела?`\n"
        "Повторяет отправку 5 раз с интервалом 3600 сек (1 час)\n\n"
        "**5. /stop - Остановка задачи**\n"
        "`/stop task_id`\n\n"
        "**6. /tasks - Просмотр активных задач**\n"
        "`/tasks`\n\n"
        "**Форматы чатов:**\n"
        "• @username - пользователь\n"
        "• @channel - канал\n"
        "• -123456789 - группа (ID)\n"
        "• 123456789 - пользователь (ID)"
    )

@bot.on(events.NewMessage(pattern='/send'))
async def send_handler(event):
    try:
        command = event.message.text[len('/send '):]
        if '|' not in command:
            await event.reply("❌ Формат: /send чаты | сообщение")
            return
        
        chats_part, message = command.split('|', 1)
        chat_ids = [c.strip() for c in chats_part.strip().split() if c.strip()]
        
        if not chat_ids or not message.strip():
            await event.reply("❌ Укажите чаты и сообщение")
            return
        
        await event.reply(f"🔄 Отправляю в {len(chat_ids)} чатов...")
        
        results = []
        for chat_id in chat_ids:
            success, result = await send_message_to_chat(chat_id, message.strip())
            results.append(result)
        
        await event.reply(f"📊 Результаты:\n" + "\n".join(results))
        
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/multi'))
async def multi_handler(event):
    try:
        command = event.message.text[len('/multi '):]
        if '|' not in command:
            await event.reply("❌ Формат: /multi чаты | сообщение1 ;; сообщение2 ;; сообщение3")
            return
        
        chats_part, messages_part = command.split('|', 1)
        chat_ids = [c.strip() for c in chats_part.strip().split() if c.strip()]
        messages = [m.strip() for m in messages_part.split(';;') if m.strip()]
        
        if not chat_ids or not messages:
            await event.reply("❌ Укажите чаты и сообщения")
            return
        
        await event.reply(f"🔄 Отправляю {len(messages)} сообщений в {len(chat_ids)} чатов...")
        result = await send_multiple_messages(chat_ids, messages)
        await event.reply(f"📊 Результаты:\n{result}")
        
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/interval'))
async def interval_handler(event):
    try:
        command = event.message.text[len('/interval '):]
        parts = command.split('|')
        
        if len(parts) != 3:
            await event.reply("❌ Формат: /interval чаты | интервал_сек | сообщение1 ;; сообщение2")
            return
        
        chats_part = parts[0].strip()
        interval = int(parts[1].strip())
        messages_part = parts[2].strip()
        
        chat_ids = [c.strip() for c in chats_part.split() if c.strip()]
        messages = [m.strip() for m in messages_part.split(';;') if m.strip()]
        
        if not chat_ids or not messages:
            await event.reply("❌ Укажите чаты и сообщения")
            return
        
        await event.reply(f"⏱ Начинаю отправку с интервалом {interval} сек...")
        
        task_id = f"interval_{datetime.now().timestamp()}"
        task = asyncio.create_task(send_multiple_messages(chat_ids, messages, interval))
        active_tasks[task_id] = task
        
        await event.reply(f"✅ Задача {task_id} запущена")
        
    except ValueError:
        await event.reply("❌ Интервал должен быть числом")
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/repeat'))
async def repeat_handler(event):
    try:
        command = event.message.text[len('/repeat '):]
        parts = command.split('|')
        
        if len(parts) != 4:
            await event.reply("❌ Формат: /repeat чаты | интервал_сек | количество | сообщение1 ;; сообщение2")
            return
        
        chats_part = parts[0].strip()
        interval = int(parts[1].strip())
        repeat_count = int(parts[2].strip())
        messages_part = parts[3].strip()
        
        chat_ids = [c.strip() for c in chats_part.split() if c.strip()]
        messages = [m.strip() for m in messages_part.split(';;') if m.strip()]
        
        if not chat_ids or not messages:
            await event.reply("❌ Укажите чаты и сообщения")
            return
        
        task_id = f"repeat_{datetime.now().timestamp()}"
        task = asyncio.create_task(
            scheduled_task(task_id, chat_ids, messages, interval, repeat_count)
        )
        active_tasks[task_id] = task
        
        await event.reply(
            f"🔄 Задача {task_id} запущена\n"
            f"• Чаты: {len(chat_ids)}\n"
            f"• Сообщений: {len(messages)}\n"
            f"• Интервал: {interval} сек\n"
            f"• Повторов: {repeat_count}"
        )
        
    except ValueError:
        await event.reply("❌ Интервал и количество должны быть числами")
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    try:
        task_id = event.message.text[len('/stop '):].strip()
        
        if task_id in active_tasks:
            active_tasks[task_id].cancel()
            del active_tasks[task_id]
            await event.reply(f"✅ Задача {task_id} остановлена")
        else:
            await event.reply(f"❌ Задача {task_id} не найдена")
            
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/tasks'))
async def tasks_handler(event):
    if not active_tasks:
        await event.reply("📭 Нет активных задач")
        return
    
    tasks_list = "📋 **Активные задачи:**\n\n"
    for task_id, task in active_tasks.items():
        status = "🟢 Выполняется" if not task.done() else "🔴 Завершена"
        tasks_list += f"• `{task_id}` - {status}\n"
    
    await event.reply(tasks_list)

async def main():
    # Запускаем HTTP сервер с веб-интерфейсом авторизации
    await start_http_server()
    
    print("\n🔐 Начинаем авторизацию...")
    
    try:
        # Пробуем войти с существующей сессией
        if session_string:
            print("📱 Вход по SESSION_STRING...")
            await client.start(session_string=session_string)
        elif phone:
            print(f"📱 Вход по номеру {phone}...")
            await client.start(phone=phone)
        else:
            print("📱 Интерактивный вход...")
            # Запускаем клиент с веб-колбэками
            await client.start(
                phone=phone if phone else lambda: input('Введите номер: '),
                code_callback=phone_code_callback,
                password_callback=password_callback
            )
        
        print("✅ Юзербот успешно авторизован!")
        
        # Сохраняем сессию для будущих запусков
        me = await client.get_me()
        print(f"👤 Вошли как: {me.first_name} (@{me.username})")
        
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        print("💡 Откройте /auth на вашем сервере для ввода кода")
    
    # Запуск бота
    print("\n🤖 Запускаем бота...")
    await bot.start(bot_token=bot_token)
    print("✅ Бот запущен!")
    print(f"\n🌐 Сервер: http://0.0.0.0:{PORT}")
    print(f"🔑 Авторизация: http://0.0.0.0:{PORT}/auth")
    print("\n📋 Команды для бота в Telegram:")
    print("  /start - Начать работу")
    print("  /send - Отправить сообщение")
    print("  /multi - Несколько сообщений")
    print("  /interval - С интервалом")
    print("  /repeat - Повторять")
    print("  /tasks - Активные задачи")
    print("  /stop - Остановить задачу")
    print("  /help - Справка\n")
    
    await asyncio.gather(
        client.run_until_disconnected(),
        bot.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())