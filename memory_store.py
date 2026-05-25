import asyncio
from data import SESSDATA, BILI_JCT, BUVID3
from bilibili_api import Credential
from ids import *

MEMORY = {
    "box": {},
    "gift": {},
    "all": [],
    "danmu": [],
    "meta": {
        "total_battery": 0,
        "total_danmu_cnt_from_start": 0,
        "is_loss_warning_sent": False,
        "is_whole_profit_msg_sent": False,
        "next_threshold": 4000,
        "current_gear": 0,
        "dog": 0,
        "is_birthday_msg_sent": False,
        "is_kfc_msg_sent": False,
        "is_castle_msg_sent": False,
    },
    "audience": {
        "interact_cache": []
    }
}

processed_records = []  # 用于大航海判重
last_query_time = {}
gachi_last_time = {}
# last_global_reply = 0
last_save_time = 0
last_log_save = 0
interact_cache = set()

reply_queue = asyncio.Queue()
ROOM_ID = 27885573
# ROOM_ID = 1828180031

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT)

WELCOME_MAP = {
    GACHI_ID[0]: '[欢迎姬]报告！发现一个说着"早早天下第一可爱！"的gachi进入直播间！',
    GACHI_ID[1]: '[欢迎姬]报告！发现一个说着"早早天下第一可爱！"的gachi进入直播间！',
    GACHI_ID[2]: '[欢迎姬]报告！发现一个说着"早早天下第一可爱！"的gachi进入直播间！',
    GACHI_ID[3]: "[欢迎姬]报告！发现{uname}老师来直播间盯着云宝今天也要早早睡觉！",
    GACHI_GACHI_ID: "[欢迎姬]报告！发现{uname}老师来直播间盯着庄宝今天也要早早睡觉！",
    JIALEISI_ID: '[欢迎姬]报告！发现一个说着"唉，gachi"的早崎鸭进入直播间！',
    ZAIYI_ID: "[欢迎姬]报告！一只叫{uname}的大傻呗进入了直播间！",
    XINGCHEN_KAISER_ID: "[欢迎姬]一只叫{uname}的早崎鸭怎么学习学到直播间嘞？",
    FEIXINGTING_ID: "[欢迎姬]报告！观测到一架飞行艇飞入直播间！",
    SHUANGSHUI_ID: "[欢迎姬]报告喵！发现爽睡老师进入直播间喵！",
}

COMBO_GUARD_PRICE = {
    "舰长": 1680,
    "提督": 15980,
    "总督": 159980,
    "大航海": 1680
}

GUARD_FIRST_PRICE = {
    "舰长": {0: 1680, 1380: 1380, 300: 1980},
    "大航海": {0: 1680, 1380: 1380, 300: 1980},
    "提督": {0: 15980, 4000: 19980},
    "总督": {0: 159980, 40000: 199980},
}

CN_MONTHS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12
}

BOX_MEMORY_MAP = {
    "心动": "心动盲盒",
    "幸运": "幸运盲盒",
    "幸运S": "幸运盲盒S",
    "真爱": "真爱盲盒",
    "梦幻之夏": "梦幻之夏盲盒",
}

GIFT_BOX_MAP = {
    "幸运": 1,
    "幸运S": 2,
    "心动": 3,
    "真爱": 4,
    "梦幻之夏": 5,
}

# 幸运盲盒
BOX_LIST_1 = {
    "星愿花园": 600,
    "福灵小兽": 200,
    "梦雾纸签": 100,
    "星光铃铛": 52,
    "好运柚叶": 25,
    "幸运泡泡": 15
}

# 幸运盲盒S
BOX_LIST_2 = {
    "命契幻境": 30000,
    "幽镜之门": 5000,
    "光羽预言": 1000,
    "福引转轮": 520,
    "星币女王": 300,
    "初兆光符": 160
}

# 心动盲盒
BOX_LIST_3 = {
    "浪漫城堡": 22330,
    "神驹宝玺": 2000,
    "时空之站": 1000,
    "绮彩权杖": 400,
    "爱心抱枕": 160,
    "棉花糖": 90,
    "电影票": 20
}

# 真爱盲盒
BOX_LIST_4 = {
    "真爱降临": 12000,
    "心意列车": 5000,
    "星之恋歌": 660,
    "玫瑰序章": 260,
    "云间来信": 190,
    "心跳曲线": 50
}

# 梦幻之夏盲盒
BOX_LIST_5 = {
    "爱心气球": 50,
    "BW蛋糕": 190,
    "BW权杖": 260,
    "玫瑰花冠": 660,
    "花束殿堂": 5000,
    "加冕仪式": 12000
}