import json
from pyrogram.filters import create
from settings import *
from pyrogram.types import CallbackQuery
from db import get_state
from pyrogram.types import Message

async def models_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data_json = json.loads(update.data) 
    return "sub_id" in data_json
models_callback = create(models_callback_filter)

async def order_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "order" if "cn" in data else False
order_callback = create(order_callback_filter)

async def remove_order_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "remove_order" if "cn" in data else False
remove_order_callback = create(remove_order_callback_filter)

async def add_item_brand_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "add_item_brand" if "cn" in data else False
add_item_brand_callback = create(add_item_brand_callback_filter)

async def brands_callback_filter(_, __, update: CallbackQuery):
    
    if not bool(update.data):
        return False
    data_json = json.loads(update.data)
    return "brand" in data_json
brands_callback = create(brands_callback_filter)

def has_text(text):
    async def has_text_filter(flt, _, message: Message, text=None):
        return str(message.text) in flt.text
    return create(has_text_filter,text=text)

async def admin_filter(_, __, message: Message):
    return message.chat.id in ADMIN_IDs
admin = create(admin_filter)

def state(state_name):
    async def state_filter(flt, _, message: Message, state_names = None):
        state_str = get_state(message.chat.id)
        # Проверяем, что строка не пустая и корректная
        if not state_str or state_str.strip() == "" or state_str == "None":
            return False
        try:
            data = json.loads(state_str)
        except Exception:
            return False
        return data["state"] == flt.state_names if "state" in data else False
    return create(state_filter,"State_filter", state_names = state_name)

async def add_item_model_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "add_item_model" if "cn" in data else False
add_item_model_callback = create(add_item_model_callback_filter)

async def catalog_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "catalog" if "cn" in data else False
catalog_callback = create(catalog_callback_filter)

async def search_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "search" if "cn" in data else False
search_callback = create(search_callback_filter)

async def contact_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "contact" if "cn" in data else False
contact_callback = create(contact_callback_filter)

async def news_confirm_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "news_confirm" if "cn" in data else False
news_confirm_callback = create(news_confirm_callback_filter)

async def cancel_callback_filter(_, __, update: CallbackQuery):
    if not bool(update.data):
        return False
    data = json.loads(update.data)
    return data["cn"] == "cancel" if "cn" in data else False
cancel_callback = create(cancel_callback_filter)
