from memory_store import *
from constants import *
from ids import *
from logger import add_log
from bilibili_api import user
import re, os, json
from datetime import datetime
import time
import asyncio

# 呼叫盲盒姬
async def call_box(uid, uname, msg):
    global last_query_time
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
            return

    if uid == ADMIN_ID:
        add_log("[盲盒姬] 卡米宝宝触发盲盒姬")
        await asyncio.sleep(3)

    box_name = extract_type(msg)
    # reply_box_name = BOX_MEMORY_MAP.get(box_name, "盲盒")
    reply_box_name = box_name

    data_type = "box" if box_name == "盲盒" else "gift"

    if data_type == "box":
        cnt, cost, profit = await load_daily_data(uid, data_type, box_name=box_name, check_user_type="single")
        net = profit - cost
    elif data_type == "gift":
        base_box_name = re.sub(r'(盲盒)+$', '', reply_box_name.strip())
        cnt, cost, profit = await load_daily_data(uid, data_type, box_name=base_box_name, check_user_type="single")
        net = profit - cost
        if cnt == 0:
            retry_box_name = f"{base_box_name}盲盒"
            retry_cnt, retry_cost, retry_profit = await load_daily_data(uid, data_type, box_name=retry_box_name, check_user_type="single")
            if retry_cnt > 0:
                box_name = retry_box_name
                cnt, cost, profit = retry_cnt, retry_cost, retry_profit
                net = profit - cost
                reply_box_name = f"{base_box_name}盲盒"
            else:
                if reply_box_name.strip().endswith("盲盒"):
                    reply_box_name = reply_box_name.strip()
                else:
                    reply_box_name = f"{reply_box_name}盲盒"

    if cnt > 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝今天已抽取{cnt}个{reply_box_name}，净收益{net:.0f}电池"
        else:
            reply = f"[盲盒姬]{uname}老师今天已抽取{cnt}个{reply_box_name}，净收益{net:.0f}电池"

        if net < -10000:
            reply += "!？"
        elif net < -2000:
            reply += "？"
        elif net > 10000:
            reply += "?！"
        elif net > 2000:
            reply += "!！"
        else:
            reply += "！"
    
    elif cnt == 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝今天还没有开过{reply_box_name}哦"
        else:
            reply = f"[盲盒姬]{uname}老师今天还没有开过{reply_box_name}哦"
    
    if len(reply) <= 40:
        await reply_queue.put((uid, reply))
    else:
        part1 = reply[:40]
        part2 = "[盲盒姬]" + reply[40:]
        await reply_queue.put((uid, part1))
        await reply_queue.put((uid, part2))

    add_log(f"[盲盒姬] 回复 {uname}")
    last_query_time[uid_str] = now

# 呼叫盲盒姬总部
async def call_all_box(uid, uname, msg):
    global last_query_time
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
        return

    if uid == ADMIN_ID:
        add_log("[盲盒姬] 卡米宝宝触发全局盲盒姬")
        await asyncio.sleep(3)
    
    box_name = extract_type(msg)
    # reply_box_name = BOX_MEMORY_MAP.get(box_name, "盲盒")
    reply_box_name = box_name

    data_type = "box" if box_name == "盲盒" else "gift"

    if data_type == "box":
        cnt, cost, profit = await load_daily_data(uid, data_type, box_name=box_name, check_user_type="all")
        net = profit - cost
    elif data_type == "gift":
        base_box_name = re.sub(r'(盲盒)+$', '', reply_box_name.strip())
        cnt, cost, profit = await load_daily_data(uid, data_type, box_name=base_box_name, check_user_type="all")
        net = profit - cost
        if cnt == 0:
            retry_box_name = f"{base_box_name}盲盒"
            retry_cnt, retry_cost, retry_profit = await load_daily_data(uid, data_type, box_name=retry_box_name, check_user_type="all")
            if retry_cnt > 0:
                box_name = retry_box_name
                cnt, cost, profit = retry_cnt, retry_cost, retry_profit
                net = profit - cost
                reply_box_name = f"{base_box_name}盲盒"
            else:
                if reply_box_name.strip().endswith("盲盒"):
                    reply_box_name = reply_box_name.strip()
                else:
                    reply_box_name = f"{reply_box_name}盲盒"

    if cnt > 0:
        reply = f"[盲盒姬]今天全场已抽取{cnt}个{reply_box_name}，净收益{net:.0f}电池"

        if net < -20000:
            reply += "!？"
        elif net < -4000:
            reply += "？"
        elif net > 20000:
            reply += "?！"
        elif net > 4000:
            reply += "!！"
        else:
            reply += "！"
    
    elif cnt == 0:
        reply = f"[盲盒姬]今天还没有人开过{reply_box_name}哦"
    
    if len(reply) <= 40:
        await reply_queue.put((uid, reply))
    else:
        part1 = reply[:40]
        part2 = "[盲盒姬]" + reply[40:]
        await reply_queue.put((uid, part1))
        await reply_queue.put((uid, part2))

    add_log(f"[盲盒姬] 全局回复 {uname}")
    last_query_time[uid_str] = now

