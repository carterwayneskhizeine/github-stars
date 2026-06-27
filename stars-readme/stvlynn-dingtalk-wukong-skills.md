# DingTalk Wukong Skills

A curated collection of Agent Skills for DingTalk ecosystem and professional document processing.

[English](./README.md) | [简体中文](./README.zh.md)

> [!IMPORTANT]
> This project is a collection of skills extracted from Wukong v0.9.2 (arm64).
> These skills are optimized for Agent environments like [cli-gemini](https://github.com/google-gemini/cli), [claude-code](https://github.com/anthropics/claude-code), and [codex](https://github.com/vercel-labs/codex).

## Installation

To install all skills from this repository:

```bash
npx --yes skills add stvlynn/dingtalk-wukong-skills --skill='*' --full-depth
```

Or to install them globally:

```bash
npx --yes skills add stvlynn/dingtalk-wukong-skills --skill='*' --full-depth -g
```

> [!TIP]
> Use `--full-depth` is required for this multi-skill repository to discover all subdirectories.

## Skills

This collection provides a comprehensive set of skills for office automation and travel assistance.

### DingTalk Workspace

Opinionated skills for interacting with DingTalk products.

| Skill | Description | Source |
| :--- | :--- | :--- |
| [dws](./dws) | Comprehensive DingTalk workspace operations (OA, Todo, Calendar, Doc, etc.) | Wukong v0.9.2 |

### Document Processing

Professional tools for handling Office and PDF documents with high fidelity.

| Skill | Description | Source |
| :--- | :--- | :--- |
| [docx](./docx) | Advanced Word document processing with redlining and formatting support | Wukong v0.9.2 |
| [xlsx](./xlsx) | Excel spreadsheet manipulation with formula and analysis support | Wukong v0.9.2 |
| [pptx](./pptx) | PowerPoint presentation handling including HTML-to-PPT conversion | Wukong v0.9.2 |
| [pdf](./pdf) | PDF document handler for text/table extraction and form filling | Wukong v0.9.2 |
| [pdf-convert-to-word](./pdf-convert-to-word) | Specialized PDF to Word/Markdown conversion | Wukong v0.9.2 |

### Travel & Information

Real-time query skills for travel and local life.

| Skill | Description | Source |
| :--- | :--- | :--- |
| [12306-train-query](./12306-train-query) | Real-time 12306 train schedule and availability query | Wukong v0.9.2 |
| [ctrip-flight-search](./ctrip-flight-search) | Global flight search and price comparison via Ctrip | Wukong v0.9.2 |
| [dianping-info-query](./dianping-info-query) | Local business information and reviews from Dianping | Wukong v0.9.2 |

### Developer Tools

| Skill | Description | Source |
| :--- | :--- | :--- |
| [skill-creator](./skill-creator) | Tools for designing, validating, and packaging new agent skills | Wukong v0.9.2 |