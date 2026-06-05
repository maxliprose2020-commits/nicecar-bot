import os
import io
import base64
import json
import logging
from datetime import date, datetime
from urllib.parse import quote
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
OWNER_CHAT_ID = int(os.environ.get("OWNER_CHAT_ID", "862676483"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "862676483"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "nicecar_tuning_bot")
MANAGER_IDS = set(
    int(x.strip()) for x in os.environ.get("MANAGER_IDS", "").split(",") if x.strip().isdigit()
)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

COUNTERS_FILE = "counters.json"
USERS_FILE = "users.json"
REFERRALS_FILE = "referrals.json"
PURCHASES_FILE = "purchases.json"
BLOGGERS_FILE = "bloggers.json"
CARDS_FILE = "user_cards.json"
MANAGER_STATS_FILE = "manager_stats.json"
MANAGER_CARDS_FILE = "manager_cards.json"
COSTS_FILE = "costs.json"
LEADS_FILE = "leads.json"
STUDIOS_FILE = "studios.json"
MAX_GENERATIONS = 3
COST_PER_GENERATION = 0.042  # USD, gpt-image-1 1024x1024 medium quality

STARS_PACKAGES = [
    {"stars": 75,  "generations": 10, "payload": "buy_10", "label": "10 генераций — 75 ⭐"},
    {"stars": 180, "generations": 25, "payload": "buy_25", "label": "25 генераций — 180 ⭐"},
    {"stars": 360, "generations": 50, "payload": "buy_50", "label": "50 генераций — 360 ⭐"},
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
    "pink":      "Розовый",
}

FINISH_OPTIONS = {
    "matte":       "Матт",
    "gloss":       "Глянец",
    "satin":       "Сатин",
    "carbon":      "Карбон",
    "chrome":      "Хром",
    "camouflage":  "Камуфляж",
    "psychedelic": "Психоделика",
    "pearl":       "Жемчужный хамелеон",
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
    "original":          "Оригинал",
    "roof_only":         "Чёрная крыша (без стоек)",
    "roof_with_pillars": "Чёрная крыша + стойки",
    "maybach":           "Майбах стиль (верх до ручек)",
}

MAYBACH_COLOR_OPTIONS = {
    "black_gloss": "Чёрный глянец",
    "black_matte": "Чёрный матт",
    "black_satin": "Чёрный сатин",
    "white_gloss": "Белый глянец",
    "dark_blue":   "Тёмно-синий",
    "burgundy":    "Бордовый",
    "silver":      "Серебристый",
}

MAYBACH_COLOR_EN = {
    "black_gloss": "gloss black",
    "black_matte": "matte black",
    "black_satin": "satin black",
    "white_gloss": "gloss white",
    "dark_blue":   "dark navy blue",
    "burgundy":    "deep burgundy",
    "silver":      "silver",
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
    "pink":      "pink",
}

FINISH_EN = {
    "matte":       "matte vinyl wrap",
    "gloss":       "gloss vinyl wrap",
    "satin":       "satin vinyl wrap",
    "carbon":      "carbon fiber vinyl wrap",
    "chrome":      "chrome vinyl wrap",
    "camouflage":  "camouflage vinyl wrap",
    "psychedelic": "psychedelic multicolor holographic vinyl wrap with vivid neon patterns",
    "pearl":       "pearlescent white chameleon vinyl wrap with purple and pink color-shifting iridescent shimmer",
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
    "original":          "",
    "roof_only":         "roof panel only wrapped in gloss black vinyl, keep all A/B/C pillars in original color",
    "roof_with_pillars": "roof panel and all window pillars (A/B/C pillars) wrapped in gloss black vinyl",
    "maybach":           "Maybach-style two-tone: entire upper body from roofline down to the door handle line (roof, pillars, upper door panels) wrapped in gloss black vinyl, lower body keeps original color — clean horizontal split at door handle level",
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
    "roof":          "original",
    "maybach_color": "black_gloss",
    "bodykit":      "none",
    "decor":        "none",
    "angle":        "original",
    "background":   "night_city",
}

# user_id → {"photo_id": str | None, "selections": dict, "custom_design": str, "awaiting_custom_design": bool}
user_states: dict[int, dict] = {}
admin_state: dict[int, str] = {}


# ── Водяной знак ──────────────────────────────────────────────────────────────

LOGO_PATH = "logo.png"

def add_watermark(image_bytes: io.BytesIO) -> io.BytesIO:
    img = Image.open(image_bytes).convert("RGBA")

    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        # Делаем белый фон прозрачным
        data = logo.getdata()
        new_data = []
        for r, g, b, a in data:
            if r > 220 and g > 220 and b > 220:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        logo.putdata(new_data)
        # Размер: 1/4 ширины изображения
        logo_w = img.width // 4
        logo_h = int(logo.height * logo_w / logo.width)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        # Полупрозрачность 80%
        r, g, b, a = logo.split()
        a = a.point(lambda x: int(x * 0.80))
        logo = Image.merge("RGBA", (r, g, b, a))
        pad = 16
        x = pad
        y = pad
        img.paste(logo, (x, y), logo)
    else:
        # Фолбэк — текст если лого нет
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        text = "NiceCar Center"
        font_size = max(28, img.width // 22)
        font = None
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]:
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except Exception:
                pass
        if font is None:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 16
        x, y = img.width - tw - pad, img.height - th - pad
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 120))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 200))
        img = Image.alpha_composite(img, overlay)

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=95)
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
        "joined_time": datetime.now().strftime("%H:%M, %d.%m.%Y"),
    }
    _save(USERS_FILE, users)
    init_user_counter(user_id)
    return True

