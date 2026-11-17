import os, re, json, sys

base = os.path.dirname(__file__)
os.chdir(os.path.join(os.path.dirname(base), "trending-readme"))
result = {}
for f in sorted(os.listdir(".")):
    if not f.endswith((".md", ".rst", ".txt", ".adoc")):
        continue
    with open(f, encoding="utf-8", errors="replace") as fh:
        text = fh.read(4000)
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else ""
    desc = ""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "!", "[", "<", "|", "-", "*", ">", "`")):
            continue
        if len(s) > 15:
            desc = s[:150]
            break
    result[f] = {"title": title, "desc": desc}

out = sys.argv[1] if len(sys.argv) > 1 else "titles.json"
with open(out, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)
print(f"wrote {out}: {len(result)} entries")
