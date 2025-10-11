from pyrogram import Client, filters
from settings import *
from time import sleep
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid
from pyrogram.errors import FloodWait
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from db import *
import json
from filters import *
from keyboard import *
init() # fix инициализации базы данных

# Добавляем вызов создания таблицы промокодов сразу после инициализации БД
try:
    ensure_promo_table()
except Exception:
    # Если по какой-то причине создание не удалось — безопасно игнорируем здесь
    pass

# --- FIX: синхронизируем cur и con в текущем модуле с курсором/соединением из db.py ---
try:
    import db as db_mod
    # Обновляем имена cur и con в пространстве имен main.py,
    # чтобы обращения вида cur.execute(...) использовали реальный курсор.
    cur = db_mod.cur
    con = db_mod.con
except Exception:
    # если по какой-то причине не удалось — пропускаем, ошибки будут обработаны позже
    pass

app = Client('my_bot',
    api_id=API_ID, 
    api_hash=API_HASH,
    bot_token=BOT_TOKEN)

@app.on_callback_query(cancel_callback)
async def cancel(_, query: CallbackQuery|Message):
    set_state(query.message.chat.id,json.dumps({'cn':'None'}))
    await send_menu(app, query.message.chat.id)
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(admin & filters.command("send_news"))
async def send_news(_, message: Message):
    set_state(message.chat.id ,json.dumps({"state": "news_input"}))
    await message.reply("Scrie știrea și o voi trimite tuturor clienților")

@app.on_message(state("news_input"))
async def sends_news(_, message: Message):
    set_state(message.chat.id ,json.dumps({"state": "None"}))
    news_buttons = [[InlineKeyboardButton("Tremite", callback_data=json.dumps({'cn':'news_confirm','cid':message.chat.id, "mid":message.id})),InlineKeyboardButton("Stop", callback_data=json.dumps({'cn':'cancel'}))]]
    news_markup = InlineKeyboardMarkup(inline_keyboard=news_buttons)
    await message.reply("Doriți să trimiteți știri tuturor utilizatorilor?", reply_markup=news_markup)

@app.on_callback_query(news_confirm_callback)
async def news_confirm(_, query: CallbackQuery):
    json_data = json.loads(query.data)
    mci, mi = json_data["cid"], json_data["mid"]
    await app.send_message(query.message.chat.id, "Vestea va ajunge în curând la toți utilizatorii.")
    await app.delete_messages(query.message.chat.id, query.message.id)
    await send_menu(app, query.message.chat.id)
    for i in get_all_users():
        while True:
            try:
                await app.forward_messages(i, from_chat_id=mci, message_ids=mi)
            except PeerIdInvalid:
                remove_user(i)
                break
            except FloodWait:
                sleep(1)
            except Exception as e:
                print(e)
                break
            else:
                break
    await app.send_message(query.message.chat.id, "Știrea a fost trimisă tuturor utilizatorilor")


@app.on_callback_query(cancel_callback)
async def cancel(_, query: CallbackQuery|Message):
    set_state(query.message.chat.id,json.dumps({'cn':'None'}))
    await send_menu(app, query.message.chat.id)
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_callback_query(contact_callback)
async def contact(_, query: CallbackQuery):
    await app.send_message(query.message.chat.id, f'Nr de telefon: <b>+37368617062</b> \nInstagram: <b>cross_brand.md</b> \nTelegram: @cross_brand_manager \nTik tok : <b>cross_brand.md</b>')
    await send_menu(app, query.message.chat.id)
    # Удаление сообщения не требуется

@app.on_message(state('search') & ~ has_text('Anulare⬅')& ~ filters.command('stop'))
async def result_search(_, message:Message):
    text = message.text
    mci = message.chat.id
    if text.isdecimal():
        await model_callback(_,query=CallbackQuery(from_user=message.from_user,chat_instance='1',id='1',message=message,data=json.dumps({'ids':[int(text)], 'current':0})))
    else:
        ids=search_items(message.text)
        if len(ids) == 0:
            await app.send_message(mci, 'Îmi pare rău, dar rezultat nu aratat nimic')
            return
        ids = [i[1] for i in ids]
        add_prev_data_state(message.chat.id,{'cn':'search','ids':ids})
        await model_callback(_,query=CallbackQuery(from_user=message.from_user,chat_instance=message.chat,id='1',message=message,data=json.dumps({'sub_id':'search', 'current':0})))


