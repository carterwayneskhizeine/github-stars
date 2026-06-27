# Claude Code Skills

我的个人 Claude Code Skill 合集——解决内容创作、会议处理、播客下载等日常工作场景。

[English version below](#english)

---

## Skill 列表

### 内容创作

| Skill | 描述 |
|-------|------|
| [公众号文章](./公众号文章/) | 将 AI 对话记录提炼成微信公众号文章，含完整文章、50 个标题、10 个简介、10 组配图提示词 |
| [多视角对话素材](./多视角对话素材/) | 从多个视角并行生成多轮追问对话，作为公众号文章的原始素材 |

### 会议与文字处理

| Skill | 描述 |
|-------|------|
| [会议方法论提炼](./会议方法论提炼/) | 从会议录音转写稿中提炼管理者的方法论指导，还原讨论背景，输出结构化文档 |
| [文字稿润色](./文字稿润色/) | 将原始录音转文字整理为书面逐字稿，执行脱敏，输出原文 vs 整理后对照格式 |
| [长文结构优化](./长文结构优化/) | 审查长文档的标题层级、段落节奏，输出结构优化建议 |

### 工具与效率

| Skill | 描述 |
|-------|------|
| [API脚本化](./API脚本化/) | 根据 API 文档自动生成配置驱动的工程项目（零硬编码、保姆级 UX） |
| [小宇宙播客下载](./小宇宙播客下载/) | 自动提取小宇宙播客音频直链并批量下载 |

### 诊断

| Skill | 描述 |
|-------|------|
| [模型指纹检测](./模型指纹检测/) | 通过自省式分析检测当前 API 是否为真实 Claude 模型，或是否存在多层封装 |

---

## 安装方法

### 安装单个 Skill

```bash
# 以「公众号文章」为例
mkdir -p ~/.claude/skills/公众号文章
curl -o ~/.claude/skills/公众号文章/SKILL.md \
  https://raw.githubusercontent.com/bi-boo/claude-model-fingerprint/main/公众号文章/SKILL.md
```

### 一键安装所有 Skill

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/bi-boo/claude-model-fingerprint/main/install.sh)
```

### 手动安装（推荐）

```bash
git clone https://github.com/bi-boo/claude-model-fingerprint.git /tmp/claude-skills
cp -r /tmp/claude-skills/公众号文章 ~/.claude/skills/
cp -r /tmp/claude-skills/会议方法论提炼 ~/.claude/skills/
# 按需复制所需 Skill
```

---

## 使用方式

安装后在 Claude Code 对话中直接调用：

```
/公众号文章
/会议方法论提炼
/模型指纹检测
```

或用自然语言触发，Claude 会自动识别对应的 Skill。

---

## 环境变量配置

部分 Skill 依赖环境变量，建议在 `~/.zshrc` 或 `~/.bashrc` 中配置：

```bash
# 公众号文章素材输出目录（多视角对话素材 Skill 使用）
export WECHAT_ARTICLES_DIR="$HOME/Documents/articles"

# 播客下载目录（小宇宙播客下载 Skill 使用）
export PODCAST_DOWNLOAD_DIR="$HOME/Downloads/podcasts"
```

---

<a name="english"></a>

## English

A collection of personal Claude Code Skills for content creation, meeting processing, and productivity.

| Skill | Description |
|-------|-------------|
| 公众号文章 | Transform AI conversations into WeChat articles with titles, descriptions, and image prompts |
| 多视角对话素材 | Generate multi-perspective dialogues as raw material for articles |
| 会议方法论提炼 | Extract methodology and insights from meeting transcripts |
| 文字稿润色 | Polish raw transcripts into formal prose with side-by-side diff format |
| 长文结构优化 | Review heading hierarchy and paragraph rhythm of long documents |
| API脚本化 | Generate zero-hardcoding, config-driven project from API docs |
| 小宇宙播客下载 | Extract and batch-download podcast audio from XiaoyuzhouFM |
| 模型指纹检测 | Detect if the current API is authentic Claude or a wrapped/spoofed model |
