from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message, LabeledPrice, PreCheckoutQuery

API_TOKEN = "8788609939:AAGKxMowULnkYPoFbu7nrr9ZBFLFSBF_br8"
ADMIN_ID = 7959524856

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AnswerState(StatesGroup):
    waiting_for_reply = State()

ACTIVE_CHATS = {}
BLACKLIST = {}

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("id_"):
        recipient_id = int(args[1].replace("id_", ""))
        await state.update_data(recipient_id=recipient_id)
        await message.answer("💬 Введите текст анонимного сообщения:")
    else:
        my_link = f"https://t.me/{(await bot.get_me()).username}?start=id_{message.from_user.id}"
        await message.answer(f"Привет! Вот твоя ссылка для анонимных вопросов:\n{my_link}")

@dp.message(F.text & ~F.text.startswith("/"))
async def send_anon_message(message: Message, state: FSMContext):
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    sender_id = message.from_user.id

    if not recipient_id:
        await message.answer("Сначала перейдите по ссылке для отправки анонимного сообщения.")
        return

    if recipient_id in BLACKLIST and sender_id in BLACKLIST[recipient_id]:
        await message.answer("❌ Вы заблокированы этим пользователем и не можете отправлять ему сообщения.")
        await state.clear()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{sender_id}"),
            InlineKeyboardButton(text="👁 Узнать автора (10 ⭐)", callback_data=f"reveal_{sender_id}")
        ],
        [
            InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_{sender_id}")
        ]
    ])
    
    await bot.send_message(
        chat_id=recipient_id,
        text=f"📩 **Новое анонимное сообщение:**\n\n{message.text}",
        reply_markup=keyboard
    )

    await message.answer("✅ Ваше сообщение успешно отправлено анонимно!")
    await state.clear()

@dp.callback_query(F.data.startswith("reply_"))
async def process_reply_button(callback: CallbackQuery, state: FSMContext):
    target_user_id = int(callback.data.split("_")[1])
    ACTIVE_CHATS[callback.from_user.id] = target_user_id
    await callback.message.answer("✍️ Напишите ваш ответ на это анонимное сообщение:")
    await callback.answer()
    await state.set_state(AnswerState.waiting_for_reply)

@dp.message(AnswerState.waiting_for_reply, F.text)
async def send_reply_to_anon(message: Message, state: FSMContext):
    owner_id = message.from_user.id
    target_user_id = ACTIVE_CHATS.get(owner_id)
    
    if target_user_id:
        if owner_id in BLACKLIST and target_user_id in BLACKLIST[owner_id]:
            await message.answer("Невозможно отправить: пользователь заблокирован.")
        else:
            await bot.send_message(
                chat_id=target_user_id,
                text=f"📨 **Ответ на ваше анонимное сообщение:**\n\n{message.text}"
            )
            await message.answer("✅ Ответ успешно отправлен!")
        
        ACTIVE_CHATS.pop(owner_id, None)
        await state.clear()
    else:
        await message.answer("Ошибка сессии. Попробуйте нажать кнопку «Ответить» заново.")
        await state.clear()

@dp.callback_query(F.data.startswith("reveal_"))
async def process_reveal_button(callback: CallbackQuery):
    sender_id = int(callback.data.split("_")[1])
    recipient_id = callback.from_user.id
    
    if recipient_id == ADMIN_ID:
        try:
            user_info = await bot.get_chat(sender_id)
            username = f"@{user_info.username}" if user_info.username else "нет юзернейма"
            await callback.message.answer(f"👑 **Админ-режим:** Автор этого сообщения — {user_info.full_name} (ID: `{sender_id}`, {username})")
        except Exception:
            await callback.message.answer(f"👑 **Админ-режим:** ID автора: `{sender_id}`")
        await callback.answer()
    else:
        await bot.send_invoice(
            chat_id=recipient_id,
            title="Раскрытие автора",
            description="Узнайте, кто отправил вам это анонимное сообщение.",
            payload=f"reveal_user_{sender_id}",
            currency="XTR",
            prices=[LabeledPrice(label="Узнать автора", amount=10)]
        )
        await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("reveal_user_"):
        sender_id = int(payload.split("_2"))
        try:
            user_info = await bot.get_chat(sender_id)
            username = f"@{user_info.username}" if user_info.username else "нет юзернейма"
            await message.answer(f"👁 **Аноним рассекречен!**\n\nИмя: {user_info.full_name}\nЮзернейм: {username}\nID: `{sender_id}`")
        except Exception:
            await message.answer(f"👁 ID отправителя: `{sender_id}`")

@dp.callback_query(F.data.startswith("block_"))
async def process_block_button(callback: CallbackQuery):
    sender_id = int(callback.data.split("_")[1])
    recipient_id = callback.from_user.id
    
    if recipient_id not in BLACKLIST:
        BLACKLIST[recipient_id] = set()
    
    BLACKLIST[recipient_id].add(sender_id)
    
    await callback.message.answer("🚫 Отправитель успешно заблокирован. Больше он не сможет прислать вам сообщения.")
    await callback.answer()

if __name__ == "__main__":
    import asyncio
    async def main():
        print("Бот запущен на Railway!")
        await dp.start_polling(bot)
    asyncio.run(main())
  
