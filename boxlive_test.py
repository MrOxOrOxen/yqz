import asyncio
import time
import json
import ssl
import aiohttp
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bilibili_api import live, sync, Credential
from bilibili_api.live import LiveDanmaku
from data import SESSDATA, BILI_JCT, BUVID3
credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

ROOM_ID = 27885573

MEMORY = {
    "box": {},
    "gift": {},
    "all": []
}

LOG_BUFFER = []
last_query_time = {}
last_global_reply = 0

last_gift_save = 0
last_log_save = 0

def load_json_files():
    json_map = {
        "files/box.json": ("box", MEMORY),
        "files/gift.json": ("gift", MEMORY),
        "files/all.json": ("all", MEMORY),
    }

    if not os.path.exists("files"):
        os.makedirs("files")

    for file_path, (key, target) in json_map.items():
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                target[key] = data
            else:
                # target[key] = {} if isinstance(target[key], dict) else []
                if isinstance(target[key], dict): target[key].clear()
                elif isinstance(target[key], list): target[key][:] = []
                add_log(f"Detected file deletion: {file_path}, memory cleared.")
        except Exception as e:
            print(f"Error: {e}")

    try:
        log_path = "files/log.json"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                global LOG_BUFFER
                LOG_BUFFER = json.load(f)
        else:
            pass
    except Exception as e:
        print(f"Error: {e}")

def add_log(msg):
    global LOG_BUFFER
    LOG_BUFFER.append({
        "time": int(time.time()),
        "msg": msg
    })
    LOG_BUFFER = LOG_BUFFER[-10:]
    print("[LOG]", msg)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def update_gift(uid, uname, gift_name, num, battery):
    uid = str(uid)

    if uid not in MEMORY["gift"]:
        MEMORY["gift"][uid] = {
            "uid": int(uid),
            "uname": uname,
            "gift_list": {},
            "profit": 0
        }

    user = MEMORY["gift"][uid]
    user["uname"] = uname
    user["profit"] += battery

    if gift_name:
        user["gift_list"][gift_name] = \
            user["gift_list"].get(gift_name, 0) + num


def update_box(uid, uname, count, cost_battery, profit_battery):
    uid = str(uid)

    if uid not in MEMORY["box"]:
        MEMORY["box"][uid] = {
            "uid": int(uid),
            "uname": uname,
            "count": 0,
            "cost": 0,
            "profit": 0
        }

    user = MEMORY["box"][uid]
    user["uname"] = uname
    user["count"] += count
    user["cost"] += cost_battery
    user["profit"] += profit_battery


def update_all(battery):
    MEMORY["all"].append({
        "time": int(time.time()),
        "battery": battery
    })

def on_gift_saved():
    add_log("HTML refresh triggered")

async def periodic_tasks():
    global last_gift_save, last_log_save

    while True:
        now = time.time()

        # gift.json
        if now - last_gift_save > 60:
            save_json("files/gift.json", MEMORY["gift"])
            save_json("files/all.json", MEMORY["all"])
            last_gift_save = now
            add_log("gift.json saved")
            on_gift_saved()

        # log.json
        if now - last_log_save > 5:
            save_json("files/log.json", LOG_BUFFER)
            last_log_save = now

        await asyncio.sleep(1)

# patch ssl
def patch_ssl():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    orig_init = aiohttp.TCPConnector.__init__

    def new_init(self, *args, **kwargs):
        kwargs['ssl'] = ssl_context
        orig_init(self, *args, **kwargs)

    aiohttp.TCPConnector.__init__ = new_init

patch_ssl()

