"""生成本地预览入口页 output/index.html。

扫描 output/ 下所有含 book.html 的成品，读取 transcript.json 里的标题/时长/
章节信息，取第一张截图做封面，生成一张卡片式落地页，方便在 http.server 里
一眼看出每本书是什么内容。

用法:
    python make_index.py
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")


def fmt_duration(sec):
    sec = int(round(float(sec or 0)))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    if h:
        return f"{h} 小时 {m} 分" if m else f"{h} 小时"
    if m:
        return f"{m} 分 {s} 秒" if s else f"{m} 分钟"
    return f"{s} 秒"


def seq_key(vid, title):
    """标题里带 [NN-] 序列号时按其排序，否则排在最后。"""
    m = re.search(r"\[(\d+)[-－]", title or "")
    return (int(m.group(1)), title or vid) if m else (10**9, title or vid)


def load_meta(vid):
    p = os.path.join(OUT, vid, "transcript.json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        d = {}
    title = (d.get("title") or vid).strip()
    chapters = d.get("chapters") or []
    return {
        "vid": vid,
        "title": title,
        "duration": d.get("duration", 0),
        "n_chapters": len(chapters),
        "chapters": [c.get("title", "") for c in chapters if c.get("title")],
        "corrected": os.path.isfile(os.path.join(OUT, vid, "transcript.corrected.txt")),
        "thumb": first_thumb(vid),
        "mtime": os.path.getmtime(os.path.join(OUT, vid, "book.html")),
    }


def first_thumb(vid):
    img = os.path.join(OUT, vid, "images")
    if not os.path.isdir(img):
        return None
    pngs = sorted(f for f in os.listdir(img) if f.lower().endswith(".png"))
    return f"{vid}/images/{pngs[0]}" if pngs else None


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(metas):
    cards = []
    for i, m in enumerate(metas):
        href = f"{m['vid']}/book.html"
        thumb = (f'<div class="thumb"><img src="{esc(m["thumb"])}" alt="" loading="lazy"></div>'
                 if m["thumb"] else '<div class="thumb empty-thumb">无封面</div>')
        dur = fmt_duration(m["duration"])
        chapters = f"{m['n_chapters']} 个章节" if m["n_chapters"] else "无章节"
        sub = ('<a class="btn sub" href="%s/transcript.corrected.txt">字幕对照</a>' % esc(m["vid"])
               if m["corrected"] else "")
        if m["chapters"]:
            ch_txt = " · ".join(m["chapters"][:3])
            if len(m["chapters"]) > 3:
                ch_txt += " …"
            chapters += f'<br><span class="ch">{esc(ch_txt)}</span>'
        cards.append(
            f'      <div class="card">\n'
            f'        <a class="stretch" href="{esc(href)}" aria-label="开始阅读"></a>\n'
            f'        {thumb}\n'
            f'        <div class="body">\n'
            f'          <h2>{esc(m["title"])}</h2>\n'
            f'          <p class="meta">{esc(m["vid"])} · {dur} · {chapters}</p>\n'
            f'          <div class="row">{sub}<a class="btn read hb{i % 4}" href="{esc(href)}">开始阅读</a></div>\n'
            f'        </div>\n'
            f'      </div>')
    body = "\n".join(cards) or '      <p class="empty">暂无成品，先跑一遍流水线生成 book.html。</p>'
    return INDEX_TMPL.replace("{body}", body)


INDEX_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>生成式软件工程 · 电子书架</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #f6f7f9; color: #1f2328;
    font-family: "Inter", "Noto Sans SC", system-ui, -apple-system, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased; line-height: 1.7;
  }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 56px 24px 56px; }
  header h1 { font-size: 1.9em; font-weight: 700; letter-spacing: -0.02em; }
  header p { color: #57606a; margin: 8px 0 34px; font-size: .95em; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 22px; }
  .card {
    position: relative;
    display: flex; flex-direction: column; overflow: hidden;
    background: #ffffff; border-radius: 16px;
    box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 24px rgba(15,23,42,.06);
    text-decoration: none; color: inherit;
    transition: transform .18s ease, box-shadow .18s ease;
  }
  .stretch { position: absolute; inset: 0; z-index: 1; }
  .card:hover { transform: translateY(-3px); box-shadow: 0 2px 4px rgba(15,23,42,.05), 0 16px 36px rgba(15,23,42,.11); }
  .thumb { aspect-ratio: 16/9; background: #0f172a; overflow: hidden; }
  .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .empty-thumb { display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: .85em; }
  .body { display: flex; flex-direction: column; gap: 8px; padding: 18px 20px 16px; flex: 1; }
  .body h2 { font-size: 1.05em; font-weight: 600; line-height: 1.45; }
  .meta { color: #6e7781; font-size: .82em; }
  .ch { color: #8b949e; font-size: .92em; }
  .row { position: relative; z-index: 2; display: flex; align-items: center; gap: 10px; margin-top: auto; padding-top: 8px; }
  .btn {
    display: inline-block; background: #f0f1f3; color: #1f2328; border-radius: 10px;
    padding: 7px 13px; font-size: .82em; font-weight: 500; text-decoration: none;
  }
  .btn:hover { background: #e4e6ea; }
  .btn.read { margin-left: auto; }
  .read.hb0:hover { background: linear-gradient(135deg,#dbeafe,#e0e7ff); }
  .read.hb1:hover { background: linear-gradient(135deg,#ede9fe,#fce7f3); }
  .read.hb2:hover { background: linear-gradient(135deg,#dcfce7,#dbeafe); }
  .read.hb3:hover { background: linear-gradient(135deg,#fef3c7,#fce7f3); }
  .empty { color: #6e7781; }
  footer { margin-top: 44px; color: #8b949e; font-size: .8em; text-align: center; }
  @media (max-width: 500px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>生成式软件工程 · 电子书架</h1>
      <p>由 VideoBook 流水线自动生成 · 内容衍生自 B 站公开课程视频</p>
    </header>
    <div class="grid">
{body}
    </div>
    <footer>本地预览入口 · 刷新前请重新运行 make_index.py 以收录新书</footer>
  </div>
</body>
</html>
"""


def main():
    ids = [d for d in sorted(os.listdir(OUT))
           if os.path.isfile(os.path.join(OUT, d, "book.html"))]
    if not ids:
        sys.exit("output/ 下暂无 book.html")
    metas = [load_meta(v) for v in ids]
    metas.sort(key=lambda m: (seq_key(m["vid"], m["title"])[0], -m["mtime"]))
    out = os.path.join(OUT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build(metas))
    for m in metas:
        print(f">> {m['vid']}  {m['title'][:40]}  {fmt_duration(m['duration'])}  {m['n_chapters']}章节")
    print(f"\n入口页已生成: {out}")


if __name__ == "__main__":
    main()
