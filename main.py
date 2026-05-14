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
from ids import *

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)
ROOM_ID = 27885573
# ROOM_ID = 1828180031

STATUS = 1
LIVE_STATUS = 0

MEMORY = {
    "box": {},
    "gift": {},
    "all": [],
    "danmu": [],
    "meta": {
        "total_battery": 0,
        "total_danmu_cnt_from_start": 0,
        "is_loss_warning_sent": False,
        "is_whole_profit_msg_sent": False,
        "next_threshold": 4000,
        "current_gear": 0,
        "dog": 0,
        "is_birthday_msg_sent": False,
        "is_kfc_msg_sent": False,
        "is_castle_msg_sent": False,
    },
    "audience": {
        "interact_cache": []
    }
}

LOG_BUFFER = []
reply_queue = asyncio.Queue()
processed_records = []  # 用于大航海判重
last_query_time = {}
gachi_last_time = {}
# last_global_reply = 0
last_save_time = 0
last_log_save = 0
interact_cache = set()

# 用于danmu_egg的所有时间戳
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
        add_log(f"[ERROR] Failed to get initial LIVE_STATUS", e)

async def reply_worker():
    add_log("Reply queue start")
    while True:
        uid, content = await reply_queue.get()
        
        try:
            await send_reply(ROOM_ID, content, reply_uid=uid)
            random_time = round(random.uniform(2.5, 3.5), 1)
            await asyncio.sleep(random_time) 
        except Exception as e:
            add_log(f"[ERROR] Reply queue error: {e}")
        finally:
            reply_queue.task_done()