@app.on_message(admin & filters.command('add_item'))
async def add_item_name(_, message: Message):
        models = get_brands()
        if len(models) % 2 == 0:
            models = list(zip(models[len(models)//2:],models[:len(models)//2]))
        else:
            models = list(zip(models[len(models)//2:],models[:len(models)//2]))+[[models[-1]]]
        catalog_buttons = [[InlineKeyboardButton(j, callback_data=json.dumps({'cn':'add_item_brand','add_brand':j})) for j in i] for i in models]
        catalog_markup = InlineKeyboardMarkup(inline_keyboard=catalog_buttons)
        await app.send_message(message.chat.id, 'Alegeți brand', reply_markup=catalog_markup)

@app.on_callback_query(add_item_brand_callback)
async def catalog_input(_, query: CallbackQuery):
    mci = query.message.chat.id
    try:
        await app.delete_messages(mci, query.message.id)
    except Exception:
        pass
    data_json = json.loads(query.data)
    models = get_models(data_json['add_brand'])
    if len(models) % 2 == 0:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))
    else:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))+[[models[-1]]]
    sub_catalog_buttons = [[InlineKeyboardButton(j, callback_data=json.dumps({'cn':'add_item_model','sub_id':get_sub_id(j)}))for j in i] for i in models]
    sub_catalog_markup = InlineKeyboardMarkup(inline_keyboard=sub_catalog_buttons)
    await app.send_message(mci, 'Alegeți modelu',reply_markup=sub_catalog_markup)


@app.on_callback_query(add_item_model_callback)
async def sub_catalog_input(_, query: CallbackQuery):
    data = json.loads(query.data)
    
    data =json.dumps({
            'state':'name_input',
            'data':{
                    'sub_id':data['sub_id'],
                    }
            })
    set_state(query.message.chat.id, data)
    await app.send_message(query.message.chat.id,text='Scrieți numele complect a modelului..')
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state('name_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def name_input(_, message: Message):
    old_data = json.loads(get_state(message.chat.id))['data']
    
    data =json.dumps({
            'state':'photo_input',
            'data':{
                    'sub_id':old_data['sub_id'],
                    'name': message.text.capitalize()
                    }
            })
    set_state(message.chat.id, data)
    await app.send_message(message.chat.id, f'Numele produsului a fost introdus: {message.text}. Tremiteți o poza cu modelul.')

@app.on_message(filters.photo & state('photo_input'))
async def photo_input(_, message: Message):
    if not message.photo:
        await app.send_message(message.chat.id, 'Va rog, tremiteți o poza cu modelul.')
        return
    
    old_data = json.loads(get_state(message.chat.id))['data']
    photo_id = message.photo.file_id
    
    data =json.dumps({
            'state':'description_input',
            'data':{
                    'sub_id':old_data['sub_id'],
                    'name': old_data['name'],
                    'photo': photo_id
                    }
            })
    set_state(message.chat.id, data)
    await app.send_message(message.chat.id, 'Fotografia modelului salvată. Introduceți descrierile modelului.')





@app.on_message(state('description_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def description_input(_, message: Message):
    old_data = json.loads(get_state(message.chat.id))['data']
    
    data =json.dumps({
            'state':'price_input',
            'data':{
                    'sub_id':old_data['sub_id'],
                    'name': old_data['name'],
                    'photo': old_data['photo'],
                    'description': message.text
                    }
            })
    set_state(message.chat.id, data)
    await app.send_message(message.chat.id, 'Descriere modelului salvată. Introduceți prețul modelului.')


@app.on_message(state('price_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def price_input(_, message: Message):
    old_data = json.loads(get_state(message.chat.id))['data']
    
    try:
        price = float(message.text)
    except ValueError:
        await app.send_message(message.chat.id, 'Prețul trebuie să fie un număr. Introduceți prețul din nou.')
        return
    set_state(message.chat.id, json.dumps({'cn':'None'}))
    add_item(old_data['sub_id'], old_data['name'], price, old_data['description'], old_data['photo'])
    await app.send_message(message.chat.id, f'Numele: {old_data['name']}\nDescriere: {old_data['description']}\nPreț: {price} MDL')


@app.on_message(filters.command('menu') | filters.command('stop') | has_text('Anulare⬅'))
async def menu(_, message: Message):
    set_state(message.chat.id,json.dumps({'cn':'None'}))
    await send_menu(app, message.chat.id)

@app.on_message(filters.command('start'))
async def start(_, message: Message):
    args = message.text.split()
    user_id = message.from_user.id
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referrer_id = int(args[1][3:])
        except Exception:
            referrer_id = None
    # Регистрируем пользователя (с рефералом или без)
    if referrer_id and referrer_id != user_id:
        register_referral(user_id, referrer_id)
    else:
        register_referral(user_id, None)
    await app.send_message(
        message.chat.id,
        f'Buna <b>{message.from_user.first_name if message.from_user.first_name else ""} {message.from_user.last_name if message.from_user.last_name else ""}</b> \nAcest Bot vă prezintă gama completă de adidași din magazinul @Cross_Brand_md. Pentru a plasa o comandă, accesați „Catalog”, selectați modelul dorit de adidași și indicați detaliile destinatarului. După aceasta, așteptați un mesaj de la manager pentru confirmarea comenzii. \n\n<b>Important: pentru modelele de pe loc  și cele care sunt la reducere, livrarea se efectuează în 24-48 de ore; celelalte modele vor fi livrate în 3-5 zile lucrătoare.</b>\n\nPentru comenzi și întrebări, scrieți managerului @cross_brand_manager.'
    )
    set_state(message.chat.id, json.dumps({'cn': 'None'}))
    await send_menu_with_referral(app, message.chat.id)


@app.on_callback_query(brands_callback)
async def brand_callback(client, query:CallbackQuery):
    mci = query.message.chat.id
    try:
        await app.delete_messages(mci, query.message.id)
    except Exception:
        pass
    data_json = json.loads(query.data)
    brand = data_json['brand']
    models = get_models(brand)
    if len(models) % 2 == 0:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))
    else:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))+[[models[-1]]]
    sub_catalog_buttons = [[InlineKeyboardButton(j+f'[{len(get_id(get_sub_id(j)))}]', callback_data=json.dumps({'sub_id':get_sub_id(j), 'current':0}))for j in i] for i in models]
    # Добавляем кнопку "Показать всю обувь" только если моделей больше одной
    if len(get_models(brand)) > 1:
        sub_catalog_buttons.insert(0, [InlineKeyboardButton('Toate modele 👟', callback_data=json.dumps({'sub_id':f'all_{brand}', 'current':0}))])
    sub_catalog_buttons.append([InlineKeyboardButton('Înapoi⬅',callback_data=json.dumps({'cn':'catalog'}))])
    sub_catalog_markup = InlineKeyboardMarkup(inline_keyboard=sub_catalog_buttons)
    add_prev_data_state(query.message.chat.id,json.loads(query.data))
    await app.send_message(mci, 'Alegeți modelu',reply_markup=sub_catalog_markup)

@app.on_callback_query(models_callback)
async def model_callback(_, query:CallbackQuery):
    mci = query.message.chat.id

    data_json = json.loads(query.data)
    if data_json['sub_id'] == 'search':
        ids = get_prev_data_state(query.message.chat.id)["ids"]
    elif data_json["sub_id"] == "new":
        ids = get_new_item()
        if len(ids) == 0:
            await app.send_message(mci, 'Așteptați-vă la noi modele!')
            return
    elif str(data_json["sub_id"]).startswith("all_"):
        brand = data_json["sub_id"][4:]
        sub_ids = [get_sub_id(model) for model in get_models(brand)]
        ids = []
        for sub_id in sub_ids:
            ids.extend(get_id(sub_id))
        ids = [i[0] for i in cur.execute("SELECT id FROM items WHERE id IN ({}) ORDER BY add_time DESC".format(",".join(map(str, ids))))] if ids else []
        if len(ids) == 0:
            await app.send_message(mci, 'Error.')
            return
    else:
        ids = get_id(data_json['sub_id'])
        ids = [i[0] for i in cur.execute("SELECT id FROM items WHERE sub_id=? ORDER BY add_time DESC", (data_json['sub_id'],))]
    if len(ids) == 0:
        await app.send_message(mci, 'Scuzați,nu exictă nici un produs.')
        return
    item_id = ids[data_json['current']]

    curr = data_json['current']
    name, price, description, photo = get_item(item_id)
    if curr == len(ids)-1:
        curr = -1
    if curr == -len(ids):
        curr = 0
    curr_vis = ids.index(ids[curr])+1
    navigation_buttons = []
    prev_data = get_prev_data_state(query.message.chat.id)
    try:
        prev_data.pop("ids")
    except:
        pass
    if len(ids) > 1:
        navigation_buttons.append([InlineKeyboardButton('⬅️', callback_data=json.dumps({'sub_id':data_json['sub_id'],
                                                                            'current':curr-1,})),
        InlineKeyboardButton('➡️', callback_data=json.dumps({'sub_id':data_json['sub_id'],
                                                                            'current':curr+1,}))])
    navigation_buttons.append([InlineKeyboardButton('Plasați o comandă', callback_data=json.dumps({'cn':'order','data':{'order_id':item_id}}))])
    navigation_buttons.append([InlineKeyboardButton('Înapoi⬅',callback_data=json.dumps(prev_data))])
    navigation_markup = InlineKeyboardMarkup(navigation_buttons)
    caption = f'[{curr_vis} din {len(ids)}]\n<b>{name}</b>\n<b>Articul:</b>{item_id}\n<b>Descriere:</b>{description}\n<b>Preț:</b>{price}<b> MDL</b>'

    # Плавная навигация: если сообщение фото — меняем фото, иначе только подпись и клавиатуру
    if query.message.photo:
        try:
            await app.edit_message_media(
                chat_id=mci,
                message_id=query.message.id,
                media={"type": "photo", "media": photo, "caption": caption, "parse_mode": "html"},
                reply_markup=navigation_markup
            )
        except Exception:
            # Если не удалось, пробуем изменить только подпись и клавиатуру
            try:
                await app.edit_message_caption(
                    chat_id=mci,
                    message_id=query.message.id,
                    caption=caption,
                    reply_markup=navigation_markup,
                    parse_mode="html"
                )
            except Exception:
                msg = await app.send_photo(mci, photo, caption, reply_markup=navigation_markup)
                try:
                    await app.delete_messages(mci, query.message.id)
                except Exception:
                    pass
    else:
        try:
            await app.edit_message_caption(
                chat_id=mci,
                message_id=query.message.id,
                caption=caption,
                reply_markup=navigation_markup,
                parse_mode="html"
            )
        except Exception:
            msg = await app.send_photo(mci, photo, caption, reply_markup=navigation_markup)
            try:
                await app.delete_messages(mci, query.message.id)
            except Exception:
                pass

@app.on_callback_query(order_callback)
async def order(_, query: CallbackQuery):
    mci = query.message.chat.id
    order_id = json.loads(query.data)['data']['order_id']
    set_state(mci, json.dumps({'state':'order_name_input','data':{'order_id':order_id}}))
    await app.send_message(mci, 'Completați formularul de comandă:\nPrenumele și numele vostru:', reply_markup=cancel_kb)


@app.on_message(state('order_name_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def order_name(_, message: Message):
    mci = message.chat.id
    old_data = json.loads(get_state(mci))['data']
    data = json.dumps({
        'state':'order_size_input',
        'data':{
                'order_id':old_data['order_id'],
                'name':message.text.capitalize()
            }
        })
    set_state(mci, data)
    await app.send_message(mci, 'Introduceți numerul dvs. de telefon:')

@app.on_message(state('order_size_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def order_size(_, message: Message):
    mci = message.chat.id
    old_data = json.loads(get_state(mci))['data']
    data = json.dumps({
        'state':'order_number_input',
        'data':{
                'order_id':old_data['order_id'],
                'name':old_data['name'],
                'size':message.text
            }
        })
    set_state(mci, data)
    await app.send_message(mci, 'Introduceți mărimea:')

@app.on_message(state('order_number_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def order_number(_, message: Message):
    mci = message.chat.id
    old_data = json.loads(get_state(mci))['data']
    data = json.dumps({
        'state':'order_adress_input',
        'data':{
                'order_id':old_data['order_id'],
                'name':old_data['name'],
                'size':old_data['size'],
                'number':message.text
            }
        })
    set_state(mci, data)
    await app.send_message(mci, 'Introduceți orașul, raionul, strada:')

@app.on_message(state('order_adress_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def order_promo_ask(_, message: Message):
    mci = message.chat.id
    old_data = json.loads(get_state(mci))['data']
    # Сохраняем адрес
    data = {
        'order_id': old_data['order_id'],
        'name': old_data['name'],
        'size': old_data['size'],
        'number': old_data['number'],
        'adress': message.text
    }
    set_state(mci, json.dumps({'state': 'order_promo_input', 'data': data}))
    await app.send_message(mci, "Aveți un cod promoțional? Dacă da, introduceți его acum.\nDacă nu, scrieți „Nu”.")

@app.on_message(state('order_promo_input') & ~ has_text('Anulare⬅') & ~ filters.command('stop'))
async def order_complete_with_promo(_, message: Message):
    mci = message.chat.id
    state_data = json.loads(get_state(mci))
    data = state_data['data']
    promo_code = message.text.strip()
    discount = 0
    promo_info = None
    if promo_code.lower() != "nu":
        promo_info = check_promo_code(promo_code)
        if promo_info:
            discount = promo_info['discount']
            # Если single-use, удаляем промокод после использования
            if promo_info.get('single_use'):
                remove_promo_code(promo_code)
        else:
            await app.send_message(mci, "Cod promoțional invalid sau expirat. Comanda va fi procesată fără reducere.")
    set_state(mci, json.dumps({'cn': 'None'}))
    name, price, _, photo = get_item(data['order_id'])
    final_price = price
    if discount:
        final_price = round(price * (100 - discount) / 100, 2)
        discount_text = f"\n<b>Reducere aplicată:</b> -{discount}%\n<b>Preț cu reducere:</b> {final_price} MDL"
    else:
        discount_text = ""
    remove_order_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Anulare comandei', callback_data=json.dumps({'cn':'remove_order'}))]])
    for i in ADMIN_IDs:
        await app.send_photo(
            i,
            photo,
            f'Produs {name} este comandat \n'
            f'<b>Price: </b>{price}\n'
            f'<b>Numele: </b>{data["name"]}\n'
            f'<b>Telefon: </b>{data["size"]}\n'
            f'<b>Mărimea: </b>{data["number"]}\n'
            f'<b>Adresa: </b>{data["adress"]}'
            f'{discount_text}'
            f'\n<b>Contact: </b>@{message.from_user.username} | {message.from_user.mention}',
            reply_markup=remove_order_keyboard
        )
    await app.send_message(
        mci,
        f'<b>Comanda a fost înregistrată. Așteptați răspunsul managerului pentru a confirma comanda.</b> \n'
        f'{discount_text}\n'
        f'<a href="https://t.me/cross_brand_manager">Pentru întrebări, accesați aici…</a>'
    )

@app.on_callback_query(remove_order_callback)
async def remove_order(_, query: CallbackQuery):
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_callback_query(catalog_callback)
async def catalog(client, query: CallbackQuery):

    models = get_brands()
    models.remove('Reduceri')
    models.remove('Modele pe loc')
    models.remove('Articole noi in stoc')

    if len(models) % 2 == 0:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))
    else:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))+[[models[-1]]]
    catalog_buttons = [[InlineKeyboardButton('Modele pe loc ✅', callback_data=json.dumps({'brand':'Modele pe loc'}))],[InlineKeyboardButton('Reduceri 🔥', callback_data=json.dumps({'sub_id':188,"current":0}))],[InlineKeyboardButton('Articole noi in stoc ✨', callback_data=json.dumps({"sub_id":"new", "current":0}))]]
    catalog_buttons += [[InlineKeyboardButton(j, callback_data=json.dumps({'brand':j})) for j in i] for i in models]
    catalog_buttons.append([InlineKeyboardButton('Înapoi⬅',callback_data=json.dumps({'cn':'cancel'}))])
    catalog_markup = InlineKeyboardMarkup(inline_keyboard=catalog_buttons)
    await app.send_message(query.message.chat.id, 'Alegeți brandul', reply_markup=catalog_markup)
    add_prev_data_state(query.message.chat.id, {'cn':'catalog'})
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_callback_query(search_callback)
async def search(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({'state':'search'}))
    await app.send_message(query.message.chat.id,'Introduceți numele aproximativ sau articul produsului.', reply_markup=cancel_kb)

@app.on_message(admin & filters.command('remove_item'))
async def remove_item_command(_, message: Message):
    ids_item = message.text.split()[1:]
    if len(ids_item) == 0:
        await app.send_message(message.chat.id, 'Introduceți articul al produsului pentru anulare prin (SPACE). Exemplu:/remove_item 1 12 40 ')
        return
    for i in ids_item:
        remove_item(i)
    await app.send_message(message.chat.id, 'Produse sunt anulate')

@app.on_message(filters.command('get_chat_id'))
async def get_chat_id(_, message: Message):
    await app.send_message(message.chat.id,message.chat.id)

@app.on_message(admin & filters.command("admin"))
async def admin_panel(_, message: Message):
    buttons = [
        [InlineKeyboardButton("Adăugați produsul 🛒", callback_data=json.dumps({"cn":"add_item_panel"})),
         InlineKeyboardButton("Eliminați produsul 💣", callback_data=json.dumps({"cn":"remove_item_panel"}))],
        [InlineKeyboardButton("Adăugați brand 👟", callback_data=json.dumps({"cn":"add_category_panel"})),
         InlineKeyboardButton("Eliminați brand 💣", callback_data=json.dumps({"cn":"remove_category_panel"}))],
        [InlineKeyboardButton("Adăugați modelul 👀", callback_data=json.dumps({"cn":"add_subcategory_panel"})),
         InlineKeyboardButton("Eliminați modelul 💣", callback_data=json.dumps({"cn":"remove_subcategory_panel"}))],
        [InlineKeyboardButton("News 📰", callback_data=json.dumps({"cn":"send_news_panel"}))],
        [InlineKeyboardButton("Promo 🎫", callback_data=json.dumps({"cn": "promo_panel"}))]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await app.send_message(message.chat.id, "Admin panel ⚙️", reply_markup=markup)

    # Добавляем обработчик для promo_panel, который вызывает ту же логику, что и /promo
    @app.on_callback_query(
        filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "promo_panel" if q.data else False))
    async def promo_panel_callback(_, query: CallbackQuery):
        # Просто вызываем функцию promo_admin_entry с тем же message.chat.id
        class DummyMsg:
            def __init__(self, chat_id):
                self.chat = type("obj", (), {"id": chat_id})()
                self.message_id = None

        await promo_admin_entry(_, DummyMsg(query.message.chat.id))

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "add_item_panel" if q.data else False))
async def add_item_panel_callback(_, query: CallbackQuery):
    # Повторяет действия команды /add_item
    models = get_brands()
    if len(models) % 2 == 0:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))
    else:
        models = list(zip(models[len(models)//2:],models[:len(models)//2]))+[[models[-1]]]
    catalog_buttons = [[InlineKeyboardButton(j, callback_data=json.dumps({'cn':'add_item_brand','add_brand':j})) for j in i] for i in models]
    catalog_markup = InlineKeyboardMarkup(inline_keyboard=catalog_buttons)
    await app.send_message(query.message.chat.id, 'Alegeți brand', reply_markup=catalog_markup)
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

# --- Добавление категории ---
@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "add_category_panel" if q.data else False))
async def add_category_panel_callback(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({"state": "add_category_input"}))
    await app.send_message(query.message.chat.id, "Introduceți un nume pentru nou brand")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state("add_category_input"))
async def add_category_input(_, message: Message):
    brand = message.text.strip()
    # Добавление категории (бренда)
    cur.execute("INSERT INTO model_brand (brand, model) VALUES (?, ?)", (brand, ""))  # пустая модель для категории
    con.commit()
    set_state(message.chat.id, json.dumps({'cn':'None'}))
    await app.send_message(message.chat.id, f'Brand "{brand}" a fost adăugat.')

# --- Удаление категории ---
@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "remove_category_panel" if q.data else False))
async def remove_category_panel_callback(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({"state": "remove_category_input"}))
    await app.send_message(query.message.chat.id, "Introduceți numele brendul pe care doriți să o ștergeți")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state("remove_category_input"))
