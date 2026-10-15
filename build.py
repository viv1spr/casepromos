#!/usr/bin/env python3
"""Static site generator for the CS2 sites catalog.

  python3 build.py           -> builds the site for hosting into ./dist
  python3 build.py --local   -> builds a preview into ./preview (open index.html by double-click)

Edit data/sites.json (sites, ref links, promo codes), data/i18n.json (texts),
config.json (domain, brand, languages), then run the build again.
"""
import json, re, shutil, html, sys
from pathlib import Path

ROOT = Path(__file__).parent
LOCAL = "--local" in sys.argv
DIST = ROOT / ("preview" if LOCAL else "dist")
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
T = json.loads((ROOT / "data/i18n.json").read_text(encoding="utf-8"))
SITES = json.loads((ROOT / "data/sites.json").read_text(encoding="utf-8"))
for _l, _v in json.loads((ROOT / "data/i18n_brand.json").read_text(encoding="utf-8")).items():
    T[_l].update(_v)
GUIDES = json.loads((ROOT / "data/guides.json").read_text(encoding="utf-8"))
GUIDE_SLUG = {"sell": "sell-cs2-skins", "scams": "avoid-cs2-scams"}
BLOG = json.loads((ROOT / "data/blog.json").read_text(encoding="utf-8"))
BLOG_DIR = ROOT / "content/blog"
GAMES = json.loads((ROOT / "data/games.json").read_text(encoding="utf-8"))
GAME_LIST = ["rust", "dota2"]
SEOP = ROOT / "data/seo.json"
SEO = json.loads(SEOP.read_text(encoding="utf-8")) if SEOP.exists() else {}

LANGS = CFG["languages"]
DEFAULT = CFG["default_language"]
BASE_URL = CFG["site_url"].rstrip("/")
BRAND = CFG["brand"]
YEAR = CFG.get("updated", "2026")[:4]
UPDATED = CFG.get("updated", "")
import datetime
BUILD_DATE = datetime.date.today().isoformat()

TYPES = ["cases", "roulette", "p2p", "bot", "instasell"]
TYPE_SLUG = {"p2p": "p2p-marketplaces", "bot": "bot-trading", "instasell": "instant-sell",
             "cases": "case-sites", "roulette": "roulette-sites"}
FEATURES = ["free_case", "no_deposit", "crypto", "card", "paypal", "low_min"]
TRADE_TYPES = {"p2p", "bot", "instasell"}
EMPTY = (None, "", "—", "-")

e = html.escape
ARIA = ' aria-current="true"'
ON = ' class="on"'
ON_C = ' on'
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Unbounded:wght@500;700;800&display=swap" rel="stylesheet">')
SEARCH_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M20 20l-4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
ARROW_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M7 17L17 7M9 7h8v8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def loc(field, lang):
    if isinstance(field, dict):
        return field.get(lang) or field.get(DEFAULT) or ""
    return field or ""


def fee_num(v):
    m = re.search(r"[\d.]+", str(v or ""))
    return float(m.group()) if m else 999


def sites_for(lang, typ=None):
    out = [s for s in SITES if (not s.get("langs") or lang in s["langs"])]
    if typ:
        out = [s for s in out if s["type"] == typ]
    return sorted(out, key=lambda s: s.get("order", 99))


def types_for(lang):
    return [ty for ty in TYPES if sites_for(lang, ty)]


# ---------- paths ----------
def p_home(lang): return f"{lang}/"
def p_type(lang, typ): return f"{lang}/{TYPE_SLUG[typ]}/"
def p_review(lang, slug): return f"{lang}/sites/{slug}/"
def p_go(slug): return f"go/{slug}/"
def p_game(lang, g): return f"{lang}/{g}/"


def sites_game(lang, g):
    return [s for s in sites_for(lang) if g in s.get("games", ["cs2"])]


def games_list(s, lang):
    N = GAMES[lang]["names"]
    return [N[g] for g in s.get("games", ["cs2"])]


def rel(from_path, to_path, index=True):
    depth = from_path.count("/")
    if LOCAL and index and (to_path == "" or to_path.endswith("/")):
        return ("../" * depth) + to_path + "index.html"
    return ("../" * depth) + to_path if to_path else ("../" * depth or "./")


# ---------- text helpers ----------
def s_bonus(s, t): return loc(s.get("bonus"), t["_lang"]) or (t["bonus_generic"] if s.get("promo_code") else t["bonus_generic_link"])
def s_short(s, t): return loc(s.get("short"), t["_lang"]) or t["type_short"][s["type"]]


# ---------- fragments ----------
def logo(s, size="md"):
    letter = e(s["name"][:1].upper())
    if s.get("logo"):
        src = "{P}assets/logos/" + e(s["logo"])
    elif s.get("domain"):
        src = f"https://www.google.com/s2/favicons?domain={e(s['domain'])}&amp;sz=128"
    else:
        src = ""
    img = (f'<img src="{src}" alt="{e(s["name"])}" loading="lazy" referrerpolicy="no-referrer" '
           f'onerror="this.remove()">') if src else ""
    return f'<span class="logo logo-{size}" style="--c:{e(s.get("color", "#64748b"))}"><span class="lt">{letter}</span>{img}</span>'


def code_box(s, t):
    code = s.get("promo_code")
    if not code:
        link = s.get("ref_link", "")
        shown = re.sub(r"^https?://(www\.)?", "", link).rstrip("/")
        if not link:
            return f'<div class="code code-none"><span>{e(t["no_code"])}</span></div>'
        return (f'<div class="code code-link"><span class="code-val">{e(shown)}</span>'
                f'<button type="button" class="copy" data-code="{e(link)}" data-done="{e(t["copied"])}">{e(t["copy"])}</button></div>')
    return (f'<div class="code"><span class="code-val">{e(code)}</span>'
            f'<button type="button" class="copy" data-code="{e(code)}" data-done="{e(t["copied"])}">{e(t["copy"])}</button></div>')


def badges(s, t):
    b = f'<span class="badge t-{s["type"]}">{e(t["type_one"][s["type"]])}</span>'
    if s.get("license"):
        b += f'<span class="badge lic">✓ {e(t["licensed"])} · {e(s["license"])}</span>'
    if len(s.get("games", [])) > 1:
        b += f'<span class="badge gm">{e(" · ".join(games_list(s, t["_lang"])))}</span>'
    return b


def pay_chips(s, t=None):
    items = list(s.get("payments", []))
    if t:
        for p in s.get("deposit", []) + s.get("withdraw", []):
            n = t["pays"].get(p, p)
            if n not in items:
                items.append(n)
    return "".join(f'<span class="chip">{e(p)}</span>' for p in items[:5])


def data_attrs(s):
    return (f'data-type="{s["type"]}" data-features="{" ".join(s.get("features", []))}" '
            f'data-name="{e((s["name"] + " " + s.get("domain", "")).lower())}" '
            f'data-order="{s.get("order", 99)}" data-sf="{fee_num(s.get("seller_fee"))}" data-bf="{fee_num(s.get("buyer_fee"))}"')


