import requests
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# 🔑 Replace with your Telegram Bot Token
TOKEN = "8010159416:AAH11rRQnvRjjze5HkBZaEtxsxHZt0OU5Z8"

# 🌍 Haversine Distance Calculation
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = map(math.radians, [lat1, lat2])
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# 📍 Get Location Name using Nominatim
def get_location_name(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=14"
        headers = {"User-Agent": "TelegramBot-Tracker/1.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get("display_name", "Unknown Area")
    except:
        return "Unknown Area"

# 🚉 Find Nearest Place by Overpass (Generic for train/bus)
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
        return f"{name} ({distance // 1000} km away)"
    except:
        return None

# 🔘 /start Command with Inline Buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🚆 Train Tracker", callback_data="train"),
        InlineKeyboardButton("🚌 Bus Tracker", callback_data="bus")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Hi! What do you want to track? 🚦", reply_markup=reply_markup)

# 🔘 Handle Button Selection
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = query.data
    keyboard = [[KeyboardButton("📍 Send Location", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await query.message.reply_text("📍 Please send your location:", reply_markup=reply_markup)

# 📍 Handle Location Messages
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.location:
        await update.effective_chat.send_message("❌ Please send your location using the 📍 button.")
        return

    lat = update.message.location.latitude
    lon = update.message.location.longitude
    mode = context.user_data.get("mode", "train")

    location_name = get_location_name(lat, lon)
    result = find_nearest_place(lat, lon, mode)

    reply_text = f"📍 You are near: *{location_name}*\n"
    if result:
        label = "🚉 Nearest Station:" if mode == "train" else "🚌 Nearest Bus Stop:"
        reply_text += f"{label} *{result}*"
    else:
        reply_text += "❌ No nearby places found."

    await update.message.reply_text(reply_text, parse_mode="Markdown")

# 🚀 Start the Bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
