# GB-Libby

本项目用于批量查询 Goodreads 导出的书单在 Libby（OverDrive）图书馆的可借情况，并导出结果到 CSV 文件。

## 功能简介

- 支持读取 Goodreads 导出的 CSV 文件（只处理 `Exclusive Shelf` 为 `to-read` 的书）。
- 自动处理书名格式（去除括号和冒号后的系列号/副标题）。
- 精准匹配书名和作者，支持模糊作者匹配。
- 查询每本书在 Libby 图书馆的电子书和有声书可借情况。
- 综合判断可借状态（可立即借阅/不可借/等待x周），并支持 Lucky Day 副本。
- 导出结果为 CSV，包含：书名（含作者）、Availability（有/没有）、MediaType（电子书/有声书）、等待情况。

## 使用方法

1. 准备好 Goodreads 导出的 CSV 文件，命名为 `goodreads_export.csv`，放在项目根目录。
2. 安装依赖：
   ```bash
   pip install pandas requests
   ```
3. 运行主程序：
   ```bash
   python test.py
   ```
4. 查询结果会自动导出到 `libby_search_results.csv`。

## 字段说明

- **Title**：书名（含作者）
- **Availability**：有/没有（是否可借）
- **MediaType**：电子书/有声书
- **等待情况**：可立即借阅/不可借/等待约x周

## 适用场景

- 批量查询你的待读书单在 Libby 图书馆的借阅情况。
- 快速筛选哪些书可以直接借阅，哪些需要等待。

---

如需进一步定制 README 内容，请告诉我你的具体需求！