async def remove_category_input(_, message: Message):
    brand = message.text.strip()
    cur.execute("DELETE FROM model_brand WHERE brand=? AND (model='' OR model IS NULL)", (brand,))
    con.commit()
    set_state(message.chat.id, json.dumps({'cn':'None'}))
    await app.send_message(message.chat.id, f'Brand "{brand}" a fost adăugat.')

# --- Добавление подкатегории ---
@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "add_subcategory_panel" if q.data else False))
async def add_subcategory_panel_callback(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({"state": "add_subcategory_input"}))
    await app.send_message(query.message.chat.id, "Introduceți numele de brand și numele de modelul separate prin virgule (exemplu: Nike, Air Max)")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state("add_subcategory_input"))
async def add_subcategory_input(_, message: Message):
    try:
        brand, model = [x.strip() for x in message.text.split(",", 1)]
    except Exception:
        await app.send_message(message.chat.id, "Error. Vă rugăm să introduceți următorul format: Brand, Model.")
        return
    cur.execute("INSERT INTO model_brand (brand, model) VALUES (?, ?)", (brand, model))
    con.commit()
    set_state(message.chat.id, json.dumps({'cn':'None'}))
    await app.send_message(message.chat.id, f'Modelul „{model}” pentru categoria „{brand}” a fost adăugată.')

