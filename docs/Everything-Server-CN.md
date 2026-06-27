# MCP Everything Server（中文解读）

> 本文档是对 [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers)
> 仓库中 **`src/everything`** 参考实现的解读与翻译。
>
> **信息来源说明**：原 README 仅给出"Reference / test server with prompts,
> resources, and tools"这一行描述。本文档其余内容（具体工具/资源/提示列表）
> 整理自该 server 的公开源码与 MCP 官方文档；**非原 README 原文逐字翻译**。

---

## 一、原 README 中的定位

```
🌟 Reference Servers

- **[Everything](src/everything)** - Reference / test server with
  prompts, resources, and tools.
```

> 🌟 **参考服务器**
>
> - **[Everything](src/everything)** — 演示 prompts、resources、tools 三大能力的参考/测试服务器。

仓库说明里强调：这里的 server 是**参考实现**，目的是展示 MCP 特性和 SDK 用法，**不是生产级方案**。

## 二、Everything Server 的设计目的

| 目的 | 说明 |
| --- | --- |
| **覆盖 MCP 三大原语** | 一次性展示 `prompts` + `resources` + `tools` 的完整用法 |
| **协议能力回归测试** | 任何 MCP 客户端实现都可以用它做协议兼容性测试 |
| **SDK 演示** | TypeScript / Python SDK 作者常用它来演示 API 调用模式 |
| **学习样例** | 想写自己的 MCP server 的开发者，看这一个就够入门 |

⚠️ 同样适用 `modelcontextprotocol/servers` 仓库的总警告：

> The servers in this repository are intended as **reference implementations**
> to demonstrate MCP features and SDK usage. They are meant to serve as
> educational examples for developers building their own MCP servers, **not
> as production-ready solutions**.

翻译：这些 server 是**参考实现**，用于演示 MCP 特性和 SDK 用法，作为开发
者构建自己 MCP server 的**教学示例**，**不是可直接上线的生产级方案**。

## 三、暴露的能力概览

> 以下内容整理自 `src/everything` 的源码与公开 MCP 文档。原 README 中
> 仅有"prompts, resources, and tools"一句，并未列举具体 API。

### 1. Tools（工具）

Everything server 通常暴露以下工具（不同 SDK 版本可能有微小差异）：

| 工具名                    | 功能        | 演示的 MCP 能力                         |
| ---------------------- | --------- | ---------------------------------- |
| `echo`                 | 回显传入的消息   | 基础 tool 调用 + schema                |
| `add`                  | 两数相加      | 简单参数与返回类型                          |
| `longRunningOperation` | 长任务模拟     | **进度通知（progress notifications）**   |
| `printEnv`             | 打印环境变量    | 读取 server 端环境                      |
| `sampleLLMEcho`        | 调用 LLM 采样 | **Sampling（让 server 反向调用客户端 LLM）** |
| `getTinyImage`         | 返回一张小图    | **返回图片内容（image content）**          |
| `annotatedMessage`     | 带注解的消息    | **Annotated messages / 提示注解**      |

### 2. Resources（资源）

| 资源 URI | 说明 |
| --- | --- |
| `test://static/text/{name}` | 静态文本资源 |
| `test://dynamic/text/{name}` | 动态生成的文本资源（演示 `resources/read`） |
| `test://static/image/{name}` | 静态图片资源（演示二进制返回） |

### 3. Prompts（提示模板）

| 提示名 | 说明 |
| --- | --- |
| `simple_prompt` | 一个无参数的最简模板 |
| `complex_prompt` | 多个参数 + 嵌套上下文 |
| `resource_prompt` | 引用资源 URI 的提示模板 |

## 四、它演示的关键 MCP 能力（重点）

| MCP 能力 | 怎么在 Everything 里被演示 |
| --- | --- |
| **Tools 调用** | `echo` / `add` / `printEnv` 是最朴素的例子 |
| **Sampling（采样）** | `sampleLLMEcho` 让 server 主动向客户端请求一次 LLM 采样 |
| **Progress 通知** | `longRunningOperation` 用 `notifications/progress` 推送进度 |
| **Image / Blob 返回** | `getTinyImage` 演示 tool 返回图片二进制 |
| **Resources** | `test://...` 系列 URI 演示 `resources/list` 与 `resources/read` |
| **Prompts** | `simple_prompt` / `complex_prompt` 演示提示模板与参数 |
| **Logging** | 触发 server 端日志消息 |
| **Roots / Elicitation 等** | 视版本而定，部分 SDK 版本会演示 |

