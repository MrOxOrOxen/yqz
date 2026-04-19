from bilibili_api import live, sync
import json, requests, time
import tkinter as tk
from threading import Thread
import asyncio

ROOM_ID = 9483869
gift_data = {}  # 全局礼物价格表
total_cost = 0.0
total_profit = 0.0
total_box_count = 0
pending_boxes = {}

def get_gift_dict_json(room_id=27885573):
    """
    强制获取最新的礼物配置
    """
    print(f"正在获取房间 {room_id} 的礼物列表...")
    url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{room_id}"
    }
    params = {"room_id": room_id, "platform": "pc"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)
        response.raise_for_status()
        data = response.json()
        if data['code'] == 0:
            gift_list = data['data']['list']
            # 构建价格映射字典
            gift_map = {str(g['id']): {"name": g['name'], "price": g['price'] / 1000} for g in gift_list}
            
            # 成功获取后，顺手存一下本地，方便下次救急
            with open("bili_gift_map.json", "w", encoding="utf-8") as f:
                json.dump(gift_map, f, ensure_ascii=False, indent=4)
            print(f"API 获取成功，已更新并保存 {len(gift_map)} 个礼物配置")
            return gift_map
    except Exception as e:
        print(f"API 获取失败 (Connection Error): {e}")
    
    return None

def handle_logic(uid, user_name, bg_id, bg_name, bg_num, bg_value, g_id, g_name, g_num, g_value):
    global total_cost, total_profit, total_box_count
    bg_name = str(bg_name) if bg_name is not None else ""
    g_name = str(g_name) if g_name is not None else ""

    if "盲盒" in bg_name:
        cost_step = bg_value * bg_num
        total_cost += cost_step
        total_box_count += bg_num

        profit_step = g_value * g_num
        total_profit += profit_step


# --- 监听部分 ---
room = live.LiveDanmaku(ROOM_ID)

@room.on('SEND_GIFT')
async def on_gift(event):
    data_dict = event['data']
    print(f"收到礼物数据包: {data_dict}")
    real_uid = data_dict.get('data').get('sender_uinfo').get('uid')
    real_uname = data_dict.get('data').get('sender_uinfo').get('base').get('name') or data_dict.get('data').get('sender_uinfo').get('base').get('origin_info').get('name')
    # 盲盒（开之前）
    if data_dict['data']['blind_gift'] is not None:
        bg_name = data_dict.get('data').get('blind_gift').get('original_gift_name')
        bg_value = data_dict.get('data').get('blind_gift').get('original_gift_price') / 1000
        bg_id = data_dict.get('data').get('blind_gift').get('original_gift_id')
        bg_num = data_dict.get('data').get('batch_combo_send').get('batch_combo_num')
    else:
        bg_name = "Default"
        bg_value = 0
        bg_id = "0"
        bg_num = 0

    # 盲盒（开之后）
    g_id = data_dict.get('data').get('giftId') or data_dict.get('data').get('batch_combo_send').get('gift_id')
    g_name = data_dict.get('data').get('giftName') or data_dict.get('data').get('batch_combo_send').get('gift_name')
    g_num = data_dict.get('data').get('batch_combo_send').get('gift_num')
    if data_dict['data']['blind_gift'] is not None:
        g_value = data_dict.get('data').get('blind_gift').get('gift_tip_price') / 1000
    else:
        g_value = data_dict.get('data').get('price') / 1000
    print(f"INFO: 收到来自 [{real_uname}]({real_uid}) 的 {g_name} x{g_num} ({g_value*10}电池)")
    handle_logic(
        uid=real_uid,
        user_name=real_uname,
        bg_id=bg_id,
        bg_name=bg_name,
        bg_num=bg_num,
        bg_value=bg_value,
        g_id=g_id,
        g_name=g_name,
        g_num=g_num,
        g_value=g_value
    )


