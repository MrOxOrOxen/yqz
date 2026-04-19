import asyncio
import aiohttp
import json
import struct
import brotli

# ================= 配置区 =================
ROOM_ID = 6
# 1. 填入你之前在浏览器 F12 里看到的 token
MANUAL_TOKEN = r"SNIm7KubRg3_ENzMJ1exXrFmzblu2qOMRP3y_shrvS3mPQ6n0fBTrJqEdxbiPmhDby01FG1OzAf5JH2HKwGZJCl2FdKpoTWEh9w_Fj5UrQzKzvJKaXjRxxq-dJlpL-8Mgs8Vvnv6qfSwTTImBN7Blj1g7ABrUpS8_qQ-4DiGgL4kCI6lXiGhhtaFkidWdS59heRu1GctoXTjHjUxfRk7hjvutxROstq7r3ipKSDxqoVWUOSth1_RpLrzvdiUcaCIQIL2Xg=="
        
# 2. 这里的地址通常是固定的
MANUAL_HOST = "broadcastlv.chat.bilibili.com"
# ==========================================

class BiliLiveSimple:
    def __init__(self, room_id, token, host):
        self.room_id = room_id
        self.token = token
        self.host = host
        self.total_blindbox = 0

    def make_packet(self, data, op):
        body = json.dumps(data).encode('utf-8')
        header = struct.pack('>IHHII', len(body) + 16, 16, 1, op, 1)
        return header + body

    async def run(self):
        async with aiohttp.ClientSession() as session:
            url = f'wss://{self.host}/sub'
            print(f"📡 正在尝试连接至 {url}...")
            
            try:
                async with session.ws_connect(url) as ws:
                    # 认证包
                    auth_data = {
                        'uid': 0,
                        'roomid': self.room_id,
                        'protover': 3,
                        'platform': 'web',
                        'type': 2,
                        'key': str(self.token[0] if isinstance(self.token, tuple) else self.token).strip()
                    }
                    print(f"DEBUG 发送的完整认证包: {auth_data}")
                    await ws.send_bytes(self.make_packet(auth_data, 7))

                    # 启动心跳
                    async def heartbeat():
                        while not ws.closed:
                            await ws.send_bytes(struct.pack('>IHHII', 16, 16, 1, 2, 1))
                            await asyncio.sleep(20) # 缩短到20秒
                    
                    asyncio.create_task(heartbeat())
                    print(f"✅ 认证已发送，正在等待服务器握手回执...")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            self.parse_msg(msg.data)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("❌ WebSocket 状态变为 CLOSED")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print("❌ WebSocket 发生错误")
                            break
                    
                    print("🏁 循环结束，连接已断开。")

            except Exception as e:
                print(f"💥 无法建立连接: {e}")

    def parse_msg(self, data):
        print(f"DEBUG: 收到原始字节，长度 {len(data)}")
        offset = 0
        while offset < len(data):
            if len(data) - offset < 16: break
            packet_len, header_len, ver, op, seq = struct.unpack('>IHHII', data[offset:offset+16])
            body = data[offset+16:offset+packet_len]
            offset += packet_len

            if op == 5:
                if ver == 3:
                    try: self.parse_msg(brotli.decompress(body))
                    except: pass
                else:
                    try:
                        msg = json.loads(body.decode('utf-8'))
                        # 打印所有收到的指令，确保我们知道程序在工作
                        cmd = msg.get('cmd', '')
                        print(f"DEBUG: 收到指令 [{cmd}]")
                        
                        if cmd == 'SEND_GIFT':
                            d = msg['data']
                            print(f"🎁 {d['uname']} -> {d['giftName']}")
                            if "盲盒" in d['giftName']:
                                self.total_blindbox += 1
                                print(f"🔥 累计盲盒: {self.total_blindbox}")
                    except: pass
            elif op == 8:
                print("✨✨✨ [重点] 服务器握手成功！开始接收数据 ✨✨✨")
            elif op == 3:
                # 人气值更新，说明连接是活的
                pass

if __name__ == '__main__':
    bot = BiliLiveSimple(ROOM_ID, MANUAL_TOKEN, MANUAL_HOST)
    asyncio.run(bot.run())