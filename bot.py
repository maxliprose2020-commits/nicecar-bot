import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8796093456:AAGyivhIUsJq9tzQyBkeibej_5dTQ5RZsE8"
SPREADSHEET_ID = "1lNQv77MIRLZOi6u9Hy_lenXAw0NQ0LQT2GExeuXOcDs"
SERVICE_ACCOUNT_FILE = "credentials.json"
MIN_CORRECT = 2

def get_sheet(name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(name)

def get_lesson(lesson_id):
    sheet = get_sheet("content")
    for row in sheet.get_all_records():
        if str(row["id"]) == str(lesson_id):
            return row
    return None

def get_progress(telegram_id):
    sheet = get_sheet("progress")
    records = sheet.get_all_records()
    for i, row in enumerate(records):
        if str(row["telegram_id"]) == str(telegram_id):
            return row, i + 2
    return None, None

def save_progress(telegram_id, name, current_lesson, passed_lessons, status="active"):
    sheet = get_sheet("progress")
    record, row_num = get_progress(telegram_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if record is None:
        sheet.append_row([str(telegram_id), name, current_lesson, passed_lessons, now, status])
    else:
        sheet.update(f"A{row_num}:F{row_num}", [[str(telegram_id), name, current_lesson, passed_lessons, now, status]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    progress, _ = get_progress(user.id)
    if progress is None:
        save_progress(user.id, user.full_name, 1, "", "active")
        current_lesson = 1
    else:
        current_lesson = int(progress["current_lesson"])

    keyboard = [[InlineKeyboardButton("▶️ Начать обучение", callback_data=f"lesson_{current_lesson}")]]
    await update.message.reply_text(
        f"Привет, {user.full_name}!\n\n"
        f"Добро пожаловать в систему обучения NiceCar Training.\n\n"
        f"Ты будешь поэтапно изучать технику оклейки PPF.\n"
        f"После каждого видео — тест из 3 вопросов.\n"
        f"Минимум 2 правильных ответа — и следующий урок открыт.\n\n"
        f"Твой текущий урок: {current_lesson}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_lesson(query, lesson_id):
    lesson = get_lesson(lesson_id)
    if lesson is None:
        await query.message.reply_text(
            "Поздравляем! Ты прошёл весь курс!\n\nТы настоящий мастер PPF!"
        )
        return
    keyboard = [[InlineKeyboardButton("✅ Видео просмотрено, начать тест", callback_data=f"test_{lesson_id}_1")]]
    await query.message.reply_text(
        f"Урок {lesson['id']}: {lesson['topic']}\n\n"
        f"Посмотри видео, затем пройди тест.\n\n"
        f"{lesson['video_url']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_question(query, lesson_id, q_num):
    lesson = get_lesson(lesson_id)
    question = lesson[f"q{q_num}"]
    a = lesson[f"q{q_num}_a"]
    b = lesson[f"q{q_num}_b"]
    c = lesson[f"q{q_num}_c"]
    keyboard = [
        [InlineKeyboardButton(f"A) {a}", callback_data=f"ans_{lesson_id}_{q_num}_a")],
        [InlineKeyboardButton(f"B) {b}", callback_data=f"ans_{lesson_id}_{q_num}_b")],
        [InlineKeyboardButton(f"C) {c}", callback_data=f"ans_{lesson_id}_{q_num}_c")]
    ]
    await query.message.reply_text(
        f"Вопрос {q_num} из 3:\n\n{question}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data.startswith("lesson_"):
        lesson_id = int(data.split("_")[1])
        await send_lesson(query, lesson_id)

    elif data.startswith("test_"):
        _, lesson_id, q_num = data.split("_")
        context.user_data[f"correct_{lesson_id}"] = 0
        await send_question(query, int(lesson_id), int(q_num))

    elif data.startswith("ans_"):
        _, lesson_id, q_num, answer = data.split("_")
        lesson_id = int(lesson_id)
        q_num = int(q_num)
        lesson = get_lesson(lesson_id)
        correct_raw = str(lesson[f"q{q_num}_correct"]).lower().strip()
        correct_list = [x.strip() for x in correct_raw.split(",")]
        key = f"correct_{lesson_id}"
        if key not in context.user_data:
            context.user_data[key] = 0

        if answer in correct_list:
            context.user_data[key] += 1
            await query.message.reply_text("✅ Правильно!")
        else:
            correct_texts = " или ".join([
                f"{c.upper()}) {lesson[f'q{q_num}_{c}']}" for c in correct_list
            ])
            await query.message.reply_text(
                f"❌ Неверно. Правильный ответ: {correct_texts}"
            )

        if q_num < 3:
            await send_question(query, lesson_id, q_num + 1)
        else:
            count = context.user_data.get(key, 0)
            if count >= MIN_CORRECT:
                next_lesson = lesson_id + 1
                progress, _ = get_progress(user.id)
                passed = str(progress["passed_lessons"]) if progress else ""
                passed_list = [x for x in passed.split(",") if x]
                if str(lesson_id) not in passed_list:
                    passed_list.append(str(lesson_id))
                save_progress(user.id, user.full_name, next_lesson, ",".join(passed_list))

                next_lesson_data = get_lesson(next_lesson)
                if next_lesson_data:
                    keyboard = [[InlineKeyboardButton(
                        f"▶️ Урок {next_lesson}: {next_lesson_data['topic']}",
                        callback_data=f"lesson_{next_lesson}"
                    )]]
                    await query.message.reply_text(
                        f"Тест пройден! Правильных: {count}/3\n\nСледующий урок разблокирован",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.message.reply_text(
                        f"Курс пройден! Правильных: {count}/3\n\nТы настоящий мастер PPF!"
                    )
            else:
                keyboard = [[InlineKeyboardButton("🔄 Пересмотреть видео", callback_data=f"lesson_{lesson_id}")]]
                await query.message.reply_text(
                    f"Тест не пройден. Правильных: {count}/3\n"
                    f"Нужно минимум {MIN_CORRECT}/3.\n\nПересмотри видео и попробуй снова",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
