from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from aiohttp import web
import asyncio
import random
import aiosqlite
import os

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
ADMIN_ID = 8121754585
DB_PATH = "/app/data/bot.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()

users_data = {}
promocodes = {}
mines_games = {}
chicken_games = {}
crash_games = {}
blackjack_games = {}
withdraw_pending = {}

class MinesState(StatesGroup):
    waiting_bet = State()

class BuyState(StatesGroup):
    waiting_amount = State()

class ChickenState(StatesGroup):
    waiting_bet = State()

class CrashState(StatesGroup):
    waiting_bet = State()

class BlackjackState(StatesGroup):
    waiting_bet = State()

class WithdrawState(StatesGroup):
    waiting_username = State()

class AdminState(StatesGroup):
    waiting_give = State()
    waiting_take = State()
    waiting_broadcast = State()
    waiting_promo = State()
    waiting_promo_activate = State()
    waiting_promo_delete = State()

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
])

games_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💣 Мины", callback_data="mines")],
    [InlineKeyboardButton(text="🐔 Курица", callback_data="chicken")],
    [InlineKeyboardButton(text="📈 Краш", callback_data="crash")],
    [InlineKeyboardButton(text="🃏 Блэкджек", callback_data="blackjack")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
])

bet_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="games")]
])

end_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back")]
])

withdraw_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="15⭐ — 150 Germ", callback_data="wd_150")],
    [InlineKeyboardButton(text="25⭐ — 250 Germ", callback_data="wd_250")],
    [InlineKeyboardButton(text="50⭐ — 500 Germ", callback_data="wd_500")],
    [InlineKeyboardButton(text="100⭐ — 1000 Germ", callback_data="wd_1000")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
])

withdraw_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="withdraw")]
])

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
    [InlineKeyboardButton(text="💰 Выдать Germ", callback_data="admin_give")],
    [InlineKeyboardButton(text="💸 Забрать Germ", callback_data="admin_take")],
    [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promo")],
    [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
    [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
])

promo_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Создать промокод", callback_data="promo_create")],
    [InlineKeyboardButton(text="📋 Список промокодов", callback_data="promo_list")],
    [InlineKeyboardButton(text="🗑 Удалить промокод", callback_data="promo_delete")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
])

promo_list_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🗑 Удалить промокод", callback_data="promo_delete")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_promo")]
])

promo_activate_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back")]
])

buy_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
])

give_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
])

take_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
])

def fmt(x):
    return f"{round(x, 2):.2f}"

def get_main_menu(user_id):
    buttons = [
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="daily")],
        [InlineKeyboardButton(text="🎲 Игры", callback_data="games")],
        [InlineKeyboardButton(text="⭐ Купить Germ", callback_data="buy_germ")],
        [InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw")],
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="promo_activate")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def mines_multiplier(opened):
    safe_total = 21
    safe_left = safe_total - opened
    if safe_left <= 0:
        return 0
    return round(25 / safe_left, 2)

