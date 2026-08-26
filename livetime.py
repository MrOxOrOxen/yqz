from datetime import datetime
import shutil
import os
import time
import asyncio

LIVETIME_FILE = "stable_json/livetime.json"

async def load_livetime(start_time):
    now = int(time.time())
    now_str = datetime.now().strftime("%H%M")
    now_day = datetime.now().day
    if now_day == 1 and now_str < "0800":
        today_zero = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = int(today_zero.timestamp())
    try:
        with open(LIVETIME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            livetime = data["livetime"] + (now - start_time)
            livetime_hours = livetime // 3600
            livetime_mins = (livetime % 3600) // 60
            return livetime_hours, livetime_mins
    except Exception as e:
        add_log(f"读取 livetime.json 失败: {e}")

async def load_livedays(start_time):
    today = datetime.now().strftime("%Y%m%d")
    start_day = datetime.fromtimestamp(start_time).strftime("%Y%m%d")
    if today != start_day and datetime.now().day == 1:
        start_day = today
    with open(LIVETIME_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if start_day in data["exactday"]:
            return data["liveday"]
        else:
            return data["liveday"] + 1

async def save_livetime(start_time, end_time):
    livetime = end_time - start_time
    start_dt = datetime.fromtimestamp(start_time)
    end_dt = datetime.fromtimestamp(end_time)
    
    end_timestr = end_dt.strftime("%Y%m%d %H:%M:%S")
    start_timestr = start_dt.strftime("%Y%m%d %H:%M:%S")
    start_month = start_dt.month
    start_day = start_dt.strftime("%Y%m%d")

    if livetime >= 1800:
        retry_count = 0
        while not os.path.exists(LIVETIME_FILE) and retry_count < 3:
            await asyncio.sleep(5)
            retry_count += 1

        if not os.path.exists(LIVETIME_FILE):
            add_log(f"[ERROR] LIVETIME_FILE reset time saving: {start_timestr} - {end_timestr}")
            return

        try:
            with open(LIVETIME_FILE, "r+", encoding="utf-8") as f:
                data = json.load(f)

                now = datetime.now()
                if now.day == 1 and start_dt.day != 1:
                    today_zero = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    zero_timestamp = int(today_zero.timestamp())
                    
                    data["livetime"] = data.get("livetime", 0) + (end_time - zero_timestamp)
                    if start_day not in data.get("exactday", []) and start_month == now.month:
                        data["exactday"].append(start_day)
                else:
                    data["livetime"] = data.get("livetime", 0) + livetime
                    if start_day not in data.get("exactday", []):
                        data["exactday"].append(start_day)

                data["exacttime"].append(f"{start_timestr} - {end_timestr}")
                data["liveday"] = len(data.get("exactday", []))

                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.truncate()

        except Exception as e:
            add_log(f"[ERROR] Failed to update {LIVETIME_FILE}: {start_timestr} - {end_timestr}: {e}")

async def save_cross_month(start_time):
    if start_time != 0:
        try:
            with open(LIVETIME_FILE, "w", encoding="utf-8") as f:
                today_zero = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                zero_timestamp = int(zero_timestamp.timestamp())
                data = json.load(f)
                data["livetime"] = data["livetime"] + zero_timestamp - start_time
                if start_day not in data["exactday"]:
                    data["exactday"].append(start_day)
                data["exacttime"].append(f"{start_timestr} - {zero_timestamp}")
                data["liveday"] = len(data["exactday"])
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            add_log(f"[ERROR] Failed to json dump in livetime.json: {start_timestr} - {end_timestr}: {e}")

    now = datetime.now()
    year, month = now.year, now.month
    last_year = year - 1 if month == 1 else year
    last_month = 12 if month == 1 else month - 1
    yymm_str = f"{last_year % 100:02d}{last_month:02d}"
    src_dir = LIVETIME_FILE
    dst_dir = f"history_files/livetime/livetime{yymm_str}.json"
    shutil.move(src_dir, dst_dir)

    if not os.path.exists(LIVETIME_FILE):
        os.makedirs(os.path.dirname(LIVETIME_FILE), exist_ok=True)
    data = {
        "month": datetime.now().strftime("%Y%m"),
        "livetime": 0,
        "liveday": 0,
        "exacttime": [],
        "exactday": []
    }
    with open(LIVETIME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
