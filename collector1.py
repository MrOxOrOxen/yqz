import asyncio
import json
import struct
import websockets
import zlib
import brotli  # 你之前已经 pip install brotli 成功了

# ================= 配置区 =================
ROOM_ID = 27885573 
MANUAL_TOKEN = r"MQEJanVlWo8yysg_rgJvD_dSg5tYOwnbxV6Mh0Qn5NZyNB0B6dWNqc4v7e9VsGZxp7Pycj8hx9x3liYUOcYgz84N0CvyWNyY-hnqxgn6fUy1Wm0013uIHDsIKR6uiMeuZ6PlVyaiQougYcRVUjjhAyo0ymvQMp_l2JKI4wivCdvOEntPp-eJ9gjGX5p4IfdlJi1jOXOjSWAVxUwCLCkiJD4CCQv8vHpN1uFZwi7h8D6vkAgp0terpI0Je6dGETtU1oKLiw=="
MANUAL_UID = 1224551233 # 填你的UID或0
# ==========================================

class BiliLiveCollector:
    def __init__(self, room_id, token):
        self.room_id = room_id
        self.token = token
        self.total_blindbox = 0

    def make_packet(self, data, operation):
        body = json.dumps(data).encode('utf-8')
        header = struct.pack('>IHHII', len(body) + 16, 16, 1, operation, 1)
        return header + body

    async def connect(self):
        url = "wss://broadcastlv.chat.bilibili.com/sub"
        async with websockets.connect(url) as ws:
            # 1. 发送认证包 (protover 3 表示使用 brotli)
            auth_data = {
                "uid": MANUAL_UID,
                "roomid": self.room_id,
                "protover": 3,
                "platform": "web",
                "type": 2,
                "key": self.token
            }
            await ws.send(self.make_packet(auth_data, 7))
            
            # 2. 维持心跳任务
            async def heartbeat():
                while True:
                    await asyncio.sleep(30)
                    # 标准心跳包：16字节头部，Op 2
                    await ws.send(struct.pack('>IHHII', 16, 16, 1, 2, 1))
            asyncio.create_task(heartbeat())

            print(f"🚀 监控中... 只要看到礼物信息就说明稳住了！")

            print(f"🚀 尝试连接中...")
            while True:
                try:
                    data = await ws.recv()
                    self.parse_packet(data)
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"❌ 连接已断开，原因: {e}")
                    break # 必须退出循环，否则会无限打印报错
                except Exception as e:
                    print(f"⚠️ 解析逻辑出错: {e}")

    def parse_packet(self, data):
        offset = 0
        while offset < len(data):
            # 解析 B 站私有协议头
            header = struct.unpack('>IHHII', data[offset:offset+16])
            packet_len, head_len, protover, operation, _ = header
            body = data[offset+16 : offset+packet_len]
            offset += packet_len

            if operation == 5: # 业务数据
                if protover == 3: # Brotli 压缩
                    self.parse_packet(brotli.decompress(body))
                elif protover == 2: # Zlib 压缩
                    self.parse_packet(zlib.decompress(body))
                else: # 普通 JSON
                    try:
                        msg = json.loads(body.decode('utf-8'))
                        self.handle_msg(msg)
                    except: pass
            elif operation == 8:
                print("✅ 认证成功！")

    def handle_msg(self, msg):
        cmd = msg.get("cmd")
        if cmd == "SEND_GIFT":
            data = msg['data']
            uname, gift = data['uname'], data['giftName']
            print(f"🎁 {uname} 送出了 {gift}")
            if "盲盒" in gift:
                self.total_blindbox += 1
                print(f"🔥 累计盲盒: {self.total_blindbox}")

if __name__ == "__main__":
    collector = BiliLiveCollector(ROOM_ID, MANUAL_TOKEN)
    asyncio.run(collector.connect())