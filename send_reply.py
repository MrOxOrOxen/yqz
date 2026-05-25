import asyncio
import random
import time
import aiohttp
from logger import add_log

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