def get_user_name(user_id: int) -> str:
    users = _load(USERS_FILE)
    u = users.get(str(user_id), {})
    name = u.get("name", str(user_id))
    username = u.get("username", "")
    return f"{name} @{username}" if username else name

def build_card_text(user_id: int) -> str:
    users = _load(USERS_FILE)
    u = users.get(str(user_id), {})
    username = u.get("username", "")
    name = u.get("name", str(user_id))
    joined_time = u.get("joined_time", "—")
    id_line = f"@{username}" if username else f"ID: {user_id}"

    counters = _load(COUNTERS_FILE)
    c = counters.get(str(user_id), {})
    gen_count = c.get("total_ever", 0)

    refs = _load(REFERRALS_FILE)
    shared_icon = "✅" if any(str(user_id) == k and refs[k].get("invited") for k in refs) else "❌"

    purchases = _load(PURCHASES_FILE)
    user_purchases = [p for v in purchases.values() for p in v if p.get("user_id") == user_id]
    if user_purchases:
        last = user_purchases[-1]
        stars_line = f"✅ {last['stars']} Stars ({last['generations']} генераций)"
    else:
        stars_line = "❌"

    user_cost = gen_count * COST_PER_GENERATION
    return (
        f"👤 Новый пользователь — Найскар Центр\n\n"
        f"🆔 {id_line}\n"
        f"📱 ID: {user_id}\n"
        f"⏰ {joined_time}\n\n"
        f"🎨 Генераций сделал: {gen_count}\n"
        f"💸 Расходы на AI: ${user_cost:.3f}\n"
        f"🔗 Поделился с другом: {shared_icon}\n"
        f"⭐ Купил Stars: {stars_line}"
    )

async def send_user_card(bot, user_id: int) -> None:
    try:
        text = build_card_text(user_id)
        msg = await bot.send_message(chat_id=OWNER_CHAT_ID, text=text)
        cards = _load(CARDS_FILE)
        cards[str(user_id)] = msg.message_id
        _save(CARDS_FILE, cards)
    except Exception as e:
        logger.error("Ошибка отправки карточки: %s", e)

async def update_user_card(bot, user_id: int) -> None:
    cards = _load(CARDS_FILE)
    msg_id = cards.get(str(user_id))
    if not msg_id:
        await send_user_card(bot, user_id)
        return
    try:
        text = build_card_text(user_id)
        await bot.edit_message_text(chat_id=OWNER_CHAT_ID, message_id=msg_id, text=text)
    except Exception as e:
        logger.error("Ошибка обновления карточки: %s", e)

def count_users() -> tuple:
    users = _load(USERS_FILE)
    today = str(date.today())
    return len(users), sum(1 for u in users.values() if u.get("joined") == today)


# ── Счётчики генераций ────────────────────────────────────────────────────────

def _ensure(counters: dict, key: str) -> None:
    if key not in counters:
        counters[key] = {"free": MAX_GENERATIONS, "bonus": 0, "total_ever": 0}
    else:
        # Миграция со старой структуры с daily_count
        if "daily_count" in counters[key] and "free" not in counters[key]:
            used = counters[key].get("daily_count", 0)
            counters[key]["free"] = max(0, MAX_GENERATIONS - used)
            del counters[key]["daily_count"]
            counters[key].pop("date", None)
        for f in ("free", "bonus", "total_ever"):
            if f not in counters[key]:
                counters[key][f] = 0

def init_user_counter(user_id: int) -> None:
    counters = _load(COUNTERS_FILE)
    key = str(user_id)
    if key not in counters:
        counters[key] = {"free": MAX_GENERATIONS, "bonus": 0, "total_ever": 0}
        _save(COUNTERS_FILE, counters)

def get_generation_info(user_id: int) -> dict:
    counters = _load(COUNTERS_FILE)
    key = str(user_id)
    _ensure(counters, key)
    free = counters[key]["free"]
    bonus = counters[key]["bonus"]
    return {"free": free, "bonus": bonus, "total_left": free + bonus}

