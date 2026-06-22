import asyncio
import random
import time
import aiohttp
from logger import add_log
import requests
import subprocess, sys

from memory_store import *
from data import SESSDATA, BILI_JCT, BUVID3

async def reply_worker():
    add_log("Reply queue start")
    while True:
        uid, content = await reply_queue.get()
        
        try:
            await send_reply(ROOM_ID, content, reply_uid=uid)
            random_time = round(random.uniform(2.5, 3.5), 1)
            await asyncio.sleep(random_time) 
        except Exception as e:
            add_log(f"[ERROR] Reply queue error: {e}")
        finally:
            reply_queue.task_done()

async def send_reply(room_id, content, reply_uid=None):
    url = "https://api.live.bilibili.com/msg/send"

    payload = {
        "bubble": "0",
        "msg": content,
        "color": "16777215",
        "mode": "1",
        "fontsize": "25",
        "rnd": int(time.time()),
        "roomid": room_id,
        "csrf": BILI_JCT,
        "csrf_token": BILI_JCT
    }

    if reply_uid:
        payload["reply_mid"] = reply_uid

    headers = {
        "Cookie": f"SESSDATA={SESSDATA}; bili_jct={BILI_JCT}; buvid3={BUVID3}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as resp:
                res = await resp.json()
                if res.get("code") != 0:
                    add_log(f"[ERROR] Failed to send danmu because: {res.get('message')} (Code: {res.get('code')})")
                else:
                    pass
    except Exception as e:
        add_log(f"[ERROR] Network layer error: {e}")

async def name_to_uid(name, sessdata, bili_jct, buvid3):
    url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/name-to-uid"
    params = {"names": name}
    
    cookies = {
        "SESSDATA": sessdata,
        "bili_jct": bili_jct,
        "buvid3": buvid3,
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://t.bilibili.com/",
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, cookies=cookies, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                
                if data.get("code") == 0:
                    uid_list = data.get("data", {}).get("uid_list", [])
                    if uid_list:
                        return int(uid_list[0].get("uid"))
    except Exception as e:
        add_log(f"[ERROR] name_to_uid failed: {e}")
    
    return None