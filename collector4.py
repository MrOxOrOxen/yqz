from bilibili_api import live, sync
import json, requests, time
import tkinter as tk
from threading import Thread
import asyncio

ROOM_ID = 25902599
gift_data = {}
total_cost = 0.0
total_profit = 0.0
total_box_count = 0
pending_boxes = {}

def get_gift_dict_json(room_id=27885573):
    print("Getting gift list...")
    url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{room_id}"
    }
    params = {
        "room_id": room_id,
        "platform": "pc"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data['code'] != 0:
            print(f"Socket return error: {data['message']}")
            return
        
        gift_list = data['data']['list']
        gift_map = {}
        
        for gift in gift_list:
            g_id = str(gift['id'])
            gift_map[g_id] = {
                "name": gift['name'],
                "price": gift['price'] / 1000
            }
        
        with open("bili_gift_map.json", "w", encoding="utf-8") as f:
            json.dump(gift_map, f, ensure_ascii=False, indent=4)
        print(f"Gift list saved at bili_gift_map.json. {len(gift_map)} gifts saved.")

    except Exception as e:
        print(f"Gift list error: {e}")

    return {}

def handle_logic(uid, user_name, gift_id, gift_name, gift_num):
    global total_cost, total_profit, total_box_count, pending_boxes, gift_data

    if not gift_data:
        print("Gift data is empty.")
        gift_data = {}

    price = gift_data.get(str(gift_id), {}).get("price", 0)
    current_val = price * gift_num

    if "盲盒" in gift_name:
        total_cost += current_val
        total_box_count += gift_num
        if uid not in pending_boxes:
            pending_boxes[uid] = {"count": 0, "time": time.time()}
        pending_boxes[uid]["count"] += gift_num
        pending_boxes[uid]["time"] = time.time()

        print(f"{user_name}开启了{gift_name}个盲盒")

    elif uid in pending_boxes:
        if (time.time() - pending_boxes[uid]["time"]) < 5:
            total_profit += current_val
            pending_boxes[uid]["count"] -= gift_num
            pending_boxes[uid]["time"] = time.time()
            
            if pending_boxes[uid]["count"] <= 0:
                del pending_boxes[uid]
            print(f"{user_name}抽中奖品: {gift_name} x{gift_num}")
        else:
            del pending_boxes[uid]

room = live.LiveDanmaku(ROOM_ID)
@room.on('SEND_GIFT')
async def on_gift(event):
    data = event['data']
    handle_logic(
        uid = data.get('uid'),
        user_name = data.get('uname'),
        gift_id = data.get('giftId'),
        gift_name = data.get('giftName'),
        gift_num = int(data.get('num', 1))
    )

@room.on('COMBO_SEND')
async def on_combo(event):
    data = event['data']
    handle_logic(
        uid = data.get('uid'),
        user_name = data.get('uname'),
        gift_id = data.get('gift_id'),
        gift_name = data.get('gift_name'),
        gift_num = int(data.get('combo_num', 1)) 
    )

class StatsApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("云宝的盲盒统计器")
        self.root.attributes("-topmost", True)
        self.root.geometry("300x200")
        
        self.root.configure(bg='#f0f0f0')
        self.label_title = tk.Label(self.root, text="云宝的盲盒统计器", font=("微软雅黑", 16, "bold"), bg='#f0f0f0', fg='#fb7299')
        self.label_title.pack(pady=10)
        
        self.label_cost = tk.Label(self.root, text="总计送出：0个盲盒 (0元)", font=("微软雅黑", 11), bg='#f0f0f0')
        self.label_cost.pack(pady=5)
        
        self.label_profit = tk.Label(self.root, text="总计开出：0元", font=("微软雅黑", 11), bg='#f0f0f0')
        self.label_profit.pack(pady=5)

        self.label_net = tk.Label(self.root, text="净盈亏：0元", font=("微软雅黑", 11), bg='#f0f0f0')
        self.label_net.pack(pady=5)

    def update_ui(self):
        self.label_cost.config(text=f"总计送出：{total_box_count}个盲盒 ({total_cost:.1f}元)")
        self.label_profit.config(text=f"总计开出：{total_profit:.1f}元")
        net = total_profit - total_cost
        color = "#f44336" if net < 0 else "#4caf50"
        self.label_net.config(text=f"净盈亏：{net:.1f}元", fg=color)
        self.root.after(1000, self.update_ui)

def run_bili():
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    sync(room.connect())

if __name__ == "__main__":
    with open("bili_gift_map.json", "r", encoding="utf-8") as f:
        gift_data = json.load(f)

    gift_data = get_gift_dict_json(ROOM_ID)
    app = StatsApp()

    get_gift_dict_json()
    t = Thread(target=run_bili, daemon=True)
    t.start()

    app.update_ui()
    app.root.mainloop()