def meta(s, t):
    kv = []
    if s["type"] in TRADE_TYPES:
        if s.get("seller_fee") not in EMPTY:
            kv.append((t["seller_fee"], s["seller_fee"]))
        if s.get("buyer_fee") not in EMPTY:
            kv.append((t["buyer_fee"], s["buyer_fee"]))
    if s.get("min_deposit") not in EMPTY:
        kv.append((t["min_deposit"], s["min_deposit"]))
    if not kv:
        return ""
    return '<div class="meta">' + "".join(f'<div class="kv"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in kv) + "</div>"


def cta(s, t, page, cls="btn btn-primary"):
    code = s.get("promo_code")
    dc = f' data-code="{e(code)}" data-msg="{e(t["copied_go"].replace("{code}", code))}"' if code else ""
    return (f'<a class="{cls}" href="{rel(page, p_go(s["slug"]))}" target="_blank" rel="sponsored nofollow noopener"{dc}>'
            f'<span>{e(t["get_bonus"])}</span>{ARROW_SVG}</a>')


def card(s, lang, t, page, rank=None):
    chips = pay_chips(s, t)
    rk = f'<span class="rank">#{rank:02d}</span>' if rank else ""
    return f'''<article class="card" {data_attrs(s)}>
  {rk}
  <header class="card-head">
    {logo(s)}
    <div class="ch"><h3><a href="{rel(page, p_review(lang, s["slug"]))}">{e(s["name"])}</a></h3>
    <div class="badges">{badges(s, t)}</div></div>
  </header>
  <p class="desc">{e(s_short(s, t))}</p>
  <div class="bonus"><span class="label">{e(t["bonus"])}</span><strong>{e(s_bonus(s, t))}</strong></div>
  {code_box(s, t)}
  {meta(s, t)}
  {f'<div class="chips">{chips}</div>' if chips else ''}
  <div class="actions">
    {cta(s, t, page)}
    <a class="btn btn-ghost" href="{rel(page, p_review(lang, s["slug"]))}">{e(t["read_review"])}</a>
  </div>
</article>'''


def feat_card(s, lang, t, page, rank):
    return f'''<article class="feat r{rank}">
  <div class="feat-in">
    <span class="medal">{rank}</span>
    {logo(s, "lg")}
    <h3><a href="{rel(page, p_review(lang, s["slug"]))}">{e(s["name"])}</a></h3>
    <div class="badges">{badges(s, t)}</div>
    <div class="bonus"><span class="label">{e(t["bonus"])}</span><strong>{e(s_bonus(s, t))}</strong></div>
    {code_box(s, t)}
    {cta(s, t, page, "btn btn-primary btn-lg")}
  </div>
</article>'''


def table_row(s, lang, t, page):
    return f'''<tr {data_attrs(s)}>
  <td><a class="tsite" href="{rel(page, p_review(lang, s["slug"]))}">{logo(s, "sm")}<span>{e(s["name"])}</span></a></td>
  <td><span class="badge t-{s["type"]}">{e(t["type_one"][s["type"]])}</span></td>
  <td>{e(s_bonus(s, t))}</td>
  <td>{code_box(s, t)}</td>
  <td>{e(s.get("seller_fee") or "—")}</td>
  <td>{e(s.get("buyer_fee") or "—")}</td>
  <td>{cta(s, t, page, "btn btn-primary btn-sm")}</td>
</tr>'''


def lang_switch(alts, lang, page):
    items = "".join(
        f'<a href="{rel(page, alts[l])}" hreflang="{T[l]["html_lang"]}"{ARIA if l == lang else ""}>{T[l]["flag"]} {e(T[l]["lang_name"])}</a>'
        for l in LANGS if l in alts)
    return f'<details class="langs"><summary>{T[lang]["flag"]} <span>{e(lang.upper())}</span></summary><div class="langs-menu">{items}</div></details>'


def head(lang, page, title, desc, alts, extra="", img=None):
    og = img if img and img.startswith("http") else f"{BASE_URL}/assets/og/{img or lang + '-cs2'}.png"
    canonical = f"{BASE_URL}/{page}"
    hl = "".join(f'<link rel="alternate" hreflang="{T[l]["html_lang"]}" href="{BASE_URL}/{alts[l]}">' for l in LANGS if l in alts)
    if DEFAULT in alts:
        hl += f'<link rel="alternate" hreflang="x-default" href="{BASE_URL}/{alts[DEFAULT]}">'
    return f'''<!doctype html>
<html lang="{T[lang]["html_lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
{hl}
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{canonical}">
<meta property="og:locale" content="{T[lang]["og_locale"]}"><meta property="og:site_name" content="{e(BRAND)}">
<meta property="og:image" content="{og}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{og}">
<meta name="theme-color" content="#07080d">{f'<meta name="yandex-verification" content="{e(CFG["yandex_verification"])}">' if CFG.get("yandex_verification") else ""}
<link rel="icon" href="{rel(page, "assets/favicon.svg", False)}" type="image/svg+xml">
{FONTS}
<link rel="stylesheet" href="{rel(page, "assets/style.css", False)}">
{extra}
</head>'''


def suggest_data(alts, page):
    return json.dumps({l: [T[l]["suggest"], T[l]["suggest_btn"], rel(page, alts[l])] for l in LANGS if l in alts}, ensure_ascii=False)


def game_switch(lang, page, game):
    N = GAMES[lang]["names"]
    items = [("cs2", p_home(lang))] + [(g, p_game(lang, g)) for g in GAME_LIST if sites_game(lang, g)]
    links = "".join(f'<a href="{rel(page, u)}" class="g-{g}{ON_C if g == game else ""}"{ARIA if g == game else ""}><i></i>{e(N[g])}</a>' for g, u in items)
    return f'<nav class="gsw" aria-label="{e(GAMES[lang]["label"])}">{links}</nav>'


def topbar(lang, page, alts, active=None, clean=False, game="cs2"):
    t = T[lang]
    G = GUIDES[lang]
    def a(u, label, on, cls=""):
        c = (cls + (" on" if on else "")).strip()
        c_attr = f' class="{c}"' if c else ""
        return f'<a href="{rel(page, u)}"{c_attr}{ARIA if on else ""}>{label}</a>'
    main = []
    if not clean:
        main.append(a(p_codes(lang), e(t["nav_codes"]), active == "codes", "hot"))
    main.append(a(p_guides(lang), e(G["nav"]), active == "guides"))
    if POSTS_BY_LANG.get(lang):
        main.append(a(p_blog(lang), e(BLOG[lang]["nav"]), active == "blog"))
    main_html = "".join(main)
    if clean:
        cats = [a(p_type(lang, ty), f'<i class="dot d-{ty}"></i>{e(t["types"][ty])}', active == ty) for ty in types_for(lang) if ty in TRADE_TYPES]
    elif game == "cs2":
        cats = [a(p_home(lang), e(t["nav_all"]), active is None)] + \
               [a(p_type(lang, ty), f'<i class="dot d-{ty}"></i>{e(t["types"][ty])}', active == ty) for ty in types_for(lang)]
    else:
        cats = []
    cats_html = f'<div class="subnav"><div class="wrap"><nav class="cats" aria-label="categories">{"".join(cats)}</nav></div></div>' if cats else ""
    gsw = "" if clean else game_switch(lang, page, game)
    return f'''<div class="bg" aria-hidden="true"><i></i><i></i><i></i></div>
<div id="suggest" class="suggest" hidden><span></span><a class="btn btn-sm btn-primary" href="#"></a><button type="button" class="x" aria-label="close">✕</button></div>
<header class="hdr{" clean" if clean else ""}">
  <div class="wrap hdr-row">
    <a class="brand" href="{rel(page, p_home(lang))}"><img src="{rel(page, "assets/favicon.svg", False)}" alt="" width="30" height="30"><span>{e(BRAND)}</span></a>
    {gsw}
    <nav class="mainnav" id="mainnav" aria-label="main">{main_html}</nav>
    {lang_switch(alts, lang, page)}
    <button type="button" class="burger" id="burger" aria-label="Menu" aria-controls="mainnav" aria-expanded="false"><span></span><span></span><span></span></button>
  </div>
  {cats_html}
</header>'''


def foot_links(lang, page, clean=False):
    t = T[lang]
    if clean:
        links = [(GUIDES[lang]["nav"], p_guides(lang))] + [(GUIDES[lang][k]["h1"], p_guide(lang, k)) for k in GUIDE_SLUG] + [(t["types"][ty], p_type(lang, ty)) for ty in types_for(lang) if ty in TRADE_TYPES]
    else:
        links = [(t["nav_all"], p_home(lang)), (t["nav_codes"], p_codes(lang)), (GUIDES[lang]["nav"], p_guides(lang))] + ([(BLOG[lang]["nav"], p_blog(lang))] if POSTS_BY_LANG.get(lang) else []) + [(t["types"][ty], p_type(lang, ty)) for ty in types_for(lang)] + [(GAMES[lang][g]["h1"], p_game(lang, g)) for g in GAME_LIST if sites_game(lang, g)]
    return "".join(f'<a href="{rel(page, u)}">{e(n)}</a>' for n, u in links)


def foot_sites(lang, page, clean=False):
    ss = [x for x in sites_for(lang) if not clean or x["type"] in TRADE_TYPES]
    links = "".join(f'<a href="{rel(page, p_review(lang, x["slug"]))}">{e(x["name"])}</a>' for x in ss)
    return f'<div class="foot-sites"><b>{e(T[lang]["nav_codes"] if not clean else GUIDES[lang]["nav"])}:</b>{links}</div>'


def footer(lang, page, clean=False):
    t = T[lang]
    disc = f'<p>{e(GUIDES[lang]["disclaimer"])}</p>' if clean else f'<p><span class="age18">18+</span> {e(t["footer_disclaimer"])}</p>'
    return f'''<footer class="foot"><div class="wrap">
  <nav class="foot-links">{foot_links(lang, page, clean)}</nav>
  {foot_sites(lang, page, clean)}
  <div class="foot-brand"><img src="{rel(page, "assets/favicon.svg", False)}" alt="" width="26" height="26"> {e(BRAND)}</div>
  {disc}
  <p class="coop">{e(t["coop"])} <a href="https://t.me/Vivistop" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M21.9 4.3 18.7 19.4c-.2 1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.3-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.2 13.1l-4.8-1.5c-1-.3-1-1 .2-1.5L20.6 2.8c.9-.3 1.6.2 1.3 1.5z"/></svg>Telegram @Vivistop</a></p>
  <p class="muted">© {YEAR} {e(BRAND)} · {e(t["updated"])}: {e(UPDATED)}</p>
</div></footer>
<script src="{rel(page, "assets/app.js", False)}" defer></script>
</body></html>'''


def listing(lang, page, sites):
    t = T[lang]
    used = [f for f in FEATURES if any(f in s.get("features", []) for s in sites)]
    chips = ""
    if used:
        chips = f'<button type="button" class="fchip on" data-f="">{e(t["f_all"])}</button>' + \
            "".join(f'<button type="button" class="fchip" data-f="{f}">{e(t["f_" + f])}</button>' for f in used)
    has_fees = any(s["type"] in TRADE_TYPES and s.get("seller_fee") not in EMPTY for s in sites)
    sort_opts = f'<option value="order">{e(t["sort_featured"])}</option>'
    if has_fees:
        sort_opts += f'<option value="sf">{e(t["sort_seller"])}</option><option value="bf">{e(t["sort_buyer"])}</option>'
    cards = "\n".join(card(s, lang, t, page, i) for i, s in enumerate(sites, 1))
    rows = "\n".join(table_row(s, lang, t, page) for s in sites)
    return f'''<div class="toolbar">
  <label class="search">{SEARCH_SVG}<input id="q" type="search" placeholder="{e(t["search"])}" autocomplete="off"></label>
  {f'<div class="fchips" role="group">{chips}</div>' if chips else ''}
  <div class="tools">
    <label class="sort"><span>{e(t["sort"])}</span><select id="sort">{sort_opts}</select></label>
    <div class="view" role="group"><button type="button" data-view="cards" class="on" aria-label="{e(t["view_cards"])}"><svg viewBox="0 0 24 24" width="16" height="16"><path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" fill="currentColor"/></svg>{e(t["view_cards"])}</button><button type="button" data-view="table" aria-label="{e(t["view_table"])}"><svg viewBox="0 0 24 24" width="16" height="16"><path d="M4 5h16v3H4zM4 10.5h16v3H4zM4 16h16v3H4z" fill="currentColor"/></svg>{e(t["view_table"])}</button></div>
  </div>
</div>
<div id="cards" class="grid">{cards}</div>
<div id="table" class="tablewrap" hidden><table>
<thead><tr><th>{e(t["site"])}</th><th>{e(t["type"])}</th><th>{e(t["bonus"])}</th><th>{e(t["promo_code"])}</th><th>{e(t["seller_fee"])}</th><th>{e(t["buyer_fee"])}</th><th></th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p id="empty" class="empty" hidden>{e(t["nothing_found"])}</p>'''


def faq_block(lang):
    t = T[lang]
    items = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in t["faq"])
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in t["faq"]]}
    return f'<section class="faq"><h2 class="sec">{e(t["faq_title"])}</h2><div class="faq-list">{items}</div></section>', \
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def seo_block(lang, key):
    lines = (SEO.get(lang) or {}).get(key) or []
    if not lines:
        return ""
    out, ul = [], []
    def flush():
        if ul:
            out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in ul) + "</ul>")
            ul.clear()
    for ln in lines:
        if ln.startswith("- "):
            ul.append(ln[2:]); continue
        flush()
        if ln.startswith("## "):
            out.append(f"<h2>{e(ln[3:])}</h2>")
        else:
            out.append(f"<p>{e(ln)}</p>")
    flush()
    return (f'<section class="seo"><details><summary>{e(SEO[lang].get("more", "More"))}</summary>'
            f'<div class="seo-body">{"".join(out)}</div></details></section>')


