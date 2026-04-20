from bilibili_api import live, sync
import json, requests, time, os, sys, ssl
import tkinter as tk
from threading import Thread
import asyncio
import aiohttp

# ==================== 1. 环境优化与 SSL 补丁 ====================
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

# ==================== 2. 全局数据与状态 ====================
temp_room_id = input("直播间号：")
ROOM_ID = int(temp_room_id)
total_cost = 0.0
total_profit = 0.0
total_box_count = 0
combo_tracker = {}
IS_CONNECTED = False 

# ==================== 3. 业务逻辑 ====================
def handle_logic(bg_name, bg_num, bg_value, g_value):
    global total_cost, total_profit, total_box_count
    bg_name = str(bg_name) if bg_name is not None else ""
    if "盲盒" in bg_name: 
        total_cost += bg_value * bg_num 
        total_box_count += bg_num
        total_profit += g_value * bg_num

room = live.LiveDanmaku(ROOM_ID)

@room.on('ALL')
async def on_all(event):
    global IS_CONNECTED
    if not IS_CONNECTED:
        IS_CONNECTED = True

@room.on('SEND_GIFT')
async def on_gift(event):
    data = event['data']['data']
    uname = data.get('sender_uinfo', {}).get('base', {}).get('name', '用户')
    num = data.get('num', 1) # 获取礼物数量
    gift_name = data.get('giftName', '礼物')
    batch_id = data.get('batch_combo_id')

    if batch_id:
        combo_tracker[batch_id] = combo_tracker.get(batch_id, 0) + num
    
    blind_data = data.get('blind_gift') or (data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift'))
    
    if blind_data:
        # 盲盒打印逻辑
        # print(f"{uname} 送出盲盒 x{num}")
        print(f"+{num}")
        bg_name = blind_data.get('original_gift_name')
        bg_price = blind_data.get('original_gift_price', 0) / 1000 
        g_value = blind_data.get('gift_tip_price', 0) / 1000 
        handle_logic(bg_name, num, bg_price, g_value)
    else:
        # 加回的普通礼物打印逻辑，包含数量显示
        # print(f"[*] 收到普通礼物: {uname} 送出 {gift_name} x{num}")
        print("#")

@room.on('COMBO_SEND')
async def on_combo(event):
    data = event['data']['data']
    batch_id = data.get('batch_combo_id')
    if batch_id in combo_tracker:
        del combo_tracker[batch_id]

# ==================== 4. UI 界面 ====================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("云宝的盲盒统计器")
        self.root.attributes("-topmost", True)
        self.root.geometry("300x200")
        self.root.configure(bg='#f2f2f2')

        self.title_label = tk.Label(self.root, text="云宝的盲盒统计器", font=("微软雅黑", 16, "bold"), bg='#f2f2f2', fg='#ff0000')
        self.title_label.pack(pady=10)
        
        self.label_cost = tk.Label(self.root, text="正在同步网络...", font=("微软雅黑", 12), bg='#f2f2f2')
        self.label_cost.pack(pady=5)
        self.label_profit = tk.Label(self.root, text="", font=("微软雅黑", 12), bg='#f2f2f2')
        self.label_profit.pack(pady=5)
        self.label_net = tk.Label(self.root, text="", font=("微软雅黑", 14, "bold"), bg='#f2f2f2')
        self.label_net.pack(pady=10)
        
        self.update_ui()

    def update_ui(self):
        global IS_CONNECTED
        if IS_CONNECTED:
            self.title_label.config(fg='#fb7299') 
            self.label_cost.config(text=f"总计送出：{total_box_count}个盲盒 ({total_cost*10:.0f}电池)")
            self.label_profit.config(text=f"总计开出：{total_profit*10:.0f}电池")
            net = total_profit - total_cost
            color = "#f44336" if net < -0.01 else ("#4caf50" if net > 0.01 else "#333333")
            self.label_net.config(text=f"净收益：{net*10:.0f}电池", fg=color)
        else:
            self.title_label.config(fg='#ff0000') 
            self.label_cost.config(text="正在建立连接...")

        self.root.after(2000, self.update_ui)

def run_bili():
    global IS_CONNECTED
    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            IS_CONNECTED = False 
            sync(room.connect())
        except:
            IS_CONNECTED = False
            time.sleep(5)

if __name__ == "__main__":
    t = Thread(target=run_bili, daemon=True)
    t.start()
    
    root = tk.Tk()
    def on_closing():
        root.destroy()
        os._exit(0)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    app = App(root)
    root.mainloop()