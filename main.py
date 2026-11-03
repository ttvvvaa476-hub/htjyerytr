from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import asyncio
import random
import aiosqlite

TOKEN = "9184774782:AAEGB-NlqoZpsFTJwDFaXxvEdrmZN5p4vIk"
ADMIN_ID = 8121754585
DB_PATH = "bot.db"

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
                f"✅ Оплата получена! +{fmt(amount_germ)} Germ\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=get_main_menu(user_id)
            )

@dp.message(WithdrawState.waiting_username)
async def withdraw_username(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    amount = withdraw_pending.get(user_id)
    if not amount:
        await state.clear()
        await message.answer("❌ Заявка не найдена.")
        return
    username = message.text.strip()
    users_data.setdefault(user_id, {"balance": 0.0})
    if users_data[user_id]["balance"] < amount:
        await state.clear()
        await message.answer("❌ Недостаточно Germ.")
        return
    users_data[user_id]["balance"] = round(users_data[user_id]["balance"] - amount, 2)
    await db_update_balance(user_id, users_data[user_id]["balance"])
    withdraw_pending.pop(user_id, None)
    await state.clear()
    await message.answer(
        f"✅ Заявка на вывод {amount} Germ отправлена.\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
        reply_markup=get_main_menu(user_id)
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💸 Новая заявка на вывод\n"
            f"Сумма: {amount} Germ\n"
            f"ID: {user_id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Юзернейм для отправки: {username}"
        )
    except Exception:
        pass

@dp.message(MinesState.waiting_bet)
async def process_mines_bet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        bet = int(message.text)
    except ValueError:
        await message.answer("❌ Введи целое число от 1 до 1000.")
        return
    if bet < 1 or bet > 1000:
        await message.answer("❌ Ставка должна быть от 1 до 1000.")
        return
    users_data.setdefault(user_id, {"balance": 0.0})
    if users_data[user_id]["balance"] < bet:
        await message.answer(f"❌ Недостаточно Germ. У тебя {fmt(users_data[user_id]['balance'])}.")
        return
    await state.clear()
    users_data[user_id]["balance"] = round(users_data[user_id]["balance"] - bet, 2)
    await db_update_balance(user_id, users_data[user_id]["balance"])
    cells = list(range(25))
    mines = set(random.sample(cells, 4))
    game = {"bet": bet, "cells": ["mine" if i in mines else "safe" for i in range(25)], "mines": mines, "opened": set(), "finished": False}
    mines_games[user_id] = game
    await message.answer(f"💣 Ставка: {bet} Germ\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ", reply_markup=mines_kb(game))

@dp.message(ChickenState.waiting_bet)
async def process_chicken_bet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        bet = int(message.text)
    except ValueError:
        await message.answer("❌ Введи целое число от 1 до 1000.")
        return
    if bet < 1 or bet > 1000:
        await message.answer("❌ Ставка должна быть от 1 до 1000.")
        return
    users_data.setdefault(user_id, {"balance": 0.0})
    if users_data[user_id]["balance"] < bet:
        await message.answer(f"❌ Недостаточно Germ. У тебя {fmt(users_data[user_id]['balance'])}.")
        return
    await state.clear()
    users_data[user_id]["balance"] = round(users_data[user_id]["balance"] - bet, 2)
    await db_update_balance(user_id, users_data[user_id]["balance"])
    game = {"bet": bet, "step": 0, "finished": False}
    chicken_games[user_id] = game
    await message.answer(
        f"🐔 Ставка: {bet} Germ\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ\nШаг 1/10. Жми «Шаг 1».",
        reply_markup=chicken_kb(game)
    )

@dp.message(CrashState.waiting_bet)
async def process_crash_bet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        bet = int(message.text)
    except ValueError:
        await message.answer("❌ Введи целое число от 1 до 1000.")
        return
    if bet < 1 or bet > 1000:
        await message.answer("❌ Ставка должна быть от 1 до 1000.")
        return
    users_data.setdefault(user_id, {"balance": 0.0})
    if users_data[user_id]["balance"] < bet:
        await message.answer(f"❌ Недостаточно Germ. У тебя {fmt(users_data[user_id]['balance'])}.")
        return
    await state.clear()
    users_data[user_id]["balance"] = round(users_data[user_id]["balance"] - bet, 2)
    await db_update_balance(user_id, users_data[user_id]["balance"])
    game = {"bet": bet, "mult": 1.0, "current_win": bet, "finished": False}
    crash_games[user_id] = game
    msg = await message.answer(
        f"📈 Ставка: {bet} Germ\nМножитель: ×1.00\n💰 Забрать: {fmt(bet)} Germ",
        reply_markup=crash_kb(game)
    )
    asyncio.create_task(crash_loop(user_id, msg))

async def crash_loop(user_id, msg):
    game = crash_games.get(user_id)
    if not game:
        return
    while not game["finished"]:
        await asyncio.sleep(1.0)
        game["mult"] = round(game["mult"] + 0.2, 2)
        game["current_win"] = round(game["bet"] * game["mult"], 2)
        if game["mult"] >= 1.5 and random.random() < 0.25:
            game["finished"] = True
            await msg.edit_text(
                f"💥 Краш на ×{game['mult']}!\nТы потерял {fmt(game['bet'])} Germ.\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=end_menu
            )
            crash_games.pop(user_id, None)
            return
        if game["mult"] >= 7.0:
            win = round(game["bet"] * game["mult"], 2)
            users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
            await db_update_balance(user_id, users_data[user_id]["balance"])
            game["finished"] = True
            await msg.edit_text(
                f"🚀 Максимум ×7! Выигрыш {fmt(win)} Germ.\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
                reply_markup=end_menu
            )
            crash_games.pop(user_id, None)
            return
        try:
            await msg.edit_text(
                f"📈 Ставка: {game['bet']} Germ\nМножитель: ×{game['mult']}\n💰 Забрать: {fmt(game['current_win'])} Germ",
                reply_markup=crash_kb(game)
            )
        except Exception:
            pass

@dp.message(BlackjackState.waiting_bet)
async def process_blackjack_bet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        bet = int(message.text)
    except ValueError:
        await message.answer("❌ Введи целое число от 1 до 1000.")
        return
    if bet < 1 or bet > 1000:
        await message.answer("❌ Ставка должна быть от 1 до 1000.")
        return
    users_data.setdefault(user_id, {"balance": 0.0})
    if users_data[user_id]["balance"] < bet:
        await message.answer(f"❌ Недостаточно Germ. У тебя {fmt(users_data[user_id]['balance'])}.")
        return
    await state.clear()
    users_data[user_id]["balance"] = round(users_data[user_id]["balance"] - bet, 2)
    await db_update_balance(user_id, users_data[user_id]["balance"])
    deck = new_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    game = {"bet": bet, "deck": deck, "player": player, "dealer": dealer, "finished": False}
    blackjack_games[user_id] = game
    pv = blackjack_value(player)
    if pv == 21:
        win = round(bet * 2.5, 2)
        users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + win, 2)
        await db_update_balance(user_id, users_data[user_id]["balance"])
        game["finished"] = True
        await message.answer(
            f"🃏 Блэкджек! {hand_text(player)} ({pv})\n💰 Выигрыш: {fmt(win)} Germ\n💳 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
            reply_markup=end_menu
        )
        blackjack_games.pop(user_id, None)
        return
    await message.answer(
        f"🃏 Твои карты: {hand_text(player)} ({pv})\nКарта бота: {dealer[0]} ?\n\nЕщё или хватит?",
        reply_markup=blackjack_kb(game)
    )

