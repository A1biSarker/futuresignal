import random
import pytz
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# --- CONFIGURATION ---
BOT_TOKEN = "8137290461:AAFyJ3clD6ewADQ-iLG4J8C-nV0GpfaDVkM"
ALLOWED_CHAT_IDS = [7718800367, 7669227388,6475709676]

USER_DATA = {}
DIRECTIONS = ["CALL", "PUT"]

# --- PAIR LISTS ---
REGULAR_PAIRS = [
    "EURJPY", "EURUSD", "USDCHF", "GBPJPY", "AUDCHF", "AUDCAD", "AUDJPY",
    "CADJPY", "AUDUSD", "CADCHF", "USDJPY", "USDCAD", "EURCAD", "EURGBP",
    "GBPUSD", "NZDUSD", "NZDJPY", "CHFJPY", "GBPCHF", "EURAUD", "GBPAUD",
    "EURCHF"
]

POCKET_OPTION_FULL_PAIRS = [
    "AUDCAD_otc", "AUDNZD_otc", "CADCHF_otc", "CHFJPY_otc", "EURRUB_otc", "EURTRY_otc",
    "EURUSD_otc", "JODCNY_otc", "KESUSD_otc", "NZDJPY_otc", "USDCNH_otc", "USDINR_otc",
    "USDJPY_otc", "USDRUB_otc", "USDTHB_otc", "EURHUF_otc", "EURCHF_otc", "AUDCHF_otc",
    "AUDUSD_otc", "QARCNY_otc", "USDCAD_otc", "USDPKR_otc", "EURNZD_otc", "GBPJPY_otc",
    "AUDJPY_otc", "EURJPY_otc", "USDBRL_otc", "CADJPY_otc", "SARCNY_otc", "NGNUSD_otc",
    "USDCHF_otc", "CHFNOK_otc", "UAHUSD_otc", "USDCOP_otc", "USDSGD_otc", "MADUSD_otc",
    "GBPAUD_otc", "USDBDT_otc", "AEDCNY_otc", "USDPHP_otc", "ZARUSD_otc", "USDDZD_otc",
    "USDMYR_otc", "USDIDR_otc", "USDVND_otc", "USDCLP_otc", "USDARS_otc", "USDMXN_otc",
    "BHDCNY_otc", "LBPUSD_otc", "NZDUSD_otc", "GBPUSD_otc", "USDEGP_otc", "EURGBP_otc",
    "OMRCNY_otc"
]

QUOTEX_FULL_PAIRS = [
    "EURSGD_otc", "USDCHF_otc", "USDARS_otc", "USDZAR_otc",
    "GBPNZD_otc", "CADCHF_otc", "NZDUSD_otc", "NZDJPY_otc", "USDDZD_otc",
    "AUDNZD_otc", "USDPKR_otc", "EURNZD_otc", "USDINR_otc", "USDPHP_otc",
    "USDBRL_otc", "USDEGP_otc", "NZDCHF_otc", "USDCOP_otc", "USDIDR_otc",
    "USDNGN_otc", "USDMXN_otc", "USDTRY_otc", "NZDCAD_otc", "USDBDT_otc"
]

UTC_MAP = {
    "UTC+6": "Asia/Dhaka",
    "UTC+5:30": "Asia/Kolkata",
    "UTC-3": "America/Sao_Paulo",
    "UTC-5": "US/Eastern",
    "UTC-8": "US/Pacific",
}

# --- GLOBAL STORAGE FOR SIGNALS ---
recent_signals = []  # list of dicts: {"pair": str, "time": str, "direction": str, "result": str or None}

# --- UTILITIES ---

