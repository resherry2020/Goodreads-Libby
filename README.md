# Goodreads-Libby

This project allows you to batch query the availability of books exported from Goodreads in your Libby (OverDrive) library, and export the results to a CSV file.


## Features

- Reads Goodreads exported CSV file (only processes books with `Exclusive Shelf` set to `to-read`).
- Automatically normalizes book titles (removes series info/subtitles after parentheses or colons).
- Accurate matching of book title and author, supports fuzzy author matching.
- Queries both eBook and Audiobook availability for each book in Libby.
- Comprehensive availability judgment (Found/Not found), with wait time estimation.
- Exports results to CSV, including: Title (with author), Availability (Found/Not found), MediaType (Ebook/Audiobook), WaitStatus.

## Usage

1. Prepare your Goodreads exported CSV file, name it `goodreads_library_export.csv`, and place it in the project root.
2. Install dependencies:
   ```bash
   pip install pandas requests
   ```
3. Run the main program:
   ```bash
   python test.py
   ```
4. The results will be exported to `libby_search_results.csv`.

**Note:**

- The default `LIBRARY_ID` is set to Adelaide Library (`sapln-adelaide`). If you are using a different library, please change the `LIBRARY_ID` variable in `test.py` to your own library's ID.


## How to Find Your Libby Library ID

1. Open and log in to your Libby account in a desktop browser:
   https://libbyapp.com/
2. Open Developer Tools:
   - Windows: Ctrl + Shift + I
   - Mac: Cmd + Opt + I
   - Go to the **Network** panel and check **Preserve log**.
3. Search for a book you know your library owns (e.g., "Harry Potter").
4. Wait for results to load. In the Network panel, find a request with a URL like:
   ```
   https://thunder.api.overdrive.com/v2/libraries/sapln-adelaide/media?query=Bat%20Eater&...
   ```
   The part after `/libraries/` (e.g., `sapln-adelaide`) is your library ID.

## How to Export Your Goodreads Library

1. Log in to Goodreads on the web.
2. Go to **My Books** → **Tools** → **Import and export** → **Export Library**.
3. Download the exported CSV file.

## Field Description

- **Title**: Book title (with author)
- **Availability**: Found/Not found (whether the book is available in the library)
- **MediaType**: Ebook/Audiobook
- **WaitStatus**: Available now / Not borrowable / Wait about x weeks

## Use Cases

- Batch query the borrowing status of your to-read list in Libby.
- Quickly filter which books are available to borrow and which require waiting.

---

# Goodreads-Libby

本项目用于批量查询 Goodreads 导出的书单在 Libby（OverDrive）图书馆的可借情况，并导出结果到 CSV 文件。


## 功能简介

- 支持读取 Goodreads 导出的 CSV 文件（只处理 `Exclusive Shelf` 为 `to-read` 的书）。
- 自动处理书名格式（去除括号和冒号后的系列号/副标题）。
- 精准匹配书名和作者，支持模糊作者匹配。
- 查询每本书在 Libby 图书馆的电子书和有声书可借情况。
- 综合判断可借状态（Found/Not found），并估算等待时间。
- 导出结果为 CSV，包含：书名（含作者）、Availability（Found/Not found）、MediaType（电子书/有声书）、等待情况。

## 使用方法

1. 准备好 Goodreads 导出的 CSV 文件，命名为 `goodreads_library_export.csv`，放在项目根目录。
2. 安装依赖：
   ```bash
   pip install pandas requests
   ```
3. 运行主程序：
   ```bash
   python test.py
   ```
4. 查询结果会自动导出到 `libby_search_results.csv`。

**注意：**

- 默认的 `LIBRARY_ID` 是阿德莱德图书馆（`sapln-adelaide`）。如果你使用的是其他图书馆，请在 `test.py` 文件中将 `LIBRARY_ID` 修改为你所在图书馆的 ID。


## 如何获取你的 Libby 图书馆 ID

步骤 1：在电脑浏览器中打开并登录你的 Libby 账户
https://libbyapp.com/

步骤 2：打开开发者工具

- Windows: Ctrl + Shift + I
- Mac: Cmd + Opt + I
- 选择 Network 面板，勾选 Preserve log。

步骤 3：搜索一本你确定图书馆有的书（如 Harry Potter）。

步骤 4：等待加载结果，在 Network 面板的 header 里找到 Request URL，例如：

```
https://thunder.api.overdrive.com/v2/libraries/sapln-adelaide/media?query=Bat%20Eater&...
```

其中 `/libraries/` 后面的部分（如 `sapln-adelaide`）就是你的图书馆 ID。

## 如何导出自己的 Goodreads 收藏清单

1. 登录网页版 Goodreads。
2. 进入 **My Books** → **Tools** → **Import and export** → **Export Library**。
3. 下载导出的 CSV 文件。

## 字段说明

- **Title**：书名（含作者）
- **Availability**：Found/Not found（是否在图书馆可借）
- **MediaType**：电子书/有声书
- **等待情况**：可立即借阅/不可借/等待约 x 周

## 适用场景

- 批量查询你的待读书单在 Libby 图书馆的借阅情况。
- 快速筛选哪些书可以直接借阅，哪些需要等待。

---
