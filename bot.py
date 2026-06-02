import os
import io
import base64
import json
import logging
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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

openai_client = OpenAI(api_key=OPENAI_API_KEY)

COUNTERS_FILE = "counters.json"
MAX_GENERATIONS = 5
OWNER_CHAT_ID = 862676483

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
    "matte":      "Матт",
    "gloss":      "Глянец",
    "satin":      "Сатин",
    "carbon":     "Карбон",
    "chrome":     "Хром",
    "camouflage": "Камуфляж",
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
    "matte":      "matte vinyl wrap",
    "gloss":      "gloss vinyl wrap",
    "satin":      "satin vinyl wrap",
    "carbon":     "carbon fiber vinyl wrap",
    "chrome":     "chrome vinyl wrap",
    "camouflage": "camouflage vinyl wrap",
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
    "none":        "",
    "gloss_black": "all chrome trim replaced with gloss black vinyl chrome delete",
    "matte_black": "all chrome trim replaced with matte black vinyl chrome delete",
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
    "bodykit":      "none",
    "decor":        "none",
    "angle":        "original",
    "background":   "night_city",
}

# user_id → {"photo_id": str | None, "selections": dict}
user_states: dict[int, dict] = {}


# ── Счётчики генераций ─────────────────────────────────────────────────────────

def load_counters() -> dict:
    if os.path.exists(COUNTERS_FILE):
        with open(COUNTERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_counters(counters: dict) -> None:
    with open(COUNTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(counters, f)


def get_user_generations(user_id: int) -> int:
    counters = load_counters()
    today = str(date.today())
    key = str(user_id)
    if key not in counters or counters[key]["date"] != today:
        return 0
    return counters[key]["count"]


def increment_user_generations(user_id: int) -> None:
    counters = load_counters()
    today = str(date.today())
    key = str(user_id)
    if key not in counters or counters[key]["date"] != today:
        counters[key] = {"date": today, "count": 0}
    counters[key]["count"] += 1
    save_counters(counters)


# ── Клавиатуры ────────────────────────────────────────────────────────────────

def main_menu(selections: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🎨 Цвет кузова: {BODY_OPTIONS[selections['body']]}",
            callback_data="cat_body",
        )],
        [InlineKeyboardButton(
            f"🔲 Покрытие: {FINISH_OPTIONS[selections['finish']]}",
            callback_data="cat_finish",
        )],
        [InlineKeyboardButton(
            f"💿 Диски: {WHEELS_OPTIONS[selections['wheels']]}",
            callback_data="cat_wheels",
        )],
        [InlineKeyboardButton(
            f"⚙️ Радиус: {WHEELS_SIZE_OPTIONS[selections['wheels_size']]}",
            callback_data="cat_wheels_size",
        )],
        [InlineKeyboardButton(
            f"🪟 Тонировка задних: {TINT_OPTIONS[selections['tint']]}",
            callback_data="cat_tint",
        )],
        [InlineKeyboardButton(
            f"🔵 Лобовое стекло: {WINDSHIELD_OPTIONS[selections['windshield']]}",
            callback_data="cat_windshield",
        )],
        [InlineKeyboardButton(
            f"🌊 Боковые передние: {SIDEGLASS_OPTIONS[selections['sideglass']]}",
            callback_data="cat_sideglass",
        )],
        [InlineKeyboardButton(
            f"💡 Оптика: {OPTICS_OPTIONS[selections['optics']]}",
            callback_data="cat_optics",
        )],
        [InlineKeyboardButton(
            f"⚫ Антихром: {ANTICHROME_OPTIONS[selections['antichrome']]}",
            callback_data="cat_antichrome",
        )],
        [InlineKeyboardButton(
            f"🏎 Обвес: {BODYKIT_OPTIONS[selections['bodykit']]}",
            callback_data="cat_bodykit",
        )],
        [InlineKeyboardButton(
            f"✨ Декор: {DECOR_OPTIONS[selections['decor']]}",
            callback_data="cat_decor",
        )],
        [InlineKeyboardButton(
            f"📷 Ракурс: {ANGLE_OPTIONS[selections['angle']]}",
            callback_data="cat_angle",
        )],
        [InlineKeyboardButton(
            f"🏙 Фон: {BACKGROUND_OPTIONS[selections['background']]}",
            callback_data="cat_background",
        )],
        [InlineKeyboardButton("🎨 Сгенерировать визуализацию", callback_data="generate")],
    ])


