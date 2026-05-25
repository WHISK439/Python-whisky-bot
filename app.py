import logging
import time
import re
import asyncio
import random
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonCommands, MenuButtonWebApp, MenuButtonDefault, BotCommand, BotCommandScopeChat, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler, CallbackQueryHandler
from telegram.constants import ParseMode
from typing import Dict, Set, List, Tuple, Optional
from datetime import datetime, timedelta
import sqlite3
import json
import os

# إعدادات البوت
TOKEN = "8268945183:AAH5ADVWn6O3UvLqMXcgCUIVz4QXH1kvMWw"
DEVELOPER_NAME = "𝐖𝐇𝐈𝗦𝗞𝗬 𝗘𝗟𝗬𝗢𝐔َ𝗧𝐔𝗕𝗘𝗥​ 𓊈𝑽꯭𝑰꯭𝑷ࠡࠡࠡࠡࠢ𓊉"
DEVELOPER_ID = 8562457386
DEVELOPER_LINK = "https://t.me/sayouda220309"

# ============ قناة التحديثات الجديدة ============
CHANNEL_USERNAME = "Whiskybots"  # يوزر القناة بدون @
CHANNEL_LINK = "https://t.me/Whiskybots"

# إعداد القائمة السوداء للكلمات المسيئة - محدثة مع الكلمات الجديدة
BAD_WORDS = [
    # الكلمات الأصلية
    "كسمك", "ابن المتناكه", "قحبة", "شرموطة", "متناكه", "ديوس",
    "متناك", "سخيف", "بضان", "بيض", "ينعل", "دين اهلك",
    "امك", "يا ابن", "يلعن", "عاهر", "زانية", "فحل",
    "منيوك", "منيوكة", "دعارة", "شراميط", "قحاب",
    
    # الكلمات الجديدة المضافة
    "كسم", "سكس", "خخخخ", "متناك", "بيتناك", "ينيكك", "ينيك", 
    "كسمين امك", "امك", "هلس", "علق", "نجس", "منيوك", "منيوكه",
    "نط", "تعال اركبك", "تعالي اركبك", "تعالى اركبك", "زوبري", "زبي",
    "انيك", "انيكك", "شرموط", "معرص", "عرص", "مستجد", "دين اهلك",
    "دين امك", "ابوك", "خول", "عرصجي", "مايكي", "مستهلس", "كذاب"
]

# منع جميع الروابط بشكل كامل
ALLOWED_DOMAINS = []

# مخزن مؤقت لتحسين الأداء
USER_WARNINGS: Dict[int, Dict[str, int]] = {}
USER_WARNINGS_DETAILS: Dict[int, list] = {}  # لتخزين تفاصيل التحذيرات
MESSAGE_CACHE: Set[int] = set()
MAX_WARNINGS = 4  # تم التحديث إلى 4 إنذارات

# ============ متغيرات جديدة لعدد رسائل الأعضاء ============
USER_MESSAGES_COUNT: Dict[int, Dict[int, int]] = {}  # {chat_id: {user_id: message_count}}

# ============ متغيرات نظام الزواج ============
# قاعدة بيانات SQLite للزواج
MARRIAGE_DB_PATH = "marriage_data.db"

def init_marriage_db():
    """تهيئة قاعدة بيانات الزواج"""
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS marriages (
            chat_id INTEGER,
            user_id INTEGER,
            spouse_id INTEGER,
            user_name TEXT,
            spouse_name TEXT,
            user_username TEXT,
            spouse_username TEXT,
            marriage_date TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_marriage_db()

def get_marriage(chat_id: int, user_id: int) -> Optional[dict]:
    """الحصول على معلومات زواج المستخدم"""
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM marriages WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'chat_id': row[0],
            'user_id': row[1],
            'spouse_id': row[2],
            'user_name': row[3],
            'spouse_name': row[4],
            'user_username': row[5],
            'spouse_username': row[6],
            'marriage_date': row[7]
        }
    return None

def add_marriage(chat_id: int, user_id: int, spouse_id: int, user_name: str, spouse_name: str, user_username: str, spouse_username: str):
    """إضافة زواج جديد"""
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    marriage_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''
        INSERT OR REPLACE INTO marriages (chat_id, user_id, spouse_id, user_name, spouse_name, user_username, spouse_username, marriage_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, user_id, spouse_id, user_name, spouse_name, user_username, spouse_username, marriage_date))
    conn.commit()
    conn.close()

def remove_marriage(chat_id: int, user_id: int):
    """حذف زواج"""
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM marriages WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()

def get_spouse(chat_id: int, user_id: int) -> Optional[dict]:
    """الحصول على معلومات الزوج/ة من خلال البحث في كلا الاتجاهين"""
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM marriages WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    row = c.fetchone()
    if not row:
        c.execute("SELECT * FROM marriages WHERE chat_id = ? AND spouse_id = ?", (chat_id, user_id))
        row = c.fetchone()
    conn.close()
    if row:
        return {
            'chat_id': row[0],
            'user_id': row[1],
            'spouse_id': row[2],
            'user_name': row[3],
            'spouse_name': row[4],
            'user_username': row[5],
            'spouse_username': row[6],
            'marriage_date': row[7]
        }
    return None

# ============ متغيرات نظام القفل المؤقت ============
LOCKED_CHATS: Dict[int, bool] = {}  # تخزين حالة القفل للمجموعات

# ============ متغيرات الأعضاء المكتومين ============
MUTED_USERS: Dict[int, Dict[int, datetime]] = {}  # {chat_id: {user_id: mute_until}}

# ============ متغيرات القائمة السفلية ============
USER_MENU_STATE: Dict[int, str] = {}  # تخزين حالة القائمة لكل مستخدم

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# أنماط الروابط
LINK_PATTERNS = [
    r'https?://[^\s]+',
    r't\.me/[^\s]+',
    r'telegram\.me/[^\s]+',
    r'telegram\.dog/[^\s]+',
    r'@[a-zA-Z0-9_]+',
    r'[a-zA-Z0-9]+\.(com|org|net|io|info|xyz|tk|ml|ga|cf|gq|ru|cn|uk|de|fr|es|it|ae|sa|eg)[^\s]*',
]

# رسائل ترحيب متنوعة
WELCOME_MESSAGES = [
    "🎉 أهلاً وسهلاً بك في عائلتنا",
    "🤝 نورت المجموعة بحضورك",
    "✨ انضمامك شرف لنا",
    "🌸 أهلاً بك صديقنا الجديد",
    "🌟 مرحباً بك في منزل الجميع",
    "💫 سعداء بانضمامك إلينا",
    "🎊 أهلًا وسهلًا بيك",
    "🌈 نورت الدنيا علينا",
]

# قائمة الألوان للتصميم
COLORS = {
    'main': '✦',
    'sep': '═',
    'header': '✦',
    'border': '╌'
}

# وسائط تزيين للترند
TREND_MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

# ============ نظام التفاعل مع الأعضاء - محدث بشكل كبير مع الكلمات الجديدة ============
INTERACTION_RESPONSES = {
    # الردود العامة لجميع الأعضاء - سيتم البحث عن هذه الكلمات في أي مكان بالرسالة
    "😂": "تـدوم ءالـضـحڪه يحب 💕✨",
    "عاملين ايه": "الحمدلله يحب وانت عـآمل اي",
    "عاملين اي": "الحمدلله يحب وانت عـآمل اي",
    "رحتو فين": "بيڪلمو ومشغولين مع نسـوان 😂",
    "بحبك": "يدوم الحب بينڪو ❤",
    "شخرت": "عـيب",
    "سحوره": "موجوده وشغاله يعم زي الفل 😂❤",
    "بوسه": "سسـآفل 🫦",
    "وسكي": "مـــطـوࢪي وحبـيبـي مـش فـاضي دلـوقت 😭 💔",
    "حد هنا": "مشغولين مع النسوان بتاعتهم 😂✨",
    "ممكن نتعرف": "سحوره بـنت ويـسڪي \nمطـوري:  ويـسڪي الــيوتيوبـࢪ \nوظيـفتي حمـآيه الــبآر ده 😂",
    "عرفوني عليكو": "سحوره بـنت ويـسڪي \nمطـوري:  ويـسڪي الــيوتيوبـࢪ \nوظيـفتي حمـآيه الــبآر ده 😂",
    "جوزوني": "اڪتب أمر ( زواج)  وهجوزك 😂",
    "زهقان": "مالك يسطا اي الـ مزعلك، في حاجه لو في حاجة معاك ممكن تفضفض وتحكي مع اخواتك هنا في البار 🎀",
    "مبضون": "مالك يسطا اي الـ مزعلك، في حاجه لو في حاجة معاك ممكن تفضفض وتحكي مع اخواتك هنا في البار 🎀",
    "تعبان": "مالك يسطا اي الـ مزعلك، في حاجه لو في حاجة معاك ممكن تفضفض وتحكي مع اخواتك هنا في البار 🎀",
    "مدايق": "مالك يسطا اي الـ مزعلك، في حاجه لو في حاجة معاك ممكن تفضفض وتحكي مع اخواتك هنا في البار 🎀",
    "الحمدلله": "دايما يحب ❤",
    "كويس": "دايما يحب ❤",
    
    # الكلمات الجديدة المضافة
    "السلام عليكم": "وعليڪم السلام نورت يغالي 🫶🏻",
    "سلام عليكم": "وعليڪم السلام نورت يغالي 🫶🏻",
    "نتعرف": "سـحوره 😘",
    "اسمك": "سـحوره 😘",
    "بوت": "اسمي سـحوࢪه يحب لـو عـاوز حاجه انا موجوده",
    "هههه": "تدوم ♡♡",
    "قلبي": "يسلم قلبك 💚",
    "اي": "ألعب بعـيد يسطا 😂😂",
    "ايه": "إلعـب بعيـد يسطـآ 😂😂",
    "همووت": "مووت بعيد يـعم  😂❤️‍🩹",
    "عامله اي": "كويسه الحمدلله وانت/ي",
    "عامله ايه": "كويسه الحمدلله وانت/ي",
    "احا": "عـيب",
    "مالك": "مش عارفه المود خرباان",
}

# رسالة خاصة للمطور عند كتابة "سحوره"
DEVELOPER_SOHOURA_RESPONSE = "❤ قـلب سحـوره ي ويـسڪي بحبڪ 💙، عامـل اي إنهارده"

# رسالة عند استخدام أدوات النداء
MENTION_RESPONSE = "شڪلو مـش فــــآضي يحـب، أرمـي رسـآلتك واســـتنى لـحد ما يــرد عليڪ 🍷"

# أدوات النداء
MENTION_TOOLS = ["ي", "يا"]

# ============ قوائم أوامر المطور الجديدة ============

# قائمة رسائل التحفيل
TAHFIL_MESSAGES = [
    "انت ياض ي إيحه ي تلقيحه ي صبونه من غير ريحه 😂🙊",
    "اتكسف ياض عاوز اشوفك بتعيط ههههه 😄",
    "اشوفك مره تانيه بتشتم عمك ( WHISKEY ) او بتبعبص في قوانين البار 😑",
    "خخخ انتي ضعيف مووت اتكلم ياض و رد عليا زي ما بكلمك",
    "هههه مش شايفك شكلك علء فشخ ، بطل خولنه ياض ي مايكي",
    "اخر زوبر هيجي في خورمك مش هتستحملو ، انشف ياض ي عرصجي ي معرص ، تع هنا متجريش متخافش لسه التقيل مجاش ههههه"
]

# قائمة أخطاء البوت المسجلة
BOT_ERRORS: List[Dict] = []

# ============ دوال الإذاعة الجديدة ============

def get_all_users_from_database() -> List[int]:
    """الحصول على جميع المستخدمين من قاعدة البيانات"""
    try:
        # استخدام قاعدة البيانات لحفظ المستخدمين
        conn = sqlite3.connect("users_data.db")
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("SELECT user_id FROM users")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users
    except Exception as e:
        logger.error(f"خطأ في جلب المستخدمين: {e}")
        return []

def save_user_to_database(user_id: int, username: str, first_name: str):
    """حفظ المستخدم في قاعدة البيانات"""
    try:
        conn = sqlite3.connect("users_data.db")
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في حفظ المستخدم: {e}")

def save_broadcast_log(message_text: str, sent_count: int, failed_count: int, broadcast_type: str):
    """حفظ سجل الإذاعة"""
    log_file = "broadcast_logs.json"
    log_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message_text[:100],
        "sent": sent_count,
        "failed": failed_count,
        "type": broadcast_type
    }
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        logs.insert(0, log_entry)
        logs = logs[:50]
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ سجل الإذاعة: {e}")

def get_broadcast_logs() -> List[Dict]:
    """جلب سجل الإذاعات"""
    log_file = "broadcast_logs.json"
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []

# ============ قائمة الأزرار السفلية الجديدة مع تلوين الأزرار ============

