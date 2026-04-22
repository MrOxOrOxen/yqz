from bilibili_api import live, sync, Credential
from bilibili_api.live import LiveDanmaku
import json, time, os, sys, ssl
import asyncio
import aiohttp
from pathlib import Path

sys.path.append(r"D:\\")
from data import SESSDATA, BILI_JCT, BUVID3
credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

STATS_FILE = "user_stats.json"
LEDGER_FILE = "gift_ledger.json"
user_stats = {}
all_user_stats = {}
last_query_time = {}
last_global_reply = 0

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

temp_room_id = input("请输入直播间号：")
ROOM_ID = int(temp_room_id)

def load_data():
    global user_stats, all_user_stats
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            user_stats = json.load(f)
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_user_stats = {str(item.get('uid', '0')): item for item in data if 'uid' in item}
            else:
                all_user_stats = data
    
def save_all_data():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_stats, f, ensure_ascii=False, indent=4)

        sorted_list = sorted(
            all_user_stats.values(), 
            key=lambda x: x.get('total_batteries', 0), 
            reverse=True
        )

        final_output = []
        for user in sorted_list:
            entry = {
                "uid": user.get("uid"),
                "uname": user.get("uname", "未知用户"),
                "total_batteries": user.get("total_batteries", 0)
            }
            if entry["total_batteries"] >= 10:
                entry["gift_list"] = user.get("gift_list", {})
            final_output.append(entry)

        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"!!! 保存数据时出错: {e}")

def update_ledger(uid, uname, gift_name, num, battery_count):
    uid_str = str(uid)
    if uid_str not in all_user_stats:
        all_user_stats[uid_str] = {
            "uid": uid,
            "uname": uname,
            "total_batteries": 0,
            "gift_list": {}
        }
    
    user = all_user_stats[uid_str]
    user["uname"] = uname
    user["total_batteries"] += battery_count

    if gift_name:
        user["gift_list"][gift_name] = user["gift_list"].get(gift_name, 0) + num
    
    save_all_data()

def handle_box_logic(uid, uname, bg_name, bg_num, bg_price, g_value):
    global user_stats
    uid_str = str(uid)
    if "盲盒" in str(bg_name): 
        if uid_str not in user_stats:
            user_stats[uid_str] = {"uname": uname, "count": 0, "cost": 0, "profit": 0}
        
        user_stats[uid_str]["count"] += bg_num
        user_stats[uid_str]["cost"] += bg_price * bg_num
        user_stats[uid_str]["profit"] += g_value * bg_num
        print(f"[盲盒] {uname} 开启 {bg_name}x{bg_num}")

async def send_reply(room_id, content, reply_uid=None):
    url = "https://api.live.bilibili.com/msg/send"
    payload = {
        "bubble": "0", "msg": content, "color": "16777215", "mode": "1",
        "fontsize": "25", "rnd": int(time.time()), "roomid": room_id,
        "csrf": BILI_JCT, "csrf_token": BILI_JCT
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
                await resp.json()
    except:
        pass

room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('SEND_GIFT')
async def on_gift(event):
    data = event['data']['data']
    uid = data.get('uid')
    uname = data.get('sender_uinfo', {}).get('base', {}).get('name', '用户')
    gift_name = data.get('giftName')
    num = data.get('num', 1)
    price = data.get('price', 0) * 10
    battery_count = (price * num) / 1000

    update_ledger(uid, uname, gift_name, num, battery_count)

    # if box
    blind_data = data.get('blind_gift') or (data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift'))
    if blind_data:
        bg_name = blind_data.get('original_gift_name')
        bg_price = blind_data.get('original_gift_price', 0) / 1000 
        g_value = blind_data.get('gift_tip_price', 0) / 1000
        handle_box_logic(uid, uname, bg_name, num, bg_price, g_value)
    else:
        print(f"[礼物] {uname} 送出 {gift_name}x{num}")

@room.on('SUPER_CHAT_MESSAGE')
async def on_sc(event):
    data = event['data']['data']
    uid = data.get('uid')
    uname = data.get('user_info', {}).get('uname', '用户')
    price = data.get('price', 0)
    battery_count = price * 10
    print(f"[SC] {uname} 送出 {price}元 SC")
    update_ledger(uid, uname, "SuperChat", 1, battery_count)

@room.on('GUARD_BUY')
async def on_guard(event):
    data = event['data']['data']
    uid = data.get('uid')
    uname = data.get('username', '用户')
    gift_name = data.get('gift_name')
    num = data.get('num', 1)
    price = data.get('price', 0) / 1000
    print(f"[大航海] {uname} 购买了 {gift_name}")
    update_ledger(uid, uname, gift_name, num, price)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    global last_global_reply, last_query_time
    data = event['data']['info']
    msg = data[1]
    uid_str = str(data[2][0])
    uname = data[2][1]
    raw_uid = data[2][0]

    print(f"[{uname}]: {msg}")

    if msg == "呼叫盲盒姬":
        current_time = time.time()
        if uid_str in last_query_time and current_time - last_query_time[uid_str] < 10:
            return
        if current_time - last_global_reply < 3:
            return
        if uid_str in user_stats:
            stats = user_stats[uid_str]
            net_val = (stats['profit'] - stats['cost']) * 10
            reply = f"[盲盒姬] {uname}老师已抽取{stats['count']}个盲盒，净收益{net_val:.0f}电池！"

        else:
            reply = f"[盲盒姬] {uname}老师今天还没有开过盲盒哦"

        last_query_time[uid_str] = current_time
        last_global_reply = current_time

        await send_reply(ROOM_ID, reply, reply_uid=raw_uid)

if __name__ == "__main__":
    load_data()
    print(f"正在连接到直播间 [{ROOM_ID}]...")
    try:
        sync(room.connect())
    except KeyboardInterrupt:
        print("\n程序已手动停止")
    except Exception as e:
        print(f"连接意外中断: {e}")