def use_generation(user_id: int) -> None:
    counters = _load(COUNTERS_FILE)
    key = str(user_id)
    _ensure(counters, key)
    if counters[key]["free"] > 0:
        counters[key]["free"] -= 1
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
    total_ever = sum(c.get("total_ever", 0) for c in counters.values())
    today_count = total_ever  # нет дневного счётчика, используем total
    exhausted = sum(
        1 for c in counters.values()
        if c.get("free", 0) == 0 and c.get("bonus", 0) == 0
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
    # Привязываем студию реферера к новому пользователю
    studio_name = get_user_studio(referrer_id)
    if studio_name:
        set_user_studio(new_user_id, studio_name)
        studios = _load(STUDIOS_FILE)
        if studio_name in studios:
            studios[studio_name]["users_count"] = studios[studio_name].get("users_count", 0) + 1
            _save(STUDIOS_FILE, studios)

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


# ── Карточки менеджеров ───────────────────────────────────────────────────────

def track_manager_generation(user_id: int) -> None:
    data = _load(MANAGER_STATS_FILE)
    key = str(user_id)
    if key not in data:
        data[key] = {"count": 0}
    data[key]["count"] += 1
    _save(MANAGER_STATS_FILE, data)

def build_manager_card_text(user_id: int) -> str:
    users = _load(USERS_FILE)
    u = users.get(str(user_id), {})
    username = u.get("username", "")
    name = u.get("name", str(user_id))
    id_line = f"@{username}" if username else f"ID: {user_id}"
    data = _load(MANAGER_STATS_FILE)
    count = data.get(str(user_id), {}).get("count", 0)
    cost = count * COST_PER_GENERATION
    return (
        f"👨‍💼 Менеджер — Найскар Центр\n\n"
        f"🆔 {id_line}\n"
        f"📱 ID: {user_id}\n\n"
        f"🎨 Генераций сделал: {count}\n"
        f"💸 Расходы на AI: ${cost:.3f}"
    )

async def send_manager_card(bot, user_id: int) -> None:
    try:
        text = build_manager_card_text(user_id)
        msg = await bot.send_message(chat_id=OWNER_CHAT_ID, text=text)
        cards = _load(MANAGER_CARDS_FILE)
        cards[str(user_id)] = msg.message_id
        _save(MANAGER_CARDS_FILE, cards)
    except Exception as e:
        logger.error("Ошибка отправки карточки менеджера: %s", e)

async def update_manager_card(bot, user_id: int) -> None:
    cards = _load(MANAGER_CARDS_FILE)
    msg_id = cards.get(str(user_id))
    if not msg_id:
        await send_manager_card(bot, user_id)
        return
    try:
        text = build_manager_card_text(user_id)
        await bot.edit_message_text(chat_id=OWNER_CHAT_ID, message_id=msg_id, text=text)
    except Exception as e:
        logger.error("Ошибка обновления карточки менеджера: %s", e)


# ── Расходы на OpenAI ─────────────────────────────────────────────────────────

def add_generation_cost() -> None:
    data = _load(COSTS_FILE)
    data["total_usd"] = round(data.get("total_usd", 0.0) + COST_PER_GENERATION, 4)
    data["total_generations"] = data.get("total_generations", 0) + 1
    _save(COSTS_FILE, data)

def get_cost_stats() -> tuple:
    data = _load(COSTS_FILE)
    return data.get("total_generations", 0), data.get("total_usd", 0.0)


# ── Квалификационные вопросы (лиды) ──────────────────────────────────────────

def should_ask_qualification(user_id: int) -> bool:
    counters = _load(COUNTERS_FILE)
    total = counters.get(str(user_id), {}).get("total_ever", 0)
    leads = _load(LEADS_FILE)
    already_asked = str(user_id) in leads
    return total >= MAX_GENERATIONS and not already_asked

def mark_qualification_asked(user_id: int) -> None:
    leads = _load(LEADS_FILE)
    leads[str(user_id)] = {"asked": True}
    _save(LEADS_FILE, leads)

def save_lead(user_id: int, interest: str, service: str = "") -> None:
    leads = _load(LEADS_FILE)
    if str(user_id) not in leads:
        leads[str(user_id)] = {"asked": True}
    leads[str(user_id)]["interest"] = interest
    if service:
        leads[str(user_id)]["service"] = service
    _save(LEADS_FILE, leads)

async def send_hot_lead(bot, user, service: str) -> None:
    username = f"@{user.username}" if user.username else user.full_name
    link = f"t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    now = datetime.now().strftime("%H:%M, %d.%m.%Y")
    studio_name = get_user_studio(user.id)
    studios = _load(STUDIOS_FILE)
    if studio_name and studio_name in studios:
        track_studio_lead_count(studio_name)
        studio = studios[studio_name]
        try:
            await bot.send_message(
                chat_id=studio["telegram_id"],
                text=(
                    f"👤 Новый лид — {studio_name}\n\n"
                    f"🆔 {username}\n"
                    f"📱 ID: {user.id}\n"
                    f"⏰ {now}\n\n"
                    f"🚗 Интерес: {service}\n"
                    f"🔗 Написать клиенту: {link}"
                ),
            )
        except Exception as e:
            logger.error("Ошибка отправки лида студии: %s", e)
    else:
        try:
            await bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=(
                    f"🔥 Горячий лид!\n\n"
                    f"👤 {username}\n"
                    f"🚗 Интерес: {service}\n"
                    f"⏰ {now}\n\n"
                    f"{link}"
                ),
            )
        except Exception as e:
            logger.error("Ошибка отправки лида: %s", e)


# ── Студии ───────────────────────────────────────────────────────────────────

