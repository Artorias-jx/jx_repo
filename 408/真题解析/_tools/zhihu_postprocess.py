#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知乎408真题解析剪藏后处理（图片保留外链版）

默认行为（用户 2026-09-22 拍板「改成链接图片」）：
  - 图片保持知乎图床外链 ![](https://xx.zhimg.com/...) 不动
  - 只清理知乎站内跳转污染：
      [文本](https://zhida.zhihu.com/search?...)  ->  文本
      [文本](https://link.zhihu.com/?target=URL编码)  ->  [文本](真实URL)

可选行为：
  --download-images : 把图床图片下载到同级 assets/ 并改成本地引用 ![[...]]
                      （默认关闭；用户当前要求保留外链）

用法:
  单文件: python zhihu_postprocess.py <md文件路径> [--dry-run] [--download-images] [--no-backup]
  整个目录: python zhihu_postprocess.py <目录> --all [--dry-run]
"""
import os
import re
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REFERER = "https://zhuanlan.zhihu.com/"

# markdown 图片：![alt](url) 与 ![alt](url "title")
RE_MD_IMG = re.compile(r'!\[([^\]]*)\]\((https?://[^)\s]+?)(?:\s+"[^"]*")?\)')
# 知乎站内跳转链接 [文本](https://zhida.zhihu.com/search?...)
RE_ZHIDA_LINK = re.compile(r'\[([^\]]+)\]\(https://zhida\.zhihu\.com/[^)]+\)')
# 站外跳转 [文本](https://link.zhihu.com/?target=<urlencoded>)
RE_LINK_JUMP = re.compile(r'\[([^\]]+)\]\(https://link\.zhihu\.com/\?target=([^)&]+)[^)]*\)')


def guess_ext(url: str, content_type: str = "") -> str:
    if "webp" in url:
        return ".webp"
    if "png" in url:
        return ".png"
    if "gif" in url:
        return ".gif"
    if "jpeg" in url or "jpg" in url:
        return ".jpg"
    if "image/png" in content_type:
        return ".png"
    if "image/webp" in content_type:
        return ".webp"
    if "image/gif" in content_type:
        return ".gif"
    return ".jpg"


def download(url: str, dest: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": REFERER,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        ct = r.headers.get("Content-Type", "")
    with open(dest, "wb") as f:
        f.write(data)
    return len(data), ct


def clean_links(text: str):
    """清理知乎跳转污染，返回 (新文本, zhida数, link_jump数)"""
    n1 = len(RE_ZHIDA_LINK.findall(text))
    text = RE_ZHIDA_LINK.sub(r'\1', text)

    n2 = len(RE_LINK_JUMP.findall(text))

    def jump_repl(m):
        label, enc = m.group(1), m.group(2)
        try:
            real = urllib.parse.unquote(enc)
        except Exception:
            real = enc
        return f"[{label}]({real})"

    text = RE_LINK_JUMP.sub(jump_repl, text)
    return text, n1, n2


def download_images(md_path: str, text: str, prefix: str, dry_run: bool):
    """把图床外链下载到 assets/，返回 (新文本, mapping, ok, fail, total)"""
    md_dir = os.path.dirname(md_path)
    assets_dir = os.path.join(md_dir, "assets")

    urls, seen = [], set()
    for mm in RE_MD_IMG.finditer(text):
        u = mm.group(2)
        if "zhimg.com" in u and u not in seen:
            seen.add(u)
            urls.append(u)

    mapping = {}
    ok = fail = 0
    if not urls:
        return text, mapping, ok, fail, 0

    if not dry_run:
        os.makedirs(assets_dir, exist_ok=True)

    for i, u in enumerate(urls, 1):
        u_orig = re.sub(r'_(?:1440w|720w|1080w|414w|qhd|r)\.(jpg|jpeg|png|webp|gif)$', r'.\1', u)
        fname = f"{prefix}_{i:02d}{guess_ext(u_orig)}"
        rel = f"assets/{fname}"
        if dry_run:
            print(f"[DRY] {u_orig[:78]}... -> {fname}")
            mapping[u] = rel
            continue
        try:
            size, ct = download(u_orig, os.path.join(assets_dir, fname))
            if size < 500:
                fname2 = f"{prefix}_{i:02d}{guess_ext(u_orig, ct)}"
                os.replace(os.path.join(assets_dir, fname), os.path.join(assets_dir, fname2))
                rel = f"assets/{fname2}"
            mapping[u] = rel
            ok += 1
            print(f"[OK ] {i:02d} {size:>8} B  {rel}")
        except Exception as e:
            fail += 1
            print(f"[FAIL] {i:02d} {u_orig[:66]} -> {e}")

    def repl(m):
        if m.group(2) in mapping:
            return f"![[{mapping[m.group(2)]}]]"
        return m.group(0)

    return RE_MD_IMG.sub(repl, text), mapping, ok, fail, len(urls)


def process_one(md_path, dry_run, do_backup, dl_images):
    md_dir = os.path.dirname(md_path)
    base = os.path.splitext(os.path.basename(md_path))[0]
    m = re.match(r'(\d{4})', base)
    year = m.group(1) if m else "0000"
    subj = re.sub(r'^\d{4}年408真题', '', base)
    prefix = f"{year}_{subj}"

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"文件: {base}.md")
    orig = text

    # 1. 图片处理（默认不下载，保留外链）
    n_img = len(RE_MD_IMG.findall(text))
    if dl_images:
        print(f"图片外链: {n_img} 张 -> 下载到本地 assets/")
        print("-" * 60)
        text, _, ok, fail, tot = download_images(md_path, text, prefix, dry_run)
        print("-" * 60)
        print(f"图片下载: 成功 {ok} / 失败 {fail} / 共 {tot} 张")
    else:
        print(f"图片外链: {n_img} 张 -> 保留外链，不下载")

    # 2. 清理跳转污染
    text2, n1, n2 = clean_links(text)
    print(f"清理跳转: {n1} 处 zhida.zhihu.com、{n2} 处 link.zhihu.com")

    # 3. 写回
    if dry_run:
        print("[DRY] 不写文件")
    elif text2 != orig:
        if do_backup:
            import shutil
            bak_dir = os.path.join(md_dir, "_tools", "_bak")
            os.makedirs(bak_dir, exist_ok=True)
            shutil.copy2(md_path, os.path.join(bak_dir, os.path.basename(md_path)))
            print(f"[备份] _tools/_bak/{os.path.basename(md_path)}")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text2)
        print("[写入] 已更新")
    else:
        print("[跳过] 内容无变化")

    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        sys.exit(1)

    target = os.path.abspath(args[0])
    dry_run = "--dry-run" in flags
    do_backup = "--no-backup" not in flags
    dl_images = "--download-images" in flags
    all_mode = "--all" in flags

    if not dl_images:
        print("模式: 保留图片外链（如需本地化请加 --download-images）\n")

    if all_mode:
        if not os.path.isdir(target):
            print(f"[ERROR] --all 需要传入目录: {target}")
            sys.exit(1)
        mds = sorted(os.path.join(target, f) for f in os.listdir(target)
                     if f.endswith(".md") and not f.startswith("_"))
        if not mds:
            print(f"[INFO] 目录下没有待处理 md: {target}")
            return 0
        print(f"批量模式: 共 {len(mds)} 篇\n" + "=" * 60)
        for p in mds:
            process_one(p, dry_run, do_backup, dl_images)
            print("=" * 60)
        return 0

    if not os.path.isfile(target):
        print(f"[ERROR] 文件不存在: {target}")
        sys.exit(1)
    return process_one(target, dry_run, do_backup, dl_images)


if __name__ == "__main__":
    sys.exit(main())
