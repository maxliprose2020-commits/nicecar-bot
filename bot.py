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

# ── Варианты на русском ────────────────────────────────────────────────────────

BODY_OPTIONS = {
    "matte_original":  "Матовый (без смены цвета)",
    "black_matte":     "Чёрный матт",
    "white_matte":     "Белый матт",
    "grey_matte":      "Серый матт",
    "blue_matte":      "Синий матт",
    "red_matte":       "Красный матт",
    "green_matte":     "Зелёный матт",
    "carbon":          "Карбон",
    "chrome":          "Хром",
    "camouflage":      "Камуфляж",
}

WHEELS_OPTIONS = {
    "original":     "Оставить как есть",
    "black_matte":  "Чёрные матт",
    "black_gloss":  "Чёрные глянец",
    "white":        "Белые",
    "gold":         "Золотые",
    "grey":         "Серые",
}

TINT_OPTIONS = {
    "none":   "Без тонировки",
    "light":  "Лёгкая",
    "medium": "Средняя",
    "dark":   "Тёмная",
}

FRONTGLASS_OPTIONS = {
    "standard":  "Стандартное",
    "athermal":  "Атермальная плёнка",
    "chameleon": "Хамелеон",
    "sea_wave":  "Морская волна",
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
    "matte_original":  "matte finish keeping the original color",
    "black_matte":     "matte black vinyl wrap",
    "white_matte":     "matte white vinyl wrap",
    "grey_matte":      "matte grey vinyl wrap",
    "blue_matte":      "matte blue vinyl wrap",
    "red_matte":       "matte red vinyl wrap",
    "green_matte":     "matte green vinyl wrap",
    "carbon":          "carbon fiber vinyl wrap",
    "chrome":          "chrome vinyl wrap",
    "camouflage":      "camouflage vinyl wrap",
}

WHEELS_EN = {
    "original":     "original stock wheels",
    "black_matte":  "matte black wheels",
    "black_gloss":  "glossy black wheels",
    "white":        "white wheels",
    "gold":         "gold wheels",
    "grey":         "grey wheels",
}

TINT_EN = {
    "none":   "clear rear windows with no tint",
    "light":  "lightly tinted rear windows",
    "medium": "medium tinted rear windows",
    "dark":   "heavily tinted rear windows",
}

FRONTGLASS_EN = {
    "standard":  "clear standard front windshield",
    "athermal":  "athermal heat-rejection film on front windows",
    "chameleon": "chameleon iridescent color-shifting film on front windows",
    "sea_wave":  "sea wave blue-green tinted film on front windows",
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

BACKGROUND_EN = {
    "night_city":  "night city with neon lights and bokeh",
    "mountains":   "scenic mountain landscape",
    "track":       "racing track",
    "underground": "underground parking with dramatic lighting",
    "dubai":       "Dubai skyline at sunset",
    "minsk":       "Minsk city center Belarus",
}

DEFAULT_SELECTIONS = {
    "body":        "black_matte",
    "wheels":      "original",
    "tint":        "none",
    "frontglass":  "standard",
    "antichrome":  "none",
    "bodykit":     "none",
    "decor":       "none",
    "background":  "night_city",
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
            f"🎨 Кузов: {BODY_OPTIONS[selections['body']]}",
            callback_data="cat_body",
        )],
        [InlineKeyboardButton(
            f"💿 Диски: {WHEELS_OPTIONS[selections['wheels']]}",
            callback_data="cat_wheels",
        )],
        [InlineKeyboardButton(
            f"🪟 Тонировка задних: {TINT_OPTIONS[selections['tint']]}",
            callback_data="cat_tint",
        )],
        [InlineKeyboardButton(
            f"🌈 Передние стёкла: {FRONTGLASS_OPTIONS[selections['frontglass']]}",
            callback_data="cat_frontglass",
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
            f"🏙 Фон: {BACKGROUND_OPTIONS[selections['background']]}",
            callback_data="cat_background",
        )],
        [InlineKeyboardButton("🎨 Сгенерировать визуализацию", callback_data="generate")],
    ])


def options_keyboard(category: str, options: dict, current: str) -> InlineKeyboardMarkup:
    rows = []
    for key, name in options.items():
        prefix = "✅ " if key == current else ""
        rows.append([InlineKeyboardButton(f"{prefix}{name}", callback_data=f"sel_{category}_{key}")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


# ── Промпт ────────────────────────────────────────────────────────────────────

def build_prompt(selections: dict) -> str:
    body = BODY_EN[selections["body"]]
    wheels = WHEELS_EN[selections["wheels"]]
    tint = TINT_EN[selections["tint"]]
    frontglass = FRONTGLASS_EN[selections["frontglass"]]
    antichrome = ANTICHROME_EN[selections["antichrome"]]
    decor = DECOR_EN[selections["decor"]]
    background = BACKGROUND_EN[selections["background"]]

    bodykit = BODYKIT_EN[selections["bodykit"]]
    extras = [x for x in [antichrome, bodykit, decor] if x]
    extras_text = (", " + ", ".join(extras)) if extras else ""

    return (
        f"Edit this car: apply {body}, change wheels to {wheels}, "
        f"{tint}, {frontglass}{extras_text}, "
        f"place the car in {background}. "
        f"Keep the exact same car model, shape and camera angle. "
        f"Photorealistic, 4K, professional automotive photography."
    )


# ── Хэндлеры ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_states[user_id] = {
        "photo_id": None,
        "selections": DEFAULT_SELECTIONS.copy(),
    }
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
            "🎨 Выбери покрытие кузова:",
            reply_markup=options_keyboard("body", BODY_OPTIONS, sel["body"]),
        )
    elif data == "cat_wheels":
        await query.edit_message_text(
            "💿 Выбери цвет дисков:",
            reply_markup=options_keyboard("wheels", WHEELS_OPTIONS, sel["wheels"]),
        )
    elif data == "cat_tint":
        await query.edit_message_text(
            "🪟 Тонировка задних стёкол:",
            reply_markup=options_keyboard("tint", TINT_OPTIONS, sel["tint"]),
        )
    elif data == "cat_frontglass":
        await query.edit_message_text(
            "🌈 Передние стёкла:",
            reply_markup=options_keyboard("frontglass", FRONTGLASS_OPTIONS, sel["frontglass"]),
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
    elif data == "cat_background":
        await query.edit_message_text(
            "🏙 Выбери фон:",
            reply_markup=options_keyboard("background", BACKGROUND_OPTIONS, sel["background"]),
        )
    elif data.startswith("sel_"):
        _, category, key = data.split("_", 2)
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

        caption = (
            "✨ Визуализация готова!\n\n"
            f"🎨 {BODY_OPTIONS[sel['body']]}\n"
            f"💿 {WHEELS_OPTIONS[sel['wheels']]}  •  🪟 {TINT_OPTIONS[sel['tint']]}\n"
            f"🌈 {FRONTGLASS_OPTIONS[sel['frontglass']]}\n"
            f"⚫ {ANTICHROME_OPTIONS[sel['antichrome']]}  •  🏎 {BODYKIT_OPTIONS[sel['bodykit']]}\n"
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
