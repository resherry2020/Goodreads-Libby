import requests
import pandas as pd
import time
import json
import re
from urllib.parse import quote
import math

# ========== 配置 ==========
LIBRARY_ID = "sapln-adelaide"
BASE_URL = f"https://thunder.api.overdrive.com/v2/libraries/{LIBRARY_ID}/media"
CLIENT_ID = "dewey"

# ========== 工具函数 ==========
def clean_title(title: str) -> str:
    """
    清洗标题，去掉括号()和冒号:后面的部分
    """
    return re.split(r"[\(:：]", title)[0].strip()
def normalize(text):
    """标准化字符串：去掉标点、大小写"""
    if not isinstance(text, str):
        return ""
    return re.sub(r"[^\w\s]", "", text).strip().lower()
    
def get_format_names(item):
    names = []
    for f in item.get("formats", []) or []:
        if isinstance(f, dict):
            names.append(f.get("name", ""))
        elif isinstance(f, str):
            names.append(f)
    return names

def detect_media_type(format_names):
    joined = " | ".join(format_names).lower()
    if "audiobook" in joined:
        return "有声书"
    if "ebook" in joined or "read" in joined or "kobo" in joined or "kindle" in joined:
        return "电子书"
    return "未知"

def extract_availability_fields(item):
    """
    同时兼容两种可能结构：
    1) 平铺在顶层：copiesOwned / copiesAvailable / numberOfHolds / availabilityType / estimatedWaitDays
    2) 嵌套在 item['availability'] 里
    """
    avail = item.get("availability", {}) or {}

    def pick(k, default=None):
        return avail.get(k, item.get(k, default))

    fields = {
        "availabilityType": item.get("availabilityType", avail.get("availabilityType")),
        "copiesOwned": pick("copiesOwned", 0) or 0,
        "copiesAvailable": pick("copiesAvailable", 0) or 0,
        "numberOfHolds": pick("numberOfHolds", 0) or 0,
        "estimatedWaitDays": pick("estimatedWaitDays", None),
    }
    return fields

def compute_wait_weeks(copies_owned, holds, estimated_wait_days):
    if estimated_wait_days is not None:
        try:
            return max(1, round(float(estimated_wait_days) / 7))
        except Exception:
            pass
    if copies_owned and copies_owned > 0:
        # 粗略估算：每本两周；(排队人数+现有本数)/本数 * 2 周
        return max(1, round((holds + copies_owned) / copies_owned * 2))
    return None

