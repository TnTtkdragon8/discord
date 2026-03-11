import discord
from discord.ext import commands
import logging
import asyncio
import os
import json
import random
from datetime import timedelta, datetime, timezone

logging.basicConfig(level=logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    intents=intents
)

# =========================
# إعدادات عامة
# =========================
WELCOME_CHANNEL_NAME = "الترحيب"
WELCOME_IMAGE_URL = "https://i.postimg.cc/4d6Yww05/lwjw.png"
AUTO_ROLE_NAME = "👥 𝕸𝖇 ❁ عـضـو"

# الرتب الوحيدة المسموح لها باستخدام أوامر البوت
ALLOWED_ADMIN_ROLES = [
    "باشا البلد",
    "𝕺ₙ 𝓣𝓱𝓮 𝓚𝓲𝓷𝓰",
    "𝕺ₙ مسؤول إداره"
]

# الرتب التي يسمح لها بكسر قيد الرومات الخاصة
BYPASS_ROOM_ROLES = [
    "باشا البلد",
    "𝕺ₙ 𝓣𝓱𝓮 𝓚𝓲𝓷𝓰",
    "𝕺ₙ مسؤول إداره"
]

CREDITS_CHANNEL_NAME = "ア・「🤖」أوامــر"
GAMES_CHANNEL_NAME = "モ・「🎉」الــفــعــالــيــات"

# الأمر السري الخاص بك فقط
OWNER_USERNAME_ONLY = "xjb5"
SECRET_CLEAR_PHRASE = "كش ملك @. 1973"

WARNINGS_FILE = "warnings.json"
BALANCES_FILE = "balances.json"
DAILY_FILE = "daily_claims.json"

# كلمات سيئة - زود عليها براحتك
BAD_WORDS = [
    "حمار",
    "كلب",
    "تافه",
    "غبي",
    "زباله",
    "زبالة",
    "قذر",
    "خول",
    "متناك",
    "كس",
    "شرموط",
]

warnings_data = {}
balances = {}
daily_claims = {}
unauthorized_attempts = {}

chairs_games = {}   # {channel_id: {"players": [ids], "started": False}}
xo_games = {}       # {channel_id: {...}}

# =========================
# تحميل / حفظ البيانات
# =========================
def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    global warnings_data, balances, daily_claims
    warnings_data = load_json(WARNINGS_FILE, {})
    balances = load_json(BALANCES_FILE, {})
    daily_claims = load_json(DAILY_FILE, {})

def save_warnings():
    save_json(WARNINGS_FILE, warnings_data)

def save_balances():
    save_json(BALANCES_FILE, balances)

def save_daily():
    save_json(DAILY_FILE, daily_claims)

# =========================
# مساعدات
# =========================
def has_any_role(member, role_names):
    return any(role.name in role_names for role in member.roles)

def is_admin_role(member):
    return has_any_role(member, ALLOWED_ADMIN_ROLES)

def bypass_room_check(member):
    return has_any_role(member, BYPASS_ROOM_ROLES)

def is_owner_username_from_author(author):
    return author.name == OWNER_USERNAME_ONLY

def get_balance(user_id: int) -> int:
    return int(balances.get(str(user_id), 0))

def set_balance(user_id: int, amount: int):
    balances[str(user_id)] = max(0, int(amount))
    save_balances()

def add_balance(user_id: int, amount: int):
    set_balance(user_id, get_balance(user_id) + amount)

def take_balance(user_id: int, amount: int) -> bool:
    current = get_balance(user_id)
    if current < amount:
        return False
    set_balance(user_id, current - amount)
    return True

def normalize_text(text: str) -> str:
    return text.lower().strip()

def contains_bad_word(text: str) -> bool:
    text = normalize_text(text)
    return any(word in text for word in BAD_WORDS)

def is_in_channel(ctx, channel_name: str) -> bool:
    return ctx.channel.name == channel_name

