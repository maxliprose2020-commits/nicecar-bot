import os
import io
import base64
import json
import logging
from datetime import date
from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
NOTIFY_TOKEN = os.environ.get("NOTIFY_TOKEN")
OWNER_CHAT_ID = int(os.environ.get("OWNER_CHAT_ID", "862676483"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "862676483"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "nicecar_tuning_bot")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

from telegram import Bot as TelegramBot
_notify_bot = TelegramBot(token=NOTIFY_TOKEN) if NOTIFY_TOKEN else None

COUNTERS_FILE = "counters.json"
USERS_FILE = "users.json"
REFERRALS_FILE = "referrals.json"
PURCHASES_FILE = "purchases.json"
MAX_GENERATIONS = 5

STARS_PACKAGES = [
    {"stars": 50,  "generations": 20, "payload": "buy_20", "label": "20 генераций — 50 ⭐"},
    {"stars": 100, "generations": 50, "payload": "buy_50", "label": "50 генераций — 100 ⭐"},
]

# ── Варианты на русском ────────────────────────────────────────────────────────

BODY_OPTIONS = {
    "original":  "Без смены цвета",
    "black":     "Чёрный",
    "white":     "Белый",
    "grey":      "Серый",
    "silver":    "Серебристый",
    "blue":      "Синий",
    "navy":      "Тёмно-синий",
    "red":       "Красный",
    "burgundy":  "Бордовый",
    "green":     "Зелёный",
    "orange":    "Оранжевый",
    "yellow":    "Жёлтый",
    "purple":    "Фиолетовый",
    "beige":     "Бежевый",
    "brown":     "Коричневый",
}

FINISH_OPTIONS = {
    "matte":       "Матт",
    "gloss":       "Глянец",
    "satin":       "Сатин",
    "carbon":      "Карбон",
    "chrome":      "Хром",
    "camouflage":  "Камуфляж",
    "psychedelic": "Психоделика",
}

WHEELS_OPTIONS = {
    "original":     "Оставить как есть",
    "black_matte":  "Чёрные матт",
    "black_gloss":  "Чёрные глянец",
    "white":        "Белые",
    "gold":         "Золотые",
    "grey":         "Серые",
}

WHEELS_SIZE_OPTIONS = {
    "original": "Стандартный",
    "r19":      "R19",
    "r20":      "R20",
    "r21":      "R21",
    "r22":      "R22",
}

TINT_OPTIONS = {
    "none":   "Без тонировки",
    "light":  "Лёгкая",
    "medium": "Средняя",
    "dark":   "Тёмная",
}

WINDSHIELD_OPTIONS = {
    "none":      "Без плёнки",
    "tint_50":   "Тонировка 50%",
    "chameleon": "Хамелеон (сине-фиолетовый)",
    "sea_wave":  "Морская волна (голубой оттенок)",
}

SIDEGLASS_OPTIONS = {
    "none":      "Без плёнки",
    "tint_50":   "Тонировка 50%",
    "chameleon": "Хамелеон (сине-фиолетовый)",
    "sea_wave":  "Морская волна (голубой оттенок)",
}

OPTICS_OPTIONS = {
    "none":    "Без тонировки",
    "tint_35": "Затемнение 35%",
    "tint_50": "Затемнение 50%",
}

ANTICHROME_OPTIONS = {
    "none":        "Без антихрома",
    "gloss_black": "Чёрный глянец",
    "matte_black": "Чёрный матт",
}

MIRRORS_OPTIONS = {
    "original":    "Оригинал",
    "matte_black": "Чёрный матт",
    "gloss_black": "Чёрный глянец",
}

HANDLES_OPTIONS = {
    "original":    "Оригинал",
    "matte_black": "Чёрный матт",
    "gloss_black": "Чёрный глянец",
}

ROOF_OPTIONS = {
    "original":    "Оригинал",
    "gloss_black": "Чёрная крыша (эффект панорамы)",
}

DECOR_OPTIONS = {
    "none":          "Без декора",
    "sport_stripes": "Спортивные полосы",
    "side_stripes":  "Боковые полосы",
    "ornament":      "Орнамент/узор",
}

BODYKIT_OPTIONS = {
    "none":        "Без обвеса",
    "sport":       "Спортивный обвес",
    "aggressive":  "Агрессивный обвес",
    "spoiler":     "Спойлер сзади",
    "full":        "Полный обвес + спойлер",
}

ANGLE_OPTIONS = {
    "original":    "Как на фото",
    "front":       "Спереди",
    "front_side":  "Спереди сбоку (3/4)",
    "side":        "Сбоку",
    "rear_side":   "Сзади сбоку (3/4)",
    "rear":        "Сзади",
    "top":         "Сверху",
}

BACKGROUND_OPTIONS = {
    "night_city":  "Ночной город",
    "mountains":   "Горы",
    "track":       "Трасса",
    "underground": "Подземный паркинг",
    "dubai":       "Дубай",
    "minsk":       "Минск",
}

# ── Переводы для промпта ───────────────────────────────────────────────────────

BODY_EN = {
    "original":  "original color",
    "black":     "black",
    "white":     "white",
    "grey":      "grey",
    "silver":    "silver",
    "blue":      "blue",
    "navy":      "dark navy blue",
    "red":       "red",
    "burgundy":  "deep burgundy",
    "green":     "green",
    "orange":    "orange",
    "yellow":    "yellow",
    "purple":    "purple",
    "beige":     "beige",
    "brown":     "brown",
}

FINISH_EN = {
    "matte":       "matte vinyl wrap",
    "gloss":       "gloss vinyl wrap",
    "satin":       "satin vinyl wrap",
    "carbon":      "carbon fiber vinyl wrap",
    "chrome":      "chrome vinyl wrap",
    "camouflage":  "camouflage vinyl wrap",
    "psychedelic": "psychedelic multicolor holographic vinyl wrap with vivid neon patterns",
}

WHEELS_EN = {
    "original":     "original stock wheels",
    "black_matte":  "matte black wheels",
    "black_gloss":  "glossy black wheels",
    "white":        "white wheels",
    "gold":         "gold wheels",
    "grey":         "grey wheels",
}

WHEELS_SIZE_EN = {
    "original": "",
    "r19":      "19-inch",
    "r20":      "20-inch",
    "r21":      "21-inch",
    "r22":      "22-inch",
}

TINT_EN = {
    "none":   "clear rear windows with no tint",
    "light":  "lightly tinted rear windows",
    "medium": "medium tinted rear windows",
    "dark":   "heavily tinted rear windows",
}

WINDSHIELD_EN = {
    "none":      "clear windshield with no film",
    "tint_50":   "windshield with 50% tint film",
    "chameleon": "windshield with very light blue-purple chameleon iridescent color-shifting film, 83% light transmission, barely tinted",
    "sea_wave":  "windshield with sea wave 70% light transmission light blue tinted film",
}

SIDEGLASS_EN = {
    "none":      "clear front side windows with no film",
    "tint_50":   "front side windows with 50% tint film",
    "chameleon": "front side windows with very light blue-purple chameleon iridescent color-shifting film, 83% light transmission, barely tinted",
    "sea_wave":  "front side windows with sea wave 70% light transmission light blue tinted film",
}

OPTICS_EN = {
    "none":    "",
    "tint_35": "headlights and taillights tinted with 35% dark film",
    "tint_50": "headlights and taillights tinted with 50% dark film",
}

ANTICHROME_EN = {
    "none":        "all chrome trim kept as original shiny chrome finish",
    "gloss_black": "all chrome trim on the body replaced with gloss black vinyl chrome delete",
    "matte_black": "all chrome trim on the body replaced with matte black vinyl chrome delete",
}

MIRRORS_EN = {
    "original":    "",
    "matte_black": "side mirrors wrapped in matte black vinyl",
    "gloss_black": "side mirrors wrapped in gloss black vinyl",
}

HANDLES_EN = {
    "original":    "",
    "matte_black": "door handles wrapped in matte black vinyl",
    "gloss_black": "door handles wrapped in gloss black vinyl",
}

ROOF_EN = {
    "original":    "",
    "gloss_black": "roof wrapped in gloss black vinyl giving a panoramic sunroof appearance",
}

BODYKIT_EN = {
    "none":        "",
    "sport":       "sport body kit with side skirts and front lip spoiler",
    "aggressive":  "aggressive wide-body kit with flared fenders and front splitter",
    "spoiler":     "rear wing spoiler",
    "full":        "full sport body kit with front splitter, side skirts, diffuser and rear wing spoiler",
}

DECOR_EN = {
    "none":          "",
    "sport_stripes": "bold racing stripes on hood and roof",
    "side_stripes":  "decorative side body stripes",
    "ornament":      "decorative ornamental pattern on the body panels",
}

ANGLE_EN = {
    "original":    "same camera angle as in the original photo",
    "front":       "front view",
    "front_side":  "front three-quarter view",
    "side":        "side profile view",
    "rear_side":   "rear three-quarter view",
    "rear":        "rear view",
    "top":         "top-down aerial view",
}

BACKGROUND_EN = {
    "night_city":  "night city with neon lights and bokeh",
    "mountains":   "scenic mountain landscape",
    "track":       "racing track",
    "underground": "underground parking with dramatic lighting",
    "dubai":       "Dubai skyline at sunset",
    "minsk":       "Minsk city center Belarus",
}

DEFAULT_SELECTIONS = {
    "body":         "black",
    "finish":       "matte",
    "wheels":       "original",
    "wheels_size":  "original",
    "tint":         "none",
    "windshield":   "none",
    "sideglass":    "none",
    "optics":       "none",
    "antichrome":   "none",
    "mirrors":      "original",
    "handles":      "original",
    "roof":         "original",
    "bodykit":      "none",
    "decor":        "none",
    "angle":        "original",
    "background":   "night_city",
}

# user_id → {"photo_id": str | None, "selections": dict}
user_states: dict[int, dict] = {}


# ── Водяной знак ──────────────────────────────────────────────────────────────

def add_watermark(image_bytes: io.BytesIO) -> io.BytesIO:
    img = Image.open(image_bytes).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    text = "Найскар Центр"
    font_size = max(28, img.width // 22)
    font = None
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = 16
    x = img.width - tw - pad
    y = img.height - th - pad

    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 120))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 200))

    combined = Image.alpha_composite(img, overlay)
    out = io.BytesIO()
    combined.convert("RGB").save(out, format="JPEG", quality=95)
    out.seek(0)
    return out


