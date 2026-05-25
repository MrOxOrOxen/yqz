import asyncio
import time
import json
import ssl
import aiohttp
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bilibili_api import live, sync, Credential, user
from bilibili_api.live import LiveDanmaku
from data import SESSDATA, BILI_JCT, BUVID3
import random
from datetime import datetime
import re
from pydantic import BaseModel
from typing import Optional

from ids import *
from logger import add_log, log_buffer
from memory_store import *
from json_handle import load_json_files, save_json, append_to_jsonl
from send_reply import reply_worker
from box_bot import call_box, call_all_box, call_at_box, call_month_box, call_month_all_box, call_month_at_box
from gift_bot import get_gift_reply, handle_thank_reply, handle_total_gift_reply, thank_gift, call_at_gift, call_gift
from eggs import danmu_egg, check_gachi_egg, box_egg, check_global_loss_warning, guard_egg, sc_egg

STATUS = 1
LIVE_STATUS = 0

# 用于danmu_egg的所有时间戳（已弃用）
last_gachi_danmu_trigger = 0
last_question_mark_trigger = 0
last_circle_trigger = 0
last_good_night_trigger = 0
last_haha_trigger = 0

# total_battery = 0
# is_loss_warning_sent = False
# current_gear = 0

async def init_get_room_status():
    global LIVE_STATUS
    room1 = live.LiveRoom(ROOM_ID)
    try:
        info = await room1.get_room_info()
        status = info["room_info"]["live_status"]
        LIVE_STATUS = 1 if status == 1 else 0
        add_log(f"Initial LIVE_STATUS: {LIVE_STATUS}")
    except Exception as e:
        add_log(f"[ERROR] Failed to get initial LIVE_STATUS: {e}")

# 计算大航海连开数量
def calc_guard_combo(gift_name, total_battery):
    base = COMBO_GUARD_PRICE.get(gift_name, 1680)
    remainder = total_battery % base
    first_map = GUARD_FIRST_PRICE.get(gift_name, {})

    if remainder in first_map:
        first_price = first_map[remainder]
        if total_battery <= first_price:
            return 1, first_price, base
        cnt = (total_battery - first_price) // base + 1
        return cnt, first_price, base

    cnt = max(1, round(total_battery / base))
    avg = total_battery // cnt
    return cnt, avg, avg

# 内存更新
def update_all_log(uid, uname, gift_name, battery):
    if gift_name in COMBO_GUARD_PRICE:
        cnt, first_price, follow_price = calc_guard_combo(gift_name, battery)
        for i in range(cnt):
            single = first_price if i == 0 else follow_price
            MEMORY["all"].append({
                "uid": int(uid),
                "uname": uname,
                "time": int(time.time()),
                "gift_name": gift_name,
                "gift_price": single
            })
    else:
        MEMORY["all"].append({
            "uid": int(uid),
            "uname": uname,
            "time": int(time.time()),
            "gift_name": gift_name,
            "gift_price": battery
        })

def update_danmu_log(uid, uname, msg):
    MEMORY["danmu"].append({
        "uid": int(uid), "uname": uname, "time": int(time.time()), "danmu": msg
    })

def update_gift_summary(uid, uname, gift_name, num, battery):
    uid_str = str(uid)
    if uid_str not in MEMORY["gift"]:
        MEMORY["gift"][uid_str] = {"uid": int(uid), "uname": uname, "gift_list": {}, "profit": 0}
    user = MEMORY["gift"][uid_str]
    user["uname"] = uname
    user["profit"] += battery
    if gift_name:
        user["gift_list"][gift_name] = user["gift_list"].get(gift_name, 0) + num

def update_box_summary(uid, uname, count, cost, profit):
    uid_str = str(uid)
    if uid_str not in MEMORY["box"]:
        MEMORY["box"][uid_str] = {"uid": int(uid), "uname": uname, "count": 0, "cost": 0, "profit": 0, "is_personal_loss_egg_sent": False}
    user = MEMORY["box"][uid_str]
    user["uname"] = uname
    user["count"] += count
    user["cost"] += cost
    user["profit"] += profit

