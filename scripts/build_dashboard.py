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


def enrich(repos: list[dict], stars: dict) -> list[dict]:
    """为每条记录补全规范化后的 https URL 字段（origin/upstream/parent）。
    source_star 从本地 stars_mapping.json 解析出对应 GitHub URL，不调 API。
    """
    out = []
    for r in repos:
        r2 = dict(r)
        r2["origin_web"]    = normalize_github_url(r.get("origin"))
        r2["upstream_web"]  = normalize_github_url(r.get("upstream"))
        r2["parent_web"]    = normalize_github_url(r.get("parent"))
        src = r.get("source_star")
        r2["source_star_url"] = stars.get(src) if src else None
        out.append(r2)
    return out


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
    padding: 20px 28px;
    background: var(--bg-2); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 10;
  }
  h1 { margin: 0 0 4px; font-size: 20px; }
  header .meta { color: var(--fg-2); font-size: 12px; }
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
  .badge {
    display: inline-block;
    padding: 2px 9px; border-radius: 12px;
    font-size: 11px; font-weight: 600; color: white;
    flex-shrink: 0;
  }
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
</head>
<body>

<header>
  <h1>📁 Code 文件夹仪表盘</h1>
  <div class="meta" id="meta">加载中…</div>
</header>

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

<main>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">没有匹配的仓库</div>
</main>

<footer>
  数据源: <code>data/c-code-repos.json</code> · 生成于 <span id="built"></span>
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
      if (r.origin_web)  parts.push(`<div>origin: ${link(r.origin_web, r.origin_web)}</div>`);
      else if (r.origin) parts.push(`<div>origin: ${esc(r.origin)}</div>`);
      if (r.upstream_web) parts.push(`<div>upstream: ${link(r.upstream_web, r.upstream_web)}</div>`);
      if (r.parent_web)   parts.push(`<div>parent: ${link(r.parent_web, r.parent_web)}</div>`);
      if (r.source_star_url)
        parts.push(`<div>★ starred: ${link(r.source_star_url, r.source_star_url)}</div>`);
      else if (r.source_star)
        parts.push(`<div>★ starred: ${esc(r.source_star)}</div>`);
      if (r.notes) parts.push(`<div>📝 ${esc(r.notes)}</div>`);

      return `
        <div class="card">
          <h3>
            <span class="badge" style="background:${meta.color}">${esc(meta.label)}</span>
            ${link(r.origin || '#', r.name)}
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
    data["repos"] = enrich(data["repos"], stars)
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