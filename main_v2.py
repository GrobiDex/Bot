import logging

from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# ДАННЫЕ ДЛЯ НАСТРОЙКИ
CONFIG = {
    "TOKEN": "6071429503:AAFZ8V2LdRmrUKINGxmVb2rRxBznyqAqBnc",
    "ID_CHANNEL": -1001641924266,
}

# СООБЩЕНИЯ
MESSAGES = {
    "not_in_group": "Для получения инфрмации необходима подписка на мой телеграм-канал 'Евгений Кравченко | Адвокат по оспариванию сделок, защите активов и банкротству'.",
    "in_group": "Спасибо за подписку",
    "sms_not_in_group": "Вы не подписались на канал :-(",
    "policy_confirmation": "Вот держи файл.",
    "thanks": "Спасибо, что ознакомились и согласились с публичной офертой, политикой конфиденциальности и правилами оказания услуг.",
}


btn_channel = InlineKeyboardButton(text="Подписаться", url="https://t.me/+EPWWTZsQ_n1kYmM6")
btn_accept_channel = InlineKeyboardButton(text="Я подписался", callback_data="check")

BUTTON_TYPES = {
    "BTN_SUB": InlineKeyboardMarkup().add(btn_channel, btn_accept_channel),
}


logging.basicConfig(format=u'%(filename)+13s [ LINE:%(lineno)-4s] %(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG)

bot = Bot(token=CONFIG["TOKEN"])
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())

# =============== СТАНДАРТНЫЕ КОМАНДЫ ===============
@dp.message_handler(commands=['start'])
async def start_command(message: Message):
    #   ПРОВЕРКА ПОДПИСКИ НА КАНАЛ
    user_channel_status = await bot.get_chat_member(chat_id=CONFIG["ID_CHANNEL"], user_id=message.from_user.id)
    if user_channel_status["status"] != 'left':
        start_mes = f"приветики"
        await bot.send_message(chat_id=message.from_user.id, text=start_mes, reply_markup=BUTTON_TYPES["BTN_HOME"])

    else:
        await bot.send_message(message.from_user.id, MESSAGES["not_in_group"], reply_markup=BUTTON_TYPES["BTN_SUB"])
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(StatesUSERS.all()[0])

# =============== ПРОВЕРКА ПОДПИСКИ ===============
@dp.message_handler(state=StatesUSERS.STATES_0)
async def check_sub(message: Message):
    state = dp.current_state(user=message.from_user.id)
    user_channel_status = await bot.get_chat_member(chat_id=CONFIG["ID_CHANNEL"], user_id=message.from_user.id)
    if user_channel_status["status"] != 'left':
        await message.answer(MESSAGES['in_group'])
        await message.answer(MESSAGES['policy_confirmation'], reply_markup=BUTTON_TYPES["BTN_POLIT"])
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(StatesUSERS.all()[1])

    else:
        await bot.send_message(message.from_user.id, MESSAGES["not_in_group"], reply_markup=BUTTON_TYPES["BTN_SUB"])
        await state.set_state(StatesUSERS.all()[0])


@dp.callback_query_handler(lambda callback: callback.data == "check", state=StatesUSERS.STATES_0)
async def check_sub_q(callback: CallbackQuery):
    user_channel_status = await bot.get_chat_member(chat_id=CONFIG["ID_CHANNEL"], user_id=callback.from_user.id)
    if user_channel_status["status"] != 'left':
        await callback.message.delete()
        await callback.message.answer(MESSAGES['in_group'])
        await callback.message.answer(MESSAGES['policy_confirmation'], reply_markup=BUTTON_TYPES["BTN_POLIT"])
        state = dp.current_state(user=callback.from_user.id)
        await state.set_state(StatesUSERS.all()[1])
    else:
        await callback.answer(MESSAGES["sms_not_in_group"], show_alert=True)



async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, on_shutdown=shutdown)