# ── Хранилище данных ──────────────────────────────────────────────────────────

def _load(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


# ── Пользователи ──────────────────────────────────────────────────────────────

def register_user(user_id: int, user) -> bool:
    users = _load(USERS_FILE)
    key = str(user_id)
    if key in users:
        return False
    users[key] = {
        "name": user.full_name,
        "username": user.username or "",
        "joined": str(date.today()),
    }
    _save(USERS_FILE, users)
    return True

def get_user_name(user_id: int) -> str:
    users = _load(USERS_FILE)
    u = users.get(str(user_id), {})
    name = u.get("name", str(user_id))
    username = u.get("username", "")
    return f"{name} @{username}" if username else name

def count_users() -> tuple:
    users = _load(USERS_FILE)
    today = str(date.today())
    return len(users), sum(1 for u in users.values() if u.get("joined") == today)


# ── Счётчики генераций ────────────────────────────────────────────────────────

def _ensure(counters: dict, key: str) -> None:
    today = str(date.today())
    if key not in counters:
        counters[key] = {"date": today, "daily_count": 0, "bonus": 0, "total_ever": 0}
    elif counters[key].get("date") != today:
        counters[key]["date"] = today
        counters[key]["daily_count"] = 0
    for f in ("bonus", "total_ever"):
        if f not in counters[key]:
            counters[key][f] = 0

def get_generation_info(user_id: int) -> dict:
    counters = _load(COUNTERS_FILE)
    key = str(user_id)
    _ensure(counters, key)
    daily = counters[key]["daily_count"]
    bonus = counters[key]["bonus"]
    free_left = max(0, MAX_GENERATIONS - daily)
    return {"daily_used": daily, "bonus": bonus, "free_left": free_left, "total_left": free_left + bonus}

def use_generation(user_id: int) -> None:
    counters = _load(COUNTERS_FILE)
    key = str(user_id)
    _ensure(counters, key)
    if counters[key]["daily_count"] < MAX_GENERATIONS:
        counters[key]["daily_count"] += 1
    else:
        counters[key]["bonus"] = max(0, counters[key]["bonus"] - 1)
    counters[key]["total_ever"] += 1
    _save(COUNTERS_FILE, counters)

def add_bonus(user_id: int, amount: int) -> None:
    counters = _load(COUNTERS_FILE)
    key = str(user_id)
    _ensure(counters, key)
    counters[key]["bonus"] += amount
    _save(COUNTERS_FILE, counters)

def get_stats_counters() -> tuple:
    counters = _load(COUNTERS_FILE)
    today = str(date.today())
    total_ever = sum(c.get("total_ever", 0) for c in counters.values())
    today_count = sum(c.get("daily_count", 0) for c in counters.values() if c.get("date") == today)
    exhausted = sum(
        1 for c in counters.values()
        if c.get("date") == today and c.get("daily_count", 0) >= MAX_GENERATIONS and c.get("bonus", 0) == 0
    )
    top = sorted(
        [(k, c.get("total_ever", 0)) for k, c in counters.items()],
        key=lambda x: x[1], reverse=True
    )[:5]
    return total_ever, today_count, exhausted, top


# ── Рефералы ─────────────────────────────────────────────────────────────────

def process_referral(new_user_id: int, referrer_id: int) -> None:
    if new_user_id == referrer_id:
        return
    refs = _load(REFERRALS_FILE)
    key = str(referrer_id)
    new_key = str(new_user_id)
    for r in refs.values():
        if new_key in r.get("invited", []):
            return
    if key not in refs:
        refs[key] = {"invited": [], "bonus_earned": 0}
    refs[key]["invited"].append(new_key)
    refs[key]["bonus_earned"] += 3
    _save(REFERRALS_FILE, refs)
    add_bonus(referrer_id, 3)
    add_bonus(new_user_id, 2)

def get_referral_stats(user_id: int) -> dict:
    refs = _load(REFERRALS_FILE)
    r = refs.get(str(user_id), {})
    return {"invited": len(r.get("invited", [])), "bonus_earned": r.get("bonus_earned", 0)}


# ── Покупки (Stars) ───────────────────────────────────────────────────────────

def record_purchase(user_id: int, stars: int, generations: int) -> None:
    purchases = _load(PURCHASES_FILE)
    today = str(date.today())
    if today not in purchases:
        purchases[today] = []
    purchases[today].append({"user_id": user_id, "stars": stars, "generations": generations})
    _save(PURCHASES_FILE, purchases)

def get_purchase_stats() -> tuple:
    purchases = _load(PURCHASES_FILE)
    total_p = sum(len(v) for v in purchases.values())
    total_s = sum(p["stars"] for v in purchases.values() for p in v)
    return total_p, total_s


# ── Клавиатуры ────────────────────────────────────────────────────────────────

def main_menu(selections: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎨 Цвет кузова: {BODY_OPTIONS[selections['body']]}", callback_data="cat_body")],
        [InlineKeyboardButton(f"🔲 Покрытие: {FINISH_OPTIONS[selections['finish']]}", callback_data="cat_finish")],
        [InlineKeyboardButton(f"💿 Диски: {WHEELS_OPTIONS[selections['wheels']]}", callback_data="cat_wheels")],
        [InlineKeyboardButton(f"⚙️ Радиус: {WHEELS_SIZE_OPTIONS[selections['wheels_size']]}", callback_data="cat_wheels_size")],
        [InlineKeyboardButton(f"🪟 Тонировка задних: {TINT_OPTIONS[selections['tint']]}", callback_data="cat_tint")],
        [InlineKeyboardButton(f"🔵 Лобовое стекло: {WINDSHIELD_OPTIONS[selections['windshield']]}", callback_data="cat_windshield")],
        [InlineKeyboardButton(f"🌊 Боковые передние: {SIDEGLASS_OPTIONS[selections['sideglass']]}", callback_data="cat_sideglass")],
        [InlineKeyboardButton(f"💡 Оптика: {OPTICS_OPTIONS[selections['optics']]}", callback_data="cat_optics")],
        [InlineKeyboardButton(f"⚫ Антихром: {ANTICHROME_OPTIONS[selections['antichrome']]}", callback_data="cat_antichrome")],
        [InlineKeyboardButton(f"🪞 Зеркала: {MIRRORS_OPTIONS[selections['mirrors']]}", callback_data="cat_mirrors")],
        [InlineKeyboardButton(f"🚪 Ручки дверей: {HANDLES_OPTIONS[selections['handles']]}", callback_data="cat_handles")],
        [InlineKeyboardButton(f"🖤 Крыша: {ROOF_OPTIONS[selections['roof']]}", callback_data="cat_roof")],
        [InlineKeyboardButton(f"🏎 Обвес: {BODYKIT_OPTIONS[selections['bodykit']]}", callback_data="cat_bodykit")],
        [InlineKeyboardButton(f"✨ Декор: {DECOR_OPTIONS[selections['decor']]}", callback_data="cat_decor")],
        [InlineKeyboardButton(f"📷 Ракурс: {ANGLE_OPTIONS[selections['angle']]}", callback_data="cat_angle")],
        [InlineKeyboardButton(f"🏙 Фон: {BACKGROUND_OPTIONS[selections['background']]}", callback_data="cat_background")],
        [InlineKeyboardButton("🎨 Сгенерировать визуализацию", callback_data="generate")],
    ])


