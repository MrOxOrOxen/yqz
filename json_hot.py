import json

gift_name = "全城告白"
gift_price = 5200
uid = 129803120
uname = "庄生梦方宜"
timestamp = 1779027696
uid_str = str(uid)

with open("files/gift.json", "r", encoding="utf-8") as f:
    gift_dict = json.load(f)


if uid_str in gift_dict:
    if gift_name in gift_dict[uid_str]["gift_list"]:
        gift_dict[uid_str]["gift_list"][gift_name] += 1
    else:
        gift_dict[uid_str]["gift_list"][gift_name] = 1
    gift_dict[uid_str]["profit"] += gift_price
else:
    gift_dict[uid_str] = {
        "uid": uid,
        "uname": uname,
        "gift_list": {
            gift_name: 1
        },
        "profit": gift_price
    }

with open("files/gift.json", "w", encoding="utf-8") as f:
    json.dump(gift_dict, f, ensure_ascii=False, indent=2)

with open("files/all.json", "r", encoding="utf-8") as f:
    all_list = json.load(f)

all_list.append(
    {
        "uid": uid,
        "uname": uname,
        "time": timestamp,
        "gift_name": gift_name,
        "gift_price": gift_price
    }
)

with open("files/all.json", "w", encoding="utf-8") as f:
    json.dump(all_list, f, ensure_ascii=False, indent=2)

print("Done.") 