def mines_kb(game, reveal_all=False, lose=False):
    buttons = []
    row = []
    for i, cell in enumerate(game["cells"]):
        if reveal_all:
            if lose:
                text = "💣" if cell == "mine" else " "
            else:
                if cell == "mine":
                    text = "💣"
                elif i in game["opened"]:
                    text = "✅"
                else:
                    text = " "
            row.append(InlineKeyboardButton(text=text, callback_data="noop"))
        else:
            if i in game["opened"]:
                row.append(InlineKeyboardButton(text="✅", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton(text="❓", callback_data=f"mine_open_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not reveal_all and game["opened"]:
        mult = mines_multiplier(len(game["opened"]))
        win = round(game["bet"] * mult, 2)
        buttons.append([InlineKeyboardButton(text=f"💰 Забрать {fmt(win)} Germ", callback_data="mine_cashout")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def chicken_multiplier(step):
    return round(1.0 + step * 0.5, 2)

def chicken_kb(game):
    buttons = []
    for i in range(10):
        if i < game["step"]:
            text = "✅"
        else:
            text = f"Шаг {i+1}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"chicken_step_{i}")])
    if game["step"] > 0:
        mult = chicken_multiplier(game["step"])
        win = round(game["bet"] * mult, 2)
        buttons.append([InlineKeyboardButton(text=f"💰 Забрать {fmt(win)} Germ", callback_data="chicken_cashout")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def crash_kb(game):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Забрать {fmt(game['current_win'])} Germ", callback_data="crash_cashout")]
    ])

def blackjack_value(hand):
    total = 0
    aces = 0
    for card in hand:
        rank = card[:-1]
        if rank in ("J", "Q", "K"):
            total += 10
        elif rank == "A":
            aces += 1
            total += 11
        else:
            total += int(rank)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def new_deck():
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    suits = ["♠", "♥", "♦", "♣"]
    deck = [r + s for r in ranks for s in suits]
    random.shuffle(deck)
    return deck

def hand_text(hand):
    return " ".join(hand)

def blackjack_kb(game):
    buttons = []
    if not game["finished"]:
        buttons.append([InlineKeyboardButton(text="🃏 Ещё", callback_data="bj_hit")])
        buttons.append([InlineKeyboardButton(text="✋ Хватит", callback_data="bj_stand")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def db_init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0,
                last_daily TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                germ REAL,
                limit_count INTEGER,
                used TEXT
            )
        """)
        await db.commit()

async def db_get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance, last_daily FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return {"balance": row[0], "last_daily": row[1]}
        await db.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        await db.commit()
        return {"balance": 0.0, "last_daily": None}

async def db_update_balance(user_id, new_balance):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        await db.commit()

async def db_update_daily(user_id, timestamp):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (timestamp, user_id))
        await db.commit()

async def db_load_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, balance, last_daily FROM users")
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            result[row[0]] = {"balance": row[1], "last_daily": row[2]}
        return result

async def db_save_promocodes():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promocodes")
        for code, p in promocodes.items():
            used_str = ",".join(str(x) for x in p["used"])
            await db.execute(
                "INSERT INTO promocodes (code, germ, limit_count, used) VALUES (?, ?, ?, ?)",
                (code, p["germ"], p["limit"], used_str)
            )
        await db.commit()

async def db_load_promocodes():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT code, germ, limit_count, used FROM promocodes")
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            used = set(int(x) for x in row[3].split(",") if x)
            result[row[0]] = {"germ": row[1], "limit": row[2], "used": used}
        return result

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_data:
        users_data[user_id] = await db_get_user(user_id)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\nВыбери действие:",
        reply_markup=get_main_menu(user_id)
    )

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data

    if data == "profile":
        user = callback.from_user
        balance = users_data.get(user_id, {}).get("balance", 0)
        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"🪪 Имя: {user.first_name}\n"
            f"💰 Баланс: {fmt(balance)} Germ"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=profile_menu)

    elif data == "daily":
        user = await db_get_user(user_id)
        last = user["last_daily"]
        now = datetime.now()
        if last:
            last_dt = datetime.fromisoformat(last)
            if now - last_dt < timedelta(days=1):
                left = timedelta(days=1) - (now - last_dt)
                hours = left.seconds // 3600
                minutes = (left.seconds % 3600) // 60
                await callback.message.edit_text(
                    f"⏳ Бонус уже получен.\nПриходи через {hours} ч {minutes} мин.",
                    reply_markup=get_main_menu(user_id)
                )
                await callback.answer()
                return
        users_data.setdefault(user_id, {"balance": 0.0})
        users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + 0.1, 2)
        await db_update_balance(user_id, users_data[user_id]["balance"])
        await db_update_daily(user_id, now.isoformat())
        await callback.message.edit_text(
            f"🎁 Ты получил 0.10 Germ!\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
            reply_markup=get_main_menu(user_id)
        )

    elif data == "games":
        await callback.message.edit_text(
            "🎮 <b>Игры</b>\n\nВыбери игру:",
            parse_mode="HTML",
            reply_markup=games_menu
        )

    elif data == "mines":
        await state.set_state(MinesState.waiting_bet)
        await callback.message.edit_text(
            "💣 <b>Мины</b>\n\nВведи ставку от 1 до 1000 Germ:",
            parse_mode="HTML",
            reply_markup=bet_menu
        )

    elif data == "chicken":
        await state.set_state(ChickenState.waiting_bet)
        await callback.message.edit_text(
            "🐔 <b>Курица</b>\n\n10 шагов, с каждым шанс взрыва растёт. Забирай в любой момент.\n\nВведи ставку от 1 до 1000 Germ:",
            parse_mode="HTML",
            reply_markup=bet_menu
        )

    elif data == "crash":
        await state.set_state(CrashState.waiting_bet)
        await callback.message.edit_text(
            "📈 <b>Краш</b>\n\nМножитель растёт. Забери до взрыва.\n\nВведи ставку от 1 до 1000 Germ:",
            parse_mode="HTML",
            reply_markup=bet_menu
        )

    elif data == "blackjack":
        await state.set_state(BlackjackState.waiting_bet)
        await callback.message.edit_text(
            "🃏 <b>Блэкджек</b>\n\nНабери 21 или ближе к нему, чем бот. Перебор — проигрыш.\n\nВведи ставку от 1 до 1000 Germ:",
            parse_mode="HTML",
            reply_markup=bet_menu
        )

    elif data == "buy_germ":
        await state.set_state(BuyState.waiting_amount)
        await callback.message.edit_text(
            "⭐ <b>Покупка Germ</b>\n\n1 звезда = 10 Germ\nДо 10 000 Germ за раз.\n\nВведи количество Germ:",
            parse_mode="HTML",
            reply_markup=buy_menu
        )

    elif data == "withdraw":
        await callback.message.edit_text(
            "💸 <b>Вывод</b>\n\nВыбери сумму Germ для вывода:",
            parse_mode="HTML",
            reply_markup=withdraw_menu
        )

    elif data.startswith("wd_"):
        amount = int(data.split("_")[1])
        users_data.setdefault(user_id, {"balance": 0.0})
        if users_data[user_id]["balance"] < amount:
            await callback.answer("Недостаточно Germ.")
            return
        withdraw_pending[user_id] = amount
        await state.set_state(WithdrawState.waiting_username)
        await callback.message.edit_text(
            f"💸 Вывод {amount} Germ.\n\nВведи юзернейм получателя (например, @username):",
            reply_markup=withdraw_back
        )

    elif data == "back":
        await state.clear()
        await callback.message.edit_text(
            f"👋 Привет, {callback.from_user.first_name}!\nВыбери действие:",
            reply_markup=get_main_menu(user_id)
        )

    elif data.startswith("mine_open_"):
        game = mines_games.get(user_id)
        if not game or game["finished"]:
            await callback.answer("Игра не найдена.")
            return
        idx = int(data.split("_")[2])
        if idx in game["opened"]:
            await callback.answer("Уже открыта.")
            return
        if idx in game["mines"]:
            game["finished"] = True
            kb = mines_kb(game, reveal_all=True, lose=True)
            await callback.message.edit_text(
                f"💥 Мина! Ты потерял {fmt(game['bet'])} Germ.\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=kb
            )
            mines_games.pop(user_id, None)
            await callback.message.answer("Выбери действие:", reply_markup=end_menu)
            await callback.answer()
            return
        game["opened"].add(idx)
        if len(game["opened"]) == 21:
            mult = mines_multiplier(21)
            win = round(game["bet"] * mult, 2)
            users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
            await db_update_balance(user_id, users_data[user_id]["balance"])
            game["finished"] = True
            kb = mines_kb(game, reveal_all=True)
            await callback.message.edit_text(
                f"🎉 Все безопасные клетки открыты!\n💰 Выигрыш: {fmt(win)} Germ (×{mult})\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=kb
            )
            mines_games.pop(user_id, None)
            await callback.message.answer("Выбери действие:", reply_markup=end_menu)
            await callback.answer()
            return
        mult = mines_multiplier(len(game["opened"]))
        await callback.message.edit_reply_markup(reply_markup=mines_kb(game))
        await callback.answer(f"×{mult}")

    elif data == "mine_cashout":
        game = mines_games.get(user_id)
        if not game or game["finished"] or not game["opened"]:
            await callback.answer("Нечего забирать.")
            return
        mult = mines_multiplier(len(game["opened"]))
        win = round(game["bet"] * mult, 2)
        users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
        await db_update_balance(user_id, users_data[user_id]["balance"])
        game["finished"] = True
        kb = mines_kb(game, reveal_all=True)
        await callback.message.edit_text(
            f"💰 Ты забрал {fmt(win)} Germ (×{mult})\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
            reply_markup=kb
        )
        mines_games.pop(user_id, None)
        await callback.message.answer("Выбери действие:", reply_markup=end_menu)

    elif data.startswith("chicken_step_"):
        game = chicken_games.get(user_id)
        if not game or game["finished"]:
            await callback.answer("Игра не найдена.")
            return
        step = int(data.split("_")[2])
        if step != game["step"]:
            await callback.answer("Не твой шаг.")
            return
        bomb_chance = 0.22 + step * 0.09
        if random.random() < bomb_chance:
            game["finished"] = True
            await callback.message.edit_text(
                f"💥 Курица взорвалась на шаге {step+1}!\nТы потерял {fmt(game['bet'])} Germ.\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=end_menu
            )
            chicken_games.pop(user_id, None)
            await callback.answer()
            return
        game["step"] += 1
        if game["step"] >= 10:
            mult = chicken_multiplier(10)
            win = round(game["bet"] * mult, 2)
            users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
            await db_update_balance(user_id, users_data[user_id]["balance"])
            game["finished"] = True
            await callback.message.edit_text(
                f"🎉 Ты прошёл все 10 шагов!\n💰 Выигрыш: {fmt(win)} Germ (×{mult})\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=end_menu
            )
            chicken_games.pop(user_id, None)
            await callback.answer()
            return
        mult = chicken_multiplier(game["step"])
        await callback.message.edit_text(
            f"🐔 Шаг {game['step']}/10\nМножитель: ×{mult}\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
            reply_markup=chicken_kb(game)
        )
        await callback.answer()

    elif data == "chicken_cashout":
        game = chicken_games.get(user_id)
        if not game or game["finished"] or game["step"] == 0:
            await callback.answer("Нечего забирать.")
            return
        mult = chicken_multiplier(game["step"])
        win = round(game["bet"] * mult, 2)
        users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
        await db_update_balance(user_id, users_data[user_id]["balance"])
        game["finished"] = True
        await callback.message.edit_text(
            f"💰 Ты забрал {fmt(win)} Germ (×{mult})\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
            reply_markup=end_menu
        )
        chicken_games.pop(user_id, None)

    elif data == "crash_cashout":
        game = crash_games.get(user_id)
        if not game or game["finished"]:
            await callback.answer("Игра не найдена.")
            return
        win = round(game["bet"] * game["mult"], 2)
        users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
        await db_update_balance(user_id, users_data[user_id]["balance"])
        game["finished"] = True
        await callback.message.edit_text(
            f"💰 Ты забрал на ×{game['mult']}!\nВыигрыш: {fmt(win)} Germ\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
            reply_markup=end_menu
        )
        crash_games.pop(user_id, None)
        await callback.answer()

    elif data == "bj_hit":
        game = blackjack_games.get(user_id)
        if not game or game["finished"]:
            await callback.answer("Игра не найдена.")
            return
        game["player"].append(game["deck"].pop())
        pv = blackjack_value(game["player"])
        if pv > 21:
            game["finished"] = True
            await callback.message.edit_text(
                f"🃏 Перебор! У тебя {pv}.\nТы проиграл {fmt(game['bet'])} Germ.\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=end_menu
            )
            blackjack_games.pop(user_id, None)
        else:
            await callback.message.edit_text(
                f"🃏 Твои карты: {hand_text(game['player'])} ({pv})\nКарта бота: {game['dealer'][0]} ?\n\nЕщё или хватит?",
                reply_markup=blackjack_kb(game)
            )
        await callback.answer()

    elif data == "bj_stand":
        game = blackjack_games.get(user_id)
        if not game or game["finished"]:
            await callback.answer("Игра не найдена.")
            return
        while blackjack_value(game["dealer"]) < 18:
            game["dealer"].append(game["deck"].pop())
        pv = blackjack_value(game["player"])
        dv = blackjack_value(game["dealer"])
        game["finished"] = True
        if dv > 21 or pv > dv:
            win = round(game["bet"] * 2, 2)
            users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
            await db_update_balance(user_id, users_data[user_id]["balance"])
            text = (
                f"🃏 Твои карты: {hand_text(game['player'])} ({pv})\n"
                f"Карты бота: {hand_text(game['dealer'])} ({dv})\n\n"
                f"🏆 Ты выиграл {fmt(win)} Germ!\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ"
            )
        elif pv == dv:
            users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + game["bet"], 2)
            await db_update_balance(user_id, users_data[user_id]["balance"])
            text = (
                f"🃏 Твои карты: {hand_text(game['player'])} ({pv})\n"
                f"Карты бота: {hand_text(game['dealer'])} ({dv})\n\n"
                f"🤝 Ничья. Возврат {fmt(game['bet'])} Germ.\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ"
            )
        else:
            text = (
                f"🃏 Твои карты: {hand_text(game['player'])} ({pv})\n"
                f"Карты бота: {hand_text(game['dealer'])} ({dv})\n\n"
                f"❌ Ты проиграл {fmt(game['bet'])} Germ.\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ"
            )
        await callback.message.edit_text(text, reply_markup=end_menu)
        blackjack_games.pop(user_id, None)
        await callback.answer()

    elif data == "admin_panel":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await callback.message.edit_text("🛠 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=admin_menu)

    elif data == "admin_users" or data.startswith("admin_users_page_"):
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        page = 0
        if data.startswith("admin_users_page_"):
            page = int(data.split("_")[3])
        uids = list(users_data.keys())
        per_page = 50
        total_pages = max(1, (len(uids) + per_page - 1) // per_page)
        if page >= total_pages:
            page = total_pages - 1
        start = page * per_page
        chunk = uids[start:start + per_page]
        lines = []
        for uid in chunk:
            d = users_data[uid]
            name = "—"
            uname = "—"
            try:
                chat = await bot.get_chat(uid)
                name = chat.full_name or "—"
                uname = f"@{chat.username}" if chat.username else "—"
            except Exception:
                pass
            lines.append(f"{uid} | {name} | {uname} | {fmt(d['balance'])} Germ")
        text = f"👥 <b>Пользователи</b> (стр. {page+1}/{total_pages})\n\n" + "\n".join(lines) if lines else "Пользователей нет."
        buttons = []
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{page-1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{page+1}"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data == "admin_stats":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        total = sum(u["balance"] for u in users_data.values())
        await callback.message.edit_text(
            f"📊 <b>Статистика</b>\n\n👥 Пользователей: {len(users_data)}\n💰 Germ в системе: {fmt(total)}\n🎟 Промокодов: {len(promocodes)}",
            parse_mode="HTML",
            reply_markup=admin_menu
        )

    elif data == "admin_give":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await state.set_state(AdminState.waiting_give)
        await callback.message.edit_text("💰 Введи: <code>ID сумма</code>\nПример: <code>123456789 100</code>", parse_mode="HTML", reply_markup=give_menu)

    elif data == "admin_take":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await state.set_state(AdminState.waiting_take)
        await callback.message.edit_text("💸 Введи: <code>ID сумма</code> — сколько списать", parse_mode="HTML", reply_markup=take_menu)

    elif data == "admin_broadcast":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await state.set_state(AdminState.waiting_broadcast)
        await callback.message.edit_text("📢 Введи текст рассылки:", reply_markup=admin_menu)

    elif data == "admin_promo":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await callback.message.edit_text("🎟 <b>Промокоды</b>", parse_mode="HTML", reply_markup=promo_menu)

    elif data == "promo_create":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await state.set_state(AdminState.waiting_promo)
        await callback.message.edit_text(
            "Введи: <code>КОД СУММА ЛИМИТ</code>\nПример: <code>WELCOME 50 100</code>",
            parse_mode="HTML",
            reply_markup=promo_menu
        )

    elif data == "promo_list":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        if not promocodes:
            await callback.message.edit_text("Промокодов нет.", reply_markup=promo_list_menu)
        else:
            lines = []
            for code, p in promocodes.items():
                lines.append(f"{code} | {fmt(p['germ'])} Germ | {len(p['used'])}/{p['limit']}")
            await callback.message.edit_text("📋 <b>Промокоды</b>\n\n" + "\n".join(lines), parse_mode="HTML", reply_markup=promo_list_menu)

    elif data == "promo_delete":
        if user_id != ADMIN_ID:
            await callback.answer("Нет доступа.")
            return
        await state.set_state(AdminState.waiting_promo_delete)
        await callback.message.edit_text("🗑 Введи код промокода для удаления:", reply_markup=promo_menu)

    elif data == "promo_activate":
        await state.set_state(AdminState.waiting_promo_activate)
        await callback.message.edit_text("Введи промокод:", reply_markup=promo_activate_menu)

    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(lambda m: m.successful_payment is not None)
async def on_paid(message: Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    payload = payment.invoice_payload or ""
    if payload.startswith("germ_"):
        try:
            amount_germ = float(payload.split("_")[1])
        except (IndexError, ValueError):
            amount_germ = 0
        if amount_germ > 0:
            users_data.setdefault(user_id, {"balance": 0.0})
            users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + amount_germ, 2)
            await db_update_balance(user_id, users_data[user_id]["balance"])
            await message.answer(
                f"✅ Оплата получена! +{fmt(amount_germ)} Germ\n💰 Баланс: {fmt(users_data[user_id]['