def can_manage_target(ctx, member: discord.Member):
    if member == bot.user:
        return False, "❌ لا يمكن تنفيذ الأمر على البوت."
    if member == ctx.author:
        return False, "❌ لا يمكن تنفيذ الأمر على نفسك."
    if member == ctx.guild.owner:
        return False, "❌ لا يمكن تنفيذ الأمر على مالك السيرفر."
    if ctx.author != ctx.guild.owner and ctx.author.top_role <= member.top_role:
        return False, "❌ لا يمكنك تنفيذ الأمر على عضو رتبته أعلى منك أو تساويك."
    if ctx.guild.me.top_role <= member.top_role:
        return False, "❌ رتبة البوت أقل من رتبة العضو المطلوب."
    return True, None

def format_xo_board(board):
    cells = []
    for i, cell in enumerate(board, start=1):
        cells.append(cell if cell != " " else str(i))
    return (
        f"`{cells[0]}` | `{cells[1]}` | `{cells[2]}`\n"
        f"`{cells[3]}` | `{cells[4]}` | `{cells[5]}`\n"
        f"`{cells[6]}` | `{cells[7]}` | `{cells[8]}`"
    )

def check_xo_winner(board, symbol):
    wins = [
        (0,1,2), (3,4,5), (6,7,8),
        (0,3,6), (1,4,7), (2,5,8),
        (0,4,8), (2,4,6)
    ]
    return any(board[a] == board[b] == board[c] == symbol for a, b, c in wins)

def admin_only():
    async def predicate(ctx):
        if not is_admin_role(ctx.author):
            raise commands.CheckFailure("NO_ADMIN_ROLE")
        return True
    return commands.check(predicate)

def credits_room_or_admin():
    async def predicate(ctx):
        if not is_admin_role(ctx.author):
            raise commands.CheckFailure("NO_ADMIN_ROLE")
        if bypass_room_check(ctx.author):
            return True
        if is_in_channel(ctx, CREDITS_CHANNEL_NAME):
            return True
        raise commands.CheckFailure("WRONG_CREDITS_ROOM")
    return commands.check(predicate)

def games_room_or_admin():
    async def predicate(ctx):
        if not is_admin_role(ctx.author):
            raise commands.CheckFailure("NO_ADMIN_ROLE")
        if bypass_room_check(ctx.author):
            return True
        if is_in_channel(ctx, GAMES_CHANNEL_NAME):
            return True
        raise commands.CheckFailure("WRONG_GAMES_ROOM")
    return commands.check(predicate)

# =========================
# أحداث
# =========================
@bot.event
async def on_ready():
    load_data()
    print(f"✅ البوت شغال كـ {bot.user}")

@bot.event
async def on_member_join(member):
    # إعطاء الرتبة التلقائية
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        try:
            await member.add_roles(role, reason="Auto role for new member")
        except discord.Forbidden:
            print("❌ البوت لا يملك صلاحية إعطاء الرتبة التلقائية.")
        except Exception as e:
            print(f"❌ خطأ أثناء إعطاء الرتبة: {e}")

    # رسالة الترحيب
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
            f"🤝 توجه إلى {middlemen}\n"
            f"🌍 Welcome to **{server_name}**!"
        ),
        color=discord.Color.dark_red()
    )

    embed.set_image(url=WELCOME_IMAGE_URL)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"{member.name} joined the server")

    await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    # فلتر الكلمات السيئة
    if contains_bad_word(content):
        try:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} ❌ ممنوع استخدام الألفاظ السيئة.",
                delete_after=4
            )
        except discord.Forbidden:
            pass
        return

    # ردود تلقائية
    if content == "السلام عليكم":
        await message.channel.send("وعليكم السلام ورحمة الله وبركاته")
    elif content == ".":
        await message.channel.send("شيلها يا حبيبي")

    # منشن البوت من إداري => يكتب everyone/here
    if bot.user in message.mentions and is_admin_role(message.author):
        try:
            await message.channel.send(
                "@everyone @here",
                allowed_mentions=discord.AllowedMentions(everyone=True)
            )
        except discord.Forbidden:
            pass

    # الأمر السري الخاص بك فقط - تنظيف الروم الحالي بالكامل
    if content == SECRET_CLEAR_PHRASE and is_owner_username_from_author(message.author):
        try:
            total_deleted = 0

            while True:
                deleted = await message.channel.purge(limit=100)
                if not deleted:
                    break
                total_deleted += len(deleted)
                if len(deleted) < 100:
                    break

            await message.channel.send(
                f"🧹 تم تنظيف الروم بالكامل.\nعدد الرسائل المحذوفة: {total_deleted}",
                delete_after=5
            )
        except discord.Forbidden:
            await message.channel.send("❌ مش عندي صلاحية أحذف الرسائل.")
        except Exception as e:
            await message.channel.send(f"❌ حصل خطأ: {e}")
        return

    await bot.process_commands(message)