## 五、快速使用

### 1. 启动（TypeScript 版本）

原 README 给出的通用用法：

```bash
npx -y @modelcontextprotocol/server-everything
```

### 2. 接入 Claude Desktop

参考 README 中其它 server 的写法，Claude Desktop 配置形如：

```json
{
  "mcpServers": {
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

### 3. 接入到 Cursor / Continue / Cline 等

```json
{
  "mcpServers": {
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

> 客户端不同，配置文件名/位置略有差异（`.cursor/mcp.json`、`.continue/config.json`、
> Cline 的 `cline_mcp_settings.json` 等）。

## 六、它跟你 star 过的项目的关联

| 你 star 过的项目 | 关系 |
| --- | --- |
| [`modelcontextprotocol-servers`](../stars-readme/modelcontextprotocol-servers.md) | 本仓库的父仓库（Everything 在 `src/everything` 子目录） |
| [`modelcontextprotocol-typescript-sdk`](../stars-readme/modelcontextprotocol-typescript-sdk.md) | TypeScript 官方 SDK，Everything 主要用它实现 |
| [`microsoft-playwright-mcp`](../stars-readme/microsoft-playwright-mcp.md) | Puppeteer-MCP 的官方继任者（同为 MCP server 实现范例） |
| [`vimo-ai-mcp-router`](../stars-readme/vimo-ai-mcp-router.md) | 路由器形态的 MCP，与 Everything 是**正交关系**——后者是 server 实现，前者聚合多个 server |
| [`MicrosoftDocs-mcp`](../stars-readme/MicrosoftDocs-mcp.md) | 微软文档 MCP——功能更聚焦，Everything 是"全能 demo" |
| [`microsoft-mcp-for-beginners`](../stars-readme/microsoft-mcp-for-beginners.md) | 微软的 MCP 入门教程，里面大概率会引用 Everything 作为示例 |

## 七、典型使用场景

| 你是谁 | 为什么要看 Everything |
| --- | --- |
| **协议学习者** | 想要一份"看一份代码就把 MCP 三大原语搞懂"的样例 |
| **SDK 作者** | 想给自己的 SDK 写 conformance test，Everything 是事实标准 |
| **客户端开发者** | 想给自己开发的 MCP 客户端做兼容性验证 |
| **想写 MCP server** | 把 Everything 的源码复制一份，把 tools 改成自己需要的即可 |

## 八、源码与官方仓库

- **MCP 官方 servers 仓库**：<https://github.com/modelcontextprotocol/servers>
- **Everything 子目录**：<https://github.com/modelcontextprotocol/servers/tree/main/src/everything>
- **TypeScript SDK**（主要实现语言）：<https://github.com/modelcontextprotocol/typescript-sdk>
- **Python SDK**（也提供 Python 版本）：<https://github.com/modelcontextprotocol/python-sdk>

## 九、安全提示（沿用原仓库总警告）

原 README 警告原文：

> Developers should evaluate their own security requirements and implement
> appropriate safeguards based on their specific threat model and use case.

翻译：开发者应**自行评估安全需求**，并根据自己的威胁模型和用例实施相应
的防护措施。Everything server 暴露了 `printEnv` 等**信息泄漏风险**的工具，
**切勿暴露在公网或不受信环境**。

---

## 附：本翻译的边界声明

| 部分 | 来源 |
| --- | --- |
| 第一节（"原 README 中的定位"） | ✅ **原 README 逐字引用** |
| 第二节（"仓库说明的总警告"） | ✅ **原 README 警告原文翻译** |
| 第三节（"暴露的能力概览"） | ⚠️ 整理自 Everything 公开源码/MCP 文档，**非原 README 内容** |
| 第四节（"关键 MCP 能力"） | ⚠️ 整理自 MCP 协议规范 + Everything 实现 |
| 第五节（"快速使用"） | ⚠️ 启动命令来自原 README；客户端配置是**示例写法** |
| 第六节（"关联项目"） | ⚠️ 基于本仓库 `stars-readme/` 内容整理 |
| 第七节（"典型场景"） | ⚠️ 作者解读 |
| 第九节（"安全提示"） | ✅ **原 README 警告原文翻译** |

如需最权威信息，请直接看：
- <https://github.com/modelcontextprotocol/servers/tree/main/src/everything>
- <https://modelcontextprotocol.io>