async def send_reply(room_id, content, reply_uid=None):
    url = "https://api.live.bilibili.com/msg/send"

    payload = {
        "bubble": "0",
        "msg": content,
        "color": "16777215",
        "mode": "1",
        "fontsize": "25",
        "rnd": int(time.time()),
        "roomid": room_id,
        "csrf": BILI_JCT,
        "csrf_token": BILI_JCT
    }

    if reply_uid:
        payload["reply_mid"] = reply_uid

    headers = {
        "Cookie": f"SESSDATA={SESSDATA}; bili_jct={BILI_JCT}; buvid3={BUVID3}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as resp:
                res = await resp.json()
                if res.get("code") != 0:
                    add_log(f"弹幕发送失败！原因: {res.get('message')} (Code: {res.get('code')})")
                else:
                    pass
    except Exception as e:
        add_log(f"网络层错误: {e}")
        # pass

def get_box_reply(uid, uname):
    uid = str(uid)

    if uid not in MEMORY["box"]:
        return f"[盲盒姬] {uname}老师今天还没有开过盲盒哦"

    stats = MEMORY["box"][uid]

    count = stats["count"]
    cost = stats["cost"]
    profit = stats["profit"]

    net = profit - cost

    return f"[盲盒姬] {uname}老师已抽取{count}个盲盒，净收益{net:.0f}电池！"

processed_records = []

async def record_to_blind_box(uid, uname, price, guard_level, start_time, order_id=None):
    is_duplicate = False
    for p_uid, p_time in processed_records:
        if p_uid == uid and p_time == start_time:
            is_duplicate = True
            break
    
    if is_duplicate:
        return

    if price <= 0:
        level_map = {1: 199980, 2: 19980, 3: 1980}
        price = level_map.get(guard_level, 1980)

    role_name = {1: "总督", 2: "提督", 3: "舰长"}.get(guard_level, "大航海")
    update_gift(uid, uname, role_name, 1, price)
    
    source_tag = "[大航海]" if order_id else "[GUARD_BUY]"
    add_log(f"{source_tag} {uname} 开启 {role_name} ({price} 电池) [T:{start_time}]")

    processed_records.append((uid, start_time))
    
    if len(processed_records) > 200:
        processed_records.pop(0)

room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    global last_global_reply, last_query_time

    data = event['data']['info']

    msg = data[1]
    uid = data[2][0]
    uname = data[2][1]

    uid_str = str(uid)
    now = time.time()

    if msg == "呼叫盲盒姬":
        if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
            return

        if now - last_global_reply < 3:
            return

        reply = get_box_reply(uid, uname)

        last_query_time[uid_str] = now
        last_global_reply = now

        await send_reply(ROOM_ID, reply, reply_uid=uid)

        add_log(f"[盲盒姬] 回复 {uname}")

@room.on('SEND_GIFT')
async def on_gift(event):
    data = event['data']['data']

    uid = data.get('uid')
    uname = data.get('sender_uinfo', {}).get('base', {}).get('name', '用户')
    gift_name = data.get('giftName')
    num = data.get('num', 1)

    price_gold = data.get('price', 0)
    
    blind_data = data.get('blind_gift') or (
        data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift')
    )

    if blind_data:
        bg_cost_battery = blind_data.get('original_gift_price', 0) / 100
        g_profit_battery = blind_data.get('gift_tip_price', 0) / 100
        
        update_box(uid, uname, num, bg_cost_battery * num, g_profit_battery * num)
        save_json("files/box.json", MEMORY["box"])

        update_gift(uid, uname, gift_name, num, g_profit_battery * num)
        update_all(g_profit_battery * num)

        add_log(f"[盲盒] {uname} 开启x{num}，价值 {g_profit_battery*num:.1f} 电池")
    else:
        battery = (price_gold * num) / 100
        update_gift(uid, uname, gift_name, num, battery)
        update_all(battery)
        add_log(f"[礼物] {uname} {gift_name}x{num} ({battery:.1f} 电池)")

@room.on('SUPER_CHAT_MESSAGE')
async def on_sc(event):
    data = event['data']['data']

    uid = data.get('uid')
    uname = data.get('user_info', {}).get('uname', '用户')
    price = data.get('price', 0)

    battery = price * 10

    update_gift(uid, uname, "SuperChat", 1, battery)
    update_all(battery)

    add_log(f"[SC] {uname} ({price}元)")

@room.on('USER_TOAST_MSG')
async def handle_toast(event):
    data = event['data']['data']
    await record_to_blind_box(
        uid=data.get('uid'),
        uname=data.get('username'),
        price=data.get('price', 0) / 100,
        guard_level=data.get('guard_level'),
        start_time=data.get('start_time'),
        order_id=data.get('payflow_id')
    )

@room.on('GUARD_BUY')
async def handle_guard(event):
    data = event['data']['data']
    await asyncio.sleep(1) 
    await record_to_blind_box(
        uid=data.get('uid'),
        uname=data.get('username'),
        price=data.get('price', 0) / 100,
        guard_level=data.get('guard_level'),
        start_time=data.get('start_time')
    )

# FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/gift")
def get_gift():
    return MEMORY["gift"]

@app.get("/box")
def get_box():
    return MEMORY["box"]

@app.get("/all")
def get_all():
    return MEMORY["all"]

@app.get("/log")
def get_log():
    return LOG_BUFFER

@app.get("/data")
def get_data():
    return sorted(MEMORY["gift"].values(), key=lambda x: x.get('profit', 0), reverse=True)


# main
async def main():
    add_log("Start")
    load_json_files()

    asyncio.create_task(periodic_tasks())
    asyncio.create_task(room.connect())

    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
    server = uvicorn.Server(config)

    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())