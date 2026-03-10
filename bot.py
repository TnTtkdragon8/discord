import discord
from discord.ext import commands
import logging
import asyncio
import os
from datetime import timedelta

logging.basicConfig(level=logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="", intents=intents)

warnings = {}  # تخزين التحذيرات

# ------------------- إعدادات الترحيب -------------------
WELCOME_CHANNEL_NAME = "الترحيب"          # اسم قناة الترحيب
WELCOME_IMAGE_URL = "https://i.postimg.cc/4d6Yww05/lwjw.png"  # رابط الصورة الكبيرة

# الرتب المسموح لها باستخدام أوامر الإدارة
ALLOWED_ROLES = ["باشا البلد", "𝕺ₙ 𝓣𝓱𝓮 𝓚𝓲𝓷𝓰", "𝕺ₙ مسؤول إداره"]

def has_allowed_role(ctx):
    return any(role.name in ALLOWED_ROLES for role in ctx.author.roles)

def is_basha(ctx):
    return any(role.name == "باشا البلد" for role in ctx.author.roles)

@bot.event
async def on_ready():
    print(f"البوت شغال كـ {bot.user}")

# ------------------- ردود تلقائية -------------------
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.strip() == "السلام عليكم":
        await message.channel.send("وعليكم السلام ورحمة الله وبركاته")
    elif message.content.strip() == ".":
        await message.channel.send("شيلها يا حبيبي")

    await bot.process_commands(message)

# ------------------- حدث الترحيب -------------------
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if not channel:
        print("❌ قناة الترحيب غير موجودة")
        return

    server_name = member.guild.name
    member_count = member.guild.member_count

    rules_channel = discord.utils.get(member.guild.text_channels, name="قوانين")
    middlemen_channel = discord.utils.get(member.guild.text_channels, name="روم-الوسطاء")

    rules = rules_channel.mention if rules_channel else "#قوانين"
    middlemen = middlemen_channel.mention if middlemen_channel else "#روم-الوسطاء"

    embed = discord.Embed(
        title=f"🎉 مرحباً بك في {server_name}",
        description=(
            f"👋 أهلاً بك {member.mention}\n"
            f"🔢 أنت العضو رقم **{member_count}**\n\n"
            f"📜 اقرأ {rules}\n"
            f"🌍 Welcome to **{server_name}**!"
        ),
        color=discord.Color.dark_red()
    )

    embed.set_image(url=WELCOME_IMAGE_URL)                     # الصورة الكبيرة
    avatar = member.avatar.url if member.avatar else member.default_avatar.url
    embed.set_thumbnail(url=avatar)                            # صورة العضو
    embed.set_footer(text=f"{member.name} joined the server")

    await channel.send(embed=embed)

# ------------------- أوامر التحذير والإدارة -------------------
@bot.command(name="ت")
async def warn(ctx, member: discord.Member):
    if member == bot.user:
        msg = await ctx.send("لا يمكن تحذير البوت!")
        await asyncio.sleep(3)
        await msg.delete()
        return

    warnings[member.id] = warnings.get(member.id, 0) + 1
    count = warnings[member.id]

    try:
        await member.send(f"⚠️ لقد تلقيت تحذيراً في سيرفر **{ctx.guild.name}**!\nعدد تحذيراتك الآن: {count}")
    except:
        pass

    msg = await ctx.send(f"🔴 تم إعطاؤك تحذير {member.mention}\nعدد التحذيرات: {count}")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="تحذيرات")
async def show_warnings(ctx, member: discord.Member):
    count = warnings.get(member.id, 0)
    msg = await ctx.send(f"{member.mention} لديه {count} تحذيرات ⚠️")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="حذف")
async def clear(ctx, amount: int):
    if not ctx.author.guild_permissions.manage_messages:
        msg = await ctx.send("❌ مش عندك صلاحية لإدارة الرسائل.")
        await asyncio.sleep(3)
        await msg.delete()
        return

    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم مسح {amount} رسالة", delete_after=3)

@bot.command(name="ق")
async def lock_channel(ctx):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return

    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    msg = await ctx.send("🔒 تم قفل الشات.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="ف")
async def unlock_channel(ctx):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return

    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    msg = await ctx.send("🔓 تم فتح الشات.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="تايم")
async def timeout(ctx, member: discord.Member, duration: str):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return

    try:
        if duration.endswith("د"):
            minutes = int(duration[:-1])
            delta = timedelta(minutes=minutes)
        elif duration.endswith("س"):
            hours = int(duration[:-1])
            delta = timedelta(hours=hours)
        else:
            await ctx.send("❌ صيغة خاطئة. استخدم مثلاً: `10د` للدقائق أو `2س` للساعات")
            return
    except ValueError:
        await ctx.send("❌ صيغة خاطئة. اكتب رقم صحيح متبوع بـ 'د' أو 'س'.")
        return

    try:
        await member.timeout(delta, reason=f"تم تايم بواسطة {ctx.author}")
        msg = await ctx.send(f"✅ {member.mention} تم تايـمه لمدة {duration}.")
        await asyncio.sleep(3)
        await msg.delete()
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أعمل تايم للعضو.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="انطر")
async def kick(ctx, member: discord.Member):
    if not is_basha(ctx):
        await ctx.send("❌ فقط باشا البلد يقدر يستخدم هذا الأمر.")
        return

    try:
        await member.kick(reason=f"تم طرده بواسطة {ctx.author}")
        await ctx.send(f"👢 {member.mention} تم طرده من السيرفر.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أطرد العضو.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="تفو")
async def ban(ctx, member: discord.Member):
    if not is_basha(ctx):
        await ctx.send("❌ فقط باشا البلد يقدر يستخدم هذا الأمر.")
        return

    try:
        await member.ban(reason=f"تم حظره بواسطة {ctx.author}")
        await ctx.send(f"🔨 {member.mention} تم حظره من السيرفر.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أحظر العضو.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

# ------------------- تشغيل البوت -------------------
# ------------------- تشغيل البوت -------------------
if __name__ == "__main__":
    token = os.environ.get('TOKEN')

    if not token:
        print("❌ خطأ: لم يتم تعيين متغير TOKEN في إعدادات Railway")
    else:
        print("✅ جاري تشغيل البوت...")
        bot.run(token)