def write(page, content):
    out = DIST / page / "index.html" if page.endswith("/") or page == "" else DIST / page
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content.replace("{P}", rel(page, "", index=False)), encoding="utf-8")


# ---------- pages ----------
def hero(lang, h1, sub, n_sites):
    t = T[lang]
    return f'''<section class="hero">
  <span class="eyebrow"><i class="pulse"></i>{e(t["updated"])}: {e(UPDATED)}</span>
  <h1><span class="grad">{e(h1)}</span></h1>
  <p class="lead">{e(sub)}</p>
</section>'''


def build_list_page(lang, typ=None):
    t = T[lang]
    page = p_type(lang, typ) if typ else p_home(lang)
    alts = {l: (p_type(l, typ) if typ else p_home(l)) for l in LANGS if sites_for(l, typ)}
    title = (t["type_title"][typ] if typ else t["home_title"]).replace("{year}", YEAR)
    desc = t["type_desc"][typ] if typ else t["home_desc"]
    h1 = title.split(" (")[0] if typ else t["h1"]
    sub = desc if typ else t["subtitle"]
    sites = sites_for(lang, typ)
    faq_html, faq_ld = faq_block(lang)
    podium = ""
    if not typ and len(sites) >= 3:
        podium = f'<section class="podium-wrap"><h2 class="sec">{e(t["top"])}</h2><div class="podium">' + \
            "".join(feat_card(s, lang, t, page, i) for i, s in enumerate(sites[:3], 1)) + "</div></section>"
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, typ)}
<main class="wrap">
  {hero(lang, h1, sub, len(sites))}
  {podium}
  {listing(lang, page, sites)}
  {faq_html}
  {seo_block(lang, typ or "home")}
