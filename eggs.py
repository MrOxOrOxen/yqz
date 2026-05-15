from ids import *
import time
from memory_store import MEMORY, reply_queue, gachi_last_time
from logger import add_log
from datetime import datetime
from json_handle import save_json
import json

# 彩蛋设置
async def check_gachi_egg(uid, guard_name, battery):
    now = time.time()
    if uid in GACHI_ID and battery >= 52:
        if uid not in gachi_last_time or (now - gachi_last_time[uid] > 600):
            gachi_last_time[uid] = now
            await reply_queue.put((uid, "[礼物姬]唉gachi"))
            add_log(f"[礼物姬] check_gachi_egg")

async def box_egg(uid, uname, gift_name, num, cost, profit):
    async def huli_box(uid, num):
        if uid == HULI_ID:
            if str(uid) in MEMORY["box"]:
                current_count = MEMORY["box"][str(uid)]["count"]
                old_count = current_count - num
                for i in range(int(old_count) + 1, int(current_count) + 1):
                    if i % 50 == 10:
                        await reply_queue.put((uid, "[盲盒姬]狐狸老师你又在抽盲盒喔，休息一下好不好"))
                        add_log("[盲盒姬] huli_box")
                        break

    async def yqz_box(uid, num):
        if uid == XIAOZAO_ID:
            if str(uid) in MEMORY["box"]:
                current_count = MEMORY["box"][str(uid)]["count"]
                old_count = current_count - num
                for i in range(int(old_count) + 1, int(current_count) + 1):
                    if i % 50 == 1:
                        await reply_queue.put((uid, "[盲盒姬]云宝你也在抽盲盒喔，别抽了好不好"))
                        add_log("[盲盒姬] yqz_box")
                        break
    
    await huli_box(uid, num)
    await yqz_box(uid, num)

async def check_global_loss_warning(uid):
    if MEMORY["meta"].get("is_loss_warning_sent", False):
        return

    if MEMORY["meta"].get("is_whole_profit_msg_sent", False):
        return

    total_net = sum(u["profit"] - u["cost"] for u in MEMORY["box"].values())
    
    if total_net <= -15000:
        warning_msg = f"[盲盒姬]天台拥挤不要插队，觉得风大的老板走后面楼梯下楼谢谢"
        await reply_queue.put((uid, warning_msg))
        
        MEMORY["meta"]["is_loss_warning_sent"] = True
        save_json("files/meta.json", MEMORY["meta"])
        add_log(f"[盲盒姬] total_net < -15000")

    if total_net >= 15000:
        msg = f"[盲盒姬]ohhhhhhhhhh转运了转运了！云崎早的直播间竟然欧起来了!！"
        await reply_queue.put((uid, msg))
        MEMORY["meta"]["is_whole_profit_msg_sent"] = True
        save_json("files/meta.json", MEMORY["meta"])
        add_log(f"[盲盒姬] total_net > 15000")


