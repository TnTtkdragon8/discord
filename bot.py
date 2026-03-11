import discord
from discord.ext import commands
import logging
import asyncio
import os
import random
from datetime import timedelta

logging.basicConfig(level=logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="", intents=intents)

# ------------------- التخزين المؤقت -------------------
warnings = {}          # التحذيرات
balances = {}          # الأرصدة (الكريديت)
# ------------------------------------------------------

# ------------------- إعدادات الترحيب -------------------
WELCOME_CHANNEL_NAME = "الترحيب"
WELCOME_IMAGE_URL = "https://i.postimg.cc/4d6Yww05/lwjw.png"
# ------------------------------------------------------

# ------------------- الرتب المسموح لها -------------------
# هنا تقدر تضيف رتب بعدين – فقط غير القائمة دي
ALLOWED_ROLES = [
    "باشا البلد",
    "𝕺ₙ 𝓣𝓱𝓮 𝓚𝓲𝓷𝓰",
    "𝕺ₙ مسؤول إداره"
]

# رتبة العضو الجديد
MEMBER_ROLE_NAME = "👥 𝕸𝖇 ❁ عـضـو"

# ------------------------------------------------------
# قائمة الكلمات الممنوعة (الشتائم) – تقدر تعدلها براحتك
BAD_WORDS = ["كسم", "شرموط", "عرص", "خول", "متناك", "ابن الكلب", "ياكلخ", "منيوك"]  # أضف اللي تعرفه
# ------------------------------------------------------

# ------------------- دوال التحقق من الصلاحية -------------------
def has_allowed_role(ctx):
    """ترجع True لو المستخدم عنده رتبة من ALLOWED_ROLES"""
    return any(role.name in ALLOWED_ROLES for role in ctx.author.roles)

def is_basha(ctx):
    """للأوامر الخاصة جداً (مثل أمر و)"""
    return any(role.name == "باشا البلد" for role in ctx.author.roles)

def is_owner(ctx):
    """لأمر و – مخصص ليك وحدك (غير كدة مش هيشتغل)"""
    # استبدل الرقم ده برقم حسابك (خذ ID حسابك من Discord)
    return ctx.author.id == 123456789012345678  # ⚠️ غير الرقم ده لـ ID حسابك
# ----------------------------------------------------------------

# ------------------- حدث تشغيل البوت -------------------
@bot.event
async def on_ready():
    print(f"البوت شغال كـ {bot.user}")

# ------------------- حدث دخول عضو جديد (رتبة تلقائية) -------------------
@bot.event
async def on_member_join(member):
    # إعطاء رتبة العضو الجديد
    role = discord.utils.get(member.guild.roles, name=MEMBER_ROLE_NAME)
    if role:
        try:
            await member.add_roles(role)
            print(f"أعطى {member.name} رتبة {MEMBER_ROLE_NAME}")
        except:
            print("مقدرتش أعطي الرتبة (تأكد إن البوت أعلى من الرتبة)")
    
    # رسالة الترحيب (زي ما كانت)
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if not channel:
        print("❌ قناة الترحيب مش موجودة")
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

    embed.set_image(url=WELCOME_IMAGE_URL)
    avatar = member.avatar.url if member.avatar else member.default_avatar.url
    embed.set_thumbnail(url=avatar)
    embed.set_footer(text=f"{member.name} joined the server")

    await channel.send(embed=embed)

# ------------------- ردود تلقائية (السلام عليكم، النقطة) -------------------
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # منع الشتائم
    for word in BAD_WORDS:
        if word in message.content:
            await message.delete()
            await message.channel.send(f"❌ ممنوع استعمال كلمات نابية يا {message.author.mention}", delete_after=5)
            return  # يخرج عشان ما يعالجش الأوامر

    # ردود تلقائية
    if message.content.strip() == "السلام عليكم":
        await message.channel.send("وعليكم السلام ورحمة الله وبركاته")
    elif message.content.strip() == ".":
        await message.channel.send("شيلها يا حبيبي")

    # مهم عشان الأوامر تشتغل
    await bot.process_commands(message)

# ------------------- الأوامر -------------------

# 1️⃣ أمر فك التايم
@bot.command(name="فك")
async def untimeout(ctx, member: discord.Member):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    try:
        await member.timeout(None, reason=f"تم فك التايم بواسطة {ctx.author}")
        await ctx.send(f"✅ تم فك التايم عن {member.mention}")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أعدل التايم.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

# 2️⃣ أمر منشن everyone/here (للمشرفين)
@bot.command(name="منشن")
async def mention_all(ctx, target: str):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    if target.lower() == "everyone":
        await ctx.send("@everyone")
    elif target.lower() == "here":
        await ctx.send("@here")
    else:
        await ctx.send("استخدم `منشن everyone` أو `منشن here`")

# 3️⃣ أوامر الاقتصاد (كريديت)
# قناة الأوامر المسموح للأعضاء العاديين
ECONOMY_CHANNEL = "ア・「🤖」أوامــر"

@bot.command(name="p")  # معرفة الرصيد
async def balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    # لو العضو مش إداري ومش في القناة المخصصة، ارفض
    if not has_allowed_role(ctx) and ctx.channel.name != ECONOMY_CHANNEL:
        return
    bal = balances.get(member.id, 0)
    await ctx.send(f"💰 رصيد {member.mention}: **{bal}** كريديت")

