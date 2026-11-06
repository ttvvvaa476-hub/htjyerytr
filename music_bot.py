import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from yukiapi import YukiAPI

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}

class MusicState(StatesGroup):
    waiting_query = State()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать музыку", callback_data="search_music")]
    ])

def build_results_kb(results, page, total_pages):
    buttons = []
    start = page * 10
    end = start + 10
    page_items = results[start:end]

    for i, track in enumerate(page_items):
        title = track.title[:40]
        duration = track.duration
        buttons.append([InlineKeyboardButton(text=f"{title} [{duration}]", callback_data=f"play:{start + i}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{page + 1}"))
    
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎵 Привет! Я бот для поиска музыки.\n"
        "Нажми кнопку ниже, чтобы начать.",
        reply_markup=get_main_menu()
    )

@dp.callback_query(lambda c: c.data == "search_music")
async def ask_query(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(MusicState.waiting_query)
    await callback.message.edit_text("✍️ Напиши название трека или имя автора:")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🎵 Главное меню:", reply_markup=get_main_menu())
    await callback.answer()

@dp.message(MusicState.waiting_query)
async def search_music(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return

    status = await message.answer(f"🔍 Ищу: {query}...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await state.clear()

    try:
        async with YukiAPI() as yuki:
            results = await yuki.search(query, limit=10)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка поиска: {str(e)}")
        return

    if not results:
        await status.edit_text("❌ Ничего не найдено. Попробуй другой запрос.")
        return

    user_id = message.from_user.id
    search_cache[user_id] = results

    total_pages = 1  # yukiapi отдаёт до 10 за раз, но можно и больше
    await status.edit_text(
        f"🎶 Результаты по запросу «{query}»:",
        reply_markup=build_results_kb(results, 0, total_pages)
    )

@dp.callback_query(lambda c: c.data.startswith("page:"))
async def paginate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in search_cache:
        await callback.answer("Поиск устарел, начни заново.")
        return
    
    page = int(callback.data.split(":")[1])
    entries = search_cache[user_id]
    total_pages = 1
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=build_results_kb(entries, page, total_pages)
        )
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("play:"))
async def download_track(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in search_cache:
        await callback.answer("Поиск устарел.")
        return
    
    idx = int(callback.data.split(":")[1])
    entries = search_cache[user_id]
    if idx >= len(entries):
        await callback.answer("Трек не найден.")
        return
    
    track = entries[idx]
    
    await callback.message.edit_text(f"⏳ Скачиваю: {track.title}...")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_audio")
    await callback.answer()

    try:
        async with YukiAPI() as yuki:
            # yukiapi скачивает по названию или ссылке
            file_path = await yuki.download(track.link, type="audio", output_dir=DOWNLOAD_DIR)
        
        await callback.message.answer_audio(
            audio=types.FSInputFile(file_path),
            title=track.title,
            performer="Music"
        )
        await callback.message.delete()
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка скачивания: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
