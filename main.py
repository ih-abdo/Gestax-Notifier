import os
import re
import discord
from discord.ext import commands
from discord import ui, app_commands
from aiohttp import web
from dotenv import load_dotenv
import datetime
import logging

# إعداد نظام تسجيل السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GestaxNotifier")

load_dotenv()

TOKEN = os.getenv("NOTIFIER_BOT_TOKEN")
EMAIL_CHANNEL_ID = int(os.getenv("CHANNEL_EMAIL_ID", 0))
INSTAGRAM_CHANNEL_ID = int(os.getenv("CHANNEL_INSTAGRAM_ID", 0))
FACEBOOK_CHANNEL_ID = int(os.getenv("CHANNEL_FACEBOOK_ID", 0))

# القنوات الجديدة المخصصة لإرسال المحاضر والإعلانات
MEETINGS_CHANNEL_ID = int(os.getenv("CHANNEL_MEETINGS_ID", 0))
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("CHANNEL_ANNOUNCEMENTS_ID", 0))

intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix="?", intents=intents)

RTL = "\u202b"
LRM = "\u200E"

def detect_rtl(text):
    if re.search(r'[\u0600-\u06FF]', text):
        return "\u200F"
    return ""

def truncate_text(text, max_length):
    """✂️ مقص ذكي لحماية البوت من الانهيار إذا تجاوز النص حدود ديسكورد المسموحة"""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text

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

# ========================================================
# 📝 واجهات محضر الاجتماعات
# ========================================================
class MeetingModal(ui.Modal, title='📝 كتابة محضر اجتماع جديد'):
    meeting_title = ui.TextInput(label='عنوان الاجتماع', style=discord.TextStyle.short, required=True, max_length=100)
    attendees = ui.TextInput(label='الأعضاء الحاضرون', style=discord.TextStyle.short, required=True, max_length=1000)
    decisions = ui.TextInput(label='القرارات والنقاط المطروحة', style=discord.TextStyle.paragraph, required=True, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"📝 محضر اجتماع: {self.meeting_title.value}",
            color=0x2E86C1, 
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="👥 الحضور", value=f"> {self.attendees.value}", inline=False)
        embed.add_field(name="📌 تفاصيل وقرارات الاجتماع", value=f"```\n{self.decisions.value}\n```", inline=False)
        embed.set_footer(text=f"كُتب بواسطة: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        # جلب القناة المخصصة للمحاضر وإرسال الرسالة إليها
        channel = await safely_get_channel(MEETINGS_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            # الرد على المستخدم برسالة مخفية لتأكيد الإرسال
            await interaction.response.send_message("✅ تم إرسال محضر الاجتماع إلى القناة المخصصة بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لم يتم العثور على القناة المخصصة لمحاضر الاجتماعات. يرجى التحقق من إعدادات ملف .env.", ephemeral=True)

class MeetingView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @ui.button(label="إنشاء محضر اجتماع 📝", style=discord.ButtonStyle.primary, custom_id="btn_create_meeting")
    async def create_meeting(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MeetingModal())

# ========================================================
# 📢 واجهات إعلانات الفريق
# ========================================================
class AnnouncementModal(ui.Modal):
    announcement_title = ui.TextInput(label='عنوان الإعلان', style=discord.TextStyle.short, required=True, max_length=100)
    details = ui.TextInput(label='تفاصيل الإعلان', style=discord.TextStyle.paragraph, required=True, max_length=3000)

    # استقبال مستوى الأهمية الذي اختاره المستخدم من القائمة المنسدلة
    def __init__(self, urgency_val: str):
        super().__init__(title=f'📢 نشر إعلان جديد ({urgency_val})')
        self.urgency_val = urgency_val

    async def on_submit(self, interaction: discord.Interaction):
        color = 0xF1C40F 
        is_urgent = "عاجل" in self.urgency_val or "حرج" in self.urgency_val
        
        if "عاجل" in self.urgency_val: color = 0xE67E22 
        elif "حرج" in self.urgency_val: color = 0xE74C3C 

        embed = discord.Embed(
            title=f"📢 إعلان إداري: {self.announcement_title.value}",
            description=f"{RTL}{self.details.value}",
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="⚠️ الأهمية", value=f"`{self.urgency_val}`", inline=False)
        embed.set_footer(text=f"إدارة الفريق | بواسطة: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        # جلب القناة المخصصة للإعلانات وإرسال الرسالة إليها
        channel = await safely_get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if channel:
            await channel.send(
                content="||@everyone||" if is_urgent else None, 
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=is_urgent)
            )
            # الرد على المستخدم برسالة مخفية لتأكيد الإرسال
            await interaction.response.send_message("✅ تم نشر الإعلان في القناة المخصصة بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لم يتم العثور على القناة المخصصة للإعلانات. يرجى التحقق من إعدادات ملف .env.", ephemeral=True)

class AnnouncementView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # استبدال الزر بقائمة منسدلة (خيارات إجبارية)
    @ui.select(
        placeholder="اختر مستوى أهمية الإعلان أولاً ⬇️",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="عادي", description="إعلان روتيني غير مستعجل", emoji="🟢"),
            discord.SelectOption(label="عاجل", description="إعلان هام يتطلب انتباه الجميع", emoji="🟠"),
            discord.SelectOption(label="حرج", description="إعلان طارئ وحرج جداً", emoji="🔴")
        ],
        custom_id="select_announcement_urgency"
    )
    async def select_urgency(self, interaction: discord.Interaction, select: ui.Select):
        selected_urgency = select.values[0]
        # بمجرد الاختيار، يتم فتح نافذة الإعلان وتمرير الأهمية إليها
        await interaction.response.send_modal(AnnouncementModal(urgency_val=selected_urgency))

