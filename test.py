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

def get_book_availability(item):
    """
    把一条 Libby 搜索记录合并为【有声书 / 电子书】两行。
    去掉格式细节，只显示媒体类型 + 状态。
    """
    results = []

    # 书名
    raw_title = item.get("title", "未知书名")
    title = raw_title.get("main") if isinstance(raw_title, dict) else raw_title

    # 所有格式
    format_names = get_format_names(item)
    if not format_names:
        format_names = ["未知格式"]

    # 获取可用性字段
    av = extract_availability_fields(item)

    # 按媒体类型分组
    grouped_formats = {"电子书": [], "有声书": [], "未知": []}
    for fmt in format_names:
        media_type = detect_media_type([fmt])
        grouped_formats[media_type].append(fmt)

    # 遍历每个媒体类型
    for media_type, formats in grouped_formats.items():
        if not formats:
            continue

        # 计算等待时间
        wait_weeks = compute_wait_weeks(
            av["copiesOwned"], av["numberOfHolds"], av["estimatedWaitDays"]
        )
        if wait_weeks is None:
            wait_text = "不可借"
        elif wait_weeks == 0:
            wait_text = "可立即借阅"
        else:
            wait_text = f"预计等待约 {wait_weeks} 周"

        # 每种媒体类型只生成一行
        results.append({
            "Title": title,
            "MediaType": media_type,
            "等待情况": wait_text
        })

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

# ========== 主程序 ==========
def search_books_in_libby(csv_path):
    # 读取 CSV 文件（Goodreads 导出是逗号分隔）
    try:
        df = pd.read_csv(csv_path, sep=",", dtype=str, encoding="utf-8")
    except Exception as e:
        print(f"❌ CSV 读取失败: {e}")
        return

    # 检查是否有 Title 和 Author 列
    if "Title" not in df.columns or "Author" not in df.columns:
        print("❌ 错误：CSV 文件中缺少 Title 或 Author 列，请检查文件格式！")
        print(f"可用列：{df.columns.tolist()}")
        return

    results = []

    for idx, row in df.iterrows():
        title = str(row["Title"]).strip()
        author = str(row["Author"]).strip()
        print(f"\n🔍 开始查询: {title} by {author}")

        items = search_libby_by_title(title)
        matches = find_all_matches(items, title, author)

        if matches:
            for it in matches:
                book_infos = get_book_availability(it)
                results.extend(book_infos)
                # 多行打印每个版本
                for info in book_infos:
                    print(
                    f"✅ 找到: {info['Title']} | 类型: {info['MediaType']} | 状态: {info['等待情况']}"
                )
            
            
        else:
            results.append({
                "Title": title,
                "MediaType": "未找到",
                "Formats": "",
                "Availability": "未找到"
            })
            print(f"❌ 未找到: {title}")

        time.sleep(1)  # 防止被封

    result_df = pd.DataFrame(results)
    result_df.to_csv("libby_search_results.csv", index=False)
    print("\n✅ 查询完成！结果已导出到 libby_search_results.csv")
    return result_df

# ========== 执行 ==========
if __name__ == "__main__":
    # 先做探针，验证字段是否拿到
    #debug_probe("That's Not My Name", author="Megan Lally")
    #debug_probe("When No One Is Watching", author="Alyssa Cole")

    # 再跑你原来的批量流程
    search_books_in_libby("goodreads_library_export.csv")