@dp.message(BuyState.waiting_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount_germ = int(message.text)
    except ValueError:
        await message.answer("❌ Введи целое число Germ.")
        return
    if amount_germ < 1 or amount_germ > 10000:
        await message.answer("❌ Можно купить от 1 до 10 000 Germ за раз.")
        return
    if amount_germ % 10 != 0:
        await message.answer("❌ Количество Germ должно быть кратно 10 (1 звезда = 10 Germ).")
        return
    stars = amount_germ // 10
    await state.clear()
    prices = [LabeledPrice(label=f"{amount_germ} Germ", amount=stars)]
    await bot.send_invoice(
        chat_id=user_id,
        title="Покупка Germ",
        description=f"{amount_germ} Germ за {stars} звёзд",
        payload=f"germ_{amount_germ}",
        provider_token="",
        currency="XTR",
        prices=prices
    )

@dp.message(AdminState.waiting_give)
async def admin_give(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: ID сумма")
        return
    try:
        target = int(parts[0])
        amount = float(parts[1])
    except ValueError:
        await message.answer("❌ ID и сумма должны быть числами.")
        return
    users_data.setdefault(target, {"balance": 0.0})
    users_data[target]["balance"] = round(users_data[target]["balance"] + amount, 2)
    await db_update_balance(target, users_data[target]["balance"])
    await state.clear()
    await message.answer(
        f"✅ Выдано {fmt(amount)} Germ пользователю {target}.\n💰 Его баланс: {fmt(users_data[target]['balance'])} Germ",
        reply_markup=admin_menu
    )
    try:
        await bot.send_message(target, f"🎁 Тебе начислено {fmt(amount)} Germ!")
    except Exception:
        pass

@dp.message(AdminState.waiting_take)
async def admin_take(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: ID сумма")
        return
    try:
        target = int(parts[0])
        amount = float(parts[1])
    except ValueError:
        await message.answer("❌ ID и сумма должны быть числами.")
        return
    users_data.setdefault(target, {"balance": 0.0})
    if users_data[target]["balance"] < amount:
        await message.answer("❌ У пользователя недостаточно Germ.")
        return
    users_data[target]["balance"] = round(users_data[target]["balance"] - amount, 2)
    await db_update_balance(target, users_data[target]["balance"])
    await state.clear()
    await message.answer(
        f"✅ Списано {fmt(amount)} Germ у пользователя {target}.\n💰 Его баланс: {fmt(users_data[target]['balance'])} Germ",
        reply_markup=admin_menu
    )

@dp.message(AdminState.waiting_broadcast)
async def admin_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text
    await state.clear()
    sent = 0
    for uid in list(users_data.keys()):
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass
    await message.answer(f"📢 Рассылка отправлена: {sent} получателей.", reply_markup=admin_menu)

@dp.message(AdminState.waiting_promo)
async def admin_promo_create(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Формат: КОД СУММА ЛИМИТ")
        return
    code = parts[0].upper()
    try:
        germ = float(parts[1])
        limit = int(parts[2])
    except ValueError:
        await message.answer("❌ Сумма и лимит должны быть числами.")
        return
    if code in promocodes:
        await message.answer("❌ Такой промокод уже есть.")
        return
    promocodes[code] = {"germ": germ, "limit": limit, "used": set()}
    await db_save_promocodes()
    await state.clear()
    await message.answer(f"✅ Промокод {code} создан.\n💰 {fmt(germ)} Germ\n👥 Лимит: {limit}", reply_markup=promo_menu)

@dp.message(AdminState.waiting_promo_delete)
async def admin_promo_delete(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    code = message.text.strip().upper()
    if code not in promocodes:
        await message.answer("❌ Промокод не найден.", reply_markup=promo_menu)
        return
    promocodes.pop(code, None)
    await db_save_promocodes()
    await state.clear()
    await message.answer(f"✅ Промокод {code} удалён.", reply_markup=promo_menu)

@dp.message(AdminState.waiting_promo_activate)
async def promo_activate(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip().upper()
    p = promocodes.get(code)
    if not p:
        await message.answer("❌ Промокод не найден.")
        return
    if user_id in p["used"]:
        await message.answer("❌ Ты уже активировал этот промокод.")
        return
    if len(p["used"]) >= p["limit"]:
        await message.answer("❌ Лимит активаций исчерпан.")
        return
    p["used"].add(user_id)
    users_data.setdefault(user_id, {"balance": 0.0})
    users_data[user_id]["balance"] = round(users_data[user_id]["balance"] + p["germ"], 2)
    await db_update_balance(user_id, users_data[user_id]["balance"])
    await db_save_promocodes()
    await state.clear()
    await message.answer(
        f"✅ Промокод активирован!\n🎁 +{fmt(p['germ'])} Germ\n💰 Баланс: {fmt(users_data[user_id]['balance'])} Germ",
        reply_markup=get_main_menu(user_id)
    )

async def main():
    global users_data, promocodes
    await db_init()
    users_data = await db_load_all_users()
    promocodes = await db_load_promocodes()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
