# Computing Power Platform

大模型算力中转站平台，用于统一接入多家大模型供应商，并向企业和其他客户提供账号、API Key、额度分配、调用统计与模型转发能力。

当前平台以 New API `v1.0.0-rc.24` 为源码基线，已经完成首轮生产迁移、域名 HTTPS 接入和证书自动续签监控。后续功能修改直接在本仓库的 New API 源码基础上进行，不再维护独立的旧平台代码线。

## 当前能力

- 客户注册、登录和邮箱验证基础能力。
- 超级管理员在 New API 原生管理后台分配用户额度和限制用量。
- 多上游大模型供应商、模型渠道和 API Key 中转。
- 原生产用户、管理员、Token 和业务配置迁移方案及验证脚本。
- `xyz.fantasy-lab.com` HTTPS 访问。
- 证书剩余 20 天时自动续签，20/15/10/5 天邮件提醒，续签后公网验证和成功通知。
- systemd 与 cron 双路径的证书监控保活。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `src/new-api/` | 可直接修改和构建的 New API 完整源码 |
| `deploy/remote/` | 生产迁移演练、切换、验证和回滚脚本 |
| `deploy/cert-monitor/` | HTTPS 证书续签、邮件通知、systemd 与 cron 保活程序 |
| `docs/requirements/` | 当前确认的产品需求和决策 |
| `docs/architecture/` | 平台目标架构 |
| `docs/migration/` | 生产替换与数据迁移方案 |
| `docs/operations/` | 生产运维、HTTPS 和证书监控手册 |
| `docs/acceptance/` | 迁移与生产验收记录 |
| `docs/research/` | New API 源码、数据库和 Token 迁移研究证据 |

## 源码基线

- 上游项目：`https://github.com/QuantumNous/new-api`
- 上游版本：`v1.0.0-rc.24`
- 上游提交：`5c3abffe8572aa8a49f15c3916707d2019d66af4`
- 源码许可证：GNU Affero General Public License v3.0

完整溯源信息见 [New API upstream baseline](docs/source/new-api-upstream.md)。上游许可证、NOTICE 和第三方许可证文件保留在 `src/new-api/` 中。

## 开发入口

New API 的后端、前端、Docker 和本地开发说明均位于 `src/new-api/`：

```bash
cd src/new-api
```

项目级需求、修改范围和生产约束以 [文档总索引](docs/README.md) 为准。涉及数据库、Token、生产迁移或证书调整时，先阅读相应迁移和运维文档，不要把真实密钥、数据库备份或服务器环境文件提交到 Git。

## 生产入口

- HTTPS：`https://xyz.fantasy-lab.com`
- 兼容 HTTP：`http://xyz.fantasy-lab.com`
- 原 IP 入口：`http://8.140.19.149:3000`

生产操作命令和回滚边界见 [New API production operations](docs/operations/new-api-production-operations.md) 与 [certificate renewal monitor](docs/operations/xyz-certificate-renewal-monitor-2026-08-14.md)。

## 安全规则

- 仓库只保存 `.env.example` 等无密钥模板。
- SMTP 授权码、API Key、数据库口令、JWT 密钥、私钥和证书私钥只能保存在服务器权限受控文件中。
- `.research-cache/`、`node_modules/`、本地二进制和生产数据库备份不进入版本控制。
- 发布前必须运行敏感信息扫描和 GitHub 大文件检查。