</main>
{footer(lang, page)}'''
    items = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "itemListElement": [
        {"@type": "ListItem", "position": i, "name": x["name"], "url": f"{BASE_URL}/{p_review(lang, x['slug'])}"} for i, x in enumerate(sites, 1)]}
    faq_ld += ld_tags(items)
    if typ:
        faq_ld += ld_tags(breadcrumb_ld([(t["home_crumb"], p_home(lang)), (t["types"][typ], page)]))
    else:
        faq_ld += ld_tags({"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": f"{BASE_URL}/{page}", "inLanguage": t["html_lang"]},
                          {"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": BASE_URL + "/", "logo": f"{BASE_URL}/assets/favicon.svg",
                           "sameAs": ["https://t.me/Vivistop"]})
    write(page, head(lang, page, title, desc, alts, faq_ld) + body)
    return page, alts


def build_game(lang, g):
    t, Gm = T[lang], GAMES[lang][g]
    page = p_game(lang, g)
    alts = {l: p_game(l, g) for l in LANGS if sites_game(l, g)}
    mon, yr = month_year(t)
    title = fill(Gm["title"], month=(mon.capitalize() if lang in ("en", "tr") else mon), year=yr)
    desc = fill(Gm["desc"], month=mon, year=yr)
    sites = sites_game(lang, g)
    items = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in Gm["faq"])
    faq_html = f'<section class="faq"><h2 class="sec">{e(t["faq_title"])}</h2><div class="faq-list">{items}</div></section>'
    seo = (f'<section class="seo"><details><summary>{e(SEO.get(lang, {}).get("more", "More"))}</summary>'
           f'<div class="seo-body">{md(Gm["seo"])}</div></details></section>')
    crumbs = [(t["home_crumb"], p_home(lang)), (GAMES[lang]["names"][g], page)]
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, "game", game=g)}
<main class="wrap">
  <section class="hero">
    <span class="eyebrow"><i class="pulse"></i>{e(fill(t["checked"], month=mon, year=yr))}</span>
    <h1><span class="grad">{e(Gm["h1"])}</span></h1>
    <p class="lead">{e(Gm["intro"])}</p>
  </section>
  {listing(lang, page, sites)}
  {faq_html}
  {seo}
</main>
{footer(lang, page)}'''
    write(page, head(lang, page, title, desc, alts, ld_tags(faq_ld(Gm["faq"]), breadcrumb_ld(crumbs)), img=f"{lang}-{g}") + body)
    return page, alts


GAMBLING = {"cases", "roulette"}
WHAT_NOTES = {"provably_fair", "p2p_market", "daily_free", "rebrand_ggcs2", "float_tool", "lootbear", "big_bot_inventory", "regulated_de"}
NOTE_PROS = ["daily_free", "fast_withdraw", "float_tool", "p2p_market", "big_bot_inventory", "fast_crypto", "regulated_de"]
NOTE_CONS = ["spread", "no_cashout", "balance_lock7", "visa_only", "kyc", "delays"]


def month_year(t):
    try:
        m = int(UPDATED.split("-")[1])
    except Exception:
        m = 1
    return t["months"][m - 1], YEAR


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


def lst(items, table):
    return ", ".join(table.get(i, i) for i in items)


def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": f"{BASE_URL}/{u}"} for i, (n, u) in enumerate(items, 1)]}


def faq_ld(pairs):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}


def ld_tags(*objs):
    return "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in objs)


def pros_cons(s, t):
    notes = set(s.get("notes", []))
    pay = set(s.get("deposit", [])) | set(s.get("withdraw", []))
    sf = fee_num(s.get("seller_fee"))
    P, C = [], []
    if "provably_fair" in notes: P.append(t["pros"]["pf"])
    if s.get("license"): P.append(fill(t["pros"]["license"], license=s["license"]))
    if s["type"] in TRADE_TYPES and sf <= 3: P.append(fill(t["pros"]["lowfee"], sf=s["seller_fee"]))
    if s.get("buyer_fee") == "0%": P.append(t["pros"]["nobuyer"])
    if len(s.get("modes", [])) >= 5: P.append(fill(t["pros"]["modes"], n=len(s["modes"])))
    if "skins" in s.get("deposit", []) and "skins" in s.get("withdraw", []): P.append(t["pros"]["skins"])
    if "crypto" in pay or "usdc" in pay: P.append(t["pros"]["crypto"])
    if "card" in pay: P.append(t["pros"]["card"])
    if "paypal" in pay: P.append(t["pros"]["paypal"])
    if {"bank", "sepa"} & set(s.get("withdraw", [])): P.append(t["pros"]["bank"])
    if "steam_balance" in s.get("withdraw", []): P.append(t["pros"]["steam_balance"])
    P += [t["pros"][n] for n in NOTE_PROS if n in notes]
    if s["type"] in GAMBLING and not s.get("license"): C.append(t["cons"]["nolicense"])
    if s["type"] in TRADE_TYPES and 8 <= sf < 999: C.append(fill(t["cons"]["highfee"], sf=s["seller_fee"]))
    if s["type"] in GAMBLING and 0 < len(s.get("modes", [])) <= 2: C.append(t["cons"]["fewmodes"])
    if s.get("deposit") == ["crypto"] and s["type"] in GAMBLING: C.append(t["cons"]["cryptoonly"])
    C += [t["cons"][n] for n in NOTE_CONS if n in notes]
    P = (loc(s.get("pros"), t["_lang"]) or []) + P
    C = (loc(s.get("cons"), t["_lang"]) or []) + C
    return P, C


