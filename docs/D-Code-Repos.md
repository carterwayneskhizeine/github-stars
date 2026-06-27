# `D:\Code\` 仓库清单 — 使用说明书

> **本文件是 `data/d-code-repos.json` 的用户手册**。
> JSON 是单一数据源，本文件解释 schema、常见查询、和更新方式。

## TL;DR

| 你想… | 怎么做 |
| --- | --- |
| 看 `D:\Code\` 里有什么 | `cat data/d-code-repos.json` 或用 `jq`（见下方查询示例） |
| 知道哪些是 fork 哪些是 clone | `jq '.repos[] \| select(.type=="fork")' data/d-code-repos.json` |
| 把 star 里的 X 克隆到 `D:\Code\` | **直接跟 agent 说「克隆 https://github.com/X/Y」** — skill 会自动跑「克隆 → 同步 stars → 回填 `source_star`」整条链（详见「运行环境」章节）|
| 重新扫一遍本地 | `python .agents/skills/d-code/scripts/scan_inventory.py` |
| 跨平台（macOS / Linux / Termux） | macOS / Linux：改 JSON 的 `_meta.root_path` 后重跑 scan。Termux 下不能写，详见「运行环境」和 §6 |
| 找 star 了但还没 clone 的 | `python .agents/skills/d-code/scripts/clone_repo.py --list-new` |

---

## 1. 文件位置

```
github-stars/
├── data/
│   └── d-code-repos.json    ← 唯一数据源（_meta + repos[]）
├── .agents/skills/d-code/
│   ├── SKILL.md             ← skill 主文件（agent 怎么用这个数据）
│   ├── references/
│   │   └── json-schema.md   ← 字段详细规范
│   └── scripts/
│       ├── scan_inventory.py ← 扫描本地 → 写 JSON
│       └── clone_repo.py     ← 克隆 + 冲突检测 + 更新 JSON
└── docs/
    └── D-Code-Repos.md      ← 本文件
```

> **改 JSON 之前先读一下 [`references/json-schema.md`](../.agents/skills/d-code/references/json-schema.md)**——那里有完整的字段定义和示例。

---

## 2. Schema 一览

```json
{
  "_meta": {
    "description":     "本地 Code 文件夹的仓库清单（单一数据源）",
    "root_path":       "D:\\Code",
    "schema_version":  1,
    "last_full_scan":  "2026-06-27T17:58:00+08:00",
    "gh_user":         "carterwayneskhizeine"
  },
  "repos": [
    {
      "name":         "a2ui",
      "type":         "upstream-clone",
      "origin":       "git@github.com:a2ui-project/a2ui.git",
      "upstream":     null,
      "parent":       null,
      "is_fork":      false,
      "source_star":  null,
      "last_scanned": "2026-06-27T17:57:36+08:00",
      "notes":        null
    }
  ]
}
```

### 5 种 `type`

| `type` | 含义 | 例子 |
| --- | --- | --- |
| `original` | 你的原创 repo（`is_fork: false`） | `ai-os-eve`, `bazi`, `whitenote` |
| `fork` | 你的 fork（有 `upstream` 指向父仓） | `cua → trycua/cua`, `goldie-fork → thedotmack/claude-mem` |
| `upstream-clone` | 第三方 repo 的直接 clone | `a2ui`, `langgraph`, `openui` |
| `no-remote-git` | 本地 `git init` 但没 remote | `goldie_jobs`, `langchain_demo`, `reverse-website` |
| `non-git` | 没 `.git` 的纯目录 | `Goldie`, `opencode`, `hermes_chat` |

完整字段语义见 [`references/json-schema.md`](../.agents/skills/d-code/references/json-schema.md)。

---

## 运行环境（三种 mode）

d-code skill 在跑任何写文件的脚本（`clone_repo.py` / `scan_inventory.py` / `download_stars.py`）之前，会先检测自己在哪种环境里。三种 mode 对应不同的允许动作，**不满足条件就拒绝执行并问用户**，不会吞错或瞎猜。

### 检测脚本

跑一次就知道自己在哪种 mode：

```bash
python -c "
import os, platform
sys_name = platform.system()
root = r'D:\Code'
if sys_name == 'Windows' and os.path.isdir(root):
    print(f'windows-local  ({sys_name} + {root})')
elif 'ANDROID_ROOT' in os.environ or 'TERMUX_VERSION' in os.environ or os.path.isdir('/data/data/com.termux'):
    print('termux-ubuntu  (Termux / proot-distro Ubuntu detected)')