from datetime import timedelta

def create_studio(name: str, telegram_id: int) -> dict:
    studios = _load(STUDIOS_FILE)
    start = date.today()
    end = start + timedelta(days=5)
    studio = {
        "name": name, "telegram_id": telegram_id,
        "limit": 150, "used": 0,
        "start_date": str(start), "end_date": str(end),
        "status": "trial", "leads_count": 0, "users_count": 0,
    }
    studios[name] = studio
    _save(STUDIOS_FILE, studios)
    return studio

def get_user_studio(user_id: int) -> str:
    users = _load(USERS_FILE)
    return users.get(str(user_id), {}).get("studio", "")

def set_user_studio(user_id: int, studio_name: str) -> None:
    users = _load(USERS_FILE)
    if str(user_id) in users:
        users[str(user_id)]["studio"] = studio_name
        _save(USERS_FILE, users)

def get_studio_by_owner(telegram_id: int) -> dict | None:
    studios = _load(STUDIOS_FILE)
    for s in studios.values():
        if s.get("telegram_id") == telegram_id:
            return s
    return None

def studio_days_elapsed(studio: dict) -> int:
    start = date.fromisoformat(studio["start_date"])
    return (date.today() - start).days + 1

def studio_days_left(studio: dict) -> int:
    end = date.fromisoformat(studio["end_date"])
    return (end - date.today()).days

def track_studio_generation(user_id: int) -> None:
    name = get_user_studio(user_id)
    if not name:
        return
    studios = _load(STUDIOS_FILE)
    if name in studios:
        studios[name]["used"] = studios[name].get("used", 0) + 1
        _save(STUDIOS_FILE, studios)

def track_studio_lead_count(studio_name: str) -> None:
    studios = _load(STUDIOS_FILE)
    if studio_name in studios:
        studios[studio_name]["leads_count"] = studios[studio_name].get("leads_count", 0) + 1
        _save(STUDIOS_FILE, studios)


# ── Блогеры ──────────────────────────────────────────────────────────────────

def blogger_track_click(name: str, user_id: int) -> None:
    data = _load(BLOGGERS_FILE)
    if name not in data:
        return
    key = str(user_id)
    if key not in data[name]["clicks"]:
        data[name]["clicks"].append(key)
    _save(BLOGGERS_FILE, data)

def blogger_track_generation(user_id: int) -> None:
    data = _load(BLOGGERS_FILE)
    key = str(user_id)
    for name, info in data.items():
        if key in info.get("clicks", []) and key not in info.get("generated", []):
            info.setdefault("generated", []).append(key)
    _save(BLOGGERS_FILE, data)

def blogger_track_purchase(user_id: int) -> None:
    data = _load(BLOGGERS_FILE)
    key = str(user_id)
    for name, info in data.items():
        if key in info.get("clicks", []) and key not in info.get("purchased", []):
            info.setdefault("purchased", []).append(key)
    _save(BLOGGERS_FILE, data)


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
        *([[InlineKeyboardButton(f"🎨 Цвет верха Майбах: {MAYBACH_COLOR_OPTIONS[selections['maybach_color']]}", callback_data="cat_maybach_color")]] if selections.get("roof") == "maybach" else []),
        [InlineKeyboardButton(f"🏎 Обвес: {BODYKIT_OPTIONS[selections['bodykit']]}", callback_data="cat_bodykit")],
        [InlineKeyboardButton(f"✨ Декор: {DECOR_OPTIONS[selections['decor']]}", callback_data="cat_decor")],
        [InlineKeyboardButton(f"📷 Ракурс: {ANGLE_OPTIONS[selections['angle']]}", callback_data="cat_angle")],
        [InlineKeyboardButton(f"🏙 Фон: {BACKGROUND_OPTIONS[selections['background']]}", callback_data="cat_background")],
        [InlineKeyboardButton("✏️ Индивидуальный дизайн: " + ("🎲 сюрприз" if selections.get("custom_design") == "__surprise__" else "✅ задан" if selections.get("custom_design") else "не задан"), callback_data="cat_custom_design")],
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
    if finish in ("carbon", "chrome", "camouflage", "psychedelic", "pearl"):
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
    if selections["roof"] == "maybach":
        mb_color = MAYBACH_COLOR_EN[selections.get("maybach_color", "black_gloss")]
        roof = (
            f"Maybach-style bicolor two-tone vinyl wrap: "
            f"roof panel, hood, trunk lid, and all window pillars (A/B/C) wrapped in {mb_color} vinyl. "
            f"Door panels, fenders, and bumpers remain in the original car color. "
            f"A thin elegant contrasting pinstripe accent line runs precisely along the entire boundary "
            f"between the two colors, following the body's character line. "
            f"The color separation line must be razor-sharp and clean with no blending or gradients. "
            f"This is exactly the classic Mercedes-Maybach bicolor two-tone finish."
        )
    else:
        roof = ROOF_EN[selections["roof"]]
    decor = DECOR_EN[selections["decor"]]
    background = BACKGROUND_EN[selections["background"]]
    optics = OPTICS_EN[selections["optics"]]
    bodykit = BODYKIT_EN[selections["bodykit"]]
    custom = selections.get("custom_design", "").strip()
    extras = [x for x in [optics, antichrome, mirrors, handles, roof, bodykit, decor] if x]
    if custom == "__surprise__":
        extras.append(
            "add unique creative individual design elements of your own choosing — "
            "something unexpected and original that makes this car truly one-of-a-kind, "
            "different from any previous generation"
        )
    elif custom:
        extras.append(f"custom individual design elements: {custom}")
    extras_line = f"(6) Additional details: {', '.join(extras)}. " if extras else ""
    angle = ANGLE_EN[selections["angle"]]
    angle_key = selections["angle"]
    if angle_key == "original":
        return (
            f"PHOTO RETOUCHING TASK — edit this existing car photo, do NOT generate a new car. "
            f"Preserve EVERY original detail: exact make, model, body shape, proportions, wheelbase, "
            f"door count, headlight shape, grille design, bumper contours, all body lines. "
            f"Keep the same camera angle and position as the original photo. "
            f"ONLY apply these specific changes: "
            f"(1) Body finish: {body}. "
            f"(2) Wheels: {wheels}. "
            f"(3) Rear windows: {tint}. "
            f"(4) Windshield: {windshield}. "
            f"(5) Front side windows: {sideglass}. "
            f"{extras_line}"
            f"Background: {background}. "
            f"Result must look like the SAME car with a vinyl wrap applied by a professional detailing shop. "
            f"Photorealistic quality, not illustration or CGI. 8K resolution."
        )
    else:
        return (
            f"Create a photorealistic image of the SAME car from this photo, shown from a {angle} view. "
            f"Identify this car's exact make, model, body shape, headlights, grille and all exterior details "
            f"from the input photo and reproduce them faithfully from the new angle. "
            f"Apply these modifications to the car: "
            f"(1) Body finish: {body}. "
            f"(2) Wheels: {wheels}. "
            f"(3) Rear windows: {tint}. "
            f"(4) Windshield: {windshield}. "
            f"(5) Front side windows: {sideglass}. "
            f"{extras_line}"
            f"Background: {background}. "
            f"The car must be recognizable as the exact same vehicle — same model, same proportions, "
            f"same design details, only viewed from a different angle with the listed modifications applied. "
            f"Photorealistic automotive photography, not illustration or CGI. 8K resolution."
        )


