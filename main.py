import os
import re
import discord
from discord.ext import commands
from aiohttp import web
from dotenv import load_dotenv
import datetime
import logging

# إعداد نظام تسجيل السجلات لمراقبة الأخطاء في Render بدقة
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GestaxNotifier")

load_dotenv()

TOKEN = os.getenv("NOTIFIER_BOT_TOKEN")
EMAIL_CHANNEL_ID = int(os.getenv("CHANNEL_EMAIL_ID", 0))
INSTAGRAM_CHANNEL_ID = int(os.getenv("CHANNEL_INSTAGRAM_ID", 0))
FACEBOOK_CHANNEL_ID = int(os.getenv("CHANNEL_FACEBOOK_ID", 0))

intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix="?", intents=intents)

RTL = "\u202b"
LRM = "\u200E"
WIDTH_HACK = "\u2800" * 45  

def detect_rtl(text):
    """تفحص الدالة ما إذا كان النص يحتوي على حروف عربية لتحديد اتجاه القراءة الصحيح في ديسكورد"""
    if re.search(r'[\u0600-\u06FF]', text):
        return "\u200F"  # رمز (Right-to-Left Mark) لإجبار ديسكورد على بدء السطر من اليمين
    return ""  # نص فارغ إذا كانت الرسالة إنجليزية بالكامل


# دالة آمنة لجلب القنوات لتفادي مشاكل الـ Cache في ديسكورد
async def safely_get_channel(channel_id):
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            logger.error(f"⚠️ فشل جلب القناة {channel_id} من ديسكورد: {e}")
            return None
    return channel

# --------------------------------------------------------
# 🌐 مستقبل الويب هوك الاحترافي (API Endpoint)
# --------------------------------------------------------
async def handle_webhook(request):
    try:
        source = request.match_info.get('source', '').lower()
        
        # التأكد من صحة البيانات القادمة وتجنب انهيار السيرفر لو كانت فارغة
        try:
            data = await request.json()
        except Exception:
            logger.warning("❌ تم استقبال طلب بجسم بيانات (Body) غير صالح أو ليس JSON")
            return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)
        
        if not bot.is_ready():
            return web.json_response({"status": "retry", "message": "Bot is booting up..."}, status=503)

        logger.info(f"📥 تم استقبال إشعار جديد من المصدر: {source}")

        # --- 1. معالجة إشعارات البريد الإلكتروني ---
        if source == "email":
            channel = await safely_get_channel(EMAIL_CHANNEL_ID)
            if channel:
                subject = data.get('subject', 'بدون عنوان').strip() or 'بدون عنوان'
                sender = data.get('sender', 'غير معروف').strip() or 'غير معروف'
                snippet = data.get('snippet', 'لا يوجد محتوى معاينة').strip() or 'لا يوجد محتوى معاينة'

                # الفحص التلقائي الذكي للغة لتحديد اتجاه النصوص
                email_rtl = detect_rtl(snippet)
                subject_rtl = detect_rtl(subject)

                # تصميم هندسي منظم يفصل البيانات لسهولة القراءة
                embed = discord.Embed(
                    title="📬 إشعار بريد إلكتروني جديد",
                    color=0xEA4335,  # لون Gmail الأحمر الرسمي
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                
                # حقل المرسل: معزول داخل كود بلوك لحماية بنية الاسم والإيميل من التداخل
                embed.add_field(
                    name="👤 المُرْسِل", 
                    value=f"`{sender}`", 
                    inline=False
                )
                
                # حقل العنوان (مع فحص لغوي)
                embed.add_field(
                    name="📌 الموضوع", 
                    value=f"**{subject_rtl}{subject}**", 
                    inline=False
                )
                
                # حقل المحتوى (مع فحص لغوي واقتباس عمودي جمالي)
                embed.add_field(
                    name="📝 نص الرسالة", 
                    value=f"> {email_rtl}{snippet}", 
                    inline=False
                )

                embed.set_footer(text=f"{LRM}Gestax Mail System{LRM}")
                await channel.send(embed=embed)
                return web.json_response({"status": "success"}, status=200)

        # --- 2. معالجة إشعارات إنستغرام ---
        elif source == "instagram":
            channel = await safely_get_channel(INSTAGRAM_CHANNEL_ID)
            if channel:
                caption = data.get('caption', 'منشور جديد بدون نص').strip() or 'منشور جديد بدون نص'
                post_url = data.get('url', '').strip()
                image_url = data.get('image_url', '').strip()

                embed = discord.Embed(
                    title="📸 منشور إنستغرام جديد",
                    description=f"{RTL}{caption}" + (f"\n\n🔗 [عرض المنشور]({post_url})" if post_url else ""),
                    color=0xE1306C,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                if image_url and image_url.startswith("http"):
                    embed.set_image(url=image_url)
                embed.set_footer(text=f"Gestax Instagram Monitor{WIDTH_HACK}")
                await channel.send(embed=embed)
                return web.json_response({"status": "success"}, status=200)

        # --- 3. معالجة إشعارات فيسبوك ---
        elif source == "facebook":
            channel = await safely_get_channel(FACEBOOK_CHANNEL_ID)
            if channel:
                message = data.get('message', 'منشور جديد بدون نص').strip() or 'منشور جديد بدون نص'
                post_url = data.get('url', '').strip()
                image_url = data.get('image_url', '').strip()

                embed = discord.Embed(
                    title="🔵 منشور فيسبوك جديد",
                    description=f"{RTL}{message}" + (f"\n\n🔗 [عرض المنشور]({post_url})" if post_url else ""),
                    color=0x1877F2,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                if image_url and image_url.startswith("http"):
                    embed.set_image(url=image_url)
                embed.set_footer(text=f"Gestax Facebook Monitor{WIDTH_HACK}")
                await channel.send(embed=embed)
                return web.json_response({"status": "success"}, status=200)

        # إذا كان المصدر غير معروف أو القناة لم يتم تحديدها في .env
        logger.warning(f"⚠️ مصدر غير معروف أو قناة غير مهيأة للمصدر: {source}")
        return web.json_response({"status": "ignored", "message": "Source unknown or channel configuration missing"}, status=400)

    except Exception as e:
        logger.error(f"❌ خطأ حرج غير متوقع داخل الـ Webhook Handler: {e}", exc_info=True)
        return web.json_response({"status": "error", "message": "Internal Server Error"}, status=500)

async def start_web_server():
    app = web.Application()
    app.router.add_post('/webhook/{source}', handle_webhook)
    app.router.add_get('/', lambda r: web.Response(text="Gestax API Gateway is fully operational! 🚀", status=200))
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 [API SERVER] يعمل بنجاح على المنفذ السحابي {port}")

async def setup_hook():
    bot.loop.create_task(start_web_server())

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    logger.info(f"🔥 تم تسجيل الدخول بنجاح! البوت أونلاين: {bot.user}")

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ خطأ: لم يتم العثور على NOTIFIER_BOT_TOKEN في متغيرات البيئة!")
    else:
        bot.run(TOKEN)