def build_review(lang, s):
    t = T[lang]
    page = p_review(lang, s["slug"])
    alts = {l: p_review(l, s["slug"]) for l in LANGS if s in sites_for(l)}
    name, dom = s["name"], s.get("domain", "")
    mon, yr = month_year(t)
    bonus = s_bonus(s, t)
    code = s.get("promo_code")
    if code:
        title = fill(t["brand_title_code"], name=name, month=(mon.capitalize() if lang in ("en","tr") else mon), year=yr, code=code)
        desc = fill(t["brand_desc_code"], name=name, month=mon, year=yr, code=code, bonus=bonus)
    else:
        title = fill(t["brand_title"], name=name, month=(mon.capitalize() if lang in ("en","tr") else mon), year=yr)
        desc = fill(t["brand_desc"], name=name, month=mon, year=yr, bonus=bonus)
    if loc(s.get("title"), lang):
        title = fill(loc(s["title"], lang), month=(mon.capitalize() if lang in ("en", "tr") else mon), year=yr)
        desc = fill(loc(s["desc"], lang), month=mon, year=yr)
    h1 = fill(t["brand_h1"], name=name, month=mon, year=yr)
    notes = s.get("notes", [])
    # --- promo code section
    generic = not loc(s.get("bonus"), lang)
    code_p = fill(t["code_have"] if code else (t["code_generic"] if generic else t["code_none"]), name=name, code=code or "", bonus=bonus)
    steps_src = list(t["steps_trade"] if s["type"] in TRADE_TYPES else t["steps"])
    if not code:
        steps_src = steps_src[:2]
    steps = "".join(f"<li>{e(x.replace('{name}', name)).replace('{code}', '<b>' + e(code or '') + '</b>')}</li>" for x in steps_src)
    # --- what is
    what = [fill(t["what_t"][s["type"]], name=name, domain=dom)]
    if s.get("founded") and not loc(s.get("about"), lang):
        what.append(fill(t["founded"], year=s["founded"]))
    what += [t["notes"][n] for n in notes if n in WHAT_NOTES]
    lic = ""
    if s.get("license"):
        lic = fill(t["lic_yes"], name=name, license=s["license"])
    elif s["type"] in GAMBLING:
        lic = fill(t["lic_no"], name=name)
    if len(s.get("games", [])) > 1:
        what.append(fill(GAMES[lang]["games_sent"], name=name, list=", ".join(games_list(s, lang))))
    if lic:
        what.append(lic)
    custom_about = loc(s.get("about"), lang) or []
    what_html = "".join(f"<p>{e(p)}</p>" for p in custom_about + [" ".join(what)])
    # --- modes
    modes = s.get("modes", [])
    modes_html = ""
    if modes and (s["type"] in GAMBLING or len(modes) >= 2):
        modes_html = (f'<h2>{e(t["sec_modes"])}</h2><p>{e(fill(t["modes_sent"], name=name, list=lst(modes, t["modes"])))}</p>'
                      f'<div class="mchips">' + "".join(f'<span class="mchip">{e(t["modes"].get(m, m))}</span>' for m in modes) + "</div>")
    # --- payments
    pay = []
    if s.get("deposit"):
        pay.append(fill(t["dep_sent"], list=lst(s["deposit"], t["pays"])))
    if s.get("withdraw"):
        pay.append(fill(t["wd_sent"], list=lst(s["withdraw"], t["pays"])))
    if s["type"] in TRADE_TYPES and s.get("seller_fee") not in EMPTY:
        pay.append(fill(t["fees_sent"], name=name, sf=s["seller_fee"], bf=s.get("buyer_fee") if s.get("buyer_fee") not in EMPTY else "—"))
    pay += [t["notes"][n] for n in notes if n not in WHAT_NOTES]
    pay_html = f'<h2>{e(t["sec_pay"])}</h2><p>{e(" ".join(pay))}</p>' if pay else ""
    wdm = fill(t["wd_methods"], list=lst(s["withdraw"], t["pays"])) if s.get("withdraw") else ""
    wd_steps_txt = [fill(x, name=name, methods=wdm) for x in t["wd_steps"]]
    pay_html += f'<h2>{e(fill(t["sec_wd"], name=name))}</h2><ol class="steps">' + "".join(f"<li>{e(x)}</li>" for x in wd_steps_txt) + "</ol>"
    # --- pros / cons
    P, C = pros_cons(s, t)
    pc = ""
    if P or C:
        pc = '<div class="pc">' + \
            (f'<div class="pros"><h3>{e(t["pros_title"])}</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in P) + "</ul></div>" if P else "") + \
            (f'<div class="cons"><h3>{e(t["cons_title"])}</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in C) + "</ul></div>" if C else "") + "</div>"
    # --- FAQ
    faq = [(fill(t["q_code"], name=name), fill(t["a_code_yes"] if code else (t["a_code_generic"] if generic else t["a_code_no"]), code=code or "", bonus=bonus))]
    if modes:
        faq.append((fill(t["q_what"], name=name), fill(t["modes_sent"], name=name, list=lst(modes, t["modes"]))))
    faq.append((fill(t["sec_wd"], name=name) + "?", " ".join(wd_steps_txt)))
    if s["type"] in GAMBLING:
        faq.append((fill(t["q_free"], name=name), fill(t["a_free"], name=name, via=fill(t["via_code"], code=code) if code else t["via_link"])))
        faq.append((fill(t["q_legit"], name=name), fill(t["a_legit_g"], name=name, modes=lst(modes, t["modes"]) or "-", lic=lic)))
    else:
        faq.append((fill(t["q_legit"], name=name), fill(t["a_legit_t"], name=name, type=t["type_one"][s["type"]].lower())))
    if lic:
        faq.append((fill(t["q_lic"], name=name), lic))
    faq.append((fill(t["q_safe"], name=name), t["a_safe"]))
    custom_faq = [tuple(x) for x in (loc(s.get("faq"), lang) or [])]
    seen = {q for q, _ in custom_faq}
    faq = custom_faq + [(q, a) for q, a in faq if q not in seen]
    faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
    # --- facts table
    facts = [(t["type"], t["type_one"][s["type"]]), (GAMES[lang]["games_label"], ", ".join(games_list(s, lang))), (t["bonus"], bonus), (t["promo_code"], code or t["no_code"])]
    if s.get("license"):
        facts.append((t["licensed"], s["license"]))
    if s["type"] in TRADE_TYPES:
        facts += [(t["seller_fee"], s.get("seller_fee")), (t["buyer_fee"], s.get("buyer_fee"))]
    facts += [(t["min_deposit"], s.get("min_deposit"))]
    if s.get("deposit"):
        facts.append((t["dep_sent"].split(":")[0], lst(s["deposit"], t["pays"])))
    if s.get("withdraw"):
        facts.append((t["wd_sent"].split(":")[0], lst(s["withdraw"], t["pays"])))
    facts.append((t["updated"], f"{mon} {yr}"))
    facts_html = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in facts if v not in EMPTY)
    # --- alternatives
    others = [o for o in sites_for(lang) if o["slug"] != s["slug"]]
    others = sorted(others, key=lambda o: (o["type"] != s["type"], o.get("order", 99)))[:3]
    others_html = "\n".join(card(o, lang, t, page) for o in others)
    crumbs = [(t["home_crumb"], p_home(lang)), (t["types"][s["type"]], p_type(lang, s["type"])), (name, page)]
    crumbs_html = " <span>/</span> ".join(
        f'<a href="{rel(page, u)}">{e(n)}</a>' if i < 2 else f"<span>{e(n)}</span>" for i, (n, u) in enumerate(crumbs))
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, s["type"])}
<main class="wrap review">
  <nav class="crumbs" aria-label="breadcrumb">{crumbs_html}</nav>
  <section class="rhero">
    {logo(s, "xl")}
    <div class="rhero-txt"><div class="badges">{badges(s, t)}</div>
      <h1>{e(h1)}</h1>
      <p class="lead">{e(s_short(s, t))}</p></div>
    <div class="rhero-cta">
      <div class="bonus"><span class="label">{e(t["bonus"])}</span><strong>{e(bonus)}</strong></div>
      {code_box(s, t)}
      {cta(s, t, page, "btn btn-primary btn-lg")}
    </div>
  </section>
  <div class="rgrid">
    <article class="prose">
      <h2>{e(fill(t["sec_code"], name=name))}</h2>
      <p>{e(code_p)} <span class="muted">{e(fill(t["checked"], month=mon, year=yr))}</span></p>
      <h3>{e(t["how_title"])}</h3><ol class="steps">{steps}</ol>
      <h2>{e(fill(t["sec_what"], name=name))}</h2>{what_html}
      {modes_html}
      {pay_html}
      {pc}
      {md(loc(s.get("seo"), lang) or [])}
      <h2>{e(fill(t["sec_faq"], name=name))}</h2><div class="faq-list">{faq_html}</div>
    </article>
    <aside class="facts"><table>{facts_html}</table>{cta(s, t, page, "btn btn-primary btn-lg")}</aside>
  </div>
  <section><h2 class="sec">{e(fill(t["sec_alt"], name=name))}</h2><div class="grid">{others_html}</div></section>
