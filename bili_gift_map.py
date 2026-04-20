import requests
import json

def get_bilibili_gift_map(room_id=27885573):
    print(f"📡 正在请求 B 站官方接口获取房间 [{room_id}] 的礼物清单...")
    
    url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{room_id}"
    }
    params = {
        "room_id": room_id,
        "platform": "pc"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # 检查网络请求是否成功
        
        data = response.json()
        if data['code'] != 0:
            print(f"❌ 接口返回错误: {data['message']}")
            return

        gift_list = data['data']['list']
        gift_map = {}
        
        for gift in gift_list:
            g_id = str(gift['id'])
            gift_map[g_id] = {
                "name": gift['name'],
                "price": gift['price'] / 1000 # 1000金瓜子 = 1元
            }
        
        # 写入文件
        with open("bili_gift_map.json", "w", encoding="utf-8") as f:
            json.dump(gift_map, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 成功！已抓取 {len(gift_map)} 个礼物。")
        print(f"📂 文件已保存至: bili_gift_map.json")

    except Exception as e:
        print(f"❌ 运行报错: {e}")

if __name__ == "__main__":
    get_bilibili_gift_map()