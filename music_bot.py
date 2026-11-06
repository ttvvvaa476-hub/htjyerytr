import asyncio
import os
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}

class MusicState(StatesGroup):
    waiting_query = State()

ydl_search_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': True,
    'skip_download': True,
    'ignoreerrors': True,
    'playlistend': 10,
    'socket_timeout': 10,
    'cachedir': False,
}

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать музыку", callback_data="search_music")]
    ])

def build_results_kb(results, page, total_pages):
    buttons = []
    start = page * 10
    end = start + 10
    page_items = results[start:end]

    for i, item in enumerate(page_items):
        title = item.get('title', 'Без названия')[:40]
        duration = item.get('duration', 0)
        dur_str = f"{duration // 60}:{duration % 60:02d}" if duration else "?:??"
        buttons.append([InlineKeyboardButton(text=f"{title} [{dur_str}]", callback_data=f"sc_play:{start + i}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sc_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"sc_page:{page + 1}"))
    
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎵 Привет! Я бот для поиска музыки на SoundCloud.\n"
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

    # Отправляем сообщение с крутящимися часиками (action="typing" или просто эмодзи)
    status = await message.answer(f"🔍 Ищу на SoundCloud: {query}...\n⌛ Пожалуйста, подожди.")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await state.clear()

    search_url = f"scsearch10:{query}"
    try:
        with yt_dlp.YoutubeDL(ydl_search_opts) as ydl:
            # Запускаем поиск в отдельном потоке, чтобы не блокировать бота
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_url, download=False))
            entries = info.get('entries', [])
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

@dp.callback_query(lambda c: c.data.startswith("sc_page:"))
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

@dp.callback_query(lambda c: c.data.startswith("sc_play:"))
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
    url = track.get('url') or track.get('webpage_url')
    title = track.get('title', 'audio')
    
    await callback.message.edit_text(f"⏳ Скачиваю: {title}...\n⌛ Подожди немного.")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_audio")
    await callback.answer()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'cachedir': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3').replace('.opus', '.mp3')
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp3', '.m4a', '.webm']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break

        await callback.message.answer_audio(
            audio=types.FSInputFile(filename),
            title=info.get('title', title),
            performer=info.get('uploader', 'SoundCloud')
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