def load_json_files():
    global interact_cache
    json_map = {
        "files/box.json": ("box", MEMORY),
        "files/gift.json": ("gift", MEMORY),
        "files/all.json": ("all", MEMORY),
        "files/meta.json": ("meta", MEMORY),
        "files/audience.json": ("audience", MEMORY)
    }

    if not os.path.exists("files"):
        os.makedirs("files")

    meta_path = "files/meta.json"
    audience_path = "files/audience.json"
    
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                MEMORY["meta"]["total_battery"] = data.get("total_battery", 0)
                # MEMORY["meta"]["total_danmu_cnt_from_start"] = data.get("total_danmu_cnt_from_start", 0)
                MEMORY["meta"]["is_loss_warning_sent"] = data.get("is_loss_warning_sent", False)
                MEMORY["meta"]["is_whole_profit_msg_sent"] = data.get("is_whole_profit_msg_sent", False)
                MEMORY["meta"]["next_threshold"] = data.get("next_threshold", random.randint(4000, 5000))
                MEMORY["meta"]["current_gear"] = data.get("current_gear", 0)
                MEMORY["meta"]["dog"] = data.get("dog", 0)
                MEMORY["meta"]["is_birthday_msg_sent"] = data.get("is_birthday_msg_sent", False)
                MEMORY["meta"]["is_kfc_msg_sent"] = data.get("is_kfc_msg_sent", False)
                MEMORY["meta"]["is_castle_msg_sent"] = data.get("is_castle_msg_sent", False)
                add_log(f"Total battery from history file: {MEMORY['meta']['total_battery']}")
                add_log(f"Next battery threshold: {MEMORY['meta']['next_threshold']}")
        except Exception as e:
            add_log(f"[ERROR] Error when reading meta.json: {e}")
            MEMORY["meta"]["total_battery"] = 0
    else:
        MEMORY["meta"]["total_battery"] = 0
        add_log("No meta.json. Total battery starts with 0")
        MEMORY["meta"]["next_threshold"] = random.randint(4000, 5000)
        add_log(f"Next battery threshold: {MEMORY['meta']['next_threshold']}")

    if os.path.exists(audience_path):
        try:
            with open(audience_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                MEMORY["audience"]["interact_cache"] = data.get("interact_cache", [])
                interact_cache = set(data.get("interact_cache", []))
                add_log(f"Loaded interact_cache with {len(interact_cache)} entries.")
        except Exception as e:
            add_log(f"[ERROR] Error when reading audience.json: {e}")

    else:
        interact_cache = set()
        save_json("files/audience.json", MEMORY["audience"])


    for file_path, (key, target) in json_map.items():
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                target[key] = data
            else:
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

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def append_to_jsonl(filename, data_list):
    if not data_list: return
    with open(filename, "a", encoding="utf-8") as f:
        for item in data_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def add_log(msg):
    global LOG_BUFFER
    LOG_BUFFER.append({"time": int(time.time()), "msg": msg})
    LOG_BUFFER = LOG_BUFFER[-100:]
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

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
                    add_log(f"[ERROR] Failed to send danmu because: {res.get('message')} (Code: {res.get('code')})")
                else:
                    pass
    except Exception as e:
        add_log(f"[ERROR] Network layer error: {e}")

# 盲盒姬基本功能
def get_box_reply(uid, uname):
    uid = str(uid)

    if uid not in MEMORY["box"]:
        if len(uname) > 23:
            uname = uname[:20] + "..."
        return f"[盲盒姬]{uname}老师今天还没有开过盲盒哦", None

    stats = MEMORY["box"][uid]

    count = stats["count"]
    cost = stats["cost"]
    profit = stats["profit"]

    net = profit - cost

    if net < -10000 and len(uname) > 9:
        uname = uname[:6] + "..."
    elif len(uname) > 10:
        uname = uname[:7] + "..."

    reply1 = f"[盲盒姬]{uname}老师已抽取{count}个盲盒，净收益{net:.0f}电池"
    reply2 = None

    if net < -10000:
        reply1 += "!？"
        reply2 = "[盲盒姬]温馨提醒：道路千万条，理性第一条；盲盒别上头，破财没解药"
    elif net < -2000:
        reply1 += "？"
    elif net > 10000:
        reply1 += "?！"
        reply2 = "[盲盒姬]老板大气，云崎早快给老板磕一个！"
    elif net > 2000:
        reply1 += "!！"
    else:
        reply1 += "！"

    return reply1, reply2

# 全局盲盒姬基本功能
def get_all_box_reply():
    if not MEMORY["box"]:
        return "[盲盒姬]今天还没有人开过盲盒哦"
    else:
        total_cost = 0
        total_profit = 0
        total_count = 0
        for uid, value in MEMORY["box"].items():
            total_cost += value["cost"]
            total_profit += value["profit"]
            total_count += value["count"]
        total_net = total_profit - total_cost

        reply = f"[盲盒姬]今天全场一共开启了{total_count:.0f}个盲盒，净收益{total_net:.0f}电池"

        if total_net < -10000:
            reply += "!？"
        elif total_net < -2000:
            reply += "？"
        elif total_net > 10000:
            reply += "?！"
        elif total_net > 2000:
            reply += "!！"
        else:
            reply += "！"

        return reply

# 礼物姬基本功能
def get_gift_reply(uid, uname):
    uid = str(uid)

    if uid not in MEMORY["gift"]:
        if len(uname) > 23:
            uname = uname[:20] + "..."
        return f"[礼物姬]{uname}老师今天还没有送过礼物哦"

    stats = MEMORY["gift"][uid]
    profit = stats["profit"]

    if len(uname) > 13:
        uname = uname[:10] + "..."

    reply = f"[礼物姬]{uname}老师已送出{profit:.0f}电池的礼物，老板大气！"

    return reply

def thank_gift(uid, uname, gift_name, gift_value):
    if gift_name == "SuperChat":
        if len(uname) > 12:
            uname = uname[:9] + "..."
        return f"[礼物姬]哇！感谢{uname}老师送出的{gift_value/10:.0f}元SC！老板大气！"

    elif gift_name in ["舰长", "提督", "总督", "大航海"]:
        if len(uname) > 14:
            uname = uname[:11] + "..."
        return f"[礼物姬]哇！感谢{uname}老师的{gift_name}！老板大气！"

    else:
        if len(uname) > 15:
            uname = uname[:12] + "..."
        return f"[礼物姬]哇！感谢{uname}老师投喂的{gift_name}！老板大气！"

async def handle_thank_reply(uid, uname, reply):
    if len(reply) <= 40:
        await reply_queue.put((uid, reply))
    else:
        part1 = reply[:40]
        part2 = "[礼物姬]" + reply[40:]
        await reply_queue.put((uid, part1))
        await reply_queue.put((uid, part2))
    add_log(f"[礼物姬] 感谢 {uname}")

async def handle_total_gift_reply(uid, profit):
    next_t = MEMORY["meta"]["next_threshold"]
    gear = MEMORY["meta"]["current_gear"]
    triggered = False

    while profit >= next_t:
        gear += 1
        random_step = random.randint(4000, 5000)
        next_t += random_step
        triggered = True
        add_log(f"[礼物姬] 下一电池阈值: {next_t}")

    if triggered:
        MEMORY["meta"]["current_gear"] = gear
        MEMORY["meta"]["next_threshold"] = next_t
        save_json("files/meta.json", MEMORY["meta"])

        reply = f"[礼物姬]你看又⭕️ x{int(gear)}" if int(gear) != 1 else "[礼物姬]你看又⭕️"
        await reply_queue.put((uid, reply))
        
        add_log(f"[礼物姬] 下一电池阈值: {next_t}")

# 内存更新
def update_all_log(uid, uname, gift_name, battery):
    MEMORY["all"].append({
        "uid": int(uid), "uname": uname, "time": int(time.time()),
        "gift_name": gift_name, "gift_price": battery
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
        MEMORY["box"][uid_str] = {"uid": int(uid), "uname": uname, "count": 0, "cost": 0, "profit": 0}
    user = MEMORY["box"][uid_str]
    user["uname"] = uname
    user["count"] += count
    user["cost"] += cost
    user["profit"] += profit

# 彩蛋设置
async def check_gachi_egg(uid, guard_name, battery):
    now = time.time()
    if uid in GACHI_ID and battery >= 52:
        if uid not in gachi_last_time or (now - gachi_last_time[uid] > 600):
            gachi_last_time[uid] = now
            await reply_queue.put((uid, "[礼物姬]唉gachi"))
            add_log(f"[礼物姬] check_gachi_egg")

async def box_egg(uid, uname, gift_name, num, cost, profit):
    async def huli_box(uid, num):
        if uid == HULI_ID:
            if str(uid) in MEMORY["box"]:
                current_count = MEMORY["box"][str(uid)]["count"]
                old_count = current_count - num
                for i in range(int(old_count) + 1, int(current_count) + 1):
                    if i % 50 == 10:
                        await reply_queue.put((uid, "[盲盒姬]狐狸老师你又在抽盲盒喔，休息一下好不好"))
                        add_log("[盲盒姬] huli_box")
                        break

    async def yqz_box(uid, num):
        if uid == XIAOZAO_ID:
            if str(uid) in MEMORY["box"]:
                current_count = MEMORY["box"][str(uid)]["count"]
                old_count = current_count - num
                for i in range(int(old_count) + 1, int(current_count) + 1):
                    if i % 50 == 1:
                        await reply_queue.put((uid, "[盲盒姬]云宝你也在抽盲盒喔，别抽了好不好"))
                        add_log("[盲盒姬] yqz_box")
                        break
    
    await huli_box(uid, num)
    await yqz_box(uid, num)

async def check_global_loss_warning(uid):
    if MEMORY["meta"].get("is_loss_warning_sent", False):
        return

    if MEMORY["meta"].get("is_whole_profit_msg_sent", False):
        return

    total_net = sum(u["profit"] - u["cost"] for u in MEMORY["box"].values())
    
    if total_net <= -15000:
        warning_msg = f"[盲盒姬]天台拥挤不要插队，觉得风大的老板走后面楼梯下楼谢谢"
        await reply_queue.put((uid, warning_msg))
        
        MEMORY["meta"]["is_loss_warning_sent"] = True
        save_json("files/meta.json", MEMORY["meta"])
        add_log(f"[盲盒姬] total_net < -15000")

    if total_net >= 15000:
        msg = f"[盲盒姬]ohhhhhhhhhh转运了转运了！云崎早的直播间竟然欧起来了!！"
        await reply_queue.put((uid, msg))
        MEMORY["meta"]["is_whole_profit_msg_sent"] = True
        save_json("files/meta.json", MEMORY["meta"])
        add_log(f"[盲盒姬] total_net > 15000")


async def danmu_egg():
    async def birthday():
        if datetime.now().strftime("%m%d") != "0503":
            return False

        if MEMORY["meta"]["is_birthday_msg_sent"] == True:
            return False

        try:
            total_count = MEMORY["meta"].get("total_danmu_cnt_from_start", 0) + len(MEMORY["danmu"])
            if total_count >= 100:
                MEMORY["meta"]["is_birthday_msg_sent"] = True
                save_json("files/meta.json", MEMORY["meta"])
                birthday_msg = "[卡米宝宝]今天是全世界最最最可爱的云崎早的生日，让我们祝云宝生日快乐！"
                await reply_queue.put((YQZ_ID, birthday_msg))
                add_log("[卡米宝宝] birthday")
        except Exception as e:
            print(f"统计弹幕失败: {e}")
            return False


    async def kfc():
        if datetime.now().weekday() != 3:
            return False

        if datetime.now().hour < 12:
            return False

        if MEMORY["meta"]["is_kfc_msg_sent"] == True:
            return False

        try:
            total_count = MEMORY["meta"].get("total_danmu_cnt_from_start", 0) + len(MEMORY["danmu"])

            if total_count >= 100:
                MEMORY["meta"]["is_kfc_msg_sent"] = True
                save_json("files/meta.json", MEMORY["meta"])
                kfc_msg = "[礼物姬]今天是星期四，不想被做成烤鸭的早崎鸭请自觉上交50元谢谢"
                await reply_queue.put((YQZ_ID, kfc_msg))
                add_log(f"[礼物姬] kfc")
        except Exception as e:
            print(f"统计弹幕失败: {e}")
            return False

    async def castle():
        if datetime.now().weekday() != 4:
            return False

        if datetime.now().hour < 12:
            return False

        if MEMORY["meta"]["is_castle_msg_sent"] == True:
            return False

        try:
            total_count = MEMORY["meta"].get("total_danmu_cnt_from_start", 0) + len(MEMORY["danmu"])
            if total_count >= 100:
                MEMORY["meta"]["is_castle_msg_sent"] = True
                save_json("files/meta.json", MEMORY["meta"])
                castle_msg = "[盲盒姬]听说今天城堡概率翻倍"
                await reply_queue.put((YQZ_ID, castle_msg))
                add_log(f"[盲盒姬] castle")

        except Exception as e:
            print(f"统计弹幕失败: {e}")
            return False

    # combo functions
    async def gachi_combo():
        global last_gachi_danmu_trigger
        recent_msgs = [item["danmu"] for item in MEMORY["danmu"][-10:] if time.time() - item.get("time", 0) < 60]
        keywords = ["唉gachi", "哎gachi", "唉，gachi", "哎，gachi", "唉,gachi", "哎,gachi", "唉, gachi", "哎, gachi"]
        gachi_count = sum(1 for m in recent_msgs if any(k in m for k in keywords))
        if gachi_count >= 3:
            if time.time() - last_gachi_danmu_trigger >= 300:
                gachi_msg = "[观测姬(跟读弹幕)]唉gachi"
                await reply_queue.put((None, gachi_msg))
                last_gachi_danmu_trigger = time.time()
                add_log("[观测姬] gachi_combo")

    async def question_mark_combo():
        global last_question_mark_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 60 and item["uid"] != ADMIN_ID
        ]

        keywords1 = ["?", "？"]
        keywords2 = "？？？"
        question_mark_count = sum(
            1 for m in recent_msgs
            if m in keywords1 or keywords2 in m
        )

        if question_mark_count > 3:
            if time.time() - last_question_mark_trigger > 300:
                question_mark_msg = "[观测姬(跟读弹幕)]？"
                await reply_queue.put((None, question_mark_msg))
                last_question_mark_trigger = time.time()
                add_log("[观测姬] question_mark_combo")

    async def circle_combo():
        global last_circle_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 60 and item["uid"] != ADMIN_ID
        ]

        keywords = ["⭕️", "圈"]
        circle_count = sum(1 for m in recent_msgs if any(k in m for k in keywords))

        if circle_count > 3:
            if time.time() - last_circle_trigger > 300:
                circle_msg = "[观测姬(跟读弹幕)]⭕️"
                await reply_queue.put((None, circle_msg))
                last_circle_trigger = time.time()
                add_log("[观测姬] circle_combo")

    async def good_night_combo():
        global last_good_night_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 300 and item["uid"] != ADMIN_ID
        ]

        keywords = "晚安"
        good_night_count = sum(1 for m in recent_msgs if keywords in m)

        if good_night_count > 3:
            if time.time() - last_good_night_trigger > 600:
                good_night_msg = "[观测姬(跟读弹幕)]晚安晚安"
                await reply_queue.put((None, good_night_msg))
                last_good_night_trigger = time.time()
                add_log("[观测姬] good_night")

    async def haha_combo():
        global last_haha_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 300 and item["uid"] != ADMIN_ID
        ]

        keywords = "哈哈"
        haha_count = sum(1 for m in recent_msgs if keywords in m)

        if haha_count > 3:
            if time.time() - last_haha_trigger > 300:
                haha_msg = "[观测姬(跟读弹幕)]哈哈"
                await reply_queue.put((None, haha_msg))
                last_haha_trigger = time.time()
                add_log("[观测姬] haha_combo")

    await birthday()
    await kfc()
    await castle()
    # await gachi_combo()
    # await question_mark_combo()
    # await circle_combo()
    # await good_night_combo()
    # await haha_combo()

