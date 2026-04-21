from bilibili_api import live, sync, Credential
import asyncio

SESSDATA = ''
BILI_JCT = ''

# 初始化凭据
credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

ROOM_ID = int(input("请输入直播间号进行【登录态】测试："))
room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    info = event['data']['info']
    
    raw_uid = info[2][0]
    raw_uname = info[2][1]
    msg = info[1]
    
    print(f"\n--- 收到弹幕 ---")
    print(f"内容: {msg}")
    print(f"用户: {raw_uname}")
    print(f"UID : {raw_uid}")
    
    if raw_uid == 0:
        print("状态: 【失败】依然是匿名状态，Cookie 未生效或已过期")
    else:
        print("状态: 【成功】已抓取到真实 UID！")

async def main():
    is_login = await credential.check_valid()
    if is_login:
        print(f"验证结果: Cookie 有效，正在连接直播间...")
    else:
        print(f"验证结果: Cookie 无效！请检查 SESSDATA 是否正确或是否已过期。")
    
    await room.connect()

if __name__ == "__main__":
    try:
        sync(main())
    except KeyboardInterrupt:
        print("\n停止监听")