# 指定uid盲盒姬
async def call_at_box(uid, uname, msg):
    global last_query_time
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
        return

    if uid not in [ADMIN_ID, YQZ_ID, XIAOZAO_ID]:
        return

    if uid == ADMIN_ID:
        add_log("[盲盒姬] 卡米宝宝触发盲盒姬")
        await asyncio.sleep(3)

    at_match = re.search(r'@(\d+)$', msg)
    to_check_uid_str = at_match.group(1) if at_match else "0"
    clean_msg = re.sub(r'@\d+$', '', msg)

    user_data = MEMORY["box"].get(to_check_uid_str)
    if user_data:
        to_check_uid = user_data.get("uid", 0)
        to_check_uname = user_data.get("uname", "您指定的")
    else:
        to_check_uid = int(to_check_uid_str.strip())
        try:
            u = user.User(to_check_uid, credential=credential)
            to_check_info = await u.get_user_info()
            to_check_uname = to_check_info.get("name", "您指定的")
        except Exception as e:
            to_check_uname = "Default"
            print(f"ERROR when loading to_check_uname: {e}")

    box_name = extract_type(clean_msg)
    # reply_box_name = BOX_MEMORY_MAP.get(box_name, "盲盒")
    reply_box_name = box_name

    data_type = "box" if box_name == "盲盒" else "gift"

    if data_type == "box":
        cnt, cost, profit = await load_daily_data(to_check_uid, data_type, box_name=box_name, check_user_type="single")
        net = profit - cost
    elif data_type == "gift":
        base_box_name = re.sub(r'(盲盒)+$', '', reply_box_name.strip())
        cnt, cost, profit = await load_daily_data(to_check_uid, data_type, box_name=base_box_name, check_user_type="single")
        net = profit - cost
        if cnt == 0:
            retry_box_name = f"{base_box_name}盲盒"
            retry_cnt, retry_cost, retry_profit = await load_daily_data(to_check_uid, data_type, box_name=retry_box_name, check_user_type="single")
            if retry_cnt > 0:
                box_name = retry_box_name
                cnt, cost, profit = retry_cnt, retry_cost, retry_profit
                net = profit - cost
                reply_box_name = f"{base_box_name}盲盒"
            else:
                if reply_box_name.strip().endswith("盲盒"):
                    reply_box_name = reply_box_name.strip()
                else:
                    reply_box_name = f"{reply_box_name}盲盒"

    if cnt > 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝今天已抽取{cnt}个{reply_box_name}，净收益{net:.0f}电池"
        else:
            reply = f"[盲盒姬]{to_check_uname}老师今天已抽取{cnt}个{reply_box_name}，净收益{net:.0f}电池"

        if net < -10000:
            reply += "!？"
        elif net < -2000:
            reply += "？"
        elif net > 10000:
            reply += "?！"
        elif net > 2000:
            reply += "!！"
        else:
            reply += "！"
    
    elif cnt == 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝今天还没有开过{reply_box_name}哦"
        else:
            reply = f"[盲盒姬]{to_check_uname}老师今天还没有开过{reply_box_name}哦"
    
    if len(reply) <= 40:
        await reply_queue.put((uid, reply))
    else:
        part1 = reply[:40]
        part2 = "[盲盒姬]" + reply[40:]
        await reply_queue.put((uid, part1))
        await reply_queue.put((uid, part2))

    add_log(f"[盲盒姬] 回复 {uname}（指定查询用户: {to_check_uname}）")
    last_query_time[uid_str] = now

