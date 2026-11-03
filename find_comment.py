import asyncio
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from bilibili_api import comment, dynamic
from memory_store import *
from constants import *

PAGE_SIZE = 20
DEFAULT_TIME_WINDOW = 20
DEFAULT_REQUEST_DELAY = 0.25
TZ_CN = timezone(timedelta(hours=8))

KNOWN_COMMENT_TYPES = {
    1: comment.CommentResourceType.VIDEO,
    11: comment.CommentResourceType.DYNAMIC_DRAW,
    12: comment.CommentResourceType.ARTICLE,
    14: comment.CommentResourceType.AUDIO,
    17: comment.CommentResourceType.DYNAMIC,
}

class SearchIncomplete(Exception):
    """数据不完整或 API 异常，不能认定评论未找到。"""

def to_int(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise ValueError("bool 不是有效的数字")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value.strip()) if value.strip() else default
    raise ValueError(f"不能转换为 int 的类型：{type(value).__name__}")


def _matches(reply, uid, text, low, high):
    try:
        if not isinstance(reply, dict):
            return False
        member = reply.get("member") or {}
        content = reply.get("content") or {}
        reply_uid = to_int(member.get("mid"))
        ctime = to_int(reply.get("ctime"))
        return (
            reply_uid is not None
            and ctime is not None
            and reply_uid > 0
            and ctime > 0
            and reply_uid == uid
            and str(content.get("message") or "").strip() == text
            and low <= ctime <= high
        )
    except (TypeError, ValueError, AttributeError):
        return False


def _result(status, reason, stats, reply=None, oid=None, resource_type=None, errors=None):
    result = {"status": status, "reason": reason, "stats": dict(stats)}
    if oid is not None:
        result["oid"] = to_int(oid)
    if resource_type is not None:
        enum_value = getattr(resource_type, "value", resource_type)
        result["resource_type"] = to_int(enum_value)
    if reply is not None:
        try:
            timestamp = to_int(reply.get("ctime"))
            member = reply.get("member") or {}
            content = reply.get("content") or {}
            result["comment"] = {
                "rpid": to_int(reply.get("rpid") or reply.get("rpid_str")),
                "root": to_int(reply.get("root") if reply.get("root") is not None else reply.get("root_str"), 0),
                "parent": to_int(reply.get("parent") if reply.get("parent") is not None else reply.get("parent_str"), 0),
                "uid": to_int(member.get("mid")),
                "uname": str(member.get("uname") or ""),
                "text": str(content.get("message") or ""),
                "ctime": timestamp,
                "time": datetime.fromtimestamp(timestamp, TZ_CN).isoformat() if timestamp else None,
            }
        except (TypeError, ValueError, AttributeError, OverflowError) as exc:
            raise SearchIncomplete(f"命中评论的数据格式异常：{exc}") from exc
    if errors:
        result["errors"] = errors[:8]
    return result


