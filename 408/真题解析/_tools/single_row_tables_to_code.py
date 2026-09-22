#!/usr/bin/env python3
"""
把「只有表头、无数据行」的单行表格转成 ASCII 结构框代码块。

背景（2026-09-22）：
    知乎作者常用**单行表格**画「结构示意框」，例如地址字段划分：
        | 页号（10位） | 页内偏移量（22位） |
    或结构体定义：
        | data | firstedge |
    这类表在 Markdown 里渲染成「表头 + 空行」，观感像坏掉了。

    原文意图就是画框，故转成等宽代码块更还原、更清晰。

用法：
    python single_row_tables_to_code.py <目录> [--dry-run]
"""
import os
import re
import sys

# 连续 markdown 表格行
RE_TABLE_BLOCK = re.compile(r'((?:^\|.*\|[ \t]*\n)+)', re.M)
RE_SEP = re.compile(r'^\|[\s\-:|]+\|$')


def build_box(cells):
    """把单元格列表画成 ASCII 框"""
    w = [max(len(c), 3) for c in cells]
    top = '┌' + '┬'.join('─' * (x + 2) for x in w) + '┐'
    mid = '│' + '│'.join(' ' + c.ljust(x) + ' ' for c, x in zip(cells, w)) + '│'
    bot = '└' + '┴'.join('─' * (x + 2) for x in w) + '┘'
    return '\n'.join([top, mid, bot])


def process(text: str):
    n = 0

    def rep(m):
        nonlocal n
        lines = [l for l in m.group(1).strip().split('\n') if l.strip()]
        if len(lines) != 2 or not RE_SEP.match(lines[1].strip()):
            return m.group(0)
        # 解析表头单元格（空单元格保留为空）
        cells = [c.strip() for c in lines[0].strip().strip('|').split('|')]
        n += 1
        return '\n```\n' + build_box(cells) + '\n```\n'

    return RE_TABLE_BLOCK.sub(rep, text), n


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
        out, n = process(src)
        if n == 0:
            continue
        touched += 1
        total += n
        print(f'{os.path.relpath(f, root)}: 转 {n} 个结构框')
        if not dry:
            out = re.sub(r'\n{3,}', '\n\n', out)
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(out)

    tag = '[dry-run] ' if dry else ''
    print(f'\n{tag}命中 {touched} 个文件，共 {total} 个')


if __name__ == '__main__':
    main()