# --- Удаление подкатегории ---
@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "remove_subcategory_panel" if q.data else False))
async def remove_subcategory_panel_callback(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({"state": "remove_subcategory_input"}))
    await app.send_message(query.message.chat.id, "Introduceți numele de brand și numele de modelul separate prin virgule (exemplu: Nike, Air Max)")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state("remove_subcategory_input"))
async def remove_subcategory_input(_, message: Message):
    try:
        brand, model = [x.strip() for x in message.text.split(",", 1)]
    except Exception:
        await app.send_message(message.chat.id, "Eroare de format. Vă rugăm să introduceți următorul format: Categorie, Subcategorie.")
        return
    cur.execute("DELETE FROM model_brand WHERE brand=? AND model=?", (brand, model))
    con.commit()
    set_state(message.chat.id, json.dumps({'cn':'None'}))
    await app.send_message(message.chat.id, f'Modelul „{model}” pentru categoria „{brand}” a fost adăugată.')

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "remove_item_panel" if q.data else False))
async def remove_item_panel_callback(_, query: CallbackQuery):
    # Повторяет действия команды /remove_item
    await app.send_message(query.message.chat.id, 'Introduceți articolele produselor pentru anulare prin (SPACE). Exemplu:/remove_item 1 12 40 ')
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "send_news_panel" if q.data else False))
async def send_news_panel_callback(_, query: CallbackQuery):
    set_state(query.message.chat.id ,json.dumps({"state": "news_input"}))
    await app.send_message(query.message.chat.id, "Scrie știrea și o voi trimite tuturor clienților")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