</main>
<div class="mbar" id="mbar" aria-hidden="true">{logo(s, "sm")}<div class="mbar-t"><b>{e(name)}</b><span>{e(code or t["no_code"])}</span></div>{cta(s, t, page, "btn btn-primary btn-sm")}</div>
{footer(lang, page)}'''
    extra = ld_tags(faq_ld(faq), breadcrumb_ld(crumbs))
    write(page, head(lang, page, title, desc, alts, extra) + body)
    return page, alts


def p_codes(lang): return f"{lang}/promo-codes/"


def build_codes(lang):
    t = T[lang]
    page = p_codes(lang)
    alts = {l: p_codes(l) for l in LANGS}
    mon, yr = month_year(t)
    title = fill(t["codes_title"], month=(mon.capitalize() if lang in ("en","tr") else mon), year=yr)
    desc = fill(t["codes_desc"], month=mon, year=yr)
    sites = sites_for(lang)
    rows = "".join(f'''<tr {data_attrs(s)}>
  <td><a class="tsite" href="{rel(page, p_review(lang, s["slug"]))}">{logo(s, "sm")}<span>{e(s["name"])}</span></a></td>
  <td><span class="badge t-{s["type"]}">{e(t["type_one"][s["type"]])}</span></td>
  <td>{e(s_bonus(s, t))}</td>
  <td>{code_box(s, t)}</td>
  <td class="tact">{cta(s, t, page, "btn btn-primary btn-sm")}<a class="btn btn-ghost btn-sm" href="{rel(page, p_review(lang, s["slug"]))}">{e(t["read_review"])}</a></td>
</tr>''' for s in sites)
    intro = "".join(f"<p class='lead'>{e(p)}</p>" for p in t["codes_intro"])
    faq_html, faq_ld_tag = faq_block(lang)
    crumbs = [(t["home_crumb"], p_home(lang)), (t["nav_codes"], page)]
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, "codes")}
<main class="wrap">
  <section class="hero">
    <span class="eyebrow"><i class="pulse"></i>{e(fill(t["checked"], month=mon, year=yr))}</span>
    <h1><span class="grad">{e(fill(t["codes_h1"], month=mon, year=yr))}</span></h1>
    {intro}
  </section>
  <div class="toolbar"><label class="search">{SEARCH_SVG}<input id="q" type="search" placeholder="{e(t["search"])}" autocomplete="off"></label></div>
  <div class="tablewrap codes"><table>
  <thead><tr><th>{e(t["site"])}</th><th>{e(t["type"])}</th><th>{e(t["bonus"])}</th><th>{e(t["promo_code"])}</th><th></th></tr></thead>
  <tbody>{rows}</tbody></table></div>
  <p id="empty" class="empty" hidden>{e(t["nothing_found"])}</p>
  {faq_html}
  {seo_block(lang, "codes")}
</main>
{footer(lang, page)}'''
    write(page, head(lang, page, title, desc, alts, faq_ld_tag + ld_tags(breadcrumb_ld(crumbs))) + body)
    return page, alts


def p_guides(lang): return f"{lang}/guides/"
def p_guide(lang, k): return f"{lang}/guides/{GUIDE_SLUG[k]}/"


def md(lines):
    out, ul = [], []
    def flush():
        if ul:
            out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in ul) + "</ul>"); ul.clear()
    for ln in lines:
        if ln.startswith("- "):
            ul.append(ln[2:]); continue
        flush()
        out.append(f"<h2>{e(ln[3:])}</h2>" if ln.startswith("## ") else f"<p>{e(ln)}</p>")
    flush()
    return "".join(out)


