from bilibili_api import live, sync, Credential
import json, time, os, sys, ssl
import asyncio
import aiohttp
import json
import sys
from pathlib import Path
sys.path.append(r"D:\\")

from data import SESSDATA, BILI_JCT, BUVID3

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

def patch_ssl():
    """防止部分环境下 SSL 握手失败"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    orig_init = aiohttp.TCPConnector.__init__
    def new_init(self, *args, **kwargs):
        kwargs['ssl'] = ssl_context
        orig_init(self, *args, **kwargs)
    aiohttp.TCPConnector.__init__ = new_init

patch_ssl()

# 初始化配置
temp_room_id = input("请输入直播间号：")
ROOM_ID = int(temp_room_id)

# 数据存储：{uid: {"uname": "", "count": 0, "cost": 0, "profit": 0}}
user_stats = {}
combo_tracker = {}

STATS_FILE = "user_stats.json"
def load_data():
    """程序启动时读取旧数据"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    """每次数据更新后写入文件"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_stats, f, ensure_ascii=False, indent=4)

user_stats = load_data()

def handle_logic(uid, uname, bg_name, bg_num, bg_price, g_value):
    """处理盲盒统计逻辑"""
    global user_stats
    uid_str = str(uid) # 统一转成字符串
    bg_name = str(bg_name) if bg_name is not None else ""
    
    if "盲盒" in bg_name: 
        if uid_str not in user_stats:
            # 修正点：这里必须也用 uid_str
            user_stats[uid_str] = {"uname": uname, "count": 0, "cost": 0, "profit": 0}
        
        user_stats[uid_str]["count"] += bg_num
        user_stats[uid_str]["cost"] += bg_price * bg_num
        user_stats[uid_str]["profit"] += g_value * bg_num
        
        save_data() # 实时保存
        # 修正点：这里的索引也统一用 uid_str
        print(f"[统计] {uname} 开盒x{bg_num} | 个人总消耗: {user_stats[uid_str]['cost']*10:.0f}电池")

async def send_reply(room_id, content):
    """通过 API 发送弹幕回复"""
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
    headers = {
        "Cookie": f"SESSDATA={SESSDATA}; bili_jct={BILI_JCT}; buvid3={BUVID3}",
        "Origin": "https://live.bilibili.com",
        "Referer": f"https://live.bilibili.com/{room_id}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as resp:
                res = await resp.json()
                if res['code'] == 0:
                    print(f">>> 成功回复：{content}")
                else:
                    print(f"!!! 回复失败：{res['message']}")
    except Exception as e:
        print(f"!!! 网络请求异常：{e}")

# 初始化直播间监听
room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('SEND_GIFT')
async def on_gift(event):
    """处理送礼事件"""
    data = event['data']['data']
    uid = data.get('uid')
    uname = data.get('sender_uinfo', {}).get('base', {}).get('name', '用户')
    num = data.get('num', 1)
    batch_id = data.get('batch_combo_id')

    if batch_id:
        combo_tracker[batch_id] = combo_tracker.get(batch_id, 0) + num
    
    blind_data = data.get('blind_gift') or (data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift'))
    
    if blind_data:
        bg_name = blind_data.get('original_gift_name')
        # 换算单位：金瓜子/1000 = 电池
        bg_price = blind_data.get('original_gift_price', 0) / 1000 
        g_value = blind_data.get('gift_tip_price', 0) / 1000 
        handle_logic(uid, uname, bg_name, num, bg_price, g_value)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    """处理弹幕指令"""
    data = event['data']['info']
    # print(event)
    msg = data[1]       # 弹幕内容
    uid_str = str(data[2][0])   # 发送者UID
    uname = data[2][1]  # 发送者用户名

    if msg == "呼叫盲盒姬":
        print(f"[指令] {uname} 请求查询数据")
        if uid_str in user_stats:
            stats = user_stats[uid_str]
            # 换算成电池展示（*10）
            cost_val = stats['cost'] * 10
            profit_val = stats['profit'] * 10
            net_val = profit_val - cost_val
            
            reply = (f"[盲盒姬] {uname}已抽取{stats['count']}个盲盒，"
                     f"净收益{net_val:.0f}电池！")
            
        else:
            reply = f"[盲盒姬] {uname}今天还没有开过盲盒哦"
        
        await send_reply(ROOM_ID, reply)

@room.on('COMBO_SEND')
async def on_combo(event):
    """处理连击结束逻辑"""
    data = event['data']['data']
    batch_id = data.get('batch_combo_id')
    if batch_id in combo_tracker:
        del combo_tracker[batch_id]

if __name__ == "__main__":
    print(f"正在连接到直播间 [{ROOM_ID}]...")
    try:
        sync(room.connect())
    except KeyboardInterrupt:
        print("\n程序已手动停止")
        os._exit(0)
    except Exception as e:
        print(f"连接意外中断: {e}")