# ── Хэндлеры ──────────────────────────────────────────────────────────────────

def user_link(user) -> str:
    name = user.full_name or "Без имени"
    username = f" @{user.username}" if user.username else ""
    return f"{name}{username}"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    is_new = register_user(user_id, user)

    user_states[user_id] = {
        "photo_id": None,
        "selections": DEFAULT_SELECTIONS.copy(),
        "custom_design": "",
        "awaiting_custom_design": False,
    }

    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_") and is_new:
            try:
                referrer_id = int(arg[4:])
                process_referral(user_id, referrer_id)
                await update_user_card(context.bot, referrer_id)
                gen_info = get_generation_info(user_id)
                await update.message.reply_text(
                    f"🎁 Ты пришёл по реферальной ссылке — тебе начислено "
                    f"+{gen_info['bonus']} бонусных генераций!"
                )
            except ValueError:
                pass
        elif arg.startswith("blogger_"):
            blogger_name = arg[8:]
            blogger_track_click(blogger_name, user_id)
        elif arg.startswith("studio_") and is_new:
            studio_name = arg[7:]
            studios = _load(STUDIOS_FILE)
            if studio_name in studios and studios[studio_name]["status"] == "trial":
                set_user_studio(user_id, studio_name)
                studios[studio_name]["users_count"] = studios[studio_name].get("users_count", 0) + 1
                _save(STUDIOS_FILE, studios)

    if is_new:

        await send_user_card(context.bot, user_id)

    await update.message.reply_text(
        "👋 Привет! За пару кликов покажу как будет выглядеть твоя машина "
        "после тюнинга — меняй цвет, диски, тонировку и обвес прямо здесь.\n\n"
        "Это бесплатно и работает на AI 🤖\n\n"
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
    cost_gen, cost_usd = get_cost_stats()

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
        f"🚫 Исчерпали лимит: {exhausted}\n\n"
        f"⭐ Покупок Stars: {total_purchases} (итого {total_stars} Stars)\n\n"
        f"💸 Расходы OpenAI: {cost_gen} генераций = ${cost_usd:.2f}\n\n"
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
        f"✅ Фото получено! Доступно генераций: {info['total_left']}\n\n"
        "Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
        reply_markup=main_menu(user_states[user_id]["selections"]),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Квалификационные вопросы — не требуют user_states
    if data.startswith("qual|"):
        answer = data[5:]
        if answer == "no":
            save_lead(user_id, "no")
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
            await query.edit_message_text(
                "Окей! Если надумаешь — мы здесь 😊\n\n"
                "Пригласи друга и получи +3 генерации бесплатно 👇",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Пригласить друга", url=f"https://t.me/share/url?url={quote(ref_link)}")],
                ]),
            )
        else:
            save_lead(user_id, answer)
            await query.edit_message_text(
                "Что интересует больше всего?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎨 Оклейка плёнкой", callback_data="lead|Оклейка плёнкой")],
                    [InlineKeyboardButton("✨ Полировка кузова", callback_data="lead|Полировка кузова")],
                    [InlineKeyboardButton("🛡 Керамика", callback_data="lead|Керамика")],
                    [InlineKeyboardButton("🧹 Химчистка салона", callback_data="lead|Химчистка салона")],
                    [InlineKeyboardButton("🪟 Тонировка", callback_data="lead|Тонировка")],
                    [InlineKeyboardButton("🚿 Мойка", callback_data="lead|Мойка")],
                    [InlineKeyboardButton("🔧 Другие услуги", callback_data="lead|Другие услуги")],
                ]),
            )
        return

    if data.startswith("lead|"):
        service = data[5:]
        save_lead(user_id, "interested", service)
        await query.edit_message_text(
            "Отлично! Скоро свяжемся с тобой\n"
            "и сориентируем по стоимости услуг 😊"
        )
        await send_hot_lead(context.bot, query.from_user, service)
        return

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
    elif data == "cat_custom_design":
        user_states[user_id]["awaiting_custom_design"] = True
        current = user_states[user_id].get("custom_design", "")
        current_text = f"\n\nТекущее: «{current}»" if current and current != "__surprise__" else ""
        await query.edit_message_text(
            f"✏️ Индивидуальный дизайн{current_text}\n\n"
            f"Выбери вариант:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Удиви меня — AI придумает сам", callback_data="custom_surprise")],
                [InlineKeyboardButton("✍️ Написать своё описание", callback_data="custom_type")],
                [InlineKeyboardButton("🗑 Сбросить", callback_data="clear_custom_design")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_custom_design")],
            ]),
        )
    elif data == "custom_surprise":
        user_states[user_id]["awaiting_custom_design"] = False
        user_states[user_id]["custom_design"] = "__surprise__"
        sel["custom_design"] = "__surprise__"
        await query.edit_message_text(
            "🎲 Режим «Удиви меня» включён — AI каждый раз придумает уникальный дизайн!\n\n"
            "Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
            reply_markup=main_menu(sel),
        )
    elif data == "custom_type":
        await query.edit_message_text(
            "✍️ Напиши своё описание дизайна в чат.\n\n"
            "Например: «золотые акценты на бамперах», «граффити на капоте», «неоновая подсветка днища»",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel_custom_design")]]),
        )
    elif data == "cancel_custom_design":
        user_states[user_id]["awaiting_custom_design"] = False
        await query.edit_message_text(
            "Выбери услуги и нажми 🎨 Сгенерировать визуализацию:",
            reply_markup=main_menu(sel),
        )
    elif data == "clear_custom_design":
        user_states[user_id]["custom_design"] = ""
        user_states[user_id]["awaiting_custom_design"] = False
        sel["custom_design"] = ""
        await query.edit_message_text(
            "Индивидуальный дизайн сброшен.\nВыбери услуги и нажми 🎨 Сгенерировать визуализацию:",
            reply_markup=main_menu(sel),
        )
    elif data == "cat_maybach_color":
        await query.edit_message_text("🎨 Выбери цвет верха Майбах:", reply_markup=options_keyboard("maybach_color", MAYBACH_COLOR_OPTIONS, sel["maybach_color"]))
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
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=pkg["label"], amount=pkg["stars"])],
        )
    elif data == "generate":
        if not state.get("photo_id"):
            await query.edit_message_text("Сначала загрузи фото своей машины!", reply_markup=main_menu(sel))
            return

        info = get_generation_info(user_id)
        is_manager = user_id in MANAGER_IDS or user_id == ADMIN_ID
        if info["total_left"] <= 0 and not is_manager:
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
            await query.edit_message_text(
                f"Ты использовал все бесплатные генерации 🎨\n\n"
                f"Хочешь ещё?\n\n"
                f"⭐ 10 генераций — 75 Stars (~$1.8)\n"
                f"⭐ 25 генераций — 180 Stars (~$4.3)\n"
                f"⭐ 50 генераций — 360 Stars (~$8.6)\n\n"
                f"Или пригласи друга и получи +3 генерации бесплатно 👇",
                reply_markup=buy_keyboard(),
            )
            return

        await query.edit_message_text("⏳ Генерирую визуализацию… это займёт 30–60 секунд.")

        prompt = build_prompt(sel)
        logger.info("prompt: %s", prompt)

        try:
            photo_file = await context.bot.get_file(state["photo_id"])
            photo_data = await photo_file.download_as_bytearray()
            orig_img = Image.open(io.BytesIO(bytes(photo_data))).convert("RGB")
            photo_io = io.BytesIO()
            orig_img.save(photo_io, format="PNG")
            photo_io.seek(0)
            photo_io.name = "car.png"
            response = openai_client.images.edit(
                model="gpt-image-1",
                image=photo_io,
                prompt=prompt,
                size="1024x1024",
                quality="medium",
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

        if not is_manager:
            use_generation(user_id)
            await update_user_card(context.bot, user_id)
        else:
            track_manager_generation(user_id)
            await update_manager_card(context.bot, user_id)
        blogger_track_generation(user_id)
        track_studio_generation(user_id)
        add_generation_cost()
        info_after = get_generation_info(user_id)

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
            f"Осталось генераций: {info_after['total_left']}"
        )

        share_text = quote("Смотри как я изменил свою машину! Попробуй сам бесплатно 👇")
        ref_url = quote(f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}")
        result_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Узнать стоимость тюнинга", url="https://t.me/nicecar_center")],
            [InlineKeyboardButton("🚀 Поделиться с другом (+3 генерации)", url=f"https://t.me/share/url?url={ref_url}&text={share_text}")],
            [InlineKeyboardButton("🔄 Изменить параметры", callback_data="back_main")],
        ])

        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_bytes,
            caption=caption,
            reply_markup=result_keyboard,
        )

        if not is_manager and should_ask_qualification(user_id):
            mark_qualification_asked(user_id)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=(
                    "Кстати, хочу спросить 🙂\n\n"
                    "Твоя машина сейчас нуждается\n"
                    "в уходе?"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да, давно пора", callback_data="qual|yes")],
                    [InlineKeyboardButton("🤔 Думаю об этом", callback_data="qual|maybe")],
                    [InlineKeyboardButton("❌ Пока нет", callback_data="qual|no")],
                ]),
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
    blogger_track_purchase(user_id)
    await update_user_card(context.bot, user_id)
    info = get_generation_info(user_id)
    await update.message.reply_text(
        f"✅ Оплата прошла! Начислено {pkg['generations']} генераций.\n"
        f"Всего доступно: {info['total_left']} генераций."
    )
    try:
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=(
                f"⭐ Покупка!\n"
                f"{user_link(update.effective_user)}\n"
                f"ID: {user_id}\n"
                f"{pkg['stars']} Stars → {pkg['generations']} генераций"
            ),
        )
    except Exception as e:
        logger.error("Ошибка уведомления о покупке: %s", e)


