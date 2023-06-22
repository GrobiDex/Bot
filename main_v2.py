import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
from datetime import date
import re
from hashlib import md5
from urllib.parse import urlencode


bot = telebot.TeleBot('6071429503:AAFZ8V2LdRmrUKINGxmVb2rRxBznyqAqBnc')
provider_token = '1920051371:TEST:638216808152488606'


# Функция проверки подписался пользователь на канал или нет
def check_subscription(chat_id):
    if bot.get_chat_member('@dealinvalid', chat_id).status == 'member':
        return True
    else:
        return False

# Функция поиска информации упоминаниях в сформированной таблице
def search(key_code, user_name):
    # Создаем соединение с базой данных
    conn = sqlite3.connect('dbmentions.db')
    cursor = conn.cursor()
    # Выполняем SELECT запрос для поиска строк с нужным кодом
    query = f"SELECT GUID, pub_date, dec_date FROM messages WHERE code LIKE '%{key_code}%'"
    result = cursor.execute(query).fetchall()
    if result:
        # Выводим найденные строки
        text = 'Вот что мне удалось найти:'
        print(f"Пользователь {user_name} ищет строки с кодом {key_code}:")
        for row in result:
            message_guid, pub_date, dec_date = row
            text = text + f''' 

Дата публикации: {pub_date}
Дата подачи заявления: {dec_date}
Ссылка на сообщение: https://old.bankrot.fedresurs.ru/MessageWindow.aspx?ID={message_guid}&attempt=1'''
        cursor.close()
        conn.close()
        return text
    else:
        cursor.close()
        conn.close()
        return (f'''Совпадений с указанным ИНН/ОГРН/ОГРНИП/СНИЛС не найдено.''')

def create_db():
    # Создание таблицы подписчиков и оставшихся у них сообщений
    connection = sqlite3.connect('subscriptions.db')
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (chat_id INTEGER PRIMARY KEY,
                 user_name TEXT,
                 date_created TEXT,
                 message_count INTEGER,
                 date_paid TEXT,
                 fall_date_paid TEXT,
                 paid INTEGER)''')
    connection.commit()
    connection.close()
    # Создание таблицы конфиденциальности
    connection = sqlite3.connect('policy.db')
    cursor = connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS policy
                 (chat_id INTEGER PRIMARY KEY,
                 user_name TEXT,
                 is_policy_accepted INTEGER,
                 accepted_date INTEGER)''')
    connection.commit()
    connection.close()
create_db()

# Обработчик команды /start
@bot.message_handler(commands=['start', 'старт'])
def start(message):
    chat_id = message.chat.id
    user_name = message.from_user.username
    today = date.today()
    date_paid = ''
    fall_date_paid = ''
    # Создаем\открываем sql таблицу, которая ведет учет подписчиков
    connection = sqlite3.connect('subscriptions.db')
    cursor = connection.cursor()
    # Обновляем информацию о том, что пользователь участник бота
    cursor.execute('INSERT OR REPLACE INTO subscriptions (chat_id, user_name, date_created, message_count, date_paid, fall_date_paid, paid) VALUES (?, ?, ?, ?, ?, ?, ?)', (chat_id, user_name, today, 10, date_paid, fall_date_paid, 0))
    connection.commit()
    cursor.close()
    connection.close()
    # Отправляем кнопку "Подписаться" и кнопку для проверки подписки в объединенной клавиатуре inline keyboard
    keyboard = types.InlineKeyboardMarkup()
    subscribe_button = types.InlineKeyboardButton('Подписаться', url='https://t.me/+EPWWTZsQ_n1kYmM6')
    check_subscription_button = types.InlineKeyboardButton('Я подписался', callback_data='privacy_policy')
    keyboard.add(subscribe_button, check_subscription_button)
    bot.send_message(chat_id, 'Чтобы использовать бота, необходимо подписаться на канал @dealinvalid.', reply_markup=keyboard)

# Обработчик "Проверить подписку"
@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def check_subscription_callback(call):
    chat_id = call.message.chat.id
    if check_subscription(chat_id):
        privacy_policy_callback(call)
    else:
        bot.answer_callback_query(call.id, "Вы не подписаны на канал @dealinvalid. Подпишитесь, чтобы использовать бота.", show_alert=True)