async def gift_egg(uid, uname, gift_name, num, profit):
    pass

async def sc_egg(uid, uname, battery, message):
    async def shennai(uid, message):
        keywords = ["云购", "溜溜", "狗", "66", "遛狗", "√", "遛遛", "溜狗", "6狗", "6购"]
        if uid == SHENNAI_ID and any(k in message for k in keywords):
            MEMORY["meta"]["dog"] += 1
            save_json("files/meta.json", MEMORY["meta"])
            dog_msg = f"[礼物姬]每日遛狗（{MEMORY['meta']['dog']}/1）"
            await reply_queue.put((uid, dog_msg))
            add_log(f"[礼物姬] shennai")
    
    await shennai(uid, message)


async def guard_egg(uid, uname, guard_name, price):
    async def shuangshui(uid):
        if uid == SHUANGSHUI_ID:
            await reply_queue.put((uid, "[礼物姬]爽睡你的19级牌子不要了喵？"))
            add_log(f"[礼物姬] shuangshui")

    # 由于thank_guard中@的人不一样，需要单独列出
    async def thank_guard(uid, uname, guard_name):
        if guard_name == "总督":
            if uid == GACHI_ID[3]:
                reply = "[from 庄生梦方宜]云宝，生日快乐！你这么好，值得这世上所有温柔的对待！"
                await reply_queue.put((YQZ_ID, reply))
            else:
                reply1 = "[礼物姬]哇谢谢早崎鸭大人的……不对这是什么？！这不会是总督吧！！！"
                reply2 = "[礼物姬]哇呜呜呜呜呜谢谢老板的总督，这也是给我的生日礼物吗 T_T！"
                reply3 = "[礼物姬]云崎早有你真的好幸福好幸福！生日同乐！！"
                await reply_queue.put((uid, reply1))
                await reply_queue.put((uid, reply2))
                await reply_queue.put((uid, reply3))
            add_log("[礼物姬] 总督")
        elif guard_name == "提督":
            if uid == GACHI_ID[3]:
                reply = "[from 庄生梦方宜]我会一直在这里，看你发光，也等你休息。"
                await reply_queue.put((YQZ_ID, reply))
            else:
                reply1 = "[礼物姬]哇谢谢早崎鸭大人的提督！提督大人生日同乐！"
                reply2 = "[礼物姬]谢谢你愿意给云崎早分一口生日蛋糕！！"
                await reply_queue.put((uid, reply1))
                await reply_queue.put((uid, reply2))
        elif guard_name == "舰长" and uid != JUNBEN_ID:
            if uid == GACHI_ID[3]:
                reply = "[from 庄生梦方宜]新的一岁，愿你被人爱，也被人照顾。"
                await reply_queue.put((YQZ_ID, reply))
            else:
                reply = "[礼物姬]谢谢早崎鸭大人的舰长！生日同乐！不死族又可以+1了！！"
                await reply_queue.put((uid, reply))
        else:
            pass
        add_log(f"[礼物姬]感谢{uname}的{guard_name}")

    await shuangshui(uid)
    # await thank_guard(uid, uname, guard_name)

