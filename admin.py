import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_IDS, WAITING_FOR_TASK
from db import (
    get_titles, get_users_by_title, get_all_users, delete_user,
    add_task, get_task_stats, get_user_info
)
from keyboards import admin_panel, titles_menu, users_menu, complete_task_button

logger = logging.getLogger(__name__)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة تحكم الأدمن"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ غير مصرح لك بالدخول")
        return
    
    await update.message.reply_text(
        "🛠 **لوحة التحكم**\nاختر الإجراء المطلوب:",
        reply_markup=admin_panel(),
        parse_mode='Markdown'
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استعلامات الأدمن"""
    query = update.callback_query
    data = query.data
    
    print(f"📌 Callback received: {data}")  # للتصحيح
    
    # ===== مهمة نصية =====
    if data == "admin_task_text":
        await query.answer("📝 جاري تحميل المسميات...")
        context.user_data["mode"] = "text"
        titles = get_titles()
        
        if not titles:
            await query.edit_message_text("❌ لا يوجد مستخدمين في النظام")
            return
        
        await query.edit_message_text(
            "👥 **اختر المسمى الوظيفي:**",
            reply_markup=titles_menu(titles),
            parse_mode='Markdown'
        )
        return
    
    # ===== مهمة وسائط =====
    elif data == "admin_task_media":
        await query.answer("🖼 جاري تحميل المسميات...")
        context.user_data["mode"] = "media"
        titles = get_titles()
        
        if not titles:
            await query.edit_message_text("❌ لا يوجد مستخدمين في النظام")
            return
        
        await query.edit_message_text(
            "👥 **اختر المسمى الوظيفي:**",
            reply_markup=titles_menu(titles),
            parse_mode='Markdown'
        )
        return
    
    # ===== اختيار المسمى =====
    elif data.startswith("title_"):
        await query.answer("✅ تم الاختيار")
        title = data.replace("title_", "")
        context.user_data["selected_title"] = title
        context.user_data["step"] = "waiting_for_task"
        
        if context.user_data["mode"] == "text":
            await query.edit_message_text(
                f"✏️ **إرسال مهمة نصية**\n\n"
                f"👥 المستهدف: {title}\n\n"
                f"📝 أرسل نص المهمة:",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"📎 **إرسال مهمة مع وسائط**\n\n"
                f"👥 المستهدف: {title}\n\n"
                f"📝 أرسل الوسائط مع وصف:",
                parse_mode='Markdown'
            )
        return WAITING_FOR_TASK
    
    # ===== حذف مستخدم =====
    elif data == "admin_delete_user":
        await query.answer("👥 جاري تحميل المستخدمين...")
        users = get_all_users()
        
        if not users:
            await query.edit_message_text("❌ لا يوجد مستخدمين للحذف")
            return
        
        await query.edit_message_text(
            "👥 **اختر المستخدم للحذف:**",
            reply_markup=users_menu(users),
            parse_mode='Markdown'
        )
        return
    
    # ===== تأكيد حذف مستخدم =====
    elif data.startswith("del_user_"):
        await query.answer("🗑 جاري الحذف...")
        user_id = int(data.replace("del_user_", ""))
        delete_user(user_id)
        await query.edit_message_text(f"✅ **تم حذف المستخدم {user_id} بنجاح**", parse_mode='Markdown')
        
        # العودة للوحة التحكم بعد 3 ثواني
        import asyncio
        await asyncio.sleep(2)
        await query.message.reply_text(
            "🛠 **لوحة التحكم**\nاختر الإجراء المطلوب:",
            reply_markup=admin_panel(),
            parse_mode='Markdown'
        )
        return
    
    # ===== إحصائيات النظام =====
    elif data == "admin_stats":
        await query.answer("📋 جاري حساب الإحصائيات...")
        users = get_all_users()
        total_tasks = 0
        completed_tasks = 0
        
        for user in users:
            stats = get_task_stats(user[0])
            if stats:
                total_tasks += (stats[0] or 0) + (stats[1] or 0)
                completed_tasks += (stats[1] or 0)
        
        msg = f"📋 **إحصائيات النظام**\n\n"
        msg += f"👥 عدد المستخدمين: {len(users)}\n"
        msg += f"📋 إجمالي المهام: {total_tasks}\n"
        msg += f"✅ المهام المنجزة: {completed_tasks}\n"
        msg += f"⏳ المهام المعلقة: {total_tasks - completed_tasks}"
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        return
    
    # ===== عرض المستخدمين =====
    elif data == "admin_users":
        await query.answer("👥 جاري تحميل المستخدمين...")
        users = get_all_users()
        
        if not users:
            await query.edit_message_text("❌ لا يوجد مستخدمين")
            return
        
        msg = "👥 **قائمة المستخدمين**\n\n"
        for user in users:
            user_id, name, username, title = user
            stats = get_task_stats(user_id)
            pending = stats[0] if stats else 0
            done = stats[1] if stats else 0
            
            msg += f"👤 **{name}**\n"
            msg += f"🆔 `{user_id}`\n"
            if username:
                msg += f"🔗 @{username}\n"
            msg += f"📝 {title}\n"
            msg += f"✅ منجز: {done} | ⏳ معلق: {pending}\n"
            msg += f"➖➖➖➖➖➖➖➖\n\n"
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        return
    
    # ===== رجوع =====
    elif data == "back_to_admin":
        await query.answer("🔙 جاري العودة...")
        await query.edit_message_text(
            "🛠 **لوحة التحكم**\nاختر الإجراء المطلوب:",
            reply_markup=admin_panel(),
            parse_mode='Markdown'
        )
        return
    
    elif data == "cancel_reply":
        await query.answer("❌ تم الإلغاء")
        await query.edit_message_text("❌ تم إلغاء العملية")
        return ConversationHandler.END
    
    else:
        await query.answer("❌ حدث خطأ")

async def receive_task_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال المهمة من الأدمن وإرسالها للمستخدمين"""
    if context.user_data.get("step") != "waiting_for_task":
        return
    
    mode = context.user_data.get("mode")
    title = context.user_data.get("selected_title")
    
    if not title or not mode:
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        context.user_data.clear()
        return
    
    # جلب المستخدمين حسب المسمى
    users = get_users_by_title(title)
    
    if not users:
        await update.message.reply_text(f"❌ لا يوجد مستخدمين بالمسمى: {title}")
        context.user_data.clear()
        return
    
    # استخراج النص
    text = update.message.caption or update.message.text
    if not text:
        text = "بدون وصف"
    
    await update.message.reply_text(f"⏳ جاري إرسال المهام إلى {len(users)} مستخدم...")
    
    success_count = 0
    failed_users = []
    
    for (uid,) in users:
        try:
            if mode == "text":
                # مهمة نصية
                task_id = add_task(uid, text)
                
                await context.bot.send_message(
                    uid,
                    f"📌 **مهمة جديدة #{task_id}**\n\n{text}",
                    reply_markup=complete_task_button(task_id),
                    parse_mode='Markdown'
                )
                success_count += 1
                logger.info(f"✅ تم إرسال مهمة #{task_id} للمستخدم {uid}")
            
            else:
                # مهمة مع وسائط
                file_id = None
                send_func = None
                
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
                    await update.message.reply_text("❌ أرسل وسائط صحيحة (صورة، فيديو، أو ملف)")
                    return
                
                task_id = add_task(uid, text, file_id)
                
                await send_func(
                    uid,
                    file_id,
                    caption=f"📌 **مهمة جديدة #{task_id}**\n\n{text}",
                    reply_markup=complete_task_button(task_id),
                    parse_mode='Markdown'
                )
                success_count += 1
                logger.info(f"✅ تم إرسال مهمة #{task_id} (مع وسائط) للمستخدم {uid}")
                
        except Exception as e:
            logger.error(f"❌ خطأ في الإرسال للمستخدم {uid}: {e}")
            failed_users.append(uid)
            continue
    
    # تقرير الإرسال
    report = f"✅ **تقرير إرسال المهام**\n\n"
    report += f"📝 النوع: {'نصية' if mode == 'text' else 'وسائط'}\n"
    report += f"👥 المسمى: {title}\n"
    report += f"✅ تم الإرسال إلى: {success_count}/{len(users)} مستخدم\n"
    
    if failed_users:
        report += f"❌ فشل الإرسال إلى: {len(failed_users)} مستخدم\n"
        report += f"🆔 المعرفات: {', '.join(map(str, failed_users))}"
    
    await update.message.reply_text(report, parse_mode='Markdown')
    
    # عرض لوحة التحكم مرة أخرى
    await show_admin_panel(update, context)
    
    context.user_data.clear()