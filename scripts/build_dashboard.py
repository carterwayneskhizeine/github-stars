#!/usr/bin/env python
"""
build_dashboard.py — 把 data/c-code-repos.json 渲染成 docs/dashboard.html

设计目标:
  - 零依赖（只用标准库）
  - 产物是单文件 HTML，可双击打开（file://）也可丢 GitHub Pages
  - 数据嵌进 HTML 的 <script type="application/json">，前端纯 JS 渲染
  - 不调任何外部 API；source_star 链接从本地 stars_mapping.json 解析

用法:
  python scripts/build_dashboard.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Windows console 默认 GBK 会炸 emoji；强制 utf-8 输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "data" / "c-code-repos.json"
STARS_JSON = ROOT / "data" / "stars_mapping.json"
OUT_HTML = ROOT / "docs" / "dashboard.html"

# 类型元数据：标签 + 颜色 + 描述（描述写进前端 tooltip）
TYPE_META = {
    "original":       {"label": "原创",     "color": "#22c55e", "desc": "你自己 GitHub 名下的仓库"},
    "fork":           {"label": "Fork",     "color": "#a855f7", "desc": "你 fork 的别人的仓库"},
    "upstream-clone": {"label": "上游克隆", "color": "#f97316", "desc": "直接 clone 的第三方仓库"},
    "non-git":        {"label": "非 Git",   "color": "#64748b", "desc": "纯文件夹，没有 git"},
}


def load_inputs() -> tuple[dict, dict]:
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    stars: dict = {}
    if STARS_JSON.is_file():
        stars = json.loads(STARS_JSON.read_text(encoding="utf-8"))
    return data, stars


_GH_SSH  = re.compile(r"^git@github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?$")
_GH_HTTPS = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


def normalize_github_url(url: str | None) -> str | None:
    """把 git@github.com:o/r.git 或 https://github.com/o/r.git 规范成 https://github.com/o/r。
    非 GitHub 链接原样返回；空值返回 None。
    """
    if not url:
        return None
    u = url.strip()
    m = _GH_SSH.match(u)
    if m:
        return f"https://github.com/{m.group(1)}/{m.group(2)}"
    m = _GH_HTTPS.match(u)
    if m:
        return f"https://github.com/{m.group(1)}/{m.group(2)}"
    return u


def enrich(repos: list[dict], stars: dict, root_path: Path) -> list[dict]:
    """为每条记录补全规范化后的 https URL 字段（origin/upstream/parent）。
    source_star 从本地 stars_mapping.json 解析出对应 GitHub URL，不调 API。
    markdowns 不在这里嵌入——浏览器运行时通过 File System Access API 直接读
    本地磁盘（见前端 fs.js），避免把几 MB md 文本硬编码进 HTML。
    scan_markdown() 保留作为 fallback（不支持 File System Access 的浏览器走
    embedded 模式）。
    """
    out = []
    for r in repos:
        r2 = dict(r)
        r2["origin_web"]    = normalize_github_url(r.get("origin"))
        r2["upstream_web"]  = normalize_github_url(r.get("upstream"))
        r2["parent_web"]    = normalize_github_url(r.get("parent"))
        src = r.get("source_star")
        r2["source_star_url"] = stars.get(src) if src else None
        # markdowns 不嵌入了——前端运行时读盘
        out.append(r2)
    return out


def scan_markdown(repo_dir: Path) -> list[dict]:
    """扫描仓库根目录下的 *.md（不递归）。

    全部嵌入策略：
      - 所有 .md 都读，单文件 ≤ MAX_FILE_BYTES 就全文嵌入
      - 超过 MAX_FILE_BYTES 的（CHANGELOG.md、exported_*.md 这类机器生成大文件）
        不嵌入，只记元数据，前端展示"📂 在本地查看"
      - 单仓库嵌入总字节 ≥ MAX_PER_REPO 后停止嵌入（剩余只记元数据）
      - README 系列排序优先，其他按字母序

    返回每条 {name, relpath, file_url, content, embedded}：
      embedded=True  → 全文在 content
      embedded=False → content=None，前端走"本地查看"分支
    """
    MAX_FILE_BYTES = 80 * 1024     # 单文件 80 KB
    MAX_PER_REPO   = 300 * 1024    # 单仓库 300 KB
    if not repo_dir.is_dir():
        return []
    files = sorted(
        (p for p in repo_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md"),
        key=lambda p: (not _is_readme(p.name), p.name.lower()),
    )
    out = []
    embedded_bytes = 0
    for p in files:
        rel = p.name
        # repo_dir = C:\Users\gotmo\Code\LiteLLM_VPS → file:///C:/Users/gotmo/Code/LiteLLM_VPS/<rel>
        root_unix = str(repo_dir).replace("\\", "/")
        sep = "" if root_unix.endswith("/") else "/"
        file_url = "file:///" + root_unix.lstrip("/") + sep + rel
        try:
            content = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        size = len(content.encode("utf-8"))
        # 单文件太大 → 不嵌入（多半是 CHANGELOG / exported 这类机器生成文件）
        if size > MAX_FILE_BYTES:
            out.append({"name": rel, "relpath": rel, "file_url": file_url,
                        "content": None, "embedded": False,
                        "reason": f"文件过大 ({size // 1024} KB)，未嵌入"})
            continue
        # 单仓库总嵌入已达上限 → 不嵌入
        if embedded_bytes + size > MAX_PER_REPO:
            out.append({"name": rel, "relpath": rel, "file_url": file_url,
                        "content": None, "embedded": False,
                        "reason": f"仓库嵌入已达 {MAX_PER_REPO // 1024} KB 上限"})
            continue
        embedded_bytes += size
        out.append({"name": rel, "relpath": rel, "file_url": file_url,
                    "content": content, "embedded": True})
    return out


def _is_readme(name: str) -> bool:
    """README.md / README_xx.md / README-xx.md 都算 README 系列。"""
    n = name.lower()
    return n == "readme.md" or n.startswith("readme.") or n.startswith("readme_") or n.startswith("readme-")


# ---------- HTML 模板 ----------
# 占位符：__DATA__ / __TYPE_META__ / __BUILT__
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Code 文件夹仪表盘</title>
<style>
  :root {
    --bg: #f8fafc;     /* page bg */
    --bg-2: #ffffff;   /* card / header / toolbar bg */
    --bg-3: #f1f5f9;   /* inline <code> bg */
    --fg: #0f172a;     /* primary text */
    --fg-2: #64748b;   /* muted text */
    --accent: #2563eb; /* links / hover */
    --border: #e2e8f0;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0;
    background: var(--bg); color: var(--fg);
    font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI",
          "PingFang SC", "Microsoft YaHei", sans-serif;
  }
  header {
    padding: 8px 20px;
    background: var(--bg-2); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 10;
    display: flex; align-items: center; gap: 16px;
    flex-wrap: wrap;
  }
  h1 { margin: 0; font-size: 15px; font-weight: 600; flex-shrink: 0; }
  header .meta {
    color: var(--fg-2); font-size: 11px;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; min-width: 0;
  }
  code { background: var(--bg-3); padding: 1px 6px; border-radius: 4px; }
  .toolbar {
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    padding: 14px 28px;
    background: var(--bg-2); border-bottom: 1px solid var(--border);
  }
  .toolbar input[type=search] {
    flex: 1; min-width: 200px;
    background: var(--bg); color: var(--fg);
    border: 1px solid var(--border); border-radius: 6px;
    padding: 7px 11px; font-size: 14px;
  }
  .toolbar input[type=search]:focus { outline: none; border-color: var(--accent); }
  .filter-group { display: flex; gap: 6px; flex-wrap: wrap; }
  .filter-group label {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 10px;
    border: 1px solid var(--border); border-radius: 6px;
    cursor: pointer; user-select: none; font-size: 13px;
    transition: opacity .12s;
  }
  .filter-group label.off { opacity: 0.35; }
  .filter-group label .dot {
    width: 10px; height: 10px; border-radius: 50%; display: inline-block;
  }
  .toolbar select {
    background: var(--bg); color: var(--fg);
    border: 1px solid var(--border); border-radius: 6px;
    padding: 6px 10px; font-size: 13px;
  }
  .toolbar .count {
    margin-left: auto; color: var(--fg-2); font-size: 13px;
    font-variant-numeric: tabular-nums;
  }
  main { padding: 22px 28px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
  }
  .card {
    background: var(--bg-2);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    transition: transform .1s, border-color .1s, box-shadow .1s;
  }
  .card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
  }
  .card h3 {
    margin: 0 0 6px; font-size: 16px;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }
  .card h3 a {
    color: var(--fg); text-decoration: none; font-weight: 600;
    word-break: break-all;
  }
  .card h3 a:hover { color: var(--accent); }
  .card h3 .local-btn {
    display: inline-flex; align-items: center; gap: 3px;
    padding: 2px 8px;
    border: 1px solid var(--border); border-radius: 6px;
    font-size: 12px; font-weight: 500;
    color: var(--fg-2); background: var(--bg);
    text-decoration: none;
    transition: color .12s, border-color .12s, background .12s;
  }
  .card h3 .local-btn:hover {
    color: var(--accent); border-color: var(--accent); background: var(--bg-2);
  }
  .card h3 .local-btn[title]:hover::after {
    content: attr(title);
    position: absolute; transform: translateY(-130%);
    background: var(--fg); color: var(--bg-2);
    font-size: 11px; padding: 4px 8px; border-radius: 4px;
    white-space: nowrap; pointer-events: none;
  }
  .badge {
    display: inline-block;
    padding: 2px 9px; border-radius: 12px;
    font-size: 11px; font-weight: 600; color: white;
    flex-shrink: 0;
  }
  .card h3 .md-btn {
    display: inline-flex; align-items: center; gap: 3px;
    padding: 2px 8px;
    border: 1px solid var(--border); border-radius: 6px;
    font-size: 12px; font-weight: 500;
    color: var(--fg-2); background: var(--bg);
    text-decoration: none; cursor: pointer;
    transition: color .12s, border-color .12s, background .12s;
  }
  .card h3 .md-btn:hover {
    color: var(--accent); border-color: var(--accent); background: var(--bg-2);
  }
  .card h3 .md-btn[disabled] {
    opacity: 0.4; cursor: not-allowed;
  }
  /* ---- Detail view (两栏布局：sidebar + content) ---- */
  .detail-view {
    display: grid;
    grid-template-columns: 240px 1fr;
    height: calc(100vh - 60px);  /* 减去 header 高度 */
    overflow: hidden;
  }
  .detail-sidebar {
    background: var(--bg-2);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 12px 0;
  }
  .detail-sidebar .back {
    display: block;
    margin: 0 12px 12px;
    padding: 8px 12px;
    color: var(--accent);
    text-decoration: none;
    font-size: 13px; font-weight: 500;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg);
  }
  .detail-sidebar .back:hover {
    background: var(--bg-2);
    border-color: var(--accent);
  }
  .detail-sidebar .repo-title {
    padding: 4px 16px 8px;
    font-size: 13px; font-weight: 600;
    color: var(--fg);
    word-break: break-all;
    border-bottom: 1px solid var(--border);
  }
  .detail-sidebar .repo-meta {
    padding: 4px 16px 10px;
    font-size: 11px;
    color: var(--fg-2);
    border-bottom: 1px solid var(--border);
  }
  .detail-sidebar .repo-actions {
    display: flex; gap: 4px; flex-wrap: wrap;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
  }
  .detail-sidebar .repo-actions a {
    flex: 1; min-width: 0;
    padding: 5px 8px;
    font-size: 11px;
    text-align: center;
    color: var(--fg-2);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 5px;
    text-decoration: none;
    white-space: nowrap;
  }
  .detail-sidebar .repo-actions a:hover {
    color: var(--accent);
    border-color: var(--accent);
  }
  .detail-sidebar .files-label {
    padding: 12px 16px 4px;
    font-size: 11px;
    color: var(--fg-2);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .detail-sidebar ul.files {
    list-style: none; padding: 0; margin: 0;
  }
  .detail-sidebar ul.files li a {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 16px;
    color: var(--fg);
    text-decoration: none;
    font-size: 13px;
    border-left: 3px solid transparent;
  }
  .detail-sidebar ul.files li a:hover {
    background: var(--bg);
  }
  .detail-sidebar ul.files li a.active {
    background: var(--bg-3);
    border-left-color: var(--accent);
    font-weight: 600;
  }
  .detail-sidebar ul.files li a .size {
    margin-left: auto;
    font-size: 10px;
    color: var(--fg-2);
    font-variant-numeric: tabular-nums;
  }
  .detail-sidebar ul.files li a.external {
    color: var(--fg-2);
    font-style: italic;
  }

  .detail-content {
    overflow-y: auto;
    padding: 32px 48px;
    font-size: 15px; line-height: 1.7;
  }
  .detail-content h1, .detail-content h2, .detail-content h3,
  .detail-content h4, .detail-content h5, .detail-content h6 {
    margin-top: 1.4em; margin-bottom: 0.6em;
    line-height: 1.3;
  }
  .detail-content h1:first-child, .detail-content h2:first-child { margin-top: 0; }
  .detail-content p { margin: 0.6em 0; }
  .detail-content code {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.9em;
  }
  .detail-content pre {
    background: #0f172a; color: #e2e8f0;
    padding: 14px 16px; border-radius: 8px;
    overflow-x: auto; line-height: 1.5;
  }
  .detail-content pre code { background: none; padding: 0; color: inherit; }
  .detail-content blockquote {
    margin: 0.8em 0; padding: 4px 16px;
    border-left: 4px solid var(--border);
    color: var(--fg-2);
  }
  .detail-content table {
    border-collapse: collapse; margin: 1em 0;
  }
  .detail-content th, .detail-content td {
    border: 1px solid var(--border); padding: 6px 12px;
  }
  .detail-content a { color: var(--accent); }
  .detail-content img { max-width: 100%; height: auto; }
  .detail-content hr { border: none; border-top: 1px solid var(--border); margin: 1.5em 0; }
  .detail-content ul, .detail-content ol { padding-left: 1.6em; }
  .detail-content .file-source {
    display: inline-block;
    padding: 2px 10px;
    background: var(--bg-3);
    border-radius: 4px;
    font-size: 12px;
    color: var(--fg-2);
    margin-bottom: 16px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  /* 大文件占位卡片 */
  .placeholder {
    text-align: center;
    padding: 80px 24px;
    color: var(--fg-2);
    max-width: 480px;
    margin: 40px auto;
    border: 1px dashed var(--border);
    border-radius: 12px;
  }
  .placeholder .icon { font-size: 48px; margin-bottom: 12px; }
  .placeholder .name { font-size: 18px; color: var(--fg); margin: 0 0 8px; font-weight: 600; }
  .placeholder .reason { font-size: 13px; margin: 0 0 20px; }
  .placeholder .open-btn {
    display: inline-block;
    padding: 10px 22px;
    background: var(--accent);
    color: white;
    border-radius: 6px;
    text-decoration: none;
    font-size: 14px;
  }
  .placeholder .open-btn:hover { opacity: 0.9; }

  /* ---- File System Access 授权横幅 ---- */
  .fs-banner {
    padding: 10px 20px;
    font-size: 13px;
    display: flex; align-items: center; gap: 10px;
    flex-wrap: wrap;
  }
  .fs-banner.fs-prompt {
    background: #fef3c7; color: #78350f;
    border-bottom: 1px solid #fde68a;
  }
  .fs-banner.fs-ok {
    background: #ecfdf5; color: #065f46;
    border-bottom: 1px solid #a7f3d0;
    padding: 6px 20px;
    font-size: 12px;
  }
  .fs-banner.fs-error {
    background: #fef2f2; color: #991b1b;
    border-bottom: 1px solid #fecaca;
  }
  .fs-btn {
    padding: 4px 12px;
    border: 1px solid currentColor;
    border-radius: 5px;
    background: transparent;
    color: inherit;
    font-size: 12px;
    cursor: pointer;
  }
  .fs-btn:hover { background: rgba(0,0,0,.05); }
  .fs-btn-primary {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
    font-weight: 600;
  }
  .fs-btn-primary:hover { background: #1d4ed8; opacity: 1; }
  .fs-banner .close {
    margin-left: auto;
    background: transparent;
    border: none;
    color: inherit;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
    padding: 0 6px;
    opacity: 0.6;
  }
  .fs-banner .close:hover { opacity: 1; }

  /* Header 里的授权状态锁图标 */
  .fs-lock {
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 1px 6px;
    font-size: 13px;
    cursor: pointer;
    margin-left: 4px;
    vertical-align: 2px;
  }
  .fs-lock:hover { background: var(--bg-2); border-color: var(--fg-2); }
  .fs-lock.unauth { opacity: 0.7; }
  /* 锁图标的 popover */
  .fs-popover {
    position: absolute;
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.12);
    padding: 12px 14px;
    font-size: 13px;
    color: var(--fg);
    z-index: 50;
    min-width: 260px;
  }
  .fs-popover h4 { margin: 0 0 6px; font-size: 13px; }
  .fs-popover p { margin: 0 0 8px; color: var(--fg-2); font-size: 12px; }
  .fs-popover .popover-actions {
    display: flex; gap: 6px; margin-top: 8px;
  }
  .fs-popover.hidden { display: none; }

  /* 文件分组（子目录） */
  .files-group {
    padding: 8px 16px 4px;
    font-size: 11px;
    color: var(--fg-2);
    background: var(--bg);
    border-top: 1px solid var(--border);
    font-weight: 600;
  }

  /* 视图切换 */
  #list-view.hidden, #detail-view.hidden { display: none; }
  .card .links {
    font-size: 12px; color: var(--fg-2); margin-top: 4px;
    word-break: break-all;
  }
  .card .links a {
    color: var(--accent); text-decoration: none;
  }
  .card .links a:hover { text-decoration: underline; }
  .card .links div { margin-top: 3px; }
  .card .footer {
    margin-top: 10px; padding-top: 8px;
    border-top: 1px solid var(--border);
    font-size: 11px; color: var(--fg-2);
    display: flex; justify-content: space-between; gap: 8px;
  }
  .empty {
    text-align: center; padding: 80px 20px;
    color: var(--fg-2);
  }
  footer {
    padding: 24px 28px;
    color: var(--fg-2); font-size: 12px; text-align: center;
  }
</style>
<!-- Markdown 渲染：marked.js (15 KB) + DOMPurify (sanitize, 防 XSS)。CDN 加载，GitHub Pages 和本机 file:// 都能跑。 -->
<script src="https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js"></script>
</head>
<body>

<!-- File System Access 状态横幅（顶部，根据授权状态切换样式） -->
<div id="fs-banner" class="fs-banner"></div>

<header>
  <h1>📁 Code 文件夹仪表盘 <button type="button" id="fs-lock" class="fs-lock" title="授权状态">🔓</button></h1>
  <div class="meta" id="meta">加载中…</div>
</header>

<main id="list-view">
  <div class="toolbar">
    <input type="search" id="search" placeholder="搜索仓库名…" autocomplete="off">
    <div class="filter-group" id="filters"></div>
    <select id="sort">
      <option value="name">按名称</option>
      <option value="type">按类型</option>
      <option value="last_scanned">按最近扫描</option>
    </select>
    <div class="count" id="count">—</div>
  </div>
  <div style="padding: 22px 28px;">
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty" style="display:none">没有匹配的仓库</div>
  </div>
</main>

<!-- 详情页：默认隐藏，hash 路由切到 #/repo/<name> 时显示 -->
<div id="detail-view" class="detail-view hidden">
  <aside class="detail-sidebar" id="detail-sidebar"></aside>
  <section class="detail-content" id="detail-content"></section>
</div>

<footer id="page-footer">
  数据源: <code>data/c-code-repos.json</code> · 生成于 <span id="built"></span>
  · <kbd>Esc</kbd> 返回列表 · <kbd>←/→</kbd> 切换文件
</footer>

<script id="dashboard-data" type="application/json">__DATA__</script>
<script>
(function(){
  const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
  const TYPE_META = __TYPE_META__;

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
  const link = (url, label) =>
    `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>`;

  // 类型分布
  const byType = {};
  DATA.repos.forEach(r => { byType[r.type] = (byType[r.type]||0) + 1; });
  const dist = Object.keys(TYPE_META)
    .map(k => `${TYPE_META[k].label} ${byType[k]||0}`)
    .join(' · ');

  // header meta
  document.getElementById('meta').innerHTML =
    `根目录 <code>${esc(DATA._meta.root_path)}</code> · ` +
    `上次扫描 ${esc(DATA._meta.last_full_scan)} · 共 ${DATA.repos.length} 个 (${esc(dist)})`;

  // 把 root_path + repo.name 拼成本地 file:// URL
  // Windows: C:\Users\gotmo\Code\foo  →  file:///C:/Users/gotmo/Code/foo
  // Unix:    /Users/x/Code/foo       →  file:///Users/x/Code/foo
  const fileUrl = (name) => {
    const root = (DATA._meta.root_path || '').replace(/\\/g, '/');
    const sep = root.endsWith('/') ? '' : '/';
    return 'file:///' + root.replace(/^\/+/, '') + sep + name;
  };

  // filter chips
  const filtersEl = document.getElementById('filters');
  const enabled = new Set(Object.keys(TYPE_META));
  Object.entries(TYPE_META).forEach(([k, v]) => {
    const lab = document.createElement('label');
    lab.dataset.type = k;
    lab.title = v.desc;
    lab.innerHTML = `<span class="dot" style="background:${v.color}"></span>${esc(v.label)}`;
    lab.addEventListener('click', () => {
      if (enabled.has(k)) { enabled.delete(k); lab.classList.add('off'); }
      else                { enabled.add(k);    lab.classList.remove('off'); }
      render();
    });
    filtersEl.appendChild(lab);
  });

  document.getElementById('sort').addEventListener('change', render);
  let q = '';
  document.getElementById('search').addEventListener('input', e => {
    q = e.target.value.trim().toLowerCase();
    render();
  });

  function render() {
    const sort = document.getElementById('sort').value;
    const list = DATA.repos.filter(r => {
      if (!enabled.has(r.type)) return false;
      if (q && !r.name.toLowerCase().includes(q)) return false;
      return true;
    });

    if (sort === 'name')
      list.sort((a,b) => a.name.localeCompare(b.name));
    else if (sort === 'type')
      list.sort((a,b) => (a.type+a.name).localeCompare(b.type+b.name));
    else if (sort === 'last_scanned')
      list.sort((a,b) => (b.last_scanned||'').localeCompare(a.last_scanned||''));

    const grid = document.getElementById('grid');
    const empty = document.getElementById('empty');
    document.getElementById('count').textContent = `${list.length} / ${DATA.repos.length}`;
    if (list.length === 0) { grid.innerHTML = ''; empty.style.display = 'block'; return; }
    empty.style.display = 'none';

    grid.innerHTML = list.map(r => {
      const meta = TYPE_META[r.type] || {label: r.type, color: '#64748b'};
      const parts = [];
      // 去重：规范化后的 URL 完全相同就只显示一次（先到先得）。
      // 例：upstream-clone 的 origin 和 source_star 经常指向同一仓库。
      const shown = new Set();
      const add = (label, url, fallback) => {
        if (url) {
          const norm = url.replace(/\.git$/, '').replace(/\/$/, '').toLowerCase();
          if (shown.has(norm)) return;
          shown.add(norm);
          parts.push(`<div>${label} ${link(url, url)}</div>`);
        } else if (fallback) {
          parts.push(`<div>${label} ${esc(fallback)}</div>`);
        }
      };
      add('origin:',     r.origin_web,    r.origin);
      add('upstream:',   r.upstream_web,  r.upstream);
      add('parent:',     r.parent_web,    r.parent);
      add('★ starred:',  r.source_star_url, r.source_star);
      if (r.notes) parts.push(`<div>📝 ${esc(r.notes)}</div>`);

      // md 按钮：现在 .md 是运行时扫的（File System Access），所以按钮始终启用。
      // 真没文件的话点进去会显示"未在授权目录下找到该文件夹，或仓库内无 .md 文件"。
      const mdBtn = `<button type="button" class="md-btn" data-md-repo="${esc(r.name)}"
            title="阅读 markdown 文档">📖 文档</button>`;

      return `
        <div class="card">
          <h3>
            <span class="badge" style="background:${meta.color}">${esc(meta.label)}</span>
            ${link(r.origin || '#', r.name)}
            ${mdBtn}
            <a class="local-btn" href="${esc(fileUrl(r.name))}"
               title="打开本地文件夹 ${esc(DATA._meta.root_path + '\\' + r.name)}">📂 本地</a>
          </h3>
          <div class="links">${parts.join('')}</div>
          <div class="footer">
            <span>${esc(r.name)}</span>
            <span>${esc((r.last_scanned||'').slice(0,19))}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  document.getElementById('built').textContent = __BUILT__;
  render();

  // -------- File System Access（运行时读盘，不嵌 md） --------
  // 用户授权 C:\Users\gotmo\Code 后，浏览器拿 handle，所有 .md 实时从磁盘读。
  // handle 存 IndexedDB，下次自动恢复。
  const FS_DB = 'gh-dashboard-fs';
  const FS_STORE = 'handles';

  const hasFS = 'showDirectoryPicker' in window;

  let rootHandle = null;       // 用户授权的根目录 handle
  let authPromptShown = false; // 避免反复弹授权横幅
  // 当前详情页仓库的文件列表（[{relpath, handle, size, depth}, ...]）
  let currentFiles = [];
  // 文件内容缓存（key=绝对 handle 引用，避免重复读盘）
  const contentCache = new Map();

  const bannerEl = document.getElementById('fs-banner');
  const lockBtn = document.getElementById('fs-lock');
  const BANNER_DISMISSED = 'gh-dashboard.fsBannerDismissed';

  // ---- 授权状态 popover（点 header 🔓 时弹出）----
  let popoverEl = null;
  function showLockPopover() {
    hideLockPopover();
    popoverEl = document.createElement('div');
    popoverEl.className = 'fs-popover';
    const path = esc(DATA._meta.root_path);
    const statusHtml = rootHandle
      ? `<h4>✅ 已授权</h4><p>已授权根目录 <code>${path}</code></p>
         <div class="popover-actions">
           <button type="button" class="fs-btn" id="pop-reauth">重新授权</button>
           <button type="button" class="fs-btn" id="pop-clear">清除授权</button>
         </div>`
      : `<h4>⚠ 未授权</h4><p>需要授权 <code>${path}</code> 才能查看 markdown 文档。</p>
         <div class="popover-actions">
           <button type="button" class="fs-btn fs-btn-primary" id="pop-auth">点击授权</button>
         </div>`;
    popoverEl.innerHTML = statusHtml;
    // 定位到 lockBtn 旁边
    document.body.appendChild(popoverEl);
    const r = lockBtn.getBoundingClientRect();
    popoverEl.style.top = (r.bottom + 6) + 'px';
    popoverEl.style.left = r.left + 'px';
    // 事件
    const reauth = popoverEl.querySelector('#pop-reauth');
    const clear  = popoverEl.querySelector('#pop-clear');
    const auth   = popoverEl.querySelector('#pop-auth');
    if (reauth) reauth.addEventListener('click', () => { hideLockPopover(); requestAccess(); });
    if (clear)  clear.addEventListener('click',  clearAuth);
    if (auth)   auth.addEventListener('click',   () => { hideLockPopover(); requestAccess(); });
    // 点别处关闭
    setTimeout(() => {
      document.addEventListener('click', outsideClose, {once: true});
    }, 0);
  }
  function hideLockPopover() {
    if (popoverEl) { popoverEl.remove(); popoverEl = null; }
  }
  function outsideClose(e) {
    if (popoverEl && !popoverEl.contains(e.target) && e.target !== lockBtn) {
      hideLockPopover();
    } else if (popoverEl) {
      setTimeout(() => document.addEventListener('click', outsideClose, {once: true}), 0);
    }
  }
  lockBtn.addEventListener('click', e => {
    e.stopPropagation();
    if (popoverEl) hideLockPopover(); else showLockPopover();
  });

  // 更新锁图标状态
  function updateLockIcon() {
    lockBtn.textContent = rootHandle ? '🔓' : '🔒';
    lockBtn.classList.toggle('unauth', !rootHandle);
    lockBtn.title = rootHandle ? `已授权: ${DATA._meta.root_path}` : '未授权 — 点击授权';
  }

  // 清除授权（IndexedDB + 清空 handle + 显示提示横幅）
  async function clearAuth() {
    hideLockPopover();
    if (!confirm('清除本地授权记录？\n\n下次访问 dashboard 时需要重新授权 Code 文件夹。')) return;
    try {
      const db = await openDB();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(FS_STORE, 'readwrite');
        tx.objectStore(FS_STORE).delete('root');
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
      localStorage.removeItem(BANNER_DISMISSED);
    } catch (err) {
      console.warn('清除授权失败:', err);
    }
    rootHandle = null;
    updateLockIcon();
    showAuthPrompt();
  }

  // Banner 显示 / 关闭
  function dismissBanner() {
    bannerEl.style.display = 'none';
    localStorage.setItem(BANNER_DISMISSED, '1');
  }
  function bannerCloseBtn() {
    return `<button type="button" class="close" title="关闭" aria-label="关闭">×</button>`;
  }

  // 浏览器支持检测：Firefox / 老 Safari 等
  if (!hasFS) {
    bannerEl.className = 'fs-banner fs-error';
    bannerEl.innerHTML = `⚠ 当前浏览器不支持 <code>File System Access API</code>。
      请用 <strong>Chrome / Edge</strong>（桌面版）打开此页面。
      <a href="https://caniuse.com/native-filesystem-api" target="_blank" rel="noopener">兼容性参考</a>
      ${bannerCloseBtn()}`;
    bannerEl.querySelector('.close').addEventListener('click', dismissBanner);
    updateLockIcon();  // 🔒
  } else {
    updateLockIcon();  // 先假设无 handle，🔒
    // 异步恢复 handle（不阻塞渲染）
    restoreHandle().then(h => {
      rootHandle = h;
      updateLockIcon();
      if (rootHandle) {
        // 已授权：默认不显示横幅（除非用户没关过）
        if (localStorage.getItem(BANNER_DISMISSED) !== '1') {
          bannerEl.className = 'fs-banner fs-ok';
          bannerEl.innerHTML = `✅ 已授权 <code>${esc(DATA._meta.root_path)}</code>
            <button type="button" class="fs-btn" id="fs-reauth">重新授权</button>
            ${bannerCloseBtn()}`;
          bannerEl.querySelector('#fs-reauth').addEventListener('click', requestAccess);
          bannerEl.querySelector('.close').addEventListener('click', dismissBanner);
        } else {
          bannerEl.style.display = 'none';
        }
        // 如果当前在详情页，触发重新渲染（拿到 handle 后才能加载文件）
        if (parseHash().view === 'detail') renderRoute();
      } else if (!authPromptShown) {
        showAuthPrompt();
      }
    }).catch(err => {
      console.warn('恢复 handle 失败:', err);
      showAuthPrompt();
    });
  }

  function showAuthPrompt() {
    authPromptShown = true;
    bannerEl.style.display = '';
    bannerEl.className = 'fs-banner fs-prompt';
    bannerEl.innerHTML = `📂 请授权你的 <code>Code</code> 文件夹
      （仅本次会话可读；浏览器会记住权限，下次不再询问）
      <button type="button" class="fs-btn fs-btn-primary" id="fs-auth">点击授权</button>`;
    document.getElementById('fs-auth').addEventListener('click', requestAccess);
  }

  async function requestAccess() {
    try {
      const h = await window.showDirectoryPicker({mode: 'read', id: 'code-root'});
      // 验证 handle 路径跟 _meta.root_path 一致（防用户授权错文件夹）
      // 注意：handle 没有暴露 path，只能让用户看着办
      rootHandle = h;
      await saveHandle(h);
      authPromptShown = false;
      updateLockIcon();
      // 授权成功 → 自动关闭横幅
      localStorage.setItem(BANNER_DISMISSED, '1');
      bannerEl.style.display = 'none';
      renderRoute();  // 重新渲染当前页（拿到 handle 后才能加载文件）
    } catch (err) {
      // 用户取消授权
      console.warn('用户取消授权:', err);
      showAuthPrompt();
    }
  }

  // ---- IndexedDB: 持久化 handle ----
  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(FS_DB, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(FS_STORE)) db.createObjectStore(FS_STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function saveHandle(h) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(FS_STORE, 'readwrite');
      tx.objectStore(FS_STORE).put(h, 'root');
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async function restoreHandle() {
    if (!hasFS) return null;
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(FS_STORE, 'readonly');
      const req = tx.objectStore(FS_STORE).get('root');
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => resolve(null);
    });
  }

  // ---- 递归扫 .md 文件（带黑名单 + 深度限制） ----
  // 策略：黑名单目录直接跳；其他递归 max 2 层；多语言 README / LICENSE 类过滤掉。
  // 文档型仓库（hermes-agent 1391 个 .md）深度限制 + 文件数上限避免 sidebar 爆炸。
  const SKIP_DIRS = new Set([
    // 构建/依赖
    'node_modules', '.git', 'dist', 'build', '.next', '.nuxt',
    '.venv', 'venv', '__pycache__', 'target', 'vendor', '.idea', '.vscode',
    '.obsidian',
  ]);
  const MAX_DEPTH = 2;
  const MAX_FILES_PER_REPO = 100;

  // 多语言 README 变体（如 README.ar.md / README.zh.md）—— 与 README.md 重复
  function isLocalizedReadme(name) {
    const m = name.match(/^README\.([a-z]{2,3}(-[A-Z]{2})?)\.md$/i);
    return !!m;
  }

  async function scanRepoMd(repoHandle) {
    const out = [];
    async function walk(dirHandle, depth, baseRel) {
      if (depth > MAX_DEPTH || out.length >= MAX_FILES_PER_REPO) return;
      for await (const [name, handle] of dirHandle.entries()) {
        if (out.length >= MAX_FILES_PER_REPO) return;
        if (handle.kind === 'directory') {
          if (SKIP_DIRS.has(name)) continue;
          const childBase = baseRel ? baseRel + '/' + name : name;
          await walk(handle, depth + 1, childBase);
        } else if (handle.kind === 'file' && name.toLowerCase().endsWith('.md')) {
          if (isLocalizedReadme(name)) continue;
          if (/^LICENSE/i.test(name)) continue;
          const file = await handle.getFile();
          out.push({
            relpath: baseRel ? baseRel + '/' + name : name,
            handle: handle,
            size: file.size,
            name: name,
            depth: depth,
          });
        }
      }
    }
    await walk(repoHandle, 0, '');
    // 排序：根目录 README → 根目录其他 → 子目录
    out.sort((a, b) => {
      const keyA = (a.depth === 0 ? '0' : '1')
                 + (a.name.toUpperCase().startsWith('README') ? '0' : '1')
                 + a.relpath.toLowerCase();
      const keyB = (b.depth === 0 ? '0' : '1')
                 + (b.name.toUpperCase().startsWith('README') ? '0' : '1')
                 + b.relpath.toLowerCase();
      return keyA.localeCompare(keyB);
    });
    return out;
  }

  async function getRepoFiles(repoName) {
    if (!rootHandle) return [];
    try {
      const repoHandle = await rootHandle.getDirectoryHandle(repoName, {create: false});
      return await scanRepoMd(repoHandle);
    } catch (err) {
      // 仓库文件夹不在授权的根目录下 / 不存在
      return [];
    }
  }

  async function readFile(fileEntry) {
    if (contentCache.has(fileEntry)) return contentCache.get(fileEntry);
    const f = await fileEntry.handle.getFile();
    const text = await f.text();
    contentCache.set(fileEntry, text);
    return text;
  }

  // -------- Hash Router --------
  // URL 协议：
  //   #/                                  → 列表页
  //   #/repo/<repo-name>                  → 详情页（默认显示 README 系列第一个）
  //   #/repo/<repo-name>/<file>           → 详情页指定文件（file 用 URL 编码的 relpath）
  //
  // 用 location.hash 是因为：
  //   - 单文件、双击 file:// 也能用
  //   - 浏览器前进/后退自动工作
  //   - URL 可分享、可深链
  const listView = document.getElementById('list-view');
  const detailView = document.getElementById('detail-view');
  const sidebarEl = document.getElementById('detail-sidebar');
  const contentEl = document.getElementById('detail-content');

  let currentRepo = null;
  let currentFileIdx = 0;

  function parseHash() {
    const h = (location.hash || '').replace(/^#\/?/, '');
    if (!h) return {view: 'list'};
    const m = h.match(/^repo\/([^/]+)(?:\/(.+))?$/);
    if (!m) return {view: 'list'};
    return {view: 'detail', repo: decodeURIComponent(m[1]), file: m[2] ? decodeURIComponent(m[2]) : null};
  }

  function navigate(hash) {
    if (location.hash === hash) renderRoute();
    else location.hash = hash;
  }

  function renderRoute() {
    const route = parseHash();
    if (route.view === 'list') { showList(); return; }
    const repo = DATA.repos.find(r => r.name === route.repo);
    if (!repo) { showList(); return; }
    showDetail(repo, route.file);
  }

  function showList() {
    listView.classList.remove('hidden');
    detailView.classList.add('hidden');
    document.getElementById('page-footer').style.display = '';
    currentRepo = null;
    currentFiles = [];
    document.title = 'Code 文件夹仪表盘';
  }

  async function showDetail(repo, fileName) {
    currentRepo = repo;
    listView.classList.add('hidden');
    detailView.classList.remove('hidden');
    document.getElementById('page-footer').style.display = 'none';
    document.title = `${repo.name} · Code 仪表盘`;

    if (!rootHandle) {
      sidebarEl.innerHTML = `<a class="back" href="#/">← 返回列表</a>
        <div class="repo-title">${esc(repo.name)}</div>
        <div style="padding: 20px; color: var(--fg-2); font-size: 13px;">
          请先在顶部点击 <strong>📂 授权</strong> 按钮，授权你的 Code 文件夹后才能查看 markdown 文档。
        </div>`;
      contentEl.innerHTML = '';
      return;
    }

    // 加载文件列表（首次慢，后续走 cache）
    currentFiles = await getRepoFiles(repo.name);
    renderSidebar(repo);

    if (currentFiles.length === 0) {
      contentEl.innerHTML = `<div class="placeholder">
        <div class="icon">📂</div>
        <p class="name">${esc(repo.name)}</p>
        <p class="reason">未在授权目录下找到该文件夹，或仓库内无 .md 文件</p>
      </div>`;
      return;
    }

    // 选文件：参数指定 → README 优先 → 第一个
    let idx = 0;
    if (fileName) {
      const found = currentFiles.findIndex(f => f.relpath === fileName);
      idx = found >= 0 ? found : 0;
    }
    currentFileIdx = idx;
    await renderFile(currentFiles[idx]);
    sidebarEl.querySelectorAll('a[data-idx]').forEach((a, i) => {
      a.classList.toggle('active', i === idx);
    });
  }

  function renderSidebar(repo) {
    const meta = TYPE_META[repo.type] || {label: repo.type, color: '#64748b'};
    // 按 depth 分组（更清晰的视觉）
    const groups = new Map();
    currentFiles.forEach((f, i) => {
      const dir = f.depth === 0 ? '' : f.relpath.includes('/') ? f.relpath.slice(0, f.relpath.lastIndexOf('/')) : '';
      if (!groups.has(dir)) groups.set(dir, []);
      groups.get(dir).push({file: f, idx: i});
    });
    const renderItem = ({file, idx}) => {
      const size = file.size < 1024 ? file.size + ' B' : (file.size / 1024).toFixed(1) + ' KB';
      return `<li><a href="#/repo/${encodeURIComponent(repo.name)}/${encodeURIComponent(file.relpath)}"
                  data-idx="${idx}">
                📄 ${esc(file.relpath)}<span class="size">${esc(size)}</span>
              </a></li>`;
    };
    const groupsHtml = [...groups.entries()].map(([dir, items]) => {
      const header = dir ? `<div class="files-group">📁 ${esc(dir)}/</div>` : '';
      return header + `<ul class="files">${items.map(renderItem).join('')}</ul>`;
    }).join('') || '<div style="padding:8px 16px;color:var(--fg-2);font-size:12px">无 .md 文件</div>';

    const ghLink = repo.origin_web || repo.origin || '#';
    sidebarEl.innerHTML = `
      <a class="back" href="#/">← 返回列表</a>
      <div class="repo-title">
        <span class="badge" style="background:${meta.color}">${esc(meta.label)}</span>
        ${esc(repo.name)}
      </div>
      <div class="repo-meta">
        共 ${currentFiles.length} 个 .md${currentFiles.length >= MAX_FILES_PER_REPO ? ' (已截断)' : ''}
      </div>
      <div class="repo-actions">
        <a href="${esc(ghLink)}" target="_blank" rel="noopener" title="在 GitHub 查看">🔗 GitHub</a>
        <a href="${esc(fileUrl(repo.name))}" title="打开本地文件夹">📂 本地</a>
      </div>
      ${groupsHtml}
    `;
  }

  async function renderFile(f) {
    if (!f) {
      contentEl.innerHTML = '<p>没有可显示的文件</p>';
      return;
    }
    contentEl.scrollTop = 0;
    const pathLabel = esc((DATA._meta.root_path + '\\' + currentRepo.name + '\\' + f.relpath).replace(/\\/g, '/'));
    const sourceTag = `<span class="file-source">${esc(f.relpath)} · ${pathLabel}</span>`;

    try {
      const text = await readFile(f);
      if (typeof marked === 'undefined') {
        contentEl.innerHTML = sourceTag + '<p style="color:#ef4444">⚠ marked.js 还没加载完，请检查网络</p>';
        return;
      }
      const html = marked.parse(text, {gfm: true, breaks: false});
      const safe = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html) : html;
      contentEl.innerHTML = sourceTag + safe;
    } catch (err) {
      contentEl.innerHTML = sourceTag + `
        <div class="placeholder">
          <div class="icon">⚠</div>
          <p class="name">${esc(f.relpath)}</p>
          <p class="reason">读取失败: ${esc(err.message || String(err))}</p>
        </div>`;
    }
  }

  // 列表卡片点击 📖 按钮 → 跳详情页
  document.getElementById('grid').addEventListener('click', e => {
    const btn = e.target.closest('.md-btn');
    if (!btn || btn.disabled) return;
    const repoName = btn.dataset.mdRepo;
    navigate('#/repo/' + encodeURIComponent(repoName));
  });

  // 键盘快捷键
  document.addEventListener('keydown', e => {
    const route = parseHash();
    if (e.key === 'Escape' && route.view === 'detail') {
      navigate('#/');
    } else if (route.view === 'detail' && currentRepo && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      if (!currentFiles.length) return;
      const curName = currentFiles[currentFileIdx]?.relpath;
      let pos = currentFiles.findIndex(f => f.relpath === curName);
      let nextPos;
      if (e.key === 'ArrowRight') nextPos = (pos + 1) % currentFiles.length;
      else                       nextPos = (pos - 1 + currentFiles.length) % currentFiles.length;
      const nextFile = currentFiles[nextPos];
      navigate('#/repo/' + encodeURIComponent(currentRepo.name) + '/' + encodeURIComponent(nextFile.relpath));
    }
  });

  window.addEventListener('hashchange', renderRoute);
  renderRoute();
})();
</script>

</body>
</html>
"""


def _safe_json_for_script(payload: dict) -> str:
    """嵌入 <script> 之前必须把 </ 转义，避免提早关闭 script 标签。"""
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def build() -> None:
    data, stars = load_inputs()
    root_path = Path(data["_meta"]["root_path"])
    data["repos"] = enrich(data["repos"], stars, root_path)
    data["_built"] = datetime.now().isoformat(timespec="seconds")

    html = (
        HTML_TEMPLATE
        .replace("__DATA__", _safe_json_for_script(data))
        .replace("__TYPE_META__", _safe_json_for_script(TYPE_META))
        .replace("__BUILT__", json.dumps(data["_built"], ensure_ascii=False))
    )

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")

    size_kb = OUT_HTML.stat().st_size / 1024
    print(f"✅ wrote {OUT_HTML.relative_to(ROOT)}  ({size_kb:.1f} KB)")
    print(f"   repos: {len(data['repos'])}    stars mapping: {len(stars)} entries")


if __name__ == "__main__":
    build()