def build_guide(lang, k):
    t, G = T[lang], GUIDES[lang]
    g = G[k]
    page = p_guide(lang, k)
    alts = {l: p_guide(l, k) for l in LANGS}
    title = g["title"].replace("{year}", YEAR)
    crumbs = [(G["nav"], p_guides(lang)), (g["h1"], page)]
    crumbs_html = f'<a href="{rel(page, p_guides(lang))}">{e(G["nav"])}</a> <span>/</span> <span>{e(g["h1"])}</span>'
    extra_html = ""
    if k == "sell":
        tr = [s for s in sites_for(lang) if s["type"] in TRADE_TYPES]
        extra_html = '<div class="grid guide-grid">' + "\n".join(card(s, lang, t, page) for s in tr) + "</div>"
    other = [x for x in GUIDE_SLUG if x != k][0]
    more = (f'<a class="guide-next" href="{rel(page, p_guide(lang, other))}"><span>{e(G["read"])}</span>'
            f'<strong>{e(G[other]["h1"])}</strong>{ARROW_SVG}</a>')
    art = {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": g["desc"],
           "inLanguage": T[lang]["html_lang"], "dateModified": f"{UPDATED}-01", "mainEntityOfPage": f"{BASE_URL}/{page}",
           "author": {"@type": "Organization", "name": BRAND}}
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, "guides", clean=True)}
<main class="wrap review guide">
  <nav class="crumbs" aria-label="breadcrumb">{crumbs_html}</nav>
  <section class="hero"><span class="eyebrow"><i class="pulse"></i>{e(t["updated"])}: {e(UPDATED)}</span>
    <h1><span class="grad">{e(g["h1"])}</span></h1><p class="lead">{e(g["intro"])}</p></section>
  <article class="prose guide-body">{md(g["body"])}</article>
  {extra_html}
  {more}
</main>
{footer(lang, page, clean=True)}'''
    write(page, head(lang, page, title, g["desc"], alts, ld_tags(art, breadcrumb_ld(crumbs))) + body)
    return page, alts


def build_guides_hub(lang):
    t, G = T[lang], GUIDES[lang]
    page = p_guides(lang)
    alts = {l: p_guides(l) for l in LANGS}
    cards = "".join(f'''<a class="gcard" href="{rel(page, p_guide(lang, k))}"><h2>{e(G[k]["h1"])}</h2><p>{e(G[k]["desc"])}</p><span class="btn btn-primary"><span>{e(G["read"])}</span>{ARROW_SVG}</span></a>''' for k in GUIDE_SLUG)
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, "guides", clean=True)}
<main class="wrap">
  <section class="hero"><h1><span class="grad">{e(G["hub_h1"])}</span></h1><p class="lead">{e(G["hub_intro"])}</p></section>
  <div class="gcards">{cards}</div>
</main>
{footer(lang, page, clean=True)}'''
    write(page, head(lang, page, G["hub_title"], G["hub_desc"], alts) + body)
    return page, alts


# ---------- blog ----------
POSTS = {}          # slug -> {lang: post}
POSTS_BY_LANG = {}  # lang -> [post]


def p_blog(lang): return f"{lang}/blog/"
def p_post(lang, slug): return f"{lang}/blog/{slug}/"


def load_posts():
    import yaml
    for lang in LANGS:
        d = BLOG_DIR / lang
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            raw = f.read_text(encoding="utf-8")
            meta, body = {}, raw
            if raw.startswith("---"):
                _, fm, body = raw.split("---", 2)
                meta = yaml.safe_load(fm) or {}
            if meta.get("draft") or not meta.get("title"):
                continue
            post = dict(meta, slug=f.stem, lang=lang, body=body.strip(), date=str(meta.get("date", ""))[:10])
            POSTS.setdefault(f.stem, {})[lang] = post
            POSTS_BY_LANG.setdefault(lang, []).append(post)
    for lst_ in POSTS_BY_LANG.values():
        lst_.sort(key=lambda p: p["date"], reverse=True)


SITE_BY_SLUG = {s["slug"]: s for s in SITES}


def render_body(post, lang, page):
    import markdown
    html_ = markdown.markdown(post["body"], extensions=["tables", "sane_lists"])
    t = T[lang]
    def site_card(m):
        s = SITE_BY_SLUG.get(m.group(1).strip())
        return f'<div class="grid post-card">{card(s, lang, t, page)}</div>' if s else ""
    html_ = re.sub(r"<p>\s*\{\{\s*site:\s*([\w-]+)\s*\}\}\s*</p>", site_card, html_)
    html_ = re.sub(r"\{\{\s*site:\s*([\w-]+)\s*\}\}", site_card, html_)
    def fix_link(m):
        href = m.group(1)
        if "/go/" in href:
            return f'<a href="{href}" target="_blank" rel="sponsored nofollow noopener"'
        if href.startswith("http") and "casepromos.com" not in href:
            return f'<a href="{href}" target="_blank" rel="nofollow noopener"'
        return m.group(0)
    html_ = re.sub(r'<a href="([^"]+)"', fix_link, html_)
    return html_


def cover_url(post):
    c = post.get("cover")
    if not c:
        return None
    return c if c.startswith("http") else BASE_URL + "/" + c.lstrip("/")


def post_card(post, lang, page):
    B = BLOG[lang]
    c = cover_url(post)
    img = f'<img src="{e(c)}" alt="" loading="lazy">' if c else ""
    return (f'<a class="pcard" href="{rel(page, p_post(lang, post["slug"]))}">{img}<div class="pcard-in">'
            f'<time datetime="{e(post["date"])}">{e(post["date"])}</time><h2>{e(post["title"])}</h2>'
            f'<p>{e(post.get("description", ""))}</p><span class="btn btn-ghost btn-sm">{e(B["read"])}</span></div></a>')


def build_blog_index(lang):
    B = BLOG[lang]
    page = p_blog(lang)
    alts = {l: p_blog(l) for l in LANGS if POSTS_BY_LANG.get(l)}
    cards = "".join(post_card(p, lang, page) for p in POSTS_BY_LANG[lang])
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, "blog")}
<main class="wrap">
  <section class="hero"><h1><span class="grad">{e(B["h1"])}</span></h1><p class="lead">{e(B["intro"])}</p></section>
  <div class="pcards">{cards}</div>
