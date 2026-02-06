import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = '7950596592:AAEwGqA-7mzRvOOAGDIcNBxLs78pQoKgp3o'
ADMIN_ID = int(os.environ.get('ADMIN_ID', '5689296851'))
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '+79785644911 - сбер')  # Ваш номер телефона

ORDERS_FILE = 'orders.json'

def load_orders():
    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_orders(orders):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Прайс", callback_data='price')],
        [InlineKeyboardButton("📋 Заказать", callback_data='order')],
        [InlineKeyboardButton("📸 Примеры", callback_data='portfolio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Быстрый дизайн за 15-30 минут!\n\n"
        "Замена фона, ретушь, аватарка\n"
        "⚡️ Оплата перед работой по СБП\n\n"
        "Выберите:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'price':
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='menu')]]
        await query.edit_message_text(
            "💰 ПРАЙС:\n\n"
            "• Замена фона — 100₽\n"
            "• Ретушь / Добавить объект — 150₽\n"
            "• Аватарка / Сложная работа — 200₽\n\n"
            "⏱ Срок: 15-30 минут\n"
            "💳 100% предоплата по СБП",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == 'order':
        keyboard = [
            [InlineKeyboardButton("100₽ - Замена фона", callback_data='service_100')],
            [InlineKeyboardButton("150₽ - Ретушь/Объект", callback_data='service_150')],
            [InlineKeyboardButton("200₽ - Аватарка/Сложная работа", callback_data='service_200')],
            [InlineKeyboardButton("◀️ Назад", callback_data='menu')]
        ]
        await query.edit_message_text(
            "📋 Выберите услугу:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith('service_'):
        price = int(query.data.split('_')[1])
        context.user_data['price'] = price
        context.user_data['waiting_order'] = True
        
        await query.edit_message_text(
            f"✅ Выбрано: {price}₽\n\n"
            "Теперь пришлите:\n"
            "📎 Фото или файл\n"
            "📝 Описание задачи\n\n"
            "(можно одним сообщением: фото + подпись к нему)"
        )
    
    elif query.data == 'portfolio':
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='menu')]]
        await query.edit_message_text(
            "📸 Примеры работ:\n\n"
            "Посмотрите закрепленное сообщение в боте ⬆️\n"
            "Или мое портфолио: https://vk.com/creative297?z=album-228935675_306824718",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == 'menu':
        keyboard = [
            [InlineKeyboardButton("💰 Прайс", callback_data='price')],
            [InlineKeyboardButton("📋 Заказать", callback_data='order')],
            [InlineKeyboardButton("📸 Примеры", callback_data='portfolio')]
        ]
        await query.edit_message_text(
            "👋 Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == 'paid':
        user = query.from_user
        user_id = str(user.id)
        orders = load_orders()
        
        if user_id not in orders:
            await query.answer("❌ Заказ не найден", show_alert=True)
            return
        
        order = orders[user_id]
        
        await query.answer("✅ Проверяю...")
        await query.edit_message_text(
            "⏳ Ожидаю подтверждения оплаты...\n\n"
            "Обычно это занимает 1-2 минуты.\n"
            "Как только деньги придут — я начну работу!"
        )
        
        # Уведомление администратору
        msg = (
            f"💰 КЛИЕНТ НАЖАЛ 'ОПЛАТИЛ'\n\n"
            f"От: @{user.username or user.first_name}\n"
            f"ID: {user.id}\n"
            f"Сумма: {order['price']}₽\n"
            f"Задача: {order['description']}\n\n"
            f"⚠️ ПРОВЕРЬТЕ БАНК!\n"
            f"Если деньги пришли:\n"
            f"/ok{user.id}"
        )
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
        
        # Отправляем фото/файл
        if order.get('photo'):
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=order['photo'])
        elif order.get('document'):
            await context.bot.send_document(chat_id=ADMIN_ID, document=order['document'])

async def receive_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_order'):
        return
    
    user = update.message.from_user
    price = context.user_data.get('price', 100)
    
    # Сохраняем заказ
    orders = load_orders()
    orders[str(user.id)] = {
        'username': user.username or user.first_name,
        'price': price,
        'description': update.message.caption or update.message.text or "[без описания]",
        'photo': update.message.photo[-1].file_id if update.message.photo else None,
        'document': update.message.document.file_id if update.message.document else None,
    }
    save_orders(orders)
    
    context.user_data['waiting_order'] = False
    
    # Кнопки оплаты
    keyboard = [
        [InlineKeyboardButton("💳 Отправить платёж", callback_data='send_payment')],
        [InlineKeyboardButton("✅ Я оплатил", callback_data='paid')]
    ]
    
    await update.message.reply_text(
        f"📦 Заказ принят!\n\n"
        f"К оплате: {price}₽\n\n"
        f"Как оплатить:\n"
        f"1. Нажмите 'Отправить платёж' чтобы скопировать номер\n"
        f"2. Откройте ваш банк и отправьте {price}₽\n"
        f"3. Вернитесь сюда и нажмите '✅ Я оплатил'\n\n"
        f"⚠️ Работа начнётся после проверки оплаты (1-2 мин)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет номер телефона для оплаты"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_order')]]
    await query.edit_message_text(
        f"📱 Номер для оплаты:\n\n"
        f"<code>{PHONE_NUMBER}</code>\n\n"
        f"Откройте ваш банк и отправьте платёж на этот номер.\n\n"
        f"После оплаты нажмите кнопку ниже 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def back_to_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к кнопкам оплаты"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = str(user.id)
    orders = load_orders()
    
    if user_id not in orders:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    order = orders[user_id]
    
    keyboard = [
        [InlineKeyboardButton("💳 Отправить платёж", callback_data='send_payment')],
        [InlineKeyboardButton("✅ Я оплатил", callback_data='paid')]
    ]
    
    await query.edit_message_text(
        f"📦 Заказ принят!\n\n"
        f"К оплате: {order['price']}₽\n\n"
        f"Как оплатить:\n"
        f"1. Нажмите 'Отправить платёж' чтобы скопировать номер\n"
        f"2. Откройте ваш банк и отправьте {order['price']}₽\n"
        f"3. Вернитесь сюда и нажмите '✅ Я оплатил'\n\n"
        f"⚠️ Работа начнётся после проверки оплаты (1-2 мин)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вы подтверждаете оплату командой /ok123456"""
    if update.message.from_user.id != ADMIN_ID:
        return
    
    try:
        client_id = int(update.message.text.replace('/ok', ''))
    except:
        await update.message.reply_text("❌ Формат: /ok123456 (ID клиента)")
        return
    
    orders = load_orders()
    order = orders.get(str(client_id))
    
    if not order:
        await update.message.reply_text("❌ Заказ не найден в базе")
        return
    
    # Уведомляем клиента
    await context.bot.send_message(
        chat_id=client_id,
        text="✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
             "Приступаю к работе прямо сейчас.\n"
             "Готово будет через 15-30 минут ⏱\n\n"
             "Пришлю результат сюда 👇"
    )
    
    await update.message.reply_text(
        f"✅ Клиент {client_id} (@{order['username']}) уведомлён!\n\n"
        f"Задача: {order['description']}\n"
        f"Сумма: {order['price']}₽\n\n"
        f"Можно работать! 🎨"
    )
    
    # Удаляем заказ из базы
    del orders[str(client_id)]
    save_orders(orders)

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ok", confirm_payment))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(send_payment, pattern='send_payment'))
    application.add_handler(CallbackQueryHandler(back_to_order, pattern='back_to_order'))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, receive_order))
    
    application.run_polling()

if __name__ == '__main__':
    main()