# Обработчик кнопки "Политика конфиденциальности"
@bot.callback_query_handler(func=lambda call: call.data == 'privacy_policy')
def privacy_policy_callback(call):
    user_name = call.message.chat.username
    chat_id = call.message.chat.id
    # Создаем\открываем sql таблицу, которая ведет учет подтвердивших политику
    connection = sqlite3.connect('policy.db')
    cursor = connection.cursor()
    # Проверяем состояние ознакомления с политикой
    cursor.execute('SELECT is_policy_accepted FROM policy WHERE user_name = ?', (user_name,))
    is_accepted = cursor.fetchone()
    if is_accepted is None:
        cursor.close()
        connection.close()
        # Если пользователь НЕ ПОДТВЕРЖДАЛ ПОЛИТИКУ ранее, отправляем сообщение с просьбой подтвердить согласие
        keyboard = types.InlineKeyboardMarkup()
        policy_button = types.InlineKeyboardButton('Ознакомиться', url='https://telegra.ph/Politika-05-19-2')
        check_policy_button = types.InlineKeyboardButton('Согласен', callback_data='policy_accepted')
        keyboard.add(policy_button, check_policy_button)
        bot.send_message(chat_id, 'Вы успешно подписались на наш канал @dealinvalid. Теперь необходимо ознакомиться с нашей политикой конфиденциальности.', reply_markup=keyboard)
    else:
        # Если пользователь УЖЕ ПОДТВЕРЖДАЛ ПОЛИТИКУ, отправляем сообщение об этом
        cursor.close()
        connection.close()
        keyboard = types.InlineKeyboardMarkup()
        policy_button = types.InlineKeyboardButton('Ознакомиться', url='https://telegra.ph/Politika-05-19-2')
        keyboard.add(policy_button)
        bot.send_message(chat_id, 'Вы уже подтвердили нашу политику конфиденциальности. Ознакомиться с ней еще раз можно по ссылке ниже', reply_markup=keyboard)
        main_def(call)

# Обработчик callback-запросов для кнопки подтверждения согласия с политикой
@bot.callback_query_handler(func=lambda call: call.data == "policy_accepted")
def process_policy_acceptance(call):
    chat_id = call.from_user.id
    user_name = call.from_user.username
    today = date.today()
    # Создаем\открываем sql таблицу, которая ведет учет подтвердивших политику
    connection = sqlite3.connect('policy.db')
    cursor = connection.cursor()
    # Обновляем информацию о том, что пользователь подтвердил политику конфиденциальности
    cursor.execute('INSERT OR REPLACE INTO policy (chat_id, user_name, is_policy_accepted, accepted_date) VALUES (?, ?, ?, ?)', (chat_id, user_name, 1, today))
    connection.commit()
    cursor.close()
    connection.close()
    # Отправляем сообщение об успешном подтверждении политики
    bot.send_message(chat_id, 'Спасибо, что подтвердили нашу политику конфиденциальности.')
    main_def(call)

