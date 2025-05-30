import json
import random
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackContext
)
import os
TOKEN = os.getenv("TOKEN")
# --- Cấu hình ---
TOKEN = "7963250637:AAGdMqGj2KTwdNeNOhG7PRnqB6J_EDl6VPo"
USERS_FILE = "users.json"
ADMIN_PASSWORD = "adminpass"
MAX_BET = 1_000_000_000

# --- Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Load/Save users ---
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

users = load_users()

# --- Trạng thái ConversationHandler ---
(
    CHOOSING_ACTION,
    LOGIN_USERNAME, LOGIN_PASSWORD,
    REGISTER_USERNAME, REGISTER_PASSWORD,
    PLAY_BET, PLAY_CHOICE,
    ADMIN_PASS,
    ADMIN_COMMAND
) = range(9)

# --- Helpers ---
def is_logged_in(user_id):
    for username, data in users.items():
        if data.get("telegram_id") == user_id:
            return username
    return None

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = is_logged_in(user_id)
    if username:
        update.message.reply_text(
            f"Chào lại {username}! Gõ /play để bắt đầu chơi hoặc /help để xem lệnh."
        )
        return CHOOSING_ACTION

    update.message.reply_text(
        "Chào bạn! Bạn muốn đăng nhập hay đăng ký tài khoản?",
        reply_markup=ReplyKeyboardMarkup([["Đăng nhập", "Đăng ký"]], one_time_keyboard=True)
    )
    return CHOOSING_ACTION