def get_main_menu_keyboard():
    """إنشاء لوحة المفاتيح السفلية الرئيسية مع تلوين الأزرار"""
    keyboard = [
        [KeyboardButton("📋 القائمة الرئيسية")],
        [KeyboardButton("👤 أوامر الأعضاء"), KeyboardButton("👮 أوامر المشرفين")],
        [KeyboardButton("💬 تفاعل ذكي"), KeyboardButton("📊 ترند وإحصائيات")],
        [KeyboardButton("❤️ زواج وطلاق"), KeyboardButton("👑 المطور")],
        [KeyboardButton("➕ أضفني إلى مجموعتك"), KeyboardButton("📢 قناة التحديثات")],
        [KeyboardButton("⚡ أوامـــر الـــمطور ⚡"), KeyboardButton("📢 الإذاعة المركزية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_member_commands_keyboard():
    """لوحة مفاتيح أوامر الأعضاء"""
    keyboard = [
        [KeyboardButton("📊 رسائلي"), KeyboardButton("🏆 ترند")],
        [KeyboardButton("⚠️ تحذيراتي"), KeyboardButton("🆔 ID")],
        [KeyboardButton("👑 المالك"), KeyboardButton("📜 القوانين")],
        [KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_commands_keyboard():
    """لوحة مفاتيح أوامر المشرفين"""
    keyboard = [
        [KeyboardButton("🔨 حظر"), KeyboardButton("🚫 طرد")],
        [KeyboardButton("🔇 كتم"), KeyboardButton("🔊 إلغاء كتم")],
        [KeyboardButton("📌 تثبيت"), KeyboardButton("🗑️ حذف")],
        [KeyboardButton("🔒 قفل مؤقت"), KeyboardButton("🔓 فتح")],
        [KeyboardButton("⚠️ تحذير"), KeyboardButton("🧹 حذف التحذيرات")],
        [KeyboardButton("👑 رفع مشرف"), KeyboardButton("⬇️ عزل مشرف")],
        [KeyboardButton("ℹ️ معلومات"), KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("🔙 رجوع")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_interaction_keyboard():
    """لوحة مفاتيح التفاعل الذكي"""
    keyboard = [
        [KeyboardButton("😂"), KeyboardButton("❤️")],
        [KeyboardButton("بحبك"), KeyboardButton("بوسه")],
        [KeyboardButton("سحوره"), KeyboardButton("وسكي")],
        [KeyboardButton("السلام عليكم"), KeyboardButton("هههه")],
        [KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_trend_keyboard():
    """لوحة مفاتيح الترند والإحصائيات"""
    keyboard = [
        [KeyboardButton("📊 إحصائياتي"), KeyboardButton("🏆 أفضل 5")],
        [KeyboardButton("👥 عدد الأعضاء"), KeyboardButton("📈 نشاط المجموعة")],
        [KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_marriage_keyboard():
    """لوحة مفاتيح الزواج والطلاق"""
    keyboard = [
        [KeyboardButton("💍 زواج"), KeyboardButton("💔 طلاق")],
        [KeyboardButton("👰 المتزوجين"), KeyboardButton("📜 سجل الزواج")],
        [KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_developer_keyboard():
    """لوحة مفاتيح المطور"""
    keyboard = [
        [KeyboardButton("👨‍💻 معلومات المطور")],
        [KeyboardButton("📞 التواصل مع المطور")],
        [KeyboardButton("📢 قناة التحديثات")],
        [KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("⚡ أوامـــر الـــمطور ⚡")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_dev_only_keyboard():
    """لوحة مفاتيح خاصة بالمطور فقط - أوامر المطور بشكل احترافي مع تلوين الأزرار"""
    keyboard = [
        [KeyboardButton("🎭 تحفيل"), KeyboardButton("💙 معلش يحب")],
        [KeyboardButton("📢 إرسال رسالة جماعية"), KeyboardButton("🗑️ حذف 200")],
        [KeyboardButton("📊 إحصائيات البوت"), KeyboardButton("🧹 تنظيف البيانات")],
        [KeyboardButton("👥 إحصائيات الأعضاء"), KeyboardButton("🔒 إحصائيات القفل")],
        [KeyboardButton("💍 إحصائيات الزواج"), KeyboardButton("💬 إحصائيات التفاعل")],
        [KeyboardButton("📋 عرض جميع المجموعات"), KeyboardButton("🔄 تحديث البيانات")],
        [KeyboardButton("➕ أضف البوت لمجموعتك")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_broadcast_menu_keyboard():
    """لوحة مفاتيح الإذاعة مع تلوين الأزرار"""
    keyboard = [
        [KeyboardButton("📢 إذاعة للجميع")],
        [KeyboardButton("📨 إذاعة لمستخدم محدد")],
        [KeyboardButton("📊 سجل الإذاعات")],
        [KeyboardButton("🔙 رجوع للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============ دوال الإذاعة المتقدمة ============

async def broadcast_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str, user_id: int):
    """إرسال رسالة لجميع المستخدمين المسجلين"""
    if user_id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")
        return False, 0, 0
    
    users = get_all_users_from_database()
    sent_count = 0
    failed_count = 0
    
    status_msg = await update.message.reply_text("⏳ جاري إرسال الإذاعة لجميع المستخدمين...")
    
    for uid in users:
        try:
            await context.bot.send_message(uid, message_text, parse_mode='HTML')
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            logger.error(f"فشل إرسال للمستخدم {uid}: {e}")
    
    await status_msg.edit_text(
        f"✅ **تم إرسال الإذاعة بنجاح!**\n\n"
        f"📊 **الإحصائيات:**\n"
        f"✓ تم الإرسال: {sent_count}\n"
        f"✗ فشل: {failed_count}\n"
        f"👥 إجمالي المستخدمين: {len(users)}",
        parse_mode='Markdown'
    )
    
    save_broadcast_log(message_text, sent_count, failed_count, "لجميع المستخدمين")
    return True, sent_count, failed_count

async def broadcast_to_specific_user(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int, message_text: str, user_id: int):
    """إرسال رسالة لمستخدم محدد"""
    if user_id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")
        return False
    
    try:
        await context.bot.send_message(target_user_id, message_text, parse_mode='HTML')
        save_broadcast_log(message_text, 1, 0, f"للمستخدم {target_user_id}")
        await update.message.reply_text(f"✅ تم إرسال الرسالة إلى المستخدم `{target_user_id}`", parse_mode='Markdown')
        return True
    except Exception as e:
        save_broadcast_log(message_text, 0, 1, f"للمستخدم {target_user_id} - فشل")
        await update.message.reply_text(f"❌ فشل الإرسال: {str(e)}")
        return False

# ============ دالة إضافة البوت للمجموعة ============

async def add_bot_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رابط إضافة البوت للمجموعة"""
    user = update.effective_user
    chat = update.effective_chat
    
    bot_username = context.bot.username
    add_bot_link = f"https://t.me/{bot_username}?startgroup=true"
    
    # إنشاء زر إنلاين لفتح رابط الإضافة مع تلوين
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=add_bot_link, style="success")]
    ])
    
    # رسالة إضافة البوت
    add_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          ➕  إضـافـة البـوت للمـجـموعـة  ➕
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👋 **مرحباً {user.first_name}**

📢 **لإضافة البوت إلى مجموعتك:**

1️⃣ **اضغط على الزر أدناه**
2️⃣ **اختر المجموعة التي تريد إضافتي إليها**
3️⃣ **امنحني صلاحيات المشرف للعمل بشكل كامل**

━━━━━━━━━━━━━━━━━━━━━━

⚙️ **الصلاحيات المطلوبة:**

✅ حذف الرسائل
✅ حظر وتقييد الأعضاء
✅ تثبيت الرسائل
✅ رفع مشرفين (اختياري)

━━━━━━━━━━━━━━━━━━━━━━

📌 **رابط الإضافة المباشر:**
`{add_bot_link}`

━━━━━━━━━━━━━━━━━━━━━━

💡 **يمكنك نسخ الرابط أعلاه ومشاركته مع أي شخص**
"""
    
    await update.message.reply_text(
        add_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=inline_keyboard,
        disable_web_page_preview=True
    )

# ============ دالة أوامر المطور الاحترافية ============

async def developer_commands_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة أوامر المطور بشكل احترافي"""
    user = update.effective_user
    
    # التحقق من أن المستخدم هو المطور أو مشرف
    if user.id != DEVELOPER_ID and user.id not in ADMINS:
        await update.message.reply_text("❌ هذه القائمة متاحة للمطور فقط!")
        return
    
    # رسالة أوامر المطور الاحترافية
    dev_commands_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👑  أوامـــر الـــمطور  👑
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👨‍💻 **مرحباً {user.first_name}**
📊 **إحصائيات سريعة:**

━━━━━━━━━━━━━━━━━━━━━━

🔹 **المستخدمين المخالفين:** `{len(USER_WARNINGS)}`
🔹 **إجمالي الرسائل:** `{sum(sum(users.values()) for users in USER_MESSAGES_COUNT.values())}`
🔹 **المجموعات النشطة:** `{len(USER_MESSAGES_COUNT)}`

━━━━━━━━━━━━━━━━━━━━━━

⚡ **الأوامر المتاحة:**

━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🎭 **أوامر التحفيل والتفاعل** ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📌 **تحفيل** - إرسال 7 رسائل تحفيل للعضو (بالرد)
📌 **معلش يحب** - إرسال رسالة اعتذار للعضو (بالرد)

━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📢 **أوامر الإرسال الجماعي** ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📌 **إرسال (الرسالة)** - إرسال رسالة لجميع المجموعات

━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🗑️ **أوامر الحذف والتنظيف** ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📌 **حذف 200** - حذف 200 رسالة من المجموعة
📌 **تنظيف البيانات** - مسح جميع البيانات المؤقتة

━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📊 **أوامر الإحصائيات** ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📌 **إحصائيات البوت** - عرض إحصائيات عامة
📌 **إحصائيات الأعضاء** - عرض إحصائيات الأعضاء
📌 **إحصائيات القفل** - عرض إحصائيات المجموعات المقفلة
📌 **إحصائيات الزواج** - عرض إحصائيات الزواج والطلاق
📌 **إحصائيات التفاعل** - عرض إحصائيات التفاعل الذكي
📌 **عرض جميع المجموعات** - عرض قائمة المجموعات النشطة

━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🔄 **أوامر الصيانة** ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📌 **تحديث البيانات** - تحديث وتحميل البيانات

━━━━━━━━━━━━━━━━━━━━━━

📌 **للبدء باستخدام أي أمر، اختر من الأزرار أدناه**
📌 **أو اكتب الأمر مباشرة في الدردشة**

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await update.message.reply_text(
        dev_commands_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_dev_only_keyboard()
    )

# ============ دوال إحصائيات إضافية للمطور ============

async def dev_stats_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات الأعضاء للمطور"""
    user = update.effective_user
    
    if user.id != DEVELOPER_ID:
        return
    
    total_members = 0
    members_per_group = {}
    
    for chat_id, users in USER_MESSAGES_COUNT.items():
        members_per_group[chat_id] = len(users)
        total_members += len(users)
    
    stats_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👥  إحـصـائـيات الأعـضـاء  👥
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

📊 **إجمالي الأعضاء النشطين:** `{total_members}`
📌 **عدد المجموعات:** `{len(members_per_group)}`

━━━━━━━━━━━━━━━━━━━━━━

📈 **توزيع الأعضاء على المجموعات:**
"""
    
    for i, (chat_id, count) in enumerate(list(members_per_group.items())[:10], 1):
        stats_message += f"\n{i}. مجموعة `{chat_id}`: `{count}` عضو"
    
    if len(members_per_group) > 10:
        stats_message += f"\n... و{len(members_per_group) - 10} مجموعات أخرى"
    
    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

async def dev_stats_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات القفل للمطور"""
    user = update.effective_user
    
    if user.id != DEVELOPER_ID:
        return
    
    locked_count = sum(1 for locked in LOCKED_CHATS.values() if locked)
    unlocked_count = len(LOCKED_CHATS) - locked_count
    
    stats_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔒  إحـصـائـيات الـقـفـل  🔒
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🔐 **مجموعات مقفلة:** `{locked_count}`
🔓 **مجموعات مفتوحة:** `{unlocked_count}`
🔇 **أعضاء مكتومين:** `{sum(len(muted) for muted in MUTED_USERS.values())}`

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

async def dev_stats_marriage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات الزواج للمطور"""
    user = update.effective_user
    
    if user.id != DEVELOPER_ID:
        return
    
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM marriages")
    total_marriages = c.fetchone()[0]
    conn.close()
    
    stats_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          💍  إحـصـائـيات الـزواج  💍
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

💑 **إجمالي الأزواج:** `{total_marriages // 2}`

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

async def dev_stats_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات التفاعل للمطور"""
    user = update.effective_user
    
    if user.id != DEVELOPER_ID:
        return
    
    stats_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          💬  إحـصـائـيات التفـاعـل  💬
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🔹 **كلمات تفاعلية:** `{len(INTERACTION_RESPONSES)}`
🔹 **أدوات النداء:** `{len(MENTION_TOOLS)}`
🔹 **رسائل التحفيل:** `{len(TAHFIL_MESSAGES)}`

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)

async def dev_list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المجموعات النشطة للمطور"""
    user = update.effective_user
    
    if user.id != DEVELOPER_ID:
        return
    
    groups_list = "📋 **المجموعات النشطة:**\n\n"
    
    for i, chat_id in enumerate(USER_MESSAGES_COUNT.keys(), 1):
        try:
            chat = await context.bot.get_chat(chat_id)
            chat_title = chat.title or "بدون عنوان"
            members_count = len(USER_MESSAGES_COUNT[chat_id])
            groups_list += f"{i}. **{chat_title}**\n   🆔 `{chat_id}`\n   👥 `{members_count}` عضو نشط\n\n"
        except:
            groups_list += f"{i}. مجموعة `{chat_id}`\n   ⚠️ غير متاحة\n\n"
        
        if i >= 20:
            groups_list += f"... و{len(USER_MESSAGES_COUNT) - 20} مجموعات أخرى"
            break
    
    if not USER_MESSAGES_COUNT:
        groups_list = "📋 لا توجد مجموعات نشطة حالياً"
    
    await update.message.reply_text(groups_list, parse_mode=ParseMode.MARKDOWN)

async def dev_refresh_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحديث بيانات البوت"""
    user = update.effective_user
    
    if user.id != DEVELOPER_ID:
        return
    
    await update.message.reply_text(
        "🔄 **جاري تحديث البيانات...**\n\n"
        f"📊 **الإحصائيات الحالية:**\n"
        f"👥 المخالفين: {len(USER_WARNINGS)}\n"
        f"💬 الرسائل: {sum(sum(users.values()) for users in USER_MESSAGES_COUNT.values())}\n"
        f"👥 المجموعات: {len(USER_MESSAGES_COUNT)}",
        parse_mode=ParseMode.MARKDOWN
    )

# ============ دالة التحقق من الاشتراك في القناة ============
async def check_channel_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في قناة التحديثات"""
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

async def send_channel_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة تطلب الاشتراك في القناة"""
    chat = update.effective_chat
    
    # إنشاء زر القناة مع تلوين
    channel_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 سـورس || سـحـوره", url=CHANNEL_LINK, style="primary")]
    ])
    
    subscription_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📢  سـورس || سـحـوره  📢
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

عليڪ الاشتـࢪاك فـ قناه التحديثات يحب 

━━━━━━━━━━━━━━━━━━━━━━

✨ **اشترك الآن ليصلك كل جديد** ✨

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await context.bot.send_message(
        chat_id=chat.id,
        text=subscription_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=channel_keyboard
    )

def check_bot_permissions(chat, context):
    """التحقق من صلاحيات البوت في المجموعة"""
    try:
        bot_member = chat.get_member(context.bot.id)
        return bot_member.status in ['administrator', 'creator']
    except:
        return False

async def get_user_profile_photo(user_id, context):
    """الحصول على صورة الملف الشخصي للمستخدم"""
    try:
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        if photos and photos.total_count > 0:
            return photos.photos[0][-1].file_id
    except Exception as e:
        logger.error(f"خطأ في جلب صورة المستخدم: {e}")
    return None

async def get_user_name(user_id, context, chat_id):
    """الحصول على اسم المستخدم من المجموعة"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        user = member.user
        name = user.first_name
        if user.last_name:
            name += f" {user.last_name}"
        return name
    except:
        return f"مستخدم {user_id}"

async def get_user_username_from_id(user_id, context, chat_id) -> str:
    """الحصول على يوزر المستخدم من معرفه"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        user = member.user
        if user.username:
            return f"@{user.username}"
        return f"[{user.first_name}](tg://user?id={user_id})"
    except:
        return f"[مستخدم](tg://user?id={user_id})"

async def get_random_member(chat_id, context, exclude_ids=None):
    """الحصول على عضو عشوائي من المجموعة"""
    if exclude_ids is None:
        exclude_ids = []
    
    try:
        # محاولة الحصول على قائمة الأعضاء (قد لا تعمل في المجموعات الكبيرة)
        admins = await context.bot.get_chat_administrators(chat_id)
        
        # تجميع قائمة الأعضاء من المشرفين والأعضاء العاديين
        all_members = []
        
        # إضافة المشرفين
        for admin in admins:
            if admin.user.id not in exclude_ids and not admin.user.is_bot:
                all_members.append(admin.user)
        
        # إذا لم نتمكن من الحصول على أعضاء كافيين، نستخدم طريقة بديلة
        if len(all_members) < 2:
            # نستخدم الأعضاء النشطين في الرسائل
            if chat_id in USER_MESSAGES_COUNT:
                for user_id in USER_MESSAGES_COUNT[chat_id].keys():
                    if user_id not in exclude_ids:
                        try:
                            member = await context.bot.get_chat_member(chat_id, user_id)
                            if not member.user.is_bot:
                                all_members.append(member.user)
                        except:
                            pass
        
        if all_members:
            return random.choice(all_members)
        else:
            return None
            
    except Exception as e:
        logger.error(f"خطأ في الحصول على عضو عشوائي: {e}")
        return None

async def set_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ضبط زر القائمة في الشريط السفلي"""
    try:
        # تعيين زر القائمة ليفتح القائمة المخصصة
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonCommands()  # هذا سيظهر زر "الأوامر" الذي يعرض أوامر البوت
        )
        
        # تعيين أوامر البوت التي ستظهر عند الضغط على زر القائمة
        commands = [
            BotCommand("start", "بدء البوت وعرض الترحيب"),
            BotCommand("القائمة", "عرض القائمة الرئيسية"),
            BotCommand("help", "عرض التعليمات"),
            BotCommand("rules", "قواعد المجموعة"),
            BotCommand("stats", "إحصائيات البوت"),
            BotCommand("warnings", "عرض تحذيراتك"),
            BotCommand("رسائلي", "عدد رسائلك في المجموعة"),
            BotCommand("ترند", "أفضل 5 أعضاء نشطين"),
            BotCommand("ويسكي", "التواصل مع المطور"),
            BotCommand("زواج", "زواج عشوائي"),
            BotCommand("طلاق", "طلاق بين المتزوجين"),
            BotCommand("id", "عرض معرفك"),
            BotCommand("المالك", "عرض منشئ المجموعة"),
        ]
        
        await context.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=update.effective_chat.id))
        
        logger.info(f"تم تعيين زر القائمة للدردشة {update.effective_chat.id}")
    except Exception as e:
        logger.error(f"خطأ في تعيين زر القائمة: {e}")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية للبوت بشكل احترافي مع تلوين الأزرار"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة إذا كانت المحادثة مجموعة وليس خاص
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return
    
    # إنشاء أزرار القائمة مع تلوين الأزرار
    keyboard = []
    
    # الزر الأول - المطور
    keyboard.append([InlineKeyboardButton("👨‍💻 الـمـطـور", callback_data="menu_developer", style="primary")])
    
    # الزر الثاني - أوامر المشرفين
    keyboard.append([InlineKeyboardButton("👮‍♂️ أوامـر المشـرفين", callback_data="menu_admin_commands", style="danger")])
    
    # الزر الثالث - مميزات البوت
    keyboard.append([InlineKeyboardButton("✨ ممـيـزات البـوت", callback_data="menu_features", style="success")])
    
    # الزر الرابع - أوامر الأعضاء
    keyboard.append([InlineKeyboardButton("👤 أوامـر الاعـضاء", callback_data="menu_member_commands", style="primary")])
    
    # الزر الخامس - إضافة البوت للمجموعة (رابط مباشر)
    bot_username = context.bot.username
    add_bot_link = f"https://t.me/{bot_username}?startgroup=true"
    keyboard.append([InlineKeyboardButton("➕ أضـفـني لمجـموعـتـك", url=add_bot_link, style="success")])
    
    # الزر السادس - القوانين
    keyboard.append([InlineKeyboardButton("📜 الـقـوانـين", callback_data="menu_rules", style="danger")])
    
    # الزر السابع - قناة التحديثات (باسم سـورس || سـحـوره)
    keyboard.append([InlineKeyboardButton("📢 سـورس || سـحـوره", callback_data="menu_channel", style="primary")])
    
    # الزر الثامن - الزر الجديد: الإذاعة المركزية (يظهر للمطور فقط)
    if user.id == DEVELOPER_ID or user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("📢 الإذاعة المركزية", callback_data="menu_broadcast", style="primary")])
    
    # الزر التاسع - خاص بالمطور فقط (يظهر فقط للمطور)
    if user.id == DEVELOPER_ID:
        keyboard.append([InlineKeyboardButton("👑 أوامـر الـمـطـور", callback_data="menu_dev_commands", style="danger")])
    
    # إضافة زر إغلاق القائمة
    keyboard.append([InlineKeyboardButton("❌ إغـلاق الـقـائـمـة", callback_data="menu_close", style="danger")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # رسالة القائمة
    menu_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📋  الـقـائـمـة الـرئـيـسـيـة  📋
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👋 **أهلاً بك عزيزي المستخدم**

📌 **اختر ما تريد من الأزرار أدناه:**

━━━━━━━━━━━━━━━━━━━━━━

✦ **المطور** - معلومات التواصل مع المطور
✦ **أوامر المشرفين** - أوامر التحكم للمشرفين
✦ **مميزات البوت** - تعرف على مميزاتي
✦ **أوامر الأعضاء** - الأوامر المتاحة لك
✦ **أضفني لمجموعتك** - أضف البوت لمجموعتك
✦ **القوانين** - قوانين المجموعة
✦ **سـورس || سـحـوره** - تابع آخر التحديثات
✦ **الإذاعة المركزية** - إرسال رسائل للمستخدمين (للمطور والمشرفين)

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # محاولة حذف رسالة القائمة السابقة إذا وجدت
    try:
        if 'last_menu_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['last_menu_message_id']
            )
    except:
        pass
    
    # إرسال القائمة الجديدة
    sent_message = await update.message.reply_text(
        menu_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    # حفظ معرف رسالة القائمة
    context.user_data['last_menu_message_id'] = sent_message.message_id

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على أزرار القائمة"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    chat = update.effective_chat
    data = query.data
    
    if data == "menu_close":
        # إغلاق القائمة
        await query.message.delete()
        return
    
    elif data == "menu_developer":
        # معلومات المطور
        photo_id = await get_user_profile_photo(DEVELOPER_ID, context)
        
        developer_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👨‍💻  مـعـلـومـات الـمـطـور  👨‍💻
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👑 **مـــطـوࢪ الـبوت هـو:**

{DEVELOPER_NAME}

━━━━━━━━━━━━━━━━━━━━━━

📞 **للتواصل معـه اضـغـط عـلـى الـزر الـذي بـالأسـفـل:**

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # زر التواصل مع المطور مع تلوين
        contact_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📨 راسـل الـمـطـور", url=DEVELOPER_LINK, style="primary")]
        ])
        
        if photo_id:
            await query.message.reply_photo(
                photo=photo_id,
                caption=developer_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=contact_keyboard
            )
        else:
            await query.message.reply_text(
                developer_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=contact_keyboard
            )
    
    elif data == "menu_admin_commands":
        # أوامر المشرفين
        admin_commands = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👮‍♂️  أوامـر المشـرفين  👮‍♂️
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🔹 **أوامر الإدارة الأساسية:**

━━━━━━━━━━━━━━━━━━━━━━

📌 `.حظر` - حظر عضو لمدة اسبوع (بالرد على الرسالة)
📌 `.طرد` - طرد عضو نهائياً (بالرد على الرسالة)
📌 `.تثبيت` - تثبيت رسالة مهمة (بالرد على الرسالة)
📌 `.حذف` - حذف رسالة (بالرد على الرسالة)

━━━━━━━━━━━━━━━━━━━━━━

🔹 **أوامر الإشراف المتقدمة:**

━━━━━━━━━━━━━━━━━━━━━━

📌 `رفع مشرف` - رفع عضو مشرف (بالرد أو باليوزر)
📌 `عزل مشرف` - عزل عضو من الإشراف (بالرد أو باليوزر)
📌 `حذف التحذيرات` - إزالة جميع تحذيرات العضو (بالرد)
📌 `تحذير` - إضافة تحذير للعضو (بالرد)

━━━━━━━━━━━━━━━━━━━━━━

🔹 **أوامر التحكم في المجموعة:**

━━━━━━━━━━━━━━━━━━━━━━

📌 `قفل مؤقت` - قفل المجموعة مؤقتاً وحذف الرسائل
📌 `فتح` - فتح المجموعة بعد القفل المؤقت
📌 `كتم` أو `اسكت` - كتم عضو (تقييد) لمدة ساعة
📌 `إلغاء كتم` أو `اتكلم` - إلغاء كتم العضو والسماح له بالدردشة ✅ **(جديد)**
📌 `إلغاء الحظر` - إلغاء حظر العضو والسماح له بالعودة ✅ **(جديد)**
📌 `إلغاء تثبيت الرسائل` - حذف جميع الرسائل المثبتة
📌 `معلومات` - عرض معلومات العضو (بالرد)

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **ملاحظات مهمة:**
• جميع الأوامر تكتب باللغة العربية
• أوامر النقطة (.) تستخدم بالرد على الرسالة
• يجب أن يكون البوت مشرفاً لتفعيل الأوامر

━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.message.reply_text(admin_commands, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "menu_features":
        # مميزات البوت
        features_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          ✨  ممـيـزات البـوت  ✨
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🔒 **ميزات الحماية:**

━━━━━━━━━━━━━━━━━━━━━━

✅ **منع جميع الروابط بشكل كامل**
✅ **منع الكلمات المسيئة والفاضحة**
✅ **نظام تحذيرات متطور (4 مراحل)**
✅ **نظام عقوبات تدريجي**

━━━━━━━━━━━━━━━━━━━━━━

🎯 **ميزات التفاعل:**

━━━━━━━━━━━━━━━━━━━━━━

✅ **ترحيب تلقائي بالأعضاء مع الصور**
✅ **عرض بيانات العضو مع صورته**
✅ **إحصاء عدد رسائل الأعضاء**
✅ **عرض ترند أفضل 5 أعضاء**
✅ **نظام تفاعل ذكي مع الأعضاء**
✅ **نظام زواج وطلاق عشوائي**

━━━━━━━━━━━━━━━━━━━━━━

⚙️ **ميزات الإدارة:**

━━━━━━━━━━━━━━━━━━━━━━

✅ **رفع وعزل المشرفين**
✅ **نظام قفل مؤقت للمجموعة**
✅ **نظام كتم متطور**
✅ **إرسال رسائل جماعية للمجموعات**
✅ **عرض معلومات مفصلة للأعضاء**

━━━━━━━━━━━━━━━━━━━━━━

💡 **ميزات إضافية:**

━━━━━━━━━━━━━━━━━━━━━━

✅ **قائمة تفاعلية شاملة**
✅ **أوامر مخصصة للمطور**
✅ **رسائل وداع احترافية**
✅ **تصميم جذاب ومنسق**

━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.message.reply_text(features_message, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "menu_member_commands":
        # أوامر الأعضاء
        member_commands = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👤  أوامـر الاعـضاء  👤
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

📋 **الأوامر المتاحة لك:**

━━━━━━━━━━━━━━━━━━━━━━

🔹 `رسائلي` - عرض عدد رسائلك في المجموعة
🔹 `ترند` - عرض أفضل 5 أعضاء نشطين (أكثر من 1000 رسالة)
🔹 `ويسكي` - للتواصل مع المطور
🔹 `زواج` - زواج عشوائي بين الأعضاء
🔹 `طلاق` - طلاق بين الأعضاء المتزوجين
🔹 `id` - عرض معرفك مع رسالة مضحكة
🔹 `المالك` - عرض منشئ المجموعة
🔹 `/warnings` - عرض تحذيراتك
🔹 `/rules` - عرض قواعد المجموعة

━━━━━━━━━━━━━━━━━━━━━━

💬 **نظام التفاعل الذكي:**

━━━━━━━━━━━━━━━━━━━━━━

🔹 البوت يرد تلقائياً على هذه الكلمات أينما وجدت:
   • 😂 • بحبك • شخرت • سحوره • بوسه
   • وسكي • حد هنا • جوزوني • زهقان • مبضون
   • تعبان • مدايق • عاملين ايه • رحتو فين
   • الحمدلله • كويس • ممكن نتعرف • عرفوني عليكو
   • السلام عليكم • سلام عليكم • نتعرف • اسمك
   • بوت • هههه • قلبي • اي • ايه • همووت
   • عامله اي • عامله ايه • احا • مالك

━━━━━━━━━━━━━━━━━━━━━━

🎯 **تفاعل واستمتع مع البوت!**

━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.message.reply_text(member_commands, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "menu_rules":
        # القوانين والقواعد
        rules_message = """
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📜  قـواعـد المجـمـوعة  📜
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🚫 **الممنوعات:**

━━━━━━━━━━━━━━━━━━━━━━

❌ **الروابط:** ممنوع إرسال أي روابط خارجية
❌ **البوتات:** ممنوع إرسال يوزرنيم البوتات
❌ **الألفاظ:** ممنوع استخدام الكلمات النابية والبذيئة
❌ **الإعلانات:** ممنوع الترويج لقنوات أو مجموعات أخرى
❌ **المحتوى:** ممنوع إرسال محتوى فاضح أو غير لائق
❌ **الإزعاج:** ممنوع تكرار الرسائل أو إرسال سبام

━━━━━━━━━━━━━━━━━━━━━━

✅ **المسموحات:**

━━━━━━━━━━━━━━━━━━━━━━

✔️ الاحترام المتبادل بين الأعضاء
✔️ الالتزام بالأدب في الحديث
✔️ الرغي والمناقشات الهادفة
✔️ التعارف والصداقات

━━━━━━━━━━━━━━━━━━━━━━

⚖️ **نظام العقوبات - 4 مراحل:**

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **الإنذار الأول:** 📝 تحذير عادي
⚠️ **الإنذار الثاني:** 🔇 كتم لمدة ساعة
⚠️ **الإنذار الثالث:** ⛔ حظر لمدة أسبوع
⚠️ **الإنذار الرابع:** 🚫 طرد نهائي

━━━━━━━━━━━━━━━━━━━━━━

📢 **الالتزام بالقوانين يحافظ على بيئة نظيفة للجميع**

━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.message.reply_text(rules_message, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "menu_channel":
        # قناة التحديثات - سـورس || سـحـوره مع تلوين
        channel_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 سـورس || سـحـوره", url=CHANNEL_LINK, style="primary")]
        ])
        
        channel_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📢  سـورس || سـحـوره  📢
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🎯 **تابع آخر تحديثات البوت عبر قناتنا الرسمية:**

━━━━━━━━━━━━━━━━━━━━━━

📌 **القناة:** @{CHANNEL_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━

✨ **اشترك الآن ليصلك كل جديد** ✨

━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.message.reply_text(
            channel_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=channel_keyboard
        )
    
    elif data == "menu_broadcast":
        # قائمة الإذاعة الجديدة (للمطور والمشرفين)
        if user.id != DEVELOPER_ID and user.id not in ADMINS:
            await query.message.reply_text("❌ هذه القائمة متاحة للمطور والمشرفين فقط!")
            return
        
        broadcast_menu_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📢  الإذاعة المركزية  📢
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👋 **مرحباً {user.first_name}**

📌 **اختر نوع الإذاعة:**

━━━━━━━━━━━━━━━━━━━━━━

✦ **إذاعة للجميع** - إرسال رسالة لجميع المستخدمين المسجلين
✦ **إذاعة لمستخدم محدد** - إرسال رسالة لمستخدم معين
✦ **سجل الإذاعات** - عرض آخر الإذاعات المرسلة

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تنبيه:** هذه الأداة مخصصة للإدارة فقط

━━━━━━━━━━━━━━━━━━━━━━
"""
        broadcast_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 إذاعة للجميع", callback_data="broadcast_all", style="primary")],
            [InlineKeyboardButton("📨 إذاعة لمستخدم محدد", callback_data="broadcast_specific", style="success")],
            [InlineKeyboardButton("📊 سجل الإذاعات", callback_data="broadcast_logs", style="danger")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main", style="danger")]
        ])
        
        await query.message.edit_text(
            broadcast_menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=broadcast_keyboard
        )
    
    elif data == "broadcast_all":
        # إذاعة للجميع - يطلب الرسالة
        if user.id != DEVELOPER_ID:
            await query.answer("❌ هذا الأمر متاح للمطور فقط!", show_alert=True)
            return
        
        context.user_data['broadcast_type'] = 'all'
        msg = await query.message.edit_text(
            "📝 **أرسل الرسالة التي تريد بثها لجميع المستخدمين:**\n\n"
            "يمكنك استخدام HTML للتنسيق.\n"
            "لإلغاء العملية، أرسل `إلغاء`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # تسجيل الحالة للمستخدم
        context.user_data['waiting_for_broadcast'] = True
        context.user_data['broadcast_chat_id'] = query.message.chat.id
        context.user_data['broadcast_message_id'] = msg.message_id
        
    elif data == "broadcast_specific":
        # إذاعة لمستخدم محدد - يطلب المعرف ثم الرسالة
        if user.id != DEVELOPER_ID:
            await query.answer("❌ هذا الأمر متاح للمطور فقط!", show_alert=True)
            return
        
        context.user_data['broadcast_type'] = 'specific'
        msg = await query.message.edit_text(
            "📝 **أرسل معرف المستخدم (ID) ثم الرسالة**\n\n"
            "مثال: `123456789 مرحبا بك في البوت`\n\n"
            "لإلغاء العملية، أرسل `إلغاء`",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['waiting_for_broadcast'] = True
        context.user_data['broadcast_chat_id'] = query.message.chat.id
        context.user_data['broadcast_message_id'] = msg.message_id
        
    elif data == "broadcast_logs":
        # عرض سجل الإذاعات
        if user.id != DEVELOPER_ID:
            await query.answer("❌ هذا الأمر متاح للمطور فقط!", show_alert=True)
            return
        
        logs = get_broadcast_logs()
        if not logs:
            logs_text = "📊 **لا توجد إذاعات سابقة**"
        else:
            logs_text = "📊 **سجل الإذاعات:**\n\n"
            for i, log in enumerate(logs[:10], 1):
                logs_text += f"{i}. 🕒 {log['date']}\n   • {log['type']}\n   • ✓ {log['sent']} | ✗ {log['failed']}\n\n"
        
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_broadcast", style="danger")]
        ])
        
        await query.message.edit_text(
            logs_text[:4000],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard
        )
    
    elif data == "menu_dev_commands" and user.id == DEVELOPER_ID:
        # أوامر المطور (تظهر فقط للمطور)
        await developer_commands_menu(update, context)
    
    elif data == "back_to_main":
        # العودة للقائمة الرئيسية
        await show_main_menu_callback(update, context)

async def show_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية عند الضغط على الزر الشفاف في /start مع تلوين الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    chat = update.effective_chat
    
    # إنشاء أزرار القائمة مع تلوين الأزرار
    keyboard = []
    
    # الزر الأول - المطور
    keyboard.append([InlineKeyboardButton("👨‍💻 الـمـطـور", callback_data="menu_developer", style="primary")])
    
    # الزر الثاني - أوامر المشرفين
    keyboard.append([InlineKeyboardButton("👮‍♂️ أوامـر المشـرفين", callback_data="menu_admin_commands", style="danger")])
    
    # الزر الثالث - مميزات البوت
    keyboard.append([InlineKeyboardButton("✨ ممـيـزات البـوت", callback_data="menu_features", style="success")])
    
    # الزر الرابع - أوامر الأعضاء
    keyboard.append([InlineKeyboardButton("👤 أوامـر الاعـضاء", callback_data="menu_member_commands", style="primary")])
    
    # الزر الخامس - إضافة البوت للمجموعة (رابط مباشر)
    bot_username = context.bot.username
    add_bot_link = f"https://t.me/{bot_username}?startgroup=true"
    keyboard.append([InlineKeyboardButton("➕ أضـفـني لمجـموعـتـك", url=add_bot_link, style="success")])
    
    # الزر السادس - القوانين
    keyboard.append([InlineKeyboardButton("📜 الـقـوانـين", callback_data="menu_rules", style="danger")])
    
    # الزر السابع - قناة التحديثات (باسم سـورس || سـحـوره)
    keyboard.append([InlineKeyboardButton("📢 سـورس || سـحـوره", callback_data="menu_channel", style="primary")])
    
    # الزر الثامن - الزر الجديد: الإذاعة المركزية (يظهر للمطور فقط)
    if user.id == DEVELOPER_ID or user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("📢 الإذاعة المركزية", callback_data="menu_broadcast", style="primary")])
    
    # الزر التاسع - خاص بالمطور فقط (يظهر فقط للمطور)
    if user.id == DEVELOPER_ID:
        keyboard.append([InlineKeyboardButton("👑 أوامـر الـمـطـور", callback_data="menu_dev_commands", style="danger")])
    
    # إضافة زر إغلاق القائمة
    keyboard.append([InlineKeyboardButton("❌ إغـلاق الـقـائـمـة", callback_data="menu_close", style="danger")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # رسالة القائمة
    menu_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📋  الـقـائـمـة الـرئـيـسـيـة  📋
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👋 **أهلاً بك عزيزي المستخدم**

📌 **اختر ما تريد من الأزرار أدناه:**

━━━━━━━━━━━━━━━━━━━━━━

✦ **المطور** - معلومات التواصل مع المطور
✦ **أوامر المشرفين** - أوامر التحكم للمشرفين
✦ **مميزات البوت** - تعرف على مميزاتي
✦ **أوامر الأعضاء** - الأوامر المتاحة لك
✦ **أضفني لمجموعتك** - أضف البوت لمجموعتك
✦ **القوانين** - قوانين المجموعة
✦ **سـورس || سـحـوره** - تابع آخر التحديثات
✦ **الإذاعة المركزية** - إرسال رسائل للمستخدمين (للمطور والمشرفين)

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # حذف رسالة الزر القديمة وإرسال القائمة الجديدة
    await query.message.delete()
    await context.bot.send_message(
        chat_id=chat.id,
        text=menu_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# ============ معالجات القائمة السفلية الجديدة ============

async def handle_bottom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار من القائمة السفلية"""
    if not update.message or not update.message.text:
        return False
    
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    
    # التحقق من الاشتراك في القناة
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return True
    
    # القائمة الرئيسية
    if text == "📋 القائمة الرئيسية":
        await update.message.reply_text(
            "📋 **القائمة الرئيسية** - اختر ما تريد:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
        return True
    
    # أوامر الأعضاء
    elif text == "👤 أوامر الأعضاء":
        await update.message.reply_text(
            "👤 **أوامر الأعضاء** - اختر الأمر الذي تريده:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_member_commands_keyboard()
        )
        return True
    
    # أوامر المشرفين
    elif text == "👮 أوامر المشرفين":
        # التحقق من أن المستخدم مشرف أو المطور
        try:
            member = await chat.get_member(user.id)
            if member.status in ['administrator', 'creator'] or user.id == DEVELOPER_ID:
                await update.message.reply_text(
                    "👮 **أوامر المشرفين** - اختر الأمر الذي تريده:\n\n⚠️ **ملاحظة:** معظم هذه الأوامر تحتاج الرد على رسالة العضو المستهدف.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_admin_commands_keyboard()
                )
            else:
                await update.message.reply_text("❌ هذه القائمة للمشرفين فقط!")
            return True
        except:
            await update.message.reply_text("❌ حدث خطأ في التحقق من الصلاحيات!")
            return True
    
    # تفاعل ذكي
    elif text == "💬 تفاعل ذكي":
        await update.message.reply_text(
            "💬 **التفاعل الذكي** - اختر كلمة لترى رد البوت:\n\n📝 يمكنك أيضاً كتابة أي كلمة من الكلمات التفاعلية في أي وقت وسيرد البوت تلقائياً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_interaction_keyboard()
        )
        return True
    
    # ترند وإحصائيات
    elif text == "📊 ترند وإحصائيات":
        if chat.type in ['group', 'supergroup']:
            await update.message.reply_text(
                "📊 **الترند والإحصائيات** - اختر ما تريد:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_trend_keyboard()
            )
        else:
            await update.message.reply_text("❌ هذه القائمة متاحة فقط في المجموعات!")
        return True
    
    # زواج وطلاق
    elif text == "❤️ زواج وطلاق":
        if chat.type in ['group', 'supergroup']:
            await update.message.reply_text(
                "💍 **نظام الزواج والطلاق** - اختر ما تريد:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_marriage_keyboard()
            )
        else:
            await update.message.reply_text("❌ هذه القائمة متاحة فقط في المجموعات!")
        return True
    
    # المطور
    elif text == "👑 المطور":
        await update.message.reply_text(
            "👨‍💻 **المطور** - اختر ما تريد:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_developer_keyboard()
        )
        return True
    
    # زر إضافة البوت للمجموعة (الزر الجديد)
    elif text == "➕ أضفني إلى مجموعتك" or text == "➕ أضف البوت لمجموعتك":
        await add_bot_to_group(update, context)
        return True
    
    # قناة التحديثات
    elif text == "📢 قناة التحديثات":
        channel_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 سـورس || سـحـوره", url=CHANNEL_LINK, style="primary")]
        ])
        await update.message.reply_text(
            f"📢 **قناة التحديثات:**\n\n@{CHANNEL_USERNAME}\n\nاشترك ليصلك كل جديد",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=channel_keyboard
        )
        return True
    
    # زر أوامر المطور (الزر الجديد)
    elif text == "⚡ أوامـــر الـــمطور ⚡":
        await developer_commands_menu(update, context)
        return True
    
    # ========== زر الإذاعة الجديد ==========
    elif text == "📢 الإذاعة المركزية":
        # التحقق من أن المستخدم هو المطور أو مشرف
        if user.id != DEVELOPER_ID and user.id not in ADMINS:
            await update.message.reply_text("❌ هذه القائمة متاحة للمطور والمشرفين فقط!")
            return True
        
        broadcast_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📢  الإذاعة المركزية  📢
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👋 **مرحباً {user.first_name}**

📌 **اختر نوع الإذاعة:**

━━━━━━━━━━━━━━━━━━━━━━

❶ **إذاعة للجميع** - إرسال رسالة لجميع المستخدمين المسجلين
❷ **إذاعة لمستخدم محدد** - إرسال رسالة لمستخدم معين
❸ **سجل الإذاعات** - عرض آخر الإذاعات المرسلة

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تنبيه:** هذه الأداة مخصصة للإدارة فقط

━━━━━━━━━━━━━━━━━━━━━━
"""
        broadcast_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 إذاعة للجميع", callback_data="broadcast_all", style="primary")],
            [InlineKeyboardButton("📨 إذاعة لمستخدم محدد", callback_data="broadcast_specific", style="success")],
            [InlineKeyboardButton("📊 سجل الإذاعات", callback_data="broadcast_logs", style="danger")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main", style="danger")]
        ])
        
        await update.message.reply_text(
            broadcast_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=broadcast_keyboard
        )
        return True
    
    # ========== أوامر الأعضاء الفرعية ==========
    
    # رسائلي
    elif text == "📊 رسائلي":
        if chat.type in ['group', 'supergroup']:
            await my_messages_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    # ترند
    elif text == "🏆 ترند":
        if chat.type in ['group', 'supergroup']:
            await trend_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    # تحذيراتي
    elif text == "⚠️ تحذيراتي":
        await warnings_command(update, context)
        return True
    
    # ID
    elif text == "🆔 ID":
        await id_command(update, context)
        return True
    
    # المالك
    elif text == "👑 المالك":
        if chat.type in ['group', 'supergroup']:
            await owner_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    # القوانين
    elif text == "📜 القوانين":
        await rules(update, context)
        return True
    
    # ========== أوامر المشرفين الفرعية ==========
    
    # حظر
    elif text == "🔨 حظر":
        await update.message.reply_text(
            "🔨 **لحظر عضو:**\n1. أرسل `.حظر` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # طرد
    elif text == "🚫 طرد":
        await update.message.reply_text(
            "🚫 **لطرد عضو:**\n1. أرسل `.طرد` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # كتم
    elif text == "🔇 كتم":
        if update.message.reply_to_message:
            await mute_user_command(update, context)
        else:
            await update.message.reply_text(
                "🔇 **لكتم عضو:**\n1. أرسل `كتم` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # إلغاء كتم
    elif text == "🔊 إلغاء كتم":
        if update.message.reply_to_message:
            await unmute_command(update, context)
        else:
            await update.message.reply_text(
                "🔊 **لإلغاء كتم عضو:**\n1. أرسل `إلغاء كتم` أو `اتكلم` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # تثبيت
    elif text == "📌 تثبيت":
        if update.message.reply_to_message:
            await pin_command(update, context)
        else:
            await update.message.reply_text(
                "📌 **لتثبيت رسالة:**\n1. أرسل `.تثبيت` بالرد على الرسالة\nأو\n2. استخدم هذا الزر بالرد على الرسالة",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # حذف
    elif text == "🗑️ حذف":
        if update.message.reply_to_message:
            await delete_message_command(update, context)
        else:
            await update.message.reply_text(
                "🗑️ **لحذف رسالة:**\n1. أرسل `.حذف` بالرد على الرسالة\nأو\n2. استخدم هذا الزر بالرد على الرسالة",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # قفل مؤقت
    elif text == "🔒 قفل مؤقت":
        await lock_group_command(update, context)
        return True
    
    # فتح
    elif text == "🔓 فتح":
        await unlock_group_command(update, context)
        return True
    
    # تحذير
    elif text == "⚠️ تحذير":
        if update.message.reply_to_message:
            await add_warning_command(update, context)
        else:
            await update.message.reply_text(
                "⚠️ **لإضافة تحذير لعضو:**\n1. أرسل `تحذير` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # حذف التحذيرات
    elif text == "🧹 حذف التحذيرات":
        if update.message.reply_to_message:
            await clear_warnings_command(update, context)
        else:
            await update.message.reply_text(
                "🧹 **لحذف تحذيرات عضو:**\n1. أرسل `حذف التحذيرات` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # رفع مشرف
    elif text == "👑 رفع مشرف":
        await update.message.reply_text(
            "👑 **لرفع مشرف:**\n1. أرسل `رفع مشرف @username`\nأو\n2. أرسل `رفع مشرف` بالرد على رسالة العضو",
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # عزل مشرف
    elif text == "⬇️ عزل مشرف":
        await update.message.reply_text(
            "⬇️ **لعزل مشرف:**\n1. أرسل `عزل مشرف @username`\nأو\n2. أرسل `عزل مشرف` بالرد على رسالة العضو",
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # معلومات
    elif text == "ℹ️ معلومات":
        if update.message.reply_to_message:
            await user_info_command(update, context)
        else:
            await update.message.reply_text(
                "ℹ️ **لعرض معلومات عضو:**\n1. أرسل `معلومات` بالرد على رسالة العضو\nأو\n2. استخدم هذا الزر بالرد على رسالة العضو",
                parse_mode=ParseMode.MARKDOWN
            )
        return True
    
    # ========== أوامر التفاعل الذكي ==========
    
    elif text in ["😂", "❤️", "بحبك", "بوسه", "سحوره", "وسكي", "السلام عليكم", "هههه"]:
        # محاكاة التفاعل الذكي
        keyword, response = contains_interaction_keyword(text)
        if response:
            await update.message.reply_text(response)
        return True
    
    # ========== أوامر الترند ==========
    
    elif text == "📊 إحصائياتي":
        if chat.type in ['group', 'supergroup']:
            await my_messages_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    elif text == "🏆 أفضل 5":
        if chat.type in ['group', 'supergroup']:
            await trend_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    elif text == "👥 عدد الأعضاء":
        if chat.type in ['group', 'supergroup']:
            try:
                count = await context.bot.get_chat_members_count(chat.id)
                await update.message.reply_text(f"👥 **عدد أعضاء المجموعة:** `{count}`", parse_mode=ParseMode.MARKDOWN)
            except:
                await update.message.reply_text("❌ لم أتمكن من الحصول على عدد الأعضاء!")
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    elif text == "📈 نشاط المجموعة":
        if chat.type in ['group', 'supergroup']:
            if chat.id in USER_MESSAGES_COUNT:
                total_messages = sum(USER_MESSAGES_COUNT[chat.id].values())
                active_users = len(USER_MESSAGES_COUNT[chat.id])
                await update.message.reply_text(
                    f"📊 **نشاط المجموعة:**\n\n"
                    f"💬 **إجمالي الرسائل:** `{total_messages}`\n"
                    f"👥 **الأعضاء النشطين:** `{active_users}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text("📊 لا توجد بيانات كافية بعد!")
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    # ========== أوامر الزواج ==========
    
    elif text == "💍 زواج":
        if chat.type in ['group', 'supergroup']:
            await marry_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    elif text == "💔 طلاق":
        if chat.type in ['group', 'supergroup']:
            await divorce_command(update, context)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    elif text == "👰 المتزوجين":
        if chat.type in ['group', 'supergroup']:
            conn = sqlite3.connect(MARRIAGE_DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM marriages WHERE chat_id = ?", (chat.id,))
            count = c.fetchone()[0]
            conn.close()
            couples = count // 2
            await update.message.reply_text(f"💍 **عدد الأزواج في المجموعة:** `{couples}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    elif text == "📜 سجل الزواج":
        if chat.type in ['group', 'supergroup']:
            conn = sqlite3.connect(MARRIAGE_DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM marriages WHERE chat_id = ?", (chat.id,))
            count = c.fetchone()[0]
            conn.close()
            await update.message.reply_text(f"📜 **إجمالي الأزواج المسجلين:** `{count // 2}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return True
    
    # ========== أوامر المطور ==========
    
    elif text == "👨‍💻 معلومات المطور":
        photo_id = await get_user_profile_photo(DEVELOPER_ID, context)
        dev_info = f"""
👨‍💻 **معلومات المطور:**

👑 **الاسم:** {DEVELOPER_NAME}
🆔 **الآيدي:** `{DEVELOPER_ID}`
📌 **اليوزرنيم:** {DEVELOPER_LINK.replace('https://t.me/', '@')}

📊 **إحصائيات سريعة:**
👥 **المستخدمين المخالفين:** `{len(USER_WARNINGS)}`
💬 **إجمالي الرسائل:** `{sum(sum(users.values()) for users in USER_MESSAGES_COUNT.values())}`
"""
        if photo_id:
            await context.bot.send_photo(chat_id=chat.id, photo=photo_id, caption=dev_info, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(dev_info, parse_mode=ParseMode.MARKDOWN)
        return True
    
    elif text == "📞 التواصل مع المطور":
        contact_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📨 راسل المطور", url=DEVELOPER_LINK, style="primary")]
        ])
        await update.message.reply_text(
            f"📞 **للتواصل مع المطور:**\n\n{DEVELOPER_LINK}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=contact_keyboard
        )
        return True
    
    # ========== أوامر المطور الخاصة ==========
    
    elif text == "🎭 تحفيل" and user.id == DEVELOPER_ID:
        if update.message.reply_to_message:
            await tahfil_command(update, context)
        else:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو لتحفيله!")
        return True
    
    elif text == "💙 معلش يحب" and user.id == DEVELOPER_ID:
        if update.message.reply_to_message:
            await sorry_command(update, context)
        else:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو لاستخدام هذا الأمر!")
        return True
    
    elif text == "📢 إرسال رسالة جماعية" and user.id == DEVELOPER_ID:
        await update.message.reply_text(
            "📢 **لإرسال رسالة جماعية:**\nأرسل `إرسال (الرسالة)`\nمثال: `إرسال مرحباً بالجميع`",
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    elif text == "🗑️ حذف 200" and user.id == DEVELOPER_ID:
        await delete_200_messages_command(update, context)
        return True
    
    elif text == "📊 إحصائيات البوت" and user.id == DEVELOPER_ID:
        await stats(update, context)
        return True
    
    elif text == "🧹 تنظيف البيانات" and user.id == DEVELOPER_ID:
        await clean(update, context)
        return True
    
    elif text == "👥 إحصائيات الأعضاء" and user.id == DEVELOPER_ID:
        await dev_stats_members(update, context)
        return True
    
    elif text == "🔒 إحصائيات القفل" and user.id == DEVELOPER_ID:
        await dev_stats_lock(update, context)
        return True
    
    elif text == "💍 إحصائيات الزواج" and user.id == DEVELOPER_ID:
        await dev_stats_marriage(update, context)
        return True
    
    elif text == "💬 إحصائيات التفاعل" and user.id == DEVELOPER_ID:
        await dev_stats_interaction(update, context)
        return True
    
    elif text == "📋 عرض جميع المجموعات" and user.id == DEVELOPER_ID:
        await dev_list_groups(update, context)
        return True
    
    elif text == "🔄 تحديث البيانات" and user.id == DEVELOPER_ID:
        await dev_refresh_data(update, context)
        return True
    
    # ========== رجوع للقائمة الرئيسية ==========
    
    elif text == "🔙 رجوع للقائمة الرئيسية" or text == "🔙 رجوع":
        await update.message.reply_text(
            "📋 **القائمة الرئيسية** - اختر ما تريد:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
        return True
    
    return False

# ============ بقية الدوال موجودة كما هي (لم يتم تغييرها) ============

# قائمة المسؤولين - يمكن إضافة المزيد من المعرفات هنا
ADMINS = [DEVELOPER_ID]  # يمكن إضافة معرفات مشرفين إضافيين هنا

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء كتم العضو والسماح له بالدردشة - إلغاء كتم أو اتكلم"""
    
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لإلغاء كتمه!\nمثال: `إلغاء كتم` (بالرد على الرسالة)", parse_mode=ParseMode.MARKDOWN)
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من الصلاحيات!")
        return
    
    # التحقق من صلاحيات البوت
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت ليس مشرفاً في المجموعة!")
            return
        
        # التحقق من أن البوت لديه صلاحية تقييد الأعضاء
        if not bot_member.can_restrict_members:
            await update.message.reply_text("❌ البوت لا يملك صلاحية تقييد الأعضاء!")
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من صلاحيات البوت!")
        return
    
    # إلغاء كتم العضو
    try:
        # صلاحيات عادية - السماح للعضو بإرسال الرسائل
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        
        # تطبيق إلغاء الكتم
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            permissions=permissions
        )
        
        # إزالة من قائمة المكتومين إذا كان موجوداً
        if chat.id in MUTED_USERS and target_user.id in MUTED_USERS[chat.id]:
            del MUTED_USERS[chat.id][target_user.id]
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # رسالة التأكيد
        unmute_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔊  تـم إلـغـاء الـكـتـم  🔊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم إلغاء الكتم بنجاح**

🗣️ **يمكنه الآن المشاركة في الدردشة**

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=unmute_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(unmute_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر إلغاء الكتم
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في إلغاء الكتم: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة إلغاء كتم العضو!")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء حظر العضو والسماح له بالعودة - إلغاء الحظر"""
    
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لإلغاء حظره!\nمثال: `إلغاء الحظر` (بالرد على الرسالة)", parse_mode=ParseMode.MARKDOWN)
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من الصلاحيات!")
        return
    
    # التحقق من صلاحيات البوت
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت ليس مشرفاً في المجموعة!")
            return
        
        # التحقق من أن البوت لديه صلاحية حظر الأعضاء
        if not bot_member.can_restrict_members:
            await update.message.reply_text("❌ البوت لا يملك صلاحية حظر الأعضاء!")
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من صلاحيات البوت!")
        return
    
    # إلغاء حظر العضو
    try:
        await context.bot.unban_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            only_if_banned=True
        )
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # رسالة التأكيد
        unban_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔓  تـم إلـغـاء الـحـظـر  🔓
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم إلغاء الحظر بنجاح**

🚪 **يمكنه الآن العودة إلى المجموعة**

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=unban_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(unban_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر إلغاء الحظر
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في إلغاء الحظر: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة إلغاء حظر العضو!")

async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض منشئ المجموعة - أمر المالك"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    try:
        # الحصول على قائمة المشرفين
        admins = await context.bot.get_chat_administrators(chat.id)
        
        # البحث عن منشئ المجموعة (creator)
        creator = None
        for admin in admins:
            if admin.status == 'creator':
                creator = admin.user
                break
        
        if not creator:
            await update.message.reply_text("❌ لم أتمكن من العثور على منشئ المجموعة!")
            return
        
        # الحصول على صورة المنشئ
        photo_id = await get_user_profile_photo(creator.id, context)
        
        # رسالة المالك
        owner_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👑  مـالـك المجـمـوعـة  👑
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

📋 **بيانات المالك:**

━━━━━━━━━━━━━━━━━━━━━━

👤 **الاسم:** `{creator.first_name}` {f'`{creator.last_name}`' if creator.last_name else ''}
🆔 **الآيدي:** `{creator.id}`
📌 **اليوزرنيم:** {'@' + creator.username if creator.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

🌟 **هذا هو مالك المجموعة** 🌟

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=owner_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(owner_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "المالك"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر المالك: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة عرض المالك!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة ترحيبية احترافية مع القائمة السفلية"""
    user = update.effective_user
    
    # حفظ المستخدم في قاعدة البيانات
    username = user.username if user.username else ""
    first_name = user.first_name
    save_user_to_database(user.id, username, first_name)
    
    # تعيين زر القائمة في الشريط السفلي (يبقى كخيار احتياطي)
    await set_menu_button(update, context)
    
    # الحصول على صورة المستخدم
    photo_id = await get_user_profile_photo(user.id, context)
    
    # الرسالة الأولى - الترحيب بالشخص
    welcome_private = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🎊  أهلاً وسهلاً بك  🎊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

📋 **بياناتك الشخصية:**

━━━━━━━━━━━━━━━━━━━━━━

👤 **الاسم:** `{user.first_name}` {f'`{user.last_name}`' if user.last_name else ''}

🆔 **الآيدي:** `{user.id}`

📌 **اليوزرنيم:** {'@' + user.username if user.username else 'لا يوجد'}

🗓️ **تاريخ الدخول:** `{datetime.now().strftime('%Y/%m/%d - %I:%M %p')}`

━━━━━━━━━━━━━━━━━━━━━━

✨ **نورت البوت ياصديقي** ✨
"""
    
    # الرسالة الثانية - معلومات البوت والمطور (معدلة)
    bot_info = f"""
━━━━━━━━━━━━━━━━━━━━━━
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🚀  𝐏𝐫𝐨𝐭𝐞𝐜𝐭𝐢𝐨𝐧 𝐁𝐨𝐭  🚀
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👨‍💻 **المطور:** `{DEVELOPER_NAME}`

🆔 **آيدي المطور:** `{DEVELOPER_ID}`

📊 **الإصدار:** `v4.7.0` ✨

━━━━━━━━━━━━━━━━━━━━━━

✨ **تم إضافة ميزات جديدة:** 
   • 🎨 تلوين الأزرار الشفافة
   • 📢 الإذاعة المركزية للمطور والمشرفين
   • 👤 عرض اليوزر في الزواج والطلاق

━━━━━━━━━━━━━━━━━━━━━━

لإستـعرآض القائمة السفلية اضغط على الأزرار أدناه 👇🏻
"""

    # إنشاء زر شفاف للقائمة مع تلوين
    menu_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 القائمة التفاعلية", callback_data="show_main_menu", style="primary")]
    ])

    # إرسال الصورة إذا وجدت للرسالة الأولى
    if photo_id:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_id,
            caption=welcome_private,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(welcome_private, parse_mode=ParseMode.MARKDOWN)

    # إرسال الرسالة الثانية مع الزر الشفاف والقائمة السفلية
    await update.message.reply_text(
        bot_info, 
        parse_mode=ParseMode.MARKDOWN, 
        disable_web_page_preview=True,
        reply_markup=menu_keyboard
    )
    
    # إرسال القائمة السفلية
    await update.message.reply_text(
        "📋 **اختر ما تريد من القائمة أدناه:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard()
    )

async def apply_punishment(chat, user, context, warning_type, reason):
    """تطبيق العقوبة على المستخدم - نظام أربع مراحل"""
    user_id = user.id
    
    # تحديث عدد التحذيرات
    if user_id not in USER_WARNINGS:
        USER_WARNINGS[user_id] = {'bad_words': 0, 'links': 0}
        USER_WARNINGS_DETAILS[user_id] = []
    
    # تحديث نوع التحذير
    if warning_type == 'bad_words':
        USER_WARNINGS[user_id]['bad_words'] += 1
    elif warning_type == 'links':
        USER_WARNINGS[user_id]['links'] += 1
    
    total_warnings = sum(USER_WARNINGS.get(user_id, {}).values())
    
    # تسجيل تفاصيل التحذير
    warning_detail = {
        'type': warning_type,
        'reason': reason,
        'date': datetime.now(),
        'warnings_count': total_warnings
    }
    USER_WARNINGS_DETAILS[user_id].append(warning_detail)
    
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            return False
        
        # نظام العقوبات الجديد - 4 مراحل
        if total_warnings >= 4:  # الإنذار الرابع: طرد نهائي
            await context.bot.ban_chat_member(
                chat_id=chat.id,
                user_id=user_id
            )
            return True
            
        elif total_warnings >= 3:  # الإنذار الثالث: حظر لمدة أسبوع
            until_date = int(time.time()) + 604800  # 7 أيام
            await context.bot.ban_chat_member(
                chat_id=chat.id,
                user_id=user_id,
                until_date=until_date
            )
            return True
            
        elif total_warnings >= 2:  # الإنذار الثاني: كتم لمدة ساعة
            until_date = int(time.time()) + 3600  # ساعة واحدة
            # استخدام الصلاحيات الصحيحة
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False
                ),
                until_date=until_date
            )
            return True
            
        elif total_warnings >= 1:  # الإنذار الأول: تحذير عادي فقط
            # لا توجد عقوبة، فقط تحذير
            return True
            
    except Exception as e:
        logger.error(f"خطأ في تطبيق العقوبة: {e}")
    
    return False

async def send_warning_message(chat, user, context, warning_type, reason, punishment_level):
    """إرسال رسالة تحذير احترافية مع جميع البيانات - يتم حذفها بعد 5 ثواني"""
    
    # الحصول على صورة المستخدم
    photo_id = await get_user_profile_photo(user.id, context)
    
    # تحديد العقوبة واللون حسب مستوى الإنذار
    if punishment_level == 1:
        punishment = "📝 **تحذير عادي** 📝"
        level_text = "الإنذار الأول"
        color = "🟢"
        punishment_desc = "تم تسجيل مخالفة في سجلك"
    elif punishment_level == 2:
        punishment = "🔇 **كتم لمدة ساعة** 🔇"
        level_text = "الإنذار الثاني"
        color = "🟡"
        punishment_desc = "تم كتمك لمدة 60 دقيقة"
    elif punishment_level == 3:
        punishment = "⛔ **حظر لمدة أسبوع** ⛔"
        level_text = "الإنذار الثالث"
        color = "🟠"
        punishment_desc = "تم حظرك لمدة 7 أيام"
    else:
        punishment = "🚫 **طرد نهائي** 🚫"
        level_text = "الإنذار الرابع"
        color = "🔴"
        punishment_desc = "تم طردك نهائياً من المجموعة"
    
    # إجمالي التحذيرات
    total_warnings = sum(USER_WARNINGS.get(user.id, {}).values())
    
    # تصميم رسالة التحذير
    warning_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          ⚠️  نـظـام الإنـذارات  ⚠️
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

{color} **{level_text}** {color}

━━━━━━━━━━━━━━━━━━━━━━

👤 **بيانات العضو المخالف:**

━━━━━━━━━━━━━━━━━━━━━━

📛 **الاسم:** `{user.first_name}` {f'`{user.last_name}`' if user.last_name else ''}

🆔 **الآيدي:** `{user.id}`

📌 **اليوزرنيم:** {'@' + user.username if user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تفاصيل المخالفة:**

📝 **السبب:** `{reason}`

🔞 **نوع المخالفة:** `{warning_type}`

━━━━━━━━━━━━━━━━━━━━━━

⚖️ **العقوبة المطبقة:**

{punishment}

📌 **تفاصيل:** {punishment_desc}

━━━━━━━━━━━━━━━━━━━━━━

📊 **إحصائيات التحذيرات:**

⚠️ **عدد الإنذارات:** `{total_warnings}/{MAX_WARNINGS}`

📅 **تاريخ المخالفة:** `{datetime.now().strftime('%Y/%m/%d - %I:%M %p')}`

━━━━━━━━━━━━━━━━━━━━━━

💢 **يسـطآ إلتـزم بقواعد المجموعه عشان لو انطردت يبقا مليش دعـوة** 💢

━━━━━━━━━━━━━━━━━━━━━━

⏳ **سيتم حذف هذه الرسالة تلقائياً بعد 5 ثواني**
"""
    
    try:
        # إرسال الصورة مع رسالة التحذير
        if photo_id:
            sent_msg = await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=warning_message,
                parse_mode=ParseMode.MARKDOWN
            )
            # حذف رسالة التحذير بعد 5 ثواني
            await asyncio.sleep(5)
            await sent_msg.delete()
        else:
            sent_msg = await context.bot.send_message(
                chat_id=chat.id,
                text=warning_message,
                parse_mode=ParseMode.MARKDOWN
            )
            # حذف رسالة التحذير بعد 5 ثواني
            await asyncio.sleep(5)
            await sent_msg.delete()
            
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة التحذير: {e}")

def contains_interaction_keyword(text):
    """البحث عن كلمات التفاعل في أي مكان داخل النص"""
    if not text:
        return None, None
    
    text_clean = text.strip()
    text_lower = text.lower()
    
    # التحقق من الرموز التعبيرية المتعددة
    if "😂" in text:
        # التحقق من عدد مرات تكرار 😂
        laugh_count = text.count("😂")
        if laugh_count >= 2:
            return "😂😂", INTERACTION_RESPONSES["😂"]
        else:
            return "😂", INTERACTION_RESPONSES["😂"]
    
    # التحقق من الكلمات المحددة
    for keyword, response in INTERACTION_RESPONSES.items():
        # نتخطى الرموز التعبيرية لأنها عولجت بالفعل
        if keyword in ["😂"]:
            continue
            
        # البحث عن الكلمة في النص
        if keyword in text_lower:
            return keyword, response
    
    # التحقق من النقطة فقط
    if text_clean == ".":
        return ".", "صلـي ؏ النبي وتبسم 💜"
    
    return None, None

async def handle_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تفاعلات البوت مع الأعضاء - البحث في أي مكان بالرسالة"""
    if not update.message or not update.message.text:
        return False
    
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text.strip()
    
    # تجاهل الرسائل من البوت نفسه
    if user.id == context.bot.id:
        return False
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        return False
    
    # التحقق من الاشتراك في القناة (للمجموعات فقط)
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return True
    
    # معالجة خاصة للمطور عند كتابة "سحوره" (تطابق تام)
    if message_text == "سحوره" and user.id == DEVELOPER_ID:
        await context.bot.send_message(
            chat_id=chat.id,
            text=DEVELOPER_SOHOURA_RESPONSE
        )
        # إضافة تفاعل قلب على رسالة المطور
        try:
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                message_id=update.message.message_id,
                reaction=[{"type": "emoji", "emoji": "❤"}]
            )
        except:
            pass
        return True
    
    # التحقق من استخدام أدوات النداء (ي أو يا) في بداية الرسالة
    words = message_text.split()
    if len(words) >= 2 and words[0] in MENTION_TOOLS:
        await context.bot.send_message(
            chat_id=chat.id,
            text=MENTION_RESPONSE
        )
        return True
    
    # البحث عن كلمات التفاعل في أي مكان بالرسالة
    keyword, response = contains_interaction_keyword(message_text)
    if keyword and response:
        # استثناء: إذا كان المستخدم هو المطور وكلمة "سحوره" (تمت معالجتها بالفعل)
        if keyword == "سحوره" and user.id == DEVELOPER_ID:
            return True
            
        await context.bot.send_message(
            chat_id=chat.id,
            text=response
        )
        return True
    
    return False

# ============ أوامر المطور الجديدة ============

async def tahfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر تحفيل - خاص بالمطور فقط - عند الرد على رسالة عضو"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المستخدم هو المطور
    if user.id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")
        return
    
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لتحفيله!\nمثال: `تحفيل` (بالرد على الرسالة)", parse_mode=ParseMode.MARKDOWN)
        return
    
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من أن العضو ليس بوت
    if target_user.is_bot:
        await update.message.reply_text("❌ لا يمكن تحفيل البوتات!")
        return
    
    # الحصول على يوزر العضو المستهدف
    target_mention = f"@{target_user.username}" if target_user.username else f"[{target_user.first_name}](tg://user?id={target_user.id})"
    
    # إرسال رسائل التحفيل الست
    for i, message in enumerate(TAHFIL_MESSAGES, 1):
        tahfil_text = f"{target_mention}\n\n{message}"
        await context.bot.send_message(
            chat_id=chat.id,
            text=tahfil_text,
            parse_mode=ParseMode.MARKDOWN
        )
        await asyncio.sleep(1)  # تأخير بسيط بين الرسائل
    
    # الرسالة السابعة - رسالة المطور مع التأكيد
    developer_mention = f"@{DEVELOPER_NAME.replace(' ', '_')}" if DEVELOPER_NAME else f"[{DEVELOPER_NAME}](tg://user?id={DEVELOPER_ID})"
    final_message = f"{developer_mention}\n\n#تم_التحفيل_عليه #بنجاح ♡>"
    
    await context.bot.send_message(
        chat_id=chat.id,
        text=final_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # حذف أمر التحفيل
    try:
        await update.message.delete()
    except:
        pass

async def sorry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر معلش يحب - خاص بالمطور فقط - عند الرد على رسالة عضو"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المستخدم هو المطور
    if user.id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")
        return
    
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لاستخدام هذا الأمر!\nمثال: `معلش يحب` (بالرد على الرسالة)", parse_mode=ParseMode.MARKDOWN)
        return
    
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من أن العضو ليس بوت
    if target_user.is_bot:
        await update.message.reply_text("❌ لا يمكن استخدام هذا الأمر مع البوتات!")
        return
    
    # الحصول على يوزر العضو المستهدف
    target_mention = f"@{target_user.username}" if target_user.username else f"[{target_user.first_name}](tg://user?id={target_user.id})"
    
    # رسالة الاعتذار
    sorry_message = f"{target_mention}\n\nمعلـش يسطا، ويـسڪي بيحبڪ \n\n#ڪان_هزار_عفڪره"
    
    await context.bot.send_message(
        chat_id=chat.id,
        text=sorry_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # حذف الأمر
    try:
        await update.message.delete()
    except:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل الواردة"""
    if not update.message or not update.message.text:
        return
    
    message_id = update.message.message_id
    if message_id in MESSAGE_CACHE:
        return
    
    MESSAGE_CACHE.add(message_id)
    asyncio.create_task(clear_message_cache(message_id, 300))
    
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text.strip()
    
    # التحقق من القائمة السفلية أولاً
    if await handle_bottom_menu(update, context):
        return
    
    # التحقق من حالة القفل المؤقت للمجموعة
    if chat.type in ['group', 'supergroup'] and chat.id in LOCKED_CHATS and LOCKED_CHATS[chat.id]:
        # التحقق من أن المستخدم ليس مشرفاً
        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
                # حذف الرسالة
                try:
                    await update.message.delete()
                except:
                    pass
                
                # إرسال تنبيه للعضو
                alert_msg = await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"⚠️ **تنبيه:** {user.first_name}\n\n📢 **المجموعة مقفلة مؤقتاً**\n💬 فقط المشرفون يمكنهم إرسال الرسائل.\n🔓 انتظر حتى يتم فتح المجموعة.\n\n🕒 **الوقت:** {datetime.now().strftime('%I:%M %p')}",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # حذف التنبيه بعد 5 ثواني
                await asyncio.sleep(5)
                try:
                    await alert_msg.delete()
                except:
                    pass
                return
        except:
            pass
    
    # التحقق من التفاعلات أولاً - إذا تم التفاعل، لا نكمل باقي المعالجة
    if await handle_interaction(update, context):
        return
    
    # تسجيل عدد رسائل المستخدم (لجميع الرسائل)
    if chat.type in ['group', 'supergroup']:
        if chat.id not in USER_MESSAGES_COUNT:
            USER_MESSAGES_COUNT[chat.id] = {}
        
        if user.id not in USER_MESSAGES_COUNT[chat.id]:
            USER_MESSAGES_COUNT[chat.id][user.id] = 0
        
        USER_MESSAGES_COUNT[chat.id][user.id] += 1
    
    # التحقق من أمر "رسائلي"
    if message_text == "رسائلي":
        await my_messages_command(update, context)
        return
    
    # التحقق من أمر "ترند"
    if message_text == "ترند":
        await trend_command(update, context)
        return
    
    # التحقق من أمر "ويسكي"
    if "ويسكي" in message_text:
        await whisky_mention_command(update, context)
        return
    
    # التحقق من أمر "id" (تم تغيير الاسم)
    if message_text.lower() == "id":
        await id_command(update, context)
        return
    
    # التحقق من أمر "المالك" (جديد)
    if message_text == "المالك":
        await owner_command(update, context)
        return
    
    # التحقق من أمر "رفع مشرف"
    if message_text.startswith("رفع مشرف"):
        await promote_command(update, context)
        return
    
    # التحقق من أمر "عزل مشرف"
    if message_text.startswith("عزل مشرف"):
        await demote_command(update, context)
        return
    
    # التحقق من أمر "زواج"
    if message_text == "زواج":
        await marry_command(update, context)
        return
    
    # التحقق من أمر "طلاق"
    if message_text == "طلاق":
        await divorce_command(update, context)
        return
    
    # التحقق من أمر "حذف التحذيرات"
    if message_text == "حذف التحذيرات" and update.message.reply_to_message:
        await clear_warnings_command(update, context)
        return
    
    # التحقق من أمر "تحذير"
    if message_text == "تحذير" and update.message.reply_to_message:
        await add_warning_command(update, context)
        return
    
    # التحقق من أمر "قفل مؤقت"
    if message_text == "قفل مؤقت":
        await lock_group_command(update, context)
        return
    
    # التحقق من أمر "فتح"
    if message_text == "فتح":
        await unlock_group_command(update, context)
        return
    
    # التحقق من أمر "إرسال" (للمطور فقط)
    if message_text.startswith("إرسال "):
        await broadcast_to_groups_command(update, context)
        return
    
    # التحقق من أمر "إلغاء تثبيت الرسائل"
    if message_text == "إلغاء تثبيت الرسائل":
        await unpin_all_messages_command(update, context)
        return
    
    # التحقق من أمر "معلومات"
    if message_text == "معلومات" and update.message.reply_to_message:
        await user_info_command(update, context)
        return
    
    # التحقق من أمر "كتم" أو "اسكت"
    if message_text in ["كتم", "اسكت"] and update.message.reply_to_message:
        await mute_user_command(update, context)
        return
    
    # التحقق من أمر "إلغاء كتم" أو "اتكلم"
    if message_text in ["إلغاء كتم", "اتكلم"] and update.message.reply_to_message:
        await unmute_command(update, context)
        return
    
    # التحقق من أمر "إلغاء الحظر"
    if message_text == "إلغاء الحظر" and update.message.reply_to_message:
        await unban_command(update, context)
        return
    
    # التحقق من أمر "حذف 200"
    if message_text == "حذف 200":
        await delete_200_messages_command(update, context)
        return
    
    # التحقق من أمر "تحفيل" (للمطور فقط)
    if message_text == "تحفيل" and update.message.reply_to_message:
        await tahfil_command(update, context)
        return
    
    # التحقق من أمر "معلش يحب" (للمطور فقط)
    if message_text == "معلش يحب" and update.message.reply_to_message:
        await sorry_command(update, context)
        return
    
    # فحص الكلمات المسيئة
    has_bad_word, bad_word = contains_bad_words(message_text)
    if has_bad_word:
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"خطأ في حذف الرسالة: {e}")
        
        # تطبيق العقوبة وإرسال التحذير
        await apply_punishment(chat, user, context, 'bad_words', f"كلمة مسيئة: {bad_word}")
        total_warnings = sum(USER_WARNINGS.get(user.id, {}).values())
        
        # إرسال رسالة تحذير مع جميع البيانات
        await send_warning_message(
            chat, user, context, 
            "كلمات مسيئة 🔞", 
            f"استخدام كلمة: {bad_word}",
            total_warnings
        )
        return
    
    # فحص الروابط
    has_link, link = contains_any_links(message_text)
    if has_link:
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"خطأ في حذف الرسالة: {e}")
        
        # تطبيق العقوبة وإرسال التحذير
        await apply_punishment(chat, user, context, 'links', f"رابط ممنوع: {link}")
        total_warnings = sum(USER_WARNINGS.get(user.id, {}).values())
        
        # إرسال رسالة تحذير مع جميع البيانات
        await send_warning_message(
            chat, user, context,
            "رابط ممنوع 🔗",
            f"إرسال رابط: {link}",
            total_warnings
        )
        return

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معرف المستخدم بشكل مضحك وجذاب"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة إذا كانت المجموعة
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return
    
    # الحصول على صورة المستخدم
    photo_id = await get_user_profile_photo(user.id, context)
    
    # رسالة مضحكة مع المعرف
    id_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🆔  الايـدي الخـاص بك  🆔
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

**اي يعم البنات لو شافوك هيموتو فيك مش هتيجي بقا  😂😂**

━━━━━━━━━━━━━━━━━━━━━━

👤 **الاسم:** {user.first_name}
🆔 **الايـدي:** `{user.id}`
📌 **اليوزر:** {'@' + user.username if user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

📝 **متـيجي نشرب شـآي واقولك بقيت فـ قلبي عامل ازاي 🤭😂**

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # إرسال الصورة مع الرسالة
    if photo_id:
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=photo_id,
            caption=id_message,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(id_message, parse_mode=ParseMode.MARKDOWN)
    
    # حذف أمر "id"
    try:
        await update.message.delete()
    except:
        pass

async def clear_warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إزالة جميع تحذيرات العضو - حذف التحذيرات"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من وجود رد على رسالة
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو لحذف تحذيراته!")
            return
        
        target_user = update.message.reply_to_message.from_user
        
        # التحقق من أن العضو ليس مشرفاً        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator'] and target_user.id != DEVELOPER_ID and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ لا يمكنك حذف تحذيرات مشرف!")
            return
        
        # حذف التحذيرات
        if target_user.id in USER_WARNINGS:
            del USER_WARNINGS[target_user.id]
        
        if target_user.id in USER_WARNINGS_DETAILS:
            del USER_WARNINGS_DETAILS[target_user.id]
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # رسالة التأكيد
        clear_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🧹  تـم حـذف التحـذيرات  🧹
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم حذف جميع التحذيرات الخاصة به**

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

📊 **العدد:** 0/{MAX_WARNINGS} إنذارات

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=clear_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(clear_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "حذف التحذيرات"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر حذف التحذيرات: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة حذف التحذيرات!")

async def add_warning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة تحذير للعضو - تحذير"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من وجود رد على رسالة
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو لإضافة تحذير!")
            return
        
        target_user = update.message.reply_to_message.from_user
        
        # التحقق من أن العضو ليس مشرفاً
        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator'] and target_user.id != DEVELOPER_ID and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ لا يمكنك تحذير مشرف!")
            return
        
        # إضافة تحذير للعضو
        if target_user.id not in USER_WARNINGS:
            USER_WARNINGS[target_user.id] = {'bad_words': 0, 'links': 0}
            USER_WARNINGS_DETAILS[target_user.id] = []
        
        # نضيف تحذير من نوع "يدوي"
        USER_WARNINGS[target_user.id]['bad_words'] = USER_WARNINGS[target_user.id].get('bad_words', 0) + 1
        
        total_warnings = sum(USER_WARNINGS[target_user.id].values())
        
        # تسجيل تفاصيل التحذير
        warning_detail = {
            'type': 'يدوي',
            'reason': 'تحذير يدوي من المشرف',
            'date': datetime.now(),
            'warnings_count': total_warnings,
            'admin': user.id
        }
        USER_WARNINGS_DETAILS[target_user.id].append(warning_detail)
        
        # تطبيق العقوبة إذا وصل للحد
        if total_warnings >= 2:  # نطبق العقوبات فقط بعد التحذير الثاني فما فوق
            await apply_punishment(chat, target_user, context, 'يدوي', 'تحذير يدوي من المشرف')
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # تحديد مستوى التحذير
        if total_warnings >= 4:
            level_text = "🔴 إنذار رابع - طرد نهائي"
        elif total_warnings == 3:
            level_text = "🟠 إنذار ثالث - حظر أسبوع"
        elif total_warnings == 2:
            level_text = "🟡 إنذار ثاني - كتم ساعة"
        else:
            level_text = "🟢 إنذار أول - تحذير عادي"
        
        # رسالة التأكيد
        warning_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          ⚠️  تـم إضـافـة تحـذيـر  ⚠️
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

📊 **إحصائيات التحذيرات:**

⚠️ **العدد الحالي:** `{total_warnings}/{MAX_WARNINGS}`

📌 **المستوى:** {level_text}

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=warning_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(warning_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "تحذير"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر تحذير: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة إضافة تحذير!")

async def lock_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قفل المجموعة مؤقتاً - حذف جميع الرسائل الجديدة"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لقفل المجموعة!")
            return
        
        # قفل المجموعة
        LOCKED_CHATS[chat.id] = True
        
        # الحصول على صورة المشرف
        photo_id = await get_user_profile_photo(user.id, context)
        
        # رسالة التأكيد
        lock_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔒  تـم قفـل المجـمـوعة  🔒
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

📢 **تم قفل المجموعة مؤقتاً**

⚠️ **لن يتمكن الأعضاء من إرسال الرسائل**

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

📌 **للفتح:** استخدم أمر `فتح`

━━━━━━━━━━━━━━━━━━━━━━

⏳ **سيتم حذف رسائل الأعضاء تلقائياً**
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=lock_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(lock_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "قفل مؤقت"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر قفل مؤقت: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة قفل المجموعة!")

async def unlock_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فتح المجموعة بعد القفل المؤقت"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # فتح المجموعة
        LOCKED_CHATS[chat.id] = False
        
        # الحصول على صورة المشرف
        photo_id = await get_user_profile_photo(user.id, context)
        
        # رسالة التأكيد
        unlock_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔓  تـم فـتح المجـمـوعة  🔓
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

📢 **تم فتح المجموعة**

✅ **يمكن للأعضاء إرسال الرسائل الآن**

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

📌 **للقفل مرة أخرى:** استخدم أمر `قفل مؤقت`

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=unlock_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(unlock_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "فتح"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر فتح: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة فتح المجموعة!")

async def broadcast_to_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة لجميع المجموعات التي بها البوت - خاص بالمطور فقط"""
    user = update.effective_user
    
    # التحقق من أن المستخدم هو المطور
    if user.id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")
        return
    
    # استخراج نص الرسالة
    message_text = update.message.text[6:].strip()  # بعد "إرسال "
    
    if not message_text:
        await update.message.reply_text("❌ يرجى كتابة الرسالة التي تريد إرسالها!\nمثال: `إرسال مرحباً بالجميع`", parse_mode=ParseMode.MARKDOWN)
        return
    
    # إرسال رسالة تأكيد البدء
    processing_msg = await update.message.reply_text(
        "⏳ **جاري إرسال الرسالة لجميع المجموعات...**\n\n"
        "📊 **يرجى الانتظار...**",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # الحصول على جميع المجموعات التي بها البوت (من سجل الرسائل)
    groups = list(USER_MESSAGES_COUNT.keys())
    
    sent_count = 0
    failed_count = 0
    
    # تصميم رسالة الإرسال الجماعي
    broadcast_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📢  رسـالـة جـمـاعـية  📢
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

{message_text}

━━━━━━━━━━━━━━━━━━━━━━

👑 **مرسلة من المطور:** {DEVELOPER_NAME}

📅 **التاريخ:** {datetime.now().strftime('%Y/%m/%d - %I:%M %p')}

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # إرسال الرسالة لكل مجموعة
    for chat_id in groups:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=broadcast_message,
                parse_mode=ParseMode.MARKDOWN
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة جماعية للمجموعة {chat_id}: {e}")
            failed_count += 1
        await asyncio.sleep(0.5)  # تأخير بسيط لتجنب سبام
    
    # تحديث رسالة التأكيد
    await processing_msg.edit_text(
        f"✅ **تم إرسال الرسالة الجماعية بنجاح!**\n\n"
        f"📊 **الإحصائيات:**\n"
        f"✅ **تم الإرسال:** {sent_count}\n"
        f"❌ **فشل الإرسال:** {failed_count}\n"
        f"📈 **النسبة:** {sent_count}/{sent_count + failed_count}\n\n"
        f"📝 **الرسالة:** {message_text[:50]}{'...' if len(message_text) > 50 else ''}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # حذف أمر "إرسال"
    try:
        await update.message.delete()
    except:
        pass

async def unpin_all_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء تثبيت جميع الرسائل في المجموعة"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لإلغاء تثبيت الرسائل!")
            return
        
        # إلغاء تثبيت جميع الرسائل
        await context.bot.unpin_all_chat_messages(chat_id=chat.id)
        
        # الحصول على صورة المشرف
        photo_id = await get_user_profile_photo(user.id, context)
        
        # رسالة التأكيد
        unpin_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📌  إلـغـاء تـثـبـيت الرسائل  📌
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم إلغاء تثبيت جميع الرسائل بنجاح**

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

📊 **العدد:** جميع الرسائل المثبتة

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=unpin_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(unpin_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "إلغاء تثبيت الرسائل"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر إلغاء تثبيت الرسائل: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة إلغاء تثبيت الرسائل!")

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات العضو في المجموعة - معلومات"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من وجود رد على رسالة
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو لعرض معلوماته!")
            return
        
        target_user = update.message.reply_to_message.from_user
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لعرض معلومات العضو!")
            return
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # الحصول على معلومات التحذيرات
        warnings_data = USER_WARNINGS.get(target_user.id, {'bad_words': 0, 'links': 0})
        warnings_details = USER_WARNINGS_DETAILS.get(target_user.id, [])
        total_warnings = sum(warnings_data.values())
        
        # تحديد حالة العضو
        if total_warnings == 0:
            status = "✅ عضو ملتزم"
            status_color = "🟢"
        elif total_warnings < 3:
            status = "⚠️ عضو مخالف"
            status_color = "🟡"
        else:
            status = "🔴 عضو خطير"
            status_color = "🔴"
        
        # الحصول على عدد رسائل العضو
        message_count = 0
        if chat.id in USER_MESSAGES_COUNT and target_user.id in USER_MESSAGES_COUNT[chat.id]:
            message_count = USER_MESSAGES_COUNT[chat.id][target_user.id]
        
        # تحديد رتبة العضو
        if message_count == 0:
            rank = "🆕 جديد"
        elif message_count < 50:
            rank = "📝 نشط"
        elif message_count < 200:
            rank = "💬 متفاعل"
        elif message_count < 500:
            rank = "🌟 مميز"
        elif message_count < 1000:
            rank = "👑 ذهبي"
        else:
            rank = "🏆 أسطورة"
        
        # بناء قائمة تفاصيل التحذيرات
        warnings_list = ""
        if warnings_details:
            for i, w in enumerate(warnings_details[-3:], 1):  # آخر 3 تحذيرات
                date_str = w['date'].strftime('%Y/%m/%d')
                reason = w['reason'][:30] if len(w['reason']) > 30 else w['reason']
                warnings_list += f"\n   {i}. {w['type']} - {reason} ({date_str})"
        else:
            warnings_list = "\n   لا توجد تحذيرات سابقة"
        
        # معلومات العضو
        info_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👤  مـعـلـومـات الـعـضـو  👤
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

📋 **البيانات الأساسية:**

👤 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

📊 **إحصائيات النشاط:**

💬 **عدد الرسائل:** `{message_count:,}`
🏅 **الرتبة:** {rank}

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **نظام التحذيرات:**

📊 **إجمالي الإنذارات:** `{total_warnings}/{MAX_WARNINGS}`
🔞 **كلمات مسيئة:** `{warnings_data.get('bad_words', 0)}`
🔗 **روابط ممنوعة:** `{warnings_data.get('links', 0)}`
🎯 **الحالة:** {status_color} {status}

━━━━━━━━━━━━━━━━━━━━━━

📝 **آخر التحذيرات:**{warnings_list}

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم الاستعلام بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=info_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(info_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف أمر "معلومات"
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر معلومات: {e}")
        await update.message.reply_text(f"❌ حدث خطأ أثناء محاولة عرض معلومات العضو: {str(e)[:100]}")

async def mute_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """كتم عضو (تقييد) - كتم أو اسكت"""
    
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لكتمه!")
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من الصلاحيات!")
        return
    
    # التحقق من صلاحيات البوت
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت ليس مشرفاً في المجموعة!")
            return
        
        # التحقق من أن البوت لديه صلاحية تقييد الأعضاء
        if not bot_member.can_restrict_members:
            await update.message.reply_text(
                "❌ البوت لا يملك صلاحية تقييد الأعضاء!\n\n"
                "🔧 **الحل:** اذهب إلى إعدادات المجموعة -> المشرفين -> البوت -> فعّل صلاحية 'تقييد الأعضاء'"
            )
            return
    except:
        await update.message.reply_text("❌ حدث خطأ في التحقق من صلاحيات البوت!")
        return
    
    # التحقق من أن العضو المستهدف ليس مشرفاً
    try:
        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator'] and target_user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ لا يمكنك كتم مشرف!")
            return
    except:
        pass
    
    # إنشاء أزرار التأكيد مع تلوين
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الكتم", callback_data=f"mute_confirm_{target_user.id}", style="success"),
         InlineKeyboardButton("❌ إلغاء", callback_data="mute_cancel", style="danger")]
    ])
    
    # إرسال رسالة التأكيد
    await update.message.reply_text(
        f"⏳ **تأكيد كتم العضو لمدة ساعة:**\n\n"
        f"👤 العضو: {target_user.first_name}\n"
        f"🆔 ID: `{target_user.id}`\n"
        f"⏱️ المدة: 1 ساعة\n\n"
        f"هل أنت متأكد من كتم هذا العضو؟",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # حذف أمر "كتم" أو "اسكت"
    try:
        await update.message.delete()
    except:
        pass

async def mute_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على أزرار الكتم"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat = query.message.chat
    data = query.data
    
    if data.startswith("mute_confirm_"):
        member_id = int(data.split("_")[2])
        
        # التحقق من أن المستخدم لا يزال مشرفاً
        try:
            member = await chat.get_member(user.id)
            if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
                await query.edit_message_text("❌ ليس لديك صلاحية الآن!")
                return
        except:
            await query.edit_message_text("❌ حدث خطأ في التحقق من الصلاحيات!")
            return
        
        try:
            # تحديد مدة الكتم (ساعة = 3600 ثانية)
            mute_duration = 3600
            until_date = int(time.time()) + mute_duration
            
            # إنشاء صلاحيات الكتم - باستخدام الصلاحيات الصحيحة للمكتبة الحديثة
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            
            # تطبيق الكتم
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=member_id,
                permissions=permissions,
                until_date=until_date
            )
            
            # الحصول على معلومات العضو
            try:
                target_member = await chat.get_member(member_id)
                target_user = target_member.user
                member_name = target_user.first_name
                if target_user.last_name:
                    member_name += f" {target_user.last_name}"
                member_username = f"@{target_user.username}" if target_user.username else "لا يوجد"
            except:
                member_name = f"عضو {member_id}"
                member_username = "غير معروف"
            
            # تسجيل العضو المكتوم
            if chat.id not in MUTED_USERS:
                MUTED_USERS[chat.id] = {}
            MUTED_USERS[chat.id][member_id] = datetime.fromtimestamp(until_date)
            
            # حساب وقت فك الكتم
            unmute_time = datetime.fromtimestamp(until_date).strftime('%I:%M %p')
            
            # الحصول على صورة العضو
            photo_id = await get_user_profile_photo(member_id, context)
            
            # رسالة التأكيد - مع تصميم جميل
            success_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔇  تـم كـتـم الـعـضـو  🔇
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو المكتوم:**

📛 **الاسم:** `{member_name}`
🆔 **الآيدي:** `{member_id}`
📌 **اليوزرنيم:** {member_username}

━━━━━━━━━━━━━━━━━━━━━━

⏱️ **مدة الكتم:** `1 ساعة`
🕒 **وقت فك الكتم:** `{unmute_time}`

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

📌 **سيتم فك الكتم تلقائياً بعد انتهاء المدة**
"""
            
            # إرسال رسالة النجاح مع الصورة إذا وجدت
            if photo_id:
                await query.message.delete()
                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=photo_id,
                    caption=success_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(success_message, parse_mode=ParseMode.MARKDOWN)
            
            # إرسال إشعار للمطور
            try:
                await context.bot.send_message(
                    chat_id=DEVELOPER_ID,
                    text=f"🔇 **تم كتم عضو**\n\n"
                         f"👤 العضو: {member_name}\n"
                         f"🆔 الآيدي: {member_id}\n"
                         f"👥 المجموعة: {chat.title}\n"
                         f"👮‍♂️ بواسطة: {user.first_name}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
                
        except Exception as e:
            error_str = str(e).lower()
            if "not enough rights" in error_str or "chat_admin_required" in error_str:
                await query.edit_message_text(
                    "❌ **البوت لا يملك صلاحية كافية!**\n\n"
                    "🔧 تأكد من أن البوت لديه صلاحية 'تقييد الأعضاء'",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif "user_admin_invalid" in error_str:
                await query.edit_message_text("❌ لا يمكن كتم مشرف!")
            else:
                await query.edit_message_text(f"❌ حدث خطأ: {str(e)[:100]}")
    
    elif data == "mute_cancel":
        await query.edit_message_text("❌ تم إلغاء عملية الكتم.")

async def delete_200_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف 200 رسالة من المجموعة - حذف 200"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من أن المستخدم هو المطور
    if user.id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")
        return
    
    # التحقق من صلاحيات البوت
    bot_member = await chat.get_member(context.bot.id)
    if bot_member.status not in ['administrator', 'creator']:
        await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لحذف الرسائل!")
        return
    
    count = 200  # عدد ثابت
    
    # إرسال رسالة تأكيد البدء
    processing_msg = await update.message.reply_text(
        f"⏳ **جاري حذف {count} رسالة...**\n\n"
        f"📊 **يرجى الانتظار...**",
        parse_mode=ParseMode.MARKDOWN
    )
    
    deleted_count = 0
    
    try:
        # حذف رسالة الأمر
        try:
            await update.message.delete()
            deleted_count += 1
        except:
            pass
        
        # حذف رسالة المعالجة بعد فترة
        await asyncio.sleep(2)
        try:
            await processing_msg.delete()
            deleted_count += 1
        except:
            pass
        
        # محاولة حذف الرسائل من الكاش
        messages_to_delete = list(MESSAGE_CACHE)[:min(count-2, len(MESSAGE_CACHE))]
        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat.id, message_id=msg_id)
                MESSAGE_CACHE.discard(msg_id)
                deleted_count += 1
                await asyncio.sleep(0.2)  # تأخير بسيط
            except:
                pass
        
        # رسالة التأكيد النهائية
        final_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🗑️  حـذف الـرسـائـل  🗑️
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم حذف الرسائل بنجاح!**

━━━━━━━━━━━━━━━━━━━━━━

📊 **الإحصائيات:**

🔢 **المطلوب حذفه:** `{count}`
✅ **تم الحذف:** `{deleted_count}`
❌ **فشل الحذف:** `{count - deleted_count}`

━━━━━━━━━━━━━━━━━━━━━━

👑 **تم بواسطة:** {DEVELOPER_NAME}

━━━━━━━━━━━━━━━━━━━━━━

⏳ **سيتم حذف هذه الرسالة بعد 5 ثواني**
"""
        
        # إرسال رسالة التأكيد
        result_msg = await context.bot.send_message(
            chat_id=chat.id,
            text=final_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # حذف رسالة التأكيد بعد 5 ثواني
        await asyncio.sleep(5)
        await result_msg.delete()
        
    except Exception as e:
        logger.error(f"خطأ في أمر حذف الرسائل: {e}")
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"❌ حدث خطأ أثناء محاولة حذف الرسائل!\n{str(e)[:100]}"
        )

async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تحذيرات المستخدم بشكل احترافي"""
    user = update.effective_user
    chat = update.effective_chat
    user_id = user.id
    
    # التحقق من الاشتراك في القناة إذا كانت المجموعة
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return
    
    # الحصول على صورة المستخدم
    photo_id = await get_user_profile_photo(user_id, context)
    
    if user_id in USER_WARNINGS:
        warnings_data = USER_WARNINGS[user_id]
        total_warnings = sum(warnings_data.values())
        
        # تحديد حالة المستخدم
        if total_warnings >= 4:
            status = "🔴 **⚠️ تم طردك نهائياً!** 🔴"
        elif total_warnings == 3:
            status = "🟠 **⚠️ أنت معرض للحظر لمدة أسبوع!** 🟠"
        elif total_warnings == 2:
            status = "🟡 **⚠️ أنت معرض للكتم لمدة ساعة!** 🟡"
        elif total_warnings == 1:
            status = "🟢 **⚠️ لديك إنذار واحد** 🟢"
        else:
            status = "🟢 **حالتك جيدة** 🟢"
        
        warnings_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📋  سـجـل الإنـذارات  📋
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **بياناتك:**

📛 **الاسم:** `{user.first_name}` {f'`{user.last_name}`' if user.last_name else ''}

🆔 **الآيدي:** `{user.id}`

📌 **اليوزرنيم:** {'@' + user.username if user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **تفاصيل الإنذارات:**

🔞 **كلمات مسيئة:** `{warnings_data.get('bad_words', 0)}`

🔗 **روابط ممنوعة:** `{warnings_data.get('links', 0)}`

━━━━━━━━━━━━━━━━━━━━━━

📊 **الإحصائيات:**

📈 **إجمالي الإنذارات:** `{total_warnings}/{MAX_WARNINGS}`

{status}

━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        warnings_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          ✅  سـجـل الإنـذارات  ✅
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **بياناتك:**

📛 **الاسم:** `{user.first_name}` {f'`{user.last_name}`' if user.last_name else ''}

🆔 **الآيدي:** `{user.id}`

📌 **اليوزرنيم:** {'@' + user.username if user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

✨ **ليس لديك أي إنذارات** ✨

━━━━━━━━━━━━━━━━━━━━━━

🎉 **أنت عضو ملتزم** 🎉

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # إرسال الصورة مع الرسالة
    if photo_id:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_id,
            caption=warnings_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(warnings_text, parse_mode=ParseMode.MARKDOWN)

async def my_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض عدد رسائل المستخدم في المجموعة بشكل احترافي"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # الحصول على عدد رسائل المستخدم
    message_count = 0
    if chat.id in USER_MESSAGES_COUNT and user.id in USER_MESSAGES_COUNT[chat.id]:
        message_count = USER_MESSAGES_COUNT[chat.id][user.id]
    
    # الحصول على صورة المستخدم
    photo_id = await get_user_profile_photo(user.id, context)
    
    # تحديد الرتبة بناءً على عدد الرسائل
    if message_count == 0:
        rank = "🆕 عضو جديد"
        rank_emoji = "🆕"
    elif message_count < 50:
        rank = "📝 عضو نشط"
        rank_emoji = "📝"
    elif message_count < 200:
        rank = "💬 عضو متفاعل"
        rank_emoji = "💬"
    elif message_count < 500:
        rank = "🌟 عضو مميز"
        rank_emoji = "🌟"
    elif message_count < 1000:
        rank = "👑 عضو ذهبي"
        rank_emoji = "👑"
    else:
        rank = "🏆 أسطورة المجموعة"
        rank_emoji = "🏆"
    
    # تصميم رسالة إحصائية الرسائل
    messages_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📊  إحـصـائـية رسـائـلـك  📊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **بياناتك الشخصية:**

📛 **الاسم:** `{user.first_name}` {f'`{user.last_name}`' if user.last_name else ''}
🆔 **الآيدي:** `{user.id}`
📌 **اليوزرنيم:** {'@' + user.username if user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

📈 **إحصائيات الرسائل:**

━━━━━━━━━━━━━━━━━━━━━━

💬 **عدد رسائلك:** `{message_count:,}` رسالة

🏅 **رتبتك:** {rank} {rank_emoji}

━━━━━━━━━━━━━━━━━━━━━━

📊 **مستوى النشاط:**

{'🟩' * min(message_count // 50, 10)}{'⬜' * (10 - min(message_count // 50, 10))} 
`{min(message_count // 50, 10) * 10}%`

━━━━━━━━━━━━━━━━━━━━━━

🎯 **تابع تفاعلك لتصل إلى رتب أعلى!**

━━━━━━━━━━━━━━━━━━━━━━

📌 **شكراً لتفاعلك في المجموعة** 💙
"""
    
    # إرسال الصورة مع الرسالة
    if photo_id:
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=photo_id,
            caption=messages_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(messages_text, parse_mode=ParseMode.MARKDOWN)
    
    # حذف أمر "رسائلي"
    try:
        await update.message.delete()
    except:
        pass

async def trend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض ترند أفضل 5 أعضاء لديهم أكثر من 1000 رسالة"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من وجود بيانات للمجموعة
    if chat.id not in USER_MESSAGES_COUNT or not USER_MESSAGES_COUNT[chat.id]:
        no_data_text = """
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📊  تـرنـد المجـمـوعـة  📊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

❌ **لا توجد بيانات كافية بعد!**

📝 **قم بالتفاعل في المجموعة لتظهر في الترند**

━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(no_data_text, parse_mode=ParseMode.MARKDOWN)
        return
    
    # تجميع بيانات الأعضاء
    members_data = []
    for user_id, count in USER_MESSAGES_COUNT[chat.id].items():
        if count >= 1000:  # فقط الأعضاء الذين لديهم 1000 رسالة فأكثر
            try:
                # محاولة الحصول على اسم العضو
                member = await context.bot.get_chat_member(chat.id, user_id)
                user_obj = member.user
                name = user_obj.first_name
                if user_obj.last_name:
                    name += f" {user_obj.last_name}"
                username = f"@{user_obj.username}" if user_obj.username else "لا يوجد"
                
                members_data.append({
                    'id': user_id,
                    'name': name,
                    'username': username,
                    'count': count
                })
            except:
                # إذا فشل جلب البيانات، نستخدم معلومات مبسطة
                members_data.append({
                    'id': user_id,
                    'name': f"مستخدم {user_id}",
                    'username': "لا يوجد",
                    'count': count
                })
    
    # ترتيب الأعضاء تنازلياً حسب عدد الرسائل
    members_data.sort(key=lambda x: x['count'], reverse=True)
    
    # أخذ أول 5 أعضاء فقط
    top_members = members_data[:5]
    
    if not top_members:
        no_trend_text = """
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📊  تـرنـد المجـمـوعـة  📊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

❌ **لا يوجد أعضاء تجاوزوا 1000 رسالة بعد!**

📝 **أول عضو يصل إلى 1000 رسالة سيظهر هنا**

━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(no_trend_text, parse_mode=ParseMode.MARKDOWN)
        return
    
    # بناء قائمة الترند
    trend_list = ""
    for i, member in enumerate(top_members):
        medal = TREND_MEDALS[i]
        trend_list += f"""
{medal} **{member['name']}**
   📌 **اليوزر:** {member['username']}
   💬 **الرسائل:** `{member['count']:,}`
   🆔 **الآيدي:** `{member['id']}`
━━━━━━━━━━━━━━━━━━━━━━"""
    
    # إجمالي عدد الأعضاء في الترند
    total_in_trend = len(members_data)
    
    # تصميم رسالة الترند
    trend_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📊  تـرنـد المجـمـوعـة  📊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🏆 **أفضل 5 أعضاء نشطين** (أكثر من 1000 رسالة)
━━━━━━━━━━━━━━━━━━━━━━
{trend_list}

━━━━━━━━━━━━━━━━━━━━━━
📊 **إحصائيات الترند:**
👥 **عدد الأعضاء في الترند:** `{total_in_trend}`
💬 **أعلى عدد رسائل:** `{top_members[0]['count']:,}` رسالة

━━━━━━━━━━━━━━━━━━━━━━
🎯 **تفاعلوا لتدخلوا قائمة الترند!**
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # إرسال رسالة الترند
    await update.message.reply_text(trend_text, parse_mode=ParseMode.MARKDOWN)
    
    # حذف أمر "ترند"
    try:
        await update.message.delete()
    except:
        pass

async def whisky_mention_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد عند ذكر ويسكي"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة إذا كانت المجموعة
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return
    
    # إنشاء زر للتواصل مع المطور مع تلوين
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("اضغط هنا", url=DEVELOPER_LINK, style="primary")]
    ])
    
    # الرسالة الأولى
    first_message = "🎭 لو عاوز تكلمني وعاوز مني حاجه نـط بف اضغط هنا"
    
    # إرسال الرسالة الأولى مع الزر
    await context.bot.send_message(
        chat_id=chat.id,
        text=first_message,
        reply_markup=keyboard
    )
    
    # الرسالة الثانية
    second_message = "بـ𝑩𝒐𝒕ـوت  ويــــسڪي ڪـآن هنـآ"
    
    # إرسال الرسالة الثانية
    await context.bot.send_message(
        chat_id=chat.id,
        text=second_message
    )

async def marry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """زواج عشوائي بين الأعضاء - يعرض اليوزر بدلاً من المعرف"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم ليس متزوجاً بالفعل
    marriage = get_spouse(chat.id, user.id)
    if marriage:
        spouse_id = marriage['user_id'] if marriage['spouse_id'] == user.id else marriage['spouse_id']
        spouse_name = marriage['spouse_name']
        spouse_username = marriage['spouse_username']
        await update.message.reply_text(
            f"❌ أنت متزوج بالفعل من {spouse_username}!\nاستخدم أمر `طلاق` أولاً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # الحصول على عضو عشوائي للزواج
    spouse = await get_random_member(chat.id, context, exclude_ids=[user.id, context.bot.id])
    
    if not spouse:
        await update.message.reply_text("❌ لا يوجد أعضاء كافيين للزواج!")
        return
    
    # التحقق من أن العضو الآخر ليس متزوجاً
    spouse_marriage = get_spouse(chat.id, spouse.id)
    if spouse_marriage:
        # البحث عن عضو آخر
        spouse = await get_random_member(chat.id, context, exclude_ids=[user.id, context.bot.id, spouse.id])
        if not spouse:
            await update.message.reply_text("❌ جميع الأعضاء متزوجون! جرب لاحقاً.")
            return
        # التحقق مرة أخرى
        spouse_marriage = get_spouse(chat.id, spouse.id)
        if spouse_marriage:
            await update.message.reply_text("❌ جميع الأعضاء متزوجون! جرب لاحقاً.")
            return
    
    # الحصول على أسماء الأعضاء واليوزرات
    user_name = user.first_name
    if user.last_name:
        user_name += f" {user.last_name}"
    user_username = f"@{user.username}" if user.username else f"[{user_name}](tg://user?id={user.id})"
    
    spouse_name = spouse.first_name
    if spouse.last_name:
        spouse_name += f" {spouse.last_name}"
    spouse_username = f"@{spouse.username}" if spouse.username else f"[{spouse_name}](tg://user?id={spouse.id})"
    
    # إضافة الزواج إلى قاعدة البيانات
    add_marriage(chat.id, user.id, spouse.id, user_name, spouse_name, user_username, spouse_username)
    
    # رسالة الزواج
    marriage_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          💍  زواج مبارك  💍
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

{user_username} 💞 {spouse_username}

━━━━━━━━━━━━━━━━━━━━━━

مـــــــبــــࢪوك ليڪو وفـࢪح وحـنه ودخله رايــقه 😂❤

━━━━━━━━━━━━━━━━━━━━━━

🎉 **ألف مبروك للعروسين** 🎉
"""
    
    await update.message.reply_text(marriage_message, parse_mode=ParseMode.MARKDOWN)
    
    # حذف أمر "زواج"
    try:
        await update.message.delete()
    except:
        pass

async def divorce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلاق بين الأعضاء المتزوجين - يعرض اليوزر بدلاً من المعرف"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من أن المجموعة جماعية
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ هذا الأمر متاح فقط في المجموعات!")
        return
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من وجود زيجات في هذه المجموعة
    marriage = get_spouse(chat.id, user.id)
    if not marriage:
        await update.message.reply_text("❌ أنت لست متزوجاً! استخدم أمر `زواج` للزواج.", parse_mode=ParseMode.MARKDOWN)
        return
    
    # تحديد الزوج والزوجة
    if marriage['user_id'] == user.id:
        husband_id = marriage['user_id']
        wife_id = marriage['spouse_id']
        husband_name = marriage['user_name']
        wife_name = marriage['spouse_name']
        husband_username = marriage['user_username'] if marriage['user_username'].startswith('@') else f"[{husband_name}](tg://user?id={husband_id})"
        wife_username = marriage['spouse_username'] if marriage['spouse_username'].startswith('@') else f"[{wife_name}](tg://user?id={wife_id})"
    else:
        husband_id = marriage['spouse_id']
        wife_id = marriage['user_id']
        husband_name = marriage['spouse_name']
        wife_name = marriage['user_name']
        husband_username = marriage['spouse_username'] if marriage['spouse_username'].startswith('@') else f"[{husband_name}](tg://user?id={husband_id})"
        wife_username = marriage['user_username'] if marriage['user_username'].startswith('@') else f"[{wife_name}](tg://user?id={wife_id})"
    
    # رسالة الطلاق الأولى - للزوج
    divorce_message_1 = f"""
{husband_username}

━━━━━━━━━━━━━━━━━━━━━━

طلقـناهم يـعم أي خــدمآت 😂❤
"""
    
    # رسالة الطلاق الثانية - للزوجة
    divorce_message_2 = f"""
{wife_username}

━━━━━━━━━━━━━━━━━━━━━━

معـلـش ي مـزه شوفـيلك غيــࢪو ❤️‍🩹
"""
    
    # إرسال رسالتي الطلاق
    await context.bot.send_message(chat_id=chat.id, text=divorce_message_1, parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(1)  # تأخير بسيط بين الرسائل
    await context.bot.send_message(chat_id=chat.id, text=divorce_message_2, parse_mode=ParseMode.MARKDOWN)
    
    # حذف الزواج من قاعدة البيانات
    remove_marriage(chat.id, husband_id)
    remove_marriage(chat.id, wife_id)
    
    # حذف أمر "طلاق"
    try:
        await update.message.delete()
    except:
        pass

async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفع عضو مشرف - رفع مشرف"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لرفع مشرفين!")
            return
        
        # التحقق من أن البوت لديه صلاحية إضافة مشرفين
        if not bot_member.can_promote_members:
            await update.message.reply_text("❌ البوت لا يملك صلاحية إضافة مشرفين!")
            return
        
        target_user = None
        target_username = None
        
        # التحقق من وجود رد على رسالة
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        else:
            # محاولة استخراج اليوزر من النص
            text_parts = update.message.text.split()
            if len(text_parts) > 1:
                target_username = text_parts[1].replace('@', '')
        
        if not target_user and not target_username:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو أو كتابة اليوزر!\nمثال: `رفع مشرف @username`", parse_mode=ParseMode.MARKDOWN)
            return
        
        # إذا كان لدينا يوزر، نحاول الحصول على العضو
        if not target_user and target_username:
            try:
                # البحث عن العضو بواسطة اليوزر
                chat_members = await context.bot.get_chat_administrators(chat.id)
                for admin in chat_members:
                    if admin.user.username and admin.user.username.lower() == target_username.lower():
                        target_user = admin.user
                        break
                
                if not target_user:
                    await update.message.reply_text("❌ لم أتمكن من العثور على العضو بهذا اليوزر!")
                    return
            except Exception as e:
                logger.error(f"خطأ في البحث عن العضو: {e}")
                await update.message.reply_text("❌ حدث خطأ أثناء البحث عن العضو!")
                return
        
        # التحقق من أن العضو ليس مشرفاً بالفعل
        try:
            target_member = await chat.get_member(target_user.id)
            if target_member.status in ['administrator', 'creator']:
                await update.message.reply_text("❌ هذا العضو مشرف بالفعل!")
                return
        except:
            pass
        
        # رفع العضو مشرف
        try:
            await context.bot.promote_chat_member(
                chat_id=chat.id,
                user_id=target_user.id,
                can_change_info=True,
                can_post_messages=True,
                can_edit_messages=True,
                can_delete_messages=True,
                can_invite_users=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_promote_members=False  # منع رفع مشرفين جدد
            )
            
            # الحصول على صورة العضو المرفوع
            photo_id = await get_user_profile_photo(target_user.id, context)
            
            # رسالة التأكيد
            promote_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👑  تـم رفـع مـشـرف  👑
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو المرفوع:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم منحه صلاحيات الإشراف بنجاح**

━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # إرسال الصورة مع الرسالة
            if photo_id:
                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=photo_id,
                    caption=promote_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(promote_message, parse_mode=ParseMode.MARKDOWN)
            
            # حذف أمر الرفع
            try:
                await update.message.delete()
            except:
                pass
                
        except Exception as e:
            logger.error(f"خطأ في رفع مشرف: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء محاولة رفع العضو مشرف!")
            
    except Exception as e:
        logger.error(f"خطأ في أمر رفع مشرف: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة رفع العضو مشرف!")

async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عزل عضو من الإشراف - عزل مشرف"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من أن المستخدم مشرف أو المطور
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لعزل مشرفين!")
            return
        
        # التحقق من أن البوت لديه صلاحية إضافة مشرفين
        if not bot_member.can_promote_members:
            await update.message.reply_text("❌ البوت لا يملك صلاحية عزل مشرفين!")
            return
        
        target_user = None
        target_username = None
        
        # التحقق من وجود رد على رسالة
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        else:
            # محاولة استخراج اليوزر من النص
            text_parts = update.message.text.split()
            if len(text_parts) > 1:
                target_username = text_parts[1].replace('@', '')
        
        if not target_user and not target_username:
            await update.message.reply_text("❌ يجب الرد على رسالة العضو أو كتابة اليوزر!\nمثال: `عزل مشرف @username`", parse_mode=ParseMode.MARKDOWN)
            return
        
        # إذا كان لدينا يوزر، نحاول الحصول على العضو
        if not target_user and target_username:
            try:
                # البحث عن العضو بواسطة اليوزر
                chat_members = await context.bot.get_chat_administrators(chat.id)
                for admin in chat_members:
                    if admin.user.username and admin.user.username.lower() == target_username.lower():
                        target_user = admin.user
                        break
                
                if not target_user:
                    await update.message.reply_text("❌ لم أتمكن من العثور على العضو بهذا اليوزر!")
                    return
            except Exception as e:
                logger.error(f"خطأ في البحث عن العضو: {e}")
                await update.message.reply_text("❌ حدث خطأ أثناء البحث عن العضو!")
                return
        
        # التحقق من أن العضو مشرف بالفعل
        try:
            target_member = await chat.get_member(target_user.id)
            if target_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ هذا العضو ليس مشرفاً!")
                return
            
            # التحقق من أن العضو ليس منشئ المجموعة
            if target_member.status == 'creator':
                await update.message.reply_text("❌ لا يمكن عزل منشئ المجموعة!")
                return
        except:
            await update.message.reply_text("❌ لم أتمكن من العثور على العضو!")
            return
        
        # عزل العضو من الإشراف
        try:
            await context.bot.promote_chat_member(
                chat_id=chat.id,
                user_id=target_user.id,
                can_change_info=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False
            )
            
            # الحصول على صورة العضو المعزول
            photo_id = await get_user_profile_photo(target_user.id, context)
            
            # رسالة التأكيد
            demote_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🔻  تـم عـزل مـشـرف  🔻
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو المعزول:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم سحب صلاحيات الإشراف منه**

━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # إرسال الصورة مع الرسالة
            if photo_id:
                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=photo_id,
                    caption=demote_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(demote_message, parse_mode=ParseMode.MARKDOWN)
            
            # حذف أمر العزل
            try:
                await update.message.delete()
            except:
                pass
                
        except Exception as e:
            logger.error(f"خطأ في عزل مشرف: {e}")
            await update.message.reply_text("❌ حدث خطأ أثناء محاولة عزل العضو من الإشراف!")
            
    except Exception as e:
        logger.error(f"خطأ في أمر عزل مشرف: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة عزل العضو من الإشراف!")

def contains_bad_words(text):
    """فحص النص للكلمات المسيئة"""
    if not text:
        return False, None
        
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True, word
    return False, None

def contains_any_links(text):
    """فحص إذا كان النص يحتوي على أي روابط"""
    if not text:
        return False, None
    
    text_lower = text.lower()
    
    for pattern in LINK_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            return True, matches[0]
    
    return False, None

async def clear_message_cache(message_id, delay):
    """تنظيف ذاكرة التخزين المؤقت للرسائل"""
    await asyncio.sleep(delay)
    if message_id in MESSAGE_CACHE:
        MESSAGE_CACHE.remove(message_id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تعليمات البوت بشكل احترافي - محدث مع الأوامر الجديدة"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة إذا كانت المجموعة
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return
    
    help_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🚀  تـعـلـيـمـات البوت  🚀
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

⚡ **نظام العقوبات المتطور - 4 مراحل:**

━━━━━━━━━━━━━━━━━━━━━━

🟢 **الإنذار الأول:** 📝 تحذير عادي
🟡 **الإنذار الثاني:** 🔇 كتم لمدة ساعة
🟠 **الإنذار الثالث:** ⛔ حظر لمدة أسبوع
🔴 **الإنذار الرابع:** 🚫 طرد نهائي

━━━━━━━━━━━━━━━━━━━━━━

📋 **الممنوعات:**

❌ جميع الروابط الخارجية
❌ روابط t.me / telegram.me
❌ يوزرنيم البوتات (@username)
❌ الكلمات البذيئة والفاحشة

━━━━━━━━━━━━━━━━━━━━━━

👤 **أوامر عامة:**

🔹 `رسائلي` - عرض عدد رسائلك في المجموعة
🔹 `ترند` - عرض أفضل 5 أعضاء نشطين (أكثر من 1000 رسالة)
🔹 `ويسكي` - للتواصل مع المطور
🔹 `زواج` - زواج عشوائي بين الأعضاء
🔹 `طلاق` - طلاق بين الأعضاء المتزوجين
🔹 `id` - عرض معرفك مع رسالة مضحكة
🔹 `المالك` - عرض منشئ المجموعة
🔹 `/warnings` - عرض تحذيراتك
🔹 `/rules` - عرض قواعد المجموعة

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **أوامر المشرفين:**

🔹 `.حظر` - حظر عضو لمدة اسبوع (بالرد على الرسالة)
🔹 `.طرد` - طرد عضو نهائياً (بالرد على الرسالة)
🔹 `.تثبيت` - تثبيت رسالة مهمة (بالرد على الرسالة)
🔹 `.حذف` - حذف رسالة (بالرد على الرسالة)
🔹 `رفع مشرف` - رفع عضو مشرف (بالرد أو باليوزر)
🔹 `عزل مشرف` - عزل عضو من الإشراف (بالرد أو باليوزر)
🔹 `حذف التحذيرات` - إزالة جميع تحذيرات العضو (بالرد)
🔹 `تحذير` - إضافة تحذير للعضو (بالرد)
🔹 `قفل مؤقت` - قفل المجموعة مؤقتاً وحذف الرسائل
🔹 `فتح` - فتح المجموعة بعد القفل المؤقت
🔹 `كتم` أو `اسكت` - كتم عضو (تقييد) لمدة ساعة
🔹 `إلغاء كتم` أو `اتكلم` - إلغاء كتم العضو والسماح له بالدردشة ✅ **(جديد)**
🔹 `إلغاء الحظر` - إلغاء حظر العضو والسماح له بالعودة ✅ **(جديد)**
🔹 `إلغاء تثبيت الرسائل` - حذف جميع الرسائل المثبتة
🔹 `معلومات` - عرض معلومات العضو (بالرد)

━━━━━━━━━━━━━━━━━━━━━━

👑 **أوامر المطور فقط:**

🔹 `إرسال (الرسالة)` - إرسال رسالة لجميع المجموعات
🔹 `حذف 200` - حذف 200 رسالة من المجموعة
🔹 `تحفيل` - **أمر جديد** 🎭 (بالرد على رسالة العضو) - إرسال 7 رسائل تحفيل للعضو
🔹 `معلش يحب` - **أمر جديد** 💙 (بالرد على رسالة العضو) - إرسال رسالة اعتذار للعضو

━━━━━━━━━━━━━━━━━━━━━━

💬 **نظام التفاعل الذكي:**

🔹 البوت يرد تلقائياً على هذه الكلمات أينما وجدت في الرسالة:
   • 😂 • بحبك • شخرت • سحوره • بوسه
   • وسكي • حد هنا • جوزوني • زهقان • مبضون
   • تعبان • مدايق • عاملين ايه • رحتو فين
   • الحمدلله • كويس • ممكن نتعرف • عرفوني عليكو
   • السلام عليكم • سلام عليكم • نتعرف • اسمك
   • بوت • هههه • قلبي • اي • ايه • همووت
   • عامله اي • عامله ايه • احا • مالك

━━━━━━━━━━━━━━━━━━━━━━

📢 **قناة التحديثات:**

🔹 اشترك في قناتنا ليصلك كل جديد: @{CHANNEL_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━

🎨 **ميزات جديدة في الإصدار v4.7.0:**

🔹 **تلوين الأزرار الشفافة** - أزرار ملونة وجذابة
🔹 **الإذاعة المركزية** - إرسال رسائل للمستخدمين (للمطور والمشرفين)
🔹 **عرض اليوزر في الزواج والطلاق** - بدلاً من المعرف

━━━━━━━━━━━━━━━━━━━━━━

📞 **للتواصل مع المطور:**
[💬 اضغط هنا للمراسلة]({DEVELOPER_LINK})

━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قواعد المجموعة بشكل احترافي - محدث لنظام 4 مراحل"""
    user = update.effective_user
    chat = update.effective_chat
    
    # التحقق من الاشتراك في القناة إذا كانت المجموعة
    if chat.type in ['group', 'supergroup']:
        is_subscribed = await check_channel_subscription(user.id, context)
        if not is_subscribed:
            await send_channel_subscription_message(update, context)
            return
    
    rules_text = """
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📜  قـواعـد المجـمـوعة  📜
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

🚫 **الممنوعات:**

━━━━━━━━━━━━━━━━━━━━━━

❌ **الروابط:** ممنوع إرسال أي روابط
❌ **البوتات:** ممنوع إرسال يوزرنيم البوتات
❌ **الألفاظ:** ممنوع استخدام الكلمات النابية
❌ **الإعلانات:** ممنوع الترويج لقنوات/مجموعات
❌ **المحتوى:** ممنوع إرسال محتوى فاضح

━━━━━━━━━━━━━━━━━━━━━━

✅ **المسموحات:**

━━━━━━━━━━━━━━━━━━━━━━

✔️ الاحترام بينك وبين الناس 
✔️ الالتزام بإحترامك وأدبك يحب
✔️ الرغي بأحترام وححبڪ
✔️ تتڪلم مع اخواتك بأدب

━━━━━━━━━━━━━━━━━━━━━━

⚖️ **نظام العقوبات - 4 مراحل:**

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **الإنذار الأول:** 📝 تحذير عادي
⚠️ **الإنذار الثاني:** 🔇 كتم لمدة ساعة
⚠️ **الإنذار الثالث:** ⛔ حظر لمدة أسبوع
⚠️ **الإنذار الرابع:** 🚫 طرد نهائي

━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات البوت بشكل احترافي - محدث مع إحصائيات الزواج والتفاعل"""
    user = update.effective_user
    if user.id == DEVELOPER_ID:
        total_users = len(USER_WARNINGS)
        total_warnings_count = sum(sum(warnings.values()) for warnings in USER_WARNINGS.values())
        
        # إحصائيات الرسائل والترند
        total_messages = 0
        total_members_with_messages = 0
        total_trend_members = 0
        
        for chat_id, users in USER_MESSAGES_COUNT.items():
            total_members_with_messages += len(users)
            total_messages += sum(users.values())
            # حساب الأعضاء الذين تجاوزوا 1000 رسالة
            total_trend_members += sum(1 for count in users.values() if count >= 1000)
        
        # إحصائيات الزواج
        conn = sqlite3.connect(MARRIAGE_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM marriages")
        total_married = c.fetchone()[0]
        conn.close()
        total_married_couples = total_married // 2
        
        # إحصائيات المجموعات المقفلة
        locked_groups_count = sum(1 for locked in LOCKED_CHATS.values() if locked)
        
        # إحصائيات المكتومين
        total_muted_users = sum(len(muted) for muted in MUTED_USERS.values())
        
        # إجمالي المستخدمين المسجلين
        total_registered_users = len(get_all_users_from_database())
        
        stats_text = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📊  إحـصـائـيات البوت  📊
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👨‍💻 **المطور:** {DEVELOPER_NAME}
🆔 **آيدي المطور:** `{DEVELOPER_ID}`
🟢 **حالة البوت:** نشط
📌 **الإصدار:** `v4.7.0` ✨

━━━━━━━━━━━━━━━━━━━━━━

📊 **إحصائيات المستخدمين:**

👥 **المستخدمين المسجلين:** `{total_registered_users}`
⚠️ **المستخدمين المخالفين:** `{total_users}`
📝 **إجمالي الإنذارات:** `{total_warnings_count}`

━━━━━━━━━━━━━━━━━━━━━━

📈 **إحصائيات الرسائل والترند:**

💬 **إجمالي الرسائل:** `{total_messages:,}`
👥 **الأعضاء النشطين:** `{total_members_with_messages}`
🏆 **أعضاء الترند (+1000):** `{total_trend_members}`
📌 **المجموعات النشطة:** `{len(USER_MESSAGES_COUNT)}`

━━━━━━━━━━━━━━━━━━━━━━

💑 **إحصائيات الزواج:**

💍 **أزواج حالياً:** `{total_married_couples}`

━━━━━━━━━━━━━━━━━━━━━━

🔒 **إحصائيات القفل والكتم:**

🔐 **مجموعات مقفلة:** `{locked_groups_count}`
🔓 **مجموعات مفتوحة:** `{len(LOCKED_CHATS) - locked_groups_count}`
🔇 **أعضاء مكتومين:** `{total_muted_users}`

━━━━━━━━━━━━━━━━━━━━━━

💬 **نظام التفاعل الذكي:**

🔹 **كلمات تفاعلية:** `{len(INTERACTION_RESPONSES)}`
🔹 **أدوات النداء:** `{len(MENTION_TOOLS)}`
🔹 **ردود خاصة للمطور:** متاحة

━━━━━━━━━━━━━━━━━━━━━━

⚡ **نظام العقوبات - 4 مراحل:**

📝 **تحذير عادي** - الإنذار الأول
🔇 **كتم (ساعة)** - الإنذار الثاني
⛔ **حظر (أسبوع)** - الإنذار الثالث
🚫 **طرد (نهائي)** - الإنذار الرابع

━━━━━━━━━━━━━━━━━━━━━━

🎨 **الميزات الجديدة (v4.7.0):**

🎨 **تلوين الأزرار الشفافة**
📢 **الإذاعة المركزية للمطور والمشرفين**
👤 **عرض اليوزر في الزواج والطلاق**

━━━━━━━━━━━━━━━━━━━━━━

📢 **قناة التحديثات:**

📌 **القناة:** @{CHANNEL_USERNAME}

━━━━━━━━━━━━━━━━━━━━━━

💾 **حالة الذاكرة:**

📌 **رسائل مخزنة:** `{len(MESSAGE_CACHE)}`
⚠️ **تحذيرات نشطة:** `{total_warnings_count}`

━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ هذا الأمر متاح للمطور فقط!")

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظيف التحذيرات والرسائل"""
    user = update.effective_user
    chat = update.effective_chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    global USER_WARNINGS, USER_WARNINGS_DETAILS, USER_MESSAGES_COUNT, LOCKED_CHATS, MUTED_USERS
    USER_WARNINGS = {}
    USER_WARNINGS_DETAILS = {}
    USER_MESSAGES_COUNT = {}
    LOCKED_CHATS = {}
    MUTED_USERS = {}
    MESSAGE_CACHE.clear()
    
    # تنظيف قاعدة بيانات الزواج
    conn = sqlite3.connect(MARRIAGE_DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM marriages")
    conn.commit()
    conn.close()
    
    clean_text = """
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🧹  تـنـظـف البيانـات  🧹
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم تنظيف جميع البيانات بنجاح**

📌 **تم مسح:**
   • جميع التحذيرات
   • جميع تفاصيل المخالفات
   • إحصائيات الرسائل
   • قائمة الترند
   • جميع حالات الزواج والطلاق
   • حالات القفل المؤقت
   • قائمة المكتومين
   • ذاكرة التخزين المؤقت

━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(clean_text, parse_mode=ParseMode.MARKDOWN)

# ============ أوامر المشرفين الأساسية ============

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حظر عضو لمدة اسبوع - .حظر بالرد على الرسالة"""
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لحظره!\nمثال: .حظر (بالرد على الرسالة)")
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من صلاحيات المستخدم
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لحظر الأعضاء!")
            return
        
        # التحقق من عدم حظر المشرفين أو المطور
        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator'] or target_user.id == DEVELOPER_ID:
            await update.message.reply_text("❌ لا يمكنك حظر مشرف أو المطور!")
            return
        
        # حظر العضو لمدة اسبوع
        until_date = int(time.time()) + 604800  # 7 أيام
        
        await context.bot.ban_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            until_date=until_date
        )
        
        # إرسال رسالة وداع
        await goodbye_member(update, context)
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # رسالة التأكيد
        ban_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          ⛔  تـم الـحـظر  ⛔
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو المخالف:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

⏰ **مدة الحظر:** `7 أيام`

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

⏳ **سيتم فك الحظر تلقائياً بعد اسبوع**
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=ban_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(ban_message, parse_mode=ParseMode.MARKDOWN)
            
        # حذف أمر الحظر
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر الحظر: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة حظر العضو!")


async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طرد عضو نهائي - .طرد بالرد على الرسالة"""
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على رسالة العضو لطرده!\nمثال: .طرد (بالرد على الرسالة)")
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_user = update.message.reply_to_message.from_user
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من صلاحيات المستخدم
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لطرد الأعضاء!")
            return
        
        # التحقق من عدم طرد المشرفين أو المطور
        target_member = await chat.get_member(target_user.id)
        if target_member.status in ['administrator', 'creator'] or target_user.id == DEVELOPER_ID:
            await update.message.reply_text("❌ لا يمكنك طرد مشرف أو المطور!")
            return
        
        # طرد العضو نهائياً
        await context.bot.ban_chat_member(
            chat_id=chat.id,
            user_id=target_user.id
        )
        
        # فك الحظر بعد الطرد مباشرة ليتمكن من الدخول مرة أخرى إذا أراد المشرف
        await context.bot.unban_chat_member(
            chat_id=chat.id,
            user_id=target_user.id
        )
        
        # إرسال رسالة وداع
        await goodbye_member(update, context)
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(target_user.id, context)
        
        # رسالة التأكيد
        kick_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🚫  تـم الـطـرد  🚫
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👤 **العضو المخالف:**

📛 **الاسم:** `{target_user.first_name}` {f'`{target_user.last_name}`' if target_user.last_name else ''}
🆔 **الآيدي:** `{target_user.id}`
📌 **اليوزرنيم:** {'@' + target_user.username if target_user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

🚷 **نوع العقوبة:** `طرد نهائي`

👮‍♂️ **تم بواسطة:** {user.first_name}

━━━━━━━━━━━━━━━━━━━━━━

❌ **تم طرد العضو من المجموعة**
"""
        
        # إرسال الصورة مع الرسالة
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=kick_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(kick_message, parse_mode=ParseMode.MARKDOWN)
            
        # حذف أمر الطرد
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر الطرد: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة طرد العضو!")


async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تثبيت رسالة مهمة - .تثبيت بالرد على الرسالة"""
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على الرسالة التي تريد تثبيتها!\nمثال: .تثبيت (بالرد على الرسالة)")
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_message = update.message.reply_to_message
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من صلاحيات المستخدم
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لتثبيت الرسائل!")
            return
        
        # تثبيت الرسالة
        await context.bot.pin_chat_message(
            chat_id=chat.id,
            message_id=target_message.message_id,
            disable_notification=False
        )
        
        # رسالة التأكيد
        pin_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          📌  تـم التـثبـيت  📌
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم تثبيت الرسالة بنجاح**

👮‍♂️ **تم بواسطة:** {user.first_name}

📌 **الرسالة:** {target_message.text[:50]}... إذا وجد نص

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        await update.message.reply_text(pin_message, parse_mode=ParseMode.MARKDOWN)
            
        # حذف أمر التثبيت
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر التثبيت: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة تثبيت الرسالة!")


async def delete_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف رسالة - .حذف بالرد على الرسالة"""
    # التحقق من أن الأمر تم بالرد على رسالة
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ يجب الرد على الرسالة التي تريد حذفها!\nمثال: .حذف (بالرد على الرسالة)")
        return
    
    user = update.effective_user
    chat = update.effective_chat
    target_message = update.message.reply_to_message
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await check_channel_subscription(user.id, context)
    if not is_subscribed:
        await send_channel_subscription_message(update, context)
        return
    
    # التحقق من صلاحيات المستخدم
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['administrator', 'creator'] and user.id != DEVELOPER_ID:
            await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
            return
        
        # التحقق من صلاحيات البوت
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ البوت يحتاج صلاحيات المشرف لحذف الرسائل!")
            return
        
        # حذف الرسالة المستهدفة
        await target_message.delete()
        
        # الحصول على صورة المشرف
        photo_id = await get_user_profile_photo(user.id, context)
        
        # رسالة التأكيد
        delete_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🗑️  تـم حـذف الـرسـالـة  🗑️
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

👮‍♂️ **تم بواسطة:**

📛 **الاسم:** `{user.first_name}` {f'`{user.last_name}`' if user.last_name else ''}
🆔 **الآيدي:** `{user.id}`
📌 **اليوزرنيم:** {'@' + user.username if user.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

✅ **تم حذف الرسالة بنجاح**

📌 **صاحب الرسالة:** {target_message.from_user.first_name}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال رسالة التأكيد
        if photo_id:
            sent_msg = await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=delete_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            sent_msg = await update.message.reply_text(delete_message, parse_mode=ParseMode.MARKDOWN)
        
        # حذف رسالة التأكيد بعد 5 ثواني
        await asyncio.sleep(5)
        await sent_msg.delete()
        
        # حذف أمر الحذف
        try:
            await update.message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في أمر حذف الرسالة: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء محاولة حذف الرسالة!")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الترحيب بالأعضاء الجدد بشكل احترافي"""
    for member in update.message.new_chat_members:
        # تجاهل البوت نفسه
        if member.id == context.bot.id:
            continue
            
        try:
            # حفظ المستخدم في قاعدة البيانات
            save_user_to_database(member.id, member.username or "", member.first_name)
            
            # الحصول على صورة العضو
            photo_id = await get_user_profile_photo(member.id, context)
            
            # اختيار رسالة ترحيب عشوائية
            welcome_text = random.choice(WELCOME_MESSAGES)
            
            # تصميم رسالة الترحيب
            welcome_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          🎭  عـضـو جـديـد  🎭
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

{welcome_text} ❤️

━━━━━━━━━━━━━━━━━━━━━━

📋 **بيانات العضو:**

👤 **الاسم:** `{member.first_name}` {f'`{member.last_name}`' if member.last_name else ''}

🆔 **الآيدي:** `{member.id}`

📌 **اليوزرنيم:** {'@' + member.username if member.username else 'لا يوجد'}

━━━━━━━━━━━━━━━━━━━━━━

🌟 **نورت المجموعة ياغالي** 🌟

━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # إرسال الصورة مع الرسالة
            if photo_id:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_id,
                    caption=welcome_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"خطأ في الترحيب بالعضو الجديد: {e}")

async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة وداع احترافية عند خروج أو حظر أو طرد عضو"""
    try:
        # تجاهل إذا كان البوت نفسه هو الخارج
        if update.message.left_chat_member.id == context.bot.id:
            return
            
        member = update.message.left_chat_member
        chat = update.effective_chat
        
        # تحديد سبب الخروج
        action_type = "خرج"
        
        # الحصول على صورة العضو
        photo_id = await get_user_profile_photo(member.id, context)
        
        # اسم العضو
        member_name = member.first_name
        if member.last_name:
            member_name += f" {member.last_name}"
        
        # اليوزر
        member_username = f"@{member.username}" if member.username else "لا يوجد"
        
        # رسالة الوداع
        goodbye_message = f"""
╭─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╮

          👋  وداعـاً  👋
          
╰─── ⋅ ⋅ ⋅ ──────── ✦ ──────── ⋅ ⋅ ⋅ ───╯

━━━━━━━━━━━━━━━━━━━━━━

💔 **مع السلامة هتوحشنا كنت طيب، محدش يزعل عليه اللي يروح يجي غيره أحسن منه 💓🪶**

━━━━━━━━━━━━━━━━━━━━━━

📋 **بيانات العضو الذي {action_type}:**

👤 **الاسم:** `{member_name}`

🆔 **الآيدي:** `{member.id}`

📌 **اليوزرنيم:** {member_username}

📅 **تاريخ {action_type}:** `{datetime.now().strftime('%Y/%m/%d - %I:%M %p')}`

━━━━━━━━━━━━━━━━━━━━━━

💬 **نتمنى لك التوفيق في مكان آخر** 💔

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # إرسال الصورة مع رسالة الوداع
        if photo_id:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=photo_id,
                caption=goodbye_message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=chat.id,
                text=goodbye_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة الوداع: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء وتجميعها في ملف"""
    error_info = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error": str(context.error),
        "update": update.to_dict() if update else None
    }
    
    # تخزين الخطأ في القائمة
    BOT_ERRORS.append(error_info)
    if len(BOT_ERRORS) > 100:
        BOT_ERRORS.pop(0)
    
    # تسجيل الخطأ في ملف
    error_log_file = "bot_errors.json"
    try:
        if os.path.exists(error_log_file):
            with open(error_log_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        else:
            errors = []
        
        errors.insert(0, error_info)
        errors = errors[:50]  # الاحتفاظ بآخر 50 خطأ فقط
        
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ سجل الأخطاء: {e}")
    
    logger.error(f"حدث خطأ: {context.error}")
    
    # إرسال إشعار للمطور
    try:
        await context.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=f"⚠️ **خطأ في البوت:**\n`{str(context.error)[:200]}`",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر (بالأحرف اللاتينية فقط)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("clean", clean))
    application.add_handler(CommandHandler("warnings", warnings_command))
    
    # معالج أمر القائمة - نستخدم MessageHandler مع Regex
    application.add_handler(MessageHandler(
        filters.Regex(r'^/القائمة$'), 
        menu_command
    ))
    
    # إضافة معالجات الأوامر للمشرفين (بالنقطة)
    application.add_handler(MessageHandler(
        filters.Regex(r'^\.حظر$') & filters.REPLY, 
        ban_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^\.طرد$') & filters.REPLY, 
        kick_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^\.تثبيت$') & filters.REPLY, 
        pin_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^\.حذف$') & filters.REPLY, 
        delete_message_command
    ))
    
    # معالجات الأوامر الجديدة
    application.add_handler(MessageHandler(
        filters.Regex(r'^إلغاء كتم$') & filters.REPLY, 
        unmute_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^اتكلم$') & filters.REPLY, 
        unmute_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^إلغاء الحظر$') & filters.REPLY, 
        unban_command
    ))
    
    # معالجة أمر "المالك" الجديد
    application.add_handler(MessageHandler(
        filters.Regex(r'^المالك$'), 
        owner_command
    ))
    
    # معالجة أوامر المطور الجديدة
    application.add_handler(MessageHandler(
        filters.Regex(r'^تحفيل$') & filters.REPLY, 
        tahfil_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^معلش يحب$') & filters.REPLY, 
        sorry_command
    ))
    
    # معالجة الأعضاء الجدد
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, 
        welcome_new_member
    ))
    
    # معالجة خروج الأعضاء
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        goodbye_member
    ))
    
    # معالجة الرسائل النصية
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message
    ))
    
    # معالجة أزرار القائمة والكتم والزر الشفاف والإذاعة
    application.add_handler(CallbackQueryHandler(menu_callback_handler, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(mute_callback_handler, pattern="^mute_"))
    application.add_handler(CallbackQueryHandler(show_main_menu_callback, pattern="^show_main_menu$"))
    application.add_handler(CallbackQueryHandler(menu_callback_handler, pattern="^broadcast_"))
    
    application.add_error_handler(error_handler)
    
    logger.info(f"🤖 بوت الحماية {DEVELOPER_NAME} يعمل بنجاح مع القائمة السفلية المتطورة...")
    print(f"""
    ═══════════════════════════════════════
          🤖 بوت الحماية {DEVELOPER_NAME} 🤖
    ═══════════════════════════════════════
    
    🔒 الوظائف المحدثة:
      ✅ زر قائمة في الشريط السفلي ✅
      ✅ أمر "القائمة" لعرض الأزرار التفاعلية
      ✅ 8 أزرار في القائمة التفاعلية (سـورس || سـحـوره)
      ✅ زر شفاف في /start لفتح القائمة
      ✅ نظام التحقق من الاشتراك في القناة
      ✅ أمر "المالك" لعرض منشئ المجموعة
      ✅ أمر "إلغاء كتم" / "اتكلم"
      ✅ أمر "إلغاء الحظر"
      ✅ منع جميع الروابط
      ✅ منع الكلمات المسيئة
      ✅ ترحيب احترافي بالصور
      ✅ نظام 4 مراحل للعقوبات
      ✅ عرض بيانات كاملة مع الصور
      ✅ إحصاء عدد رسائل الأعضاء
      ✅ أمر "رسائلي" للأعضاء
      ✅ أمر "ترند" لأفضل 5 أعضاء
      ✅ أمر "ويسكي" للتواصل مع المطور
      ✅ رفع وعزل المشرفين
      ✅ نظام زواج وطلاق عشوائي
      ✅ نظام تفاعل ذكي مع الأعضاء
    
    ⚡ **القائمة السفلية المتطورة (v4.7.0):**
      🆕 **➕ أضفني إلى مجموعتك** - رابط إضافة مباشر
      🆕 **⚡ أوامـــر الـــمطور ⚡** - قائمة أوامر المطور
      🆕 **📢 الإذاعة المركزية** - إرسال رسائل للمستخدمين (للمطور والمشرفين)
      🆕 **قائمة رئيسية** - 9 أزرار رئيسية مع تلوين
      🆕 **أوامر الأعضاء** - 7 أزرار فرعية
      🆕 **أوامر المشرفين** - 12 زر إداري
      🆕 **تفاعل ذكي** - 10 أزرار تفاعلية
      🆕 **ترند وإحصائيات** - 4 أزرار إحصائية
      🆕 **زواج وطلاق** - 4 أزرار عائلية
      🆕 **المطور** - 6 أزرار للمطور
    
    ⚡ **الإصدار v4.7.0 - الميزات الجديدة:**
      🎨 **تلوين الأزرار الشفافة** (primary, danger, success)
      📢 **الإذاعة المركزية** - للمطور والمشرفين
      👤 **عرض اليوزر في الزواج والطلاق** بدلاً من المعرف
    
    ⚡ **قائمة أوامر المطور الاحترافية:**
      🎭 تحفيل - 💙 معلش يحب
      📢 إرسال رسالة جماعية - 🗑️ حذف 200
      📊 إحصائيات البوت - 🧹 تنظيف البيانات
      👥 إحصائيات الأعضاء - 🔒 إحصائيات القفل
      💍 إحصائيات الزواج - 💬 إحصائيات التفاعل
      📋 عرض جميع المجموعات - 🔄 تحديث البيانات
    
    ⚡ أوامر المطور الجديدة (الإصدار v4.7.0):
      🎭 **تحفيل** - إرسال 7 رسائل تحفيل للعضو (بالرد)
      💙 **معلش يحب** - إرسال رسالة اعتذار للعضو (بالرد)
    
    ⚡ نظام العقوبات - 4 مراحل:
      📝 الإنذار الأول: تحذير عادي
      🔇 الإنذار الثاني: كتم ساعة
      ⛔ الإنذار الثالث: حظر أسبوع
      🚫 الإنذار الرابع: طرد نهائي
    
    📋 القائمة التفاعلية (9 أزرار مع تلوين):
      🔹 زر المطور (primary)
      🔹 زر أوامر المشرفين (danger)
      🔹 زر مميزات البوت (success)
      🔹 زر أوامر الأعضاء (primary)
      🔹 زر إضافة البوت للمجموعة (success)
      🔹 زر القوانين (danger)
      🔹 زر سـورس || سـحـوره (primary)
      🔹 زر الإذاعة المركزية (primary) - جديد!
      🔹 زر أوامر المطور (danger - للمطور فقط)
    
    📢 قناة التحديثات: @{CHANNEL_USERNAME}
    
    ⚡ الحالة: نشط (نسخة v4.7.0) - مع القائمة السفلية المتطورة وتلوين الأزرار
    ═══════════════════════════════════════
    """)
    
    # ============ خادم الويب لإبقاء البوت مستيقظاً ============
from flask import Flask
from threading import Thread

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 البوت يعمل على SnapDeploy!"

@flask_app.route('/health')
def health():
    return "OK"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

# تشغيل خادم الويب في خيط منفصل
Thread(target=run_web_server, daemon=True).start()

if __name__ == '__main__':
    main()