# --- Система скидок / промокодов: админ-инструменты (добавлено внизу файла) ---

@app.on_message(admin & filters.command("promo"))
async def promo_admin_entry(_, message):
    """Команда для открытия панели управления промокодами (для админов)."""
    buttons = [
        [InlineKeyboardButton("Adăugați cod ➕", callback_data=json.dumps({"cn":"promo_add_panel"})),
         InlineKeyboardButton("Lista codurilor 📋", callback_data=json.dumps({"cn":"promo_list"}))],
        [InlineKeyboardButton("Eliminați codul ❌", callback_data=json.dumps({"cn":"promo_remove_panel"})),
         InlineKeyboardButton("Anulare ⬅", callback_data=json.dumps({"cn":"cancel"}))]
    ]
    await app.send_message(message.chat.id, "Panou de control al codurilor promoționale:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "promo_add_panel" if q.data else False))
async def promo_add_panel(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({"state":"promo_add_input"}))
    await app.send_message(query.message.chat.id, "Introduceți codul promoțional în formatul: COD, REDUCERE(%), ZILE(days), [single]\nExemplu: REDUCERE20 20 30\nAdăugați cuvântul „single” la sfârșit dacă codul trebuie să fie de unică folosință.")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state("promo_add_input"))
async def promo_add_input(_, message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 3:
            await message.reply("Error. Exemplu: CODE DISCOUNT DAYS")
            set_state(message.chat.id, json.dumps({'cn':'None'}))
            return
        code = parts[0]
        discount = int(parts[1])
        days = int(parts[2])
        single = False
        if len(parts) > 3 and parts[3].lower() == "single":
            single = True
        add_promo_code(code, discount, days, single)
        await message.reply(f"Codul {code.upper()} a fost adăugat: {discount}% pe {days} zile{' (single-use)' if single else ''}.")
    except ValueError:
        await message.reply("Ошибка: discount и days должны быть целыми числами.")
    except Exception as e:
        await message.reply("Произошла ошибка при добавлении промокода.")
    finally:
        set_state(message.chat.id, json.dumps({'cn':'None'}))

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "promo_list" if q.data else False))
async def promo_list_callback(_, query: CallbackQuery):
    try:
        rows = list_promo_codes()
        if not rows:
            await app.send_message(query.message.chat.id, "None.")
            return
        text_lines = []
        for code, discount, valid_until, single in rows:
            text_lines.append(f"{code} — {discount}% — до {__import__('datetime').datetime.fromtimestamp(valid_until).strftime('%d.%m.%Y')} {'(single)' if single else ''}")
        await app.send_message(query.message.chat.id, "List:\n" + "\n".join(text_lines))
    except Exception:
        await app.send_message(query.message.chat.id, "Error.")

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "promo_remove_panel" if q.data else False))
async def promo_remove_panel(_, query: CallbackQuery):
    set_state(query.message.chat.id, json.dumps({"state":"promo_remove_input"}))
    await app.send_message(query.message.chat.id, "Introduceți codul promoțional pentru ștergere (exemplu: SALE20)")
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_message(state("promo_remove_input"))
async def promo_remove_input(_, message):
    code = message.text.strip()
    try:
        remove_promo_code(code)
        await message.reply(f"Codul {code.upper()} a fost utilizat.")
    except Exception:
        await message.reply("Error.")
    finally:
        set_state(message.chat.id, json.dumps({'cn':'None'}))