def choosing_action(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    if "đăng nhập" in text:
        update.message.reply_text("Nhập tên đăng nhập:", reply_markup=ReplyKeyboardRemove())
        return LOGIN_USERNAME
    elif "đăng ký" in text:
        update.message.reply_text("Chọn tên đăng nhập mới:", reply_markup=ReplyKeyboardRemove())
        return REGISTER_USERNAME
    else:
        update.message.reply_text("Vui lòng chọn 'Đăng nhập' hoặc 'Đăng ký'.")
        return CHOOSING_ACTION

# --- Đăng nhập ---
def login_username(update: Update, context: CallbackContext):
    username = update.message.text.strip()
    if username not in users:
        update.message.reply_text("Tên đăng nhập không tồn tại. Vui lòng nhập lại hoặc đăng ký.")
        return LOGIN_USERNAME
    context.user_data["login_username"] = username
    update.message.reply_text("Nhập mật khẩu:")
    return LOGIN_PASSWORD

def login_password(update: Update, context: CallbackContext):
    password = update.message.text.strip()
    username = context.user_data.get("login_username")
    if users.get(username, {}).get("password") == password:
        # Gán telegram_id cho user để xác nhận đăng nhập
        users[username]["telegram_id"] = update.message.from_user.id
        save_users(users)
        update.message.reply_text(f"Đăng nhập thành công, chào {username}!\nGõ /play để chơi game.")
        return ConversationHandler.END
    else:
        update.message.reply_text("Sai mật khẩu, vui lòng nhập lại:")
        return LOGIN_PASSWORD

# --- Đăng ký ---
def register_username(update: Update, context: CallbackContext):
    username = update.message.text.strip()
    if username in users:
        update.message.reply_text("Tên đăng nhập đã tồn tại, vui lòng chọn tên khác:")
        return REGISTER_USERNAME
    context.user_data["register_username"] = username
    update.message.reply_text("Chọn mật khẩu:")
    return REGISTER_PASSWORD

def register_password(update: Update, context: CallbackContext):
    password = update.message.text.strip()
    username = context.user_data.get("register_username")
    users[username] = {
        "password": password,
        "balance": 1000,
        "wins": 0,
        "losses": 0,
        "admin_win_rate": 0,
        "force_result": None,
        "force_count": 0,
        "is_admin": False,
        "telegram_id": update.message.from_user.id
    }
    save_users(users)
    update.message.reply_text(f"Đăng ký thành công! Bạn có 1000 xu để bắt đầu.\nGõ /play để chơi game.")
    return ConversationHandler.END

# --- Lệnh /play bắt đầu chơi game ---
def play_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    username = is_logged_in(user_id)
    if not username:
        update.message.reply_text("Bạn chưa đăng nhập. Gõ /start để đăng nhập hoặc đăng ký.")
        return ConversationHandler.END
    user = users[username]
    update.message.reply_text(
        f"Chào {username}! Bạn có {user['balance']} xu.\nNhập số tiền cược (hoặc 'all' để cược hết):"
    )
    context.user_data["username"] = username
    return PLAY_BET

def play_bet(update: Update, context: CallbackContext):
    text = update.message.text.lower().strip()
    username = context.user_data.get("username")
    user = users.get(username)
    if text == "all":
        bet = user["balance"]
    else:
        try:
            bet = int(text)
        except:
            update.message.reply_text("Nhập không hợp lệ, vui lòng nhập số tiền cược hoặc 'all':")
            return PLAY_BET

    if bet <= 0:
        update.message.reply_text("Tiền cược phải lớn hơn 0, nhập lại:")
        return PLAY_BET
    if bet > user["balance"]:
        update.message.reply_text(f"Bạn không đủ tiền cược. Số dư: {user['balance']} xu. Nhập lại:")
        return PLAY_BET
    if bet > MAX_BET:
        update.message.reply_text(f"Tiền cược tối đa là {MAX_BET} xu. Nhập lại:")
        return PLAY_BET

    context.user_data["bet"] = bet
    update.message.reply_text("Chọn T (Tài) hoặc X (Xỉu):")
    return PLAY_CHOICE

def play_choice(update: Update, context: CallbackContext):
    choice = update.message.text.lower().strip()
    if choice not in ['t', 'x']:
        update.message.reply_text("Chọn không hợp lệ, vui lòng chọn T hoặc X:")
        return PLAY_CHOICE

    username = context.user_data.get("username")
    user = users[username]
    bet = context.user_data.get("bet")

    # Xử lý kết quả có ép tỉ lệ hay kết quả từ admin
    if user["force_result"] and user["force_count"] > 0:
        result = user["force_result"]
        user["force_count"] -= 1
        while True:
            dice = [random.randint(1,6) for _ in range(3)]
            total = sum(dice)
            if ('x' if total <= 10 else 't') == result:
                break
        if user["force_count"] == 0:
            user["force_result"] = None
    elif user["admin_win_rate"] > 0:
        will_win = random.randint(1, 100) <= user["admin_win_rate"]
        while True:
            dice = [random.randint(1,6) for _ in range(3)]
            total = sum(dice)
            result = 'x' if total <= 10 else 't'
            if (will_win and result == choice) or (not will_win and result != choice):
                break
    else:
        dice = [random.randint(1,6) for _ in range(3)]
        total = sum(dice)
        result = 'x' if total <= 10 else 't'

    update.message.reply_text(f"🎲 Xúc xắc: {dice} → Tổng: {total}")
    update.message.reply_text(f"➡️ Kết quả: {result.upper()} ({'Xỉu' if result == 'x' else 'Tài'})")

    if choice == result:
        user["balance"] += bet
        user["wins"] += 1
        update.message.reply_text(f"✅ Bạn thắng {bet} xu! Số dư hiện tại: {user['balance']} xu.")
    else:
        user["balance"] -= bet
        user["losses"] += 1
        update.message.reply_text(f"❌ Bạn thua {bet} xu! Số dư hiện tại: {user['balance']} xu.")

    if user["balance"] <= 0:
        user["balance"] = 0
        update.message.reply_text("💸 Bạn đã hết tiền! Liên hệ admin để được cộng thêm xu.")

    save_users(users)
    return ConversationHandler.END

# --- Lệnh /help ---
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "/start - Bắt đầu và đăng nhập/đăng ký\n"
        "/play - Chơi game Tài Xỉu\n"
        "/help - Xem hướng dẫn"
    )

# --- Setup bot và handler ---
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ACTION: [MessageHandler(Filters.text & ~Filters.command, choosing_action)],

            LOGIN_USERNAME: [MessageHandler(Filters.text & ~Filters.command, login_username)],
            LOGIN_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, login_password)],

            REGISTER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, register_username)],
            REGISTER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, register_password)],

            PLAY_BET: [MessageHandler(Filters.text & ~Filters.command, play_bet)],
            PLAY_CHOICE: [MessageHandler(Filters.text & ~Filters.command, play_choice)],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("play", play_command))
    dp.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