# 月度盲盒姬
async def call_month_box(uid, uname, msg):
    global last_query_time
    add_log(f"[盲盒姬] {uname}触发月份盲盒姬")
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
        return

    if uid == ADMIN_ID:
        add_log("[盲盒姬] 卡米宝宝触发盲盒姬")
        await asyncio.sleep(3)

    month, box_name = extract_month_and_type(msg)
    
    if month is None:
        return

    # reply_box_name = BOX_MEMORY_MAP.get(box_name, "盲盒")
    reply_box_name = box_name

    year = datetime.now().year
    data_type = "box" if box_name == "盲盒" else "gift"

    if data_type == "box":
        month_cnt, month_cost, month_profit = await load_month_data(uid, month, year, data_type, box_name=box_name, check_user_type="single")
        month_net = month_profit - month_cost
        
    elif data_type == "gift":
        base_box_name = re.sub(r'(盲盒)+$', '', reply_box_name.strip())
        month_cnt, month_cost, month_profit = await load_month_data(uid, month, year, data_type, box_name=base_box_name, check_user_type="single")
        month_net = month_profit - month_cost
        if month_cnt == 0:
            retry_box_name = f"{base_box_name}盲盒"
            retry_cnt, retry_cost, retry_profit = await load_month_data(uid, month, year, data_type, box_name=retry_box_name, check_user_type="single")
            if retry_cnt > 0:
                box_name = retry_box_name
                month_cnt, month_cost, month_profit = retry_cnt, retry_cost, retry_profit
                month_net = month_profit - month_cost
                reply_box_name = f"{base_box_name}盲盒"
            else:
                if reply_box_name.strip().endswith("盲盒"):
                    reply_box_name = reply_box_name.strip()
                else:
                    reply_box_name = f"{reply_box_name}盲盒"
    
    if month_cnt > 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝{month}月已抽取{month_cnt}个{reply_box_name}，净收益{month_net:.0f}电池"
        else:
            reply = f"[盲盒姬]{uname}老师{month}月已抽取{month_cnt}个{reply_box_name}，净收益{month_net:.0f}电池"
    
        if month_net < -50000:
            reply += "!？"
        elif month_net < -10000:
            reply += "？"
        elif month_net > 50000:
            reply += "?！"
        elif month_net > 10000:
            reply += "!！"
        else:
            reply += "！"

    elif month_cnt == 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝{month}月还没有抽取过{reply_box_name}哦"
        else:
            reply = f"[盲盒姬]{uname}老师{month}月还没有抽取过{reply_box_name}哦"
    
    if len(reply) <= 40:
        await reply_queue.put((uid, reply))
    else:
        part1 = reply[:40]
        part2 = "[盲盒姬]" + reply[40:]
        await reply_queue.put((uid, part1))
        await reply_queue.put((uid, part2))
    
    add_log(f"[盲盒姬] 发送月份统计")
    last_query_time[uid_str] = now

# 月度全局盲盒姬
async def call_month_all_box(uid, uname, msg):
    global last_query_time
    add_log(f"[盲盒姬] {uname}触发全局月份盲盒姬")
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
        return

    if uid == ADMIN_ID:
        add_log("[盲盒姬] 卡米宝宝触发全局盲盒姬")
        await asyncio.sleep(3)

    month, box_name = extract_month_and_type(msg)
    if month is None:
        return

    # reply_box_name = BOX_MEMORY_MAP.get(box_name, "盲盒")
    reply_box_name = box_name

    year = datetime.now().year
    data_type = "box" if box_name == "盲盒" else "gift"

    if data_type == "box":
        month_cnt, month_cost, month_profit = await load_month_data(uid, month, year, data_type, box_name=box_name, check_user_type="all")
        month_net = month_profit - month_cost
    elif data_type == "gift":
        base_box_name = re.sub(r'(盲盒)+$', '', reply_box_name.strip())
        month_cnt, month_cost, month_profit = await load_month_data(uid, month, year, data_type, box_name=base_box_name, check_user_type="all")
        month_net = month_profit - month_cost
        if month_cnt == 0:
            retry_box_name = f"{base_box_name}盲盒"
            retry_cnt, retry_cost, retry_profit = await load_month_data(uid, month, year, data_type, box_name=retry_box_name, check_user_type="all")
            if retry_cnt > 0:
                box_name = retry_box_name
                month_cnt, month_cost, month_profit = retry_cnt, retry_cost, retry_profit
                month_net = month_profit - month_cost
                reply_box_name = f"{base_box_name}盲盒"
            else:
                if reply_box_name.strip().endswith("盲盒"):
                    reply_box_name = reply_box_name.strip()
                else:
                    reply_box_name = f"{reply_box_name}盲盒"
    if month_cnt > 0:
        reply = f"[盲盒姬]{month}月全场已抽取{month_cnt}个{reply_box_name}，净收益{month_net:.0f}电池"

        if month_net < -50000:
            reply += "!？"
        elif month_net < -10000:
            reply += "？"
        elif month_net > 50000:
            reply += "?！"
        elif month_net > 10000:
            reply += "!！"
        else:
            reply += "！"
        
        if len(reply) <= 40:
            await reply_queue.put((uid, reply))
        else:
            part1 = reply[:40]
            part2 = "[盲盒姬]" + reply[40:]
            await reply_queue.put((uid, part1))
            await reply_queue.put((uid, part2))

    elif month_cnt == 0:
        reply = f"[盲盒姬]{month}月还没有人抽取过{reply_box_name}哦"
        await reply_queue.put((uid, reply))
    
    add_log(f"[盲盒姬] 发送月份全局统计")
    last_query_time[uid_str] = now

