import asyncio
import json
import struct
import zlib
import requests
import websockets

# --- 配置区 ---
ROOM_ID = 6  # 你想监控的房间号
SESSDATA = "cabb4f9b%2C1791892970%2C8a472%2A41CjDk9l5-uv3TSLgWA2UEDvekCslhKd40PgQkhYgCbWPwHfFW0sSgiC97gF6sGEkJHbwSVnlFYXYxNjFuUk15ME9wc21ubG9JajJTV2pJYUxlbS0ybGNzcGRnR2twckR6MFA3Y2dQTmxobXEySm0xVVVNREs5SThabzRrb1lTLWdLMy1aTHY4MkNRIIEC"  # 从浏览器获取
BUVID3 = "FFB28B70-6E24-FC68-66A9-0609A0E3D06D41129infoc"
BILI_JCT = "728ae1e4d1de19de81c338ce60159368"

# --------------

class BiliLiveStatistics:
    def __init__(self):
        self.total_blind_boxes = 0
        self.box_details = {}

    def get_real_id_and_token(self, room_id):
        # 这是一个不需要复杂校验的旧版接口
        manual_token = "MQEJanVlWo8yysg_rgJvD_dSg5tYOwnbxV6Mh0Qn5NZyNB0B6dWNqc4v7e9VsGZxp7Pycj8hx9x3liYUOcYgz84N0CvyWNyY-hnqxgn6fUy1Wm0013uIHDsIKR6uiMeuZ6PlVyaiQougYcRVUjjhAyo0ymvQMp_l2JKI4wivCdvOEntPp-eJ9gjGX5p4IfdlJi1jOXOjSWAVxUwCLCkiJD4CCQv8vHpN1uFZwi7h8D6vkAgp0terpI0Je6dGETtU1oKLiw=="
        '''
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            # 1. 还是先拿真实 ID
            res = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}", headers=headers).json()
            real_id = res['data']['room_id']
            
            # 2. 直接返回固定的 host，Token 传空字符串
            # 旧版协议允许在认证包中使用空 key 或者简单的验证逻辑
            print(f"✅ 使用兼容模式连接房间: {real_id}")
            return real_id, manual_token, "broadcastlv.chat.bilibili.com"
            '''
        real_id = room_id
        host = "broadcastlv.chat.bilibili.com"
        
        try:
            print(f"🚀 已注入手动凭证，正在连接...")
            return real_id, manual_token, host
            
        except Exception as e:
            print(f"初始化失败: {e}")
            return None
            
        except Exception as e:
            print(f"连接初始化失败: {e}")
            return None

    def make_packet(self, data, operation):
        # 构建B站协议包头 (16字节)
        body = json.dumps(data).encode('utf-8')
        header = struct.pack('>IHHII', len(body) + 16, 16, 1, operation, 1)
        return header + body

    async def connect(self):
        real_id, token, host = self.get_real_id_and_token(ROOM_ID)
        url = f"wss://{host}/sub"

        async with websockets.connect(url) as ws:
            # 1. 发送认证包 (Operation 7)
            auth_data = {
                "uid": 1224551233,
                "roomid": real_id,
                "protover": 3,
                "platform": "web",
                "type": 2,
                "key": token
            }
            await ws.send(self.make_packet(auth_data, 7))
            print(f"成功连接直播间: {real_id}，正在监控盲盒...")

            # 2. 启动心跳任务 (Operation 2)
            async def heartbeat():
                while True:
                    await asyncio.sleep(30)
                    await ws.send(struct.pack('>IHHII', 16, 16, 1, 2, 1))
            
            asyncio.create_task(heartbeat())

            # 3. 循环接收数据
            while True:
                recv_data = await ws.recv()
                self.parse_packet(recv_data)

    def parse_packet(self, data):
        offset = 0
        while offset < len(data):
            header = struct.unpack('>IHHII', data[offset:offset+16])
            packet_len = header[0]
            version = header[2]
            operation = header[3]
            body = data[offset+16 : offset+packet_len]
            offset += packet_len

            if operation == 5: # 服务器推送的消息
                if version == 2: # zlib 压缩
                    body = zlib.decompress(body)
                    self.parse_packet(body) # 递归处理解压后的数据
                else:
                    try:
                        msg = json.loads(body.decode('utf-8'))
                        self.handle_command(msg)
                    except:
                        pass

    def handle_command(self, msg):
        cmd = msg.get("cmd")
        if cmd == "SEND_GIFT":
            data = msg.get("data", {})
            gift_name = data.get("giftName", "")
            num = data.get("num", 0)
            uname = data.get("uname", "")

            if "盲盒" in gift_name:
                self.total_blind_boxes += num
                self.box_details[gift_name] = self.box_details.get(gift_name, 0) + num
                print(f"--- 盲盒统计更新 ---")
                print(f"用户 {uname} 送出 {num} 个 [{gift_name}]")
                print(f"累计盲盒总数: {self.total_blind_boxes}")
                for name, count in self.box_details.items():
                    print(f"  - {name}: {count}个")

if __name__ == "__main__":
    stats = BiliLiveStatistics()
    try:
        asyncio.run(stats.connect())
    except KeyboardInterrupt:
        print("\n监控结束。")