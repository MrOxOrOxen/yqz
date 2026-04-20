import tkinter as tk
from tkinter import ttk, scrolledtext
import random

def draw():
    result_text.config(state=tk.NORMAL)
    result_text.delete(1.0, tk.END)
    
    try:
        prob_type = prob_var.get()
        times = int(times_entry.get())
        if times <= 0:
            result_text.insert(tk.END, "抽取次数必须大于0！\n")
            return
    except:
        result_text.insert(tk.END, "请输入有效的数字！\n")
        return

    items = ["浪漫城堡", "神驹宝玺", "时空之站", "绮彩权杖", "爱心抱枕", "棉花糖"]
    
    if prob_type == 1:
        weights = [0.04, 0.08, 0.12, 3.7, 45.56, 44.5]
    elif prob_type == 3:
        weights = [0.12, 0.04, 0.06, 1.46, 48.87, 43.7]
    elif prob_type == 4:
        weights = [0.16, 0.01, 0.02, 0.03, 48.03, 45.36]
    elif prob_type == 5:
        weights = [0.2, 0.001, 0.001, 0.001, 45.65, 43.96]
    else:
        result_text.insert(tk.END, "请选择正确的概率类型！\n")
        return

    total_cost = times * 150
    total_profit = 0
    item_count = {item:0 for item in items}

    result_text.insert(tk.END, f"===== 开始【{times}次】抽奖 =====\n\n")
    for i in range(times):
        selected = random.choices(items, weights=weights, k=1)[0]
        item_count[selected] += 1

        if selected == "浪漫城堡":
            battery = 22330
        elif selected == "神驹宝玺":
            battery = 2000
        elif selected == "时空之站":
            battery = 1000
        elif selected == "绮彩权杖":
            battery = 400
        elif selected == "爱心抱枕":
            battery = 160
        else:
            battery = 90

        total_profit += battery
        result_text.insert(tk.END, f"第{i+1}抽：抽到【{selected}】({battery}电池)\n")

    profit = total_profit - total_cost
    result_text.insert(tk.END, "\n" + "="*50 + "\n")
    result_text.insert(tk.END, f"抽奖统计：\n")
    for item, cnt in item_count.items():
        result_text.insert(tk.END, f"  {item} × {cnt}个\n")
    
    result_text.insert(tk.END, f"\n总花费：{total_cost} 电池")
    result_text.insert(tk.END, f"\n总获得：{total_profit} 电池")
    result_text.insert(tk.END, f"\n最终收益：{profit} 电池\n")

    result_text.config(state=tk.DISABLED)

# ui
root = tk.Tk()
root.title("心动盲盒模拟器")
root.geometry("650x600")

# prob
tk.Label(root, text="选择概率类型：", font=("微软雅黑", 12)).pack(pady=5)
prob_var = tk.IntVar()
prob_frame = ttk.Frame(root)
prob_frame.pack()

ttk.Radiobutton(prob_frame, text="1倍概率", variable=prob_var, value=1).grid(row=0, column=0, padx=10)
ttk.Radiobutton(prob_frame, text="3倍概率", variable=prob_var, value=3).grid(row=0, column=1, padx=10)
ttk.Radiobutton(prob_frame, text="4倍概率", variable=prob_var, value=4).grid(row=0, column=2, padx=10)
ttk.Radiobutton(prob_frame, text="5倍概率", variable=prob_var, value=5).grid(row=0, column=3, padx=10)

tk.Label(root, text="输入抽取次数：", font=("微软雅黑", 12)).pack(pady=5)
times_entry = ttk.Entry(root, font=("微软雅黑", 12), width=15)
times_entry.pack()

start_btn = ttk.Button(root, text="开始抽奖", command=draw)
start_btn.pack(pady=10)

tk.Label(root, text="抽奖结果：", font=("微软雅黑", 12)).pack()
result_text = scrolledtext.ScrolledText(root, width=70, height=25, font=("微软雅黑", 10))
result_text.pack(padx=10, pady=5)
result_text.config(state=tk.DISABLED)

root.mainloop()