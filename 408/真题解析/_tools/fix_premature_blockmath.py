#!/usr/bin/env python3
"""
修复「本该是行内公式、却被误提为独立块公式」导致句子被劈开的问题。

背景（2026-09-22）：
    crawl_zhihu.js 的 isBlockMath 原判据含「含 \\ 即为块公式」，
    但知乎作者常在**行内**公式末尾多写一个 \\（LaTeX 残留），
    于是「根据贪心策略，若 G 一定连通，则需要 [公式] 即先分成…」
    被劈成三段：
        xxx则需要
        <空行>
        $$公式\\$$
        <空行>
        即先分成…

识别特征（三个条件同时满足才修）：
    1. 块公式体内**没有** \\begin{...} 环境（array/aligned/matrix/...）
    2. 公式体以 \\ 结尾
    3. 该块公式**紧跟在中文句子后面**（前一行不以标点/空行结束），
       或**紧跟其后的行以中文续写**（形如「 即…」）

处理：
    - 去掉公式末尾的 \\
    - 把 $$…$$ 降级为 $…$
    - 合并被劈开的三段为一行

用法：
    python fix_premature_blockmath.py <目录> [--dry-run]
"""
import os
import re
import sys

RE_BLOCK = re.compile(r'\n\n\$\$([\s\S]*?)\$\$\n\n')
RE_ENV = re.compile(r'\\begin\{')
# 前一行需以这些字符结尾，才算「句子被劈开」
ENDS_SENTENCE = tuple('。，、；：,;:') + ('（', '(', '「', '『')
# 上一行以这些词收尾 → 是「引出公式」的正常写法，不算被劈开
TAIL_WORDS = ('得', '为', '有', '是', '即', '则', '：', ':')


def looks_broken(before: str, body: str, after: str) -> bool:
    """判断这个块公式是否被误提。"""
    # 条件 1：体内无环境
    if RE_ENV.search(body):
        return False
    # 条件 2：以 \\ 结尾
    if not re.search(r'\\\\\s*$', body):
        return False
    # 条件 3：前后是中文续写
    prev_line = before.rstrip('\n').split('\n')[-1].strip()
    next_line = after.lstrip('\n').split('\n')[0].strip() if after.strip() else ''
    if not prev_line or not next_line:
        return False
    # 前一行以句末标点收尾 → 话已说完，正常块公式
    if prev_line.endswith(ENDS_SENTENCE):
        return False
    # 前一行以「得 / 为 / 有 / 是 / 即」等引出词收尾 → 是正常写法，别动
    if prev_line.endswith(TAIL_WORDS):
        return False
    # 后一行必须以中文/数字续写（形如「 即先分成…」）
    if not re.match(r'^[\u4e00-\u9fff\w]', next_line):
        return False
    return True


def fix(text: str):
    n = 0
    pos = 0
    while True:
        m = RE_BLOCK.search(text, pos)
        if not m:
            break
        body = m.group(1)
        before = text[:m.start()]
        after = text[m.end():]
        if looks_broken(before, body, after):
            tex = re.sub(r'\\\\\s*$', '', body).strip()
            prev_line = before.rstrip('\n').split('\n')[-1]
            next_rest = after.lstrip('\n')
            # 合并：前一行 + 行内公式 + 后一行（去掉后一行开头的空格）
            merged = prev_line.rstrip() + ' $' + tex + '$ ' + next_rest.lstrip()
            # 保留前一行之前的空行结构
            head = before[:len(before) - len(prev_line)]
            text = head.rstrip('\n') + '\n\n' + merged if head.strip() == '' else head + merged
            n += 1
            pos = len(head)
        else:
            pos = m.end()
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
        out, n = fix(src)
        if n == 0:
            continue
        touched += 1
        total += n
        print(f'{os.path.relpath(f, root)}: 修 {n} 处')
        if not dry:
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(out)

    tag = '[dry-run] ' if dry else ''
    print(f'\n{tag}命中 {touched} 个文件，共 {total} 处')


if __name__ == '__main__':
    main()