async def cmd_add_blogger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: /add_blogger [имя]\nПример: /add_blogger ivan")
        return
    name = context.args[0].lower()
    data = _load(BLOGGERS_FILE)
    if name in data:
        await update.message.reply_text(f"Блогер '{name}' уже существует.")
        return
    data[name] = {"created": str(date.today()), "clicks": [], "generated": [], "purchased": []}
    _save(BLOGGERS_FILE, data)
    link = f"https://t.me/{BOT_USERNAME}?start=blogger_{name}"
    await update.message.reply_text(f"✅ Ссылка для {name}:\n{link}")


async def cmd_blogger_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    data = _load(BLOGGERS_FILE)
    if not data:
        await update.message.reply_text("Блогеров пока нет. Добавь через /add_blogger [имя]")
        return
    lines = ["📊 Статистика по блогерам\n"]
    for name, info in data.items():
        lines.append(
            f"👤 {name}\n"
            f"  Переходов: {len(info.get('clicks', []))}\n"
            f"  Генерировали: {len(info.get('generated', []))}\n"
            f"  Купили Stars: {len(info.get('purchased', []))}\n"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    admin_state[ADMIN_ID] = "awaiting_broadcast"
    await update.message.reply_text(
        "📢 Введи текст рассылки.\n\n"
        "Можно использовать *жирный*, _курсив_, ссылки.\n"
        "Для отмены напиши /cancel"
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    admin_state.pop(ADMIN_ID, None)
    await update.message.reply_text("Отменено.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Ввод индивидуального дизайна
    if user_states.get(user_id, {}).get("awaiting_custom_design"):
        text = update.message.text.strip()
        user_states[user_id]["awaiting_custom_design"] = False
        user_states[user_id]["custom_design"] = text
        user_states[user_id]["selections"]["custom_design"] = text
        await update.message.reply_text(
            f"✅ Индивидуальный дизайн сохранён:\n«{text}»\n\nТеперь нажми 🎨 Сгенерировать визуализацию.",
            reply_markup=main_menu(user_states[user_id]["selections"]),
        )
        return

    if user_id != ADMIN_ID or admin_state.get(ADMIN_ID) != "awaiting_broadcast":
        return
    admin_state.pop(ADMIN_ID, None)
    text = update.message.text
    users = _load(USERS_FILE)
    total = len(users)
    sent = 0
    failed = 0
    await update.message.reply_text(f"⏳ Начинаю рассылку {total} пользователям…")
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text, parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"✅ Рассылка завершена!\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed} (заблокировали бота)"
    )


async def cmd_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /trial [название] [telegram_id]\nПример: /trial topcar_moscow 123456789")
        return
    name = context.args[0].lower()
    try:
        telegram_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Ошибка: telegram_id должен быть числом")
        return
    studios = _load(STUDIOS_FILE)
    if name in studios:
        await update.message.reply_text(f"Студия '{name}' уже существует.")
        return
    studio = create_studio(name, telegram_id)
    link = f"https://t.me/{BOT_USERNAME}?start=studio_{name}"
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=(
                f"🎉 Добро пожаловать в NICECAR Tuning!\n\n"
                f"Ваш пробный период активирован:\n"
                f"📅 5 дней\n"
                f"🎨 150 генераций\n"
                f"🔗 Ваша ссылка:\n{link}\n\n"
                f"Лиды будут приходить вам в этот чат автоматически.\n"
                f"По вопросам — @maxlipai"
            ),
        )
        await context.bot.send_message(
            chat_id=telegram_id,
            text="Чтобы получать лиды убедитесь что ваш Telegram ID правильный.\nПроверить свой ID: @userinfobot",
        )
    except Exception as e:
        logger.error("Ошибка отправки студии: %s", e)
    await update.message.reply_text(
        f"✅ Студия '{name}' создана!\n"
        f"Период: {studio['start_date']} — {studio['end_date']}\n"
        f"Ссылка: {link}"
    )


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    studio = get_studio_by_owner(user_id)
    if not studio:
        return
    await update.message.reply_text(
        f"📊 Ваша статистика — {studio['name']}\n\n"
        f"👥 Пользователей по вашей ссылке: {studio.get('users_count', 0)}\n"
        f"💡 Лидов получено: {studio.get('leads_count', 0)}\n"
        f"🎨 Генераций использовано: {studio.get('used', 0)} из {studio['limit']}\n"
        f"📅 Осталось дней: {max(0, studio_days_left(studio))}"
    )


async def cmd_mylink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    studio = get_studio_by_owner(user_id)
    if not studio:
        return
    link = f"https://t.me/{BOT_USERNAME}?start=studio_{studio['name']}"
    await update.message.reply_text(f"🔗 Ваша ссылка:\n{link}")


async def daily_studio_job(context) -> None:
    import pytz
    studios = _load(STUDIOS_FILE)
    active_lines = []
    for name, studio in list(studios.items()):
        if studio["status"] != "trial":
            continue
        elapsed = studio_days_elapsed(studio)
        tid = studio["telegram_id"]
        used = studio.get("used", 0)
        leads = studio.get("leads_count", 0)
        limit = studio["limit"]
        if elapsed == 3:
            try:
                await context.bot.send_message(chat_id=tid, text=(
                    f"⏰ Осталось 2 дня пробного периода.\n"
                    f"Использовано {used} из {limit} генераций.\n"
                    f"Получено лидов: {leads}\n\n"
                    f"Хотите продолжить?\nНапишите нам: @maxlipai"
                ))
            except Exception as e:
                logger.error("Ошибка напоминания студии %s: %s", name, e)
        elif elapsed == 5:
            try:
                await context.bot.send_message(chat_id=tid, text=(
                    f"⚠️ Пробный период заканчивается завтра!\n"
                    f"Использовано {used} из {limit} генераций.\n"
                    f"Получено лидов: {leads}\n\n"
                    f"Выберите пакет чтобы продолжить:\n"
                    f"⭐ Старт — $99/мес (100 клиентов)\n"
                    f"⭐ Бизнес — $199/мес (250 клиентов)\n"
                    f"⭐ Про — $399/мес (500 клиентов)\n\n"
                    f"Написать менеджеру: @maxlipai"
                ))
            except Exception as e:
                logger.error("Ошибка напоминания студии %s: %s", name, e)
        elif elapsed >= 6:
            studios[name]["status"] = "expired"
            _save(STUDIOS_FILE, studios)
            try:
                await context.bot.send_message(chat_id=tid, text=(
                    "❌ Пробный период завершён.\nДля продолжения напишите: @maxlipai"
                ))
            except Exception as e:
                logger.error("Ошибка уведомления о конце триала %s: %s", name, e)
            continue
        active_lines.append(f"- {name}: день {elapsed}/5, использовано {used} генераций, лидов: {leads}")
    if active_lines:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="📊 Активные триалы:\n" + "\n".join(active_lines),
            )
        except Exception as e:
            logger.error("Ошибка отчёта админу: %s", e)


async def cmd_test_qual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "Кстати, хочу спросить 🙂\n\n"
        "Твоя машина сейчас нуждается\n"
        "в уходе?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, давно пора", callback_data="qual|yes")],
            [InlineKeyboardButton("🤔 Думаю об этом", callback_data="qual|maybe")],
            [InlineKeyboardButton("❌ Пока нет", callback_data="qual|no")],
        ]),
    )


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Chat ID: `{update.effective_chat.id}`", parse_mode="Markdown")


# ── Запуск ────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("referral", cmd_referral))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("add_blogger", cmd_add_blogger))
    app.add_handler(CommandHandler("blogger_stats", cmd_blogger_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("test_qual", cmd_test_qual))
    app.add_handler(CommandHandler("trial", cmd_trial))
    app.add_handler(CommandHandler("mystats", cmd_mystats))
    app.add_handler(CommandHandler("mylink", cmd_mylink))

    import pytz
    from datetime import time as dtime
    tz = pytz.timezone("Europe/Minsk")
    app.job_queue.run_daily(daily_studio_job, time=dtime(9, 0, tzinfo=tz))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
