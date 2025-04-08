import requests
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, JobQueue

TOKEN = "8010159416:AAH11rRQnvRjjze5HkBZaEtxsxHZt0OU5Z8"
INDIANRAIL_API_KEY = "a3d7c21e857a632616ff93d54691d011"

# 🌐 Multilingual Support
LANGS = {
    "en": {
        "welcome": "Hi! What do you want to track? 🚦",
        "send_location": "📍 Please send your location:",
        "invalid_location": "❌ Please send your location using the 📍 button.",
        "near": "📍 You are near:",
        "no_place": "❌ No nearby places found.",
        "station": "🚉 Nearest Station:",
        "bus_stop": "🚌 Nearest Bus Stop:",
        "failed_schedule": "❌ Failed to fetch train schedule.",
        "emergency": "📞 Emergency Contacts:\nRailway Police: 182\nCustomer Care: 139\nLost & Found: Visit IRCTC.com",
        "history_title": "🕓 Your Recent Activity:",
        "no_history": "ℹ️ No history available.",
        "auto_enabled": "🔄 Auto updates enabled! You'll receive updates every 2 minutes.",
        "auto_disabled": "🚫 Auto updates stopped."
    },
    "hi": {
        "welcome": "नमस्ते! आप क्या ट्रैक करना चाहते हैं? 🚦",
        "send_location": "📍 कृपया अपना स्थान भेजें:",
        "invalid_location": "❌ कृपया 📍 बटन से स्थान भेजें।",
        "near": "📍 आप पास हैं:",
        "no_place": "❌ पास में कोई स्थान नहीं मिला।",
        "station": "🚉 निकटतम स्टेशन:",
        "bus_stop": "🚌 निकटतम बस स्टॉप:",
        "failed_schedule": "❌ ट्रेन शेड्यूल प्राप्त नहीं कर सके:",
        "emergency": "📞 आपातकालीन संपर्क:\nरेलवे पुलिस: 182\nग्राहक सेवा: 139\nलॉस्ट और फाउंड: IRCTC.com पर जाएं",
        "history_title": "🕓 आपकी पिछली गतिविधि:",
        "no_history": "ℹ️ कोई इतिहास उपलब्ध नहीं है।",
        "auto_enabled": "🔄 ऑटो अपडेट चालू! हर 2 मिनट में अपडेट मिलेगा।",
        "auto_disabled": "🚫 ऑटो अपडेट बंद कर दिया गया है।"
    },
    "mr": {
        "welcome": "नमस्कार! आपण काय ट्रॅक करू इच्छिता? 🚦",
        "send_location": "📍 कृपया आपले स्थान पाठवा:",
        "invalid_location": "❌ कृपया 📍 बटण वापरून स्थान पाठवा.",
        "near": "📍 आपण जवळ आहात:",
        "no_place": "❌ जवळ कोणतेही स्थान सापडले नाही.",
        "station": "🚉 सर्वात जवळचे रेल्वे स्थानक:",
        "bus_stop": "🚌 सर्वात जवळचा बस स्टॉप:",
        "failed_schedule": "❌ ट्रेन वेळापत्रक मिळवण्यात अयशस्वी.",
        "emergency": "📞 आपत्कालीन संपर्क:\nरेल्वे पोलिस: 182\nग्राहक सेवा: 139\nहरवलेले व सापडलेले: IRCTC.com",
        "history_title": "🕓 आपली अलीकडील क्रियाकलाप:",
        "no_history": "ℹ️ कोणताही इतिहास उपलब्ध नाही.",
        "auto_enabled": "🔄 ऑटो अपडेट्स सुरू! प्रत्येक 2 मिनिटांनी अद्यतने मिळतील.",
        "auto_disabled": "🚫 ऑटो अपडेट्स बंद करण्यात आले आहेत."
    }
}

# 🌍 Haversine Distance Calculation
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# 📍 Reverse Geocode

