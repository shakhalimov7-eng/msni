#!/usr/bin/env python3
"""
Telegram Calculator Bot
Ishlatish: pip install python-telegram-bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Logging sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot TOKEN — @BotFather dan oling
BOT_TOKEN = "8503981749:AAFoTPUke0G2h_Dd6weqGYNpRc69PmVynrQ"

# ─── Kalkulyator tugmalari ────────────────────────────────────────────────────

BUTTONS = [
    ["C", "±", "%", "÷"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "−"],
    ["1", "2", "3", "+"],
    ["0", ".", "⌫", "="],
]

def build_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    for row in BUTTONS:
        keyboard.append([
            InlineKeyboardButton(btn, callback_data=btn)
            for btn in row
        ])
    return InlineKeyboardMarkup(keyboard)


def format_display(expr: str, result: str | None = None) -> str:
    display = f"```\n{expr or '0'}"
    if result is not None:
        display += f"\n= {result}"
    display += "\n```"
    return display


# ─── State management ─────────────────────────────────────────────────────────
# user_id -> {"expr": str, "last_result": str | None, "just_equal": bool}
user_state: dict[int, dict] = {}

def get_state(user_id: int) -> dict:
    if user_id not in user_state:
        user_state[user_id] = {"expr": "", "last_result": None, "just_equal": False}
    return user_state[user_id]


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    user_state[uid] = {"expr": "", "last_result": None, "just_equal": False}

    await update.message.reply_text(
        "🧮 *Calculator Bot*\n\nHisoblash uchun quyidagi tugmalardan foydalaning:",
        parse_mode="Markdown",
        reply_markup=build_keyboard(),
    )


async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    state = get_state(uid)
    btn = query.data

    expr: str = state["expr"]
    just_equal: bool = state["just_equal"]
    result_text: str | None = None

    # ── Tugma mantig'i ──────────────────────────────────────────────────────
    if btn == "C":
        expr = ""
        state["last_result"] = None
        state["just_equal"] = False

    elif btn == "⌫":
        expr = expr[:-1]
        state["just_equal"] = False

    elif btn == "=":
        if expr:
            try:
                # Operatorlarni almashtirish
                safe_expr = (
                    expr
                    .replace("×", "*")
                    .replace("÷", "/")
                    .replace("−", "-")
                    .replace("%", "/100")
                )
                raw = eval(safe_expr, {"__builtins__": {}})  # nosec
                # Butun son bo'lsa .0 ni olib tashlash
                if isinstance(raw, float) and raw.is_integer():
                    raw = int(raw)
                result_text = str(raw)
                state["last_result"] = result_text
                state["just_equal"] = True
            except ZeroDivisionError:
                result_text = "❌ Nolga bo'lish mumkin emas"
                expr = ""
                state["just_equal"] = False
            except Exception:
                result_text = "❌ Xato ifoda"
                expr = ""
                state["just_equal"] = False

    elif btn == "±":
        if expr:
            if expr.startswith("-"):
                expr = expr[1:]
            else:
                expr = "-" + expr

    elif btn in ("+", "−", "×", "÷"):
        # Yangi hisoblash agar oldingi = bosilgan bo'lsa
        if just_equal and state["last_result"]:
            expr = state["last_result"]
        # Oxirgi belgi operator bo'lsa almashtir
        if expr and expr[-1] in ("+", "−", "×", "÷"):
            expr = expr[:-1]
        expr += btn
        state["just_equal"] = False

    elif btn == ".":
        # Hozirgi raqam qismiga nuqta qo'shish
        if just_equal:
            expr = "0."
            state["just_equal"] = False
        elif not expr or expr[-1] in ("+", "−", "×", "÷"):
            expr += "0."
        elif "." not in expr.split("+")[-1].split("−")[-1].split("×")[-1].split("÷")[-1]:
            expr += "."

    else:  # raqamlar
        if just_equal:
            # Yangi hisoblash boshlash
            expr = btn
            state["just_equal"] = False
        else:
            expr += btn

    state["expr"] = expr

    # ── Displeyni yangilash ─────────────────────────────────────────────────
    display = format_display(expr if not just_equal else state.get("last_result", expr), 
                             result_text if btn == "=" else None)

    try:
        await query.edit_message_text(
            text=display,
            parse_mode="Markdown",
            reply_markup=build_keyboard(),
        )
    except Exception:
        pass  # Xabar o'zgarmagan bo'lsa Telegram xato beradi — ignore


async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🧮 *Calculator Bot — Yordam*\n\n"
        "• Raqamlar & operatorlar: `+ − × ÷`\n"
        "• `%` — foizga aylantirish\n"
        "• `±` — ishorni o'zgartirish\n"
        "• `⌫` — oxirgi belgini o'chirish\n"
        "• `C` — tozalash\n"
        "• `=` — hisoblash\n\n"
        "/start — botni qayta ishga tushirish"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()