# 大航海特殊判断
async def record_to_guard_log(uid, uname, price, guard_level, start_time, source="GUARD"):
    global processed_records
    if any(p_uid == uid and p_time == start_time for p_uid, p_time in processed_records):
        return

    price = int(price)

    if price <= 0:
        price = {1: 199980, 2: 19980, 3: 1980}.get(guard_level, 1980)

    guard_name = {1: "总督", 2: "提督", 3: "舰长"}.get(guard_level, "大航海")

    cnt, _, _ = calc_guard_combo(guard_name, price)

    processed_records.append((uid, start_time))
    if len(processed_records) > 200: processed_records.pop(0)
    
    update_gift_summary(uid, uname, guard_name, cnt, price)
    update_all_log(uid, uname, guard_name, price)
    add_log(f"[{source}] {uname} {guard_name}x{cnt} ({price} 电池)")

    await check_gachi_egg(uid, guard_name, price)

    reply = thank_gift(uid, uname, guard_name, price)
    if reply:
        await handle_thank_reply(uid, uname, reply)

    MEMORY["meta"]["total_battery"] += price
    save_json("files/meta.json", MEMORY["meta"])
    await handle_total_gift_reply(YQZ_ID, MEMORY["meta"]["total_battery"])

    await guard_egg(uid, uname, guard_name, price)

def on_gift_saved():
    add_log("HTML refresh triggered")

# 周期性任务
async def periodic_tasks():
    global last_save_time, last_log_save, LIVE_STATUS
    try:
        while True:
            now = time.time()
            if now - last_save_time > 30:
                print(f"LIVE_STATUS: {LIVE_STATUS}")
                # save_json("files/box.json", MEMORY["box"])
                save_json("files/gift.json", MEMORY["gift"])
                save_json("files/all.json", MEMORY["all"])
                save_json("files/meta.json", MEMORY["meta"])

                if MEMORY["danmu"]:
                    append_to_jsonl("files/danmu.jsonl", MEMORY["danmu"])
                    MEMORY["meta"]["total_danmu_cnt_from_start"] += len(MEMORY["danmu"])
                    MEMORY["danmu"].clear()

                MEMORY["audience"]["interact_cache"] = list(interact_cache)
                save_json("files/audience.json", MEMORY["audience"])
                last_save_time = now
                add_log("All json files saved")
                on_gift_saved()
            if now - last_log_save > 5:
                save_json("files/log.json", log_buffer.buffer)
                last_log_save = now
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        add_log(f"main.py cancelled. saving json files.")
        if MEMORY["gift"]:
            save_json("files/gift.json", MEMORY["gift"])
        if MEMORY["all"]:
            save_json("files/all.json", MEMORY["all"])
        if MEMORY["meta"]:
            save_json("files/meta.json", MEMORY["meta"])
        if MEMORY["audience"]:
            MEMORY["audience"]["interact_cache"] = list(interact_cache)
            save_json("files/audience.json", MEMORY["audience"])
        if MEMORY["danmu"]:
            append_to_jsonl("files/danmu.jsonl", MEMORY["danmu"])

        add_log("Emergency data save completed successfully.")
        raise

# 监听
room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    global last_query_time, LIVE_STATUS

    data = event['data']['info']
    msg, uid, uname = data[1], data[2][0], data[2][1]
    
    if msg == "呼叫礼物姬":
        await call_gift(uid, uname)
    elif "呼叫礼物姬@" in msg:
        await call_at_gift(uid, uname, msg)
    elif re.search(r'^呼叫(?:\d{1,2}|一|二|三|四|五|六|七|八|九|十|十一|十二)月(?:心动|幸运S|幸运|真爱|梦幻之夏)?盲盒姬总部$', msg):
        await call_month_all_box(uid, uname, msg)
    elif re.search(r'^呼叫(?:\d{1,2}|一|二|三|四|五|六|七|八|九|十|十一|十二)月(?:心动|幸运S|幸运|真爱|梦幻之夏)?盲盒姬@(\d+)$', msg):
        await call_month_at_box(uid, uname, msg)
    elif re.search(r'^呼叫(?:\d{1,2}|一|二|三|四|五|六|七|八|九|十|十一|十二)月(?:心动|幸运S|幸运|真爱|梦幻之夏)?盲盒姬$', msg):
        await call_month_box(uid, uname, msg)
    elif re.search(r'^呼叫(心动|幸运S|幸运|真爱|梦幻之夏)?盲盒姬总部$', msg):
        await call_all_box(uid, uname, msg)
    elif re.search(r'^呼叫(心动|幸运S|幸运|真爱|梦幻之夏)?盲盒姬@(\d+)$', msg):
        await call_at_box(uid, uname, msg)
    elif re.search(r'^呼叫(心动|幸运S|幸运|真爱|梦幻之夏)?盲盒姬$', msg):
        await call_box(uid, uname, msg)

    if LIVE_STATUS == 1:
        await danmu_egg()
        update_danmu_log(uid, uname, msg)

