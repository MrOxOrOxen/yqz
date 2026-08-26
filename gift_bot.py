from memory_store import *
from constants import *
from logger import add_log
import random
from json_handle import save_json
import json
import time
from bilibili_api import user
from ids import *
import asyncio
import re

# 礼物姬基本功能
def get_gift_reply(uid, uname):
    uid = str(uid)

    if uid not in MEMORY["gift"]:
        if uid == ADMIN_ID:
            return f"[礼物姬]卡米宝宝今天还没有送过礼物哦"
        if len(uname) > 23:
            uname = uname[:20] + "..."
        return f"[礼物姬]{uname}老师今天还没有送过礼物哦"

    stats = MEMORY["gift"][uid]
    profit = stats["profit"]

    if uid == ADMIN_ID:
        return f"[礼物姬]卡米宝宝已送出{profit:.0f}电池的礼物！"

    if len(uname) > 13:
        uname = uname[:10] + "..."

    reply = f"[礼物姬]{uname}老师已送出{profit:.0f}电池的礼物，老板大气！"

    return reply

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
        # random_step = random.randint(30000, 40000)
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

def thank_gift(uid, uname, gift_name, gift_value, cnt=1):
    pattern = r"(舰长|提督|总督)\*(\d+)天$"
    match = re.search(pattern, gift_name)
    if gift_name == "SuperChat":
        if len(uname) > 12:
            uname = uname[:9] + "..."
        return f"[礼物姬]哇！感谢{uname}老师的{gift_value/10:.0f}元SC！老板大气！" if uid != ADMIN_ID else f"[礼物姬]哇！感谢卡米宝宝的{gift_value/10:.0f}元SC！老板大气！"

    elif gift_name in ["舰长", "提督", "总督", "大航海"]:
        # return None # for annual
        if uid == 500347829:
            return f"[礼物姬]爽睡你的19级牌子不要了喵？"
        elif uid == 15247674:
            return f"[扬帆起航]扬帆起航！长风破浪会有时，直挂云帆济沧海！"

        if len(uname) > 14: uname = uname[:11] + "..."
        if uid == ADMIN_ID and gift_name == "舰长" and cnt == 12:
            return f"[礼物姬]哇！感谢卡米宝宝的提督！老板大气！"
        elif cnt == 1:
            return f"[礼物姬]哇！感谢{uname}老师的{gift_name}！老板大气！" if uid != ADMIN_ID else f"[礼物姬]哇！感谢卡米宝宝的{gift_name}！老板大气！"
        else:
            if len(uname) > 12: uname = uname[:9] + "..."
            return f"[礼物姬]哇！感谢{uname}老师的{cnt}个月{gift_name}！老板大气！" if uid != ADMIN_ID else f"[礼物姬]哇！感谢卡米宝宝的{cnt}个月{gift_name}！老板大气！"

    elif match:
        guard = match.group(1)
        days = match.group(2)
        if len(uname) > 17: uname = uname[:14] + "..."
        return f"[礼物姬]哇！感谢{uname}老师的{days}天{guard}！老板大气！" if uid != ADMIN_ID else f"[礼物姬]哇！感谢卡米宝宝的{days}天{guard}！老板大气！"

    else:
        # 卡米的一百天彩蛋
        # if uid == ADMIN_ID and gift_name == "为你摘星":
        #     return None

        if len(uname) > 15:
            uname = uname[:12] + "..."
        return f"[礼物姬]哇！感谢{uname}老师投喂的{gift_name}！老板大气！" if uid != ADMIN_ID else f"[礼物姬]哇！感谢卡米宝宝投喂的{gift_name}！老板大气！"

# 呼叫礼物姬
async def call_gift(uid, uname):
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
        return

    if uid == ADMIN_ID:
        add_log("[礼物姬] 卡米宝宝触发礼物姬")
        await asyncio.sleep(3)

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

# 指定uid礼物姬
async def call_at_gift(uid, uname, msg):
    global last_query_time
    now = time.time()
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