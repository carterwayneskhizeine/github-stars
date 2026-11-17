# 🛠️ GitHub Skill Forge：让你的 AI 助手秒变“全能王”

[![English](https://img.shields.io/badge/Language-English-blue?style=flat-square)](./README_EN.md)
[![简体中文](https://img.shields.io/badge/语言-简体中文-red?style=flat-square)](./README_ZH.md)

[![Trae Meta-Skill](https://img.shields.io/badge/Platform-Trae-blueviolet?style=for-the-badge&logo=probot)](https://github.com/Trae)
[![Skill-Forge](https://img.shields.io/badge/Skill-Forge-F39C12?style=for-the-badge&logo=hammer)](#)
[![Zero-Clone](https://img.shields.io/badge/Mode-Zero--Clone-2ECC71?style=for-the-badge&logo=githubactions)](#)

你在 GitHub 上看到一个超级好玩的开源项目，想让 AI 帮你改改代码或者跑起来，结果发现：代码太多 AI 读不过来？配置太乱 AI 搞不定？手动复制粘贴累到手抽筋？

**GitHub Skill Forge** 就是为了解决这些麻烦事而诞生的。它像一个“技能转换器”，能把任何 GitHub 上的仓库，一键转成 AI 助手（比如 Trae）能直接理解、直接调用的“技能包”。你不需要手动下载代码，不需要配置复杂的本地环境，只需要提供一个链接，它就能帮你搞定一切。

---

### 💡 它能为你做什么？

*   **✨ 全程云端 (Zero-Clone)**：直接通过 GitHub API 扫描仓库，无需将代码克隆到本地，节省磁盘空间，扫描速度极快。
*   **📦 核心提取 (Smart RAG)**：自动剔除仓库中的杂物，只挑选最核心的代码逻辑和文档，打包成一个 AI 专用上下文文件（`context_bundle.md`），让 AI 瞬间掌握项目精髓。
*   **⚡ 镜像加速**：内置多组 API 镜像站，支持自动轮换和多线程抓取，有效绕过 GitHub 的访问频率限制。
*   **🛡️ 质量初筛**：自动识别项目的 Stars 数 and 活跃度，帮你避开那些还没写完或者是“坑”的仓库。

---

### 📁 文件夹内容详解

*   🧬 **`scripts/forge.py`**：核心执行脚本。所有的抓取、解析、打包工作都是它在后台完成的。
*   📖 **`SKILL.md`**：AI 的“操作说明书”。它定义了 AI 在什么时候应该调用这个工具，以及如何调用。
*   🔐 **`.env.example`**：安全配置模板。通过设置 GitHub Token，你可以获得更高的访问频率，让工具跑得更稳。

---

### 🛠️ 怎么用？（多种调用方式）

无论你是想在终端手动操作，还是希望 AI 自动帮你搞定，这里有几种简单的方法：

#### 方法 1：在终端手动执行（最直接）
打开 Trae 的终端，输入以下命令：
```bash
# 基础锻造命令
python scripts/forge.py "https://github.com/用户名/仓库名"

# 如果项目比较冷门（Star 数低），可以加 --force 强制执行
python scripts/forge.py "https://github.com/用户名/仓库名" --force
```

#### 方法 2：在对话中直接唤醒 AI（最智能）
你可以直接在对话框里对 Trae 助手说：
> “帮我把这个仓库转成技能：https://github.com/用户名/仓库名”

AI 会自动识别并调用 `forge.py` 脚本完成所有工作。

#### 方法 3：自定义配置（进阶玩家）
你可以修改 `scripts/forge.py` 中的 `api_mirrors` 列表，添加你自己的镜像站，或者在 `.env` 中配置多个 Token 来应对大规模抓取需求。

---

### 🏮 常见问题解答

*   **Q: 报错 403 提示频率限制？**  
    A: 这是 GitHub 对匿名访问的限制。去 GitHub 申请一个 Personal Access Token，填入 `.env` 文件，就能像 VIP 一样畅通无阻。
*   **Q: 网络连接一直超时？**  
    A: 工具会自动尝试换线。如果全部镜像都失败，请检查你的本地网络代理是否正确配置。
*   **Q: 生成的技能包在哪里？**  
    A: 成功后，你会发现在 `.trae/skills/` 目录下多了一个以仓库名命名的文件夹，里面就是所有的成果。

