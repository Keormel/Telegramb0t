from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
import json

async def send_menu(app,chat_id):
    menu_buttons = [[InlineKeyboardButton("Catalog🛒",callback_data=json.dumps({"cn":"catalog"})),InlineKeyboardButton("Căutare🔎",callback_data=json.dumps({"cn":"search"}))],
                                [InlineKeyboardButton("Contacte📲",callback_data=json.dumps({"cn":"contact"}))]]
    menu_markup = InlineKeyboardMarkup(menu_buttons)
    msg=await app.send_message(chat_id,'.', reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await app.send_message(chat_id,"Accesati “Catalog” pentru a vedea toate modelele de incaltaminte.",reply_markup=menu_markup)
cancel_kb = ReplyKeyboardMarkup([["Anulare⬅"]],resize_keyboard=True,is_persistent=True)