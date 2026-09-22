#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理 408 真题解析 md：
  1. 删除 frontmatter 里的 description 字段
  2. 删除正文里「第XX~40小题...最符合题目要求的。」这句（单选题说明）

用法:
  python strip_boilerplate.py <md文件> [--dry-run]
  python strip_boilerplate.py <目录> --all [--dry-run]
"""
import os
import re
import sys

# 单选题说明句：以「第...~40小题」开头，以「最符合题目要求的。」结尾
# 兼容 3 种变体：第01~40小题 / 第 1~40 小题 / 第1~40小题，空格可有可无
RE_SINGLE_CHOICE_NOTE = re.compile(
    r'^第\s*\d+\s*~\s*40\s*小题[^\n]*最符合题目要求的。\s*$',
    re.M
)

# frontmatter 里的 description 行（可能多行缩进续行）
RE_DESC_LINE = re.compile(r'^description:.*$', re.M)


def process_one(md_path, dry_run):
    with open(md_path, 'r', encoding='utf-8') as f:
        text = f.read()
    orig = text
    report = []

    # ---- 1. frontmatter description ----
    # 只处理文件开头的 --- ... --- 块
    fm_match = re.match(r'^---\r?\n([\s\S]*?)\r?\n---\r?\n', text)
    if fm_match:
        fm = fm_match.group(1)
        new_fm = fm
        n_desc = 0
        # 逐行过滤，同时去掉紧随其后的缩进续行
        lines = fm.split('\n')
        out_lines = []
        skip_cont = False
        for ln in lines:
            if skip_cont and (ln.startswith('  ') or ln.startswith('\t')):
                continue
            skip_cont = False
            if re.match(r'^description:', ln):
                n_desc += 1
                skip_cont = True
                continue
            out_lines.append(ln)
        new_fm = '\n'.join(out_lines)
        if n_desc:
            text = text[:fm_match.start(1)] + new_fm + text[fm_match.end(1):]
            report.append(f'删 description 字段 x{n_desc}')

    # ---- 2. 单选题说明句 ----
    n_note = len(RE_SINGLE_CHOICE_NOTE.findall(text))
    if n_note:
        text = RE_SINGLE_CHOICE_NOTE.sub('', text)
        report.append(f'删单选题说明句 x{n_note}')

    # ---- 3. 收尾：清理多余空行 ----
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 标题后紧跟空行再空行的情况
    text = re.sub(r'(## 一、单项选择题)\n\n\n+', r'\1\n\n', text)
    # 确保文件末尾单换行
    text = text.rstrip('\n') + '\n'

    if text == orig:
        print(f'  [跳过] {os.path.basename(md_path)}: 无需改动')
        return 0

    if dry_run:
        print(f'  [DRY] {os.path.basename(md_path)}: {", ".join(report)}')
        return 0

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'  [OK ] {os.path.basename(md_path)}: {", ".join(report)}')
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    if not args:
        print(__doc__)
        sys.exit(1)

    target = os.path.abspath(args[0])
    dry_run = '--dry-run' in flags

    if '--all' in flags:
        if not os.path.isdir(target):
            print(f'[ERROR] 需要目录: {target}')
            sys.exit(1)
        mds = []
        for root, dirs, files in os.walk(target):
            for f in files:
                if f.endswith('.md'):
                    mds.append(os.path.join(root, f))
        mds.sort()
        print(f'批量处理 {len(mds)} 篇{"（dry-run）" if dry_run else ""}')
        for p in mds:
            process_one(p, dry_run)
        return 0

    if not os.path.isfile(target):
        print(f'[ERROR] 文件不存在: {target}')
        sys.exit(1)
    return process_one(target, dry_run)


if __name__ == '__main__':
    sys.exit(main())
