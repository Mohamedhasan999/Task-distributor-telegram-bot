# handlers.py
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, TITLE, TASK_REPLY
import db
import keyboards as kb

logger = logging.getLogger(__name__)

# ---------- START / TITLE ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db.user_exists(user_id):
        if user_id in ADMIN_IDS:
            await update.message.reply_text(
                "👋 مرحباً بك مجدداً!\nاستخدم الأزرار للتحكم:",
                reply_markup=kb.admin_menu()
            )
        else:
            await update.message.reply_text(
                "👋 مرحباً بك مجدداً!\nسيتم إرسال المهام إليك.",
                reply_markup=kb.remove_keyboard()
            )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "📝 أهلاً بك!\nيرجى إدخال مسمى وظيفتك (مثال: مهندس، مدير، موظف):",
            reply_markup=kb.remove_keyboard()
        )
        return TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    username = update.effective_user.username
    title = update.message.text.strip()
    db.add_user(user_id, name, username, title)

    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            f"✅ تم التسجيل بنجاح!\nالمسمى: {title}\n🛠 أنت أدمن.",
            reply_markup=kb.admin_menu()
        )
    else:
        await update.message.reply_text(
            f"✅ تم التسجيل بنجاح!\nالمسمى: {title}\n📌 ستصل المهام هنا.",
            reply_markup=kb.remove_keyboard()
        )
    return ConversationHandler.END

# ---------- ADMIN MENU (Reply Keyboard) ----------
async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ غير مصرح")
        return
    text = update.message.text
    if text == "📋 المهام المعلقة":
        await stats(update, context)
    elif text == "👥 المستخدمين":
        await list_users(update, context)
    elif text == "📩 مهمة نصية":
        await show_titles_for_task(update, context, mode="text")
    elif text == "🖼 مهمة وسائط":
        await show_titles_for_task(update, context, mode="media")
    elif text == "🗑 حذف مستخدم":
        await show_users_for_delete(update, context)

# ---------- ADMIN CALLBACKS ----------
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Callback received: {data}")

    async def safe_edit(text, reply_markup=None, parse_mode=None):
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}. Sending new message instead.")
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

    if data == "admin_text":
        context.user_data['mode'] = 'text'
        titles = db.get_all_titles()
        if not titles:
            await safe_edit("❌ لا يوجد مستخدمين بعد.")
            return
        await safe_edit("اختر المسمى الوظيفي:", reply_markup=kb.titles_menu(titles))
        return
    elif data == "admin_media":
        context.user_data['mode'] = 'media'
        titles = db.get_all_titles()
        if not titles:
            await safe_edit("❌ لا يوجد مستخدمين بعد.")
            return
        await safe_edit("اختر المسمى الوظيفي:", reply_markup=kb.titles_menu(titles))
        return
    elif data == "admin_deluser":
        users = db.get_all_users()
        if not users:
            await safe_edit("❌ لا يوجد مستخدمين.")
            return
        await safe_edit("اختر المستخدم للحذف:", reply_markup=kb.users_menu(users))
        return
    elif data == "admin_stats":
        await stats_callback(query, safe_edit)
        return
    elif data == "admin_users":
        await list_users_callback(query, safe_edit)
        return
    elif data == "admin_back":
        await safe_edit("🛠 لوحة التحكم:", reply_markup=kb.admin_panel())
        return

    if data.startswith("title_"):
        title = data[6:]
        context.user_data['selected_title'] = title
        await safe_edit(
            f"✏️ أرسل {'نص' if context.user_data['mode'] == 'text' else 'الوسائط مع وصف'} للمهمة\n\n👥 المستهدف: {title}"
        )
        logger.info(f"Admin selected title: {title}, mode: {context.user_data['mode']}. Waiting for task input.")
        return TASK_REPLY

    if data.startswith("del_"):
        user_id = int(data[4:])
        db.delete_user(user_id)
        await safe_edit(f"✅ تم حذف المستخدم {user_id}")
        await query.message.reply_text("🛠 لوحة التحكم:", reply_markup=kb.admin_panel())
        return

    if data.startswith("complete_"):
        task_id = int(data[9:])
        context.user_data['pending_task_id'] = task_id
        await safe_edit(
            f"📝 أرسل ردك على إنجاز المهمة #{task_id}\n(يمكنك إرسال نص أو نص مع صورة/فيديو/ملف)"
        )
        logger.info(f"User completing task {task_id}, waiting for reply.")
        return TASK_REPLY

    await safe_edit("❌ خيار غير معروف")