def options_keyboard(category: str, options: dict, current: str) -> InlineKeyboardMarkup:
    rows = []
    for key, name in options.items():
        prefix = "✅ " if key == current else ""
        rows.append([InlineKeyboardButton(f"{prefix}{name}", callback_data=f"sel|{category}|{key}")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def buy_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for pkg in STARS_PACKAGES:
        rows.append([InlineKeyboardButton(pkg["label"], callback_data=f"buy|{pkg['payload']}")])
    rows.append([InlineKeyboardButton("🔗 Пригласить друга (+3 генерации)", callback_data="show_referral")])
    return InlineKeyboardMarkup(rows)


# ── Промпт ────────────────────────────────────────────────────────────────────

def build_prompt(selections: dict) -> str:
    finish = selections["finish"]
    color = BODY_EN[selections["body"]]
    if finish in ("carbon", "chrome", "camouflage", "psychedelic"):
        body = FINISH_EN[finish]
    elif selections["body"] == "original":
        body = f"{FINISH_EN[finish]} keeping the original color"
    else:
        body = f"{color} {FINISH_EN[finish]}"
    wheels_size = WHEELS_SIZE_EN[selections["wheels_size"]]
    wheels_color = WHEELS_EN[selections["wheels"]]
    wheels = f"{wheels_size} {wheels_color}".strip()
    tint = TINT_EN[selections["tint"]]
    windshield = WINDSHIELD_EN[selections["windshield"]]
    sideglass = SIDEGLASS_EN[selections["sideglass"]]
    antichrome = ANTICHROME_EN[selections["antichrome"]]
    mirrors = MIRRORS_EN[selections["mirrors"]]
    handles = HANDLES_EN[selections["handles"]]
    roof = ROOF_EN[selections["roof"]]
    decor = DECOR_EN[selections["decor"]]
    background = BACKGROUND_EN[selections["background"]]
    optics = OPTICS_EN[selections["optics"]]
    bodykit = BODYKIT_EN[selections["bodykit"]]
    extras = [x for x in [optics, antichrome, mirrors, handles, roof, bodykit, decor] if x]
    extras_text = (", " + ", ".join(extras)) if extras else ""
    angle = ANGLE_EN[selections["angle"]]
    return (
        f"Professional automotive photo retouching. "
        f"Take this exact car and apply the following modifications: {body}, wheels changed to {wheels}, "
        f"{tint}, {windshield}, {sideglass}{extras_text}. "
        f"Place the car in {background}, camera angle: {angle}. "
        f"CRITICAL REQUIREMENTS: "
        f"Keep the exact same car make, model, body shape, proportions, and all exterior details. "
        f"Hyper-realistic photography, no cartoon or illustration style. "
        f"Shot with a professional camera, sharp focus, physically accurate materials and reflections. "
        f"The result must look like a real photograph of a real car, indistinguishable from a studio automotive photo. "
        f"8K resolution, cinematic lighting, ray-traced reflections."
    )


# ── Хэндлеры ──────────────────────────────────────────────────────────────────

def user_link(user) -> str:
    name = user.full_name or "Без имени"
    username = f" @{user.username}" if user.username else ""
    return f"{name}{username}"


async def notify_owner(context, text: str) -> None:
    try:
        bot = _notify_bot if _notify_bot else context.bot
        await bot.send_message(chat_id=OWNER_CHAT_ID, text=text)
    except Exception as e:
        logger.error("Ошибка отправки уведомления: %s", e)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    is_new = register_user(user_id, user)

    user_states[user_id] = {
        "photo_id": None,
        "selections": DEFAULT_SELECTIONS.copy(),
    }

    if is_new:
        # Обработка реферала
        if context.args:
            arg = context.args[0]
            if arg.startswith("ref_"):
                try:
                    referrer_id = int(arg[4:])
                    process_referral(user_id, referrer_id)
                    gen_info = get_generation_info(user_id)
                    await update.message.reply_text(
                        f"🎁 Ты пришёл по реферальной ссылке — тебе начислено "
                        f"+{gen_info['bonus']} бонусных генераций!"
                    )
                except ValueError:
                    pass

        await notify_owner(
            context,
            f"👤 Новый пользователь запустил бота:\n"
            f"{user_link(user)}\n"
            f"ID: {user_id}"
        )

    await update.message.reply_text(
        "👋 Привет! Я помогу тебе представить, как будет выглядеть твой автомобиль "
        "после тюнинга в Найскар Центр.\n\n"
        "📸 Загрузи фото своей машины — и начнём!"
    )


async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    stats = get_referral_stats(user_id)
    await update.message.reply_text(
        f"🔗 Твоя реферальная ссылка:\n{ref_link}\n\n"
        f"👥 Приглашено друзей: {stats['invited']}\n"
        f"⭐ Бонусных генераций заработано: {stats['bonus_earned']}\n\n"
        f"За каждого приглашённого друга:\n"
        f"• Тебе: +3 генерации\n"
        f"• Другу: +2 генерации"
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    total_users, new_today = count_users()
    total_gen, today_gen, exhausted, top = get_stats_counters()
    total_purchases, total_stars = get_purchase_stats()

    top_lines = []
    for uid, count in top:
        name = get_user_name(int(uid))
        top_lines.append(f"  {name}: {count} генераций")
    top_text = "\n".join(top_lines) if top_lines else "  —"

    await update.message.reply_text(
        f"📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🆕 Новых сегодня: {new_today}\n\n"
        f"🎨 Всего генераций: {total_gen}\n"
        f"📅 Генераций сегодня: {today_gen}\n"
        f"🚫 Исчерпали лимит сегодня: {exhausted}\n\n"
        f"⭐ Покупок Stars: {total_purchases} (итого {total_stars} Stars)\n\n"
        f"🏆 Топ-5 активных:\n{top_text}"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_states:
        user_states[user_id] = {
            "photo_id": None,
            "selections": DEFAULT_SELECTIONS.copy(),
        }
    user_states[user_id]["photo_id"] = update.message.photo[-1].file_id
    info = get_generation_info(user_id)
    await update.message.reply_text(
        f"✅ Фото получено!\n"
        f"Доступно генераций: {info['total_left']} "
        f"(бесплатных: {info['free_left']}, бонусных: {info['bonus']})\n\n"
        "Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
        reply_markup=main_menu(user_states[user_id]["selections"]),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if user_id not in user_states:
        await query.edit_message_text("Пожалуйста, начни сначала — отправь команду /start")
        return

    state = user_states[user_id]
    sel = state["selections"]

    if data == "cat_body":
        await query.edit_message_text("🎨 Выбери цвет кузова:", reply_markup=options_keyboard("body", BODY_OPTIONS, sel["body"]))
    elif data == "cat_finish":
        await query.edit_message_text("🔲 Выбери тип покрытия:", reply_markup=options_keyboard("finish", FINISH_OPTIONS, sel["finish"]))
    elif data == "cat_wheels":
        await query.edit_message_text("💿 Выбери цвет дисков:", reply_markup=options_keyboard("wheels", WHEELS_OPTIONS, sel["wheels"]))
    elif data == "cat_wheels_size":
        await query.edit_message_text("⚙️ Выбери радиус дисков:", reply_markup=options_keyboard("wheels_size", WHEELS_SIZE_OPTIONS, sel["wheels_size"]))
    elif data == "cat_tint":
        await query.edit_message_text("🪟 Тонировка задних стёкол:", reply_markup=options_keyboard("tint", TINT_OPTIONS, sel["tint"]))
    elif data == "cat_windshield":
        await query.edit_message_text("🔵 Лобовое стекло — выбери плёнку:", reply_markup=options_keyboard("windshield", WINDSHIELD_OPTIONS, sel["windshield"]))
    elif data == "cat_sideglass":
        await query.edit_message_text("🌊 Передние боковые стёкла — выбери плёнку:", reply_markup=options_keyboard("sideglass", SIDEGLASS_OPTIONS, sel["sideglass"]))
    elif data == "cat_optics":
        await query.edit_message_text("💡 Тонировка оптики (фары и фонари):", reply_markup=options_keyboard("optics", OPTICS_OPTIONS, sel["optics"]))
    elif data == "cat_antichrome":
        await query.edit_message_text("⚫ Антихром — оклейка хромированных деталей кузова:", reply_markup=options_keyboard("antichrome", ANTICHROME_OPTIONS, sel["antichrome"]))
    elif data == "cat_mirrors":
        await query.edit_message_text("🪞 Зеркала — цвет покрытия:", reply_markup=options_keyboard("mirrors", MIRRORS_OPTIONS, sel["mirrors"]))
    elif data == "cat_handles":
        await query.edit_message_text("🚪 Ручки дверей — цвет покрытия:", reply_markup=options_keyboard("handles", HANDLES_OPTIONS, sel["handles"]))
    elif data == "cat_roof":
        await query.edit_message_text("🖤 Крыша — цвет покрытия:", reply_markup=options_keyboard("roof", ROOF_OPTIONS, sel["roof"]))
    elif data == "cat_bodykit":
        await query.edit_message_text("🏎 Выбери обвес:", reply_markup=options_keyboard("bodykit", BODYKIT_OPTIONS, sel["bodykit"]))
    elif data == "cat_decor":
        await query.edit_message_text("✨ Декоративные элементы:", reply_markup=options_keyboard("decor", DECOR_OPTIONS, sel["decor"]))
    elif data == "cat_angle":
        await query.edit_message_text("📷 Выбери ракурс:", reply_markup=options_keyboard("angle", ANGLE_OPTIONS, sel["angle"]))
    elif data == "cat_background":
        await query.edit_message_text("🏙 Выбери фон:", reply_markup=options_keyboard("background", BACKGROUND_OPTIONS, sel["background"]))
    elif data.startswith("sel|"):
        _, category, key = data.split("|", 2)
        sel[category] = key
        await query.edit_message_text(
            "Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
            reply_markup=main_menu(sel),
        )
    elif data == "back_main":
        if query.message.photo:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
                reply_markup=main_menu(sel),
            )
        else:
            await query.edit_message_text(
                "Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
                reply_markup=main_menu(sel),
            )
    elif data == "show_referral":
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        stats = get_referral_stats(user_id)
        await query.edit_message_text(
            f"🔗 Твоя реферальная ссылка:\n{ref_link}\n\n"
            f"👥 Приглашено: {stats['invited']}\n"
            f"⭐ Бонусов заработано: {stats['bonus_earned']} генераций\n\n"
            "За каждого друга — тебе +3, другу +2 генерации!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]),
        )
    elif data.startswith("buy|"):
        payload = data[4:]
        pkg = next((p for p in STARS_PACKAGES if p["payload"] == payload), None)
        if not pkg:
            return
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="Генерации визуализации",
            description=f"{pkg['generations']} генераций тюнинга автомобиля в Найскар Центр",
            payload=pkg["payload"],
            currency="XTR",
            prices=[LabeledPrice(label=pkg["label"], amount=pkg["stars"])],
        )
    elif data == "generate":
        if not state.get("photo_id"):
            await query.edit_message_text("Сначала загрузи фото своей машины!", reply_markup=main_menu(sel))
            return

        info = get_generation_info(user_id)
        if info["total_left"] <= 0:
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
            await query.edit_message_text(
                f"Ты использовал все {MAX_GENERATIONS} бесплатных генераций на сегодня 🎨\n\n"
                f"Хочешь ещё?\n\n"
                f"⭐ 20 генераций за 50 Stars\n"
                f"⭐ 50 генераций за 100 Stars\n\n"
                f"Или пригласи друга и получи +3 генерации бесплатно:\n{ref_link}",
                reply_markup=buy_keyboard(),
            )
            return

        await query.edit_message_text("⏳ Генерирую визуализацию… это займёт 30–60 секунд.")

        prompt = build_prompt(sel)
        logger.info("prompt: %s", prompt)

        try:
            photo_file = await context.bot.get_file(state["photo_id"])
            photo_data = await photo_file.download_as_bytearray()
            photo_io = io.BytesIO(bytes(photo_data))
            photo_io.name = "car.jpg"
            response = openai_client.images.edit(
                model="gpt-image-1",
                image=photo_io,
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
            image_bytes = add_watermark(io.BytesIO(base64.b64decode(response.data[0].b64_json)))
        except Exception as exc:
            logger.error("OpenAI error: %s", exc)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ошибка при генерации. Попробуй ещё раз или напиши @nicecar_center",
            )
            return

        use_generation(user_id)
        info_after = get_generation_info(user_id)

        await notify_owner(
            context,
            f"🎨 Новая генерация!\n\n"
            f"👤 {user_link(query.from_user)}\n"
            f"ID: {user_id}\n\n"
            f"🎨 Кузов: {BODY_OPTIONS[sel['body']]} {FINISH_OPTIONS[sel['finish']]}\n"
            f"💿 Диски: {WHEELS_OPTIONS[sel['wheels']]} {WHEELS_SIZE_OPTIONS[sel['wheels_size']]}\n"
            f"🪟 Тонировка задних: {TINT_OPTIONS[sel['tint']]}\n"
            f"🔵 Лобовое: {WINDSHIELD_OPTIONS[sel['windshield']]}\n"
            f"🌊 Боковые: {SIDEGLASS_OPTIONS[sel['sideglass']]}\n"
            f"💡 Оптика: {OPTICS_OPTIONS[sel['optics']]}\n"
            f"⚫ Антихром: {ANTICHROME_OPTIONS[sel['antichrome']]}\n"
            f"🪞 Зеркала: {MIRRORS_OPTIONS[sel['mirrors']]}\n"
            f"🚪 Ручки: {HANDLES_OPTIONS[sel['handles']]}\n"
            f"🖤 Крыша: {ROOF_OPTIONS[sel['roof']]}\n"
            f"🏎 Обвес: {BODYKIT_OPTIONS[sel['bodykit']]}\n"
            f"✨ Декор: {DECOR_OPTIONS[sel['decor']]}\n"
            f"📷 Ракурс: {ANGLE_OPTIONS[sel['angle']]}\n"
            f"🏙 Фон: {BACKGROUND_OPTIONS[sel['background']]}"
        )

        caption = (
            "✨ Визуализация готова!\n\n"
            f"🎨 {BODY_OPTIONS[sel['body']]} {FINISH_OPTIONS[sel['finish']]}\n"
            f"💿 {WHEELS_OPTIONS[sel['wheels']]} {WHEELS_SIZE_OPTIONS[sel['wheels_size']]}  •  🪟 {TINT_OPTIONS[sel['tint']]}\n"
            f"🔵 {WINDSHIELD_OPTIONS[sel['windshield']]}  •  🌊 {SIDEGLASS_OPTIONS[sel['sideglass']]}\n"
            f"📷 {ANGLE_OPTIONS[sel['angle']]}\n"
            f"💡 {OPTICS_OPTIONS[sel['optics']]}  •  ⚫ {ANTICHROME_OPTIONS[sel['antichrome']]}\n"
            f"🪞 {MIRRORS_OPTIONS[sel['mirrors']]}  •  🚪 {HANDLES_OPTIONS[sel['handles']]}  •  🖤 {ROOF_OPTIONS[sel['roof']]}\n"
            f"🏎 {BODYKIT_OPTIONS[sel['bodykit']]}\n"
            f"✨ {DECOR_OPTIONS[sel['decor']]}\n\n"
            f"Осталось генераций: {info_after['total_left']} "
            f"(бесплатных: {info_after['free_left']}, бонусных: {info_after['bonus']})"
        )

        share_text = f"Смотри как я изменил свою машину! Попробуй сам бесплатно → https://t.me/{BOT_USERNAME}"
        result_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚗 Получить консультацию в Найскар Центр по внешнему виду", url="https://t.me/nicecar_center")],
            [InlineKeyboardButton("🚀 Поделиться с другом", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text={share_text}")],
            [InlineKeyboardButton("🔄 Изменить параметры", callback_data="back_main")],
        ])

        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_bytes,
            caption=caption,
            reply_markup=result_keyboard,
        )


async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    pkg = next((p for p in STARS_PACKAGES if p["payload"] == payload), None)
    if not pkg:
        return
    add_bonus(user_id, pkg["generations"])
    record_purchase(user_id, pkg["stars"], pkg["generations"])
    info = get_generation_info(user_id)
    await update.message.reply_text(
        f"✅ Оплата прошла! Начислено {pkg['generations']} генераций.\n"
        f"Всего доступно: {info['total_left']} генераций."
    )
    await notify_owner(
        context,
        f"⭐ Покупка!\n{user_link(update.effective_user)}\n"
        f"ID: {user_id}\n{pkg['stars']} Stars → {pkg['generations']} генераций"
    )


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Chat ID: `{update.effective_chat.id}`", parse_mode="Markdown")


# ── Запуск ────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("referral", cmd_referral))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
