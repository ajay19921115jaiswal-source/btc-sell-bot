import os
import json
import logging
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

user_sessions = {}

ANALYZE_PROMPT = """You are a Polymarket crypto prediction market analyst. Analyze this market and respond ONLY with a JSON object, no markdown, no extra text.

Market: "{market}"
Asset: {asset}
Current Polymarket price: {price}

Respond with EXACTLY this JSON:
{{
  "direction": "YES" or "NO",
  "confidence": number between 50 and 95,
  "recommended_bet": "YES" or "NO" or "SKIP",
  "edge_percent": number between -20 and 40,
  "momentum": "Bullish" or "Bearish" or "Neutral",
  "crowd_bias": "Overpriced" or "Underpriced" or "Fair",
  "mispricing": number between -30 and 30,
  "reason": one sentence under 15 words explaining the call,
  "entry_tip": one sentence tip on entry timing under 15 words
}}"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    text = (
        f"👋 Welcome {user}! I'm your *Polymarket AI Bot*.\n\n"
        "I analyze crypto prediction markets and give you:\n"
        "• Confidence scores\n"
        "• YES/NO direction calls\n"
        "• Edge percentage\n"
        "• Entry tips\n\n"
        "Use /analyze to start analyzing a market.\n"
        "Use /log to see your trade log.\n"
        "Use /help for all commands."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Commands:*\n\n"
        "/analyze — Analyze a Polymarket market\n"
        "/log — View your trade log\n"
        "/clear — Clear your trade log\n"
        "/help — Show this message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_sessions[uid] = {"step": "market"}
    await update.message.reply_text(
        "📊 *Step 1/3* — Paste the market question:\n\n"
        "_Example: Will BTC be above $70k by June 30?_",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    session = user_sessions.get(uid, {})

    if session.get("step") == "market":
        session["market"] = text
        session["step"] = "price"
        user_sessions[uid] = session
        await update.message.reply_text(
            "💰 *Step 2/3* — What's the current market price?\n\n"
            "_Example: 0.44 (means 44¢ = 44% probability)_",
            parse_mode="Markdown"
        )

    elif session.get("step") == "price":
        session["price"] = text
        session["step"] = "asset"
        user_sessions[uid] = session

        keyboard = [
            [InlineKeyboardButton("BTC", callback_data="asset_BTC"),
             InlineKeyboardButton("ETH", callback_data="asset_ETH")],
            [InlineKeyboardButton("SOL", callback_data="asset_SOL"),
             InlineKeyboardButton("BNB", callback_data="asset_BNB")],
            [InlineKeyboardButton("Other", callback_data="asset_Other")]
        ]
        await update.message.reply_text(
            "🪙 *Step 3/3* — Select the crypto asset:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    else:
        await update.message.reply_text(
            "Use /analyze to start a new analysis, or /help for commands."
        )


async def asset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    asset = query.data.replace("asset_", "")
    session = user_sessions.get(uid, {})

    if session.get("step") != "asset":
        await query.edit_message_text("Session expired. Use /analyze to start again.")
        return

    session["asset"] = asset
    session["step"] = "analyzing"
    user_sessions[uid] = session

    await query.edit_message_text(f"🤖 Analyzing {asset} market... please wait.")

    try:
        prompt = ANALYZE_PROMPT.format(
            market=session["market"],
            asset=asset,
            price=session["price"]
        )
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip().replace("```json", "").replace("```", "")
        result = json.loads(raw)

        conf = round(result["confidence"])
        edge = round(result["edge_percent"])
        misprice = round(result["mispricing"])
        direction = result["direction"]
        rec = result["recommended_bet"]

        conf_bar = "🟢" if conf >= 70 else "🟡" if conf >= 60 else "🔴"
        dir_emoji = "⬆️" if direction == "YES" else "⬇️"
        rec_emoji = "✅" if rec == "YES" else "❌" if rec == "NO" else "⏸️"

        response = (
            f"{'='*30}\n"
            f"📊 *POLYMARKET ANALYSIS*\n"
            f"{'='*30}\n\n"
            f"*Market:* {session['market'][:60]}...\n"
            f"*Asset:* {asset} | *Price:* {session['price']}\n\n"
            f"{dir_emoji} *Direction:* {direction}\n"
            f"{conf_bar} *Confidence:* {conf}%\n"
            f"{rec_emoji} *Recommended Bet:* {rec}\n\n"
            f"📈 *Edge:* {'+' if edge >= 0 else ''}{edge}%\n"
            f"⚖️ *Crowd bias:* {result['crowd_bias']}\n"
            f"📉 *Mispricing:* {'+' if misprice >= 0 else ''}{misprice}%\n"
            f"🌊 *Momentum:* {result['momentum']}\n\n"
            f"💡 *Reason:* {result['reason']}\n"
            f"⏰ *Entry tip:* {result['entry_tip']}\n"
            f"{'='*30}"
        )

        if uid not in user_sessions:
            user_sessions[uid] = {}
        if "log" not in user_sessions[uid]:
            user_sessions[uid]["log"] = []

        user_sessions[uid]["log"].append({
            "asset": asset,
            "direction": direction,
            "price": session["price"],
            "confidence": conf,
            "rec": rec
        })

        del user_sessions[uid]["step"]

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=response,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Analysis failed. Please try /analyze again."
        )


async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    log = user_sessions.get(uid, {}).get("log", [])

    if not log:
        await update.message.reply_text("No trades logged yet. Use /analyze to start!")
        return

    lines = ["📋 *Your Trade Log:*\n"]
    for i, t in enumerate(reversed(log[-10:]), 1):
        emoji = "⬆️" if t["direction"] == "YES" else "⬇️"
        rec = "✅" if t["rec"] == "YES" else "❌" if t["rec"] == "NO" else "⏸️"
        lines.append(f"{i}. {emoji} *{t['asset']}* {t['direction']} @ {t['price']} — {t['confidence']}% conf {rec}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_sessions:
        user_sessions[uid]["log"] = []
    await update.message.reply_text("✅ Trade log cleared!")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("log", log_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CallbackQueryHandler(asset_callback, pattern="^asset_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
