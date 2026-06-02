Read 1 file (ctrl+o to expand)

● Иди в GitHub → nicecar-bot → нажми на bot.py → карандаш ✏️ → выдели всё
  (Ctrl+A) → удали → вставь этот код:

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

  COLOR_OPTIONS = {
      "black_matte":  "Чёрный матт",
      "white_gloss":  "Белый глянец",
      "grey_matte":   "Серый матт",
      "blue_chrome":  "Синий хром",
      "red_gloss":    "Красный глянец",
      "green_matte":  "Зелёный матт",
      "gold_chrome":  "Золотой хром",
      "orange_matte": "Оранжевый матт",
  }

  FILM_OPTIONS = {
      "matte":       "Матовая",
      "gloss":       "Глянцевая",
      "chrome":      "Хром",
      "carbon":      "Карбон",
      "camo":        "Камуфляж",
      "psychedelic": "Психоделика",
  }

  WHEELS_OPTIONS = {
      "black":    "Чёрные",
      "silver":   "Серебристые",
      "gold":     "Золотые",
      "chrome":   "Хром",
      "original": "Оставить как есть",
  }

  TINT_OPTIONS = {
      "none":   "Без тонировки",
      "light":  "Лёгкая",
      "medium": "Средняя",
      "dark":   "Тёмная",
  }

  BACKGROUND_OPTIONS = {
      "night_city":  "Ночной город",
      "mountains":   "Горы",
      "track":       "Трасса",
      "underground": "Подземный паркинг",
      "dubai":       "Дубай",
      "minsk":       "Минск",
  }

  COLOR_EN = {
      "black_matte":  "matte black",
      "white_gloss":  "glossy white",
      "grey_matte":   "matte grey",
      "blue_chrome":  "chrome blue",
      "red_gloss":    "glossy red",
      "green_matte":  "matte green",
      "gold_chrome":  "chrome gold",
      "orange_matte": "matte orange",
  }

  FILM_EN = {
      "matte":       "matte vinyl",
      "gloss":       "glossy vinyl",
      "chrome":      "chrome vinyl",
      "carbon":      "carbon fiber vinyl",
      "camo":        "camouflage vinyl",
      "psychedelic": "psychedelic holographic vinyl",
  }

  WHEELS_EN = {
      "black":    "black",
      "silver":   "silver",
      "gold":     "gold",
      "chrome":   "chrome",
      "original": "stock original",
  }

  TINT_EN = {
      "none":   "clear windows with no tint",
      "light":  "lightly tinted windows",
      "medium": "medium tinted windows",
      "dark":   "heavily tinted windows",
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
      "color":      "black_matte",
      "film":       "matte",
      "wheels":     "black",
      "tint":       "none",
      "background": "night_city",
  }

  user_states: dict[int, dict] = {}


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


  def main_menu(selections: dict) -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [InlineKeyboardButton(
              f"🎨 Цвет: {COLOR_OPTIONS[selections['color']]}",
              callback_data="cat_color",
          )],
          [InlineKeyboardButton(
              f"🖤 Плёнка: {FILM_OPTIONS[selections['film']]}",
              callback_data="cat_film",
          )],
          [InlineKeyboardButton(
              f"💿 Диски: {WHEELS_OPTIONS[selections['wheels']]}",
              callback_data="cat_wheels",
          )],
          [InlineKeyboardButton(
              f"🪟 Тонировка: {TINT_OPTIONS[selections['tint']]}",
              callback_data="cat_tint",
          )],
          [InlineKeyboardButton(
              f"🏙 Фон: {BACKGROUND_OPTIONS[selections['background']]}",
              callback_data="cat_background",
          )],
          [InlineKeyboardButton("✨ Сгенерировать",
  callback_data="generate")],
      ])


  def options_keyboard(category: str, options: dict, current: str) ->
  InlineKeyboardMarkup:
      rows = []
      for key, name in options.items():
          prefix = "✅ " if key == current else ""
          rows.append([InlineKeyboardButton(f"{prefix}{name}",
  callback_data=f"sel_{category}_{key}")])
      rows.append([InlineKeyboardButton("◀️ Назад",
  callback_data="back_main")])
      return InlineKeyboardMarkup(rows)


  def build_prompt(selections: dict) -> str:
      color = COLOR_EN[selections["color"]]
      film = FILM_EN[selections["film"]]
      wheels = WHEELS_EN[selections["wheels"]]
      tint = TINT_EN[selections["tint"]]
      background = BACKGROUND_EN[selections["background"]]
      return (
          f"Realistic professional photo of a car fully wrapped in {color}
  {film}, "
          f"{wheels} wheels, {tint}, parked in {background}. "
          f"Photorealistic, 4K, professional automotive photography, studio
  lighting, "
          f"sharp details, high contrast"
      )


  async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) ->
   None:
      user_id = update.effective_user.id
      user_states[user_id] = {
          "photo_id": None,
          "selections": DEFAULT_SELECTIONS.copy(),
      }
      await update.message.reply_text(
          "👋 Привет! Я помогу тебе представить, как будет выглядеть твой
  автомобиль "
          "после тюнинга в Найскар Центр.\n\n"
          "📸 Загрузи фото своей машины — и начнём!"
      )


  async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE)
   -> None:
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
          f"Осталось генераций сегодня: {remaining} из
  {MAX_GENERATIONS}\n\n"
          "Выбери параметры тюнинга и нажми ✨ Сгенерировать:",
          reply_markup=main_menu(user_states[user_id]["selections"]),
      )


  async def handle_callback(update: Update, context:
  ContextTypes.DEFAULT_TYPE) -> None:
      query = update.callback_query
      await query.answer()
      user_id = query.from_user.id
      data = query.data

      if user_id not in user_states:
          await query.edit_message_text("Пожалуйста, начни сначала — отправь
   команду /start")
          return

      state = user_states[user_id]
      sel = state["selections"]

      if data == "cat_color":
          await query.edit_message_text(
              "🎨 Выбери цвет кузова:",
              reply_markup=options_keyboard("color", COLOR_OPTIONS,
  sel["color"]),
          )
      elif data == "cat_film":
          await query.edit_message_text(
              "🖤 Выбери тип плёнки:",
              reply_markup=options_keyboard("film", FILM_OPTIONS,
  sel["film"]),
          )
      elif data == "cat_wheels":
          await query.edit_message_text(
              "💿 Выбери диски:",
              reply_markup=options_keyboard("wheels", WHEELS_OPTIONS,
  sel["wheels"]),
          )
      elif data == "cat_tint":
          await query.edit_message_text(
              "🪟 Выбери тонировку:",
              reply_markup=options_keyboard("tint", TINT_OPTIONS,
  sel["tint"]),
          )
      elif data == "cat_background":
          await query.edit_message_text(
              "🏙 Выбери фон:",
              reply_markup=options_keyboard("background",
  BACKGROUND_OPTIONS, sel["background"]),
          )
      elif data.startswith("sel_"):
          _, category, key = data.split("_", 2)
          sel[category] = key
          await query.edit_message_text(
              "Параметры тюнинга — выбери что нужно и нажми ✨
  Сгенерировать:",
              reply_markup=main_menu(sel),
          )
      elif data == "back_main":
          if query.message.photo:
              await context.bot.send_message(
                  chat_id=query.message.chat_id,
                  text="Параметры тюнинга — выбери что нужно и нажми ✨
  Сгенерировать:",
                  reply_markup=main_menu(sel),
              )
          else:
              await query.edit_message_text(
                  "Параметры тюнинга — выбери что нужно и нажми ✨
  Сгенерировать:",
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
                  f"Ты использовал {MAX_GENERATIONS} бесплатных генераций на
   сегодня.\n\n"
                  "Напиши нам в @nicecar_center для получения дополнительных
   генераций 🚗"
              )
              return

          await query.edit_message_text("⏳ Генерирую изображение… это
  займёт 30–60 секунд.")

          prompt = build_prompt(sel)
          logger.info("prompt: %s", prompt)

          try:
              response = openai_client.images.generate(
                  model="gpt-image-1",
                  prompt=prompt,
                  size="1024x1024",
                  n=1,
              )
              image_bytes =
  io.BytesIO(base64.b64decode(response.data[0].b64_json))
          except Exception as exc:
              logger.error("OpenAI error: %s", exc)
              await context.bot.send_message(
                  chat_id=query.message.chat_id,
                  text="❌ Ошибка при генерации. Попробуй ещё раз или напиши
   @nicecar_center",
              )
              return

          increment_user_generations(user_id)
          remaining = MAX_GENERATIONS - get_user_generations(user_id)

          caption = (
              "✨ Вот твоя машина в новом стиле!\n\n"
              f"🎨 {COLOR_OPTIONS[sel['color']]}  •  🖤
  {FILM_OPTIONS[sel['film']]}\n"
              f"💿 {WHEELS_OPTIONS[sel['wheels']]}  •  🪟
  {TINT_OPTIONS[sel['tint']]}\n"
              f"🏙 {BACKGROUND_OPTIONS[sel['background']]}\n\n"
              f"Осталось генераций сегодня: {remaining} из
  {MAX_GENERATIONS}"
          )

          result_keyboard = InlineKeyboardMarkup([
              [InlineKeyboardButton("🚗 Заказать в Найскар Центр",
  url="https://t.me/nicecar_center")],
              [InlineKeyboardButton("🔄 Изменить параметры",
  callback_data="back_main")],
          ])

          await context.bot.send_photo(
              chat_id=query.message.chat_id,
              photo=image_bytes,
              caption=caption,
              reply_markup=result_keyboard,
          )


  def main() -> None:
      app = Application.builder().token(TELEGRAM_TOKEN).build()
      app.add_handler(CommandHandler("start", cmd_start))
      app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
      app.add_handler(CallbackQueryHandler(handle_callback))
      logger.info("Бот запущен")
      app.run_polling(drop_pending_updates=True)


  if __name__ == "__main__":
      main()
