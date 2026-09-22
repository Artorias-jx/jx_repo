#!/usr/bin/env python3
"""
清理已抓 md 中残留的知乎跳转污染（含 td.keep 保留的原始 HTML 表格内的 <a> 链接）

背景：crawl_zhihu.js 的 cleanLinks 原只处理 markdown 格式 [label](url)，
但表格是 turndown keep 保留的原始 HTML，里面的 <a href="zhida.zhihu.com/...">
不会被命中。本脚本补这一刀。

用法：
    python patch_html_links.py <目录> [--dry-run]
"""
import os
import re
import sys
from urllib.parse import unquote

RE_SVG = re.compile(r'<svg[\s\S]*?</svg>')

# HTML 版：<a ... href="https://zhida.zhihu.com/...">内嵌内容</a> -> 纯文字
RE_HTML_ZHIDA = re.compile(
    r'<a\b[^>]*href="https://zhida\.zhihu\.com/[^"]*"[^>]*>([\s\S]*?)</a>')
# HTML 版：link.zhihu.com 包装 -> 还原真实目标
RE_HTML_LINK = re.compile(
    r'<a\b[^>]*href="https://link\.zhihu\.com/\?target=([^&"]+)[^"]*"[^>]*>([\s\S]*?)</a>')

# markdown 版兜底
RE_MD_ZHIDA = re.compile(r'\[([^\]]+)\]\(https://zhida\.zhihu\.com/[^)]+\)')
RE_MD_LINK = re.compile(
    r'\[([^\]]+)\]\(https://link\.zhihu\.com/\?target=([^)&]+)[^)]*\)')


def _plain(inner: str) -> str:
    return RE_SVG.sub('', inner).strip()


def clean(text: str):
    n = 0

    def sub_html_zhida(m):
        nonlocal n
        n += 1
        return _plain(m.group(1))

    def sub_html_link(m):
        nonlocal n
        n += 1
        return f'[{_plain(m.group(2))}]({unquote(m.group(1))})'

    def sub_md_zhida(m):
        nonlocal n
        n += 1
        return m.group(1)

    def sub_md_link(m):
        nonlocal n
        n += 1
        return f'[{m.group(1)}]({unquote(m.group(2))})'

    text = RE_HTML_ZHIDA.sub(sub_html_zhida, text)
    text = RE_HTML_LINK.sub(sub_html_link, text)
    text = RE_MD_ZHIDA.sub(sub_md_zhida, text)
    text = RE_MD_LINK.sub(sub_md_link, text)
    # 残留的空 span
    text = re.sub(r'<span>\s*</span>', '', text)
    return text, n


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
        out, n = clean(src)
        if n == 0:
            continue
        touched += 1
        total += n
        print(f'{os.path.relpath(f, root)}: 清理 {n} 处')
        if not dry:
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(out)

    tag = '[dry-run] ' if dry else ''
    print(f'\n{tag}命中 {touched} 个文件，共 {total} 处')


if __name__ == '__main__':
    main()
