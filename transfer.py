import json
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates
import pandas as pd
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

date = input("请输入日期 (yyyy-mm-dd): ")
folder_box = "analysis/box"
folder_gift = "analysis/gift"
folder_all = "analysis/all"
os.makedirs(folder_box, exist_ok=True)
os.makedirs(folder_gift, exist_ok=True)
os.makedirs(folder_all, exist_ok=True)

# all.json
try:
    with open('files/all.json', 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    stats = {}
    for item in all_data:
        period = (item['time'] // 60) * 60 
        stats[period] = stats.get(period, 0) + item['battery']

    sorted_keys = sorted(stats.keys())
    times = [datetime.fromtimestamp(t) for t in sorted_keys]
    counts = [stats[t] for t in sorted_keys]

    plt.figure(figsize=(12, 6))
    
    # 平滑折线 + 粉色填充（核心修改处）
    plt.plot(times, counts, color='#ff85c0', linewidth=2.5, alpha=0.9)
    plt.fill_between(times, counts, color='#ff85c0', alpha=0.3)  # 折现下方粉色填充

    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 20)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    plt.title(f'{date} 云宝直播间电池统计图')
    plt.ylabel('电池数')
    plt.grid(axis='y', linestyle=':', alpha=0.6)
    plt.tight_layout()

    plt.savefig(f'{folder_all}/{date}电池统计.png', dpi=300)
except FileNotFoundError:
    print("Error: no all.json")

# gift.json
try:
    with open('files/gift.json', 'r', encoding='utf-8') as f:
        gift_data = json.load(f)

    gift_list = []
    all_gift_profit = 0
    
    for uid, info in gift_data.items():
        details = ", ".join([f"{name}*{num}" for name, num in info['gift_list'].items()])
        profit = info['profit']
        all_gift_profit += profit
        
        gift_list.append({
            "用户名": info['uname'],
            "电池总数": profit,
            "礼物详情": details
        })

    gift_df = pd.DataFrame(gift_list)
    gift_df = gift_df.sort_values(by="电池总数", ascending=False)

    gift_path = os.path.join(folder_gift, f"{date}礼物详情统计.xlsx")
    gift_df.to_excel(gift_path, index=False)

    wb_gift = load_workbook(gift_path)
    ws_gift = wb_gift.active
    
    ws_gift.insert_rows(1)
    ws_gift.merge_cells('A1:C1')
    ws_gift['A1'] = f'总收益：{round(all_gift_profit, 1)}电池'
    ws_gift['A1'].alignment = Alignment(horizontal='center', vertical='center')

    ws_gift.column_dimensions['A'].width = 25
    ws_gift.column_dimensions['B'].width = 15
    ws_gift.column_dimensions['C'].width = 70
    wb_gift.save(gift_path)
except FileNotFoundError:
    print("Error: no gift.json")

# box.json
try:
    with open('files/box.json', 'r', encoding='utf-8') as f:
        boxlive_dict = json.load(f)

    user_list = []
    total_box = 0
    total_cost = 0
    total_profit = 0

    for uid, user_info in boxlive_dict.items():
        count = user_info["count"]
        cost = user_info["cost"]
        profit = user_info["profit"]
        
        user_list.append({
            "用户名": user_info["uname"],
            "盲盒数": count,
            "总花费（电池）": round(cost),
            "总收益（电池）": round(profit),
            "净收益（电池）": round(profit)-round(cost)
        })
        
        total_box += count
        total_cost += cost
        total_profit += profit

    df_box = pd.DataFrame(user_list)
    box_path = os.path.join(folder_box, f"{date}盲盒统计.xlsx")
    df_box.to_excel(box_path, index=False)

    wb_box = load_workbook(box_path)
    ws_box = wb_box.active
    ws_box.insert_rows(1)
    ws_box.merge_cells('A1:E1')
    ws_box['A1'] = f'总盲盒数：{total_box}，共花费{round(total_cost)}电池，共开出{round(total_profit)}电池，净收益{round(total_profit)-round(total_cost)}电池'
    ws_box['A1'].alignment = Alignment(horizontal='center', vertical='center')

    ws_box.column_dimensions['A'].width = 20
    for col in ['B', 'C', 'D', 'E']:
        ws_box.column_dimensions[col].width = 15

    wb_box.save(box_path)
except FileNotFoundError:
    print("Error: no box.json")

print("Done.")