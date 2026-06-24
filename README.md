# github-stars

把你在 GitHub 上 star 过的每个项目的 README.md 单文件下载到本地，并把
文件名重命名为 `Owner-RepoName.md`（例如 `Helvesec-rmux.md`），
方便你离线阅读、检索和全文搜索。

> 配套文件 `stars_mapping.json` 记录了本地文件名 ↔ 原始 GitHub 网址
> 的对应表，可以随时反查。

## 目录结构

```
D:\Code\github-stars\
├── README.md              ← 你正在看这个
├── download_stars.py      ← 唯一的脚本
├── stars_mapping.json     ← 本地文件名 → GitHub URL 对照表
├── stars_state.json       ← 增量下载用的状态文件（哪些 star 已处理）
└── stars-readme\          ← 所有下载下来的 README 都放这里
    ├── Helvesec-rmux.md
    ├── langchain-ai-langgraph.md
    └── ...
```

## 准备：安装并登录 `gh` CLI

脚本通过 `gh api` 调 GitHub REST API，所以本机需要先装好 GitHub
官方 CLI 并完成认证：

```bash
# 检查是否已安装
gh --version

# 登录（按提示在浏览器里授权）
gh auth login

# 确认登录状态
gh auth status
```

登录后 `gh` 默认带一个 5000 次/小时的 REST API 配额，下载
1200 多个 README 完全没问题。

## 快速开始

```bash
# 第一次跑：默认下前 10 个新 star（会把状态自动从已有 mapping 里初始化）
python download_stars.py

# 跑剩下所有未处理的 star（一次性，可能要 10 分钟左右）
python download_stars.py --all

# 只生成对照表，不下载（适合 mapping 丢失后想重建）
python download_stars.py --rebuild-mapping
```

> 提示：默认每次只下 10 个，是为防止一开始调试时不小心下太多。
> 平时用 `--all` 一次跑完即可。

## 增量下载

脚本是**幂等且增量**的：每个被处理过的 star（无论下载成功还是确认没有
README）都会写入 `stars_state.json`。下次再跑时，脚本只会处理**新增的**
star，已经处理过的会自动跳过。

常用工作流：

```bash
# 平时：在 GitHub 网站上点了一些 star 后，回命令行跑一下
python download_stars.py --all

# 想完全重新来过（清空 state，从 1206 个从头下）
python download_stars.py --reset-state --all

# 只想重新生成对照表，磁盘上有什么就记录什么
python download_stars.py --rebuild-mapping
```

## 所有命令行参数

| 参数 | 说明 |
| --- | --- |
| `--limit N` | 一次最多下 N 个新的 star（默认 10）。配合 `--all` 时无效。 |
| `--all` | 处理所有**未处理过**的 star。 |
| `--delay SECONDS` | 每次 API 请求后等多少秒，默认 0.5（GitHub 限流保护）。 |
| `--include-known` | 忽略 state，把所有 1206 个 star 重新处理一遍。 |
| `--reset-state` | 删掉 `stars_state.json` 再跑。和 `--include-known` 区别是 state 仍然会重建。 |
| `--rebuild-mapping` | 不下载，只根据磁盘上已有的 `*.md` 重新生成 `stars_mapping.json`。 |

## `stars_mapping.json` 用法

```json
{
  "_note": "Key = local README filename in stars-readme/; value = original GitHub URL...",
  "Helvesec-rmux.md": "https://github.com/Helvesec/rmux",
  "langchain-ai-langgraph.md": "https://github.com/langchain-ai/langgraph"
}
```

### 文件名 → 网址

```bash
python -c "import json; m=json.load(open('stars_mapping.json')); print(m['Helvesec-rmux.md'])"
# https://github.com/Helvesec/rmux
```

### 网址 → 文件名

```bash
python -c "import json; m={v:k for k,v in json.load(open('stars_mapping.json')).items() if not k.startswith('_')}; print(m['https://github.com/Helvesec/rmux'])"
# Helvesec-rmux.md
```

### 用 `jq` 找包含某关键字的 star

```bash
# 需要先装 jq (https://jqlang.github.io/jq/)
jq 'to_entries | map(select(.key | contains("llm"))) | from_entries' stars_mapping.json
```

### 在编辑器里搜

直接用 VSCode / Sublime / 任意编辑器的全局搜索，对 `stars-readme/`
目录做全文搜索即可。所有 README 都是纯文本，本地搜索比 GitHub 网页
搜索快得多。

## 常见问题

**Q：网络断了 / 脚本被 Ctrl-C 中断了怎么办？**
A：再跑一次即可，state 已经记录了已处理过的 star，下次只会处理剩下的。

**Q：某个 star 之前没有 README，后来作者加上了。**
A：删掉 `stars_state.json` 里对应的 `owner/repo` 条目（用编辑器打开
`stars_state.json` 删一行），再跑一次脚本即可重新拉取。

**Q：文件名为什么是 `Owner-Repo.md` 而不是 `Repo.md`？**
A：避免冲突——GitHub 上有大量同名 repo（例如 `awesome`、`demo`），
加上 owner 才能唯一对应到原始 URL。

**Q：为什么不用 `git clone` 整个仓库？**
A：README 单文件就够阅读了，单文件比克隆整个 repo 省 100 倍磁盘；
另外 fork / 私有的 repo 不会出现在 stars 里，所以单文件最干净。

## 重新部署到另一台机器

把这整个文件夹（包括 `stars-readme/`、`stars_mapping.json`、
`stars_state.json`）拷贝到新机器，登录 `gh` 之后直接跑：

```bash
python download_stars.py --rebuild-mapping   # 如果 mapping 丢了
python download_stars.py --all               # 增量下完剩下的
```

## 许可

这个项目本身（脚本和文档）按 MIT 发布。`stars-readme/` 下所有
README 文件版权归各自的原作者所有。
