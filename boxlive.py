import asyncio
import aiohttp
import http.cookies
import blivedm
import blivedm.models.web as web_models

# --- 配置区域 ---
temp_room_id = int(input("直播间号："))
SESSDATA = '5ac9aa87%2C1792152691%2C75543%2A41CjBwHGBGtDEKlrUs5MUqxrgvvYJOjyEhylO6EOOvUsJy_usU84eL81E4fDNEPbxQIewSVmktSTJDMGNmVjlaamRtVExDeXA4aUpOWUotY2s0NzNXMG0xeWxSM2ZFOUFkOGluaFB3eDVoYXRJa2lGdzZmbGEzN1d5aGppU2lyaVpRT3Rob21mLWJBIIEC'
BILI_JCT = '6fd4fd7a74df714b7712181ccbd0119a'  # 在浏览器Cookie中找
ROOM_ID = temp_room_id     # 你的直播间ID

# 用于存储所有用户的统计数据 {uid: {"uname": "", "count": 0, "cost": 0, "profit": 0}}
user_stats = {}

class MyHandler(blivedm.BaseHandler):
    def __init__(self, session):
        super().__init__()
        self.session = session

    async def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        global user_stats
        
        # 匹配盲盒礼物
        if "盲盒" in message.gift_name:
            uid = message.uid
            if uid not in user_stats:
                user_stats[uid] = {"uname": message.uname, "count": 0, "cost": 0, "profit": 0}
            
            num = message.num
            # 1. 统计成本：price通常是金瓜子，/100 换算为常用单位（根据你之前 collector11 乘以10的逻辑调整）
            cost = (message.price / 100) * num
            
            # 2. 统计收益：尝试从原始数据抓取盲盒中出的“电池”价值
            # blivedm会将原始数据存在 message.raw_data 中
            gift_tip_price = 0
            try:
                # 某些版本或特定盲盒，中奖金额在 raw_data 的 data 字段里
                gift_tip_price = message.raw_data.get('data', {}).get('gift_tip_price', 0) / 100
            except:
                pass

            user_stats[uid]["count"] += num
            user_stats[uid]["cost"] += cost
            user_stats[uid]["profit"] += gift_tip_price * num # 累加中奖价值

            print(f"统计更新：{message.uname} 开盒x{num}，消耗:{cost}，中奖:{gift_tip_price * num}")

    async def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        # 增加判断，防止机器人自言自语（如果SESSDATA是你自己的号）
        if message.msg == "查盲盒":
            uid = message.uid
            if uid in user_stats:
                data = user_stats[uid]
                net = data["profit"] - data["cost"]
                # 格式化回复，保留0位小数更直观
                reply = (f"@{message.uname} 您已开{data['count']}盒，"
                         f"消耗{data['cost']:.0f}电池，"
                         f"当前净收益:{net:.0f}电池")
            else:
                reply = f"@{message.uname} 您目前没有统计记录哦"
            
            await self.send_reply(client.room_id, reply)

    async def send_reply(self, room_id, content):
        url = "https://api.live.bilibili.com/msg/send"
        # 随机rnd防止被判重复消息
        import random
        data = {
            "msg": content,
            "roomid": room_id,
            "csrf": BILI_JCT,
            "csrf_token": BILI_JCT,
            "rnd": str(random.randint(100000, 999999))
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://live.bilibili.com/{room_id}"
        }
        try:
            async with self.session.post(url, data=data, headers=headers) as resp:
                res = await resp.json()
                if res['code'] == 0:
                    print(f"成功回复：{content}")
                else:
                    print(f"回复失败：{res['message']}")
        except Exception as e:
            print(f"网络异常：{e}")

# 在 main 函数里创建 session 时建议加上：
# async with aiohttp.ClientSession(headers={'Accept-Encoding': 'gzip, deflate'}) as session:

async def main():
    cookies = http.cookies.SimpleCookie()
    cookies['SESSDATA'] = SESSDATA
    cookies['bili_jct'] = BILI_JCT

    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
        session.cookie_jar.update_cookies(cookies)
        client = blivedm.BLiveClient(ROOM_ID, session=session)
        client.set_handler(MyHandler(session))
        client.start()
        try:
            await client.join()
        finally:
            await client.stop_and_close()

if __name__ == '__main__':
    asyncio.run(main())