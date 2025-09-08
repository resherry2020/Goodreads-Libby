import requests
import pandas as pd
import time
import json
import re
from urllib.parse import quote
import math

## ========== Configuration ==========
LIBRARY_ID = "sapln-adelaide"
BASE_URL = f"https://thunder.api.overdrive.com/v2/libraries/{LIBRARY_ID}/media"
CLIENT_ID = "dewey"

# ========== Tolls ==========
def normalize(text):
    """Normalize string: remove punctuation, lowercase"""
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
        return "Audiobook"
    if "ebook" in joined or "read" in joined or "kobo" in joined or "kindle" in joined:
        return "Ebook"
    return "Unknown"

def extract_availability_fields(item):
    """
    Compatible with two possible structures:
    1) Top-level: copiesOwned / copiesAvailable / numberOfHolds / availabilityType / estimatedWaitDays
    2) Nested in item['availability']
    Also adds isAvailable, isHoldable, luckyDayAvailableCopies fields
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
        "isAvailable": item.get("isAvailable", avail.get("isAvailable", False)),
        "isHoldable": item.get("isHoldable", avail.get("isHoldable", True)),
        "luckyDayAvailableCopies": item.get("luckyDayAvailableCopies", avail.get("luckyDayAvailableCopies", 0)),
    }
    return fields

def compute_wait_weeks(copies_owned, holds, estimated_wait_days):
    if estimated_wait_days is not None:
        try:
            return max(1, round(float(estimated_wait_days) / 7))
        except Exception:
            pass
    if copies_owned and copies_owned > 0:
        # Rough estimate: each copy two weeks; (queue + owned)/owned * 2 weeks
        return max(1, round((holds + copies_owned) / copies_owned * 2))
    return None

def search_libby_by_title(title):
    """Search title in OverDrive (Libby)"""
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
    Each row contains Title, Author, Availability, MediaType, WaitStatus
    Optimized borrow status judgment, combining isAvailable, isHoldable, luckyDayAvailableCopies
    """
    results = []

    # 书名
    raw_title = item.get("title", "Unknown Title")
    title = raw_title.get("main") if isinstance(raw_title, dict) else raw_title

    # 作者
    creators = item.get("creators") or []
    author = ", ".join([c.get("name", "") for c in creators if isinstance(c, dict)])

    # 所有格式
    format_names = get_format_names(item)
    if not format_names:
        format_names = ["Unknown Format"]

    # 获取可用性字段
    av = extract_availability_fields(item)

    # 按媒体类型分组
    grouped_formats = {"Ebook": [], "Audiobook": [], "Unknown": []}
    for fmt in format_names:
        media_type = detect_media_type([fmt])
        grouped_formats[media_type].append(fmt)

    # 遍历每个媒体类型
    for media_type, formats in grouped_formats.items():
        if not formats:
            continue

        # Determine borrow status
        if av["isAvailable"] or av["copiesAvailable"] > 0 or av["luckyDayAvailableCopies"] > 0:
            wait_text = "Available now"
            availability = "Available"
        elif not av["isHoldable"]:
            wait_text = "Not borrowable"
            availability = "Not available"
        elif av["estimatedWaitDays"] is not None:
            try:
                wait_weeks = max(1, round(float(av["estimatedWaitDays"]) / 7))
                wait_text = f"Wait about {wait_weeks} weeks"
                availability = "Not available"
            except Exception:
                wait_text = "Not borrowable"
                availability = "Not available"
        else:
            wait_text = "Not borrowable"
            availability = "Not available"

        results.append({
            "Title": title,
            "Author": author,
            "Availability": availability,
            "MediaType": media_type,
            "WaitStatus": wait_text
        })

    return results

def preprocess_title(title):
    """Keep only the part before the first '(' or ':'"""
    if not isinstance(title, str):
        return ""
    # 找到第一个 ( 或 : 的位置
    idx1 = title.find('(')
    idx2 = title.find(':')
    idx = min(idx1 if idx1 != -1 else len(title), idx2 if idx2 != -1 else len(title))
    return title[:idx].strip()

