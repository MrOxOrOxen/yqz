import asyncio
from data import SESSDATA, BILI_JCT, BUVID3
from bilibili_api import Credential

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