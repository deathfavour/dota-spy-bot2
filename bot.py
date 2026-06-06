import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# СПИСОК ГЕРОЕВ ДОТА 2
# ============================================================
DOTA_HEROES = [
    "Axe", "Bristleback", "Centaur Warrunner", "Chaos Knight", "Dawnbreaker",
    "Dragon Knight", "Earth Spirit", "Earthshaker", "Elder Titan", "Huskar",
    "Kunkka", "Legion Commander", "Lifestealer", "Mars", "Night Stalker",
    "Ogre Magi", "Pudge", "Sand King", "Slardar", "Spirit Breaker",
    "Sven", "Tidehunter", "Tiny", "Underlord", "Undying",
    "Wraith King", "Anti-Mage", "Arc Warden", "Bloodseeker", "Clinkz",
    "Drow Ranger", "Ember Spirit", "Faceless Void", "Gyrocopter", "Hoodwink",
    "Juggernaut", "Luna", "Medusa", "Meepo", "Mirana",
    "Monkey King", "Morphling", "Naga Siren", "Phantom Assassin", "Phantom Lancer",
    "Razor", "Riki", "Shadow Fiend", "Slark", "Sniper",
    "Spectre", "Templar Assassin", "Terrorblade", "Troll Warlord", "Ursa",
    "Viper", "Weaver", "Windranger", "Zeus", "Ancient Apparition",
    "Bane", "Batrider", "Chen", "Crystal Maiden", "Dark Seer",
    "Dark Willow", "Dazzle", "Death Prophet", "Disruptor", "Enigma",
    "Grimstroke", "Invoker", "Jakiro", "Keeper of the Light", "Leshrac",
    "Lina", "Lion", "Muerta", "Nature's Prophet", "Necrophos",
    "Nightstalker", "Nyx Assassin", "Puck", "Pugna", "Queen of Pain",
    "Rubick", "Shadow Demon", "Shadow Shaman", "Silencer", "Skywrath Mage",
    "Storm Spirit", "Techies", "Tinker", "Visage", "Void Spirit",
    "Warlock", "Witch Doctor", "Abaddon", "Beastmaster", "Brewmaster",
    "Broodmother", "Clockwerk", "Doom", "Io", "Lycan",
    "Magnus", "Marci", "Natures Prophet", "Primal Beast", "Timbersaw",
    "Treant Protector", "Vengeful Spirit", "Venomancer", "Witch Doctor",
]

# ============================================================
# ХРАНИЛИЩЕ ИГР: {chat_id: game_state}
# ============================================================
games = {}

def new_game_state():
    return {
        "phase": "lobby",       # lobby | playing | voting | finished
        "players": {},          # {user_id: {"name": ..., "role": "spy"/"player"}}
        "hero": None,
        "spy_id": None,
        "votes": {},            # {voter_id: target_id}
        "round": 0,
        "creator_id": None,
    }

