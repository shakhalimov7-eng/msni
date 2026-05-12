
import os
import json
import logging
import asyncio
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

# Bot TOKEN — Vercel Dashboard'dan kiritiladi, topilmasa kod to'xtaydi
BOT_TOKEN = os.environ.get("8503981749:AAFoTPUke0G2h_Dd6weqGYNpRc69PmVynrQ")

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
                safe_expr = (
                    expr
                    .replace("×", "*")
                    .replace("÷", "/")
                    .replace("−", "-")
                    .replace("%", "/100")
                )
                raw = eval(safe_expr, {"__builtins__": {}})
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
        if just_equal and state["last_result"]:
            expr = state["last_result"]
        if expr and expr[-1] in ("+", "−", "×", "÷"):
            expr = expr[:-1]
        expr += btn
        state["just_equal"] = False
    elif btn == ".":
        if just_equal:
            expr = "0."
            state["just_equal"] = False
        elif not expr or expr[-1] in ("+", "−", "×", "÷"):
            expr += "0."
        elif "." not in expr.split("+")[-1].split("−")[-1].split("×")[-1].split("÷")[-1]:
            expr += "."
    else:
        if just_equal:
            expr = btn
            state["just_equal"] = False
        else:
            expr += btn

    state["expr"] = expr
    display = format_display(expr if not just_equal else state.get("last_result", expr), 
                             result_text if btn == "=" else None)

    try:
        await query.edit_message_text(
            text=display,
            parse_mode="Markdown",
            reply_markup=build_keyboard(),
        )
    except Exception:
        pass

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

# ─── Vercel Serverless Handler ────────────────────────────────────────────────

# Application-ni bir marta global yuklab olamiz
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(button_handler))

# Vercel talab qiladigan WSGI/ASGI asinxron kirish funksiyasi
async def handler(request):
    if request.method == "POST":
        try:
            # Vercel so'rovini matn ko'rinishida olamiz
            request_body = await request.text()
            data = json.loads(request_body)
            
            # Application ob'ektini asinxron ishga tushirish (agar boshlanmagan bo'lsa)
            if not app.running:
                await app.initialize()
            
            # Telegramdan kelgan update'ni asinxron qayta ishlash
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            
            return Response("OK", status=200)
        except Exception as e:
            logger.error(f"Xatolik: {e}")
            return Response(f"Error: {e}", status=500)
            
    return Response("Metod noto'g'ri", status=405)

# Vercel Python muhiti uchun ASGI wrapper (Response mosligi uchun)
class Response:
    def __init__(self, text, status=200):
        self.text = text
        self.status = status

    async def __call__(self, scope, receive, send):
        await send({
            'type': 'http.response.start',
            'status': self.status,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': self.text.encode('utf-8'),
        })

# Vercel aynan shu 'app' o'zgaruvchisini qidiradi
app_asgi = handler
