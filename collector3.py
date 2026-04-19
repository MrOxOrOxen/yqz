from bilibili_api import live, sync
import json

# 1. 设置你想监控的房间号
ROOM_ID = 2652387

# 2. 创建直播监听实例
# credential 参数如果不传，默认就是以“游客”身份进入，完全合规
room = live.LiveDanmaku(ROOM_ID)

@room.on('SEND_GIFT')
async def on_gift(event):
    print(json.dumps(data, indent=2, ensure_ascii=False))
    # 收到礼物时的处理逻辑
    data = event['data']
    user_name = data['uname']
    gift_name = data['giftName']
    gift_num = data['num']
    
    # 核心：过滤盲盒关键词
    if "盲盒" in gift_name:
        print(f"✨【关键发现】{user_name} 送出了 {gift_num} 个 {gift_name}！")
    else:
        # 如果你想看所有的礼物日志，可以取消下面这行的注释
        print(f"🎁 {user_name} 送出了 {gift_name}")
        pass

@room.on('DANMU_MSG')
async def on_danmu(event):
    # B 站弹幕的原始结构是一个多层列表
    info = event['data']['info']
    
    # 1. 获取核心内容
    content = info[1]         # 弹幕文本
    user_name = info[2][1]    # 发送者昵称
    uid = info[2][0]          # 用户 UID
    
    # 2. 检查是否为“抽奖、盲盒、奖池”相关的关键词
    keywords = ["盲盒", "抽奖", "奖池", "中奖", "开奖"]
    is_keyword = any(k in content for k in keywords)

    # 3. 格式化输出
    if is_keyword:
        print(f"🔥 [关键词捕捉] {user_name}({uid}): {content}")
    else:
        # 为了不让屏幕太乱，我们只打印前 10 个字符
        short_msg = content[:15] + "..." if len(content) > 15 else content
        print(f"💬 {user_name}: {short_msg}")

# 3. 启动监听
print(f"📡 正在监控直播间 [{ROOM_ID}] 的礼物掉落...")
sync(room.connect())