import os
import json
from logger import add_log
from json_handle import save_json
from memory_store import birthday_cache

BIRTHDAY_CACHE_FILE = "stable_json/birthday_cache.json"

def load_birthday_cache():
    global birthday_cache
    if os.path.exists(BIRTHDAY_CACHE_FILE):
        try:
            with open(BIRTHDAY_CACHE_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                birthday_cache = set(data)
            else:
                birthday_cache = set()
        except Exception as e:
            add_log(f"读取 birthday_cache.json 失败: {e}")
            birthday_cache = set()
    else:
        birthday_cache = set()
        try:
            with open(BIRTHDAY_CACHE_FILE, "w", encoding='utf-8') as f:
                json.dump([], f)
        except Exception as e:
            add_log(f"创建 birthday_cache.json 失败: {e}")

def save_birthday_cache():
    save_json(BIRTHDAY_CACHE_FILE, list(birthday_cache))

def daily_reset_birthday_cache():
    birthday_cache.clear()
    save_birthday_cache()
    add_log("[定时任务] birthday_cache.json 已在 0:00 定时清空")