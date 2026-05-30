# Git 大文件导致 push 被拒与附件管理方案

## 问题现象

执行 `git push` 时，远程仓库返回错误：

```
remote: error: File Attachment/Yoken怀古_计网思维导图Xmind版本可修改.xmind is 136.18 MB; this exceeds GitHub's file size limit of 100.00 MB
remote: error: GH001: Large files detected.
```

同时 git status 显示大量 `.doc`/`.xmind`/`.pdf` 等二进制文件被追踪。

## 原因分析

### 直接原因

`Attachment/` 文件夹存放了大量大体积的二进制附件（doc、xmind、pdf），有的超过 100MB。GitHub 对单个文件有 **100MB 的硬限制**，超过会直接拒绝推送。

### 深层原因

这两个提交包含了这个大文件：

| 提交 | 内容 |
|------|------|
| `b6b12a0` | 新增 Attachment/* 大文件 + 数学笔记 |
| `09e5074` | 添加 .gitignore 并删除 Attachment 文件 |

即使第二个提交删除了大文件，**GitHub 仍然拒绝推送**，因为 Git 的历史记录里保留着大文件的 blob 对象。GitHub 的 pre-receive hook 会检查所有被推送提交的完整历史，**只要某个提交的树对象中包含大文件，就会被拒**。

## 解决方案

### 第一步：清理历史记录

不能简单地"加一个新提交来删除大文件"，必须**重写提交历史**，让大文件从未出现在任何提交中。

```bash
# 1. 回退到远程同步点，保留工作区文件
git reset origin/main

# 2. 谨慎选择要提交的内容，只 git add 需要的文件
git add .gitignore
git add "数学/定积分的反三角复合与对称性.md"

# 3. 提交并推送
git commit -m "提交说明"
git push
```

> [!warning] `git reset` 的三种模式
> - `--soft`：只移动 HEAD，所有更改保留在暂存区
> - `--mixed`（默认）：移动 HEAD，更改保留在工作区但不暂存
> - `--hard`：**危险**！丢弃所有更改，慎用

### 第二步：配置 .gitignore

将 `Attachment/` 加入 `.gitignore`，让 git 彻底忽略该目录：

```
Attachment/
```

同时需要移除已被追踪的 Attachment 文件：

```bash
git rm -r --cached Attachment/
```

`--cached` 表示只从 git 的索引中移除，**不会删除磁盘上的文件**。

### 第三步：处理"已推送"的情况

如果大文件已经被推送到远程仓库（虽然本例未发生），需要用 `git filter-branch` 或 `git filter-repo` 从整个历史中删除大文件，然后 `git push --force`。**强制推送会破坏协作者的历史，需谨慎。**

## 教训与最佳实践

### 1. 不要跟踪二进制文件

Git 适合跟踪文本文件（源码、文档），不适合跟踪大型二进制文件（doc、xmind、pdf、图片）。每次修改都会存储完整副本，导致仓库体积膨胀。

### 2. `Attachment/` 从一开始就该被忽略

建议在创建仓库时立即配置 `.gitignore`，或在首次 `git add` 前就加入忽略规则。否则一旦被追踪，清理起来麻烦得多。

### 3. 大文件替代方案

| 需求 | 推荐方案 |
|------|----------|
| 笔记附件（图片、PDF） | 留在本地 Obsidian 的 `Attachment/`，不同步到 git |
| 需要共享的大文件 | 网盘 / NAS / Git LFS |
| 二进制构建产物 | 不提交，用 CI/CD 自动构建 |

### 4. git add 前先检查

养成习惯：在 `git add` 前先 `git status` 看看有哪些文件会被追踪，确认无误后再操作。

## 相关链接

- [GitHub 文件大小限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [Git LFS 官方文档](https://git-lfs.com/)
- [其他网络配置问题](github克隆问题.md)
[[知识卡片]]