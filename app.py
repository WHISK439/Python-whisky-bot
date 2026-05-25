# ==============================================================================
# bot_maker.py - الإصدار النهائي (يعمل مثل app.py)
# ==============================================================================
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import threading
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================================================================
# الإعدادات
# ==============================================================================
MAKER_TOKEN = "8589873953:AAEOjxx3FV1YzORj8fEY6e785RxnAk3Wyp4"
MAKER_ADMIN_ID = 8562457386
DEVELOPER_LINK = "https://t.me/sayouda220309"

# ==============================================================================
# المسارات
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_FILE = os.path.join(BASE_DIR, "bots.json")

if not os.path.exists(BOTS_FILE):
    with open(BOTS_FILE, 'w') as f:
        json.dump({}, f)

maker_bot = telebot.TeleBot(MAKER_TOKEN)

# قاموس لتخزين البوتات العاملة
running_bots = {}

# ==============================================================================
# دالة تشغيل البوت (مثل app.py)
# ==============================================================================
def run_protect_bot(token, owner_id):
    """تشغيل بوت الحماية - نفس أسلوب app.py"""
    try:
        requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
    except:
        pass
    
    time.sleep(1)
    
    # إنشاء البوت
    bot = telebot.TeleBot(token)
    
    @bot.message_handler(commands=['start'])
    def start(message):
        welcome = f"""🔰 بوت حماية المجموعات

مرحباً {message.from_user.first_name}
أضفني كمشرف في مجموعتك"""
        bot.reply_to(message, welcome)
    
    @bot.message_handler(func=lambda m: True)
    def handle(message):
        if message.from_user.is_bot:
            return
        
        text = message.text.lower()
        
        # كلمات ممنوعة
        bad_words = ["كسمك", "قحبة", "شرموطة", "متناكه", "ابن", "كسم", "خخخخ", "سكس", "كسمين", "عرص", "احا", "انيك", "متناك", "خول", "معرص", "امك", "زباله", "انيكك", "بنيكك", "هنيكك", "زانيه", "دعاره", "سكساوي"]
        for word in bad_words:
            if word in text:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"💀 {message.from_user.first_name} مـمـنوع ي سسـافل 😹😹")
                except:
                    pass
                return
        
        # روابط
        if 'http' in text or 't.me' in text or '@' in text:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id, f"😂 {message.from_user.first_name}الـــࢪوابط ممـنوعه ي حـلـو 😂😂")
            except:
                pass
            return
    
    print(f"✅ بوت {token[:10]} يعمل...")
    
    try:
        bot.infinity_polling()
    except:
        pass

# ==============================================================================
# أوامر البوت الصانع
# ==============================================================================
@maker_bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🖤✨ إنشاء بــوت", callback_data="create"),
        InlineKeyboardButton("📋 البوتات بتـاعتك", callback_data="list")
    )
    maker_bot.reply_to(
        message,
        f"❤ تـنـصيب بـوتات حمـايةة\n\n@sayouda220309",
        reply_markup=keyboard
    )

@maker_bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "create":
        maker_bot.edit_message_text(
            "📤 خـش ؏ بــــوت @botfather وهـآت الـتوڪن بتاع بـوتك #يـحب",
            call.message.chat.id,
            call.message.message_id
        )
        maker_bot.register_next_step_handler(call.message, create_bot)
    
    elif call.data == "list":
        if not running_bots:
            maker_bot.answer_callback_query(call.id, "لا توجد بوتات عاملة", show_alert=True)
            return
        
        text = "🤖 البوتات العاملة حالياً:\n\n"
        for token in running_bots:
            try:
                r = requests.get(f"https://api.telegram.org/bot{token}/getMe")
                if r.status_code == 200:
                    username = r.json()['result']['username']
                    text += f"• @{username}\n"
            except:
                text += f"• {token[:15]}...\n"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back"))
        maker_bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data == "back":
        start(call.message)

def create_bot(message):
    token = message.text.strip()
    chat_id = message.chat.id
    
    msg = maker_bot.send_message(chat_id, "⏳ جاري إنشاء البوت...")
    
    # التحقق من التوكن
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        if r.status_code != 200:
            maker_bot.edit_message_text("❌ توكن غير صالح", chat_id, msg.message_id)
            return
        info = r.json()['result']
    except:
        maker_bot.edit_message_text("❌ توكن غير صالح", chat_id, msg.message_id)
        return
    
    # تشغيل البوت في ثريد منفصل (نفس app.py)
    bot_thread = threading.Thread(
        target=run_protect_bot,
        args=(token, message.from_user.id),
        daemon=True
    )
    bot_thread.start()
    
    # تخزين البوت
    running_bots[token] = bot_thread
    
    # رسالة نجاح
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📋 البوتات العاملة", callback_data="list"))
    
    maker_bot.edit_message_text(
        f"✅ تم إنشاء @{info['username']}\n🚀 يعمل الآن!",
        chat_id,
        msg.message_id,
        reply_markup=keyboard
    )

# ==============================================================================
# خادم الويب لـ KataBump
# ==============================================================================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"OK\nBots: {len(running_bots)}".encode())
    
    def log_message(self, *args):
        pass

def run_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🌐 خادم الويب على منفذ {port}")
    server.serve_forever()

# ==============================================================================
# التشغيل
# ==============================================================================
if __name__ == "__main__":
    print("="*50)
    print("🚀 صانع بوتات الحماية")
    print("="*50)
    
    # تشغيل خادم الويب
    threading.Thread(target=run_server, daemon=True).start()
    
    # تشغيل البوت الصانع
    try:
        maker_bot.infinity_polling()
    except Exception as e:
        print(f"⚠️ خطأ: {e}")
        time.sleep(5)