# 指定uid月度盲盒姬
async def call_month_at_box(uid, uname, msg):
    global last_query_time
    now = time.time()
    uid_str = str(uid)
    if uid_str in last_query_time and now - last_query_time[uid_str] < 10:
        return

    if uid not in [ADMIN_ID, YQZ_ID, XIAOZAO_ID]:
        return

    if uid == ADMIN_ID:
        add_log("[盲盒姬] 卡米宝宝触发盲盒姬")
        await asyncio.sleep(3)

    at_match = re.search(r'@(\d+)$', msg)
    to_check_uid_str = at_match.group(1) if at_match else "0"
    clean_msg = re.sub(r'@\d+$', '', msg)

    user_data = MEMORY["box"].get(to_check_uid_str)
    if user_data:
        to_check_uid = user_data.get("uid", 0)
        to_check_uname = user_data.get("uname", "您指定的")
    else:
        to_check_uid = int(to_check_uid_str.strip())
        try:
            u = user.User(to_check_uid, credential=credential)
            to_check_info = await u.get_user_info()
            to_check_uname = to_check_info.get("name", "您指定的")
        except Exception as e:
            to_check_uname = "Default"
            print(f"ERROR when loading to_check_uname: {e}")

    month, box_name = extract_month_and_type(clean_msg)

    if month is None:
        return

    # reply_box_name = BOX_MEMORY_MAP.get(box_name, "盲盒")
    reply_box_name = box_name

    year = datetime.now().year
    data_type = "box" if box_name == "盲盒" else "gift"
    if data_type == "box":
        month_cnt, month_cost, month_profit = await load_month_data(to_check_uid, month, year, data_type, box_name=box_name, check_user_type="single")
        month_net = month_profit - month_cost
    elif data_type == "gift":
        base_box_name = re.sub(r'(盲盒)+$', '', reply_box_name.strip())
        month_cnt, month_cost, month_profit = await load_month_data(to_check_uid, month, year, data_type, box_name=base_box_name, check_user_type="single")
        month_net = month_profit - month_cost
        if month_cnt == 0:
            retry_box_name = f"{base_box_name}盲盒"
            retry_cnt, retry_cost, retry_profit = await load_month_data(to_check_uid, month, year, data_type, box_name=retry_box_name, check_user_type="single")
            if retry_cnt > 0:
                box_name = retry_box_name
                month_cnt, month_cost, month_profit = retry_cnt, retry_cost, retry_profit
                month_net = month_profit - month_cost
                reply_box_name = f"{base_box_name}盲盒"
            else:
                if reply_box_name.strip().endswith("盲盒"):
                    reply_box_name = reply_box_name.strip()
                else:
                    reply_box_name = f"{reply_box_name}盲盒"
    if month_cnt > 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝{month}月已抽取{month_cnt}个{reply_box_name}，净收益{month_net:.0f}电池"
        else:
            reply = f"[盲盒姬]{to_check_uname}老师{month}月已抽取{month_cnt}个{reply_box_name}，净收益{month_net:.0f}电池"

        if month_net < -50000:
            reply += "!？"
        elif month_net < -10000:
            reply += "？"
        elif month_net > 50000:
            reply += "?！"
        elif month_net > 10000:
            reply += "!！"
        else:
            reply += "！"

    elif month_cnt == 0:
        if uid == ADMIN_ID:
            reply = f"[盲盒姬]卡米宝宝{month}月还没有抽取过{reply_box_name}哦"
        else:
            reply = f"[盲盒姬]{to_check_uname}老师{month}月还没有抽取过{reply_box_name}哦"
    
    if len(reply) <= 40:
        await reply_queue.put((uid, reply))
    else:
        part1 = reply[:40]
        part2 = "[盲盒姬]" + reply[40:]
        await reply_queue.put((uid, part1))
        await reply_queue.put((uid, part2))
    
    add_log(f"[盲盒姬] 回复 {uname}（指定查询用户：{to_check_uname}）")
    last_query_time[uid_str] = now


