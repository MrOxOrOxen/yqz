import json, os, random
from memory_store import *
from constants import *
from logger import add_log, log_buffer

def load_json_files():
    json_map = {
        "files/box.json": ("box", MEMORY),
        "files/gift.json": ("gift", MEMORY),
        "files/all.json": ("all", MEMORY),
        # "files/meta.json": ("meta", MEMORY),
        # "files/audience.json": ("audience", MEMORY)
    }

    if not os.path.exists("files"):
        os.makedirs("files")

    meta_path = "files/meta.json"
    audience_path = "files/audience.json"
    
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                MEMORY["meta"]["live_time"] = data.get("live_time", 0)
                MEMORY["meta"]["total_battery"] = data.get("total_battery", 0)
                # MEMORY["meta"]["total_danmu_cnt_from_start"] = data.get("total_danmu_cnt_from_start", 0)
                MEMORY["meta"]["total_danmu_cnt_from_start"] = data.get("total_danmu_cnt_from_start", 0)
                MEMORY["meta"]["is_loss_warning_sent"] = data.get("is_loss_warning_sent", False)
                MEMORY["meta"]["is_whole_profit_msg_sent"] = data.get("is_whole_profit_msg_sent", False)
                MEMORY["meta"]["next_threshold"] = data.get("next_threshold", random.randint(4000, 5000))
                MEMORY["meta"]["current_gear"] = data.get("current_gear", 0)
                MEMORY["meta"]["dog"] = data.get("dog", 0)
                MEMORY["meta"]["is_birthday_msg_sent"] = data.get("is_birthday_msg_sent", False)
                MEMORY["meta"]["is_kfc_msg_sent"] = data.get("is_kfc_msg_sent", False)
                MEMORY["meta"]["is_castle_msg_sent"] = data.get("is_castle_msg_sent", False)
                MEMORY["meta"]["is_huli_egg_sent"] = data.get("is_huli_egg_sent", False)
                add_log(f"Total battery from history file: {MEMORY['meta']['total_battery']}")
                add_log(f"Next battery threshold: {MEMORY['meta']['next_threshold']}")
        except Exception as e:
            add_log(f"[ERROR] Error when reading meta.json: {e}")
            MEMORY["meta"]["total_battery"] = 0
    else:
        MEMORY["meta"]["live_time"] = 0
        MEMORY["meta"]["total_battery"] = 0
        add_log("No meta.json. Total battery starts with 0")
        MEMORY["meta"]["next_threshold"] = random.randint(4000, 5000)
        add_log(f"Next battery threshold: {MEMORY['meta']['next_threshold']}")

    if os.path.exists(audience_path):
        try:
            with open(audience_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                MEMORY["audience"] = {
                    "total_audience": data.get("total_audience", 0),
                    "interact_cache": data.get("interact_cache", [])
                }
                interact_cache.clear()
                interact_cache.update(data.get("interact_cache", []))
                add_log(f"Loaded interact_cache with {len(interact_cache)} entries.")
        except Exception as e:
            add_log(f"[ERROR] Error when reading audience.json: {e}")

    else:
        MEMORY["audience"] = {"total_audience": 0, "interact_cache": []}
        interact_cache.clear()
        save_json("files/audience.json", MEMORY["audience"])
        add_log("No audience.json. Total audience starts with 0")


    for file_path, (key, target) in json_map.items():
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                target[key] = data
                add_log(f"Loaded file: {file_path}")
            else:
                if isinstance(target[key], dict): target[key].clear()
                elif isinstance(target[key], list): target[key][:] = []
                add_log(f"Detected file deletion: {file_path}, memory cleared.")
        except Exception as e:
            print(f"Error: {e}")

    log_buffer.load_from_file("files/log.json")

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def append_to_jsonl(filename, data_list):
    if not data_list: return
    with open(filename, "a", encoding="utf-8") as f:
        for item in data_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")