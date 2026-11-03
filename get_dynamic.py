
import asyncio
import json
from bilibili_api import dynamic, select_client

# 使用 aiohttp，绕过 curl_cffi 兼容性问题
select_client("aiohttp")

DYNAMIC_ID = 1257529594975617043

async def main():
    dy = dynamic.Dynamic(dynamic_id=DYNAMIC_ID)
    result = await dy.get_info()

    item = result.get("item", result)
    filename = f"dynamic_{DYNAMIC_ID}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)

    print(f"获取成功！已保存到 {filename}")


if __name__ == "__main__":
    asyncio.run(main())