async def danmu_egg():
    async def birthday():
        if datetime.now().strftime("%m%d") != "0503":
            return False

        if MEMORY["meta"]["is_birthday_msg_sent"] == True:
            return False

        try:
            total_count = MEMORY["meta"].get("total_danmu_cnt_from_start", 0) + len(MEMORY["danmu"])
            if total_count >= 100:
                MEMORY["meta"]["is_birthday_msg_sent"] = True
                save_json("files/meta.json", MEMORY["meta"])
                birthday_msg = "[卡米宝宝]今天是全世界最最最可爱的云崎早的生日，让我们祝云宝生日快乐！"
                await reply_queue.put((YQZ_ID, birthday_msg))
                add_log("[卡米宝宝] birthday")
        except Exception as e:
            print(f"统计弹幕失败: {e}")
            return False


    async def kfc():
        if datetime.now().weekday() != 3:
            return False

        if datetime.now().hour < 12:
            return False

        if MEMORY["meta"]["is_kfc_msg_sent"] == True:
            return False

        try:
            total_count = MEMORY["meta"].get("total_danmu_cnt_from_start", 0) + len(MEMORY["danmu"])

            if total_count >= 100:
                MEMORY["meta"]["is_kfc_msg_sent"] = True
                save_json("files/meta.json", MEMORY["meta"])
                kfc_msg = "[礼物姬]今天是星期四，不想被做成烤鸭的早崎鸭请自觉上交50元谢谢"
                await reply_queue.put((YQZ_ID, kfc_msg))
                add_log(f"[礼物姬] kfc")
        except Exception as e:
            print(f"统计弹幕失败: {e}")
            return False

    async def castle():
        if datetime.now().weekday() != 4:
            return False

        if datetime.now().hour < 12:
            return False

        if MEMORY["meta"]["is_castle_msg_sent"] == True:
            return False

        try:
            total_count = MEMORY["meta"].get("total_danmu_cnt_from_start", 0) + len(MEMORY["danmu"])
            if total_count >= 100:
                MEMORY["meta"]["is_castle_msg_sent"] = True
                save_json("files/meta.json", MEMORY["meta"])
                castle_msg = "[盲盒姬]听说今天城堡概率翻倍"
                await reply_queue.put((YQZ_ID, castle_msg))
                add_log(f"[盲盒姬] castle")

        except Exception as e:
            print(f"统计弹幕失败: {e}")
            return False

    await birthday()
    await kfc()
    await castle()
    # await gachi_combo()
    # await question_mark_combo()
    # await circle_combo()
    # await good_night_combo()
    # await haha_combo()

'''
    # combo functions
    async def gachi_combo():
        global last_gachi_danmu_trigger
        recent_msgs = [item["danmu"] for item in MEMORY["danmu"][-10:] if time.time() - item.get("time", 0) < 60]
        keywords = ["唉gachi", "哎gachi", "唉，gachi", "哎，gachi", "唉,gachi", "哎,gachi", "唉, gachi", "哎, gachi"]
        gachi_count = sum(1 for m in recent_msgs if any(k in m for k in keywords))
        if gachi_count >= 3:
            if time.time() - last_gachi_danmu_trigger >= 300:
                gachi_msg = "[观测姬(跟读弹幕)]唉gachi"
                await reply_queue.put((None, gachi_msg))
                last_gachi_danmu_trigger = time.time()
                add_log("[观测姬] gachi_combo")

    async def question_mark_combo():
        global last_question_mark_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 60 and item["uid"] != ADMIN_ID
        ]

        keywords1 = ["?", "？"]
        keywords2 = "？？？"
        question_mark_count = sum(
            1 for m in recent_msgs
            if m in keywords1 or keywords2 in m
        )

        if question_mark_count > 3:
            if time.time() - last_question_mark_trigger > 300:
                question_mark_msg = "[观测姬(跟读弹幕)]？"
                await reply_queue.put((None, question_mark_msg))
                last_question_mark_trigger = time.time()
                add_log("[观测姬] question_mark_combo")

    async def circle_combo():
        global last_circle_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 60 and item["uid"] != ADMIN_ID
        ]

        keywords = ["⭕️", "圈"]
        circle_count = sum(1 for m in recent_msgs if any(k in m for k in keywords))

        if circle_count > 3:
            if time.time() - last_circle_trigger > 300:
                circle_msg = "[观测姬(跟读弹幕)]⭕️"
                await reply_queue.put((None, circle_msg))
                last_circle_trigger = time.time()
                add_log("[观测姬] circle_combo")

    async def good_night_combo():
        global last_good_night_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 300 and item["uid"] != ADMIN_ID
        ]

        keywords = "晚安"
        good_night_count = sum(1 for m in recent_msgs if keywords in m)

        if good_night_count > 3:
            if time.time() - last_good_night_trigger > 600:
                good_night_msg = "[观测姬(跟读弹幕)]晚安晚安"
                await reply_queue.put((None, good_night_msg))
                last_good_night_trigger = time.time()
                add_log("[观测姬] good_night")

    async def haha_combo():
        global last_haha_trigger
        recent_msgs = [
            item["danmu"]
            for item in MEMORY["danmu"][-10:]
            if time.time() - item.get("time", 0) < 300 and item["uid"] != ADMIN_ID
        ]

        keywords = "哈哈"
        haha_count = sum(1 for m in recent_msgs if keywords in m)

        if haha_count > 3:
            if time.time() - last_haha_trigger > 300:
                haha_msg = "[观测姬(跟读弹幕)]哈哈"
                await reply_queue.put((None, haha_msg))
                last_haha_trigger = time.time()
                add_log("[观测姬] haha_combo")

'''
    

