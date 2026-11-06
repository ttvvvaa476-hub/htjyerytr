import asyncio
import os
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}

class MusicState(StatesGroup):
    waiting_query = State()

# Настройки для БЫСТРОГО поиска (без скачивания)
ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': 'in_playlist', # Самая быстрая настройка
    'skip_download': True,
    'playlistend': 10,
    'socket_timeout': 15,
    'cachedir': False,
}

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать музыку", callback_data="search_music")]
    ])

def build_results_kb(results, page, total_pages):
    buttons = []
    start = page * 10
    page_items = results[start:start+10]

    for i, track in enumerate(page_items):
        title = track.get('title', 'Без названия')[:40]
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
    await message.answer("🎵 Бот для поиска музыки.", reply_markup=get_main_menu())

@dp.callback_query(lambda c: c.data == "search_music")
async def ask_query(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(MusicState.waiting_query)
    await callback.message.edit_text("✍️ Напиши название трека:")
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
        # Ищем на YouTube (поиск быстрый)
        search_url = f"ytsearch10:{query}"
        loop = asyncio.get_event_loop()
        
        # Запускаем в отдельном потоке, чтобы не вешать бота
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_url, download=False))
            entries = info.get('entries', [])
            
    except Exception as e:
        await status.edit_text(f"❌ Ошибка поиска: {str(e)}")
        return

    if not entries:
        await status.edit_text("❌ Ничего не найдено.")
        return

    user_id = message.from_user.id
    search_cache[user_id] = entries
    total_pages = (len(entries) + 9) // 10
    
    await status.edit_text(
        f"🎶 Результаты:",
        reply_markup=build_results_kb(entries, 0, total_pages)
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
        await callback.message.edit_reply_markup(reply_markup=build_results_kb(entries, page, total_pages))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("play:"))
async def send_track(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in search_cache:
        await callback.answer("Поиск устарел.")
        return
    
    idx = int(callback.data.split(":")[1])
    entries = search_cache[user_id]
    track = entries[idx]
    
    video_url = track.get('url') or track.get('webpage_url')
    title = track.get('title', 'audio')
    
    await callback.message.edit_text(f"⏳ Готовлю: {title}...")
    await callback.answer()

    try:
        # Получаем прямую ссылку на аудио (без скачивания файла на сервер)
        ydl_opts_stream = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts_stream) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(video_url, download=False))
            stream_url = info.get('url')
            
        if not stream_url:
            raise ValueError("Не удалось получить ссылку на аудио")

        # Отправляем ссылку в Telegram (он сам скачает и пришлет файл)
        await callback.message.answer_audio(
            audio=stream_url,  # Передаем ссылку, а не файл
            title=title,
            performer=track.get('uploader', 'Music')
        )
        await callback.message.delete()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
