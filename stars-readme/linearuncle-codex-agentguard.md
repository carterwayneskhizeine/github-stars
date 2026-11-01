# Codex AgentGuard

中文 | [English](README.en.md)

> 🚨🚨🚨 **严重警告** 🚨🚨🚨
> ⚠️ **GPT-5.6 SOL 模型已经出现删除大V matt 的用户文件夹，以及删除另外一个用户的 database 的真实事故！** ⚠️

Codex AgentGuard 是一个 Codex 安全插件，在执行前拦截常见的文件删除和数据库
删除操作，把决定权交还给用户。

它的威胁模型是"粗心的 agent"，而不是"恶意的人"。agent 意外删除东西时，删除
命令一定是明文写出来的（`rm -rf`、`DROP TABLE`），所以检测就是对命令原文做
简单的模式匹配。误报（注释或字符串里出现删除关键词）是有意接受的：拦错的代价
只是 agent 停下来问你一句。

> [!WARNING]
> 本项目只是一道额外的护栏，不是安全边界，也不能替代备份、最小权限、沙箱和
> 人工审查。Hook 无法拦截所有可能的 shell 或删除路径。使用本软件的风险完全
> 由你自行承担，作者和贡献者不对数据丢失、损坏、中断或其他后果负责。

## 功能

- 拦截包含 `rm`、`unlink`、`rmdir`、`find -delete`、`git clean` 的 shell
  命令，无论它出现在哪里：分隔符之后、wrapper 内、嵌套 shell、命令替换中。
- 拦截常见的 Python 和 Node.js 文件删除 API
  （`os.remove`、`shutil.rmtree`、`Path(...).unlink()`、`fs.rmSync` 等）。
- 拦截 `apply_patch` 的 `Delete File` 操作，堵住实测中出现过的换工具绕过。
- 拦截直接的数据库删除 SQL——`DROP DATABASE/SCHEMA/TABLE/VIEW/COLLECTION`、
  `TRUNCATE`、`DELETE FROM`——覆盖 shell 命令和传给 MCP 数据库工具的字符串
  参数。
- 有意拦截 `echo rm`、提到 `rm` 的注释这类模糊文本；误报便宜，漏报昂贵。
- Hook 输入异常时按 fail-closed 策略直接拒绝。
- 不会把 `arm`、`rm_file`、`unlinkable` 这类相邻词误认成删除命令。

## 从 GitHub 安装

```bash
codex plugin marketplace add linearuncle/codex-agentguard
codex plugin add codex-agentguard@codex-agentguard
```

安装后启动新的 Codex 会话（CLI 或桌面应用），会弹出 "Hooks need review"
对话框——hook 必须经过信任才会运行。选 "Review hooks" 逐条审查后信任，或选
"Trust all and continue"；选 "Continue without trusting" 则 hook 不会生效。
之后随时可以用 `/hooks` 查看和管理已信任的 hook。插件升级改动 hook 后会再次
要求信任。信任完成后开一个新任务再测试。

## 安全地验证

让 Codex 执行类似 `rm example.txt` 的命令，AgentGuard 应当拒绝该工具调用并
回显被拦截的命令。请用一个不存在的测试路径——不要拿有价值的数据去测试安全
软件。

运行自动化测试：

```bash
python3 -m unittest discover -s plugins/codex-agentguard/tests -v
```

## 局限

Codex 官方将 `PreToolUse` 定位为护栏（guardrail）而非完整的强制边界。本插件
只处理该 hook 可见的 shell、`apply_patch` 和 MCP 工具调用，且只匹配明文写出
的删除操作。刻意混淆的命令（动态拼接字符串、编码变体）、内部逻辑不可见的
脚本、文件管理器操作，都在设计上不属于本插件的范围：它防的是粗心的 agent，
不是蓄意的对手。重要数据请用备份、最小权限和沙箱来保护。

## 许可证

MIT，见 [LICENSE](LICENSE)。许可证包含标准的"按原样提供"免责声明；上方的
警告强调的是实际使用中的风险。
