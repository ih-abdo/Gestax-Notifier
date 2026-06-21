import os
import discord
from discord.ext import commands
from aiohttp import web
from dotenv import load_dotenv
import datetime

# تحميل المتغيرات البيئية
load_dotenv()

TOKEN = os.getenv("NOTIFIER_BOT_TOKEN")
EMAIL_CHANNEL_ID = int(os.getenv("CHANNEL_EMAIL_ID", 0))
INSTAGRAM_CHANNEL_ID = int(os.getenv("CHANNEL_INSTAGRAM_ID", 0))
FACEBOOK_CHANNEL_ID = int(os.getenv("CHANNEL_FACEBOOK_ID", 0))

# إعدادات ديسكورد
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="?", intents=intents)

RTL = "\u202b"
WIDTH_HACK = "\u2800" * 45  

# --------------------------------------------------------
# 🌐 محرك الويب (API) لاستقبال البيانات من Make.com
# --------------------------------------------------------
async def handle_webhook(request):
    try:
        source = request.match_info.get('source')
        data = await request.json()
        
        if not bot.is_ready():
            return web.Response(text="Bot is booting up...", status=503)

        if source == "email" and EMAIL_CHANNEL_ID:
            channel = bot.get_channel(EMAIL_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title=f"📬 إيميل جديد | {data.get('subject', 'بدون عنوان')}",
                    description=f"**{RTL}👤 من:** {data.get('sender', 'غير معروف')}\n\n**{RTL}📝 المحتوى:**\n{RTL}{data.get('snippet', '')}",
                    color=0xEA4335,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_footer(text=f"Gestax Mail System{WIDTH_HACK}")
                await channel.send(embed=embed)
                
        elif source == "instagram" and INSTAGRAM_CHANNEL_ID:
            channel = bot.get_channel(INSTAGRAM_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="📸 منشور إنستغرام جديد",
                    description=f"{RTL}{data.get('caption', '')}\n\n🔗 [عرض المنشور]({data.get('url', '')})",
                    color=0xE1306C,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                if data.get("image_url"): embed.set_image(url=data.get("image_url"))
                embed.set_footer(text=f"Gestax Instagram Monitor{WIDTH_HACK}")
                await channel.send(embed=embed)
                
        elif source == "facebook" and FACEBOOK_CHANNEL_ID:
            channel = bot.get_channel(FACEBOOK_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="🔵 منشور فيسبوك جديد",
                    description=f"{RTL}{data.get('message', '')}\n\n🔗 [عرض المنشور]({data.get('url', '')})",
                    color=0x1877F2,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                if data.get("image_url"): embed.set_image(url=data.get("image_url"))
                embed.set_footer(text=f"Gestax Facebook Monitor{WIDTH_HACK}")
                await channel.send(embed=embed)
        else:
            return web.Response(text="Source unknown or channel not set.", status=400)
            
        return web.Response(text="Success", status=200)
        
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return web.Response(text="Internal Error", status=500)

async def start_web_server():
    app = web.Application()
    app.router.add_post('/webhook/{source}', handle_webhook)
    app.router.add_get('/', lambda r: web.Response(text="Gestax API is Alive! 🚀"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 [API] يعمل على المنفذ {port}")

async def setup_hook():
    bot.loop.create_task(start_web_server())

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f"🔥 بوت الإشعارات أونلاين: {bot.user}")

bot.run(TOKEN)