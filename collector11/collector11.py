from bilibili_api import live, sync
import json, requests, time, os, sys, ssl
import tkinter as tk
from threading import Thread
import asyncio
import aiohttp

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

temp_room_id = input("直播间号：")
ROOM_ID = int(temp_room_id)
total_cost = 0.0
total_profit = 0.0
total_box_count = 0
combo_tracker = {}
IS_CONNECTED = False 

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
    num = data.get('num', 1)
    gift_name = data.get('giftName', '礼物')
    batch_id = data.get('batch_combo_id')

    if batch_id:
        combo_tracker[batch_id] = combo_tracker.get(batch_id, 0) + num
    
    blind_data = data.get('blind_gift') or (data.get('batch_combo_send') and data['batch_combo_send'].get('blind_gift'))
    
    if blind_data:
        # box
        print(f"+{num}")
        bg_name = blind_data.get('original_gift_name')
        bg_price = blind_data.get('original_gift_price', 0) / 1000 
        g_value = blind_data.get('gift_tip_price', 0) / 1000 
        handle_logic(bg_name, num, bg_price, g_value)
    else:
        # normal
        print("#")

@room.on('COMBO_SEND')
async def on_combo(event):
    data = event['data']['data']
    batch_id = data.get('batch_combo_id')
    if batch_id in combo_tracker:
        del combo_tracker[batch_id]

# ui design
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("云宝的盲盒统计")
        self.root.attributes("-topmost", True)
        self.root.geometry("380x260")
        self.root.configure(bg='#ffffff')

        # 字体设置
        self.main_font_name = "Microsoft Yahei UI" # 华文楷体
        self.num_font_name = "Consolas" 
        
        self.font_title = (self.main_font_name, 20, "bold")
        self.font_net_val = (self.num_font_name, 24, "bold")
        self.font_label = (self.main_font_name, 10)
        self.font_sub_val = (self.num_font_name, 14, "bold")
        self.font_connecting = (self.main_font_name, 14) # 缩小连接中的字体

        # 第一行：标题
        self.title_label = tk.Label(self.root, text="云宝的盲盒统计", font=self.font_title, bg='#ffffff', fg='#fb7299')
        self.title_label.pack(pady=(15, 5))

        # 第二行：主要数值区域（净收益）
        self.label_net = tk.Label(self.root, text="0", font=self.font_net_val, bg='#ffffff')
        self.label_net_hint = tk.Label(self.root, text="当前预计净收益 (电池)", font=self.font_label, bg='#ffffff', fg='#999999')

        # 分割线
        self.line = tk.Frame(self.root, height=1, width=320, bg='#eeeeee')

        # 第三行：三列布局
        self.stats_frame = tk.Frame(self.root, bg='#ffffff')
        self.col_count = self._create_stat_col(self.stats_frame, "盲盒总数", "#666666", 0)
        self.col_cost = self._create_stat_col(self.stats_frame, "送出电池", "#666666", 1)
        self.col_profit = self._create_stat_col(self.stats_frame, "收到电池", "#666666", 2)
        
        # 连接状态提示文字
        self.conn_label = tk.Label(self.root, text="正在建立连接...", font=self.font_connecting, bg='#ffffff', fg='#000000')
        
        self.update_ui()

    def _create_stat_col(self, parent, label_text, color, col_idx):
        frame = tk.Frame(parent, bg='#ffffff')
        frame.grid(row=0, column=col_idx, sticky='nsew')
        parent.grid_columnconfigure(col_idx, weight=1)
        val_label = tk.Label(frame, text="0", font=self.font_sub_val, bg='#ffffff', fg=color)
        val_label.pack()
        txt_label = tk.Label(frame, text=label_text, font=self.font_label, bg='#ffffff', fg='#999999')
        txt_label.pack()
        return val_label

    def update_ui(self):
        global IS_CONNECTED
        if IS_CONNECTED:
            # 隐藏连接提示
            self.conn_label.pack_forget()
            
            # 显示正常 UI
            self.title_label.config(fg='#fb7299') 
            self.label_net.pack()
            self.label_net_hint.pack(pady=(0, 10))
            self.line.pack()
            self.stats_frame.pack(fill='x', pady=15)
            
            # 更新数据
            cost_val = total_cost * 10
            profit_val = total_profit * 10
            net_val = profit_val - cost_val
            
            net_color = "#4caf50" if net_val > 0.1 else ("#f44336" if net_val < -0.1 else "#333333")
            self.label_net.config(text=f"{net_val:.0f}", fg=net_color)
            self.col_count.config(text=f"{total_box_count}")
            self.col_cost.config(text=f"{cost_val:.0f}")
            self.col_profit.config(text=f"{profit_val:.0f}")
        else:
            # 隐藏所有统计 UI
            self.label_net.pack_forget()
            self.label_net_hint.pack_forget()
            self.line.pack_forget()
            self.stats_frame.pack_forget()
            
            # 只显示标题和缩小的连接提示
            self.title_label.config(fg='#ff0000')
            self.conn_label.pack(pady=40) # 增加边距使其居中感更强

        self.root.after(1000, self.update_ui)

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