@room.on('COMBO_SEND')
async def on_gift(event):
    data_dict = event['data']
    print(f"收到礼物数据包: {data_dict}")
    real_uid = data_dict.get('data').get('sender_uinfo').get('uid')
    real_uname = data_dict.get('data').get('sender_uinfo').get('base').get('name') or data_dict.get('data').get('sender_uinfo').get('base').get('origin_info').get('name')
    # 盲盒（开之前）
    if data_dict['data']['blind_gift'] is not None:
        bg_name = data_dict.get('data').get('blind_gift').get('original_gift_name')
        bg_value = data_dict.get('data').get('blind_gift').get('original_gift_price') / 1000
        bg_id = data_dict.get('data').get('blind_gift').get('original_gift_id')
        bg_num = data_dict.get('data').get('batch_combo_send').get('batch_combo_num')
    else:
        bg_name = "Default"
        bg_value = 0
        bg_id = "0"
        bg_num = 0

    # 盲盒（开之后）
    g_id = data_dict.get('data').get('giftId') or data_dict.get('data').get('batch_combo_send').get('gift_id')
    g_name = data_dict.get('data').get('giftName') or data_dict.get('data').get('batch_combo_send').get('gift_name')
    g_num = data_dict.get('data').get('batch_combo_send').get('gift_num')
    if data_dict['data']['blind_gift'] is not None:
        g_value = data_dict.get('data').get('blind_gift').get('gift_tip_price') / 1000
    else:
        g_value = data_dict.get('data').get('price') / 1000
    print(f"INFO: 收到来自 [{real_uname}]({real_uid}) 的 {g_name} x{g_num} ({g_value*10}电池)")
    handle_logic(
        uid=real_uid,
        user_name=real_uname,
        bg_id=bg_id,
        bg_name=bg_name,
        bg_num=bg_num,
        bg_value=bg_value,
        g_id=g_id,
        g_name=g_name,
        g_num=g_num,
        g_value=g_value
    )

# --- UI 界面 ---
class StatsApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("云宝的盲盒统计器")
        self.root.attributes("-topmost", True)
        self.root.geometry("300x200")
        self.root.configure(bg='#f2f2f2')
        
        tk.Label(self.root, text="云宝的盲盒统计器", font=("微软雅黑", 14, "bold"), bg='#f2f2f2', fg='#fb7299').pack(pady=10)
        self.label_cost = tk.Label(self.root, text="总计送出成本：0个盲盒 (0电池)", font=("微软雅黑", 12), bg='#f2f2f2')
        self.label_cost.pack(pady=3)
        self.label_profit = tk.Label(self.root, text="总计开出价值：0电池", font=("微软雅黑", 12), bg='#f2f2f2')
        self.label_profit.pack(pady=3)
        self.label_net = tk.Label(self.root, text="净盈亏：0电池", font=("微软雅黑", 12, "bold"), bg='#f2f2f2')
        self.label_net.pack(pady=10)

    def update_ui(self):
        self.label_cost.config(text=f"总计送出：{total_box_count}个盲盒 ({total_cost*10:.0f}电池)")
        self.label_profit.config(text=f"总计开出：{total_profit*10:.0f}电池")
        net = total_profit - total_cost
        
        if net < -0.01: color = "#f44336" # 亏损红
        elif net > 0.01: color = "#4caf50" # 盈利绿
        else: color = "#333333" # 持平黑
            
        self.label_net.config(text=f"净收益：{net*10:.0f}电池", fg=color)
        self.root.after(500, self.update_ui)

def run_bili():
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    sync(room.connect())

if __name__ == "__main__":
    # --- 第一步：强制尝试 API 更新 ---
    online_data = get_gift_dict_json(ROOM_ID)
    
    if online_data:
        gift_data = online_data
    else:
        # --- 第二步：API 失败后才尝试本地加载 ---
        print("API 获取失败，尝试加载本地缓存备用...")
        try:
            with open("bili_gift_map.json", "r", encoding="utf-8") as f:
                gift_data = json.load(f)
            print(f"成功恢复本地配置 ({len(gift_data)}条)。")
        except:
            print("警告：本地配置也不存在，所有礼物单价将计为 0！")
            gift_data = {}

    app = StatsApp()
    t = Thread(target=run_bili, daemon=True)
    t.start()

    app.update_ui()
    app.root.mainloop()