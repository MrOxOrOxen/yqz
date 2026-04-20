from bilibili_api import live, sync
import json, requests, time
import tkinter as tk
from threading import Thread
import asyncio

ROOM_ID = 27885573
total_cost = 0.0
total_profit = 0.0
total_box_count = 0
combo_tracker = {}

def handle_logic(uid, user_name, bg_id, bg_name, bg_num, bg_value, g_id, g_name, g_num, g_value):
    """
    盲盒统计器核心逻辑
    """
    global total_cost, total_profit, total_box_count
    bg_name = str(bg_name) if bg_name is not None else ""
    
    if "盲盒" in bg_name:
        cost_step = bg_value * bg_num 
        total_cost += cost_step
        total_box_count += bg_num

        profit_step = g_value * g_num
        total_profit += profit_step

room = live.LiveDanmaku(ROOM_ID)

@room.on('SEND_GIFT')
async def on_gift(event):
    data = event['data']['data']
    print(event['data'])
    uname = data.get('sender_uinfo', '未知用户').get('base', '未知用户').get('name', '未知用户')
    uid = data.get('sender_uinfo').get('uid')
    gift_name = data.get('giftName', '未知礼物')
    gift_id = data.get('giftId')
    num = data.get('num', 1)
    is_first = data.get('is_first', True)
    batch_id = data.get('batch_combo_id')

    if batch_id:
        combo_tracker[batch_id] = combo_tracker.get(batch_id, 0) + num
        current_total = combo_tracker[batch_id]
    else:
        current_total = num

    blind_data = data.get('blind_gift') or (data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift'))
    
    # box output
    if blind_data:
        bg_name = blind_data.get('original_gift_name')
        bg_id = blind_data.get('original_gift_id')
        bg_price = blind_data.get('original_gift_price', 0) / 1000 # 
        g_value = blind_data.get('gift_tip_price', 0) / 1000 # 
        
        handle_logic(uid, uname, bg_id, bg_name, num, bg_price, gift_id, gift_name, num, g_value)
        
        if is_first and num > 1:
            print(f"【盲盒-批量】{uname} 一次性送出 {bg_name} x{num} -> 获得 {gift_name} (价值 {g_value*10:.0f}电池/个)")
        elif not is_first:
            print(f"【盲盒-连击】{uname} 连击 {bg_name} x{current_total} -> 获得 {gift_name} (价值 {g_value*10:.0f}电池)")
        else:
            print(f"【盲盒】{uname} 送出 {bg_name} -> 获得 {gift_name} (价值 {g_value*10:.0f}电池)")
            
    # normal output
    else:
        if is_first:
            if num > 1:
                print(f"【礼物-批量】{uname} 送出 {gift_name} x{num}")
            else:
                print(f"【礼物】{uname} 送出 {gift_name}")
        else:
            print(f"【礼物-连击】{uname} 连击 {gift_name} x{current_total}")

@room.on('COMBO_SEND')
async def on_combo(event):
    """
    连击结束信号 (log_last_try)
    """
    data = event['data']['data']
    print(event['data'])
    batch_id = data.get('batch_combo_id')

    # free memory
    if batch_id in combo_tracker:
        del combo_tracker[batch_id]

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("云宝的盲盒统计器")
        self.root.attributes("-topmost", True)
        self.root.geometry("300x200")
        self.root.configure(bg='#f2f2f2')

        tk.Label(self.root, text="云宝的盲盒统计器", font=("微软雅黑", 16, "bold"), bg='#f2f2f2', fg='#fb7299').pack(pady=10)
        self.label_cost = tk.Label(self.root, text="总计送出：0个盲盒 (0电池)", font=("微软雅黑", 14), bg='#f2f2f2')
        self.label_cost.pack(pady=10)
        self.label_profit = tk.Label(self.root, text="总计开出：0电池", font=("微软雅黑", 14), bg='#f2f2f2')
        self.label_profit.pack(pady=3)
        self.label_net = tk.Label(self.root, text="净收益：0电池", font=("微软雅黑", 14, "bold"), bg='#f2f2f2')
        self.label_net.pack(pady=10)
        
        self.update_ui()

    def update_ui(self):
        self.label_cost.config(text=f"总计送出：{total_box_count}个盲盒 ({total_cost*10:.0f}电池)")
        self.label_profit.config(text=f"总计开出：{total_profit*10:.0f}电池")
        net = total_profit - total_cost
        
        if net < -0.01: color = "#f44336"
        elif net > 0.01: color = "#4caf50"
        else: color = "#333333"
            
        self.label_net.config(text=f"净收益：{net*10:.0f}电池", fg=color)
        self.root.after(500, self.update_ui)

def run_bili():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sync(room.connect())

if __name__ == "__main__":
    t = Thread(target=run_bili, daemon=False)
    t.start()
    
    root = tk.Tk()
    app = App(root)
    root.mainloop()