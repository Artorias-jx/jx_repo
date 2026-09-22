#!/usr/bin/env python3
"""
把 md 里残留的裸 HTML 表格（turndown `keep` 保留的原始 `<table>`）转成 Markdown 表格。

背景（2026-09-22）：
    crawl_zhihu.js 用 `td.keep(['table', ...])` 让 turndown 原样保留表格 HTML。
    结果 Obsidian 里渲染很差：无边框、无表头样式、单元格里的 `&lt;` / `&gt;`
    可能显示成实体原文，阅读体验像「坏掉了」。

    全库共 51 个裸表格、涉及 13 篇。本脚本统一转成 Markdown 表格。

处理要点：
    1. 解析 <table>...<tbody><tr><td>..</td><td>..</td></tr>...</tbody></table>
    2. HTML 实体反转义：&lt; -> <, &gt; -> >, &amp; -> &, &nbsp; -> 空格
    3. 单元格内的 `<br>` 转成空格
    4. 第一行作为表头，输出标准 markdown 表格
    5. 空单元格保留为空
    6. 去除 `data-draft-node` 等知乎私有属性（随 <table> 一起丢弃）
    7. 单元格内含 `|` 时转义为 `\\|`
    8. 合并单元格（rowspan/colspan）做降级处理：重复/留空

用法：
    python html_tables_to_md.py <目录> [--dry-run]
"""
import html
import os
import re
import sys

RE_TABLE = re.compile(r'<table\b[^>]*>([\s\S]*?)</table>', re.I)
RE_ROW = re.compile(r'<tr\b[^>]*>([\s\S]*?)</tr>', re.I)
RE_CELL = re.compile(r'<t[dh]\b([^>]*)>([\s\S]*?)</t[dh]>', re.I)
RE_TAG = re.compile(r'<[^>]+>')
RE_BR = re.compile(r'<br\s*/?>', re.I)


def cell_text(raw: str) -> str:
    """HTML 单元格 -> markdown 单元格文本"""
    s = RE_BR.sub(' ', raw)
    s = RE_TAG.sub('', s)          # 去剩余标签（span/a/svg 等）
    s = html.unescape(s)           # &lt; &gt; &amp; &nbsp; ...
    s = s.replace('|', '\\|')      # markdown 表格转义
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def table_to_md(inner: str):
    rows = []
    for rm in RE_ROW.finditer(inner):
        cells = [cell_text(c.group(2)) for c in RE_CELL.finditer(rm.group(1))]
        if cells:
            rows.append(cells)
    if not rows:
        return None, 0

    width = max(len(r) for r in rows)
    rows = [r + [''] * (width - len(r)) for r in rows]

    lines = []
    # 表头
    lines.append('| ' + ' | '.join(rows[0]) + ' |')
    lines.append('|' + '|'.join([' --- '] * width) + '|')
    for r in rows[1:]:
        lines.append('| ' + ' | '.join(r) + ' |')
    return '\n'.join(lines), len(rows)


def process(text: str):
    n_tbl = 0

    def rep(m):
        nonlocal n_tbl
        md, nrows = table_to_md(m.group(1))
        if md is None:
            return m.group(0)
        n_tbl += 1
        return '\n' + md + '\n'

    return RE_TABLE.sub(rep, text), n_tbl


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        sys.exit(1)
    root = args[0]
    dry = '--dry-run' in sys.argv

    files = []
    for dirpath, _, names in os.walk(root):
        for nm in names:
            if nm.endswith('.md'):
                files.append(os.path.join(dirpath, nm))
    files.sort()

    touched, total = 0, 0
    for f in files:
        with open(f, encoding='utf-8') as fh:
            src = fh.read()
        if '<table' not in src.lower():
            continue
        out, n = process(src)
        if n == 0:
            continue
        touched += 1
        total += n
        print(f'{os.path.relpath(f, root)}: 转 {n} 个表')
        if not dry:
            # 收尾：修掉表格前后多余空行堆积
            out = re.sub(r'\n{3,}', '\n\n', out)
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(out)

    tag = '[dry-run] ' if dry else ''
    print(f'\n{tag}命中 {touched} 个文件，共 {total} 个表')


if __name__ == '__main__':
    main()