def find_all_matches(items, title, author):
    """
    Title must match exactly, author name must be contained
    """
    title_norm = normalize(preprocess_title(title))
    author_norm = normalize(author)
    matches = []

    for item in items:
        raw_title = item.get("title", "")
        item_title = raw_title.get("main") if isinstance(raw_title, dict) else raw_title
        item_title_norm = normalize(preprocess_title(item_title))
        creators = item.get("creators") or []
        item_authors = " ".join([c.get("name", "") for c in creators if isinstance(c, dict)])
        item_author_norm = normalize(item_authors)
        # 书名完全匹配，作者名包含即可
        if title_norm == item_title_norm and author_norm in item_author_norm:
            matches.append(item)
    return matches

def debug_probe(title, author=None, limit=5):
    """
    Print key fields from raw response to confirm copiesAvailable / numberOfHolds / copiesOwned, etc.
    """
    print(f"\n==== DEBUG PROBE for: {title} ====")
    items = search_libby_by_title(title)
    if not items:
        print("No items returned")
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

        # Print
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
    # Read CSV file (Goodreads export is comma-separated)
    try:
        df = pd.read_csv(csv_path, sep=",", dtype=str, encoding="utf-8")
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        return

    # Check for Title, Author, Exclusive Shelf columns
    if "Title" not in df.columns or "Author" not in df.columns or "Exclusive Shelf" not in df.columns:
        print("❌ Error: CSV file missing Title, Author or Exclusive Shelf columns. Please check the file format!")
        print(f"Available columns: {df.columns.tolist()}")
        return

    # Only process to-read
    df = df[df["Exclusive Shelf"].str.strip().str.lower() == "to-read"]

    results = []

    for idx, row in df.iterrows():
        title_full = str(row["Title"]).strip()
        author = str(row["Author"]).strip()
        print(f"\n🔍 Searching: {title_full} by {author}")

        # Use preprocessed title for search
        title_query = preprocess_title(title_full)
        items = search_libby_by_title(title_query)

        # Match using preprocessed titles
        matches = []
        title_norm = normalize(title_query)
        author_norm = normalize(author)
        for item in items:
            raw_title = item.get("title", "")
            item_title = raw_title.get("main") if isinstance(raw_title, dict) else raw_title
            item_title_norm = normalize(preprocess_title(item_title))
            creators = item.get("creators") or []
            item_authors = " ".join([c.get("name", "") for c in creators if isinstance(c, dict)])
            item_author_norm = normalize(item_authors)
            if title_norm == item_title_norm and author_norm in item_author_norm:
                matches.append(item)

        # Group by normalized preprocessed title
        media_map = {}
        for it in matches:
            raw_title = it.get("title", "")
            item_title = raw_title.get("main") if isinstance(raw_title, dict) else raw_title
            key = normalize(preprocess_title(item_title))
            if key not in media_map:
                media_map[key] = []
            media_map[key].append(it)

        if media_map:
            for key, items_group in media_map.items():
                for it in items_group:
                    book_infos = get_book_availability(it)
                    for info in book_infos:
                        # Merge 'Available' and 'Not available' into 'Found', keep 'Not found' as is
                        availability = info["Availability"]
                        if availability in ["Available", "Not available"]:
                            availability_out = "Found"
                        else:
                            availability_out = availability
                        results.append({
                            "Title": f"{info['Title']} ({info['Author']})",
                            "Availability": availability_out,
                            "MediaType": info["MediaType"],
                            "WaitStatus": info["WaitStatus"]
                        })
                        print(f"✅ Found: {info['Title']} | Author: {info['Author']} | Type: {info['MediaType']} | Status: {info['WaitStatus']}")
        else:
            results.append({
                "Title": f"{title_full}",
                "Availability": "Not found",
                "MediaType": "Not found",
                "WaitStatus": "Not found"
            })
            print(f"❌ Not found: {title_full}")

        time.sleep(1)  # Prevent rate limiting

    result_df = pd.DataFrame(results)
    result_df.to_csv("libby_search_results.csv", index=False)
    print("\n✅ Search complete! Results exported to libby_search_results.csv")
    return result_df

# ========== 执行 ==========
if __name__ == "__main__":
    # First do probe to verify fields
    #debug_probe("Tell Me What You Did", author="Carter Wilson", limit=10)
    #debug_probe("Welcome to the Hyunam-Dong Bookshop", author="Hwang Bo-Reum", limit=10)

    # Then run your original batch process
    search_books_in_libby("goodreads_library_export.csv")