async def get_comment_resource(orig, credential=None):
    if not isinstance(orig, dict) or not orig:
        return None

    try:
        basic = orig.get("basic") or {}
        kind = to_int(basic.get("comment_type"))
        oid = to_int(basic.get("comment_id_str") or basic.get("rid_str"))
        if kind in KNOWN_COMMENT_TYPES and oid is not None and oid > 0:
            return oid, KNOWN_COMMENT_TYPES[kind]
    except (TypeError, ValueError, AttributeError):
        pass

    orig_type = orig.get("type")
    try:
        orig_id = to_int(orig.get("id_str"))
        if orig_id is not None and orig_id <= 0:
            orig_id = None
        modules = orig.get("modules") or {}
        module_dynamic = modules.get("module_dynamic") or {}
        major = module_dynamic.get("major") or {}
    except (TypeError, ValueError, AttributeError) as exc:
        raise SearchIncomplete(f"原动态结构异常：{exc}") from exc

    if orig_type == "DYNAMIC_TYPE_AV":
        try:
            aid = to_int((major.get("archive") or {}).get("aid"))
            if aid is not None and aid > 0:
                return aid, comment.CommentResourceType.VIDEO
        except (TypeError, ValueError, AttributeError):
            pass

    if orig_type in ("DYNAMIC_TYPE_WORD", "DYNAMIC_TYPE_FORWARD") and orig_id is not None:
        return orig_id, comment.CommentResourceType.DYNAMIC

    detail_error = None
    if orig_id is not None:
        try:
            dy = dynamic.Dynamic(dynamic_id=orig_id, credential=credential)
            detail_response = await dy.get_info()
            if not isinstance(detail_response, dict):
                raise SearchIncomplete("动态详情返回值不是字典")
            code = detail_response.get("code")
            if code is not None and str(code) != "0":
                raise SearchIncomplete(f"动态详情 API 错误 code={code}")
            detail = detail_response.get("data", detail_response)
            if not isinstance(detail, dict):
                raise SearchIncomplete("动态详情 data 不是字典")
            detail_item = detail.get("item", detail)
            if not isinstance(detail_item, dict):
                raise SearchIncomplete("动态详情 item 不是字典")
            try:
                detail_basic = detail_item.get("basic") or {}
                kind = to_int(detail_basic.get("comment_type"))
                oid = to_int(detail_basic.get("comment_id_str") or detail_basic.get("rid_str"))
                if kind in KNOWN_COMMENT_TYPES and oid is not None and oid > 0:
                    return oid, KNOWN_COMMENT_TYPES[kind]
            except (TypeError, ValueError, AttributeError):
                pass

            if orig_type == "DYNAMIC_TYPE_DRAW":
                get_rid = getattr(dy, "get_rid", None)
                if callable(get_rid):
                    rid = get_rid()
                    if asyncio.iscoroutine(rid):
                        rid = await rid
                    try:
                        rid = to_int(rid)
                        if rid is not None and rid > 0:
                            return rid, comment.CommentResourceType.DYNAMIC_DRAW
                    except (TypeError, ValueError):
                        pass
        except Exception as exc:
            detail_error = f"{type(exc).__name__}: {exc}"

    if orig_type == "DYNAMIC_TYPE_DRAW":
        try:
            draw_id = to_int((major.get("draw") or {}).get("id"))
            if draw_id is not None and draw_id > 0:
                return draw_id, comment.CommentResourceType.DYNAMIC_DRAW
        except (TypeError, ValueError, AttributeError):
            pass

    if detail_error:
        raise SearchIncomplete(f"原动态详情查询失败：{detail_error}")
    return None