# =========================
# أخطاء الأوامر
# =========================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        text = str(error)

        if text == "NO_ADMIN_ROLE":
            uid = ctx.author.id
            unauthorized_attempts[uid] = unauthorized_attempts.get(uid, 0) + 1

            if unauthorized_attempts[uid] >= 5:
                unauthorized_attempts[uid] = 0
                await ctx.send("مش بس يحبيبي صدعتني")
            return

        if text == "WRONG_CREDITS_ROOM":
            await ctx.send(f"❌ هذا الأمر يعمل فقط في روم: {CREDITS_CHANNEL_NAME}")
            return

        if text == "WRONG_GAMES_ROOM":
            await ctx.send(f"❌ هذا الأمر يعمل فقط في روم: {GAMES_CHANNEL_NAME}")
            return

        return

    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command and ctx.command.name == "ت":
            await ctx.send("❌ لازم تكتب السبب. مثال: `!ت @العضو سبام`")
        else:
            await ctx.send("❌ ناقص جزء في الأمر.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ فيه خطأ في كتابة الأمر أو المنشن.")
        return

    if isinstance(error, commands.CommandNotFound):
        return

    await ctx.send(f"❌ حصل خطأ: {error}")

# =========================
# أوامر الإدارة
# =========================
@bot.command(name="ت")
@admin_only()
async def warn(ctx, member: discord.Member, *, reason: str):
    ok, msg = can_manage_target(ctx, member)
    if not ok:
        await ctx.send(msg)
        return

    uid = str(member.id)
    warnings_data[uid] = warnings_data.get(uid, 0) + 1
    count = warnings_data[uid]
    save_warnings()

    try:
        await member.send(
            f"⚠️ لقد تلقيت تحذيراً في سيرفر **{ctx.guild.name}**.\n"
            f"📌 السبب: {reason}\n"
            f"🔢 عدد تحذيراتك الآن: {count}"
        )
    except Exception:
        pass

    msg = await ctx.send(
        f"🔴 تم إعطاء {member.mention} تحذير.\n"
        f"📌 السبب: {reason}\n"
        f"🔢 عدد التحذيرات: {count}"
    )
    await asyncio.sleep(4)
    await msg.delete()

@bot.command(name="تحذيرات")
@admin_only()
async def show_warnings(ctx, member: discord.Member):
    count = warnings_data.get(str(member.id), 0)
    msg = await ctx.send(f"{member.mention} لديه {count} تحذيرات ⚠️")
    await asyncio.sleep(4)
    await msg.delete()

@bot.command(name="مسح_تحذيرات")
@admin_only()
async def clear_warnings(ctx, member: discord.Member):
    warnings_data[str(member.id)] = 0
    save_warnings()
    await ctx.send(f"✅ تم تصفير تحذيرات {member.mention}")

