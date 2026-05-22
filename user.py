import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import WAITING_FOR_TITLE, WAITING_FOR_REPLY, ADMIN_IDS
from db import (
    add_user, user_exists, get_user_title, get_user_tasks, 
    get_task_stats, get_task_info, update_task_with_reply,
    get_user_info
)
from keyboards import remove_keyboard, complete_task_button

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المحادثة وطلب المسمى الوظيفي"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    username = update.effective_user.username
    
    # تخزين معلومات المستخدم مؤقتاً
    context.user_data["temp_user_name"] = user_name
    context.user_data["temp_username"] = username
    
    await update.message.reply_text(
        "👋 أهلاً بك!\n\n"
        "📝 يرجى إدخال مسمى وظيفتك (مثال: مدير, موظف, مهندس, الخ):",
        reply_markup=remove_keyboard()
    )
    return WAITING_FOR_TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال المسمى الوظيفي وحفظ المستخدم"""
    user_id = update.effective_user.id
    user_title = update.message.text.strip()
    user_name = context.user_data.get("temp_user_name")
    username = context.user_data.get("temp_username")
    
    # حفظ المستخدم في قاعدة البيانات
    add_user(user_id, user_name, username, user_title)
    
    # رسالة ترحيب بدون أزرار
    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            f"✅ **تم التسجيل بنجاح!**\n\n"
            f"👤 المسمى: {user_title}\n"
            f"🛠 أنت أدمن\n\n"
            f"استخدم الأمر /admin لعرض لوحة التحكم",
            parse_mode='Markdown',
            reply_markup=remove_keyboard()
        )
    else:
        await update.message.reply_text(
            f"✅ **تم التسجيل بنجاح!**\n\n"
            f"👤 المسمى: {user_title}\n"
            f"📌 سيتم إرسال المهام إليك عند الحاجة",
            parse_mode='Markdown',
            reply_markup=remove_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def show_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أوامر الأدمن"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ غير مصرح لك بالدخول")
        return
    
    from keyboards import admin_menu
    await update.message.reply_text(
        "🛠 **لوحة تحكم الأدمن**\n\n"
        "استخدم الأزرار أدناه للتحكم:",
        reply_markup=admin_menu(),
        parse_mode='Markdown'
    )

async def show_my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض مهام المستخدم المعلقة (للأدمن فقط)"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ هذه الخاصية للأدمن فقط")
        return
    
    # جلب المهام المعلقة
    tasks = get_user_tasks(user_id, 'pending')
    stats = get_task_stats(user_id)
    
    if tasks:
        msg = "📋 **مهامي المعلقة:**\n\n"
        for task in tasks:
            task_id, desc, status, file_path = task
            msg += f"🔹 #{task_id} - {desc}\n"
            if file_path:
                msg += f"   📎 يوجد مرفق\n"
            msg += f"   📍 الحالة: ⏳ قيد الانتظار\n\n"
        
        msg += f"\n📊 **إحصائياتي:**\n"
        msg += f"✅ المهام المنجزة: {stats[1]}\n"
        msg += f"⏳ المهام المعلقة: {stats[0]}"
    else:
        msg = f"📋 **لا توجد مهام معلقة**\n\n"
        msg += f"✅ المهام المنجزة: {stats[1]}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def show_all_users_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض جميع مهام المستخدمين (للأدمن فقط)"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ هذه الخاصية للأدمن فقط")
        return
    
    from db import get_all_users, get_all_user_tasks
    
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ لا يوجد مستخدمين")
        return
    
    msg = "📋 **جميع المهام:**\n\n"
    
    for user in users:
        user_id, user_name, username, title = user
        tasks = get_all_user_tasks(user_id)
        
        if tasks:
            msg += f"👤 **{user_name}** ({title})\n"
            for task in tasks:
                task_id, desc, status, file_path, reply_text, reply_file, completed_at = task
                status_icon = "✅" if status == 'done' else "⏳"
                msg += f"  {status_icon} #{task_id} - {desc}\n"
                if reply_text and status == 'done':
                    reply_preview = reply_text[:50] + "..." if len(reply_text) > 50 else reply_text
                    msg += f"     💬 الرد: {reply_preview}\n"
            msg += "\n"
    
    # تقسيم الرسالة إذا كانت طويلة
    if len(msg) > 4000:
        for i in range(0, len(msg), 4000):
            await update.message.reply_text(msg[i:i+4000], parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, parse_mode='Markdown')

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة المستخدمين (للأدمن فقط)"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ هذه الخاصية للأدمن فقط")
        return
    
    from db import get_all_users
    
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ لا يوجد مستخدمين")
        return
    
    msg = "👥 **قائمة المستخدمين:**\n\n"
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
        msg += f"✅ {done} | ⏳ {pending}\n"
        msg += f"➖➖➖➖➖➖\n\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات النظام (للأدمن فقط)"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ هذه الخاصية للأدمن فقط")
        return
    
    from db import get_all_users, get_pending_tasks_count, get_completed_tasks_count
    
    users = get_all_users()
    pending = get_pending_tasks_count()
    completed = get_completed_tasks_count()
    
    msg = f"📊 **إحصائيات النظام**\n\n"
    msg += f"👥 عدد المستخدمين: {len(users)}\n"
    msg += f"📋 إجمالي المهام: {pending + completed}\n"
    msg += f"✅ المهام المنجزة: {completed}\n"
    msg += f"⏳ المهام المعلقة: {pending}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def receive_task_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال رد المستخدم على المهمة"""
    task_id = context.user_data.get("pending_task_id")
    
    if not task_id:
        await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        return ConversationHandler.END
    
    # استخراج النص
    reply_text = update.message.caption or update.message.text
    if not reply_text:
        reply_text = "بدون نص إضافي"
    
    reply_file = None
    reply_type = None
    
    # تحديد نوع الوسائط
    if update.message.photo:
        reply_file = update.message.photo[-1].file_id
        reply_type = "photo"
    elif update.message.video:
        reply_file = update.message.video.file_id
        reply_type = "video"
    elif update.message.document:
        reply_file = update.message.document.file_id
        reply_type = "document"
    
    # تحديث المهمة بالرد
    update_task_with_reply(task_id, reply_text, reply_file, reply_type)
    
    # الحصول على معلومات المهمة
    task_info = get_task_info(task_id)
    
    if task_info:
        task_desc = task_info[1]
        user_id = task_info[3]
        
        # إرسال تأكيد للمستخدم
        confirm_msg = f"✅ **تم إنجاز المهمة #{task_id} بنجاح!**\n\n"
        confirm_msg += f"📝 ردك:\n{reply_text}\n"
        
        if reply_file:
            if reply_type == "photo":
                confirm_msg += f"\n📎 تم إرفاق صورة"
            elif reply_type == "video":
                confirm_msg += f"\n📎 تم إرفاق فيديو"
            elif reply_type == "document":
                confirm_msg += f"\n📎 تم إرفاق ملف"
        
        await update.message.reply_text(confirm_msg, parse_mode='Markdown')
        
        # الحصول على معلومات المستخدم
        user_info = get_user_info(user_id)
        user_name = user_info[1] if user_info else "مستخدم"
        user_username = user_info[2] if user_info and user_info[2] else "لا يوجد"
        user_title = user_info[3] if user_info else "غير محدد"
        
        # إرسال إشعار للأدمن
        admin_msg = f"📢 **تم إنجاز مهمة**\n\n"
        admin_msg += f"👤 المستخدم: {user_name}\n"
        admin_msg += f"🔗 اليوزر: @{user_username}\n"
        admin_msg += f"📝 المسمى: {user_title}\n"
        admin_msg += f"🆔 المعرف: {user_id}\n"
        admin_msg += f"🔢 رقم المهمة: #{task_id}\n"
        admin_msg += f"📋 المهمة: {task_desc}\n\n"
        admin_msg += f"💬 رد المستخدم:\n{reply_text}\n"
        
        # إرسال للأدمن مع المرفقات
        from config import ADMIN_IDS
        for admin in ADMIN_IDS:
            try:
                if reply_file and reply_type == "photo":
                    await context.bot.send_photo(
                        admin, 
                        reply_file, 
                        caption=admin_msg, 
                        parse_mode='Markdown'
                    )
                elif reply_file and reply_type == "video":
                    await context.bot.send_video(
                        admin, 
                        reply_file, 
                        caption=admin_msg, 
                        parse_mode='Markdown'
                    )
                elif reply_file and reply_type == "document":
                    await context.bot.send_document(
                        admin, 
                        reply_file, 
                        caption=admin_msg, 
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        admin, 
                        admin_msg, 
                        parse_mode='Markdown'
                    )
                    
                logger.info(f"✅ تم إرسال إشعار للأدمن {admin} عن إنجاز المهمة #{task_id}")
                
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال إشعار للأدمن {admin}: {e}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية الحالية"""
    await update.message.reply_text("❌ تم إلغاء العملية")
    context.user_data.clear()
    return ConversationHandler.END