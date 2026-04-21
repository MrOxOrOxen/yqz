from bilibili_api import live, sync, Credential
import asyncio

# --- 请务必正确填写这两个值 ---
SESSDATA = '5ac9aa87%2C1792152691%2C75543%2A41CjBwHGBGtDEKlrUs5MUqxrgvvYJOjyEhylO6EOOvUsJy_usU84eL81E4fDNEPbxQIewSVmktSTJDMGNmVjlaamRtVExDeXA4aUpOWUotY2s0NzNXMG0xeWxSM2ZFOUFkOGluaFB3eDVoYXRJa2lGdzZmbGEzN1d5aGppU2lyaVpRT3Rob21mLWJBIIEC'
BILI_JCT = '6fd4fd7a74df714b7712181ccbd0119a'

# 初始化凭据
credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

ROOM_ID = int(input("请输入直播间号进行【登录态】测试："))
room = live.LiveDanmaku(ROOM_ID, credential=credential)

@room.on('DANMU_MSG')
async def on_danmaku(event):
    info = event['data']['info']
    
    # 这里的索引是 B 站最原始的结构
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
    # 验证 Cookie 是否有效
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