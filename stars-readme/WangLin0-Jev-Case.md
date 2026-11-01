# Jev 研究项目

本项目用于研究和实践 TypeSafe AI 的 Jev 模型。官方文档已镜像到 [`docs/typesafe-ai/`](docs/typesafe-ai/)，入口、来源清单和抓取校验信息见其中的 README 与 `source-manifest.json`。

## 快速开始

1. 安装 Python SDK：`pip install typesafe-sdk`（要求 Python >= 3.10）。
2. 在项目根目录创建 `.env`，设置 `TYPESAFE_API_KEY`；`.env` 已加入 `.gitignore`。
3. 先阅读 [`docs/typesafe-ai/jev-usage-notes.md`](docs/typesafe-ai/jev-usage-notes.md)，再按场景查看 API、SDK、Primitive 和 Cookbook 文档。
4. 社区实践参考 [`docs/typesafe-ai/case-studies/`](docs/typesafe-ai/case-studies/README.md)，其中整理了 JEV Case 案例墙和 20 个公开用例方向。
5. 后续新增的文章和源码研究从 [社区案例研究入口](docs/typesafe-ai/case-studies/README.md) 进入，按日期批次查看。

最小请求模型是：把待判断内容放入 `state`，把一个或多个窄问题放入 `questions`，调用 `https://api.typesafe.ai/v1/systemone`，再由代码消费结构化答案。Jev 的三种问题类型是 Choice、Score 和 Noul。

## 文档范围

本次快照依据官方 [`llms.txt`](docs/typesafe-ai/llms.txt) 下载完整索引，共 110 个 Markdown 页面，包含 Introduction、Concepts、Primitives、Patterns、SDK/API、Cookbooks、模型说明和 Agent Skill。
