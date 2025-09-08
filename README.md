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

## 字段说明

- **Title**: Book title (with author)
- **Availability**: Found/Not found (whether the book is available in the library)
- **MediaType**: Ebook/Audiobook
- **WaitStatus**: Available now / Not borrowable / Wait about x weeks

## 适用场景

- 批量查询你的待读书单在 Libby 图书馆的借阅情况。
- 快速筛选哪些书可以直接借阅，哪些需要等待。

---