def get_location_name(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=14"
        headers = {"User-Agent": "TelegramBot-Tracker/1.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get("display_name", "Unknown Area")
    except:
        return "Unknown Area"

# 🚉 or 🚌 Nearest Place by Overpass
def find_nearest_place(lat, lon, place_type):
    try:
        if place_type == "train":
            query_filter = "node[\"railway\"=\"station\"]"
        elif place_type == "bus":
            query_filter = "node[\"amenity\"=\"bus_station\"] | node[\"highway\"=\"bus_stop\"]"
        else:
            return None

        query = f"""
        [out:json];
        (
            {query_filter}(around:30000,{lat},{lon});
        );
        out body;
        """
        response = requests.post("http://overpass-api.de/api/interpreter", data={"data": query})
        data = response.json()

        if not data.get("elements"):
            return None

        nearest = min(data["elements"], key=lambda el: haversine(lat, lon, el["lat"], el["lon"]))
        tags = nearest.get("tags", {})
        name = tags.get("name", "Unnamed Location")
        distance = int(haversine(lat, lon, nearest["lat"], nearest["lon"]))
        code = tags.get("ref") or tags.get("station_code") or name[:4].upper()
        return {"name": name, "distance": distance, "lat": nearest["lat"], "lon": nearest["lon"], "station_code": code}
    except:
        return None

# 🔘 /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
    [
        InlineKeyboardButton("English", callback_data="lang_en"),
        InlineKeyboardButton("हिन्दी", callback_data="lang_hi"),
        InlineKeyboardButton("मराठी", callback_data="lang_mr")
    ]
               ]
    await update.message.reply_text("Please select your language / कृपया अपनी भाषा चुनें", reply_markup=InlineKeyboardMarkup(keyboard))

async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    context.user_data["lang"] = lang
    context.user_data["history"] = []
    keyboard = [[InlineKeyboardButton("🚆 Train Tracker", callback_data="train"), InlineKeyboardButton("🚌 Bus Tracker", callback_data="bus")]]
    await query.edit_message_text(LANGS[lang]["welcome"], reply_markup=InlineKeyboardMarkup(keyboard))

# 🛰️ Handle Mode Button
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = query.data
    lang = context.user_data.get("lang", "en")
    keyboard = [[KeyboardButton("📍 Send Location", request_location=True)]]
    await query.message.reply_text(LANGS[lang]["send_location"], reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# 📍 Handle Location
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    if not update.message or not update.message.location:
        await update.effective_chat.send_message(LANGS[lang]["invalid_location"])
        return

    lat, lon = update.message.location.latitude, update.message.location.longitude
    mode = context.user_data.get("mode", "train")
    context.user_data.setdefault("history", []).append((lat, lon, mode))

    location_name = get_location_name(lat, lon)
    place_info = find_nearest_place(lat, lon, mode)
    reply_text = f"{LANGS[lang]['near']} *{location_name}*\n"

    if place_info:
        label = LANGS[lang]["station"] if mode == "train" else LANGS[lang]["bus_stop"]
        reply_text += f"{label} *{place_info['name']}* ({place_info['distance'] // 1000} km away)\n"
    else:
        reply_text += LANGS[lang]["no_place"]

    await update.message.reply_text(reply_text, parse_mode="Markdown")

# ⏱️ Auto Refresh Job
async def auto_update(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    user_data = context.job.data
    await context.bot.send_message(chat_id=chat_id, text="🔄 Auto update...")

# 🚨 Emergency Info
async def emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(LANGS[lang]["emergency"])

# 🕓 History
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    history = context.user_data.get("history", [])
    if not history:
        await update.message.reply_text(LANGS[lang]["no_history"])
        return
    text = LANGS[lang]["history_title"] + "\n"
    for i, (lat, lon, mode) in enumerate(history[-5:], 1):
        text += f"{i}. Mode: {mode} - {lat:.4f}, {lon:.4f}\n"
    await update.message.reply_text(text)

# 🚀 Run Bot

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("emergency", emergency))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CallbackQueryHandler(language_selection, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
