from sqlite3 import connect
from rapidfuzz import fuzz
import json
from time import time
cur = None
con = None

def init():
    global cur, con
    con = connect("shop.db")
    cur = con.cursor()
    
    cur.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER, sub_id INTEGER,full_name TEXT,price INTEGER,photo TEXT,description TEXT,PRIMARY KEY(id AUTOINCREMENT))")
    cur.execute("CREATE TABLE IF NOT EXISTS model_brand (id INTEGER, brand TEXT,model TEXT,PRIMARY KEY(id AUTOINCREMENT))")
    cur.execute("CREATE TABLE IF NOT EXISTS user_states(chat_id INTEGER PRIMARY KEY, state TEXT)")

def remove_user(chat_id):
    cur.execute("DELETE FROM user_states WHERE chat_id==?",(chat_id,))
    con.commit()

def get_all_users():
    results = cur.execute("SELECT chat_id FROM user_states")
    return [i[0] for i in results.fetchall()]

def get_new_item():
    results = cur.execute("SELECT id FROM items WHERE add_time > ?",(int(time())-864000,))
    return [i[0] for i in results.fetchall()]

def get_item(item_id:int):
    result = cur.execute("SELECT full_name, price, description, photo FROM items WHERE id==?",(item_id,))
    return result.fetchone()

def get_id(sub_id: int):
    result = cur.execute("SELECT id FROM items WHERE sub_id==?",(sub_id,))
    return [i[0] for i in result.fetchall()]

def get_names(sub_id: int):
    result = cur.execute("SELECT name FROM items WHERE sub_id==?",(sub_id,))
    return [i[0] for i in result.fetchall()]

def get_models(brand):
    result = cur.execute("SELECT model FROM model_brand WHERE brand==? ORDER BY id ASC",(brand,))
    return list(dict.fromkeys(([i[0] for i in result.fetchall()])))

def get_brands():
    result = cur.execute("SELECT brand, id FROM model_brand")
    return list(dict.fromkeys([i[0] for i in result.fetchall()]))

def add_item(sub_id, name, price, description, photo): 
    cur.execute("REPLACE INTO items(sub_id, full_name, price, description, photo, add_time) VALUES(?,?,?,?,?,?)", (sub_id, name, price, description, photo, int(time())))
    con.commit()

def search_items(search_text):
    result = cur.execute('SELECT full_name, id FROM items')
    names = result.fetchall()
    results = []
    for i in names:
        if fuzz.ratio(search_text.capitalize(),i[0]) > 25:
            results.append(i)
    return results
def get_state(chat_id):
    cur.execute('SELECT state FROM user_states WHERE chat_id = ?', (chat_id,))
    state = cur.fetchone()
    # Если нет состояния, возвращаем корректный JSON
    return state[0] if state and state[0] and state[0].strip() != "" else '{"state": "None"}'

def set_state(chat_id, state):
    cur.execute('REPLACE INTO user_states (chat_id, state) VALUES (?, ?)', (chat_id, state))
    con.commit()

def remove_item(item_id):
    cur.execute("DELETE FROM items WHERE id=?",(item_id,))
    con.commit()

def get_sub_id(model):
    cur.execute('SELECT id FROM model_brand WHERE model = ?', (model,))
    state = cur.fetchone()
    return state[0]

def get_brand(sub_id):
    cur.execute('SELECT brand FROM model_brand WHERE sub_id = ?', (sub_id,))
    state = cur.fetchone()
    return state[0]

def add_prev_data_state(chat_id, prev_data):
    data = get_state(chat_id)
    
    if data == "None":
        data = "{}"
    data = json.loads(data)
    data["prev_data"] = prev_data
    set_state(chat_id, json.dumps(data))

def get_prev_data_state(chat_id):
    data = json.loads(get_state(chat_id))
    return data["prev_data"] if "prev_data" in data else json.dumps({"cn":"None"})

def get_hidden_brands(chat_id):
    state = get_state(chat_id)
    if not state or state == "None":
        return []
    data = json.loads(state)
    return data.get("hidden_brands", [])

def get_hidden_models(chat_id):
    state = get_state(chat_id)
    if not state or state == "None":
        return []
    data = json.loads(state)
    return data.get("hidden_models", [])

def get_last_orders(limit=5):
    # Заглушка: реализуйте хранение заказов для расширения функционала
    return []

def ensure_promo_table():
    """Создаёт таблицу promo_codes, если её ещё нет.
       Безопасно: не выполняется до инициализации con/cur."""
    if con is None or cur is None:
        return
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount INTEGER,          -- процент скидки, 0-100
            valid_until INTEGER,       -- unix timestamp
            single_use INTEGER DEFAULT 0 -- 0флаг единовременного промокода (/1)
        )
    """)
    con.commit()

def add_promo_code(code: str, discount: int, valid_days: int, single_use: bool = False):
    """Добавляет промокод: code, процент discount, срок действия в днях, флаг single_use."""
    valid_until = int(time()) + int(valid_days) * 86400
    cur.execute("REPLACE INTO promo_codes (code, discount, valid_until, single_use) VALUES (?, ?, ?, ?)",
                (code.strip().upper(), int(discount), valid_until, 1 if single_use else 0))
    con.commit()

def check_promo_code(code: str):
    """Возвращает (discount, single_use) если код действителен, иначе None."""
    if not code:
        return None
    row = cur.execute("SELECT discount, valid_until, single_use FROM promo_codes WHERE code = ?", (code.strip().upper(),)).fetchone()
    if not row:
        return None
    discount, valid_until, single_use = row
    if int(valid_until) < int(time()):
        return None
    return {"discount": int(discount), "single_use": bool(single_use)}

def remove_promo_code(code: str):
    """Удаляет промокод по коду."""
    cur.execute("DELETE FROM promo_codes WHERE code = ?", (code.strip().upper(),))
    con.commit()

def list_promo_codes():
    """Возвращает список всех промокодов: [(code, discount, valid_until, single_use), ...]"""
    rows = cur.execute("SELECT code, discount, valid_until, single_use FROM promo_codes ORDER BY valid_until DESC").fetchall()
    return rows

# инициализация уже выполнена выше; создаём таблицу промокодов сейчас только если БД уже инициализирована
if con is not None and cur is not None:
    ensure_promo_table()
