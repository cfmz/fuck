from telethon import TelegramClient, events
import asyncio
import os
from datetime import datetime, timedelta
from aiohttp import web

# Данные
api_id = int(os.getenv('API_ID', '22376342'))
api_hash = os.getenv('API_HASH', 'f623dc4ae2b015463cfde7874ab0f270')
bot_token = os.getenv('BOT_TOKEN', '8993460481:AAF_v-ivofnXgweAoItsefcLxoMgxClzOJA')
session_string = os.getenv('SESSION_STRING')
PORT = int(os.getenv('PORT', 10000))

# Клиенты
client = TelegramClient('user_session', api_id, api_hash)
bot = TelegramClient('bot_session', api_id, api_hash)

# Хранилище задач
active_tasks = {}

# HTTP сервер
async def handle(request):
    return web.Response(text="Bot is running!")

async def send_message_to_chat(chat_id, message):
    try:
        chat = await client.get_entity(chat_id.strip())
        await client.send_message(chat, message)
        return True, f"✅ Отправлено в {chat_id}"
    except Exception as e:
        return False, f"❌ Ошибка {chat_id}: {e}"

async def send_multiple_messages(chat_ids, messages, interval=0):
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
    count = 0
    while True:
        if repeat_count and count >= repeat_count:
            break
        count += 1
        for msg in messages:
            for chat_id in chat_ids:
                await send_message_to_chat(chat_id, msg)
                await asyncio.sleep(0.5)
        if repeat_count and count >= repeat_count:
            break
        await asyncio.sleep(interval)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply(
        "👋 Юзербот для рассылки\n\n"
        "/send @user | текст\n"
        "/multi @user | текст1 ;; текст2\n"
        "/interval @user | 10 | текст1 ;; текст2\n"
        "/repeat @user | 60 | 5 | текст1 ;; текст2\n"
        "/tasks - активные задачи\n"
        "/stop task_id - остановить\n"
        "/help - справка"
    )

@bot.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    await event.reply(
        "📚 Справка:\n\n"
        "/send @user1 @user2 | Привет!\n"
        "/multi @user | Сооб1 ;; Сооб2 ;; Сооб3\n"
        "/interval @user | 5 | Сооб1 ;; Сооб2\n"
        "/repeat @user | 3600 | 10 | Сооб1 ;; Сооб2\n\n"
        "Чаты: @username, ID чата"
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
        await event.reply("📊 Результаты:\n" + "\n".join(results))
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/multi'))
async def multi_handler(event):
    try:
        command = event.message.text[len('/multi '):]
        if '|' not in command:
            await event.reply("❌ Формат: /multi чаты | сообщение1 ;; сообщение2")
            return
        chats_part, messages_part = command.split('|', 1)
        chat_ids = [c.strip() for c in chats_part.strip().split() if c.strip()]
        messages = [m.strip() for m in messages_part.split(';;') if m.strip()]
        if not chat_ids or not messages:
            await event.reply("❌ Укажите чаты и сообщения")
            return
        await event.reply(f"🔄 Отправляю {len(messages)} сообщений...")
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
            await event.reply("❌ Формат: /interval чаты | сек | сообщение1 ;; сообщение2")
            return
        chats_part = parts[0].strip()
        interval = int(parts[1].strip())
        messages_part = parts[2].strip()
        chat_ids = [c.strip() for c in chats_part.split() if c.strip()]
        messages = [m.strip() for m in messages_part.split(';;') if m.strip()]
        if not chat_ids or not messages:
            await event.reply("❌ Укажите чаты и сообщения")
            return
        task_id = f"interval_{datetime.now().timestamp()}"
        task = asyncio.create_task(send_multiple_messages(chat_ids, messages, interval))
        active_tasks[task_id] = task
        await event.reply(f"✅ Задача {task_id} запущена (интервал {interval}с)")
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
            await event.reply("❌ Формат: /repeat чаты | сек | кол-во | сообщение1 ;; сообщение2")
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
        task = asyncio.create_task(scheduled_task(task_id, chat_ids, messages, interval, repeat_count))
        active_tasks[task_id] = task
        await event.reply(f"🔄 Задача {task_id} запущена\nЧатов: {len(chat_ids)}\nИнтервал: {interval}с\nПовторов: {repeat_count}")
    except ValueError:
        await event.reply("❌ Числа для интервала и повторов")
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
            await event.reply(f"❌ Задача не найдена")
    except Exception as e:
        await event.reply(f"❌ Ошибка: {e}")

@bot.on(events.NewMessage(pattern='/tasks'))
async def tasks_handler(event):
    if not active_tasks:
        await event.reply("📭 Нет активных задач")
        return
    tasks_list = "📋 Активные задачи:\n\n"
    for task_id, task in active_tasks.items():
        status = "🟢" if not task.done() else "🔴"
        tasks_list += f"{status} {task_id}\n"
    await event.reply(tasks_list)

async def main():
    # HTTP сервер
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/health', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP на порту {PORT}")

    # Вход в Telegram
    if session_string:
        await client.start(session_string=session_string)
    else:
        await client.start()
    
    print("✅ Юзербот запущен")
    
    # Запуск бота
    await bot.start(bot_token=bot_token)
    print("✅ Бот запущен")
    
    await asyncio.gather(
        client.run_until_disconnected(),
        bot.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())