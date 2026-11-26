# -*- coding: utf-8 -*-
"""把 VPS套餐清单 md 转成单文件 HTML（内嵌样式 + 交互脚本）"""
import html
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(BASE, "VPS套餐清单_2026-11.md")
OUT = os.path.join(BASE, "VPS套餐清单_2026-11.html")

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def esc(s):
    return html.escape(s, quote=False).replace("&amp;", "&")


def inline(text):
    """行内渲染：链接 / 粗体 / code / <br>"""
    store = []

    def keep_link(m):
        store.append((m.group(1), m.group(2)))
        return f"\x01{len(store)-1}\x01"

    t = LINK_RE.sub(keep_link, text)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("&lt;br&gt;", "<br>")
    t = CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", t)
    t = BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", t)

    def put_link(m):
        label, url = store[int(m.group(1))]
        label_html = BOLD_RE.sub(lambda k: f"<strong>{k.group(1)}</strong>",
                                 label.replace("&", "&amp;").replace("<", "&lt;"))
        u = url.replace("&", "&amp;")
        return (f'<a href="{u}" target="_blank" rel="noopener">{label_html}'
                f'<span class="ext">↗</span></a>')

    t = re.sub("\x01(\\d+)\x01", put_link, t)
    return t


def badge_cell(html_cell, raw_cell):
    """给状态列加标签样式"""
    raw = raw_cell.strip()
    if raw.startswith("✅"):
        return f'<span class="tag ok">{html_cell}</span>'
    if raw.startswith("⚠️") or raw.startswith("⚠"):
        return f'<span class="tag warn">{html_cell}</span>'
    if raw.startswith("❌"):
        return f'<span class="tag bad">{html_cell}</span>'
    if "🔥" in raw:
        return f'<span class="tag fire">{html_cell}</span>'
    if raw.startswith("⭐"):
        return f'<span class="tag star">{html_cell}</span>'
    return html_cell


def IS_REC(t):
    return bool(re.match(r"^\d+\.\s*CN2 GIA", re.sub(r"[*`]", "", t)))