def options_keyboard(category: str, options: dict, current: str) -> InlineKeyboardMarkup:
    rows = []
    for key, name in options.items():
        prefix = "✅ " if key == current else ""
        rows.append([InlineKeyboardButton(f"{prefix}{name}", callback_data=f"sel|{category}|{key}")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


# ── Промпт ────────────────────────────────────────────────────────────────────

def build_prompt(selections: dict) -> str:
    finish = selections["finish"]
    color = BODY_EN[selections["body"]]
    if finish in ("carbon", "chrome", "camouflage"):
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
    decor = DECOR_EN[selections["decor"]]
    background = BACKGROUND_EN[selections["background"]]

    optics = OPTICS_EN[selections["optics"]]
    bodykit = BODYKIT_EN[selections["bodykit"]]
    extras = [x for x in [optics, antichrome, bodykit, decor] if x]
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
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=text)
    except Exception as e:
        logger.error("Ошибка отправки уведомления: %s", e)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_new = user_id not in user_states
    user_states[user_id] = {
        "photo_id": None,
        "selections": DEFAULT_SELECTIONS.copy(),
    }
    if is_new:
        await notify_owner(
            context,
            f"👤 Новый пользователь запустил бота:\n"
            f"{user_link(update.effective_user)}\n"
            f"ID: {user_id}"
        )
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе представить, как будет выглядеть твой автомобиль "
        "после тюнинга в Найскар Центр.\n\n"
        "📸 Загрузи фото своей машины — и начнём!"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_states:
        user_states[user_id] = {
            "photo_id": None,
            "selections": DEFAULT_SELECTIONS.copy(),
        }
    user_states[user_id]["photo_id"] = update.message.photo[-1].file_id
    remaining = MAX_GENERATIONS - get_user_generations(user_id)
    await update.message.reply_text(
        f"✅ Фото получено!\n"
        f"Осталось генераций сегодня: {remaining} из {MAX_GENERATIONS}\n\n"
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
        await query.edit_message_text(
            "🎨 Выбери цвет кузова:",
            reply_markup=options_keyboard("body", BODY_OPTIONS, sel["body"]),
        )
    elif data == "cat_finish":
        await query.edit_message_text(
            "🔲 Выбери тип покрытия:",
            reply_markup=options_keyboard("finish", FINISH_OPTIONS, sel["finish"]),
        )
    elif data == "cat_wheels":
        await query.edit_message_text(
            "💿 Выбери цвет дисков:",
            reply_markup=options_keyboard("wheels", WHEELS_OPTIONS, sel["wheels"]),
        )
    elif data == "cat_wheels_size":
        await query.edit_message_text(
            "⚙️ Выбери радиус дисков:",
            reply_markup=options_keyboard("wheels_size", WHEELS_SIZE_OPTIONS, sel["wheels_size"]),
        )
    elif data == "cat_tint":
        await query.edit_message_text(
            "🪟 Тонировка задних стёкол:",
            reply_markup=options_keyboard("tint", TINT_OPTIONS, sel["tint"]),
        )
    elif data == "cat_windshield":
        await query.edit_message_text(
            "🔵 Лобовое стекло — выбери плёнку:",
            reply_markup=options_keyboard("windshield", WINDSHIELD_OPTIONS, sel["windshield"]),
        )
    elif data == "cat_sideglass":
        await query.edit_message_text(
            "🌊 Передние боковые стёкла — выбери плёнку:",
            reply_markup=options_keyboard("sideglass", SIDEGLASS_OPTIONS, sel["sideglass"]),
        )
    elif data == "cat_optics":
        await query.edit_message_text(
            "💡 Тонировка оптики (фары и фонари):",
            reply_markup=options_keyboard("optics", OPTICS_OPTIONS, sel["optics"]),
        )
    elif data == "cat_antichrome":
        await query.edit_message_text(
            "⚫ Антихром — оклейка хромированных деталей:",
            reply_markup=options_keyboard("antichrome", ANTICHROME_OPTIONS, sel["antichrome"]),
        )
    elif data == "cat_bodykit":
        await query.edit_message_text(
            "🏎 Выбери обвес:",
            reply_markup=options_keyboard("bodykit", BODYKIT_OPTIONS, sel["bodykit"]),
        )
    elif data == "cat_decor":
        await query.edit_message_text(
            "✨ Декоративные элементы:",
            reply_markup=options_keyboard("decor", DECOR_OPTIONS, sel["decor"]),
        )
    elif data == "cat_angle":
        await query.edit_message_text(
            "📷 Выбери ракурс:",
            reply_markup=options_keyboard("angle", ANGLE_OPTIONS, sel["angle"]),
        )
    elif data == "cat_background":
        await query.edit_message_text(
            "🏙 Выбери фон:",
            reply_markup=options_keyboard("background", BACKGROUND_OPTIONS, sel["background"]),
        )
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
    elif data == "generate":
        if not state.get("photo_id"):
            await query.edit_message_text(
                "Сначала загрузи фото своей машины!",
                reply_markup=main_menu(sel),
            )
            return

        gens = get_user_generations(user_id)
        if gens >= MAX_GENERATIONS:
            await query.edit_message_text(
                f"Ты использовал {MAX_GENERATIONS} бесплатных визуализаций на сегодня.\n\n"
                "Напиши нам в @nicecar_center для получения дополнительных генераций 🚗"
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
            image_bytes = io.BytesIO(base64.b64decode(response.data[0].b64_json))
        except Exception as exc:
            logger.error("OpenAI error: %s", exc)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ошибка при генерации. Попробуй ещё раз или напиши @nicecar_center",
            )
            return

        increment_user_generations(user_id)
        remaining = MAX_GENERATIONS - get_user_generations(user_id)

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
            f"🏎 {BODYKIT_OPTIONS[sel['bodykit']]}\n"
            f"✨ {DECOR_OPTIONS[sel['decor']]}\n\n"
            f"Осталось генераций сегодня: {remaining} из {MAX_GENERATIONS}"
        )

        result_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚗 Получить консультацию в Найскар Центр по внешнему виду", url="https://t.me/nicecar_center")],
            [InlineKeyboardButton("🔄 Изменить параметры", callback_data="back_main")],
        ])

        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_bytes,
            caption=caption,
            reply_markup=result_keyboard,
        )


# ── Запуск ────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