# Обработчик основной функции
@bot.callback_query_handler(func=lambda call: call.data == 'main_def')
def main_def(call):
    chat_id = call.message.chat.id # Заполняем переменную с ID чата
    user_name = call.message.chat.username # Заполняем переменную с ником пользователя в телеграм
    today = datetime.today()
    connection = sqlite3.connect('subscriptions.db')
    cursor = connection.cursor()
    cursor.execute('SELECT paid FROM subscriptions WHERE user_name=?', (user_name,)) # Ищем графу состояние подписки у конкретного пользователя
    status_paid_str = re.sub(r"\D", "", str(cursor.fetchone())) # Приводим найденый результат к строке
    if status_paid_str == '0': # Если оплаченой подписки нет
        cursor.execute('SELECT message_count FROM subscriptions WHERE user_name = ?', (user_name,)) # Берем информацию об оставшихся бесплатных проверках
        message_count = cursor.fetchone()
        message_count_int = re.sub(r"\D", "", str(message_count))
        cursor.close()
        connection.close()
        # Отправляем кнопку "Оформить подписку" и кнопку для "Проверить" в объединенной клавиатуре inline keyboard
        keyboard = types.InlineKeyboardMarkup()
        paid_subscription_button = types.InlineKeyboardButton('Оформить подписку', callback_data='paid_subscription')
        check_inn_button = types.InlineKeyboardButton('Проверить 🔍', callback_data='search_inn')
        keyboard.add(paid_subscription_button, check_inn_button)
        bot.send_message(chat_id, f'''Данный бот предназначен для поиска информации на федресурсе по ИНН/ОГРН/ОГРНИП/СНИЛС.
Сейчас у Вас есть {message_count_int} бесплатных проверок. Для снятия ограничений необходимо оформить платную подписку на бота. 
Доступ к основным функциям бота также можно получить из кентекстного меню, нажав кнопку справа от строки ввода сообщений.''', reply_markup=keyboard)
    else:
        cursor.execute('SELECT fall_date_paid FROM subscriptions WHERE user_name = ?', (user_name,)) # Берем информацию об оставшихся бесплатных проверках
        touch_fall_date_paid = cursor.fetchone()
        touch_fall_date_paid_obj = datetime.strptime(re.sub(r"\D", "", str(touch_fall_date_paid)), '%Y%m%d')
        if touch_fall_date_paid_obj <= today:
            connection.execute('UPDATE subscriptions SET paid=? WHERE user_name=?', (0, user_name))
            connection.execute('UPDATE subscriptions SET message_count=? WHERE user_name=?', (10, user_name))
            cursor.execute('SELECT message_count FROM subscriptions WHERE user_name = ?', (user_name,)) # Берем информацию об оставшихся бесплатных проверках
            message_count = cursor.fetchone()
            message_count_int = re.sub(r"\D", "", str(message_count))
            connection.commit()
            cursor.close()
            connection.close()
            # Отправляем кнопку "Оформить подписку" и кнопку для "Проверить" в объединенной клавиатуре inline keyboard
            keyboard = types.InlineKeyboardMarkup()
            paid_subscription_button = types.InlineKeyboardButton('Оформить подписку', callback_data='paid_subscription')
            check_inn_button = types.InlineKeyboardButton('Проверить 🔍', callback_data='search_inn')
            keyboard.add(paid_subscription_button, check_inn_button)
            bot.send_message(chat_id, f'''Данный бот предназначен для поиска информации на федресурсе по ИНН/ОГРН/ОГРНИП/СНИЛС. 
Сейчас у Вас есть {message_count_int} бесплатных проверок. Для снятия ограничений необходимо оформить платную подписку на бота. 
Доступ к основным функциям бота также можно получить из кентекстного меню, нажав кнопку справа от строки ввода сообщений.''', reply_markup=keyboard)
        else:
            cursor.close()
            connection.close()
            # Отправляем кнопку "Оформить подписку" и кнопку для "Проверить" в объединенной клавиатуре inline keyboard
            keyboard = types.InlineKeyboardMarkup()
            paid_subscription_button = types.InlineKeyboardButton('Состояние подписки', callback_data='paid_subscription')
            check_inn_button = types.InlineKeyboardButton('Проверить 🔍', callback_data='search_inn')
            keyboard.add(paid_subscription_button, check_inn_button)
            bot.send_message(chat_id, f'''Данный бот предназначен для поиска информации на федресурсе по ИНН/ОГРН/ОГРНИП/СНИЛС. 
Сейчас у Вас есть не ограниченное колличество проверок. Доступ к основным функциям бота также можно получить из кентекстного меню, нажав кнопку справа от строки ввода сообщений.''', reply_markup=keyboard)

