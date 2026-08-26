from logger import add_log
import json
import os
from datetime import datetime, date

PUSH_STATUS = 1

'''
PUSH_TIMES = 0

def daily_reset_push_times():
    global PUSH_TIMES
    add_log(f"PUSH_TIMES = {PUSH_TIMES}")
    PUSH_TIMES = 0
    add_log(f"PUSH_TIMES = {PUSH_TIMES}")
'''

STATE_FILE = "stable_json/runtime_state.json"
PUSH_TIMES = 0
PUSH_LIVE_TIMES = 0

def load_push_times():
    global PUSH_TIMES
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") == str(date.today()):
                    PUSH_TIMES = data.get("push_times", 0)
                    PUSH_LIVE_TIMES = data.get("push_live_times", 0)
                    add_log(f"[STATE] Loaded PUSH_TIMES = {PUSH_TIMES}")
                    add_log(f"[STATE] Loaded PUSH_LIVE_TIMES = {PUSH_LIVE_TIMES}")
                    return PUSH_TIMES, PUSH_LIVE_TIMES
        except Exception as e:
            add_log(f"[ERROR] Failed to load runtime_state.json: {e}")

    PUSH_TIMES = 0
    PUSH_LIVE_TIMES = 0
    save_push_times(PUSH_TIMES, PUSH_LIVE_TIMES)
    add_log(f"[STATE] Initialized runtime_state.json for today. PUSH_TIMES and PUSH_LIVE_TIMES set to 0.")
    return PUSH_TIMES, PUSH_LIVE_TIMES

def save_push_times(times1, times2):
    global PUSH_TIMES, PUSH_LIVE_TIMES
    PUSH_TIMES = times1
    PUSH_LIVE_TIMES = times2
    data = {"date": str(date.today()), "push_times": PUSH_TIMES, "push_live_times": PUSH_LIVE_TIMES}
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        add_log(f"[ERROR] Failed to save runtime_state.json: {e}")

def increment_push_times():
    global PUSH_TIMES, PUSH_LIVE_TIMES
    PUSH_TIMES += 1
    PUSH_LIVE_TIMES += 1
    save_push_times(PUSH_TIMES, PUSH_LIVE_TIMES)
    add_log(f"[UPDATE] PUSH_TIMES = {PUSH_TIMES}, PUSH_LIVE_TIMES = {PUSH_LIVE_TIMES}")

def increment_dynamic_push_times():
    global PUSH_TIMES, PUSH_LIVE_TIMES
    PUSH_TIMES += 1
    # PUSH_LIVE_TIMES += 1
    save_push_times(PUSH_TIMES, PUSH_LIVE_TIMES)
    add_log(f"[UPDATE] PUSH_TIMES = {PUSH_TIMES}, PUSH_LIVE_TIMES = {PUSH_LIVE_TIMES}")

def daily_reset_push_times():
    global PUSH_TIMES, PUSH_LIVE_TIMES
    PUSH_TIMES = 0
    PUSH_LIVE_TIMES = 0
    save_push_times(0, 0)
    add_log(f"[RELOAD] PUSH_TIMES = 0, PUSH_LIVE_TIMES = 0")