# ========== عرض المهام المعلقة بدلاً من الإحصائيات ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع المهام المعلقة (بدلاً من الإحصائيات)"""
    tasks = db.get_all_pending_tasks()
    if not tasks:
        await update.message.reply_text("📭 لا توجد مهام معلقة حالياً.")
        return

    msg = "📋 **المهام المعلقة:**\n\n"
    for task in tasks:
        msg += f"🔹 **#{task['task_id']}**\n"
        msg += f"   📝 المهمة: {task['description'][:100]}\n"
        msg += f"   👤 المستخدم: {task['name']} (ID: {task['user_id']})\n"
        msg += f"   🏷️ المسمى: {task['title']}\n"
        msg += f"   ➖➖➖➖➖\n\n"

    if len(msg) > 4000:
        for i in range(0, len(msg), 4000):
            await update.message.reply_text(msg[i:i+4000], parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, parse_mode='Markdown')

async def stats_callback(query, safe_edit):
    """عرض جميع المهام المعلقة (للاستعلامات المضمنة)"""
    tasks = db.get_all_pending_tasks()
    if not tasks:
        await safe_edit("📭 لا توجد مهام معلقة حالياً.")
        return

    msg = "📋 **المهام المعلقة:**\n\n"
    for task in tasks:
        msg += f"🔹 **#{task['task_id']}**\n"
        msg += f"   📝 المهمة: {task['description'][:100]}\n"
        msg += f"   👤 المستخدم: {task['name']} (ID: {task['user_id']})\n"
        msg += f"   🏷️ المسمى: {task['title']}\n"
        msg += f"   ➖➖➖➖➖\n\n"

    if len(msg) > 4000:
        await safe_edit("⚠️ المهام كثيرة جداً، سيتم إرسالها في رسائل منفصلة.")
        for i in range(0, len(msg), 4000):
            await query.message.reply_text(msg[i:i+4000], parse_mode='Markdown')
    else:
        await safe_edit(msg, parse_mode='Markdown')

# دوال أخرى
async def list_users_callback(query, safe_edit):
    users = db.get_all_users()
    if not users:
        await safe_edit("❌ لا يوجد مستخدمين")
        return
    msg = "👥 **قائمة المستخدمين**\n\n"
    for u in users:
        pending, done = db.get_task_stats(u['user_id'])
        msg += f"👤 {u['name']}"
        if u['username']:
            msg += f" (@{u['username']})"
        msg += f"\n🆔 {u['user_id']}\n📝 {u['title']}\n✅ {done} | ⏳ {pending}\n➖➖➖➖\n"
    await safe_edit(msg, parse_mode='Markdown')

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_users()
    if not users:
        await update.message.reply_text("❌ لا يوجد مستخدمين")
        return
    msg = "👥 **قائمة المستخدمين**\n\n"
    for u in users:
        pending, done = db.get_task_stats(u['user_id'])
        msg += f"👤 {u['name']}"
        if u['username']:
            msg += f" (@{u['username']})"
        msg += f"\n🆔 {u['user_id']}\n📝 {u['title']}\n✅ {done} | ⏳ {pending}\n➖➖➖➖\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def show_titles_for_task(update: Update, context: ContextTypes.DEFAULT_TYPE, mode):
    context.user_data['mode'] = mode
    titles = db.get_all_titles()
    if not titles:
        await update.message.reply_text("❌ لا يوجد مستخدمين.")
        return
    await update.message.reply_text("اختر المسمى الوظيفي:", reply_markup=kb.titles_menu(titles))

async def show_users_for_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_users()
    if not users:
        await update.message.reply_text("❌ لا يوجد مستخدمين.")
        return
    await update.message.reply_text("اختر المستخدم للحذف:", reply_markup=kb.users_menu(users))