def render_table(rows, tid):
    head = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    body = rows[2:]
    out = [f'<div class="tw" data-tid="{tid}"><table>', "<thead><tr>"]
    for h in head:
        hcls = ' class="col-rec"' if ("推荐" in h and "方案" in h) else ""
        out.append(f"<th{hcls}>{inline(h)}</th>")
    out.append("</tr></thead><tbody>")
    for r in body:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        p0 = re.sub(r"[*`\s]", "", cells[0]) if cells else ""
        if any(chr(9733) in c for c in cells):
            out.append('<tr class="rec-row">')
        elif p0 == "价格" and len(cells) >= 4:
            out.append('<tr class="price-row">')
        else:
            out.append("<tr>")
        for i, c in enumerate(cells):
            cls = ' class="name"' if i == 0 else ""
            inner = inline(c)
            inner = inner.replace("需自备云前置机",
                                  '<span class="ixp-req">需自备云前置机</span>')
            if i > 0 and i < 8:
                inner = badge_cell(inner, c)
            inner = inner.replace(chr(9733), '<span class="rec-badge">本清单首选</span>')
            out.append(f"<td{cls}>{inner}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def parse(md_text):
    rec_open = [False]
    lines = md_text.split("\n")
    blocks = []
    toc = []
    i = 0
    tid = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # 代码块（围栏）
        if s.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append('<pre><code>%s</code></pre>' % esc("\n".join(buf)))
            continue

        # 表格
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            if len(rows) >= 3:
                tid += 1
                blocks.append(render_table(rows, tid))
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2)
            plain = re.sub(r"[*`]", "", txt)
            if rec_open[0] and lvl <= 2:
                blocks.append("</div>")
                rec_open[0] = False
            if lvl == 1:
                if not blocks:
                    blocks.append(f'<h1 class="doc-title">{inline(txt)}</h1>')
                else:
                    anchor = f"g{len(toc)}"
                    toc.append((1, plain, anchor))
                    rec = ' <span class="rec-badge">推荐</span>' if "CN2 GIA" in plain else ""
                    blocks.append(
                        f'<h2 class="group" id="{anchor}"><span>{inline(txt)}{rec}</span></h2>')
            elif lvl == 2 and plain.strip() == "推荐":
                toc.append((2, "推荐", "rec"))
                blocks.append(
                    '<div class="rec-hero" id="rec">'
                    '<div class="rec-hero-h">推荐</div>')
                rec_open[0] = True
            elif lvl == 2:
                anchor = f"g{len(toc)}"
                toc.append((2, plain, anchor))
                rec2 = ' <span class="rec-badge">推荐</span>' if IS_REC(plain) else ""
                blocks.append(
                    f'<h3 class="merchant" id="{anchor}">{inline(txt)}{rec2}</h3>')
            else:
                cls = "sub step" if txt.startswith("步骤") else "sub"
                blocks.append(f'<h4 class="{cls}">{inline(txt)}</h4>')
            i += 1
            continue

        # 引用
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(f'<blockquote>{inline(" ".join(buf))}</blockquote>')
            continue

        # 分隔线
        if re.match(r"^-{3,}$", s):
            blocks.append('<hr>')
            i += 1
            continue

        # 列表
        if re.match(r"^[-*]\s+", s):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            li = "".join(f"<li>{inline(x)}</li>" for x in items)
            blocks.append(f"<ul>{li}</ul>")
            continue

        # 普通段落
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(\||#|>|-{3,}|[-*]\s)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            if rec_open[0]:
                blocks.append(
                    '<div class="rec-hero-b">%s</div>' % inline("<br>".join(buf)))
            else:
                blocks.append(f"<p>{inline('<br>'.join(buf))}</p>")
        else:
            i += 1
    return blocks, toc


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>高性价比 VPS 套餐清单 · 2026-11</title>
<style>
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#f5f7fb; --card:#fff; --line:#e6eaf2; --ink:#151d2e; --sub:#5b6b85;
  --brand:#4f46e5; --brand-soft:#eef0ff;
  --fire:#f97316; --fire-soft:#fff2e8;
  --ok:#0f9d58; --ok-soft:#e8f6ee;
  --warn:#c47d00; --warn-soft:#fff6e0;
  --bad:#dc2626; --bad-soft:#fdecec;
  --star:#2563eb; --star-soft:#e8f0fe;
}
html{scroll-behavior:smooth}
[id]{scroll-margin-top:72px}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;
}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}
pre{background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:8px;overflow-x:auto;margin:10px 0;font:13px/1.7 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;line-height:1.7}
pre code{background:none;color:inherit;padding:0;border-radius:0;font:inherit}
code{background:#eef1f7;padding:.1em .38em;border-radius:4px;font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#374151}

/* ---------- 顶部 ---------- */
header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.86);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.bar{max-width:1680px;margin:0 auto;padding:12px 28px;display:flex;align-items:center;justify-content:space-between;gap:18px}
.logo{font-weight:700;font-size:15px;letter-spacing:.2px;white-space:nowrap}
.logo em{font-style:normal;color:var(--brand)}
.spacer{flex:1}
.search{position:relative}
.search input{
  width:290px;padding:9px 14px 9px 34px;border:1px solid var(--line);border-radius:9px;
  background:#fff;font-size:14px;color:var(--ink);outline:none;transition:.15s
}
.search input:focus{border-color:var(--brand);box-shadow:0 0 0 3px var(--brand-soft)}
.search svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);width:15px;height:15px;fill:var(--sub)}
.toggle{display:flex;align-items:center;gap:7px;font-size:13.5px;color:var(--sub);cursor:pointer;user-select:none;white-space:nowrap}
.toggle input{width:15px;height:15px;accent-color:var(--fire);cursor:pointer}