async def gift_egg(uid, uname, gift_name, num, profit):
    pass

async def sc_egg(uid, uname, battery, message):
    async def shennai(uid, message):
        keywords = ["云购", "溜溜", "狗", "66", "遛狗", "√", "遛遛", "溜狗", "6狗", "6购"]
        if uid == SHENNAI_ID and any(k in message for k in keywords):
            MEMORY["meta"]["dog"] += 1
            save_json("files/meta.json", MEMORY["meta"])
            dog_msg = f"[礼物姬]每日遛狗（{MEMORY['meta']['dog']}/1）"
            await reply_queue.put((uid, dog_msg))
            add_log(f"[礼物姬] shennai")
    
    await shennai(uid, message)


async def guard_egg(uid, uname, guard_name, price):
    async def shuangshui(uid):
        if uid == SHUANGSHUI_ID:
            await reply_queue.put((uid, "[礼物姬]爽睡你的19级牌子不要了喵？"))
            add_log(f"[礼物姬] shuangshui")

    # 由于thank_guard中@的人不一样，需要单独列出
    async def thank_guard(uid, uname, guard_name):
        if guard_name == "总督":
            if uid == GACHI_ID[3]:
                reply = "[from 庄生梦方宜]云宝，生日快乐！你这么好，值得这世上所有温柔的对待！"
                await reply_queue.put((YQZ_ID, reply))
            else:
                reply1 = "[礼物姬]哇谢谢早崎鸭大人的……不对这是什么？！这不会是总督吧！！！"
                reply2 = "[礼物姬]哇呜呜呜呜呜谢谢老板的总督，这也是给我的生日礼物吗 T_T！"
                reply3 = "[礼物姬]云崎早有你真的好幸福好幸福！生日同乐！！"
                await reply_queue.put((uid, reply1))
                await reply_queue.put((uid, reply2))
                await reply_queue.put((uid, reply3))
            add_log("[礼物姬] 总督")
        elif guard_name == "提督":
            if uid == GACHI_ID[3]:
                reply = "[from 庄生梦方宜]我会一直在这里，看你发光，也等你休息。"
                await reply_queue.put((YQZ_ID, reply))
            else:
                reply1 = "[礼物姬]哇谢谢早崎鸭大人的提督！提督大人生日同乐！"
                reply2 = "[礼物姬]谢谢你愿意给云崎早分一口生日蛋糕！！"
                await reply_queue.put((uid, reply1))
                await reply_queue.put((uid, reply2))
        elif guard_name == "舰长" and uid != JUNBEN_ID:
            if uid == GACHI_ID[3]:
                reply = "[from 庄生梦方宜]新的一岁，愿你被人爱，也被人照顾。"
                await reply_queue.put((YQZ_ID, reply))
            else:
                reply = "[礼物姬]谢谢早崎鸭大人的舰长！生日同乐！不死族又可以+1了！！"
                await reply_queue.put((uid, reply))
        else:
            pass
        add_log(f"[礼物姬]感谢{uname}的{guard_name}")

    await shuangshui(uid)
    # await thank_guard(uid, uname, guard_name)