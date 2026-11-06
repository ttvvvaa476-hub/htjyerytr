import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from soundcloud import SoundCloud

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализируем клиент SoundCloud (без токена, только для поиска)
sc = SoundCloud()

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
        # В soundcloud-v2 поля называются title и user.username
        artist = track.user.username if track.user else "Unknown"
        title = f"{artist} - {track.title}"[:40]
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
    await message.answer("🎵 Бот для поиска музыки на SoundCloud.", reply_markup=get_main_menu())

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

    status = await message.answer(f"🔍 Ищу на SoundCloud: {query}...")
    await state.clear()

    try:
        # Ищем треки (limit=20 для пагинации)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: sc.search_tracks(query, limit=20))
    except Exception as e:
        await status.edit_text(f"❌ Ошибка поиска: {str(e)}")
        return

    if not results:
        await status.edit_text("❌ Ничего не найдено. Попробуй другой запрос.")
        return

    user_id = message.from_user.id
    search_cache[user_id] = results

    total_pages = (len(results) + 9) // 10
    await status.edit_text(
        f"🎶 Результаты по запросу «{query}»:",
        reply_markup=build_results_kb(results, 0, total_pages)
    )

@dp.callback_query(lambda c: c.data.startswith("page:"))
async def paginate(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in search_cache:
        await callback.answer("Поиск устарел.")
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
    artist = track.user.username if track.user else "Unknown"
    title = track.title
    
    await callback.message.edit_text(f"⏳ Скачиваю: {artist} - {title}...")
    await callback.answer()

    try:
        # Получаем прямую ссылку на стрим (MP3)
        # Библиотека soundcloud-v2 умеет получать transcoding URL
        stream_url = None
        
        # Пытаемся получить progressive stream (обычный MP3)
        if track.media and track.media.transcodings:
            for trans in track.media.transcodings:
                if trans.format.protocol == "progressive":
                    # Получаем прямой URL через API
                    stream_info = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: sc.get_stream_url(trans.url)
                    )
                    if stream_info and stream_info.url:
                        stream_url = stream_info.url
                        break
        
        if not stream_url:
            raise ValueError("Не удалось найти MP3-поток для этого трека")

        filename = os.path.join(DOWNLOAD_DIR, f"{user_id}_{idx}.mp3")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(stream_url) as resp:
                if resp.status != 200:
                    raise ValueError(f"Ошибка скачивания (статус {resp.status})")
                with open(filename, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(1024 * 64):
                        f.write(chunk)

        await callback.message.answer_audio(
            audio=types.FSInputFile(filename),
            title=title,
            performer=artist
        )
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    finally:
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
