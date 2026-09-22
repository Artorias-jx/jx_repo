#!/usr/bin/env python3
"""
清理「多行块公式」末尾多余的 LaTeX 换行标记 `\\`。

这些 `\\` 是知乎原文里作者多写的（不构成 LaTeX 环境，仅尾部多余），
在 Obsidian 里会让公式多渲染一个空行。

只处理：块公式 **不含 \\begin{...} 环境** 且 **以 \\ 结尾** 的情况。
含环境的多行公式（array/aligned/matrix 等）末尾的 `\\` 是必要的，不动。

用法：
    python trim_blockmath_backslashes.py <目录> [--dry-run]
"""
import os
import re
import sys

# 匹配 \n\n$$ ... $$\n\n，贪婪范围限制在最短
RE_BLOCK = re.compile(r'\n\n\$\$([\s\S]*?)\$\$\n\n')
RE_ENV = re.compile(r'\\begin\{')
RE_TRAIL = re.compile(r'\\{2}\s*$')          # 结尾是字面 \ \
RE_TRAIL_SUB = re.compile(r'\\{1,2}\s*$')    # 去掉结尾 1~2 个反斜杠


def process(text: str):
    n = 0

    def rep(m):
        nonlocal n
        body = m.group(1)
        if RE_ENV.search(body):
            return m.group(0)
        if not RE_TRAIL.search(body):
            return m.group(0)
        n += 1
        return '\n\n$$' + RE_TRAIL_SUB.sub('', body).rstrip() + '$$\n\n'

    return RE_BLOCK.sub(rep, text), n


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
        print(f'{os.path.relpath(f, root)}: 清 {n} 处')
        if not dry:
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(out)

    tag = '[dry-run] ' if dry else ''
    print(f'\n{tag}命中 {touched} 个文件，共 {total} 处')


if __name__ == '__main__':
    main()
