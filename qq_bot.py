import asyncio, aiohttp, json
from logger import add_log
from ids import *
from bilibili_api import live, sync, Credential, user
from memory_store import *
from constants import *
import json

class QQBot:
    def __init__(self, api_url: str, group_id: str = "", token: str = ""):
        self.api_url = api_url
        self.group_id = int(group_id) if group_id else None
        self.token = token

    async def send(self, message_segments: list, group_id: str = None):
        gid = int(group_id) if group_id else self.group_id
        if gid is None:
            add_log("[NapCat推送异常] 未指定群号，跳过发送")
            return
        try:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "group_id": gid,
                    "message": message_segments
                }
                # token 放 URL 参数里，NapCat 兼容性最好
                url = f"{self.api_url}/send_group_msg"
                if self.token:
                    url += f"?access_token={self.token}"
                
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    r = await resp.json()
                    if r.get("status") == "ok" or r.get("retcode") in [0, None]:
                        add_log(f"[NapCat推送成功] 群{gid}")
                    else:
                        add_log(f"[NapCat推送失败] 群{gid}: {r}")
        except Exception as e:
            add_log(f"[NapCat推送异常] {e}")

    async def text(self, msg: str, at_all: bool = False, group_id: str = None):
        segments = []
        if at_all:
            segments.append({"type": "at", "data": {"qq": "all"}})
        segments.append({"type": "text", "data": {"text": msg}})
        await self.send(segments, group_id=group_id)

    async def image(self, url: str, at_all: bool = False, group_id: str = None):
        segments = []
        if at_all:
            segments.append({"type": "at", "data": {"qq": "all"}})
        segments.append({"type": "image", "data": {"file": url}})
        await self.send(segments, group_id=group_id)

    async def text_with_image(self, msg: str, img_url: str, at_all: bool = False, group_id: str = None):
        segments = []
        if at_all:
            segments.append({"type": "at", "data": {"qq": "all"}})
        segments.append({"type": "text", "data": {"text": msg}})
        segments.append({"type": "image", "data": {"file": img_url}})
        await self.send(segments, group_id=group_id)

    async def send_mixed(self, segments: list, at_all: bool = False, group_id: str = None):
        """segments 是 [{"type":"text"/"image", "data":{...}}, ...] 的列表"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            final_segments = []
            if at_all:
                final_segments.append({"type": "at", "data": {"qq": "all"}})
            final_segments.extend(segments)

            gid = int(group_id) if group_id else self.group_id
            if gid is None:
                add_log("[NapCat推送异常] 未指定群号，跳过发送")
                return

            # print(f"[DEBUG] token={self.token!r}, group_id={self.group_id}, api_url={self.api_url}")
        
            url = f"{self.api_url}/send_group_msg"
            if self.token:
                url += f"?access_token={self.token}"
            # print(f"[DEBUG] URL={url}")
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "group_id": gid,
                    "message": final_segments
                }
                # print(f"[DEBUG] payload={payload}")
                
                async with session.post(
                    url, json=payload, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    r = await resp.json()
                    if r.get("status") == "ok" or r.get("retcode") in [0, None]:
                        add_log(f"[NapCat推送成功] 群{gid}")
                    else:
                        add_log(f"[NapCat推送失败] 群{gid}: {r}")
        except Exception as e:
            gid = int(group_id) if group_id else (self.group_id or "未知")
            add_log(f"[NapCat推送异常] 群{gid}: {e}")

async def dynamic_monitor(qq_bot):
    from bilibili_api import client
    u = user.User(uid=YQZ_ID, credential=credential)

    seen_ids = set()
    first_run = True
    max_id = "0"
    
    TYPE_MAP = {
        'DYNAMIC_TYPE_FORWARD': "转发动态",
        'DYNAMIC_TYPE_DRAW': "图文动态",
        'DYNAMIC_TYPE_WORD': "纯文字动态",
        'DYNAMIC_TYPE_AV': "视频",
        'DYNAMIC_TYPE_SHORT': "小视频",
        'DYNAMIC_TYPE_MUSIC': "音频",
        'DYNAMIC_TYPE_ARTICLE': "专栏",
    }

    def extract_info(item):
        """从新版 Opus 动态结构中提取通用信息"""
        dyn_id = item.get('id_str', '')
        dyn_type = item.get('type', '')
        modules = item.get('modules', {})
        module_dynamic = modules.get('module_dynamic', {})
        major = module_dynamic.get('major', {}) or {}
        basic = item.get('basic', {})
        
        # 链接处理（补全 https:）
        link = basic.get('jump_url', '')
        if link and not link.startswith('http'):
            link = 'https:' + link
        
        info = {
            'id': dyn_id,
            'type': dyn_type,
            'link': link,
            'title': '',
            'text': '',
            'images': [],
            'cover': '',
        }
        
        major_type = major.get('type', '')
        
        # Opus 类型（图文、部分纯文字）
        if major_type == 'MAJOR_TYPE_OPUS':
            opus = major.get('opus', {})
            info['title'] = opus.get('title', '')
            summary = opus.get('summary', {})
            info['text'] = summary.get('text', '')
            info['images'] = [p.get('url', '') for p in opus.get('pics', []) if p.get('url')]
            if not link:
                jump_url = opus.get('jump_url', '')
                if jump_url and not jump_url.startswith('http'):
                    jump_url = 'https:' + jump_url
                info['link'] = jump_url
                
        # 视频
        elif major_type == 'MAJOR_TYPE_ARCHIVE':
            archive = major.get('archive', {})
            info['title'] = archive.get('title', '')
            info['text'] = archive.get('desc', '')
            info['cover'] = archive.get('cover', '')
            if not link:
                jump_url = archive.get('jump_url', '')
                if jump_url and not jump_url.startswith('http'):
                    jump_url = 'https:' + jump_url
                info['link'] = jump_url
                
        # 专栏
        elif major_type == 'MAJOR_TYPE_ARTICLE':
            article = major.get('article', {})
            info['title'] = article.get('title', '')
            info['text'] = article.get('desc', '') or article.get('summary', '')
            info['cover'] = article.get('cover', '')
            if not link:
                jump_url = article.get('jump_url', '')
                if jump_url and not jump_url.startswith('http'):
                    jump_url = 'https:' + jump_url
                info['link'] = jump_url
                
        # 音频
        elif major_type == 'MAJOR_TYPE_MUSIC':
            music = major.get('music', {})
            info['title'] = music.get('title', '')
            info['text'] = music.get('intro', '') or music.get('desc', '')
            info['cover'] = music.get('cover', '')
            if not link:
                jump_url = music.get('jump_url', '')
                if jump_url and not jump_url.startswith('http'):
                    jump_url = 'https:' + jump_url
                info['link'] = jump_url
                
        # 绘图/相册（另一种图文形式）
        elif major_type == 'MAJOR_TYPE_DRAW':
            draw = major.get('draw', {})
            info['title'] = draw.get('title', '')
            info['text'] = draw.get('desc', '')
            info['images'] = [p.get('url', '') for p in draw.get('items', []) if p.get('url')]
            if not link:
                jump_url = draw.get('jump_url', '')
                if jump_url and not jump_url.startswith('http'):
                    jump_url = 'https:' + jump_url
                info['link'] = jump_url
        
        # 纯文字或无 major 的情况
        if not info['text'] and not major_type:
            desc = module_dynamic.get('desc', {})
            if desc:
                info['text'] = desc.get('text', '')
            topic = module_dynamic.get('topic', {})
            if not info['text'] and topic:
                info['text'] = topic.get('name', '') or topic.get('desc', '')
        
        # 兜底链接
        if not info['link'] and dyn_id:
            info['link'] = f"https://t.bilibili.com/{dyn_id}"
            
        return info

    def _id_greater(a, b):
        if len(a) != len(b):
            return len(a) > len(b)
        return a > b

    while True:
        try:
            dyns = await u.get_dynamics_new()
            items = dyns.get('items', [])

            # for item in items:
            #     print(item)
            #     print('\n')

            # dyns = await get_dynamics_raw(ADMIN_ID, credential)
            # items = dyns.get('items', [])

            if not items:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            # 收集当前所有ID
            current_ids = [item.get('id_str', '') for item in items if item.get('id_str')]

            if first_run:
                seen_ids = set(current_ids)
                max_id = max(current_ids, key=lambda x:(len(x), x)) if current_ids else "0"
                add_log(f"[推送姬] 动态监测启动，已记录{len(seen_ids)}条历史动态")
                first_run = False
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            new_ids = {
                cid for cid in current_ids 
                if cid not in seen_ids and _id_greater(cid, max_id)
            }

            if not new_ids:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            new_items = [item for item in items if item.get('id_str', '') in new_ids]
            new_items.reverse()

            for item in new_items:
                info = extract_info(item)
                dyn_id = info['id']
                dyn_type = info['type']
                link = info['link']
                segments = []
                header = "【推送姬】动态提醒"
   
                # ========== 转发动态 ==========
                if dyn_type == 'DYNAMIC_TYPE_FORWARD':
                    orig = item.get('orig')
                    orig_info = extract_info(orig) if orig else None
                    
                    # 转发者自己的评论
                    modules = item.get('modules', {})
                    module_dynamic = modules.get('module_dynamic', {})
                    forward_text = ''
                    desc = module_dynamic.get('desc', {})
                    if desc:
                        forward_text = desc.get('text', '')
                    topic = module_dynamic.get('topic', {})
                    if not forward_text and topic:
                        forward_text = topic.get('name', '') or topic.get('desc', '')

                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]转发了动态！\n"}})

                    if forward_text.strip():
                        segments.append({"type": "text", "data": {"text": f"{forward_text}\n\n"}})

                    # 原动态信息
                    if orig_info:
                        display_imgs = orig_info['images'] if orig_info['images'] else []
                        if orig_info['cover'] and not display_imgs:
                            display_imgs = [orig_info['cover']]
                        
                        if display_imgs:
                            for img in display_imgs[:1]:
                                if img:
                                    segments.append({"type": "image", "data": {"file": img}})
                            segments.append({"type": "text", "data": {"text": "\n"}})

                        origin_text = orig_info['text']
                        if orig_info['title'] and orig_info['title'] != orig_info['text']:
                            origin_text = f"{orig_info['title']}\n{origin_text}" if origin_text else orig_info['title']
                        if not origin_text:
                            origin_text = "[该动态无文字内容]"
                        
                        # 原动态作者
                        orig_author = '未知用户'
                        if orig:
                            orig_modules = orig.get('modules', {})
                            orig_author_module = orig_modules.get('module_author', {})
                            orig_author = orig_author_module.get('name', '未知用户')
                        
                        segments.append({"type": "text", "data": {"text": f"===\n原动态：[{orig_author}]\n{origin_text}\n===\n"}})
                    else:
                        segments.append({"type": "text", "data": {"text": "===\n原动态已删除或不可见\n===\n"}})

                    segments.append({"type": "text", "data": {"text": f"动态地址：{link}"}})

                    if qq_bot:
                        await qq_bot.send_mixed(segments, at_all=True, group_id=TARGET_GROUP)
                        await asyncio.sleep(5)
                        await qq_bot.send_mixed(segments, at_all=True, group_id=TARGET_GROUP_FANS)
                    add_log(f"[推送姬] 转发提醒 ID:{dyn_id}")
                    continue

                # ========== 图文动态 ==========
                elif dyn_type == 'DYNAMIC_TYPE_DRAW':
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新动态！\n\n"}})
                    
                    if info['title']:
                        segments.append({"type": "text", "data": {"text": f"{info['title']}\n"}})
                    
                    if info['text']:
                        segments.append({"type": "text", "data": {"text": f"{info['text']}\n\n"}})

                    if info['images']:
                        for img in info['images'][:1]:
                            if img:
                                segments.append({"type": "image", "data": {"file": img}})
                        segments.append({"type": "text", "data": {"text": "\n"}})

                    segments.append({"type": "text", "data": {"text": f"===\n动态地址：{link}"}})

                # ========== 纯文字动态 ==========
                elif dyn_type == 'DYNAMIC_TYPE_WORD':
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新动态！\n\n"}})

                    if info['text']:
                        segments.append({"type": "text", "data": {"text": f"{info['text']}\n\n"}})

                    segments.append({"type": "text", "data": {"text": f"===\n动态地址：{link}"}})

                # ========== 视频 ==========
                elif dyn_type == 'DYNAMIC_TYPE_AV':
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新视频！\n\n"}})

                    if info['title']:
                        segments.append({"type": "text", "data": {"text": f"{info['title']}\n"}})

                    if info['cover']:
                        segments.append({"type": "image", "data": {"file": info['cover']}})
                        segments.append({"type": "text", "data": {"text": "\n"}})

                    if info['text']:
                        segments.append({"type": "text", "data": {"text": f"{info['text']}\n\n"}})

                    segments.append({"type": "text", "data": {"text": f"===\n视频地址：{link}"}})

                # ========== 小视频 ==========
                elif dyn_type == 'DYNAMIC_TYPE_SHORT':
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新视频！\n\n"}})

                    if info['title']:
                        segments.append({"type": "text", "data": {"text": f"{info['title']}\n"}})

                    if info['cover']:
                        segments.append({"type": "image", "data": {"file": info['cover']}})
                        segments.append({"type": "text", "data": {"text": "\n"}})

                    if info['text']:
                        segments.append({"type": "text", "data": {"text": f"{info['text']}\n\n"}})

                    segments.append({"type": "text", "data": {"text": f"===\n视频地址：{link}"}})

                # ========== 音频 ==========
                elif dyn_type == 'DYNAMIC_TYPE_MUSIC':
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新音频！\n\n"}})

                    if info['title']:
                        segments.append({"type": "text", "data": {"text": f"{info['title']}\n"}})

                    if info['cover']:
                        segments.append({"type": "image", "data": {"file": info['cover']}})
                        segments.append({"type": "text", "data": {"text": "\n"}})

                    if info['text']:
                        segments.append({"type": "text", "data": {"text": f"{info['text']}\n\n"}})

                    segments.append({"type": "text", "data": {"text": f"===\n音频地址：{link}"}})

                # ========== 专栏 ==========
                elif dyn_type == 'DYNAMIC_TYPE_ARTICLE':
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新专栏！\n\n"}})

                    if info['title']:
                        segments.append({"type": "text", "data": {"text": f"{info['title']}\n"}})

                    if info['cover']:
                        segments.append({"type": "image", "data": {"file": info['cover']}})
                        segments.append({"type": "text", "data": {"text": "\n"}})

                    if info['text']:
                        segments.append({"type": "text", "data": {"text": f"{info['text']}\n\n"}})

                    segments.append({"type": "text", "data": {"text": f"===\n专栏地址：{link}"}})

                # ========== 其他未知类型 ==========
                    '''
                    segments.append({"type": "text", "data": {"text": f"{header}\n[云崎早_haya]发布了新动态！\n\n（该动态类型暂不支持解析：{dyn_type}）\n\n===\n动态地址：{link}"}})
                    '''
                if qq_bot and segments != []:
                    await qq_bot.send_mixed(segments, at_all=True, group_id=TARGET_GROUP)
                    await asyncio.sleep(5)
                    await qq_bot.send_mixed(segments, at_all=True, group_id=TARGET_GROUP_FANS)
                    
                add_log(f"[推送姬] {TYPE_MAP.get(dyn_type, '未知')}提醒 ID:{dyn_id}")
                

            seen_ids = set(current_ids) | seen_ids
            if len(seen_ids) > 20:
                seen_ids = set(sorted(seen_ids, key=lambda x: (len(x), x))[-20:])

            if new_ids:
                new_max = max(new_ids, key=lambda x: (len(x), x))
                if _id_greater(new_max, max_id):
                    max_id = new_max

            add_log(f"[推送姬] 本次推送完成，更新最大ID: {max_id}")

        except Exception as e:
            add_log(f"[推送姬] 动态监测异常：{e}")
            # print(f"[DEBUG] 异常: {e}")

        await asyncio.sleep(CHECK_INTERVAL)