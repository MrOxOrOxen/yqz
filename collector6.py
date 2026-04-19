from bilibili_api import live, sync
import json, requests, time, sys
import tkinter as tk
from threading import Thread
import asyncio

# --- 全局变量 ---
ROOM_ID = 6924122
gift_data = {}
total_cost = 0.0
total_profit = 0.0
total_box_count = 0
room_instance = None  # 更改变量名避免与指令冲突

def get_gift_dict_json(room_id):
    url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": f"https://live.bilibili.com/{room_id}"}
    params = {"room_id": room_id, "platform": "pc"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)
        data = response.json()
        if data['code'] == 0:
            gift_list = data['data']['list']
            gift_map = {str(g['id']): {"name": g['name'], "price": g['price'] / 1000} for g in gift_list}
            return gift_map
    except:
        return None

def handle_logic(bg_name, bg_num, bg_value, g_num, g_value):
    global total_cost, total_profit, total_box_count
    if "盲盒" in str(bg_name):
        total_cost += bg_value * bg_num
        total_box_count += bg_num
        total_profit += g_value * g_num

def register_callbacks(new_room):
    @new_room.on('SEND_GIFT')
    @new_room.on('COMBO_SEND')
    async def on_gift(event):
        data = event['data'].get('data', {})
        blind = data.get('blind_gift')
        combo = data.get('batch_combo_send') or {}
        if blind:
            bg_name = blind.get('original_gift_name')
            bg_val = blind.get('original_gift_price', 0) / 1000
            bg_num = combo.get('batch_combo_num', data.get('num', 1))
            g_val = blind.get('gift_tip_price', 0) / 1000
            g_num = combo.get('gift_num', data.get('num', 1))
            handle_logic(bg_name, bg_num, bg_val, g_num, g_val)

# --- 增强版终端控制任务 ---
async def console_listener():
    global total_cost, total_profit, total_box_count, ROOM_ID, room_instance
    print("\n" + "="*30)
    print("指令系统就绪，可用指令：")
    print("- setroom [ID]   : 切换房间并清零数据")
    print("- setcost [数字] : 手动设置当前总成本")
    print("- setprofit [数字]: 手动设置当前总收益")
    print("- reset          : 全部数据归零")
    print("="*30 + "\n")
    
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        parts = line.strip().lower().split()
        if not parts: continue
        
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        try:
            if cmd == "setroom" and arg:
                total_cost, total_profit, total_box_count = 0.0, 0.0, 0
                ROOM_ID = int(arg)
                print(f"房间已切换至 {ROOM_ID}，数据已清零")
                await room_instance.disconnect()
            
            elif cmd == "setcost" and arg:
                total_cost = float(arg)
                # 假设手动设置成本时，盲盒数按 5元/个 粗略估算，或你可以保持原有 box_count
                print(f"成本已设为: {total_cost}")

            elif cmd == "setprofit" and arg:
                total_profit = float(arg)
                print(f"收益已设为: {total_profit}")
                
            elif cmd == "reset":
                total_cost, total_profit, total_box_count = 0.0, 0.0, 0
                print("所有数据已归零")
            
            else:
                print("无效指令或缺少参数")
        except ValueError:
            print("参数错误：请输入正确的数字")

# --- UI 界面 (移除房间号显示) ---
class StatsApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("云宝的盲盒统计器")
        self.root.attributes("-topmost", True)
        self.root.geometry("300x180")
        self.root.configure(bg='#f2f2f2')
        
        tk.Label(self.root, text="云宝的盲盒统计器", font=("微软雅黑", 14, "bold"), bg='#f2f2f2', fg='#fb7299').pack(pady=15)
        
        self.label_cost = tk.Label(self.root, text="", font=("微软雅黑", 10), bg='#f2f2f2')
        self.label_cost.pack(pady=2)
        
        self.label_profit = tk.Label(self.root, text="", font=("微软雅黑", 10), bg='#f2f2f2')
        self.label_profit.pack(pady=2)
        
        self.label_net = tk.Label(self.root, text="", font=("微软雅黑", 12, "bold"), bg='#f2f2f2')
        self.label_net.pack(pady=10)

    def update_ui(self):
        # UI 仅负责显示全局变量的当前值
        self.label_cost.config(text=f"总计送出成本：{total_cost:.1f} 元")
        self.label_profit.config(text=f"总计开出价值：{total_profit:.1f} 元")
        
        net = total_profit - total_cost
        if net < -0.01: color = "#f44336"
        elif net > 0.01: color = "#4caf50"
        else: color = "#333333"
            
        self.label_net.config(text=f"实时净盈亏：{net:.1f} 元", fg=color)
        self.root.after(500, self.update_ui)

# --- 异步运行桥接 ---
def run_async_bridge():
    async def main_logic():
        global room_instance
        while True:
            room_instance = live.LiveDanmaku(ROOM_ID)
            register_callbacks(room_instance)
            tasks = [
                asyncio.create_task(room_instance.connect()),
                asyncio.create_task(console_listener())
            ]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_logic())

if __name__ == "__main__":
    app = StatsApp()
    t = Thread(target=run_async_bridge, daemon=True)
    t.start()
    app.update_ui()
    app.root.mainloop()