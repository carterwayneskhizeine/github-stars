# `D:\Code\` 仓库清单

> 范围：`D:\Code\` 下所有 86 个目录
> GitHub 账号：`carterwayneskhizeine`

## 分类方法

- 用 `git -C <dir> remote get-url origin` 拉每个目录的 remote
- 用户自有 repo 用 `gh api repos/<owner>/<repo>` 查 `fork` 字段
- API 拿不到的（私有 / 已删），交叉验证 `git -C <dir> remote get-url upstream`
- 第三方账号下的 remote 不算"用户的 fork"，归入 *第三方 upstream clone*

## 统计

| 分类 | 数量 |
| --- | ---: |
| ✅ 自己的原创 / 非 fork | **16** |
| 🍴 自己的 fork | **9** |
| 📦 第三方 upstream clone（有 remote） | **42** |
| ⚠️ 有 `.git` 但没任何 remote | **3** |
| 📁 非 git 仓库 | **16** |
| **合计** | **86** |

---

## ✅ 自有原创 / 非 fork（16 个）

| 目录 | 备注 |
| --- | --- |
| CrazyTypewriter | |
| GoldieRillChat | |
| HyperBoard | |
| LiteLLM_VPS | |
| LiteLLMyamlDashboard | |
| ai-os-dev | |
| ai-os-eve | |
| bazi | |
| cv-web | |
| fde-internal-technical-design | |
| folder-location | |
| github-stars | 当前所在项目 |
| hermes-agent-windows-R | |
| nexusweave | |
| whitenote | |
| y1 | |

---

## 🍴 自己的 fork（9 个）

| 目录 | upstream（fork 自…） | 检测方式 |
| --- | --- | --- |
| MultiAgenticRAG | `nicoladisabato/MultiAgenticRAG` | `upstream` remote（API 404，原仓可能被删 / 私有） |
| SkillOpt | `microsoft/SkillOpt` | API + `upstream` remote |
| atlasclaw | `CloudChef/atlasclaw` | API + `upstream` remote |
| cua | `trycua/cua` | API |
| goldie-fork | `thedotmack/claude-mem` | API（本地叫 goldie-fork，remote 指向 claude-mem） |
| hermes-web-ui | `EKKOLearnAI/hermes-studio` | API + `upstream` remote（注意 upstream 写的是 hermes-web-ui，但 API 的 parent 是 hermes-studio，可能曾重命名） |
| oh-my-hermes | `Salomondiei08/oh-my-hermes` | API |
| stokowski | `Sugar-Coffee/stokowski` | API + `upstream` remote |
| ziwei | `ruijayfeng/ziwei` | API |

---

## 📦 第三方 upstream clone（42 个）

这些是直接 `git clone` 别人 repo 的本地副本，不算你的 fork。

| 目录 | upstream owner/repo |
| --- | --- |
| ComposioHQ-awesome-claude-skills | `ComposioHQ/awesome-claude-skills` |
| Houdini-Agent | `Kazama-Suichiku/Houdini-Agent` |
| MiniMax-AI-skills | `MiniMax-AI/skills` |
| OfficeCLI | `iOfficeAI/OfficeCLI` |
| OpenCLI | `jackwener/OpenCLI` |
| RAG-Knowledge-Base | `WangLin0/RAG-Knowledge-Base` |
| Romanescu11-hermes-skill-factory | `Romanescu11/hermes-skill-factory` |
| Understand-Anything | `Lum1104/Understand-Anything` |
| YuJunZhiXue-github-skill-forge | `YuJunZhiXue/github-skill-forge` |
| a2ui | `a2ui-project/a2ui` |
| addyosmani-agent-skills | `addyosmani/agent-skills` |
| aicommits | `Nutlope/aicommits` |
| anthropics-skills | `anthropics/skills` |
| chatbox | `chatboxai/chatbox` |
| cherry-studio | `CherryHQ/cherry-studio` |
| claude-mem | `thedotmack/claude-mem` |
| doris | `apache/doris` |
| eve | `vercel/eve` |
| fireworks-skill-memory | `yizhiyanhua-ai/fireworks-skill-memory` |
| google-gemini-gemini-skills | `google-gemini/gemini-skills` |
| google-skills | `google/skills` |
| hermes-agent | `NousResearch/hermes-agent` |
| huangserva-skill-prompt-generator | `huangserva/skill-prompt-generator` |
| knowledge-catalog | `GoogleCloudPlatform/knowledge-catalog` |
| langgraph | `langchain-ai/langgraph` |
| markitdown | `microsoft/markitdown` |
| mattpocock-skills | `mattpocock/skills` |
| mem0 | `mem0ai/mem0` |
| mempalace | `MemPalace/mempalace` |
| mesh-splatting | `meshsplatting/mesh-splatting` |
| nanoGPT | `karpathy/nanoGPT` |
| nanobot | `HKUDS/nanobot` |
| openclaw | `openclaw/openclaw` |
| openui | `thesysdev/openui` |
| pi | `earendil-works/pi` |
| planning-with-files | `OthmanAdi/planning-with-files` |
| ponytail | `DietrichGebert/ponytail` |
| portable-hermes-agent | `aivrar/portable-hermes-agent` |
| rag-web-ui | `rag-web-ui/rag-web-ui` |
| vscodium | `VSCodium/vscodium` |
| wx-cli | `jackwener/wx-cli` |
| yaojingang-yao-meta-skill | `yaojingang/yao-meta-skill` |

---

## ⚠️ 有 `.git` 但没任何 remote（3 个）

本地 `git init` 了但没 `git remote add`，也没推上去。

| 目录 | 建议 |
| --- | --- |
| `goldie_jobs` | 想保留就 `gh repo create`；不想要直接删目录 |
| `langchain_demo` | 同上 |
| `reverse-website` | 同上 |

---

## 📁 非 git 仓库（16 个）

这些目录里没有 `.git`，是纯本地项目 / 下载的代码 / 实验目录。

| 目录 | 备注 |
| --- | --- |
| `ClawX_v1` | |
| `Goldie` | |
| `PixelStreamingInfrastructure` | |
| `X` | |
| `bazi-dev` | |
| `clawdbot0403` | |
| `clawdbot_for_whitenote` | |
| `github_star` | |
| `goldierillsite` | |
| `hermes_chat` | |
| `langchain_learning` | |
| `node-switch` | |
| `openclaw-feishu` | |
| `opencode` | |
| `pinokio_openclaw` | |
| `pinokioopenclawguide` | |

---

## 复现这份报告

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