# Обработчик поиска ИНН/ОГРН/ОГРНИП/СНИЛС
@bot.callback_query_handler(func=lambda call: call.data == 'search_inn')
def search_inn(call):
    chat_id = call.message.chat.id # Заполняем переменную с ID чата
    user_name = call.message.chat.username # Заполняем переменную с ником пользователя в телеграм
    connection = sqlite3.connect('subscriptions.db')
    cursor = connection.cursor()
    cursor.execute('SELECT message_count FROM subscriptions WHERE user_name=?', (user_name,)) # Ищем графу состояние подписки у конкретного пользователя
    message_count = cursor.fetchone()
    message_count_str = re.sub(r"\D", "", str(message_count))
    message_count_int = int(message_count_str)
    if 11 > message_count_int > 0:
        message_count_int -= 1
        connection.execute('UPDATE subscriptions SET message_count=? WHERE user_name=?', (message_count_int, user_name))
        connection.commit()
        cursor.close()
        connection.close()
        # Попросите пользователя ввести число от 10 до 15 символов
        msg = bot.send_message(chat_id, 'Введите ИНН/ОГРН/ОГРНИП/СНИЛС длиной от 10 до 15 символов:')
        bot.register_next_step_handler(msg, requests_inn)
    elif message_count_int == 0:
        cursor.close()
        connection.close()
        keyboard = types.InlineKeyboardMarkup()
        paid_subscription_button = types.InlineKeyboardButton('Оформить подписку', callback_data='paid_subscription')
        keyboard.add(paid_subscription_button)
        bot.send_message(chat_id, 'У Вас не осталось бесплатных проверок. Необходимо оформить подписку.', reply_markup=keyboard)
    else:
        # Попросите пользователя ввести число от 10 до 15 символов
        cursor.close()
        connection.close()
        msg = bot.send_message(chat_id, 'Введите ИНН/ОГРН/ОГРНИП/СНИЛС длиной от 10 до 15 символов:')
        bot.register_next_step_handler(msg, requests_inn)

# Определить функцию для запроса пользовательского ввода для INN
def requests_inn(message):
    chat_id = message.chat.id
    user_name = message.from_user.username
    inn = message.text
    if not inn.isdigit():
        msg = bot.send_message(chat_id, 'Некорректный ввод ИНН/ОГРН/ОГРНИП/СНИЛС. Запрос должен состоять только из цифр. Попробуйте еще раз:')
        bot.register_next_step_handler(msg, requests_inn)
    elif len(inn) < 10 or len(inn) > 15:
        msg = bot.send_message(chat_id, 'Некорректный ввод ИНН/ОГРН/ОГРНИП/СНИЛС. Длина должна быть от 10 до 15 символов, в зависимости от типа документа. Попробуйте еще раз:')
        bot.register_next_step_handler(msg, requests_inn)
    else:
        keyboard = types.InlineKeyboardMarkup()
        paid_subscription_button = types.InlineKeyboardButton('Состояние подписки', callback_data='paid_subscription')
        check_inn_button = types.InlineKeyboardButton('Проверить 🔍', callback_data='search_inn')
        keyboard.add(paid_subscription_button, check_inn_button)
        user_inn = inn
        answer = search(user_inn, user_name)
        bot.send_message(chat_id, answer, reply_markup=keyboard)

# Обработчик второй основной функции
@bot.callback_query_handler(func=lambda call: call.data == 'second_main_def')
def second_main_def(call):
    chat_id = call.message.chat.id
    # Отправляем кнопку "Подписаться" и кнопку для проверки подписки в объединенной клавиатуре inline keyboard
    keyboard = types.InlineKeyboardMarkup()
    paid_subscription_button = types.InlineKeyboardButton('Состояние подписки', callback_data='paid_subscription')
    check_inn_button = types.InlineKeyboardButton('Проверить 🔍', callback_data='search_inn')
    keyboard.add(paid_subscription_button, check_inn_button)
    # if 
    bot.send_message(chat_id, 'Сейчас у Вас есть ' + 'Х ' + 'бесплатных проверок. Для снятия ограничений ' +
                     'необходимо оформить платную подписку на бота. Доступ к основным функциям ' +
                     'бота также можно получить из кентекстного меню, нажав кнопку справа от строки ' +
                     'ввода сообщений.', reply_markup=keyboard)

# Оформление платной подписки и возвращение результатов оплаты
@bot.callback_query_handler(func=lambda call: call.data == 'paid_subscription')

# Обработчик события "Успешная оплата"
@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    # Получаем данные о платеже из сообщения об успешной оплате
    print('успех')

    # Обрабатываем успешную оплату
    # ...


bot.infinity_polling()