# 大航海特殊判断
async def record_to_guard_log(uid, uname, price, guard_level, start_time, source="GUARD"):
    global processed_records
    if any(p_uid == uid and p_time == start_time for p_uid, p_time in processed_records):
        return

    if price <= 0:
        price = {1: 199980, 2: 19980, 3: 1980}.get(guard_level, 1980)

    guard_name = {1: "总督", 2: "提督", 3: "舰长"}.get(guard_level, "大航海")

    processed_records.append((uid, start_time))
    if len(processed_records) > 200: processed_records.pop(0)
    
    update_gift_summary(uid, uname, guard_name, 1, price)
    update_all_log(uid, uname, guard_name, price)
    add_log(f"[{source}] {uname} {guard_name} ({price} 电池)")

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
    while True:
        now = time.time()
        if now - last_save_time > 30:
            print(f"LIVE_STATUS: {LIVE_STATUS}")
            # save_json("files/box.json", MEMORY["box"])
            save_json("files/gift.json", MEMORY["gift"])
            save_json("files/all.json", MEMORY["all"])
            save_json("files/meta.json", MEMORY["meta"])
            append_to_jsonl("files/danmu.jsonl", MEMORY["danmu"])
            MEMORY["meta"]["total_danmu_cnt_from_start"] += len(MEMORY["danmu"])
            save_json("files/meta.json", MEMORY["meta"])
            save_json("files/audience.json", MEMORY["audience"])
            MEMORY["danmu"].clear()
            last_save_time = now
            add_log("All json files saved")
            on_gift_saved()
        if now - last_log_save > 5:
            save_json("files/log.json", LOG_BUFFER)
            last_log_save = now
        await asyncio.sleep(2)

