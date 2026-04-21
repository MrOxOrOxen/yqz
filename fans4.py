import requests
import tkinter as tk

MID = "3493074573461871"
UPDATE_INTERVAL = 1

headers = {
    "Referer": "https://space.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/118.0.0.0 Safari/537.36"
}

def get_fans():
    try:
        url = f"https://api.bilibili.com/x/relation/stat?vmid={MID}"
        res = requests.get(url, headers=headers, timeout=3)
        data = res.json()
        if data["code"] == 0:
            return f"粉丝数：{data['data']['follower']:,}"
    except:
        pass
    return "加载中..."

root = tk.Tk()
root.title("yqz fans' number")

root.attributes("-topmost", True)
root.overrideredirect(False) 
root.attributes("-alpha", 0.85) 
root.configure(bg="#2c2c2c")

label = tk.Label(
    root,
    font=("微软雅黑", 24, "bold"),
    fg="#FB7299",
    bg="#2c2c2c",
    padx=12, 
    pady=6
)
label.pack()

def move_window(event):
    root.geometry(f"+{event.x_root}+{event.y_root}")
root.bind("<B1-Motion>", move_window)

def close_window(event):
    root.destroy()
label.bind("<Double-Button-1>", close_window)

def update_fans():
    label.config(text=get_fans())
    root.after(UPDATE_INTERVAL * 1000, update_fans)

update_fans()

root.geometry(f"+{root.winfo_screenwidth()-250}+30")
root.mainloop()