# main.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config import BOT_TOKEN, ADMIN_IDS, TITLE, TASK_REPLY
import db
import handlers
import keyboards as kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # محادثة التسجيل
    conv_start = ConversationHandler(
        entry_points=[CommandHandler('start', handlers.start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_title)],
        },
        fallbacks=[CommandHandler('cancel', handlers.cancel)],
    )

    # محادثة إرسال المهمة من الأدمن
    conv_task_from_admin = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlers.admin_callback, pattern='^title_')],
        states={
            TASK_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_task_from_admin),
                MessageHandler(filters.PHOTO, handlers.receive_task_from_admin),
                MessageHandler(filters.VIDEO, handlers.receive_task_from_admin),
                MessageHandler(filters.Document.ALL, handlers.receive_task_from_admin),
            ],
        },
        fallbacks=[CommandHandler('cancel', handlers.cancel)],
        allow_reentry=True,
    )

    # محادثة رد المستخدم على إنجاز المهمة
    conv_task_reply = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlers.admin_callback, pattern='^complete_')],
        states={
            TASK_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_task_reply),
                MessageHandler(filters.PHOTO, handlers.receive_task_reply),
                MessageHandler(filters.VIDEO, handlers.receive_task_reply),
                MessageHandler(filters.Document.ALL, handlers.receive_task_reply),
            ],
        },
        fallbacks=[CommandHandler('cancel', handlers.cancel)],
        allow_reentry=True,
    )

    # إضافة المحادثات أولاً
    app.add_handler(conv_start)
    app.add_handler(conv_task_from_admin)
    app.add_handler(conv_task_reply)

    # معالج الأزرار العادية للأدمن
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex('^(📊 إحصائيات|👥 المستخدمين|📩 مهمة نصية|🖼 مهمة وسائط|🗑 حذف مستخدم)$'),
        handlers.admin_menu_handler
    ))

    # معالج عام للـ CallbackQuery (باستثناء title_ و complete_ التي تعاملها المحادثات)
    app.add_handler(CallbackQueryHandler(handlers.admin_callback, pattern='^(admin_|del_|admin_back|admin_stats|admin_users)'))

    # أمر /admin
    async def admin_command(update, context):
        user_id = update.effective_user.id
        if user_id in ADMIN_IDS and db.user_exists(user_id):
            await update.message.reply_text("🛠 لوحة التحكم:", reply_markup=kb.admin_panel())
        else:
            await update.message.reply_text("⛔ غير مصرح أو غير مسجل. استخدم /start أولاً.")
    app.add_handler(CommandHandler('admin', admin_command))

    # معالج الأخطاء
    async def error_handler(update, context):
        logger.error(f"خطأ: {context.error}")
    app.add_error_handler(error_handler)

    logger.info("✅ البوت يعمل...")
    app.run_polling()

if __name__ == '__main__':
    main()