# ---------- استقبال المهمة من الأدمن ----------
async def receive_task_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("receive_task_from_admin called")
    mode = context.user_data.get('mode')
    title = context.user_data.get('selected_title')
    if not title or not mode:
        await update.message.reply_text("❌ حدث خطأ، حاول مرة أخرى")
        logger.error(f"Missing mode or title: mode={mode}, title={title}")
        return ConversationHandler.END

    user_ids = db.get_users_by_title(title)
    logger.info(f"Sending task to users with title '{title}': {user_ids}")
    if not user_ids:
        await update.message.reply_text(f"❌ لا يوجد مستخدمين بالمسمى {title}")
        return ConversationHandler.END

    text = update.message.caption or update.message.text
    if not text:
        text = "بدون وصف"

    file_id = None
    send_func = None
    if mode == 'media':
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            send_func = context.bot.send_photo
        elif update.message.video:
            file_id = update.message.video.file_id
            send_func = context.bot.send_video
        elif update.message.document:
            file_id = update.message.document.file_id
            send_func = context.bot.send_document
        else:
            await update.message.reply_text("❌ يرجى إرسال صورة، فيديو، أو ملف مع وصف.")
            return ConversationHandler.END

    success = 0
    for uid in user_ids:
        try:
            task_id = db.add_task(uid, text, file_id)
            if mode == 'text':
                await context.bot.send_message(
                    uid,
                    f"📌 **مهمة جديدة #{task_id}**\n\n{text}",
                    reply_markup=kb.complete_button(task_id),
                    parse_mode='Markdown'
                )
            else:
                await send_func(
                    uid,
                    file_id,
                    caption=f"📌 **مهمة جديدة #{task_id}**\n\n{text}",
                    reply_markup=kb.complete_button(task_id),
                    parse_mode='Markdown'
                )
            success += 1
        except Exception as e:
            logger.error(f"فشل إرسال للمستخدم {uid}: {e}")

    await update.message.reply_text(f"✅ تم إرسال المهمة إلى {success} من {len(user_ids)} مستخدم.")
    await update.message.reply_text("🛠 لوحة التحكم:", reply_markup=kb.admin_panel())
    context.user_data.clear()
    return ConversationHandler.END

# ---------- استقبال رد المستخدم على إنجاز المهمة ----------
async def receive_task_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get('pending_task_id')
    if not task_id:
        await update.message.reply_text("❌ حدث خطأ، حاول مرة أخرى")
        return ConversationHandler.END

    reply_text = update.message.caption or update.message.text
    if not reply_text:
        reply_text = "بدون نص إضافي"

    reply_file_id = None
    reply_type = None
    if update.message.photo:
        reply_file_id = update.message.photo[-1].file_id
        reply_type = 'photo'
    elif update.message.video:
        reply_file_id = update.message.video.file_id
        reply_type = 'video'
    elif update.message.document:
        reply_file_id = update.message.document.file_id
        reply_type = 'document'

    db.complete_task(task_id, reply_text, reply_file_id, reply_type)

    task = db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ المهمة غير موجودة")
        return ConversationHandler.END

    await update.message.reply_text(f"✅ تم إنجاز المهمة #{task_id} بنجاح! شكراً لك.")

    with db.get_db() as conn:
        cur = conn.execute('SELECT name, username, title FROM users WHERE user_id = ?', (task['user_id'],))
        user_info = cur.fetchone()

    admin_msg = f"📢 **تم إنجاز مهمة**\n\n"
    admin_msg += f"👤 المستخدم: {user_info['name']}"
    if user_info['username']:
        admin_msg += f" (@{user_info['username']})"
    admin_msg += f"\n📝 المسمى: {user_info['title']}\n"
    admin_msg += f"🔢 رقم المهمة: #{task_id}\n"
    admin_msg += f"📋 المهمة: {task['description']}\n\n"
    admin_msg += f"💬 رد المستخدم:\n{reply_text}\n"

    for admin in ADMIN_IDS:
        try:
            if reply_file_id and reply_type == 'photo':
                await context.bot.send_photo(admin, reply_file_id, caption=admin_msg, parse_mode='Markdown')
            elif reply_file_id and reply_type == 'video':
                await context.bot.send_video(admin, reply_file_id, caption=admin_msg, parse_mode='Markdown')
            elif reply_file_id and reply_type == 'document':
                await context.bot.send_document(admin, reply_file_id, caption=admin_msg, parse_mode='Markdown')
            else:
                await context.bot.send_message(admin, admin_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"فشل إشعار الأدمن {admin}: {e}")

    context.user_data.clear()
    return ConversationHandler.END

# ---------- إلغاء المحادثة ----------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.")
    context.user_data.clear()
    return ConversationHandler.END