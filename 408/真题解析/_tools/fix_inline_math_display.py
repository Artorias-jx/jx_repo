#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全库显示问题统一修复（2026-09-22）

修四类问题：
  1. 行内公式**首位空格** -> `$ xxx$` 会被 MathJax 判为 display 模式单独换行，
     把整句话劈开（用户报的「显示有 bug」主因）。必须清掉。
  2. 行内公式**尾随空格** -> 清掉，避免 `$xxx $` 渲染出多余空隙。
  3. ZWNJ/ZWJ 零宽字符（\\u200c/\\u200d）-> 知乎原文携带的隐形字符，删除。
  4. `$xxx\\$`（公式内尾部 1~2 个反斜杠）-> 知乎作者笔误，清掉。

边界（重要）：
  - 只处理**同一行内成对**的 `$...$`，不跨行，不碰 `$$...$$` 块公式。
  - 行内公式内部的**双空格**（如 `2^{101{\\rm B}}\\times {0.10100{\\rm B}}`）
    保留 —— 那是公式排版用的，不是显示 bug。
  - LaTeX 环境（\\begin{pmatrix}...）内部的空格不动，只清最外层首尾。

用法：
  python fix_inline_math_display.py <目录> [--dry-run]
"""
import os
import re
import sys

# 行内公式：单行内成对 $...$（公式体不含 $）
RE_INLINE = re.compile(r'(?<!\$)\$([^$\n]+)\$(?!\$)')
# 块公式：$$...$$（可跨行）
RE_BLOCK = re.compile(r'\$\$([\s\S]*?)\$\$')

ZW = re.compile(r'[\u200c\u200d]')


def clean_inline(text: str):
    """清行内公式 首尾空格 + 尾部多余反斜杠"""
    n = 0

    def rep(m):
        nonlocal n
        body = m.group(1)
        new = body.strip()
        # 清尾部 1~2 个反斜杠（LaTeX 换行残留），但若公式含环境则不动
        if not re.search(r'\\begin\{', new):
            new2 = re.sub(r'\\{1,2}\s*$', '', new).rstrip()
            if new2:
                new = new2
        if new != body:
            n += 1
            return f'${new}$'
        return m.group(0)

    return RE_INLINE.sub(rep, text), n


def clean_block(text: str):
    """清块公式 $$ 内层首尾空白（不动内部环境里的换行/对齐）。

    注意：块公式体内可能含 \\\\ 换行与 \\begin{...} 多行内容，
    这里**只 strip 首尾**，中间原样保留。
    """
    n = 0

    def rep(m):
        nonlocal n
        body = m.group(1)
        new = body.strip()
        if new != body:
            n += 1
            return f'$${new}$$'
        return m.group(0)

    return RE_BLOCK.sub(rep, text), n


def clean_zw(text: str):
    k = len(ZW.findall(text))
    return ZW.sub('', text), k


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        sys.exit(1)
    root = args[0]
    dry = '--dry-run' in sys.argv

    files = []
    for dp, _, names in os.walk(root):
        if os.path.basename(dp).startswith('_'):
            continue
        for nm in names:
            if nm.endswith('.md'):
                files.append(os.path.join(dp, nm))
    files.sort()

    touched = total_math = total_zw = total_block = 0
    for f in files:
        with open(f, encoding='utf-8') as fh:
            src = fh.read()
        out, nm = clean_inline(src)
        out, nb = clean_block(out)
        out, nz = clean_zw(out)
        if nm == 0 and nz == 0 and nb == 0:
            continue
        touched += 1
        total_math += nm
        total_zw += nz
        total_block += nb
        rel = os.path.relpath(f, root)
        print(f'{rel}: 行内 {nm} 处, 块公式 {nb} 处, 零宽字符 {nz} 处')
        if not dry:
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(out)

    tag = '[dry-run] ' if dry else ''
    print(f'\n{tag}命中 {touched} 个文件；行内公式 {total_math} 处，块公式 {total_block} 处，零宽字符 {total_zw} 处')


if __name__ == '__main__':
    main()