@bot.command(name="ق")
@admin_only()
async def lock_channel(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    msg = await ctx.send("🔒 تم قفل الشات.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="ف")
@admin_only()
async def unlock_channel(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    msg = await ctx.send("🔓 تم فتح الشات.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="تايم")
@admin_only()
async def timeout_member(ctx, member: discord.Member, duration: str):
    ok, msg = can_manage_target(ctx, member)
    if not ok:
        await ctx.send(msg)
        return

    try:
        if duration.endswith("د"):
            minutes = int(duration[:-1])
            if minutes <= 0:
                await ctx.send("❌ اكتب عدد دقائق أكبر من 0.")
                return
            delta = timedelta(minutes=minutes)
        elif duration.endswith("س"):
            hours = int(duration[:-1])
            if hours <= 0:
                await ctx.send("❌ اكتب عدد ساعات أكبر من 0.")
                return
            delta = timedelta(hours=hours)
        else:
            await ctx.send("❌ استخدم مثلًا: `!تايم @user 10د` أو `!تايم @user 2س`")
            return
    except ValueError:
        await ctx.send("❌ اكتب رقم صحيح متبوع بـ `د` أو `س`.")
        return

    try:
        until = discord.utils.utcnow() + delta
        await member.edit(timed_out_until=until, reason=f"تم تايم بواسطة {ctx.author}")
        await ctx.send(f"✅ {member.mention} تم تايمه لمدة {duration}.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أعمل تايم للعضو.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="فك")
@admin_only()
async def untimeout_member(ctx, member: discord.Member):
    ok, msg = can_manage_target(ctx, member)
    if not ok:
        await ctx.send(msg)
        return

    try:
        await member.edit(timed_out_until=None, reason=f"تم فك التايم بواسطة {ctx.author}")
        await ctx.send(f"✅ تم فك التايم عن {member.mention}")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أفك التايم.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="انطر")
@admin_only()
async def kick_member(ctx, member: discord.Member):
    ok, msg = can_manage_target(ctx, member)
    if not ok:
        await ctx.send(msg)
        return

    try:
        await member.kick(reason=f"تم طرده بواسطة {ctx.author}")
        await ctx.send(f"👢 {member.mention} تم طرده من السيرفر.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أطرد العضو.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

@bot.command(name="تفو")
@admin_only()
async def ban_member(ctx, member: discord.Member):
    ok, msg = can_manage_target(ctx, member)
    if not ok:
        await ctx.send(msg)
        return

    try:
        await member.ban(reason=f"تم حظره بواسطة {ctx.author}")
        await ctx.send(f"🔨 {member.mention} تم حظره من السيرفر.")
    except discord.Forbidden:
        await ctx.send("❌ مش عندي صلاحية أحظر العضو.")
    except Exception as e:
        await ctx.send(f"❌ حصل خطأ: {e}")

# =========================
# نظام الرصيد الداخلي
# =========================
@bot.command(name="p")
@credits_room_or_admin()
async def p_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"💰 رصيد {target.mention}: **{get_balance(target.id)}** كريدت")

@bot.command(name="يومي")
@credits_room_or_admin()
async def daily(ctx):
    now = datetime.now(timezone.utc)
    uid = str(ctx.author.id)

    last_claim = daily_claims.get(uid)
    if last_claim:
        last_dt = datetime.fromisoformat(last_claim)
        if (now - last_dt).total_seconds() < 86400:
            remaining = int(86400 - (now - last_dt).total_seconds())
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await ctx.send(f"⏳ تقدر تستلم اليومي بعد {hours}س و {minutes}د")
            return

    amount = 250
    add_balance(ctx.author.id, amount)
    daily_claims[uid] = now.isoformat()
    save_daily()
    await ctx.send(f"🎁 أخذت **{amount}** كريدت. رصيدك الآن: **{get_balance(ctx.author.id)}**")

@bot.command(name="تحويل")
@credits_room_or_admin()
async def transfer(ctx, member: discord.Member, amount: int):
    if member.bot:
        await ctx.send("❌ لا يمكن التحويل إلى بوت.")
        return
    if member == ctx.author:
        await ctx.send("❌ لا يمكن التحويل لنفسك.")
        return
    if amount <= 0:
        await ctx.send("❌ اكتب مبلغ أكبر من 0.")
        return
    if not take_balance(ctx.author.id, amount):
        await ctx.send("❌ رصيدك غير كافٍ.")
        return

    add_balance(member.id, amount)
    await ctx.send(
        f"💸 تم تحويل **{amount}** كريدت إلى {member.mention}\n"
        f"رصيدك الآن: **{get_balance(ctx.author.id)}**"
    )

@bot.command(name="اعطاء")
@admin_only()
async def give_credits(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ اكتب مبلغ أكبر من 0.")
        return
    add_balance(member.id, amount)
    await ctx.send(f"✅ تم إعطاء {member.mention} **{amount}** كريدت.")

@bot.command(name="سحب")
@admin_only()
async def remove_credits(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ اكتب مبلغ أكبر من 0.")
        return
    set_balance(member.id, max(0, get_balance(member.id) - amount))
    await ctx.send(f"✅ تم سحب **{amount}** كريدت من {member.mention}")

# =========================
# الألعاب
# =========================

@bot.command(name="روليت")
@games_room_or_admin()
async def roulette(ctx, amount: int, choice: str):
    choice = choice.strip().lower()

    valid = {
        "احمر": "red",
        "أحمر": "red",
        "اسود": "black",
        "أسود": "black",
        "اخضر": "green",
        "أخضر": "green"
    }

    if choice not in valid:
        await ctx.send("❌ استخدم: `!روليت 100 احمر` أو `!روليت 100 اسود` أو `!روليت 100 اخضر`")
        return

    if amount <= 0:
        await ctx.send("❌ اكتب مبلغ أكبر من 0.")
        return

    if get_balance(ctx.author.id) < amount:
        await ctx.send("❌ رصيدك غير كافٍ.")
        return

    result_pool = ["red"] * 18 + ["black"] * 18 + ["green"] * 1
    result = random.choice(result_pool)

    take_balance(ctx.author.id, amount)

    if valid[choice] == result:
        if result == "green":
            win = amount * 14
        else:
            win = amount * 2
        add_balance(ctx.author.id, win)
        await ctx.send(
            f"🎰 النتيجة: **{result}**\n"
            f"✅ فزت بـ **{win}** كريدت\n"
            f"💰 رصيدك الآن: **{get_balance(ctx.author.id)}**"
        )
    else:
        await ctx.send(
            f"🎰 النتيجة: **{result}**\n"
            f"❌ خسرت **{amount}** كريدت\n"
            f"💰 رصيدك الآن: **{get_balance(ctx.author.id)}**"
        )

@bot.command(name="كراسي")
@games_room_or_admin()
async def chairs_create(ctx):
    cid = ctx.channel.id
    if cid in chairs_games:
        await ctx.send("❌ توجد لعبة كراسي شغالة بالفعل في هذا الروم.")
        return

    chairs_games[cid] = {
        "players": [ctx.author.id],
        "started": False
    }
    await ctx.send(
        f"🎵 بدأت لعبة كراسي!\n"
        f"المنشئ: {ctx.author.mention}\n"
        f"للإنضمام اكتب: `!دخول`\n"
        f"وللبدء اكتب: `!ابدأ_كراسي`"
    )

@bot.command(name="دخول")
@games_room_or_admin()
async def chairs_join(ctx):
    cid = ctx.channel.id
    if cid not in chairs_games:
        await ctx.send("❌ لا توجد لعبة كراسي هنا.")
        return

    game = chairs_games[cid]
    if game["started"]:
        await ctx.send("❌ اللعبة بدأت بالفعل.")
        return

    if ctx.author.id in game["players"]:
        await ctx.send("❌ أنت داخل اللعبة بالفعل.")
        return

    game["players"].append(ctx.author.id)
    await ctx.send(f"✅ {ctx.author.mention} انضم للعبة. العدد الآن: **{len(game['players'])}**")

@bot.command(name="ابدأ_كراسي")
@games_room_or_admin()
async def chairs_start(ctx):
    cid = ctx.channel.id
    if cid not in chairs_games:
        await ctx.send("❌ لا توجد لعبة كراسي هنا.")
        return

    game = chairs_games[cid]
    if len(game["players"]) < 2:
        await ctx.send("❌ لازم لاعبين على الأقل.")
        return

    game["started"] = True
    players = game["players"][:]

    await ctx.send("🎶 بدأت الموسيقى... استعدوا!")

    while len(players) > 1:
        await asyncio.sleep(2)
        out_id = random.choice(players)
        players.remove(out_id)
        member = ctx.guild.get_member(out_id)
        await ctx.send(f"🪑 خرج من الجولة: {member.mention if member else out_id}")

    winner = ctx.guild.get_member(players[0])
    reward = 300
    add_balance(players[0], reward)
    await ctx.send(f"🏆 الفائز في الكراسي: {winner.mention if winner else players[0]} وربح **{reward}** كريدت")
    del chairs_games[cid]

@bot.command(name="اكس")
@games_room_or_admin()
async def xo_start(ctx, member: discord.Member):
    cid = ctx.channel.id

    if member.bot:
        await ctx.send("❌ لا يمكنك اللعب ضد بوت.")
        return
    if member == ctx.author:
        await ctx.send("❌ لا يمكنك اللعب ضد نفسك.")
        return
    if cid in xo_games:
        await ctx.send("❌ توجد لعبة X O جارية بالفعل في هذا الروم.")
        return

    xo_games[cid] = {
        "players": [ctx.author.id, member.id],
        "turn": ctx.author.id,
        "board": [" "] * 9,
        "symbols": {
            ctx.author.id: "X",
            member.id: "O"
        }
    }

    await ctx.send(
        f"❎⭕ بدأت اللعبة بين {ctx.author.mention} و {member.mention}\n"
        f"الدور الآن على: {ctx.author.mention}\n\n"
        f"{format_xo_board(xo_games[cid]['board'])}\n\n"
        f"للعب: `!لعب 5`"
    )

@bot.command(name="لعب")
@games_room_or_admin()
async def xo_play(ctx, position: int):
    cid = ctx.channel.id

    if cid not in xo_games:
        await ctx.send("❌ لا توجد لعبة X O هنا.")
        return

    game = xo_games[cid]

    if ctx.author.id not in game["players"]:
        await ctx.send("❌ أنت لست لاعبًا في هذه الجولة.")
        return

    if game["turn"] != ctx.author.id:
        await ctx.send("❌ ليس دورك الآن.")
        return

    if position < 1 or position > 9:
        await ctx.send("❌ اختر رقمًا من 1 إلى 9.")
        return

    idx = position - 1
    if game["board"][idx] != " ":
        await ctx.send("❌ هذه الخانة مستخدمة بالفعل.")
        return

    symbol = game["symbols"][ctx.author.id]
    game["board"][idx] = symbol

    if check_xo_winner(game["board"], symbol):
        reward = 200
        add_balance(ctx.author.id, reward)
        await ctx.send(
            f"{format_xo_board(game['board'])}\n\n"
            f"🏆 الفائز: {ctx.author.mention}\n"
            f"💰 الجائزة: **{reward}** كريدت"
        )
        del xo_games[cid]
        return

    if " " not in game["board"]:
        await ctx.send(f"{format_xo_board(game['board'])}\n\n🤝 تعادل!")
        del xo_games[cid]
        return

    next_player = game["players"][0] if game["players"][1] == ctx.author.id else game["players"][1]
    game["turn"] = next_player
    next_member = ctx.guild.get_member(next_player)

    await ctx.send(
        f"{format_xo_board(game['board'])}\n\n"
        f"➡️ الدور الآن على: {next_member.mention if next_member else next_player}"
    )

@bot.command(name="الغاء_اكس")
@games_room_or_admin()
async def xo_cancel(ctx):
    cid = ctx.channel.id
    if cid not in xo_games:
        await ctx.send("❌ لا توجد لعبة X O هنا.")
        return
    del xo_games[cid]
    await ctx.send("✅ تم إلغاء لعبة X O")

# =========================
# تشغيل البوت
# =========================
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if token:
        print("✅ جاري تشغيل البوت")
        bot.run(token)
    else:
        print("❌ خطأ: لم يتم تعيين متغير TOKEN")