async def find_comment(
    *,
    oid,
    resource_type,
    uid,
    text,
    timestamp,
    credential=None,
    time_window=DEFAULT_TIME_WINDOW,
    request_delay=DEFAULT_REQUEST_DELAY,
    on_progress: Optional[Callable[[str], None]] = None,
):
    stats = {
        "api_requests": 0,
        "root_pages": 0,
        "roots_seen": 0,
        "sub_pages": 0,
        "sub_roots_checked": 0,
        "roots_skipped_newer": 0,
        "roots_skipped_no_replies": 0,
    }
    try:
        if not isinstance(resource_type, comment.CommentResourceType):
            resource_type = comment.CommentResourceType(to_int(resource_type))
        oid = to_int(oid)
        uid = to_int(uid)
        timestamp = to_int(timestamp)
        time_window = to_int(time_window)
        request_delay = float(request_delay)
        if (oid is None or uid is None or timestamp is None
                or oid <= 0 or uid <= 0 or timestamp <= 0
                or time_window is None or time_window < 0 or request_delay < 0):
            raise ValueError("缺少有效的 oid/UID/时间或请求参数")
    except (TypeError, ValueError) as exc:
        return _result("incomplete", f"参数无效：{exc}", stats)

    target_text = str(text or "").strip()
    if not target_text:
        return _result("incomplete", "目标评论正文为空", stats, oid=oid, resource_type=resource_type)

    low, high = timestamp - time_window, timestamp + time_window
    errors = []
    offsets_seen = set()
    roots_seen = set()
    offset = ""
    completed = False

    async def call_api(awaitable):
        stats["api_requests"] += 1
        if request_delay > 0:
            await asyncio.sleep(request_delay)
        response = await awaitable
        if not isinstance(response, dict):
            raise SearchIncomplete("API 返回值不是字典")
        code = response.get("code")
        if code is not None and str(code) != "0":
            raise SearchIncomplete(f"API 返回错误 code={code}: {response.get('message', '')}")
        data = response.get("data", response)
        if not isinstance(data, dict):
            raise SearchIncomplete("API 返回的 data 不是字典")
        return data

    def progress(message):
        if on_progress is not None:
            on_progress(message)

    async def scan_sub_replies(root):
        try:
            root_id = to_int(root.get("rpid") or root.get("rpid_str"))
            if root_id is None or root_id <= 0:
                raise ValueError("rpid 缺失或无效")
        except (TypeError, ValueError, AttributeError) as exc:
            raise SearchIncomplete(f"一级评论缺少有效 rpid：{exc}") from exc

        obj = comment.Comment(oid=oid, type_=resource_type, rpid=root_id, credential=credential)
        cache = {}
        baseline_count = None

        async def fetch(page_num):
            nonlocal baseline_count
            if page_num in cache:
                return cache[page_num]

            data = await call_api(obj.get_sub_comments(page_index=page_num, page_size=PAGE_SIZE))
            stats["sub_pages"] += 1
            replies = data.get("replies") or []
            page_info = data.get("page") or {}
            if not isinstance(replies, list) or not isinstance(page_info, dict):
                raise SearchIncomplete(f"楼层 {root_id} 第 {page_num} 页数据格式异常")
            try:
                count = to_int(page_info.get("count"))
            except (TypeError, ValueError) as exc:
                raise SearchIncomplete(f"楼层 {root_id} 回复总数格式异常：{exc}") from exc
            if count is None or count <= 0:
                raise SearchIncomplete(f"楼层 {root_id} 缺少有效的回复总数")
            if baseline_count is None:
                baseline_count = count
            elif baseline_count != count:
                raise SearchIncomplete(f"楼层 {root_id} 搜索期间回复总数变化")
            if not replies:
                raise SearchIncomplete(f"楼层 {root_id} 第 {page_num} 页为空或不可见")

            try:
                times = [to_int(reply.get("ctime")) for reply in replies]
            except (TypeError, ValueError, AttributeError) as exc:
                raise SearchIncomplete(f"楼层 {root_id} 第 {page_num} 页时间戳格式异常：{exc}") from exc
            if any(t is None or t <= 0 for t in times) or times != sorted(times):
                raise SearchIncomplete(f"楼层 {root_id} 第 {page_num} 页时间顺序异常")

            page = {"items": replies, "min": times[0], "max": times[-1], "count": count}
            if page_num - 1 in cache and cache[page_num - 1]["max"] > page["min"]:
                raise SearchIncomplete(f"楼层 {root_id} 相邻页面时间逆序")
            if page_num + 1 in cache and page["max"] > cache[page_num + 1]["min"]:
                raise SearchIncomplete(f"楼层 {root_id} 相邻页面时间逆序")
            cache[page_num] = page
            return page

        first = await fetch(1)
        if first["min"] > high:
            return None
        total_pages = math.ceil(first["count"] / PAGE_SIZE)
        if total_pages < 1:
            raise SearchIncomplete(f"楼层 {root_id} 回复统计与页面不一致")
        last = await fetch(total_pages)
        if last["max"] < low:
            return None

        left, right = 1, total_pages
        while left < right:
            mid = (left + right) // 2
            page = await fetch(mid)
            if page["max"] < low:
                left = mid + 1
            else:
                right = mid

        page_num = left
        while page_num <= total_pages:
            page = await fetch(page_num)
            if page["min"] > high:
                break
            for reply in page["items"]:
                try:
                    reply_root = to_int(reply.get("root") or reply.get("root_str"))
                except (TypeError, ValueError, AttributeError):
                    reply_root = None
                if reply_root == root_id and _matches(reply, uid, target_text, low, high):
                    return reply
            page_num += 1
        return None

    while True:
        try:
            data = await call_api(comment.get_comments_lazy(
                oid=oid,
                type_=resource_type,
                offset=offset,
                order=comment.OrderType.TIME,
                credential=credential,
            ))
            replies = data.get("replies") or []
            if not isinstance(replies, list):
                raise SearchIncomplete("一级评论 replies 不是列表")
            tops = data.get("top_replies") or []
            roots = list(replies)
            if isinstance(tops, list):
                roots = tops + roots
            elif isinstance(tops, dict):
                roots.insert(0, tops)
            top = data.get("top") or {}
            if isinstance(top, dict) and isinstance(top.get("upper"), dict):
                roots.insert(0, top["upper"])
        except Exception as exc:
            errors.append(f"一级评论获取失败：{type(exc).__name__}: {exc}")
            break

        stats["root_pages"] += 1
        progress(f"一级评论第 {stats['root_pages']} 页；累计 API 请求 {stats['api_requests']}")

        for root in roots:
            try:
                if not isinstance(root, dict):
                    raise ValueError("一级评论条目不是字典")
                root_id = to_int(root.get("rpid") or root.get("rpid_str"))
                if root_id is None or root_id <= 0:
                    raise ValueError("一级评论缺少有效 rpid")
            except (TypeError, ValueError, AttributeError) as exc:
                errors.append(str(exc))
                continue
            if root_id in roots_seen:
                continue
            roots_seen.add(root_id)
            stats["roots_seen"] += 1

            try:
                root_parent = to_int(root.get("parent") if root.get("parent") is not None else root.get("parent_str"), 0)
                root_root = to_int(root.get("root") if root.get("root") is not None else root.get("root_str"), 0)
                if root_parent == 0 and root_root == 0 and _matches(root, uid, target_text, low, high):
                    return _result("top_comment", "匹配到一级评论", stats, root, oid, resource_type)
            except (TypeError, ValueError) as exc:
                errors.append(f"一级评论 {root_id} 关系字段异常：{exc}")

            previews = root.get("replies") or []
            if not isinstance(previews, list):
                errors.append(f"楼层 {root_id} 的预览回复不是列表")
                previews = []
            for preview in previews:
                try:
                    preview_root = to_int(preview.get("root") or preview.get("root_str"))
                except (TypeError, ValueError, AttributeError):
                    preview_root = None
                if preview_root == root_id and _matches(preview, uid, target_text, low, high):
                    return _result("reply", "匹配到楼中楼预览回复", stats, preview, oid, resource_type)

            try:
                root_time = to_int(root.get("ctime"))
                rcount = to_int(root.get("rcount"))
                if root_time is None or root_time <= 0:
                    raise ValueError("ctime 缺失或无效")
                if rcount is None or rcount < 0:
                    raise ValueError("rcount 缺失或无效")
            except (TypeError, ValueError, AttributeError) as exc:
                errors.append(f"一级评论 {root_id} 时间/回复数量异常：{exc}")
                continue
            if root_time > high:
                stats["roots_skipped_newer"] += 1
                continue
            if rcount == 0:
                stats["roots_skipped_no_replies"] += 1
                continue

            stats["sub_roots_checked"] += 1
            try:
                found = await scan_sub_replies(root)
            except Exception as exc:
                errors.append(f"楼层 {root_id} 查询失败：{type(exc).__name__}: {exc}")
                continue
            if found is not None:
                return _result("reply", "匹配到楼中楼回复", stats, found, oid, resource_type)

        cursor = data.get("cursor") or {}
        if not isinstance(cursor, dict):
            errors.append("一级评论分页 cursor 格式异常")
            break
        if cursor.get("is_end") is True:
            completed = True
            break

        pagination = cursor.get("pagination_reply") or {}
        next_offset = pagination.get("next_offset") if isinstance(pagination, dict) else None
        if next_offset is None or next_offset == "":
            errors.append("一级评论分页缺少下一页游标")
            break
        try:
            # offset 可以是字典，不能转成 int。
            offset_key = json.dumps(next_offset, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            errors.append(f"一级评论分页游标无法处理：{exc}")
            break
        if next_offset == offset or offset_key in offsets_seen:
            errors.append("一级评论分页游标重复，无法认定遍历完成")
            break
        offsets_seen.add(offset_key)
        offset = next_offset

    if completed and not errors:
        return _result("not_found", "已遍历全部可访问评论，未找到目标；可能是普通转发", stats, oid=oid, resource_type=resource_type)
    return _result("incomplete", "评论搜索未完整结束，不能判断是否为普通转发", stats, oid=oid, resource_type=resource_type, errors=errors)


async def find_comment_from_dynamic(item, credential=None, **kwargs):
    stats = {"api_requests": 0, "root_pages": 0, "sub_pages": 0}
    if not isinstance(item, dict) or item.get("type") != "DYNAMIC_TYPE_FORWARD":
        return _result("incomplete", "输入不是转发动态", stats)

    try:
        modules = item.get("modules") or {}
        author = modules.get("module_author") or {}
        module_dynamic = modules.get("module_dynamic") or {}
        desc = module_dynamic.get("desc") or {}
        target_text = str(desc.get("text") or "").strip()
        if not target_text:
            return _result("forward_no_text", "转发时没有附加文字，无需评论匹配", stats)
        uid = to_int(author.get("mid"))
        timestamp = to_int(author.get("pub_ts"))
        orig = item.get("orig")
        if (uid is None or uid <= 0 or timestamp is None or timestamp <= 0
                or not isinstance(orig, dict) or not orig):
            raise ValueError("UID、发布时间或原动态信息缺失")
    except (TypeError, ValueError, AttributeError) as exc:
        return _result("incomplete", f"转发动态参数异常：{exc}", stats)

    try:
        resource = await get_comment_resource(orig, credential)
        if resource is None:
            return _result("incomplete", "无法确定原内容评论区的 ID 或资源类型", stats)
        oid, resource_type = resource
        return await find_comment(
            oid=oid, resource_type=resource_type,
            uid=uid, text=target_text, timestamp=timestamp,
            credential=credential, **kwargs,
        )
    except Exception as exc:
        return _result("incomplete", f"评论搜索异常：{type(exc).__name__}: {exc}", stats)