# --- Реферальная система ---

from db import register_referral, get_referrals, get_referrer, has_used_referral_bonus, mark_referral_bonus_used
from keyboard import send_menu_with_referral

REFERRAL_BONUS = 5  # размер бонуса за приглашение (можно менять)

@app.on_message(filters.command("referral"))
async def referral_info(_, message):
    user_id = message.from_user.id
    link = f"https://t.me/{(await app.get_me()).username}?start=ref{user_id}"
    referrals = get_referrals(user_id)
    text = f"Linkul dumneavoastră de recomandare:\n{link}\n\n"
    text += f"Voi aţi invitat: {len(referrals)} utilizatori.\n"
    if referrals:
        text += "ID-ul invitatului: " + ", ".join(map(str, referrals))
    await app.send_message(message.chat.id, text)

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "referral_menu" if q.data else False))
async def referral_menu_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    link = f"https://t.me/{(await app.get_me()).username}?start=ref{user_id}"
    referrals = get_referrals(user_id)
    text = f"Linkul dumneavoastră de recomandare:\n{link}\n\n"
    text += f"Voi aţi invitat: {len(referrals)} utilizatori.\n"
    if referrals:
        text += "ID: " + ", ".join(map(str, referrals))
    # Кнопка возврата в меню
    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Înapoi la meniu", callback_data=json.dumps({"cn": "back_to_menu"}))]])
    await app.send_message(query.message.chat.id, text, reply_markup=back_markup)
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

