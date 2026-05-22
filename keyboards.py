# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove

def remove_keyboard():
    return ReplyKeyboardRemove()

def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["📊 إحصائيات", "👥 المستخدمين"],
            ["📩 مهمة نصية", "🖼 مهمة وسائط"],
            ["🗑 حذف مستخدم"]
        ],
        resize_keyboard=True
    )

def admin_panel():
    keyboard = [
        [InlineKeyboardButton("📩 مهمة نصية", callback_data="admin_text")],
        [InlineKeyboardButton("🖼 مهمة وسائط", callback_data="admin_media")],
        [InlineKeyboardButton("🗑 حذف مستخدم", callback_data="admin_deluser")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)

def titles_menu(titles):
    buttons = [[InlineKeyboardButton(t, callback_data=f"title_{t}")] for t in titles]
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
    return InlineKeyboardMarkup(buttons)

def users_menu(users):
    buttons = []
    for u in users:
        name = u['name']
        username = u['username']
        display = f"{name} (@{username})" if username else name
        buttons.append([InlineKeyboardButton(display, callback_data=f"del_{u['user_id']}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
    return InlineKeyboardMarkup(buttons)

def complete_button(task_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ إنجاز المهمة", callback_data=f"complete_{task_id}")]
    ])