# 监听
room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    global last_query_time, LIVE_STATUS
    # global last_global_reply
    if LIVE_STATUS == 0:
        return
    data = event['data']['info']
    msg, uid, uname = data[1], data[2][0], data[2][1]
    update_danmu_log(uid, uname, msg)

    await danmu_egg()

    # 盲盒姬
    uid_str = str(uid)
    now = time.time()

    if msg == "呼叫盲盒姬":
        if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
            return

        # if now - last_global_reply < 3:
        #     return

        if uid == ADMIN_ID:
            add_log("[盲盒姬] 卡米宝宝触发盲盒姬")
            await asyncio.sleep(4)

        reply1, reply2 = get_box_reply(uid, uname)

        last_query_time[uid_str] = now
        # last_global_reply = now

        if len(reply1) <= 40:
            await reply_queue.put((uid, reply1))
            if reply2 is not None:
                await reply_queue.put((uid, reply2))
        else:
            part1 = reply1[:40]
            part2 = "[盲盒姬]" + reply1[40:]
            await reply_queue.put((uid, part1))
            await reply_queue.put((uid, part2))
            if reply2 is not None:
                await reply_queue.put((uid, reply2))

        add_log(f"[盲盒姬] 回复 {uname}")

    # 全局盲盒姬
    if msg == "呼叫盲盒姬总部":
        # if now - last_global_reply < 3:
        #     return

        if uid == ADMIN_ID:
            add_log("[盲盒姬] 卡米宝宝触发全局盲盒姬")
            await asyncio.sleep(4)
        
        all_reply = get_all_box_reply()
        # last_global_reply = now
        await reply_queue.put((uid, all_reply))
        add_log(f"[盲盒姬] 发送全场统计")

    # 礼物姬
    if msg == "呼叫礼物姬":
        if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
            return

        # if now - last_global_reply < 3:
        #     return

        if uid == ADMIN_ID:
            add_log("[礼物姬] 卡米宝宝触发礼物姬")
            await asyncio.sleep(4)

        reply = get_gift_reply(uid, uname)

        last_query_time[uid_str] = now
        # last_global_reply = now

        if len(reply) <= 40:
            await reply_queue.put((uid, reply))
        else:
            part1 = reply[:40]
            part2 = "[礼物姬]" + reply[40:]
            await reply_queue.put((uid, part1))
            await reply_queue.put((uid, part2))

        add_log(f"[礼物姬] 回复 {uname}")

    # 指定uid盲盒姬
    if "呼叫盲盒姬@" in msg:
        uid_str = str(uid)
        if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
            return

        if uid not in [ADMIN_ID, YQZ_ID, XIAOZAO_ID]:
            return

        to_check_uid_str = msg[6:].strip()
        user_data = MEMORY["box"].get(to_check_uid_str)
        if user_data:
            to_check_uid = user_data.get("uid", 0)
            to_check_uname = user_data.get("uname", "您指定的")
        else:
            to_check_uid = int(to_check_uid_str.strip())
            u = user.User(to_check_uid, credential=credential)
            to_check_info = await u.get_user_info()
            to_check_uname = to_check_info.get("name", "您指定的")
  
        reply1, reply2 = get_box_reply(to_check_uid, to_check_uname)
        last_query_time[uid_str] = now

        if len(reply1) <= 40:
            await reply_queue.put((uid, reply1))
            if reply2 is not None:
                await reply_queue.put((uid, reply2))
        else:
            part1 = reply1[:40]
            part2 = "[盲盒姬]" + reply1[40:]
            await reply_queue.put((uid, part1))
            await reply_queue.put((uid, part2))
            if reply2 is not None:
                await reply_queue.put((uid, reply2))

        add_log(f"[盲盒姬] 回复 {uname}（指定查询用户：{to_check_uname}）")

    # 指定uid礼物姬
    if "呼叫礼物姬@" in msg:
        uid_str = str(uid)
        if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
            return

        if uid not in [ADMIN_ID, YQZ_ID, XIAOZAO_ID]:
            return

        to_check_uid_str = msg[6:].strip()
        user_data = MEMORY["gift"].get(to_check_uid_str)
        if user_data:
            to_check_uid = user_data.get("uid", 0)
            to_check_uname = user_data.get("uname", "您指定的")
        else:
            to_check_uid = int(to_check_uid_str.strip())
            u = user.User(to_check_uid, credential=credential)
            to_check_info = await u.get_user_info()
            to_check_uname = to_check_info.get("name", "您指定的")

        reply = get_gift_reply(to_check_uid, to_check_uname)

        last_query_time[uid_str] = now

        if len(reply) <= 40:
            await reply_queue.put((uid, reply))
        else:
            part1 = reply[:40]
            part2 = "[礼物姬]" + reply[40:]
            await reply_queue.put((uid, part1))
            await reply_queue.put((uid, part2))

        add_log(f"[礼物姬] 回复 {uname}（指定查询用户：{to_check_uname}）")