# ============================================================
# КОМАНДЫ
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Шпион среди героев Доты 2*\n\n"
        "Один игрок — шпион. Он не знает героя.\n"
        "Остальные знают героя и задают вопросы.\n"
        "Шпион пытается не раскрыться!\n\n"
        "📋 *Команды:*\n"
        "/newgame — создать новую игру\n"
        "/join — присоединиться к игре\n"
        "/startgame — начать (только создатель)\n"
        "/vote — начать голосование\n"
        "/endgame — завершить игру\n"
        "/help — помощь",
        parse_mode="Markdown"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Правила игры:*\n\n"
        "1. Создатель пишет /newgame\n"
        "2. Все участники пишут /join\n"
        "3. Создатель пишет /startgame\n"
        "4. Каждый получит в личку: либо имя героя, либо сообщение что он шпион\n"
        "5. Игроки по очереди задают вопросы о герое\n"
        "6. Шпион должен не раскрыться и угадать героя\n"
        "7. /vote — начать голосование за шпиона\n\n"
        "⚠️ Бот должен быть добавлен в группу.\n"
        "Личные сообщения получат только те, кто написал боту /start в личке.",
        parse_mode="Markdown"
    )

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id == user.id:
        await update.message.reply_text("❌ Создайте игру в групповом чате!")
        return

    games[chat_id] = new_game_state()
    games[chat_id]["creator_id"] = user.id
    games[chat_id]["players"][user.id] = {"name": user.first_name, "role": None}

    await update.message.reply_text(
        f"🎮 *Новая игра создана!*\n\n"
        f"Создатель: {user.first_name}\n"
        f"Игроки ({1}): {user.first_name}\n\n"
        f"Пишите /join чтобы присоединиться.\n"
        f"Создатель пишет /startgame когда все готовы.",
        parse_mode="Markdown"
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("❌ Нет активной игры. Напишите /newgame")
        return

    game = games[chat_id]

    if game["phase"] != "lobby":
        await update.message.reply_text("❌ Игра уже началась!")
        return

    if user.id in game["players"]:
        await update.message.reply_text(f"✅ {user.first_name}, ты уже в игре!")
        return

    game["players"][user.id] = {"name": user.first_name, "role": None}
    names = [p["name"] for p in game["players"].values()]

    await update.message.reply_text(
        f"✅ *{user.first_name} присоединился!*\n\n"
        f"Игроки ({len(names)}): {', '.join(names)}",
        parse_mode="Markdown"
    )

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = games[chat_id]

    if game["creator_id"] != user.id:
        await update.message.reply_text("❌ Только создатель может начать игру!")
        return

    if game["phase"] != "lobby":
        await update.message.reply_text("❌ Игра уже идёт!")
        return

    if len(game["players"]) < 3:
        await update.message.reply_text("❌ Нужно минимум 3 игрока!")
        return

    # Выбираем героя и шпиона
    hero = random.choice(DOTA_HEROES)
    spy_id = random.choice(list(game["players"].keys()))

    game["hero"] = hero
    game["spy_id"] = spy_id
    game["phase"] = "playing"

    for pid, pdata in game["players"].items():
        if pid == spy_id:
            pdata["role"] = "spy"
        else:
            pdata["role"] = "player"

    # Рассылаем роли в личку
    sent_ok = []
    failed = []

    for pid, pdata in game["players"].items():
        try:
            if pid == spy_id:
                msg = (
                    "🕵️ *Ты — ШПИОН!*\n\n"
                    "Ты не знаешь героя.\n"
                    "Веди себя так, будто знаешь.\n"
                    "В конце попробуй угадать героя!"
                )
            else:
                msg = (
                    f"🦸 *Твоя роль: Мирный житель*\n\n"
                    f"Герой этого раунда:\n"
                    f"⚔️ *{hero}*\n\n"
                    f"Задавай вопросы, не раскрывая героя напрямую.\n"
                    f"Найди шпиона!"
                )
            await context.bot.send_message(pid, msg, parse_mode="Markdown")
            sent_ok.append(pdata["name"])
        except Exception:
            failed.append(pdata["name"])

    names = [p["name"] for p in game["players"].values()]
    spy_name = game["players"][spy_id]["name"]

    result_msg = (
        f"🎮 *Игра началась!*\n\n"
        f"Игроки: {', '.join(names)}\n\n"
        f"Роли отправлены в личку.\n"
        f"Задавайте друг другу вопросы о герое!\n\n"
        f"Когда решите — /vote для голосования."
    )

    if failed:
        result_msg += f"\n\n⚠️ Не смог написать: {', '.join(failed)}\nПусть напишут боту /start в личке."

    await update.message.reply_text(result_msg, parse_mode="Markdown")

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = games[chat_id]

    if game["phase"] != "playing":
        await update.message.reply_text("❌ Сейчас не время для голосования.")
        return

    if user.id not in game["players"]:
        await update.message.reply_text("❌ Ты не в этой игре.")
        return

    game["phase"] = "voting"
    game["votes"] = {}

    # Кнопки с именами игроков
    keyboard = []
    for pid, pdata in game["players"].items():
        keyboard.append([InlineKeyboardButton(
            f"🎯 {pdata['name']}",
            callback_data=f"vote_{chat_id}_{pid}"
        )])

    await update.message.reply_text(
        "🗳️ *Голосование началось!*\n\n"
        "Кто шпион? Каждый голосует один раз.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    # vote_{chat_id}_{target_id}
    chat_id = int(data[1])
    target_id = int(data[2])
    voter_id = query.from_user.id

    if chat_id not in games:
        await query.answer("Игра не найдена.", show_alert=True)
        return

    game = games[chat_id]

    if game["phase"] != "voting":
        await query.answer("Голосование не активно.", show_alert=True)
        return

    if voter_id not in game["players"]:
        await query.answer("Ты не в этой игре.", show_alert=True)
        return

    if voter_id in game["votes"]:
        await query.answer("Ты уже проголосовал!", show_alert=True)
        return

    game["votes"][voter_id] = target_id
    target_name = game["players"][target_id]["name"]
    voter_name = game["players"][voter_id]["name"]

    await context.bot.send_message(
        chat_id,
        f"✅ {voter_name} проголосовал за {target_name}"
    )

    # Все проголосовали?
    if len(game["votes"]) >= len(game["players"]):
        await finish_voting(context, chat_id)

async def finish_voting(context, chat_id):
    game = games[chat_id]

    # Подсчёт голосов
    vote_count = {}
    for target_id in game["votes"].values():
        vote_count[target_id] = vote_count.get(target_id, 0) + 1

    # Кто получил больше всего голосов
    max_votes = max(vote_count.values())
    accused_ids = [pid for pid, v in vote_count.items() if v == max_votes]
    accused_id = accused_ids[0]
    accused_name = game["players"][accused_id]["name"]

    spy_id = game["spy_id"]
    spy_name = game["players"][spy_id]["name"]
    hero = game["hero"]

    # Результат
    if accused_id == spy_id:
        result = f"✅ *Шпион пойман!*\nИм был {spy_name}!"
        win = "Мирные жители победили! 🎉"
    else:
        result = f"❌ *Шпион ушёл!*\nВы обвинили {accused_name}, но шпионом был *{spy_name}*!"
        win = "Шпион победил! 🕵️"

    # Таблица голосов
    vote_lines = []
    for voter_id, target_id in game["votes"].items():
        voter_name = game["players"][voter_id]["name"]
        target_name = game["players"][target_id]["name"]
        vote_lines.append(f"  {voter_name} → {target_name}")

    msg = (
        f"🏁 *Игра окончена!*\n\n"
        f"{result}\n"
        f"Герой был: ⚔️ *{hero}*\n\n"
        f"{win}\n\n"
        f"📊 *Голоса:*\n" + "\n".join(vote_lines) +
        f"\n\n/newgame — сыграть снова"
    )

    await context.bot.send_message(chat_id, msg, parse_mode="Markdown")
    game["phase"] = "finished"

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("❌ Нет активной игры.")
        return

    game = games[chat_id]

    if game["creator_id"] != user.id:
        await update.message.reply_text("❌ Только создатель может завершить игру.")
        return

    spy_id = game.get("spy_id")
    hero = game.get("hero", "неизвестен")

    if spy_id:
        spy_name = game["players"][spy_id]["name"]
        await update.message.reply_text(
            f"🛑 *Игра завершена досрочно.*\n\n"
            f"Шпион был: *{spy_name}*\n"
            f"Герой: ⚔️ *{hero}*\n\n"
            f"/newgame — новая игра",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("🛑 Игра отменена.")

    del games[chat_id]

# ============================================================
# ЗАПУСК
# ============================================================

def main():
    import os
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        raise ValueError("Переменная окружения BOT_TOKEN не задана!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("newgame", new_game))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CommandHandler("vote", vote))
    app.add_handler(CommandHandler("endgame", end_game))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote_"))

    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