#################################
# 辅助函数
def box_calculate(uid_str, daily_data, check_user_type):
    # check_user_type: "single" or "all"
    daily_cnt, daily_cost, daily_profit = 0, 0, 0
    if check_user_type == "single":
        for key, value in daily_data.items():
            if key == uid_str:
                daily_cnt += value.get("count", 0)
                daily_cost += value.get("cost", 0)
                daily_profit += value.get("profit", 0)
                break
    else:
        for key, value in daily_data.items():
            daily_cnt += value.get("count", 0)
            daily_cost += value.get("cost", 0)
            daily_profit += value.get("profit", 0)

    return daily_cnt, daily_cost, daily_profit

def boxn_calculate(uid_str, daily_data, box_name, check_user_type):
    # box_list = globals().get(f"BOX_LIST_{n}", {})
    daily_cnt, daily_cost, daily_profit = 0, 0, 0
    # single_cost = [50, 500, 150, 250, 250, 90, 90, 500, 90, 90]
    '''
    if check_user_type == "single":
        for key, value in daily_data.items():
            if key == uid_str:
                for gift_name, cnt in value.get("gift_list", {}).items():
                    if gift_name in box_list:
                        price = box_list[gift_name]
                        daily_cnt += cnt
                        daily_cost += cnt * single_cost[n-1]
                        daily_profit += cnt * price
    else:
        for key, value in daily_data.items():
            for gift_name, cnt in value.get("gift_list", {}).items():
                if gift_name in box_list:
                    price = box_list[gift_name]
                    daily_cnt += cnt
                    daily_cost += cnt * single_cost[n-1]
                    daily_profit += cnt * price

    return daily_cnt, daily_cost, daily_profit
    '''

    if check_user_type == "single":
        user_data = daily_data.get(uid_str)
        if user_data:
            daily_cnt = user_data.get("info", {}).get(box_name, 0)
            daily_cost = user_data.get("cost_detail", {}).get(box_name, 0)
            daily_profit = user_data.get("profit_detail", {}).get(box_name, 0)
    else:
        for key, value in daily_data.items():
            daily_cnt += value.get("info", {}).get(box_name, 0)
            daily_cost += value.get("cost_detail", {}).get(box_name, 0)
            daily_profit += value.get("profit_detail", {}).get(box_name, 0)

    return daily_cnt, daily_cost, daily_profit