@room.on('SEND_GIFT')
async def on_gift(event):
    global LIVE_STATUS
    if LIVE_STATUS == 0:
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
        await check_global_loss_warning(None)

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
    if LIVE_STATUS == 0:
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
    if LIVE_STATUS == 0:
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
    if LIVE_STATUS == 0:
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
    if LIVE_STATUS == 0:
        return

    data = event['data']['data']
    pb_decoded = data.get('pb_decoded', {})
    # print(pb_decoded)
    if not pb_decoded:
        return
    uname = pb_decoded.get('uname')
    user_info = pb_decoded.get('user_info', {})
    medal = user_info.get('medal') if user_info else None
    uid = user_info.get('uid', 0) if user_info else 0
    reply = None
    
    if uid in interact_cache:
            return

    if medal:
        medal_name = medal.get('name', None)
        medal_level = medal.get('level', 0)
        if uid == ADMIN_ID:
            target_date = datetime(2026, 3, 20)
            today = datetime.now().date()
            days_passed = abs((target_date.date() - today).days) + 1
            reply = f"[欢迎姬]报告！发现{days_passed}个卡米宝宝进入云宝的直播间！"
        elif uid == GACHI_ID[3]:
            reply = f"[欢迎姬]报告！发现庄生梦方宜老师来直播间盯着云宝今天也要早早睡觉！"
        elif uid == ASPK_ID:
            reply = f"[欢迎姬]欢迎帅神！！"
        elif uid == JIALEISI_ID:
            reply = f'[欢迎姬]报告！发现一个说着“唉，gachi”的早崎鸭进入直播间！'
        elif medal_name == "早崎鸭" and medal_level > 30:
            if uid in GACHI_ID[:3]:
                reply = f'[欢迎姬]报告！发现一个说着“早早天下第一可爱！”的gachi进入直播间！'
            elif uid == ZAIYI_ID:
                reply = f"[欢迎姬]报告！一只叫{uname}的大傻呗进入了直播间！"
            elif uid == XINGCHEN_KAISER_ID:
                reply = f"[欢迎姬]一只叫{uname}的早崎鸭怎么学习学到直播间嘞？"
            elif uid == FEIXINGTING_ID:
                reply = f"[欢迎姬]报告！观测到一架飞行艇飞入直播间！"
            elif uid == SHUANGSHUI_ID:
                reply = f"[欢迎姬]报告喵！发现爽睡老师进入直播间喵！"
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
        # await send_reply(ROOM_ID, reply, reply_uid=uid)
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
    return LOG_BUFFER

@app.get("/data")
def get_data():
    leaderboard = sorted(MEMORY["gift"].values(), key=lambda x: x.get('profit', 0), reverse=True)
    return {
        "status": STATUS,
        "list": leaderboard
    }

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