/* ---------- 布局 ---------- */
.wrap{max-width:1680px;margin:0 auto;padding:26px 28px 90px;display:grid;grid-template-columns:252px minmax(0,1fr);gap:34px}
nav{position:sticky;top:78px;align-self:start;max-height:calc(100vh - 104px);overflow:auto;padding-right:6px}
nav::-webkit-scrollbar{width:6px}
nav::-webkit-scrollbar-thumb{background:#d7dee9;border-radius:3px}
nav .nlabel{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#93a1b6;margin:0 0 10px 10px;font-weight:600}
nav a{display:block;padding:6px 10px;border-radius:7px;font-size:13.5px;color:var(--sub);border-left:2px solid transparent;transition:.12s;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
nav a:hover{background:#eef1f7;color:var(--ink);text-decoration:none}
nav a.grp{font-weight:650;color:var(--ink);margin-top:12px;font-size:13px}
nav a.cur{background:var(--brand-soft);color:var(--brand);border-left-color:var(--brand);font-weight:600}

/* ---------- 正文 ---------- */
main{min-width:0}
.doc-title{font-size:31px;line-height:1.3;margin:2px 0 6px;letter-spacing:-.4px}
.doc-title + p{margin-top:4px}
h2.group{
  font-size:20px;margin:46px 0 16px;padding-left:14px;position:relative;letter-spacing:-.2px;
}
h2.group::before{content:"";position:absolute;left:0;top:3px;bottom:3px;width:4px;border-radius:2px;background:linear-gradient(180deg,var(--brand),#8b5cf6)}
h2.group:first-of-type{margin-top:14px}
h3.merchant{font-size:17.5px;margin:30px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line);letter-spacing:-.1px}
.ixp-req{color:#dc2626;font-weight:700}
th.col-rec{color:var(--bad);font-weight:800;background:#fff1f2}
tr.price-row td{color:var(--bad);font-weight:600}
tr.price-row td:first-child{font-weight:800}
tr.price-row strong{color:var(--bad)}
.rec-badge{display:inline-block;padding:1px 8px;border-radius:999px;background:#dc2626;color:#fff;font-size:11px;font-weight:700;line-height:1.7;vertical-align:middle;white-space:nowrap}
tr.rec-row td{background:#fff1f2!important;border-top:1px solid #fecdd3;border-bottom:1px solid #fecdd3}
tr.rec-row td:first-child{box-shadow:inset 3px 0 0 #dc2626}
tr.rec-row:hover td{background:#ffe4e6!important}
h4.step{font-size:16px;margin:26px 0 10px;color:var(--ink);font-weight:700;padding-left:10px;border-left:3px solid var(--brand);background:linear-gradient(90deg,var(--brand-soft),transparent 70%)}h4.step:first-of-type{margin-top:20px}h4.sub{font-size:14px;margin:22px 0 10px;color:var(--sub);font-weight:650}
p{margin:10px 0}
ul{margin:10px 0;padding-left:22px}
li{margin:5px 0}
hr{border:0;border-top:1px dashed var(--line);margin:38px 0}
blockquote{
  margin:14px 0;padding:13px 17px;border-radius:10px;font-size:14.2px;
  background:linear-gradient(90deg,#fffaf3,#fffdf9);border:1px solid #fde9cf;border-left:3px solid var(--fire);
  color:#5a4630
}
blockquote strong{color:#b45309}

/* ---------- 表格 ---------- */
.tw{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:12px;margin:12px 0 4px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.tw::-webkit-scrollbar{height:9px}
.tw::-webkit-scrollbar-thumb{background:#d7dee9;border-radius:5px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:13.3px}
thead th{
  position:sticky;top:0;z-index:2;background:#f8fafc;text-align:left;font-weight:650;color:#445068;
  padding:10px 13px;white-space:nowrap;border-bottom:1px solid var(--line);font-size:12.5px;letter-spacing:.02em
}
tbody td{padding:10px 13px;border-bottom:1px solid #f1f4f9;vertical-align:top;line-height:1.6}
tbody tr:last-child td{border-bottom:0}
tbody tr:nth-child(even) td{background:#fbfcfe}
tbody tr:hover td{background:#f4f7ff}
td.name{font-weight:600;min-width:150px}
td.name a{display:inline-flex;align-items:center;gap:3px}
.ext{font-size:10px;opacity:.55;font-weight:400}
strong{font-weight:650}
td:first-child{color:var(--ink)}

/* ---------- 标签 ---------- */
.tag{display:inline-block;padding:1px 8px;border-radius:20px;font-size:12.3px;white-space:nowrap;font-weight:500}
.tag.ok{background:var(--ok-soft);color:var(--ok)}
.tag.warn{background:var(--warn-soft);color:var(--warn)}
.tag.bad{background:var(--bad-soft);color:var(--bad)}
.tag.fire{background:var(--fire-soft);color:#c2410c;font-weight:600}
.tag.star{background:var(--star-soft);color:var(--star)}

/* ---------- 交互 ---------- */
#top{
  position:fixed;right:26px;bottom:26px;width:42px;height:42px;border-radius:50%;
  background:var(--card);border:1px solid var(--line);box-shadow:0 4px 14px rgba(16,24,40,.12);
  display:none;align-items:center;justify-content:center;cursor:pointer;color:var(--sub);z-index:60
}
#top:hover{color:var(--brand);border-color:var(--brand)}
.hide{display:none!important}
.count{font-size:12.5px;color:#93a1b6;margin-left:4px}
.rec-hero{border:1px solid #fecdd3;border-left:4px solid var(--bad);background:#fff;border-radius:12px;padding:15px 20px;margin:18px 0 24px}
.rec-hero h4.sub{color:var(--ink);font-weight:800;font-size:15.5px;margin:26px 0 9px;padding-top:14px;border-top:1px dashed #f3d3d8}
.rec-hero-h{font-size:15px;font-weight:800;color:var(--bad);margin-bottom:5px}
.rec-hero-b{font-size:14.5px;line-height:1.78;color:var(--ink)}
.rec-hero .tw{margin:12px 0 4px;border-radius:10px;border-color:#f7d9dd}
.rec-hero .tw table{min-width:900px}
.rec-link{color:inherit;text-decoration:none;border-bottom:2px solid rgba(220,38,38,.35);transition:.15s}
.rec-link:hover{border-bottom-color:var(--bad);text-decoration:none}
.rec-arrow{display:inline-block;margin-left:4px;font-weight:700;color:var(--bad)}
.rec-hero-b strong{color:var(--bad);font-weight:700}
@media(max-width:1100px){
  .wrap{grid-template-columns:minmax(0,1fr);padding:20px 16px 80px}
  nav{display:none}
  .search input{width:180px}
  .bar{padding:10px 16px;gap:10px}
  .doc-title{font-size:24px}
}
.mtoc{display:none;box-sizing:border-box;max-width:100%}
.mnav{display:none;align-items:center;gap:5px;padding:7px 12px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
.mnav:hover{border-color:var(--brand);color:var(--brand)}
.drawer{position:fixed;inset:0;z-index:300;background:rgba(15,23,42,.42);opacity:0;pointer-events:none;transition:opacity .18s}
.drawer.open{opacity:1;pointer-events:auto}
.drawer-in{position:absolute;left:0;top:0;bottom:0;width:min(85vw,330px);background:#fff;overflow-y:auto;padding:14px 6px 44px;box-shadow:3px 0 24px rgba(21,29,46,.18);transform:translateX(-102%);transition:transform .22s cubic-bezier(.4,0,.2,1)}
.drawer.open .drawer-in{transform:none}
.drawer-h{display:flex;justify-content:space-between;align-items:center;padding:2px 14px 12px;margin-bottom:6px;border-bottom:1px solid var(--line);font-size:12px;font-weight:700;color:var(--sub);letter-spacing:.1em}
.dclose{cursor:pointer;font-size:14px;color:var(--sub);padding:2px 7px;border-radius:6px;line-height:1.4}
.dclose:hover{background:#f1f5f9;color:var(--ink)}
.drawer-list a{display:block;padding:9px 14px;border-radius:7px;color:var(--ink);font-size:14px;text-decoration:none}
.drawer-list a:active{background:var(--brand-soft)}
.drawer-list a.lv1{font-weight:700;margin-top:8px;border-left:3px solid var(--brand);padding-left:12px;background:linear-gradient(90deg,var(--brand-soft),transparent 70%)}
.drawer-list a.lv1:first-child{margin-top:0}
.drawer-list a.lv2{padding-left:26px;color:var(--sub);font-size:13.5px}
@media(max-width:760px){
  html,body{max-width:100%}
  .wrap,main{min-width:0}
  [id]{scroll-margin-top:104px}
.mnav{display:none}
  .bar{justify-content:space-between;padding:9px 14px}
  .mtoc{display:flex;gap:6px;overflow-x:auto;padding:0 14px 9px;scrollbar-width:none;-ms-overflow-style:none;-webkit-overflow-scrolling:touch}
  .mtoc::-webkit-scrollbar{display:none}
  .mtoc a{flex:0 0 auto;white-space:nowrap;font-size:12.5px;line-height:1.35;padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--sub);text-decoration:none;border-bottom:1px solid var(--line)}
  .mtoc a.lv1{font-weight:700;background:var(--brand-soft);border-color:#dfe3ff;color:var(--brand)}
  .mtoc a.cur{background:var(--brand-soft);border-color:var(--brand);color:var(--brand);font-weight:700}
  .mtoc .all{position:sticky;right:-1px;flex:0 0 auto;white-space:nowrap;font:inherit;font-size:12.5px;font-weight:700;padding:5px 12px;border-radius:999px;border:1px solid var(--brand);background:var(--brand);color:#fff;cursor:pointer;box-shadow:-9px 0 12px 2px #fff}
  .mtoc{-webkit-mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 78px),transparent 100%);mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 78px),transparent 100%)}
  .wrap{width:100%;max-width:100%}
  main{width:100%;min-width:0;max-width:100%}
  .tw{width:100%;max-width:100%}
  .bar{flex-wrap:wrap;gap:8px 10px;padding:9px 12px}
  .logo{font-size:13px}
  .spacer{display:none}
  .toggle{order:2;font-size:12px}
  .search{order:3;flex:1 1 100%}
  .search input{width:100%;font-size:13px;padding:8px 12px 8px 32px}
  .wrap{padding:16px 12px 68px;gap:22px}
  .doc-title{font-size:18px;letter-spacing:0;line-height:1.4}
  .tw{border-radius:10px}
  h2.group{font-size:17px;padding-left:10px}
  h3.merchant{font-size:15px}
  table{min-width:700px;font-size:12.4px}
  td,th{padding:7px 9px}
  blockquote{padding:10px 13px;margin:12px 0;font-size:13.5px}
  pre{font-size:11.5px;padding:11px 12px}
  ul{padding-left:19px}
  .rec-hero{padding:13px 15px;margin:14px 0 20px}
  .rec-hero .tw{margin:10px 0 4px;border-radius:9px}
  .rec-hero .tw table{min-width:700px}
  .rec-hero-b{font-size:13.5px}
  #top{right:12px;bottom:12px;width:38px;height:38px}
}
</style>
</head>
<body>
<header>
  <div class="bar">
    <div class="logo">VPS 选型清单 <em>2026·11</em></div>
    <button class="mnav" id="mnav" aria-label="打开目录">
      <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M3 5h18v2.4H3zm0 5.8h18v2.4H3zM3 16.6h18V19H3z"/></svg>
      目录
    </button>
    <div class="spacer"></div>
  </div>
  <div class="mtoc" id="mtoc">__MTOC__</div>
</header>

<div class="wrap">
  <nav id="toc">
    <p class="nlabel">目录</p>
    __TOC__
  </nav>
  <main id="main">
__BODY__
  </main>
</div>

<div class="drawer" id="drawer">
  <div class="drawer-in">
    <div class="drawer-h"><span>目录</span><span class="dclose" id="dclose">\u2715</span></div>
    <div class="drawer-list">
__DRAWER__
    </div>
  </div>
</div>

<div id="top" title="回到顶部">
  <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 5l7 7h-4v7h-6v-7H5z"/></svg>
</div>

<script>
// 目录高亮
const links = [...document.querySelectorAll('#toc a')];
const mlinks = [...document.querySelectorAll('#mtoc a')];
const secs = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
const io = new IntersectionObserver(es => {
  es.forEach(e => {
    if(e.isIntersecting){
      links.forEach(l => l.classList.toggle('cur', l.getAttribute('href') === '#' + e.target.id));
      mlinks.forEach(l => l.classList.toggle('cur', l.getAttribute('href') === '#' + e.target.id));
      const mc = mlinks.find(l => l.getAttribute('href') === '#' + e.target.id);
      if(mc && mc.scrollIntoView) mc.scrollIntoView({block:'nearest', inline:'center'});
      const cur = links.find(l => l.getAttribute('href') === '#' + e.target.id);
      if(cur) cur.scrollIntoView({block:'nearest'});
    }
  });
}, {rootMargin: '-114px 0px -72% 0px'});
secs.forEach(s => io.observe(s));

const topBtn = document.getElementById('top');
addEventListener('scroll', () => { topBtn.style.display = scrollY > 600 ? 'flex' : 'none'; });
topBtn.onclick = () => scrollTo({top:0});

(function(){
  var btn = document.getElementById('mnav');
  var mall = document.getElementById('mall');
  var dr = document.getElementById('drawer');
  if(!dr) return;
  function open(){ dr.classList.add('open'); document.documentElement.style.overflow='hidden'; }
  function close(){ dr.classList.remove('open'); document.documentElement.style.overflow=''; }
  if(btn) btn.addEventListener('click', function(e){ e.stopPropagation(); open(); });
  if(mall) mall.addEventListener('click', function(e){ e.stopPropagation(); open(); });
  dr.addEventListener('click', function(e){ if(e.target === dr || e.target.id === 'dclose') close(); });
  dr.querySelectorAll('a').forEach(function(a){ a.addEventListener('click', close); });
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') close(); });
})();
</script>
</body>
</html>
"""


def main():
    with open(MD, encoding="utf-8") as f:
        md_text = f.read()
    blocks, toc = parse(md_text)

    toc_html = []
    for lvl, txt, anchor in toc:
        cls = "grp" if lvl == 1 else ""
        toc_html.append(f'<a class="{cls}" href="#{anchor}">{html.escape(txt)}</a>')

    draw = []
    for lvl, txt, anchor in toc:
        cls = "lv1" if lvl == 1 else "lv2"
        rec = ' <span class="rec-badge">推荐</span>' if (lvl == 2 and IS_REC(txt)) else ""
        draw.append(f'<a class="{cls}" href="#{anchor}">{html.escape(txt)}{rec}</a>')

    body_html = "\n".join(blocks).replace("<p>[[toc]]</p>", "")

    gia = next((a for lvl, t, a in toc if t.strip().startswith("2. CN2 GIA")), None)
    if gia:
        body_html = body_html.replace(
            "<strong>\u63a8\u8350\u4f7f\u7528 CN2 GIA \u7ebf\u8def</strong>",
            '<a class="rec-link" href="#%s"><strong>\u63a8\u8350\u4f7f\u7528 CN2 GIA \u7ebf\u8def</strong>'
            '<span class="rec-arrow">\u2193</span></a>' % gia, 1)

    mtoc = []
    for lvl, txt, anchor in toc:
        cls = "lv1" if lvl == 1 else "lv2"
        rec = ' <span class="rec-badge">推荐</span>' if (lvl == 2 and IS_REC(txt)) else ""
        short = txt
        if lvl == 1:
            short = short.split("\uff08")[0].strip()
        else:
            short = short.split(" \u2014 ")[0].strip()
        mtoc.append(f'<a class="{cls}" href="#{anchor}">{html.escape(short)}{rec}</a>')

    page = TEMPLATE.replace("__DRAWER__", "\n      ".join(draw))
    mtoc.append('<button class="all" id="mall" type="button">\u76ee\u5f55</button>')
    page = page.replace("__MTOC__", "\n    ".join(mtoc))
    page = page.replace("__TOC__", "\n    ".join(toc_html))
    page = page.replace("__BODY__", body_html)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"-> {OUT}")
    print(f"  blocks={len(blocks)} toc={len(toc)} size={os.path.getsize(OUT):,}B")


if __name__ == "__main__":
    main()
