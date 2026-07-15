from telethon import TelegramClient, events
import asyncio
import os
from datetime import datetime
from aiohttp import web

api_id = int(os.getenv('API_ID', '22376342'))
api_hash = os.getenv('API_HASH', 'f623dc4ae2b015463cfde7874ab0f270')
bot_token = os.getenv('BOT_TOKEN', '8993460481:AAF_v-ivofnXgweAoItsefcLxoMgxClzOJA')
PORT = int(os.getenv('PORT', 10000))

client = TelegramClient('session', api_id, api_hash)
bot = TelegramClient('bot', api_id, api_hash)
active_tasks = {}

async def handle(request):
    return web.Response(text="OK")

async def send_msg(chat_id, msg):
    try:
        chat = await client.get_entity(chat_id.strip())
        await client.send_message(chat, msg)
        return f"✅ {chat_id}"
    except Exception as e:
        return f"❌ {chat_id}: {e}"

@bot.on(events.NewMessage(pattern='/login'))
async def login(event):
    try:
        args = event.text[len('/login '):].strip()
        
        # Если просто номер - отправляем код
        if args.startswith('+') and len(args) > 5:
            phone = args
            result = await client.send_code_request(phone)
            # Сохраняем данные в сообщение
            event.client.storage = {
                'phone': phone,
                'hash': result.phone_code_hash
            }
            await event.reply("✅ Код отправлен! Введи: /login 1.2.3.4.5")
        
        # Если цифры с точками - это код
        elif '.' in args or args.isdigit():
            code = args.replace('.', '')
            await client.sign_in(
                phone=event.client.storage['phone'],
                code=code,
                phone_code_hash=event.client.storage['hash']
            )
            me = await client.get_me()
            await event.reply(f"✅ Вход выполнен: {me.first_name}")
        
        # Иначе это пароль
        else:
            password = args
            await client.sign_in(password=password)
            me = await client.get_me()
            await event.reply(f"✅ Вход выполнен: {me.first_name}")
            
    except Exception as e:
        if "password" in str(e).lower():
            await event.reply("🔐 Нужен облачный пароль: /login твойпароль")
        else:
            await event.reply(f"❌ {e}")

@bot.on(events.NewMessage(pattern='/send'))
async def send(event):
    try:
        text = event.text[len('/send '):]
        chats, msg = text.split('|', 1)
        chats = [c.strip() for c in chats.split() if c.strip()]
        res = []
        for c in chats:
            res.append(await send_msg(c, msg.strip()))
        await event.reply("\n".join(res))
    except:
        await event.reply("❌ /send @user1 @user2 | текст")

@bot.on(events.NewMessage(pattern='/multi'))
async def multi(event):
    try:
        text = event.text[len('/multi '):]
        chats, msgs = text.split('|', 1)
        chats = [c.strip() for c in chats.split() if c.strip()]
        msgs = [m.strip() for m in msgs.split(';;') if m.strip()]
        res = []
        for c in chats:
            for m in msgs:
                res.append(await send_msg(c, m))
        await event.reply("\n".join(res))
    except:
        await event.reply("❌ /multi @user | т1 ;; т2 ;; т3")

@bot.on(events.NewMessage(pattern='/interval'))
async def interval(event):
    try:
        text = event.text[len('/interval '):]
        chats, sec, msgs = text.split('|')
        chats = [c.strip() for c in chats.split() if c.strip()]
        sec = int(sec.strip())
        msgs = [m.strip() for m in msgs.split(';;') if m.strip()]
        tid = f"i_{datetime.now().timestamp()}"
        async def task():
            for m in msgs:
                for c in chats:
                    await send_msg(c, m)
                await asyncio.sleep(sec)
        active_tasks[tid] = asyncio.create_task(task())
        await event.reply(f"✅ {tid}")
    except:
        await event.reply("❌ /interval @user | 5 | т1 ;; т2")

@bot.on(events.NewMessage(pattern='/repeat'))
async def repeat(event):
    try:
        text = event.text[len('/repeat '):]
        chats, sec, count, msgs = text.split('|')
        chats = [c.strip() for c in chats.split() if c.strip()]
        sec = int(sec.strip())
        count = int(count.strip())
        msgs = [m.strip() for m in msgs.split(';;') if m.strip()]
        tid = f"r_{datetime.now().timestamp()}"
        async def task():
            for i in range(count):
                for m in msgs:
                    for c in chats:
                        await send_msg(c, m)
                if i < count - 1:
                    await asyncio.sleep(sec)
        active_tasks[tid] = asyncio.create_task(task())
        await event.reply(f"✅ {tid} | чатов:{len(chats)} | интервал:{sec}с | повторов:{count}")
    except:
        await event.reply("❌ /repeat @user | 60 | 5 | т1 ;; т2")

@bot.on(events.NewMessage(pattern='/stop'))
async def stop(event):
    try:
        tid = event.text[len('/stop '):].strip()
        if tid in active_tasks:
            active_tasks[tid].cancel()
            del active_tasks[tid]
            await event.reply(f"✅ {tid} стоп")
        else:
            await event.reply("❌ Не найдено")
    except:
        await event.reply("❌ /stop id")

@bot.on(events.NewMessage(pattern='/tasks'))
async def tasks(event):
    if not active_tasks:
        await event.reply("Нет задач")
        return
    t = "Задачи:\n"
    for tid, task in active_tasks.items():
        t += f"{'🟢' if not task.done() else '🔴'} {tid}\n"
    await event.reply(t)

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    
    await bot.start(bot_token=bot_token)
    print("✅ Готов!")
    
    await bot.run_until_disconnected()

asyncio.run(main())