@app.on_callback_query(filters.create(lambda _, __, q: json.loads(q.data).get("cn") == "back_to_menu" if q.data else False))
async def back_to_menu_callback(_, query: CallbackQuery):
    await send_menu(app, query.message.chat.id)
    try:
        await app.delete_messages(query.message.chat.id, query.message.id)
    except Exception:
        pass

# --- Использование бонуса при заказе (пример: скидка при первом заказе) ---
# Вставьте этот код в order_complete_with_promo после расчёта скидки, если хотите давать бонус за реферала

# Пример:
# referrer_id = get_referrer(mci)
# if referrer_id and not has_used_referral_bonus(mci):
#     final_price = max(0, final_price - REFERRAL_BONUS)
#     mark_referral_bonus_used(mci)
#     await app.send_message(mci, f"Вам применён реферальный бонус {REFERRAL_BONUS} MDL!")
#     await app.send_message(referrer_id, f"Ваш приглашённый совершил покупку! Вам начислен бонус.")

# --- Конец реферальной системы ---

# --- Safety wrapper: перехват ошибок при отправке сообщений/фото (не менять вызовы в коде) ---
# (предыдущая версия использовала @app.on_startup() — у Client такого декоратора нет; применяем сразу)

try:
    # Попробовать наиболее вероятные места расположения исключения в разных версиях Pyrogram
    from pyrogram.errors.exceptions.bad_request_400 import InputUserDeactivated