async def load_month_data(uid, month, year, data_type, box_name="盲盒", check_user_type="single"):
    # data_type(str): "box", "gift"
    month_cnt = 0
    month_cost = 0
    month_profit = 0
    uid_str = str(uid)

    now = datetime.now()
    if month > now.month:
        year -= 1
    year = year % 100
    month_str = f"{month:02d}"

    pattern = re.compile(rf'box{year}{month_str}(\d{{2}})\.json')
    all_data = {}
    files_dir = f"history_files/box/"

    if not os.path.exists(files_dir):
        return (0, 0, 0)

    for filename in os.listdir(files_dir):
        match = pattern.match(filename)
        if not match:
            continue

        day = int(match.group(1))
        try:
            with open(files_dir + filename, "r", encoding="utf-8") as f:
                daily_data = json.load(f)
        except Exception as e:
            print(f"Error when loading {filename}: {e}")
            continue

        if data_type == "box":
            daily_cnt, daily_cost, daily_profit = box_calculate(uid_str, daily_data, check_user_type=check_user_type)
            
        # elif data_type == "gift" and box_name in GIFT_BOX_MAP:
        elif data_type == "gift" and box_name != "盲盒":
            # full_box_name = BOX_MEMORY_MAP.get(box_name, box_name)
            full_box_name = box_name
            daily_cnt, daily_cost, daily_profit = boxn_calculate(uid_str, daily_data, box_name=full_box_name, check_user_type=check_user_type)
            
        month_cnt += daily_cnt
        month_cost += daily_cost
        month_profit += daily_profit

    # 当天的盲盒数据
    # if data_type == "box":
    try:
        with open("files/box.json", "r", encoding="utf-8") as f:
            daily_data = json.load(f)
        if data_type == "box":
            daily_cnt, daily_cost, daily_profit = box_calculate(uid_str, daily_data, check_user_type=check_user_type)
        # month_cnt += daily_cnt
        # month_cost += daily_cost
        # month_profit += daily_profit
    # except Exception as e:
    #     print(f"No box.json: {e}, command passed")

        # elif data_type == "gift" and box_name in BOX_MEMORY_MAP:
        elif data_type == "gift":
            # try:
                # with open("files/gift.json", "r", encoding="utf-8") as f:
                #     daily_data = json.load(f)
            # full_box_name = BOX_MEMORY_MAP.get(box_name, box_name)
            full_box_name = box_name
            daily_cnt, daily_cost, daily_profit = boxn_calculate(uid_str, daily_data, box_name=full_box_name, check_user_type=check_user_type)
            # except Exception as e:
            #     print(f"No gift.json: {e}, command passed")
        else:
            daily_cnt, daily_cost, daily_profit = 0, 0, 0
        
        month_cnt += daily_cnt
        month_cost += daily_cost
        month_profit += daily_profit

    except Exception as e:
        print(f"No box.json: {e}, command passed")

    return month_cnt, month_cost, month_profit

async def load_daily_data(uid, data_type, box_name="盲盒", check_user_type="single"):
    daily_cnt = 0
    daily_cost = 0
    daily_profit = 0
    uid_str = str(uid)

    try:
        with open("files/box.json", "r", encoding="utf-8") as f:
            daily_data = json.load(f)
        if data_type == "box":
            daily_cnt, daily_cost, daily_profit = box_calculate(uid_str, daily_data, check_user_type=check_user_type)
            return daily_cnt, daily_cost, daily_profit

        # elif data_type == "gift" and box_name in BOX_MEMORY_MAP:
        elif data_type == "gift":
            # with open("files/gift.json", "r", encoding="utf-8") as f:
            #     daily_data = json.load(f)
            # full_box_name = BOX_MEMORY_MAP.get(box_name, box_name)
            full_box_name = box_name
            daily_cnt, daily_cost, daily_profit = boxn_calculate(uid_str, daily_data, box_name=full_box_name, check_user_type=check_user_type)
            return daily_cnt, daily_cost, daily_profit
        
        return daily_cnt, daily_cost, daily_profit

    except Exception as e:
        print(f"No box.json: {e}, command passed")
        return 0, 0, 0

def extract_month_and_type(msg):
    # box_names_pattern = '|'.join(re.escape(name) for name in BOX_NAME_LIST)
    match = re.search(rf'呼叫(\d{{1,2}})月(.*?)盲盒姬', msg)
    # match = re.search(r'呼叫(\d{1,2})月(心动|幸运S|幸运|真爱|梦幻之夏|噜噜|棕意|大航海|欧气|猪猪侠)?盲盒姬', msg)
    if match:
        month = int(match.group(1))
        box_name = match.group(2) or "盲盒"
        if 1 <= month <= 12:
            return month, box_name
    
    # match = re.search(r'呼叫(一|二|三|四|五|六|七|八|九|十|十一|十二)月(心动|幸运S|幸运|真爱|梦幻之夏|噜噜|棕意|大航海|欧气|猪猪侠)?盲盒姬', msg)
    match = re.search(rf'呼叫(一|二|三|四|五|六|七|八|九|十|十一|十二)月(.*?)盲盒姬', msg)
    if match:
        box_name = match.group(2) or "盲盒"
        return CN_MONTHS[match.group(1)], box_name
    
    return None, "盲盒"

def extract_type(msg):
    # box_names_pattern = '|'.join(re.escape(name) for name in BOX_NAME_LIST)
    pattern = rf'呼叫(.*?)盲盒姬'
    # match = re.search(r'呼叫(心动|幸运S|幸运|真爱|梦幻之夏|噜噜|棕意|大航海|欧气|猪猪侠)?盲盒姬', msg)
    match = re.search(pattern, msg)
    if match:
        box_name = match.group(1) or "盲盒"
        return box_name
    return "盲盒"