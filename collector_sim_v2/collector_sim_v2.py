import tkinter as tk
from tkinter import ttk, scrolledtext
import random

def draw():
    result_text.config(state=tk.NORMAL)
    result_text.delete(1.0, tk.END)
    
    try:
        times = int(times_entry.get())
        if times <= 0:
            result_text.insert(tk.END, "抽取次数必须大于0！\n")
            return
    except:
        result_text.insert(tk.END, "请输入有效的数字！\n")
        return

    items_info = {
        "浪漫城堡": 22330,
        "神驹宝玺": 2000,
        "时空之站": 1000,
        "绮彩权杖": 400,
        "爱心抱枕": 160,
        "棉花糖": 90
    }
    items = list(items_info.keys())
    
    total_cost = 0
    total_profit = 0
    item_count = {item: 0 for item in items}

    result_text.insert(tk.END, f"===== 模拟{times}次抽取 =====\n\n")

    for i in range(times):
        total_cost += 150
        
        candidate = random.choices(items, weights=[0.0001, 0.001, 0.01, 0.1, 5, 94], k=1)[0]
        
        if (total_profit + items_info[candidate]) > (total_cost * 0.8):
            selected = "棉花糖"
        else:
            selected = candidate
            
        if items_info[selected] >= 1000 and random.random() > 0.001:
            selected = "棉花糖"

        battery = items_info[selected]
        total_profit += battery
        item_count[selected] += 1
        
        if times <= 100:
            result_text.insert(tk.END, f"第{i+1}抽：抽到【{selected}】({battery}电池)\n")

    profit = total_profit - total_cost
    result_text.insert(tk.END, "\n" + "="*50 + "\n")
    result_text.insert(tk.END, f"【抽取报告】\n")
    for item in items:
        if item_count[item] > 0:
            result_text.insert(tk.END, f"  {item: <6} × {item_count[item]}个\n")
    
    result_text.insert(tk.END, f"\n总投入：{total_cost} 电池")
    result_text.insert(tk.END, f"\n总产出：{total_profit} 电池")
    result_text.insert(tk.END, f"\n净收益：{profit} 电池\n")
    
    result_text.config(state=tk.DISABLED)
    result_text.see(tk.END)

root = tk.Tk()
root.title("心动盲盒模拟器")
root.geometry("650x700")

tk.Label(root, text="心动盲盒模拟器", font=("微软雅黑", 14, "bold"), fg="red").pack(pady=10)

tip_label = tk.Label(root, text="说明：用户一定不会在这个模拟器里回本。", font=("微软雅黑", 9), fg="gray")
tip_label.pack()

input_frame = tk.Frame(root)
input_frame.pack(pady=15)
tk.Label(input_frame, text="输入抽取次数：", font=("微软雅黑", 12)).grid(row=0, column=0)
times_entry = ttk.Entry(input_frame, font=("微软雅黑", 12), width=10)
times_entry.insert(0, "100")
times_entry.grid(row=0, column=1, padx=5)

style = ttk.Style()
style.configure("TButton", font=("微软雅黑", 12))
start_btn = ttk.Button(root, text="抽取", command=draw)
start_btn.pack(pady=5)

result_text = scrolledtext.ScrolledText(root, width=75, height=30, font=("Consolas", 10))
result_text.pack(padx=15, pady=10)
result_text.config(state=tk.DISABLED, bg="#f0f0f0")

root.mainloop()