def is_allowed(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS

def get_timezone_from_utc(text):
    key = text.upper().replace(" ", "")
    return pytz.timezone(UTC_MAP.get(key)) if key in UTC_MAP else None

def get_pairs(platform, mode, tz):
    now = datetime.now(tz)
    is_weekend = now.weekday() in (5, 6)

    if mode == "otc":
        return QUOTEX_FULL_PAIRS if platform == "quotex" else POCKET_OPTION_FULL_PAIRS

    if mode == "real":
        if is_weekend:
            return []
        return REGULAR_PAIRS

    if mode == "mix":
        otc_list = QUOTEX_FULL_PAIRS if platform == "quotex" else POCKET_OPTION_FULL_PAIRS
        if is_weekend:
            return otc_list
        return REGULAR_PAIRS + otc_list

    return []

def generate_raw_signals(pairs, start_time, end_time, tz):
    if not pairs:
        return []

    signals_data = []
    today = datetime.now(tz).date()
    try:
        start_dt = tz.localize(datetime.combine(today, datetime.strptime(start_time, "%H:%M").time()))
        end_dt = tz.localize(datetime.combine(today, datetime.strptime(end_time, "%H:%M").time()))
    except:
        return []

    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    current_time = start_dt
    last_pair = None

    while current_time < end_dt:
        block_end = current_time + timedelta(minutes=10)
        signal_count = random.choice([2, 3])
        minute_points = sorted(random.sample(range(10), min(signal_count, 10)))

        for m in minute_points:
            signal_time = current_time + timedelta(minutes=m)
            if signal_time >= end_dt:
                continue

            pair = random.choice(pairs)
            if pair == last_pair and len(pairs) > 1:
                pair = random.choice([p for p in pairs if p != last_pair])

            direction = random.choice(DIRECTIONS)

            signals_data.append({
                "pair": pair,
                "time": signal_time.strftime('%H:%M'),
                "direction": direction,
                "result": None  # result will be updated later
            })

            recent_signals.append(signals_data[-1])
            last_pair = pair

        current_time = block_end

    return signals_data

def cumulative_summary():
    if not recent_signals:
        return "<pre>No signals yet.</pre>"

    wins = sum(1 for s in recent_signals if s.get("result") == "PROFIT")
    losses = sum(1 for s in recent_signals if s.get("result") == "LOSS")
    total = wins + losses
    accuracy = round((wins / total) * 100, 1) if total else 0.0

    lines = []
    lines.append("┌──────────────────────────────┐")
    lines.append("│       RESULT SHOWED          │")
    lines.append("└──────────────────────────────┘")
    lines.append("")

    for sig in recent_signals[-10:]:
        check = "✅" if sig.get("result") == "PROFIT" else "❌" if sig.get("result") == "LOSS" else "⏳"
        dir_str = "↑ CALL" if sig["direction"] == "CALL" else "↓ PUT"
        status = "PROFIT" if sig.get("result") == "PROFIT" else "LOSS" if sig.get("result") == "LOSS" else "PENDING"
        line = f"{check} {sig['pair']:<15} {sig['time']} {dir_str} {status} {check}"
        lines.append(line)

    lines.append("")
    lines.append("┌──────────────────────────────┐")
    lines.append(f"│ ✅ TOTAL WINS:     {wins:>3}         │")
    lines.append(f"│ ❌ TOTAL LOSSES:   {losses:>3}         │")
    lines.append(f"│ 💀 ACCURACY:       {accuracy:>5.1f}%     │")
    lines.append("└──────────────────────────────┘")

    return "<pre>" + "\n".join(lines) + "</pre>"

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_allowed(chat_id):
        await update.message.reply_text("Access denied.")
        return
    USER_DATA[chat_id] = {"step": "timezone"}
    await update.message.reply_text("Enter Timezone (UTC+6, UTC-3, UTC+5:30):")

async def platform_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_allowed(chat_id) or chat_id not in USER_DATA:
        return
    platform = update.message.text.replace("/", "").lower()
    USER_DATA[chat_id].update({"platform": platform, "step": "mode"})
    await update.message.reply_text(f"Selected: {platform.upper()}\n\nReply with Mode:\n- Real Market\n- OTC\n- Mix")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_allowed(chat_id) or chat_id not in USER_DATA:
        return

    text = update.message.text.strip()
    data = USER_DATA[chat_id]

    if data["step"] == "timezone":
        tz = get_timezone_from_utc(text)
        if not tz:
            await update.message.reply_text("Invalid format. Use UTC+6 etc.")
            return
        data.update({"timezone": tz, "step": "wait_for_platform"})
        await update.message.reply_text("Timezone accepted. Use /quotex or /pocketoption")

    elif data["step"] == "mode":
        mode_input = text.lower()
        if "otc" in mode_input:
            selected_mode = "otc"
        elif "real" in mode_input:
            selected_mode = "real"
        else:
            selected_mode = "mix"

        data.update({"mode": selected_mode, "step": "start_time"})
        await update.message.reply_text(f"Mode set to: {selected_mode.upper()}\nEnter Start Time (HH:MM):")

    elif data["step"] == "start_time":
        data.update({"start_time": text.replace(".", ":"), "step": "end_time"})
        await update.message.reply_text("Enter End Time (HH:MM):")

    elif data["step"] == "end_time":
        try:
            end_t = text.replace(".", ":")
            pairs = get_pairs(data["platform"], data["mode"], data["timezone"])

            if not pairs and data["mode"] == "real":
                await update.message.reply_text("Real market is closed on weekends! Please use OTC or MIX mode.")
                USER_DATA.pop(chat_id, None)
                return

            raw_signals = generate_raw_signals(pairs, data["start_time"], end_t, data["timezone"])

            if not raw_signals:
                await update.message.reply_text("No signals available for this selection.")
            else:
                output = f"<b>{data['platform'].upper()} {data['mode'].upper()} SIGNALS</b>\n"
                output += "--------------------------------\n"
                for s in raw_signals:
                    pair_fixed = s['pair'].ljust(15)
                    output += f"M1 | {pair_fixed} | {s['time']} | {s['direction']}\n"
                output += "--------------------------------"

                # Send signals list
                await update.message.reply_text(f"<code>{output}</code>", parse_mode="HTML")

                # Auto send summary in the same chat
                total_signals = len(recent_signals)
                if total_signals >= 10 and total_signals % 5 == 0:
                    summary_text = cumulative_summary()
                    await update.message.reply_text(summary_text, parse_mode="HTML")

            USER_DATA.pop(chat_id, None)
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_allowed(chat_id):
        await update.message.reply_text("Access denied.")
        return

    summary_text = cumulative_summary()
    await update.message.reply_text(summary_text, parse_mode="HTML")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["quotex", "pocketoption"], platform_select))
    app.add_handler(CommandHandler("sum", show_summary))  # /sum command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is active...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
