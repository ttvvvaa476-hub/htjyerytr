import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from YouTubeMusic.Search import Search
from YouTubeMusic.Stream import get_stream

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ПУТЬ К ФАЙЛУ С КУКАМИ (создай его и загрузи на GitHub)
COOKIES_PATH = "cookies.txt"

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
        title = track.get('title', 'Без названия')[:40]
        # У YouTubeMusic может не быть длительности в результатах поиска
        buttons.append([InlineKeyboardButton(text=title, callback_data=f"play:{start + i}")])

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
    await state.clear()

    try:
        results = await Search(query, limit=20)
        # Библиотека возвращает словарь с ключом main_results
        entries = results.get("main_results", []) if results else []
    except Exception as e:
        await status.edit_text(f"❌ Ошибка поиска: {str(e)}")
        return

    if not entries:
        await status.edit_text("❌ Ничего не найдено. Попробуй другой запрос.")
        return

    user_id = message.from_user.id
    search_cache[user_id] = entries

    total_pages = (len(entries) + 9) // 10
    await status.edit_text(
        f"🎶 Результаты по запросу «{query}»:",
        reply_markup=build_results_kb(entries, 0, total_pages)
    )

@dp.callback_query(lambda c: c.data.startswith("page:"))
async def paginate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in search_cache:
        await callback.answer("Поиск устарел, начни заново.")
        return
    
    page = int(callback.data.split(":")[1])
    entries = search_cache[user_id]
    total_pages = (len(entries) + 9) // 10
    
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
    # В YouTubeMusic ссылка на трек обычно лежит в поле url или webpage_url
    track_url = track.get('url') or track.get('webpage_url')
    title = track.get('title', 'audio')
    
    await callback.message.edit_text(f"⏳ Скачиваю: {title}...")
    await callback.answer()

    try:
        # Получаем прямую ссылку на аудиопоток
        stream_url = await get_stream(track_url, COOKIES_PATH)
        
        # Скачиваем файл по ссылке
        import aiohttp
        filename = os.path.join(DOWNLOAD_DIR, f"{idx}.mp3")
        async with aiohttp.ClientSession() as session:
            async with session.get(stream_url) as resp:
                with open(filename, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(1024):
                        f.write(chunk)

        await callback.message.answer_audio(
            audio=types.FSInputFile(filename),
            title=title,
            performer="YouTube Music"
        )
        await callback.message.delete()
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка скачивания: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