# ========================================================
# 💻 أوامر السلاش (Slash Commands)
# ========================================================
@bot.tree.command(name="setup_meetings", description="نشر قائمة تدوين محاضر الاجتماعات (للمسؤولين فقط)")
@app_commands.default_permissions(administrator=True)
async def setup_meetings_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📝 نظام إدارة محاضر الاجتماعات",
        description="اضغط على الزر أدناه لتعبئة نموذج محضر اجتماع جديد.\nسيتم نشر المحضر تلقائياً في القناة المخصصة فور اعتماده.",
        color=0x2C3E50
    )
    await interaction.channel.send(embed=embed, view=MeetingView())
    await interaction.response.send_message("✅ تم نشر بوابة محاضر الاجتماعات بنجاح.", ephemeral=True)

@bot.tree.command(name="setup_announcements", description="نشر لوحة إعلانات الفريق (للمسؤولين فقط)")
@app_commands.default_permissions(administrator=True)
async def setup_announcements_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📢 لوحة إعلانات الفريق",
        description="اختر مستوى أهمية الإعلان من القائمة المنسدلة أدناه للبدء.\nسيتم نشر الإعلان في القناة المخصصة فور الانتهاء.",
        color=0xF39C12
    )
    await interaction.channel.send(embed=embed, view=AnnouncementView())
    await interaction.response.send_message("✅ تم نشر بوابة الإعلانات الإدارية بنجاح.", ephemeral=True)

# ========================================================
# 🌐 مستقبل الويب هوك (API Endpoint)
# ========================================================
async def handle_webhook(request):
    try:
        source = request.match_info.get('source', '').lower()
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)
        
        if not bot.is_ready():
            return web.json_response({"status": "retry", "message": "Bot is booting up..."}, status=503)

        if source == "email":
            channel = await safely_get_channel(EMAIL_CHANNEL_ID)
            if channel:
                # ✂️ الحماية من تجاوز حدود الـ Embed
                subject = truncate_text(data.get('subject', 'بدون عنوان').strip() or 'بدون عنوان', 256)
                sender = truncate_text(data.get('sender', 'غير معروف').strip() or 'غير معروف', 256)
                snippet = truncate_text(data.get('snippet', 'لا يوجد محتوى').strip() or 'لا يوجد محتوى', 1000)

                email_rtl = detect_rtl(snippet)
                subject_rtl = detect_rtl(subject)

                embed = discord.Embed(title="📬 إشعار بريد إلكتروني جديد", color=0xEA4335, timestamp=datetime.datetime.now(datetime.timezone.utc))
                embed.add_field(name="👤 المُرْسِل", value=f"`{sender}`", inline=False)
                embed.add_field(name="📌 الموضوع", value=f"**{subject_rtl}{subject}**", inline=False)
                embed.add_field(name="📝 نص الرسالة", value=f"> {email_rtl}{snippet}", inline=False)
                embed.set_footer(text=f"{LRM}Gestax Mail System{LRM}")
                await channel.send(embed=embed)
                return web.json_response({"status": "success"}, status=200)

        elif source == "instagram" or source == "facebook":
            channel_id = INSTAGRAM_CHANNEL_ID if source == "instagram" else FACEBOOK_CHANNEL_ID
            channel = await safely_get_channel(channel_id)
            if channel:
                # ✂️ الحماية من تجاوز الـ Description limit (4096)
                raw_text = data.get('caption' if source == 'instagram' else 'message', 'منشور جديد بدون نص').strip() or 'منشور جديد بدون نص'
                safe_text = truncate_text(raw_text, 3900) 
                
                post_url = data.get('url', '').strip()
                image_url = data.get('image_url', '').strip()

                embed = discord.Embed(
                    title="📸 منشور إنستغرام جديد" if source == "instagram" else "🔵 منشور فيسبوك جديد",
                    description=f"{RTL}{safe_text}" + (f"\n\n🔗 [عرض المنشور]({post_url})" if post_url else ""),
                    color=0xE1306C if source == "instagram" else 0x1877F2,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                if image_url and image_url.startswith("http"):
                    embed.set_image(url=image_url)
                embed.set_footer(text=f"{LRM}Gestax {source.capitalize()} Monitor{LRM}")
                await channel.send(embed=embed)
                return web.json_response({"status": "success"}, status=200)

        return web.json_response({"status": "ignored", "message": "Source unknown or channel missing"}, status=400)

    except Exception as e:
        logger.error(f"❌ خطأ حرج غير متوقع داخل الـ Webhook Handler: {e}", exc_info=True)
        return web.json_response({"status": "error", "message": "Internal Server Error"}, status=500)

async def start_web_server():
    app = web.Application()
    app.router.add_post('/webhook/{source}', handle_webhook)
    app.router.add_get('/', lambda r: web.Response(text="Gestax API Gateway is Operational! 🚀", status=200))
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 [API SERVER] يعمل بنجاح على المنفذ السحابي {port}")

async def setup_hook():
    bot.loop.create_task(start_web_server())
    bot.add_view(MeetingView())
    bot.add_view(AnnouncementView())

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    logger.info(f"🔥 تم تسجيل الدخول بنجاح! البوت أونلاين: {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"⚡ [Global Sync] تم مزامنة {len(synced)} من أوامر السلاش بنجاح!")
    except Exception as e:
        logger.error(f"❌ فشل مزامنة أوامر السلاش: {e}")

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ خطأ: لم يتم العثور على NOTIFIER_BOT_TOKEN في متغيرات البيئة!")
    else:
        bot.run(TOKEN)