</main>
{footer(lang, page)}'''
    crumbs = [(T[lang]["home_crumb"], p_home(lang)), (B["nav"], page)]
    write(page, head(lang, page, B["title"], B["desc"], alts, ld_tags(breadcrumb_ld(crumbs))) + body)
    return page, alts


def build_post(lang, post):
    t, B = T[lang], BLOG[lang]
    slug = post["slug"]
    page = p_post(lang, slug)
    alts = {l: p_post(l, slug) for l in LANGS if l in POSTS[slug]}
    title = post.get("seo_title") or post["title"]
    desc = post.get("description", "")
    body_html = render_body(post, lang, page)
    feat = [SITE_BY_SLUG[x] for x in (post.get("sites") or []) if x in SITE_BY_SLUG]
    feat_html = (f'<section><h2 class="sec">{e(B["featured"])}</h2><div class="grid">' +
                 "\n".join(card(s, lang, t, page) for s in feat) + "</div></section>") if feat else ""
    others = [p for p in POSTS_BY_LANG[lang] if p["slug"] != slug][:3]
    more = (f'<section><h2 class="sec">{e(B["more"])}</h2><div class="pcards">' +
            "".join(post_card(p, lang, page) for p in others) + "</div></section>") if others else ""
    c = cover_url(post)
    cover = f'<img class="post-cover" src="{e(c)}" alt="{e(post["title"])}">' if c else ""
    crumbs = [(t["home_crumb"], p_home(lang)), (B["nav"], p_blog(lang)), (post["title"], page)]
    crumbs_html = (f'<a href="{rel(page, p_home(lang))}">{e(t["home_crumb"])}</a> <span>/</span> '
                   f'<a href="{rel(page, p_blog(lang))}">{e(B["nav"])}</a> <span>/</span> <span>{e(post["title"])}</span>')
    art = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": post["title"], "description": desc,
           "inLanguage": t["html_lang"], "datePublished": post["date"], "dateModified": post.get("updated") and str(post["updated"])[:10] or post["date"],
           "mainEntityOfPage": f"{BASE_URL}/{page}", "author": {"@type": "Organization", "name": BRAND},
           "publisher": {"@type": "Organization", "name": BRAND}}
    if c:
        art["image"] = c
    body = f'''<body data-suggest='{e(suggest_data(alts, page))}' data-lang="{lang}">
{topbar(lang, page, alts, "blog")}
<main class="wrap review guide">
  <nav class="crumbs" aria-label="breadcrumb">{crumbs_html}</nav>
  <section class="hero"><span class="eyebrow"><i class="pulse"></i>{e(B["published"])}: <time datetime="{e(post["date"])}">{e(post["date"])}</time></span>
    <h1><span class="grad">{e(post["title"])}</span></h1>{f'<p class="lead">{e(desc)}</p>' if desc else ""}</section>
  {cover}
  <article class="prose guide-body post-body">{body_html}</article>
  {feat_html}
  {more}
</main>
{footer(lang, page)}'''
    write(page, head(lang, page, title, desc, alts, ld_tags(art, breadcrumb_ld(crumbs)), img=c) + body)
    return page, alts


def build_root():
    links = "".join(f'<a class="lang-card" href="{rel("", p_home(l))}" data-l="{l}"><span>{T[l]["flag"]}</span>{e(T[l]["lang_name"])}</a>' for l in LANGS)
    hl = "".join(f'<link rel="alternate" hreflang="{T[l]["html_lang"]}" href="{BASE_URL}/{p_home(l)}">' for l in LANGS)
    hl += f'<link rel="alternate" hreflang="x-default" href="{BASE_URL}/">'
    langs_js = json.dumps(LANGS)
    t = T[DEFAULT]
    suffix = "index.html" if LOCAL else ""
    html_ = f'''<!doctype html>
<html lang="{T[DEFAULT]["html_lang"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(BRAND)} — {e(t["home_title"].replace("{year}", YEAR))}</title>
<meta name="description" content="{e(t["home_desc"])}">
<link rel="canonical" href="{BASE_URL}/">{hl}
<meta property="og:type" content="website"><meta property="og:title" content="{e(BRAND)}"><meta property="og:description" content="{e(t["home_desc"])}"><meta property="og:url" content="{BASE_URL}/"><meta property="og:image" content="{BASE_URL}/assets/og/en-cs2.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE_URL}/assets/og/en-cs2.png">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">{FONTS}<link rel="stylesheet" href="assets/style.css">
<script>
(function(){{var L={langs_js},pick=null;
try{{var s=localStorage.getItem("lang");if(s&&L.indexOf(s)>-1)pick=s;}}catch(e){{}}
if(!pick){{var n=(navigator.languages||[navigator.language||""]);
for(var i=0;i<n.length&&!pick;i++){{var c=(n[i]||"").toLowerCase();
if(L.indexOf(c)>-1)pick=c;else{{var b=c.split("-")[0];
if(b==="pt"&&L.indexOf("pt-br")>-1)pick="pt-br";else if(L.indexOf(b)>-1)pick=b;}}}}}}
if(pick&&!/[?&]stay/.test(location.search))location.replace(pick+"/{suffix}");}})();
</script></head>
<body class="root"><div class="bg" aria-hidden="true"><i></i><i></i><i></i></div><main class="wrap rootbox">
<a class="brand big" href="./"><img src="assets/favicon.svg" alt="" width="44" height="44"><span>{e(BRAND)}</span></a>
<h1>{" · ".join(e(T[l]["choose_lang"]) for l in LANGS[:3])}</h1>
<div class="lang-grid">{links}</div>
</main><script src="assets/app.js" defer></script></body></html>'''
    write("", html_)


def build_go(s):
    url = e(s["ref_link"])
    write(p_go(s["slug"]), f'''<!doctype html><html><head><meta charset="utf-8">
<meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="0;url={url}">
<title>Redirecting…</title><script>location.replace({json.dumps(s["ref_link"])});</script></head>
<body style="font-family:system-ui;background:#07080d;color:#cbd5e1;padding:2rem">Redirecting… <a href="{url}" rel="sponsored nofollow" style="color:#a78bfa">{e(s["name"])}</a></body></html>''')


def build_sitemap(entries):
    urls = []
    for page, alts in entries:
        al = "".join(f'<xhtml:link rel="alternate" hreflang="{T[l]["html_lang"]}" href="{BASE_URL}/{alts[l]}"/>' for l in LANGS if l in alts)
        if DEFAULT in alts:
            al += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE_URL}/{alts[DEFAULT]}"/>'
        urls.append(f"<url><loc>{BASE_URL}/{page}</loc><lastmod>{BUILD_DATE}</lastmod>{al}</url>")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nDisallow: /go/\nDisallow: /admin/\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")


def main():
    for l in LANGS:
        T[l]["_lang"] = l
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST / "assets")
    if (ROOT / "logos").exists():
        shutil.copytree(ROOT / "logos", DIST / "assets/logos")
    entries = []
    load_posts()
    if (ROOT / "admin").exists():
        shutil.copytree(ROOT / "admin", DIST / "admin")
    for lang in LANGS:
        if POSTS_BY_LANG.get(lang):
            entries.append(build_blog_index(lang))
            for post in POSTS_BY_LANG[lang]:
                entries.append(build_post(lang, post))
        entries.append(build_list_page(lang))
        for ty in types_for(lang):
            entries.append(build_list_page(lang, ty))
        entries.append(build_codes(lang))
        for g in GAME_LIST:
            if sites_game(lang, g):
                entries.append(build_game(lang, g))
        entries.append(build_guides_hub(lang))
        for k in GUIDE_SLUG:
            entries.append(build_guide(lang, k))
        for s in sites_for(lang):
            entries.append(build_review(lang, s))
    for s in SITES:
        build_go(s)
    build_root()
    build_sitemap(entries)
    (DIST / "404.html").write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/"><title>404</title>', encoding="utf-8")
    kf = ROOT / "indexnow.key"
    if kf.exists():
        k = kf.read_text().strip()
        (DIST / f"{k}.txt").write_text(k, encoding="utf-8")
    (DIST / "CNAME").write_text("casepromos.com\n", encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {len(entries)} pages into {DIST}")


if __name__ == "__main__":
    main()