except Exception:
    try:
        from pyrogram.errors import InputUserDeactivated
    except Exception:
        InputUserDeactivated = None

# Сохраняем оригинальные методы (будут заменены далее)
_original_send_photo = None
_original_send_message = None

async def _safe_send_photo(chat_id, *args, **kwargs):
    try:
        if _original_send_photo is None:
            return None
        return await _original_send_photo(chat_id, *args, **kwargs)
    except Exception as e:
        if InputUserDeactivated is not None and isinstance(e, InputUserDeactivated):
            try:
                if 'ADMIN_IDs' in globals() and chat_id in ADMIN_IDs:
                    try:
                        ADMIN_IDs.remove(chat_id)
                    except Exception:
                        pass
                try:
                    remove_user(chat_id)
                except Exception:
                    pass
            except Exception:
                pass
            return None
        raise

async def _safe_send_message(chat_id, *args, **kwargs):
    try:
        if _original_send_message is None:
            return None
        return await _original_send_message(chat_id, *args, **kwargs)
    except Exception as e:
        if InputUserDeactivated is not None and isinstance(e, InputUserDeactivated):
            try:
                if 'ADMIN_IDs' in globals() and chat_id in ADMIN_IDs:
                    try:
                        ADMIN_IDs.remove(chat_id)
                    except Exception:
                        pass
                try:
                    remove_user(chat_id)
                except Exception:
                    pass
            except Exception:
                pass
            return None
        raise

# Применяем монки‑патч немедленно — сохраняем оригиналы и заменяем методы клиента до app.run()
try:
    _original_send_photo = getattr(app, "send_photo", None)
    _original_send_message = getattr(app, "send_message", None)
    try:
        if _original_send_photo:
            app.send_photo = _safe_send_photo  # type: ignore
    except Exception:
        pass
    try:
        if _original_send_message:
            app.send_message = _safe_send_message  # type: ignore
    except Exception:
        pass
except Exception:
    pass

# --- Конец добавленного кода для безопасной отправки ---

print('running...')
app.run()