def search_libby_by_title(title):
    """在 OverDrive (Libby) 搜索书名"""
    url = f"{BASE_URL}?query={quote(title)}&format=ebook-overdrive,ebook-media-do,ebook-overdrive-provisional,audiobook-overdrive,audiobook-overdrive-provisional,magazine-overdrive&perPage=24&page=1&x-client-id={CLIENT_ID}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            print(f"⚠️ 搜索失败: {title} -> {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 请求失败: {title} -> {e}")
        return []

import math


# ---------- 辅助：在组内选出“最佳候选” ----------
def _author_matches(item, author_norm):
    if not author_norm:
        return False
    creators = item.get("creators") or []
    names = " ".join([c.get("name", "") for c in creators if isinstance(c, dict)]) or item.get("firstCreatorName", "")
    return author_norm in normalize(names)

def _is_immediately_available(item):
    # 优先判断 isAvailable 或 availableCopies / availableCopies (top-level) / luckyDayAvailableCopies
    if item.get("isAvailable") is True:
        return True
    ac = item.get("availableCopies") or item.get("availableCopies", None) or item.get("luckyDayAvailableCopies", None)
    try:
        if ac is not None and int(ac) > 0:
            return True
    except Exception:
        pass
    return False

def _est_days(item):
    # 尝试从多个字段读取 estimatedWaitDays（top-level / availability）
    val = item.get("estimatedWaitDays")
    if val is None:
        # try availability nested (some libs)
        av = item.get("availability", {}) or {}
        val = av.get("estimatedWaitDays", None)
    try:
        return float(val) if val is not None else None
    except Exception:
        return None

def select_best_for_group(items, author_norm):
    """
    从同一媒体类型的候选 items 中选一个最佳项（返回单个 item）。
    策略：先作者匹配 -> 再 isAvailable / availableCopies -> 再 min estimatedWaitDays -> else first
    """
    if not items:
        return None

    # 1) 作者匹配优先（若有多条作者匹配，继续按下面规则选）
    author_filtered = [it for it in items if _author_matches(it, author_norm)]
    pool = author_filtered if author_filtered else items

    # 2) 立即可借优先
    for it in pool:
        if _is_immediately_available(it):
            return it

    # 3) 按 estimatedWaitDays 排序（None 放后面）
    with_est = sorted(pool, key=lambda it: (_est_days(it) is None, _est_days(it) if _est_days(it) is not None else float('inf')))
    if with_est:
        return with_est[0]

    # 4) fallback
    return pool[0]


# ---------- 主匹配与汇总函数（替换 find_all_matches & get_book_availability 的职责） ----------


def get_book_availability(items):
    """
    按类型（电子书 / 有声书）合并多个格式，并且计算最短等待时间
    """
    grouped = {"电子书": [], "有声书": []}

    for item in items:
        formats = item.get("formats", [])
        format_names = []
        for f in formats:
            if isinstance(f, dict):
                # 如果是 dict，取 "name"
                if "name" in f:
                    format_names.append(f["name"].lower())
            elif isinstance(f, str):
                format_names.append(f.lower())
                
        media_type = ("有声书" if any("audiobook" in f for f in format_names) else
    "电子书" if any("ebook" in f or "overdrive read" in f for f in format_names) else
    "未知")
        if not media_type:
            continue

        copies_available = item.get("copiesAvailable", 0)
        copies_owned = item.get("ownedCopies", 0)
        estimated_wait_days = item.get("estimatedWaitDays", None)

        if copies_available > 0:
            grouped[media_type].append("可立即借阅")
        elif copies_owned == 0:
            grouped[media_type].append("不可借")
        elif estimated_wait_days is not None:
            if estimated_wait_days > 0:
                grouped[media_type].append(f"预计等待约 {math.ceil(estimated_wait_days / 7)} 周")
            else:
                grouped[media_type].append("可立即借阅")
        else:
            grouped[media_type].append("不可借")

    # 合并同类型结果
    results = []
    for media_type, statuses in grouped.items():
        if not statuses:
            continue
        if all(s == "不可借" for s in statuses):
            results.append((media_type, "不可借"))
        elif any(s == "可立即借阅" for s in statuses):
            results.append((media_type, "可立即借阅"))
        else:
            waits = []
            for s in statuses:
                match = re.search(r"(\d+)", s)
                if match:
                    waits.append(int(match.group()))
            if waits:
                results.append((media_type, f"预计等待约 {min(waits)} 周"))
            else:
                results.append((media_type, "不可借"))
        return results

def find_all_matches(items, title, author):
    """
    在搜索结果中查找所有与目标书名或作者匹配的项。
    返回所有可能相关的 item。
    """
    title_norm = normalize(title)
    author_norm = normalize(author)
    matches = []

    for item in items:
        raw_title = item.get("title", "")
        item_title = raw_title.get("main") if isinstance(raw_title, dict) else raw_title
        creators = item.get("creators") or []
        item_authors = " ".join([c.get("name", "") for c in creators if isinstance(c, dict)])
        title_match = title_norm in normalize(item_title)
        author_match = author_norm in normalize(item_authors)

        if title_match or author_match:
            matches.append(item)

    return matches



# ========== 主程序 ==========

def search_books_in_libby(csv_path):
    # 读取 CSV 文件（Goodreads 导出是逗号分隔）
    try:
        df = pd.read_csv(csv_path, sep=",", dtype=str, encoding="utf-8")
        # 只保留 Exclusive Shelf == to-read 的书籍
        df = df[df["Exclusive Shelf"].str.lower() == "to-read"]
    except Exception as e:
        print(f"❌ CSV 读取失败: {e}")
        return

    # 检查是否有 Title 和 Author 列
    if "Title" not in df.columns or "Author" not in df.columns:
        print("❌ 错误：CSV 文件中缺少 Title 或 Author 列，请检查文件格式！")
        print(f"可用列：{df.columns.tolist()}")
        return

    final_results = []

    for idx, row in df.iterrows():
        title = str(row["Title"]).strip()
        author = str(row["Author"]).strip()
        print(f"\n🔍 开始查询: {title} by {author}")

        # 搜索 Libby
        items = search_libby_by_title(title)
        best_matches = find_all_matches(items, title, author)

        # 如果没有找到匹配项
        if not best_matches:
            print(f"❌ 未找到: {title}")
            continue

        # 获取可借阅状态
        results = get_book_availability(best_matches)
        if not results:
            print(f"⚠️ 未找到可借信息: {title}")
            continue

        # 输出结果并存储
        for media_type, status in results:
            print(f"✅ 找到: {title} | 类型: {media_type} | 状态: {status}")
            final_results.append({
                "Title": title,
                "Author": author,
                "Type": media_type,
                "Status": status
            })

        time.sleep(1)  # 防止被封

    # 保存到 CSV
    result_df = pd.DataFrame(final_results)
    result_df.to_csv("libby_search_results.csv", index=False, encoding="utf-8")
    print("\n✅ 查询完成！结果已导出到 libby_search_results.csv")
    return result_df


def debug_probe(title, author=None, limit=5):
    """
    打印原始返回里的关键字段，确认是否拿到 copiesAvailable / numberOfHolds / copiesOwned 等。
    """
    print(f"\n==== DEBUG PROBE for: {title} ====")
    items = search_libby_by_title(title)
    if not items:
        print("无返回 items")
        return

    # 只看前几条，避免刷屏
    for idx, it in enumerate(items[:limit], 1):
        # 书名
        raw_title = it.get("title", "")
        tname = raw_title.get("main") if isinstance(raw_title, dict) else raw_title

        # 作者
        creators = it.get("creators") or []
        creator_names = ", ".join([c.get("name", "") for c in creators if isinstance(c, dict)]) or it.get("firstCreatorName", "")

        # 关键键是否存在
        keys = set(it.keys())
        has_av_nested = isinstance(it.get("availability"), dict)
        av = extract_availability_fields(it)

        # 打印
        print(f"\n-- ITEM {idx} --")
        print("Title:", tname)
        print("Author(s):", creator_names)
        print("Keys:", sorted(list(keys)))
        print("Formats:", get_format_names(it))
        print("MediaType (detected):", detect_media_type(get_format_names(it)))
        print("Top-level availabilityType:", it.get("availabilityType"))
        print("Has nested 'availability' dict?:", has_av_nested)
        if has_av_nested:
            print("Nested availability keys:", list(it.get("availability", {}).keys()))

        print("copiesOwned:", av["copiesOwned"])
        print("copiesAvailable:", av["copiesAvailable"])
        print("numberOfHolds:", av["numberOfHolds"])
        print("estimatedWaitDays:", av["estimatedWaitDays"])


# ========== 执行 ==========
if __name__ == "__main__":
    debug_probe("The Pact", author="Sharon J. Bolton")
    debug_probe("taboo", author="Hannah Ferguson")
    debug_probe("Welcome to the Hyunam-dong Bookshop", author="Hwang Bo-Reum")
    
    search_books_in_libby("goodreads_library_export.csv")