@bot.command(name="تحويل")
async def transfer(ctx, to_member: discord.Member, amount: int):
    if not has_allowed_role(ctx) and ctx.channel.name != ECONOMY_CHANNEL:
        return
    if amount <= 0:
        await ctx.send("❌ المبلغ يجب أن يكون أكبر من 0")
        return
    sender_id = ctx.author.id
    balances[sender_id] = balances.get(sender_id, 0)
    if balances[sender_id] < amount:
        await ctx.send("❌ رصيدك غير كافٍ")
        return
    balances[sender_id] -= amount
    balances[to_member.id] = balances.get(to_member.id, 0) + amount
    await ctx.send(f"✅ تم تحويل {amount} كريديت إلى {to_member.mention}")

# 4️⃣ الألعاب (في قناة مخصصة)
GAMES_CHANNEL = "モ・「🎉」الــفــعــالــيــات"

# لعبة روليت
@bot.command(name="روليت")
async def roulette(ctx, bet: int):
    if not has_allowed_role(ctx) and ctx.channel.name != GAMES_CHANNEL:
        return
    if bet <= 0:
        await ctx.send("❌ راهن بمبلغ أكبر من 0")
        return
    balances[ctx.author.id] = balances.get(ctx.author.id, 0)
    if balances[ctx.author.id] < bet:
        await ctx.send("❌ رصيدك غير كافٍ")
        return
    result = random.choice(["ربح", "خسارة"])
    if result == "ربح":
        win = bet * 2
        balances[ctx.author.id] += win
        await ctx.send(f"🎉 ربحت {win} كريديت!")
    else:
        balances[ctx.author.id] -= bet
        await ctx.send(f"💔 خسرت {bet} كريديت")

# لعبة إكس أو (بسيطة) – ممكن نطورها بعدين
@bot.command(name="اكس او")
async def tictactoe(ctx, opponent: discord.Member):
    if not has_allowed_role(ctx) and ctx.channel.name != GAMES_CHANNEL:
        return
    await ctx.send("⚙️ لعبة إكس أو تحتاج وقت للتطوير. هتضاف قريباً إن شاء الله.")

# 5️⃣ أمر و – خاص ليك وحدك
@bot.command(name="و")
async def owner_secret(ctx):
    if not is_owner(ctx):
        await ctx.send("❌ هذا الأمر مخصص للمالك فقط.")
        return
    await ctx.send("🤫 أنت المالك، أهلاً بك.")

# 6️⃣ أمر تحذير مع سبب (ت @شخص سبب)
@bot.command(name="ت")
async def warn(ctx, member: discord.Member, *, reason="بدون سبب"):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    if member == bot.user:
        await ctx.send("لا يمكن تحذير البوت!")
        return

    warnings[member.id] = warnings.get(member.id, 0) + 1
    count = warnings[member.id]

    try:
        await member.send(f"⚠️ لقد تلقيت تحذيراً في سيرفر **{ctx.guild.name}**!\nالسبب: {reason}\nعدد تحذيراتك الآن: {count}")
    except:
        pass

    await ctx.send(f"🔴 تم إعطاؤك تحذير {member.mention}\nالسبب: {reason}\nعدد التحذيرات: {count}")

# باقي الأوامر القديمة (تحذيرات، حذف، ق، ف، تايم، انطر، تفو) موجودة زي ما هي
# هنسيبها عشان متبوظش حاجة، لكن هضيف عليها شرط الصلاحية

@bot.command(name="تحذيرات")
async def show_warnings(ctx, member: discord.Member):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    count = warnings.get(member.id, 0)
    await ctx.send(f"{member.mention} لديه {count} تحذيرات ⚠️")

@bot.command(name="حذف")
async def clear(ctx, amount: int):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 تم مسح {amount} رسالة", delete_after=3)

@bot.command(name="ق")
async def lock_channel(ctx):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 تم قفل الشات.", delete_after=3)

@bot.command(name="ف")
async def unlock_channel(ctx):
    if not has_allowed_role(ctx):
        await ctx.send("❌ مش عندك إذن تستخدم هذا الأمر.")
        return
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 تم فتح الشات.", delete_after=3)

@bot.command(name="تايم")
async def timeout(ctx, member: discord.Member, duration: str, *, reason="بدون سبب"):
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
        await ctx.send("❌ صيغة خاطئة. اكتب رقم صحيح.")
        return

    try:
        await member.timeout(delta, reason=f"تم تايم بواسطة {ctx.author} - سبب: {reason}")
        await ctx.send(f"✅ {member.mention} تم تايـمه لمدة {duration}.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أعمل تايم.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="انطر")
async def kick(ctx, member: discord.Member, *, reason="بدون سبب"):
    if not is_basha(ctx):
        await ctx.send("❌ هذا الأمر مخصص لـ باشا البلد فقط.")
        return
    try:
        await member.kick(reason=f"تم طرده بواسطة {ctx.author} - سبب: {reason}")
        await ctx.send(f"👢 {member.mention} تم طرده من السيرفر.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أطرد.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="تفو")
async def ban(ctx, member: discord.Member, *, reason="بدون سبب"):
    if not is_basha(ctx):
        await ctx.send("❌ هذا الأمر مخصص لـ باشا البلد فقط.")
        return
    try:
        await member.ban(reason=f"تم حظره بواسطة {ctx.author} - سبب: {reason}")
        await ctx.send(f"🔨 {member.mention} تم حظره من السيرفر.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أحظر.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

# ------------------- تشغيل البوت -------------------
if __name__ == "__main__":
    token = os.getenv('TOKEN')
    if token:
        print("✅ جاري تشغيل البوت")
        bot.run(token)
    else:
        print("❌ خطأ: لم يتم تعيين متغير TOKEN")