else:
    print(f'other  ({sys_name}, {root} not present)')
"
```

### 三种 mode 对照

| Mode | 触发条件 | 允许的动作 | 禁止的动作 |
|---|---|---|---|
| `windows-local` | Windows + `D:\Code\` 存在 | clone / scan / backfill / query / 任何状态写入 | — |
| `termux-ubuntu` | Termux / proot-distro Ubuntu（`TERMUX_VERSION` / `ANDROID_ROOT` / `/data/data/com.termux` 任一命中）| 读所有文件 / 跑只读 Python / **新建**文件到 `docs/` | 写 `data/*.json`、跑 `gh clone` / `git push`、改写脚本和 `SKILL.md`、修改已有文件 |
| `other` | 其他（macOS / Linux 无 Termux / Windows 无 D 盘 / …）| 等待用户说明 | 不能猜，会问「你想怎么走？」|

### Termux 模式该怎么办

如果你在手机上用 Termux 的 Ubuntu 模拟器（proot-distro）跑这个 skill，**`D:\Code\` 没有对应物**，而且大概率没装 `gh`。所以 d-code skill 不会真去克隆——它会告诉你：

> 这个 workflow 需要 Windows。要不要我帮你写一份 `docs/clone-<owner>-<repo>-windows.md`，里面是完整的 Windows 命令？

两个选择：

1. **拿到 Windows 机器上跑** — 把你刚刚在 Termux 里跟 agent 的对话粘回 Windows 上的 pi，skill 会自动接上
2. **让 agent 写一份 Windows 操作指南** — 一个纯文档文件，方便你随时拿出来执行。skill 会写、但**不会**碰任何 JSON 或脚本

### 工作流举例：克隆一个 star 过的 repo

`windows-local` 模式下，一次对话就能跑完全部三步（agent 不会让你分三次发指令）：

1. 解析 URL → `Einsia/Browser-BC`
2. `clone_repo.py https://github.com/Einsia/Browser-BC` → `D:\Code\Browser-BC\`
3. `python download_stars.py` → 同步 stars，`stars-readme/Einsia-Browser-BC.md` 落盘
4. `scan_inventory.py --backfill-source-star` → `data/d-code-repos.json` 里 `Browser-BC.source_star = "Einsia-Browser-BC.md"`
5. 一次性汇报：folder / origin / source_star / downloaded / matched

`termux-ubuntu` 模式下，到第 2 步就会停下来，问你要不要写一份 windows 操作指南。

---

## 3. 常见查询（`jq` 速查）

需要 `jq`（[安装](https://jqlang.github.io/jq/)）。所有命令都在 `github-stars/` 根目录运行。

```bash
# 总览
jq '.repos | length' data/d-code-repos.json           # 总数
jq '._meta.last_full_scan' data/d-code-repos.json     # 上次扫描时间

# 按类型筛选
jq '.repos[] | select(.type=="fork") | .name' data/d-code-repos.json
jq '.repos[] | select(.type=="upstream-clone") | .name' data/d-code-repos.json

# Fork 详情（看是从哪个父仓 fork 的）
jq '.repos[] | select(.type=="fork") | "\(.name) → \(.parent)"' data/d-code-repos.json

# 找还没从 star 克隆下来的（交叉 data/stars_mapping.json）
jq -r '.repos[] | select(.source_star==null) | .name' data/d-code-repos.json
```

### 编程式访问（Python）

```python
import json
with open("data/d-code-repos.json", encoding="utf-8") as f:
    inv = json.load(f)

root = inv["_meta"]["root_path"]
forks = [r for r in inv["repos"] if r["type"] == "fork"]
print(f"root={root}, fork count={len(forks)}")
```

---

## 4. 跟其它文件的关系

```
stars-readme/Owner-Repo.md    ←  star 过的 repo 的 README（download_stars.py 产出）
           ↓ 怎么用
data/stars_mapping.json       ←  Owner-Repo.md → GitHub URL 映射
           ↓ 怎么用
data/d-code-repos.json        ←  本地 clone 状态（scan_inventory.py 产出）  ★ 唯一数据源
           ↓ 怎么用
docs/D-Code-Repos.md          ←  本文件
```

找 **star 了但还没 clone** 的 repo：

```bash
python .agents/skills/d-code/scripts/clone_repo.py --list-new
```

输出形如：
```
142 starred repos not yet cloned:
  anthropics/skills                            ← stars-readme/anthropics-skills.md
  ...
```

---

## 5. 怎么更新 JSON

### 5.1 重新扫描本地

```bash
python .agents/skills/d-code/scripts/scan_inventory.py
```

会：
1. 遍历 `_meta.root_path` 下所有子目录
2. 对每个目录读 `.git/config`、必要时调 `gh api` 查 fork 状态
3. **保留** 已有 entry 的 `source_star` 和 `notes` 字段，以及 `_meta` 里所有未管理的字段
4. 写回 `data/d-code-repos.json`

加 `--diff` 只看变化不写：
```bash
python .agents/skills/d-code/scripts/scan_inventory.py --diff
```

加 `--verify` 走磁盘逐字段对账（**不调 `gh api`、不写文件**）：
```bash
python .agents/skills/d-code/scripts/scan_inventory.py --verify
echo $?  # 0 = clean，1 = 有漂移
```

| 模式 | 调 `gh api` | 写 JSON | 用途 |
| --- | ---: | ---: | --- |
| `scan_inventory.py` | 是 | 是 | 全量重扫+写 |
| `scan_inventory.py --diff` | 是 | 否 | 全量重扫+看 diff（不写）|
| `scan_inventory.py --verify` | **否** | **否** | 轻量逐字段对账（CI / pre-commit）|
| `scan_inventory.py --backfill-source-star` | 否 | 仅匹配时 | 回填 `source_star` |

### 5.2 回填 `source_star`

很多 upstream-clone 是在 d-code skill 出现**之前**手动 clone 的，JSON 里它们的 `source_star` 是 `null`，没法判断是"老 clone 找不到 star 来源"还是"真没 star 过"。

回填脚本会把 `data/stars_mapping.json` 的 key（`Owner-Repo.md`）和 JSON 里 `upstream-clone` 的 `origin` 反向比对，能匹配上的就填上：

```bash
python .agents/skills/d-code/scripts/scan_inventory.py --backfill-source-star
```

- **匹配规则**：从 `origin` 提取 `owner/repo` → 查 `<owner>-<repo>.md`（大小写不敏感）
- **只改 `null` 的**：已有 `source_star` 的不会动
- **写条件**：至少匹配到 1 个才写 JSON（no-op 不写）
- **副作用**：更新 `_meta.last_backfill_source_star`；scan 不会清掉这个字段

匹配不上通常意味着：
- 你 clone 过但没 star / 已 unstar（如 `RAG-Knowledge-Base`）
- 仓库转手了（如 `Understand-Anything` 从 `Lum1104` 改到 `Egonex-AI`）

**这两种情况保留 `null` 是对的，不要手动瞎填。**

### 5.3 克隆新仓（一次性完整流程）

在 `windows-local` 模式下，d-code skill 跑的是「**clone → sync stars → backfill source_star**」三合一的完整工作流。你只需要跟 agent 说一句「把 https://github.com/X/Y 克隆到 Code 文件夹」，skill 会自动：

1. 环境检测（必须是 `windows-local`，否则停下来问你，详见「运行环境」章节）
2. 解析 `owner/repo`
3. 跑 `clone_repo.py`（带冲突检测，下面详述）
4. 跑 `python download_stars.py`（增量同步 GitHub stars）
5. 跑 `scan_inventory.py --backfill-source-star`（回填 `source_star`）
6. 一次性汇报结果

如果中途任何一步失败，skill 会**精确告诉你哪步失败、哪步成功**，不会吞掉错误。

如果只想跑单步（不进 skill），手工命令：

```bash
# Step 1: 克隆（带冲突检测）
python .agents/skills/d-code/scripts/clone_repo.py vercel/eve
python .agents/skills/d-code/scripts/clone_repo.py https://github.com/a2ui-project/a2ui
python .agents/skills/d-code/scripts/clone_repo.py stars-readme/3DTopia-MVPaint.md

# Step 2: 同步 stars（让新 star 进 stars_mapping.json）
python download_stars.py

# Step 3: 回填 source_star（把新 clone 关联到 stars-readme/Owner-Repo.md）
python .agents/skills/d-code/scripts/scan_inventory.py --backfill-source-star
```

**`clone_repo.py` 的 4 种冲突处理**：

| 本地状态 | 行为 |
| --- | --- |
| 文件夹不存在 | 跑 `gh repo clone <owner>/<repo> <repo>`，名字保持原样（`MVPaint` 而不是 `3DTopia-MVPaint`） |
| 存在且 origin 相同 | 跳过，提示"已存在" |
| 存在且是同一 fork 家族 | 提示「可以加 upstream remote」并退出 |
| 存在但完全不同的 repo | 弹 3 选项：取消 / 改名字（建议加 owner 前缀） / 删了重来（需输入文件夹名确认） |

成功后自动更新 `data/d-code-repos.json`。

加 `--yes` 跳过交互（冲突时默认用"改名字"）：
```bash
python .agents/skills/d-code/scripts/clone_repo.py --yes <target>
```

**`termux-ubuntu` 模式怎么办**：skill 会拒绝跑 `clone_repo.py`，并主动提议写一份 `docs/clone-<owner>-<repo>-windows.md` 给你拿回 Windows 执行（不碰任何 JSON）。

---

## 6. 跨平台 / 换机器

### 6.1 Windows ↔ macOS ↔ Linux

`skill/scripts` 是平台无关的（用 `pathlib`）。要把这份清单挪到另一台机器：

1. 整个 `github-stars/` 拷贝过去（含 `data/`、`.agents/skills/`、`stars-readme/`）
2. 在新机器装好 `gh` CLI 并 `gh auth login`
3. 编辑 `data/d-code-repos.json` 的 `_meta.root_path`：
   - Windows: `"D:\\Code"`
   - macOS: `"/Users/<you>/Code"`
   - Linux: `"/home/<you>/Code"`
4. 跑 `python .agents/skills/d-code/scripts/scan_inventory.py` 重新生成

如果换 GitHub 账号，改 `_meta.gh_user`（或传 `--user <name>`），脚本会用新账号判定"是不是你的 fork"。

### 6.2 Termux / Android (proot-distro Ubuntu)

**这条对应「运行环境」章节里的 `termux-ubuntu` mode**。

如果你在手机上跑 Termux + proot-distro Ubuntu，**不要试图让 d-code skill 在这里 clone / scan / backfill**：

- `D:\Code\` 没有 Linux 对应物
- 就算改成 `/data/data/com.termux/files/home/Code` 也带不走（没持久化、没 `gh`、没授权）
- skill 会自动检测到 `termux-ubuntu` mode 并拒绝执行

能在这个环境里做的事：

- ✅ **读**：`data/d-code-repos.json` 查询、`stars-readme/*.md` 内容浏览
- ✅ **新建** `docs/*.md`（比如「Windows 上要跑的命令清单」）
- ❌ **不能**：克隆、扫描、写 JSON、改脚本

实际操作建议：

1. 在 Termux 里跟 agent 对话，让它把要 clone 的 repo 写成 `docs/clone-X-Y-windows.md`
2. 拷贝到 Windows 后打开 pi agent，对它说「按 `docs/clone-X-Y-windows.md` 跑」
3. Windows 上的 skill 会自动跑完整流程（见 §5.3）

---

## 7. 复现这份清单的旧方式

保留旧版纯 bash 复现脚本作为参考（现在推荐用上面的 `scan_inventory.py` 替代）：

```bash
cd /d/Code
# 总览
ls -d */
find . -maxdepth 2 -name ".git" -type d | wc -l

# 用户自有 repo 的 fork 状态
ME=carterwayneskhizeine
for d in */; do
  [ -d "$d.git" ] || continue
  url=$(git -C "$d" remote get-url origin 2>/dev/null)
  [[ "$url" == *"$ME"* ]] || continue
  slug=$(echo "$url" | sed -E 's#.*github\.com[:/]+([^/]+)/([^/.]+)(\.git)?$#\1/\2#')
  fork=$(gh api "repos/$slug" --jq '.fork' 2>/dev/null)
  parent=$(gh api "repos/$slug" --jq '.parent.full_name // "—"' 2>/dev/null)
  printf "%-40s %s  (parent: %s)\n" "${d%/}" "$fork" "$parent"
done

# API 拿不到的，看 upstream remote
for d in */; do
  [ -d "$d.git" ] || continue
  up=$(git -C "$d" remote get-url upstream 2>/dev/null)
  [ -n "$up" ] && printf "%-40s upstream: %s\n" "${d%/}" "$up"
done
```

## 许可

本文档与 `data/d-code-repos.json` 均按 MIT 发布（与项目主 `LICENSE` 一致）。