@room.on('SEND_GIFT')
async def on_gift(event):
    global LIVE_STATUS
    if LIVE_STATUS != 1:
        return
    data = event['data']['data']
    uid, gift_name, num = data.get('uid'), data.get('giftName'), data.get('num', 1)
    uname = data.get('sender_uinfo', {}).get('base', {}).get('name', '用户')
    blind_data = data.get('blind_gift') or (data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift'))

    if blind_data:
        bg_cost_battery = blind_data.get('original_gift_price', 0) / 100
        g_profit_battery = blind_data.get('gift_tip_price', 0) / 100
        update_box_summary(uid, uname, num, bg_cost_battery*num, g_profit_battery*num)
        save_json("files/box.json", MEMORY["box"])
        update_gift_summary(uid, uname, gift_name, num, g_profit_battery*num)
        update_all_log(uid, uname, gift_name, g_profit_battery*num)
        add_log(f"[盲盒] {uname} x{num} ({g_profit_battery*num:.1f} 电池)")

        await check_gachi_egg(uid, None, g_profit_battery)
        await box_egg(uid, uname, gift_name, num, bg_cost_battery, g_profit_battery)
        await check_global_loss_warning(uid, uname)

        if g_profit_battery >= 1000:
            reply = thank_gift(uid, uname, gift_name, g_profit_battery)
            await handle_thank_reply(uid, uname, reply)
        MEMORY["meta"]["total_battery"] += g_profit_battery*num
        await handle_total_gift_reply(YQZ_ID, MEMORY["meta"]["total_battery"])

    else:
        battery = (data.get('price', 0) * num) / 100
        update_gift_summary(uid, uname, gift_name, num, battery)
        update_all_log(uid, uname, gift_name, battery)
        add_log(f"[礼物] {uname} {gift_name}x{num} ({battery:.1f} 电池)")
        single_battery = battery / num
        await check_gachi_egg(uid, None, single_battery)
        if battery >= 1000:
            reply = thank_gift(uid, uname, gift_name, single_battery)
            await handle_thank_reply(uid, uname, reply)
        MEMORY["meta"]["total_battery"] += battery
        await handle_total_gift_reply(YQZ_ID, MEMORY["meta"]["total_battery"])

@room.on('SUPER_CHAT_MESSAGE')
async def on_sc(event):
    global LIVE_STATUS
    if LIVE_STATUS != 1:
        return
    data = event['data']['data']
    uid, price, uname, content = data.get('uid'), data.get('price', 0), data.get('user_info', {}).get('uname', '用户'), data.get('message', '')
    battery = price * 10
    update_gift_summary(uid, uname, "SuperChat", 1, battery)
    update_all_log(uid, uname, "SuperChat", battery)
    add_log(f"[SuperChat] {uname} ({price}元)")
    await check_gachi_egg(uid, None, battery)
    if battery >= 1000:
        reply = thank_gift(uid, uname, "SuperChat", battery)
        await handle_thank_reply(uid, uname, reply)
    MEMORY["meta"]["total_battery"] += battery
    await handle_total_gift_reply(YQZ_ID, MEMORY["meta"]["total_battery"])
    await sc_egg(uid, uname, battery, content)

@room.on('USER_TOAST_MSG')
async def handle_toast(event):
    global LIVE_STATUS
    if LIVE_STATUS != 1:
        return
    data = event['data']['data']
    guard_level = data.get('guard_level')
    if guard_level and guard_level in [1, 2, 3]:
        await record_to_guard_log(
            uid=data.get('uid'), uname=data.get('username'),
            price=data.get('price', 0) / 100, guard_level=data.get('guard_level'),
            start_time=data.get('start_time'), source="大航海"
        )
    else:
        pass

@room.on('GUARD_BUY')
async def handle_guard(event):
    global LIVE_STATUS
    if LIVE_STATUS != 1:
        return 
    data = event['data']['data']
    await asyncio.sleep(2)
    await record_to_guard_log(
        uid=data.get('uid'), uname=data.get('username'),
        price=data.get('price', 0) / 100, guard_level=data.get('guard_level'),
        start_time=data.get('start_time'), source="大航海 (GUARD)"
    )

@room.on('INTERACT_WORD_V2')
async def interact_word(event):
    global interact_cache, LIVE_STATUS
    if LIVE_STATUS != 1:
        return

    data = event['data']['data']
    pb_decoded = data.get('pb_decoded', {})
    if not pb_decoded:
        return
    uname = pb_decoded.get('uname')
    user_info = pb_decoded.get('user_info', {})
    medal = user_info.get('medal') if user_info else None
    uid = user_info.get('uid', 0) if user_info else 0
    reply = None
    
    if uid in interact_cache:
        return

    if medal and uid != ASPK_ID:
        medal_name = medal.get('name', None)
        medal_level = medal.get('level', 0)
        if uid == ADMIN_ID:
            target_date = datetime(2026, 3, 20)
            today = datetime.now().date()
            days_passed = abs((target_date.date() - today).days) + 1
            reply = f"[欢迎姬]报告！发现{days_passed}个卡米宝宝进入云宝的直播间！"
        elif uid == JIALEISI_ID:
            reply = '[欢迎姬]报告！发现一个说着"唉，gachi"的早崎鸭进入直播间！'
        elif medal_name == "早崎鸭" and medal_level > 30:
            if uid in WELCOME_MAP:
                reply = WELCOME_MAP[uid].format(uname=uname)
            else:
                if len(uname) > 16:
                    uname = uname[:13] + "..."
                reply = f"[欢迎姬]报告！一只叫{uname}的早崎鸭偷偷进入了直播间！"
                
    elif uid == ASPK_ID:
        reply = f"[欢迎姬]欢迎帅神！！"

    interact_cache.add(uid)
    MEMORY["audience"]["interact_cache"] = list(interact_cache)
    save_json("files/audience.json", MEMORY["audience"])
            
    if reply is not None:
        if uid == GACHI_GACHI_ID and GACHI_ID[3] in MEMORY["audience"]["interact_cache"]:
            await reply_queue.put((GACHI_ID[3], reply))
        elif uid != GACHI_GACHI_ID:
            await reply_queue.put((uid, reply))
        add_log(f"[欢迎姬] 欢迎{uname}")

@room.on('LIVE')
async def on_live(event):
    global LIVE_STATUS
    LIVE_STATUS = 1
    add_log("[LOG] LIVE")

@room.on('PREPARING')
async def on_preparing(event):
    global LIVE_STATUS
    LIVE_STATUS = 0
    add_log("[LOG] PREPARING")

# FastAPI & SSL Patch
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    return log_buffer.buffer

@app.get("/data")
def get_data():
    leaderboard = sorted(MEMORY["gift"].values(), key=lambda x: x.get('profit', 0), reverse=True)
    return {
        "status": STATUS,
        "list": leaderboard
    }

#### 热更新
class HotGiftInput(BaseModel):
    uid: int
    uname: str
    gift_name: str
    gift_price: int
    timestamp: int
@app.post("/api/hot_gift")
def api_hot_gift(data: HotGiftInput):
    r'''
    curl -X POST "http://127.0.0.1:8000/api/hot_gift" \
      -H "Content-Type: application/json" \
      -d '{"uid": , "uname": , "gift_name": , "gift_price": , "timestamp": }'
    '''
    uid_str = str(data.uid)

    if uid_str in MEMORY["gift"]:
        if data.gift_name in MEMORY["gift"][uid_str]["gift_list"]:
            MEMORY["gift"][uid_str]["gift_list"][data.gift_name] += 1
        else:
            MEMORY["gift"][uid_str]["gift_list"][data.gift_name] = 1
        MEMORY["gift"][uid_str]["profit"] += data.gift_price
    else:
        MEMORY["gift"][uid_str] = {
            "uid": data.uid,
            "uname": data.uname,
            "gift_list": {data.gift_name: 1},
            "profit": data.gift_price
        }

    MEMORY["all"].append({
        "uid": data.uid,
        "uname": data.uname,
        "time": data.timestamp,
        "gift_name": data.gift_name,
        "gift_price": data.gift_price
    })

    add_log(f"[HOT UPDATE] {data.uname}: {data.gift_name}")
    return {"status": "success", "message": "Hot update inject completed."}

class SendDanmu(BaseModel):
    msg: str
    at_uid: Optional[int] = None
@app.post("/api/send_danmu")
async def api_send_danmu(data: SendDanmu):
    r'''
    curl -X POST "http://127.0.0.1:8000/api/send_danmu" \
      -H "Content-Type: application/json" \
      -d '{"msg":"", "at_uid":}'
    '''
    msg = data.msg.strip()
    uid = data.at_uid

    if uid:
        await reply_queue.put((uid, msg))
    else:
        await reply_queue.put((None, msg))

    add_log(f"[SEND DANMU] {msg}" + (f" @{uid}" if uid else ""))
    return {"status": "success", "sent": msg, "at_uid": uid}

def patch_ssl():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    orig_init = aiohttp.TCPConnector.__init__
    def new_init(self, *args, **kwargs):
        kwargs['ssl'] = ssl_context
        orig_init(self, *args, **kwargs)
    aiohttp.TCPConnector.__init__ = new_init

# __main__
async def main():
    add_log("=== Start ===")
    await init_get_room_status()
    load_json_files()
    patch_ssl()
    asyncio.create_task(periodic_tasks())
    asyncio.create_task(reply_worker())
    asyncio.create_task(room.connect())
    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())