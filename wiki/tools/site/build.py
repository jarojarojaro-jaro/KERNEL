#!/usr/bin/env python3
"""KERNEL knowledge base as a static web app (stdlib only, works offline).

    python3 wiki/tools/site/build.py [OUT]      # default: ~/.cache/wiki-graph (served on the LAN)

Pages: dashboard, one page per category (cards), note pages (rendered Markdown, backlinks, related,
local graph), the reports from product/research (read-only), REKORDY/ZRODLA as sortable tables,
AUDYT folded, search (client-side index), timeline and a clustered knowledge graph.
Assets live next to this file (assets/, vendor/); fonts are copied from app/landing/static/fonts.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import mdrender as md  # noqa: E402
from wiki import FOLDERS, LINK_RE, WIKI, REPO, Note, build_resolver, load_notes, strip_code  # noqa: E402

REPORTS = REPO / "product" / "research"
FONTS = REPO / "app" / "landing" / "static" / "fonts"
DEFAULT_OUT = Path.home() / ".cache" / "wiki-graph"

# category key -> (label, icon, colour); "" = pages in the wiki root
CATS: dict[str, tuple[str, str, str]] = {
    "decyzje": ("Decyzje", "flag", "#ff7a1a"),
    "eksperymenty": ("Eksperymenty", "flask", "#f5b841"),
    "karty": ("Karty GPU", "chip", "#e3a07a"),
    "kernele": ("Kernele", "zap", "#4ecdc4"),
    "metody": ("Metody", "checks", "#6fd08c"),
    "rocm": ("ROCm", "layers", "#ff5f6d"),
    "nvidia": ("NVIDIA", "eye", "#a3d65c"),
    "latki": ("Łatki", "branch", "#5ab0f0"),
    "modele": ("Modele", "cube", "#a99bff"),
    "research": ("Research", "filesearch", "#7f8cff"),
    "raporty": ("Raporty", "filetext", "#e58fd0"),
    "repo": ("Repozytoria", "folder", "#9fb3c8"),
    "ludzie-firmy": ("Ludzie i firmy", "users", "#c9a27e"),
    "produkt": ("Produkt", "package", "#ff8fa3"),
    "narzedzia": ("Narzędzia", "wrench", "#52c7e8"),
    "chmura": ("Chmura", "cloud", "#93b8ff"),
    "lekcje": ("Lekcje", "bulb", "#ffd84d"),
    "": ("Strony wiki", "grid", "#bdb9b1"),
}
CAT_DESC = {k: v[1] for k, v in FOLDERS.items()} | {
    "raporty": "Pełne raporty z product/research (tylko do odczytu); streszczenia są w Research",
}
# root pages: id -> (label, icon, url)
SPECIAL = {
    "REKORDY": ("Rekordy", "trophy", "/rekordy.html"),
    "ZRODLA": ("Rejestr źródeł", "bookmark", "/zrodla.html"),
    "KONWENCJE": ("Konwencje", "book", "/konwencje.html"),
    "AUDYT": ("Audyt liczb", "shield", "/audyt.html"),
    "log": ("Dziennik zmian", "history", "/dziennik.html"),
    "index": ("Strona główna wiki", "grid", "/wiki.html"),
}
NAV: list[tuple[str, list[str]]] = [
    ("Decyzje i zasady", ["decyzje", "@KONWENCJE"]),
    ("Wyniki", ["@REKORDY", "eksperymenty", "karty"]),
    ("Wiedza techniczna", ["kernele", "metody", "rocm", "nvidia", "latki"]),
    ("Modele", ["modele"]),
    ("Research i źródła", ["research", "raporty", "@ZRODLA", "repo", "ludzie-firmy"]),
    ("Produkt", ["produkt"]),
    ("Narzędzia i chmura", ["narzedzia", "chmura"]),
    ("Lekcje", ["lekcje"]),
]
GROUP_OF = {k.lstrip("@"): g for g, items in NAV for k in items}
NO_GRAPH = {"log", "AUDYT", "index"}  # meta pages that link to everything
TIMELINE_CATS = ("decyzje", "eksperymenty", "lekcje")
STATUS_LABEL = {"aktualne": "aktualne", "do-sprawdzenia": "do sprawdzenia", "nieaktualne": "nieaktualne"}
REPORT_REF = re.compile(r"product/research/([\w.+-]+?\.md)")
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
LOG_ENTRY = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*(\w+)\s*\|\s*(.+)$", re.M)


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def icon(name: str, cls: str = "i") -> str:
    return f'<svg class="{cls}" aria-hidden="true"><use href="/assets/icons.svg#{name}"></use></svg>'


@dataclass
class Doc:
    id: str
    cat: str
    kind: str  # note | hub | special | report
    title: str
    summary: str
    date: str
    status: str
    tags: list[str]
    typ: str
    zrodlo: str
    body: str
    src: Path
    url: str
    added: float = 0.0
    out: list[str] = field(default_factory=list)  # outgoing doc ids, in order
    back: list[str] = field(default_factory=list)

    @property
    def event_date(self) -> str:
        m = DATE_PREFIX.match(self.src.stem)
        return m.group(1) if m else ""

    @property
    def short(self) -> str:
        return self.title if len(self.title) <= 44 else Path(self.id).name


# ------------------------------------------------------------------ loading


def git_added() -> dict[str, float]:
    """repo-relative path -> unix time the file was first committed."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "log", "--diff-filter=A", "--format=@%at", "--name-only", "--", "wiki", "product/research"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    added: dict[str, float] = {}
    ts = 0.0
    for line in out.splitlines():
        if line.startswith("@"):
            ts = float(line[1:])
        elif line:
            added[line] = min(added.get(line, ts), ts)
    return added


def report_key(stem: str) -> tuple:
    m = re.match(r"(\d+)([a-z]*)", stem)
    return (int(m.group(1)), m.group(2)) if m else (0, stem)


def first_summary(text: str) -> str:
    lines = text.splitlines()
    for ln in lines[:80]:
        s = ln.strip()
        if s.startswith("**") and len(s) > 50:
            return md.plain(s).strip()
    for ln in lines[1:60]:
        s = ln.strip()
        if s and not s.startswith(("#", "|", "-", "`", ">", "<", "*")):
            return md.plain(s).strip()
    return ""


def clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


LABEL_MAX = 22


def short_label(d: "Doc") -> str:
    """Graph label of at most LABEL_MAX characters; the full title stays in the tooltip/panel."""
    if d.kind == "hub":
        return CATS[d.cat][0]
    if d.kind == "special":
        return SPECIAL.get(d.id, (d.title,))[0][:LABEL_MAX]
    t0 = d.title
    t = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[:–—-]?\s*", "", t0)
    t = re.sub(r"^(lekcja|decyzja|eksperyment|metoda|narzędzie|runda)\s*[:–—-]\s*", "", t, flags=re.I)
    prefix = ""
    m = re.match(r"^(?:raport\s+)?(\d{1,2}[a-z]?)\b\.?\s*(?:\([^)]*\))?\s*[:–—.-]*\s*(.*)$", t, flags=re.I)
    if m and m.group(2) and (d.kind == "report" or t.lower().startswith("raport")):
        prefix, t = f"R{m.group(1)} ", m.group(2)
    stripped = t != t0
    # keep the head of the title: cut at the first clause separator when enough remains
    for sep in (" (", ": ", " — ", " – ", " - ", ", ", "; ", " → ", " vs "):
        i = t.find(sep)
        if i >= 8:
            t = t[:i]
    if t.count("(") > t.count(")"):  # a cut inside "(d, sum)" would leave "Clamp (d"
        t = t[: t.rfind("(")]
    t = t.strip(" .,:;")
    room = LABEL_MAX - len(prefix)
    if len(t) > room:
        head = t[: room - 1]
        cut = head.rsplit(" ", 1)[0] if " " in head else head
        if len(cut) < room * 0.7:  # one short word left: cut mid-word instead
            cut = head
        t = cut.rstrip(" ,.:;–—-") + "…"
    if stripped and t:
        t = t[:1].upper() + t[1:]
    return prefix + (t or Path(d.id).name[:room])


def load() -> tuple[dict[str, Doc], callable]:
    added = git_added()
    notes = load_notes()
    resolve_note, _ = build_resolver(notes)
    docs: dict[str, Doc] = {}
    for n in notes:
        if n.rel.startswith(("tools/",)):
            continue
        nid = n.rel[:-3]
        cat = n.folder
        if cat and cat not in CATS:
            continue
        if n.name == "_hub":
            kind, url = "hub", f"/{cat}/"
        elif not cat:
            kind, url = "special", SPECIAL.get(nid, ("", "", f"/{nid}.html"))[2]
        else:
            kind, url = "note", f"/{nid}.html"
        src = n.path
        rel = src.relative_to(REPO).as_posix()
        docs[nid] = Doc(
            id=nid, cat=cat, kind=kind, title=md.plain(n.title) or n.name, summary=md.plain(n.summary),
            date=n.meta.get("aktualizacja", "") if re.match(r"\d{4}-\d\d-\d\d$", n.meta.get("aktualizacja", "")) else "",
            status=n.meta.get("status", "") if n.meta.get("status", "") in STATUS_LABEL else "",
            tags=[t for t in n.tags if t], typ=n.meta.get("typ", ""), zrodlo=n.meta.get("zrodlo", ""),
            body=n.body, src=src, url=url, added=added.get(rel, src.stat().st_mtime),
        )
    for p in sorted(REPORTS.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^# (.+)$", text, re.M)
        rid = f"raporty/{p.stem}"
        rel = p.relative_to(REPO).as_posix()
        ts = added.get(rel, p.stat().st_mtime)
        docs[rid] = Doc(
            id=rid, cat="raporty", kind="report", title=md.plain(m.group(1)).strip() if m else p.stem,
            summary=clip(first_summary(text), 260), date=time.strftime("%Y-%m-%d", time.localtime(ts)),
            status="", tags=[], typ="raport", zrodlo="", body=text, src=p, url=f"/{rid}.html", added=ts,
        )

    def resolve(target: str) -> Doc | None:
        hit = resolve_note(target)
        return docs.get(hit.rel[:-3]) if hit else None

    # links: wikilinks + report references (zrodlo, md links, code spans)
    for d in docs.values():
        seen: set[str] = set()
        if d.kind != "report":
            for t in LINK_RE.findall(strip_code(d.body)):
                hit = resolve(t)
                if hit and hit.id != d.id and hit.id not in seen:
                    seen.add(hit.id)
                    d.out.append(hit.id)
        for name in REPORT_REF.findall(d.zrodlo + "\n" + d.body):
            rid = f"raporty/{name[:-3]}"
            if rid in docs and rid != d.id and rid not in seen:
                seen.add(rid)
                d.out.append(rid)
    for d in docs.values():
        for t in d.out:
            if d.kind not in ("hub",) and d.id not in NO_GRAPH:
                docs[t].back.append(d.id)
    return docs, resolve


# ------------------------------------------------------------------ markdown context

def make_ctx(doc: Doc, docs: dict[str, Doc], resolve) -> md.Ctx:
    def wikilink(target: str):
        hit = resolve(target)
        return (hit.url, hit.short, hit.id) if hit else None

    def href(url: str):
        if url.startswith(("http://", "https://", "#")):
            return url
        path = url.split("#", 1)[0]
        try:
            p = (doc.src.parent / path).resolve()
        except (OSError, ValueError):
            return None
        if p.parent == REPORTS and p.suffix == ".md" and f"raporty/{p.stem}" in docs:
            return docs[f"raporty/{p.stem}"].url
        if p.suffix == ".md" and WIKI in p.parents:
            nid = p.relative_to(WIKI).as_posix()[:-3]
            if nid in docs:
                return docs[nid].url
        return None

    def code(text: str):
        m = REPORT_REF.search(text)
        if m and f"raporty/{m.group(1)[:-3]}" in docs:
            return docs[f"raporty/{m.group(1)[:-3]}"].url
        return None

    return md.Ctx(wikilink=wikilink, href=href, code=code)


def split_body(doc: Doc) -> tuple[str, str]:
    """Body without the H1 + summary line; returns (main, related-section markdown)."""
    body = doc.body
    if doc.kind == "hub":
        body = body.split("<!-- AUTO:START -->", 1)[0]
    m = re.search(r"^# .+$", body, re.M)
    if m:
        rest = body[m.end():]
        lines = rest.split("\n")
        for i, ln in enumerate(lines):
            if ln.strip():
                if doc.kind != "report" and re.fullmatch(r"\*\*(.+)\*\*", ln.strip()):
                    lines.pop(i)
                break
        body = body[: m.start()] + "\n".join(lines)
    related = ""
    r = re.search(r"^## Powiązane\s*$", body, re.M)
    if r:
        nxt = re.search(r"^## ", body[r.end():], re.M)
        end = r.end() + nxt.start() if nxt else len(body)
        related = body[r.end():end]
        body = body[: r.start()] + body[end:]
    return body.strip("\n"), related


def plain_body(text: str) -> str:
    text = md.COMMENT.sub(" ", text)
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        text = text[end + 5:] if end > 0 else text
    text = re.sub(r"^\s*(`{3,}|~{3,}).*$", " ", text, flags=re.M)
    text = re.sub(r"^\s*\|?\s*:?-{2,}.*$", " ", text, flags=re.M)
    text = md.plain(text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = text.replace("|", " · ")
    return re.sub(r"\s+", " ", text).strip()


# ------------------------------------------------------------------ components


def status_chip(status: str) -> str:
    if not status:
        return ""
    return f'<span class="status s-{status}">{esc(STATUS_LABEL[status])}</span>'


def cat_badge(cat: str, link: bool = True) -> str:
    label, ic, color = CATS[cat]
    inner = f'{icon(ic)}<span>{esc(label)}</span>'
    if link and cat:
        return f'<a class="cat-badge" style="--c:{color}" href="/{cat}/">{inner}</a>'
    return f'<span class="cat-badge" style="--c:{color}">{inner}</span>'


def card(d: Doc, extra: str = "", show_cat: bool = False) -> str:
    tags = "".join(f"<span>#{esc(t)}</span>" for t in d.tags if t != d.cat and t not in ("hub",))[:400]
    tags_html = f'<div class="card-tags">{tags}</div>' if tags else ""
    date = f'<time>{esc(d.date)}</time>' if d.date else ""
    catline = f'<span class="card-cat" style="--c:{CATS[d.cat][2]}">{esc(CATS[d.cat][0])}</span>' if show_cat else ""
    q = esc(" ".join([d.title, d.summary, " ".join(d.tags), Path(d.id).name]).lower())
    return (
        f'<a class="card" href="{d.url}" style="--c:{CATS[d.cat][2]}" data-s="{d.status}" data-d="{d.date}" '
        f'data-a="{int(d.added)}" data-g="{esc(" ".join(d.tags))}" data-q="{q}">'
        f'<div class="card-top">{catline}{date}{status_chip(d.status)}</div>'
        f"<h3>{esc(d.title)}</h3>"
        f'<p>{esc(clip(d.summary, 220))}</p>{extra}{tags_html}</a>'
    )


def mini_card(d: Doc) -> str:
    label, ic, color = CATS[d.cat]
    return (
        f'<a class="mini" href="{d.url}" style="--c:{color}" data-n="{esc(d.id)}">'
        f'<span class="mini-ic">{icon(ic)}</span><span class="mini-body"><b>{esc(d.title)}</b>'
        f'<small>{esc(clip(d.summary, 140)) or esc(label)}</small></span></a>'
    )


def sidebar(docs: dict[str, Doc], counts: dict[str, int], active: str) -> str:
    def item(href: str, ic: str, label: str, count: str, key: str, color: str = "") -> str:
        cur = ' aria-current="page"' if key == active else ""
        style = f' style="--c:{color}"' if color else ""
        cnt = f'<span class="cnt">{count}</span>' if count else ""
        return f'<a class="nav-item" href="{href}"{cur}{style}>{icon(ic)}<span class="lbl">{esc(label)}</span>{cnt}</a>'

    out = ['<nav class="nav" aria-label="Kategorie">', '<div class="nav-top">']
    out.append(item("/", "home", "Start", "", "home"))
    out.append(item("/szukaj.html", "search", "Szukaj", "", "search"))
    out.append(item("/os-czasu.html", "timeline", "Oś czasu", "", "timeline"))
    out.append(item("/graf.html", "graph", "Graf wiedzy", "", "graph"))
    out.append("</div>")
    for group, items in NAV:
        out.append(f'<div class="nav-group"><div class="nav-label">{esc(group)}</div>')
        for k in items:
            if k.startswith("@"):
                sid = k[1:]
                label, ic, url = SPECIAL[sid]
                out.append(item(url, ic, label, "", sid))
            else:
                label, ic, color = CATS[k]
                out.append(item(f"/{k}/", ic, label, str(counts.get(k, 0)), k, color))
        out.append("</div>")
    out.append('<div class="nav-group nav-meta"><div class="nav-label">O wiki</div>')
    for sid in ("log", "AUDYT", "index"):
        label, ic, url = SPECIAL[sid]
        out.append(item(url, ic, label, "", sid))
    out.append("</div></nav>")
    return "".join(out)


class Site:
    def __init__(self, docs: dict[str, Doc], resolve, out: Path):
        self.docs, self.resolve, self.out = docs, resolve, out
        self.files: dict[str, str | bytes] = {}
        self.by_cat: dict[str, list[Doc]] = {}
        for d in docs.values():
            if d.kind in ("note", "report"):
                self.by_cat.setdefault(d.cat, []).append(d)
        for lst in self.by_cat.values():
            lst.sort(key=lambda d: (d.date, d.added, d.title), reverse=True)
        self.counts = {k: len(v) for k, v in self.by_cat.items()}
        self.ver = ""
        self.nav_cache: dict[str, str] = {}

    # -------------------------------------------------------------- shell

    def page(self, path: str, title: str, body: str, active: str = "", cls: str = "", scripts: str = "",
             desc: str = "") -> None:
        if active not in self.nav_cache:
            self.nav_cache[active] = sidebar(self.docs, self.counts, active)
        v = self.ver
        doc_title = f"{title} · KERNEL baza wiedzy" if title else "KERNEL · baza wiedzy"
        self.files[path] = f"""<!doctype html>
<html lang="pl" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(doc_title)}</title>
<meta name="description" content="{esc(clip(desc, 160))}">
<meta name="color-scheme" content="dark light">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<script>try{{var t=localStorage.getItem('kb-theme');if(t)document.documentElement.dataset.theme=t;else if(matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.dataset.theme='light'}}catch(e){{}}</script>
<link rel="preload" href="/assets/fonts/mona-sans-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/app.css?v={v}">
</head><body class="{cls}">
<a class="skip" href="#main">Przejdź do treści</a>
<header class="topbar">
<button class="icon-btn menu-btn" type="button" aria-label="Menu" aria-controls="sidebar" aria-expanded="false">{icon("menu")}</button>
<a class="brand" href="/" aria-label="KERNEL – baza wiedzy, start"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">KERNEL</span><span class="brand-sub">baza wiedzy</span></a>
<button class="search-trigger" type="button" data-open-search>{icon("search")}<span>Szukaj notatek i raportów…</span><kbd>/</kbd></button>
<nav class="top-links" aria-label="Widoki"><a href="/os-czasu.html"{' aria-current="page"' if active == "timeline" else ""}>{icon("timeline")}<span>Oś czasu</span></a><a href="/graf.html"{' aria-current="page"' if active == "graph" else ""}>{icon("graph")}<span>Graf</span></a></nav>
<button class="icon-btn search-btn" type="button" data-open-search aria-label="Szukaj">{icon("search")}</button>
<button class="icon-btn theme-btn" type="button" aria-label="Przełącz motyw jasny/ciemny">{icon("sun", "i sun")}{icon("moon", "i moon")}</button>
</header>
<div class="shell">
<aside class="sidebar" id="sidebar">{self.nav_cache[active]}</aside>
<div class="scrim" data-close-nav></div>
<main id="main" class="main">{body}</main>
</div>
<div class="palette" id="palette" hidden role="dialog" aria-modal="true" aria-label="Szukaj">
<div class="palette-box"><div class="palette-input">{icon("search")}<input type="search" placeholder="Szukaj w {len(self.docs)} notatkach i raportach…" autocomplete="off" spellcheck="false" aria-label="Szukaj"><kbd>Esc</kbd></div>
<div class="palette-results" role="listbox"></div>
<div class="palette-foot"><span><kbd>↑</kbd><kbd>↓</kbd> wybór</span><span><kbd>Enter</kbd> otwórz</span><a href="/szukaj.html" class="palette-all">Wyszukiwanie zaawansowane →</a></div></div></div>
<script src="/assets/app.js?v={v}" defer></script>{scripts}
</body></html>
"""

    # -------------------------------------------------------------- pages

    def crumbs(self, d: Doc) -> str:
        parts = ['<a href="/">Start</a>']
        key = d.cat if d.cat else d.id
        group = GROUP_OF.get(key, "O wiki")
        parts.append(f"<span>{esc(group)}</span>")
        if d.cat:
            parts.append(f'<a href="/{d.cat}/">{esc(CATS[d.cat][0])}</a>')
        return '<nav class="crumbs" aria-label="Okruszki">' + '<i aria-hidden="true">/</i>'.join(parts) + "</nav>"

    def sources(self, d: Doc) -> str:
        if not d.zrodlo:
            return ""
        chips = []
        for part in [p.strip() for p in d.zrodlo.split(";") if p.strip()]:
            m = REPORT_REF.search(part)
            rid = f"raporty/{m.group(1)[:-3]}" if m else ""
            if rid in self.docs:
                chips.append(f'<a class="src src-link" href="{self.docs[rid].url}" title="{esc(part)}">{icon("filetext")}<code>{esc(part)}</code></a>')
            elif part.startswith(("http://", "https://")):
                chips.append(f'<a class="src src-link" href="{esc(part)}" target="_blank" rel="noopener">{icon("external")}<code>{esc(part)}</code></a>')
            else:
                chips.append(f'<span class="src">{icon("file")}<code>{esc(part)}</code></span>')
        more = f' data-more="{len(chips)}"' if len(chips) > 4 else ""
        return f'<details class="sources"{" open" if len(chips) <= 4 else ""}><summary>{icon("file")}Źródła <span class="cnt">{len(chips)}</span></summary><div class="src-list"{more}>{"".join(chips)}</div></details>'

    def note_page(self, d: Doc) -> None:
        ctx = make_ctx(d, self.docs, self.resolve)
        main_md, related_md = split_body(d)
        body_html = md.render(main_md, ctx)
        toc = [h for h in ctx.headings if h[0] in (2, 3)]
        # related: links in the "Powiązane" section, else none
        rel_ids: list[str] = []
        for t in LINK_RE.findall(related_md):
            hit = self.resolve(t)
            if hit and hit.id != d.id and hit.id not in rel_ids:
                rel_ids.append(hit.id)
        for name in REPORT_REF.findall(related_md):
            rid = f"raporty/{name[:-3]}"
            if rid in self.docs and rid not in rel_ids:
                rel_ids.append(rid)
        back = [b for b in d.back if self.docs[b].kind != "hub"]
        reports = [o for o in d.out if o.startswith("raporty/")] if d.kind != "report" else []
        chips = [f'<span class="chip">{icon("tag")}{esc(d.typ)}</span>' if d.typ else ""]
        if d.date:
            chips.append(f'<span class="chip">{icon("calendar")}<time>{esc(d.date)}</time></span>')
        chips.append(status_chip(d.status))
        chips += [f'<a class="chip tag" href="/szukaj.html?tag={esc(t)}">#{esc(t)}</a>' for t in d.tags]
        if d.kind == "report":
            chips.append(f'<span class="chip mono">{icon("file")}product/research/{esc(d.src.name)}</span>')
        kicker = cat_badge(d.cat) if d.cat else f'<span class="cat-badge" style="--c:{CATS[""][2]}">{icon(SPECIAL.get(d.id, ("", "grid"))[1])}<span>{esc(GROUP_OF.get(d.id, "O wiki"))}</span></span>'
        report_btn = ""
        if reports:
            report_btn = '<div class="report-links">' + "".join(
                f'<a class="btn btn-soft" href="{self.docs[r].url}">{icon("filetext")}Pełny raport: {esc(clip(self.docs[r].title, 60))}</a>'
                for r in reports[:3]) + "</div>"
        head = (
            f'<header class="doc-head">{self.crumbs(d)}<div class="kicker">{kicker}</div><h1>{esc(d.title)}</h1>'
            f'{f"<p class=lead>{esc(d.summary)}</p>" if d.summary and d.kind != "report" else ""}'
            f'<div class="chips">{"".join(chips)}</div>{report_btn}{self.sources(d)}</header>'
        )
        sections = []
        if rel_ids:
            sections.append(
                f'<section class="linkset"><h2>{icon("link")}Powiązane <span class="cnt">{len(rel_ids)}</span></h2>'
                f'<div class="mini-grid">{"".join(mini_card(self.docs[i]) for i in rel_ids)}</div></section>'
            )
        if back:
            label = "Cytowany w" if d.kind == "report" else "Linkują tutaj"
            sections.append(
                f'<section class="linkset"><h2>{icon("backlink")}{label} <span class="cnt">{len(back)}</span></h2>'
                f'<div class="mini-grid">{"".join(mini_card(self.docs[i]) for i in back)}</div></section>'
            )
        pager = ""
        siblings = self.by_cat.get(d.cat, []) if d.kind in ("note", "report") else []
        if d in siblings:
            i = siblings.index(d)
            prv = siblings[i - 1] if i > 0 else None
            nxt = siblings[i + 1] if i + 1 < len(siblings) else None
            pager = '<nav class="pager" aria-label="Poprzednia i następna">'
            pager += (f'<a class="prev" href="{prv.url}" rel="prev"><small>{icon("arrowleft")}Nowsza</small><b>{esc(prv.title)}</b></a>' if prv else "<span></span>")
            pager += (f'<a class="next" href="{nxt.url}" rel="next"><small>Starsza{icon("arrowright")}</small><b>{esc(nxt.title)}</b></a>' if nxt else "<span></span>")
            pager += "</nav>"
        toc_html = ""
        if len(toc) >= 2:
            toc_html = '<div class="rail-card toc"><h3>Na tej stronie</h3><ol>' + "".join(
                f'<li class="l{lvl}"><a href="#{sid}">{esc(t)}</a></li>' for lvl, sid, t in toc[:40]) + "</ol></div>"
        graph_card = ""
        if d.id not in NO_GRAPH:
            graph_card = (
                f'<div class="rail-card graph-card"><div class="rail-head"><h3>Lokalny graf</h3>'
                f'<div class="seg" role="group" aria-label="Zasięg"><button type="button" data-hops="1" aria-pressed="true">1 krok</button><button type="button" data-hops="2" aria-pressed="false">2 kroki</button></div></div>'
                f'<div class="local-graph" data-id="{esc(d.id)}"><span class="lg-empty">Ładowanie grafu…</span></div>'
                f'<a class="rail-more" href="/graf.html#{esc(d.id)}">Otwórz w grafie wiedzy {icon("arrowright")}</a></div>'
            )
        wide = d.id in ("REKORDY", "ZRODLA", "AUDYT")
        body = body_html
        if d.id == "AUDYT":
            body = self.folded(main_md, ctx)
        tools = ""
        if d.id in ("REKORDY", "ZRODLA", "AUDYT"):
            jumps = "".join(f'<a href="#{sid}">{esc(clip(t, 42))}</a>' for lvl, sid, t in ctx.headings if lvl == 2)
            tools = (
                f'<div class="table-tools" data-table-tools><label class="filter">{icon("filter")}'
                f'<input type="search" placeholder="Filtruj wiersze wszystkich tabel…" aria-label="Filtruj wiersze"></label>'
                f'<span class="rows-count"></span></div><nav class="jump">{jumps}</nav>'
            )
        article = (
            f'<article class="doc{" doc-wide" if wide else ""}" data-id="{esc(d.id)}" data-cat="{d.cat}">{head}{tools}<div class="prose"{" data-tables" if wide else ""}>{body}</div>'
            f'{"".join(sections)}{pager}</article>'
        )
        rail = "" if wide else f'<aside class="rail">{graph_card}{toc_html}</aside>'
        self.page(
            d.url.lstrip("/"), d.title,
            f'<div class="doc-layout{" wide" if wide else ""}">{article}{rail}</div>',
            active=d.cat or d.id, cls=f"p-doc k-{d.kind}", desc=d.summary,
        )

    def folded(self, main_md: str, ctx: md.Ctx) -> str:
        parts = re.split(r"(?m)^(?=## )", main_md)
        out = [md.render(parts[0], ctx)]
        for part in parts[1:]:
            head, _, rest = part.partition("\n")
            title = head[3:].strip()
            sid = ctx.slug(md.plain(title))
            ctx.headings.append((2, sid, md.plain(title)))
            rows = len(re.findall(r"(?m)^\|", rest))
            meta = f'<span class="cnt">{max(rows - 2, 0)} wierszy</span>' if rows > 2 else ""
            out.append(
                f'<details class="fold" id="{sid}"><summary><span>{md.inline(title, ctx)}</span>{meta}{icon("chevron", "i chev")}</summary>'
                f'<div class="fold-body">{md.render(rest, ctx)}</div></details>'
            )
        return "\n".join(out)

    def category_page(self, cat: str) -> None:
        label, ic, color = CATS[cat]
        items = self.by_cat.get(cat, [])
        hub = self.docs.get(f"{cat}/_hub")
        lead = hub.summary if hub and hub.summary else CAT_DESC.get(cat, "")
        intro = ""
        if hub:
            main_md, _ = split_body(hub)
            keep = [p for p in re.split(r"\n\s*\n", main_md) if p.strip() and not re.search(r"Wróć:|generowana|nie edytuj", p)]
            if keep:
                intro = f'<div class="prose hub-intro">{md.render(chr(10).join(keep), make_ctx(hub, self.docs, self.resolve))}</div>'
        st = {s: sum(1 for d in items if d.status == s) for s in STATUS_LABEL}
        tagc: dict[str, int] = {}
        for d in items:
            for t in d.tags:
                if t != cat:
                    tagc[t] = tagc.get(t, 0) + 1
        tag_opts = "".join(f'<option value="{esc(t)}">#{esc(t)} ({c})</option>' for t, c in sorted(tagc.items(), key=lambda x: (-x[1], x[0])) if c > 1)
        stats = f'<span><b>{len(items)}</b> {"raportów" if cat == "raporty" else "notatek"}</span>'
        if cat != "raporty":
            stats += "".join(f'<span class="st s-{s}"><i></i><b>{c}</b> {STATUS_LABEL[s]}</span>' for s, c in st.items() if c)
        seg = ""
        if cat != "raporty":
            seg = '<div class="seg" role="group" aria-label="Status" data-filter="status"><button type="button" data-v="" aria-pressed="true">Wszystkie</button>' + "".join(
                f'<button type="button" data-v="{s}" aria-pressed="false">{STATUS_LABEL[s].capitalize()}</button>' for s in STATUS_LABEL if st[s]) + "</div>"
        group = GROUP_OF.get(cat, "")
        body = f"""<div class="page cat-page" style="--c:{color}">
<header class="page-head"><nav class="crumbs"><a href="/">Start</a><i>/</i><span>{esc(group)}</span></nav>
<div class="page-title"><span class="big-ic">{icon(ic)}</span><div><h1>{esc(label)}</h1><p class="lead">{esc(lead)}</p></div></div>
<div class="stats-line">{stats}</div></header>
{intro}
<div class="toolbar" data-cards-toolbar>
<label class="filter">{icon("filter")}<input type="search" placeholder="Filtruj {esc(label.lower())}…" aria-label="Filtruj"></label>
{seg}
{f'<select data-filter="tag" aria-label="Tag"><option value="">Wszystkie tagi</option>{tag_opts}</select>' if tag_opts else ""}
<select data-sort aria-label="Sortowanie"><option value="new">Najnowsze</option><option value="old">Najstarsze</option><option value="az">A–Z</option></select>
<span class="shown"></span>
</div>
<div class="cards" data-cards>{"".join(card(d) for d in items)}</div>
<p class="empty" hidden>Nic nie pasuje do filtrów.</p>
</div>"""
        self.page(f"{cat}/index.html", label, body, active=cat, cls="p-cat", desc=lead)

    def home(self, log_entries: list[tuple[str, str, str, str]]) -> None:
        idx = self.docs["index"]
        ctx = make_ctx(idx, self.docs, self.resolve)
        paras = [p for p in re.split(r"\n\s*\n", idx.body.split("## ", 1)[0]) if p.strip() and not p.lstrip().startswith(("#", "**"))]
        about = md.inline(paras[0].strip(), ctx) if paras else ""
        notes = [d for d in self.docs.values() if d.kind == "note"]
        reports = [d for d in self.docs.values() if d.kind == "report"]
        links = sum(len(d.out) for d in self.docs.values())
        last = max((d.date for d in notes if d.date), default="")
        # categories grouped
        maxc = max(self.counts.values())
        cat_rows = []
        for group, items in NAV:
            cells = []
            for k in items:
                if k.startswith("@"):
                    label, ic, url = SPECIAL[k[1:]]
                    cells.append(f'<a class="cat-tile special" href="{url}">{icon(ic)}<span class="ct-name">{esc(label)}</span><span class="ct-n">↗</span></a>')
                    continue
                label, ic, color = CATS[k]
                c = self.counts.get(k, 0)
                cells.append(
                    f'<a class="cat-tile" href="/{k}/" style="--c:{color};--w:{c / maxc:.3f}">{icon(ic)}<span class="ct-name">{esc(label)}</span>'
                    f'<span class="ct-n">{c}</span><span class="ct-bar"></span></a>'
                )
            cat_rows.append(f'<div class="cat-group"><div class="cg-label">{esc(group)}</div><div class="cg-tiles">{"".join(cells)}</div></div>')
        # log
        log_html = []
        for date, kind, title, body in log_entries[:10]:
            log_ctx = make_ctx(self.docs["log"], self.docs, self.resolve)
            snippet = md.inline(clip(re.sub(r"\s+", " ", body).strip(), 220), log_ctx)
            log_html.append(
                f'<li><div class="lg-meta"><time>{esc(date)}</time><span class="kind k-{esc(kind)}">{esc(kind)}</span></div>'
                f'<div class="lg-body"><b>{md.inline(title, log_ctx)}</b><p>{snippet}</p></div></li>'
            )
        records = self.top_records()

        def newest(cat: str, n: int) -> list[Doc]:
            return self.by_cat.get(cat, [])[:n]

        def strip_cards(cat: str, n: int, title: str, ic: str) -> str:
            ds = newest(cat, n)
            return (
                f'<section class="dash-sec"><div class="sec-head"><h2>{icon(ic)}{esc(title)}</h2><a href="/{cat}/">Wszystkie {self.counts.get(cat, 0)} {icon("arrowright")}</a></div>'
                f'<div class="cards cards-3">{"".join(card(d) for d in ds)}</div></section>'
            )

        body = f"""<div class="page home">
<section class="hero">
<div class="overline"><span class="dot"></span>KERNEL · baza wiedzy projektu</div>
<h1>Szybkie lokalne LLM na&nbsp;RX&nbsp;7900&nbsp;XTX i&nbsp;kartach NVIDIA — <em>wszystko, co wiemy</em>.</h1>
<p class="lead">{about}</p>
<button class="hero-search" type="button" data-open-search>{icon("search")}<span>Szukaj w notatkach, raportach, liczbach…</span><kbd>/</kbd></button>
<div class="kpis">
<div class="kpi"><b>{len(notes)}</b><span>notatek</span></div>
<div class="kpi"><b>{len(reports)}</b><span>raportów</span></div>
<div class="kpi"><b>{links}</b><span>powiązań</span></div>
<div class="kpi"><b>{self.counts.get("decyzje", 0)}</b><span>decyzji</span></div>
<div class="kpi"><b>{esc(last)}</b><span>ostatnia aktualizacja</span></div>
</div>
</section>
<section class="dash-sec"><div class="sec-head"><h2>{icon("grid")}Kategorie</h2><a href="/graf.html">Graf wiedzy {icon("arrowright")}</a></div>
<div class="cat-groups">{"".join(cat_rows)}</div></section>
<div class="dash-2">
<section class="dash-sec records"><div class="sec-head"><h2>{icon("trophy")}Najlepsze wyniki</h2><a href="/rekordy.html">Wszystkie rekordy {icon("arrowright")}</a></div>{records}</section>
<section class="dash-sec changes"><div class="sec-head"><h2>{icon("history")}Ostatnie zmiany</h2><a href="/dziennik.html">Dziennik {icon("arrowright")}</a></div><ol class="log-list">{"".join(log_html)}</ol></section>
</div>
{strip_cards("decyzje", 6, "Najnowsze decyzje", "flag")}
{strip_cards("lekcje", 6, "Najnowsze lekcje", "bulb")}
{strip_cards("raporty", 6, "Najnowsze raporty", "filetext")}
</div>"""
        self.page("index.html", "", body, active="home", cls="p-home", desc=idx.summary)

    def top_records(self) -> str:
        rek = self.docs["REKORDY"]
        ctx = make_ctx(rek, self.docs, self.resolve)
        out = []
        for sec in re.split(r"(?m)^## ", rek.body)[1:]:
            head, _, rest = sec.partition("\n")
            rows = [ln for ln in rest.splitlines() if ln.startswith("|")]
            if len(rows) < 3:
                continue
            cols = [c.lower() for c in md.split_row(rows[0])]
            ci = lambda pred: next((i for i, c in enumerate(cols) if pred(c)), None)  # noqa: E731
            i_rec, i_date = ci(lambda c: c.startswith("rekord")), ci(lambda c: c == "data")
            i_met, i_card = ci(lambda c: "metryka" in c), ci(lambda c: c.startswith("karta"))
            i_prod = ci(lambda c: c.startswith("prod"))
            if i_rec is None or i_met is None:
                continue
            picked = [md.split_row(r) for r in rows[2:] if "**" in md.split_row(r)[i_rec]][:3]
            if not picked:
                continue
            title = re.sub(r"\s*\(.*$", "", head).strip()
            lis = []
            for cells in picked:
                g = lambda i: cells[i] if i is not None and i < len(cells) else ""  # noqa: E731
                rec = re.search(r"\*\*(.+?)\*\*", g(i_rec))
                big = md.plain(rec.group(1)) if rec else md.plain(g(i_rec))
                rest_txt = md.plain(g(i_rec).replace(rec.group(0), "", 1)).strip(" ,;") if rec else ""
                prod = md.plain(g(i_prod))
                prod_cls = "yes" if prod.startswith("tak") else "no"
                card_txt = f'<span class="rc-card">{md.inline(g(i_card), ctx)}</span>' if i_card is not None else ""
                lis.append(
                    f'<li><div class="rc-val">{esc(big)}</div><div class="rc-meta">{card_txt}<span class="rc-met">{md.inline(g(i_met), ctx)}</span>'
                    f'{f"<small>{esc(clip(rest_txt, 70))}</small>" if rest_txt else ""}</div>'
                    f'<div class="rc-side"><time>{esc(md.plain(g(i_date)))}</time>{f"<span class=prod-{prod_cls}>{esc(clip(prod, 18))}</span>" if prod else ""}</div></li>'
                )
            out.append(f'<div class="rec-block"><h3>{esc(title)}</h3><ul>{"".join(lis)}</ul></div>')
        return "".join(out[:5])

    def log_page(self, entries: list[tuple[str, str, str, str]]) -> None:
        d = self.docs["log"]
        ctx = make_ctx(d, self.docs, self.resolve)
        items = []
        for date, kind, title, body in entries:
            items.append(
                f'<li class="tl-item"><div class="tl-date"><time>{esc(date)}</time><span class="kind k-{esc(kind)}">{esc(kind)}</span></div>'
                f'<div class="tl-card"><h3>{md.inline(title, ctx)}</h3><div class="prose">{md.render(body, ctx)}</div></div></li>'
            )
        body = f"""<div class="page"><header class="page-head">{self.crumbs(d)}<div class="page-title"><span class="big-ic">{icon("history")}</span><div><h1>{esc(d.title)}</h1><p class="lead">{esc(d.summary)}</p></div></div>
<div class="stats-line"><span><b>{len(entries)}</b> wpisów, najnowsze na górze</span></div></header>
<ol class="tl log-tl">{"".join(items)}</ol></div>"""
        self.page(d.url.lstrip("/"), d.title, body, active="log", cls="p-log", desc=d.summary)

    def search_page(self) -> None:
        cats = "".join(f'<option value="{k}">{esc(v[0])}</option>' for k, v in CATS.items())
        body = f"""<div class="page search-page">
<header class="page-head"><div class="page-title"><span class="big-ic">{icon("search")}</span><div><h1>Szukaj</h1><p class="lead">Pełny tekst wszystkich notatek i raportów, od razu w przeglądarce. Kilka słów = wszystkie muszą wystąpić; „cudzysłów” szuka frazy.</p></div></div></header>
<div class="search-box"><label class="big-filter">{icon("search")}<input id="sq" type="search" placeholder="np. mmvq, PM4, 109 t/s, lookup…" autocomplete="off" spellcheck="false" autofocus aria-label="Szukaj"></label></div>
<div class="toolbar search-filters">
<select id="sf-cat" aria-label="Kategoria"><option value="">Wszystkie kategorie</option>{cats}</select>
<select id="sf-status" aria-label="Status"><option value="">Każdy status</option>{"".join(f'<option value="{s}">{l}</option>' for s, l in STATUS_LABEL.items())}</select>
<input id="sf-tag" list="sf-tags" placeholder="#tag" aria-label="Tag" autocomplete="off"><datalist id="sf-tags"></datalist>
<label class="date-f">od <input id="sf-from" type="date" aria-label="Data od"></label>
<label class="date-f">do <input id="sf-to" type="date" aria-label="Data do"></label>
<button class="btn btn-ghost" type="button" id="sf-reset">Wyczyść</button>
</div>
<div class="facets" id="facets"></div>
<p class="result-count" id="scount" aria-live="polite"></p>
<ol class="results" id="results"></ol>
</div>"""
        self.page("szukaj.html", "Szukaj", body, active="search", cls="p-search", desc="Wyszukiwanie pełnotekstowe")

    def timeline_page(self) -> None:
        items = []
        for c in TIMELINE_CATS:
            for d in self.by_cat.get(c, []):
                items.append([d.url, d.title, c, d.status, d.date, d.event_date, int(d.added), clip(d.summary, 240), d.tags])
        data = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
        chips = "".join(
            f'<button type="button" class="tchip" data-cat="{c}" aria-pressed="true" style="--c:{CATS[c][2]}">{icon(CATS[c][1])}{esc(CATS[c][0])}<span class="cnt">{self.counts.get(c, 0)}</span></button>'
            for c in TIMELINE_CATS)
        body = f"""<div class="page timeline-page">
<header class="page-head"><nav class="crumbs"><a href="/">Start</a><i>/</i><span>Widoki</span></nav><div class="page-title"><span class="big-ic">{icon("timeline")}</span><div><h1>Oś czasu</h1><p class="lead">Decyzje, eksperymenty i lekcje w kolejności dat. Wiele notatek ma tę samą datę aktualizacji — przełącz na „datę zdarzenia”, żeby zobaczyć, kiedy coś się wydarzyło (z nazwy pliku).</p></div></div></header>
<div class="toolbar tl-tools">
<div class="tchips">{chips}</div>
<div class="seg" role="group" aria-label="Data" id="tl-mode"><button type="button" data-v="a" aria-pressed="true">Aktualizacja</button><button type="button" data-v="e" aria-pressed="false">Data zdarzenia</button></div>
<select id="tl-status" aria-label="Status"><option value="">Każdy status</option>{"".join(f'<option value="{s}">{l}</option>' for s, l in STATUS_LABEL.items())}</select>
<label class="filter">{icon("filter")}<input id="tl-q" type="search" placeholder="Filtruj…" aria-label="Filtruj"></label>
</div>
<div class="tl-hist" id="tl-hist" aria-hidden="true"></div>
<ol class="tl" id="tl"></ol>
</div>
<script id="tl-data" type="application/json">{data.replace("</", "<\\/")}</script>"""
        self.page("os-czasu.html", "Oś czasu", body, active="timeline", cls="p-timeline", desc="Oś czasu decyzji, eksperymentów i lekcji")

    def graph_page(self) -> None:
        legend = []
        for group, items in NAV:
            for k in items:
                if k.startswith("@"):
                    continue
                label, ic, color = CATS[k]
                legend.append(f'<button type="button" class="lg-chip" data-cat="{k}" style="--c:{color}" aria-pressed="true"><i></i>{esc(label)}<span>{self.counts.get(k, 0)}</span></button>')
        body = f"""<div class="graph-page">
<div class="gp-canvas" id="gp"></div>
<div class="gp-loading" id="gp-loading"><span class="spinner"></span>Układam graf…</div>
<div class="gp-top">
<div class="gp-title"><h1>Graf wiedzy</h1><p>Kolor = kategoria · większe = więcej powiązań · kliknij skupisko, żeby je przybliżyć, notatkę — żeby zobaczyć jej sąsiadów</p></div>
<label class="filter gp-find">{icon("search")}<input id="gp-q" type="search" placeholder="Znajdź notatkę w grafie…" autocomplete="off" aria-label="Znajdź notatkę" list="gp-list"></label><datalist id="gp-list"></datalist>
</div>
<div class="gp-legend" id="gp-legend"><div class="lg-head"><span>Kategorie</span><button type="button" class="link-btn" id="gp-all">pokaż wszystkie</button></div>{"".join(legend)}</div>
<div class="gp-zoom"><button type="button" class="icon-btn" id="gp-in" aria-label="Przybliż">{icon("plus")}</button><button type="button" class="icon-btn" id="gp-out" aria-label="Oddal">{icon("minus")}</button><button type="button" class="icon-btn" id="gp-fit" aria-label="Pokaż cały graf">{icon("fit")}</button></div>
<aside class="gp-panel" id="gp-panel" hidden>
<button type="button" class="icon-btn gp-close" id="gp-close" aria-label="Zamknij">{icon("x")}</button>
<div class="gp-panel-body"></div>
<div class="rail-head"><h3>Sąsiedzi</h3><div class="seg" role="group" aria-label="Zasięg"><button type="button" data-hops="1" aria-pressed="true">1 krok</button><button type="button" data-hops="2" aria-pressed="false">2 kroki</button></div></div>
<div class="local-graph gp-local"></div>
<div class="gp-nb"></div>
</aside>
</div>"""
        self.page("graf.html", "Graf wiedzy", body, active="graph", cls="p-graph",
                  scripts=f'\n<script src="/assets/vendor/force-graph.min.js?v={self.ver}" defer></script><script src="/assets/graph.js?v={self.ver}" defer></script>',
                  desc="Graf powiązań bazy wiedzy")

    # -------------------------------------------------------------- data

    def data_files(self) -> None:
        ids = [d.id for d in self.docs.values() if d.id not in NO_GRAPH]
        pos = {i: n for n, i in enumerate(ids)}
        edges: dict[tuple[int, int], int] = {}
        deg = {i: 0 for i in ids}
        for d in self.docs.values():
            if d.id not in pos:
                continue
            for t in d.out:
                if t not in pos:
                    continue
                a, b = sorted((pos[d.id], pos[t]))
                hub = int(self.docs[d.id].kind == "hub" or self.docs[t].kind == "hub")
                edges[(a, b)] = 0 if hub else edges.get((a, b), 1)
        for (a, b), w in edges.items():
            if w:
                deg[ids[a]] += 1
                deg[ids[b]] += 1
        nodes = []
        for i in ids:
            d = self.docs[i]
            nodes.append([i, d.title, d.cat, d.url, d.status, d.date, clip(d.summary, 200), deg[i], 1 if d.kind == "hub" else 0, short_label(d)])
        graph = {
            "cats": {k: [v[0], v[2], v[1]] for k, v in CATS.items()},
            "order": [k for _, items in NAV for k in items if not k.startswith("@")],
            "nodes": nodes,
            "links": [[a, b, w] for (a, b), w in sorted(edges.items())],
        }
        self.files["data/graph.json"] = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
        rows = []
        for d in self.docs.values():
            if d.kind == "hub":
                continue
            rows.append([d.url, d.title, d.cat, d.status, " ".join(d.tags), d.date, d.summary, plain_body(d.body)])
        tags = sorted({t for d in self.docs.values() for t in d.tags})
        search = {"cats": {k: [v[0], v[2], v[1]] for k, v in CATS.items()}, "tags": tags, "docs": rows}
        self.files["data/search.json"] = json.dumps(search, ensure_ascii=False, separators=(",", ":"))

    def assets(self) -> None:
        css = (HERE / "assets" / "app.css").read_text(encoding="utf-8")
        js = (HERE / "assets" / "app.js").read_text(encoding="utf-8")
        gjs = (HERE / "assets" / "graph.js").read_text(encoding="utf-8")
        self.ver = hashlib.sha1((css + js + gjs).encode()).hexdigest()[:10]
        self.files["assets/app.css"] = css
        self.files["assets/app.js"] = js
        self.files["assets/graph.js"] = gjs
        self.files["assets/icons.svg"] = (HERE / "assets" / "icons.svg").read_text(encoding="utf-8")
        self.files["assets/favicon.svg"] = (HERE / "assets" / "favicon.svg").read_text(encoding="utf-8")
        for p in (HERE / "vendor").iterdir():
            self.files[f"assets/vendor/{p.name}"] = p.read_bytes()
        if FONTS.is_dir():
            for p in FONTS.glob("*.woff2"):
                self.files[f"assets/fonts/{p.name}"] = p.read_bytes()

    def write(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        written = set()
        for rel, content in self.files.items():
            p = self.out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8") if isinstance(content, str) else content
            if not p.exists() or p.read_bytes() != data:
                tmp = p.with_name(p.name + ".tmp")
                tmp.write_bytes(data)
                os.replace(tmp, p)
            written.add(p)
        # drop pages of deleted notes; the served directory itself must stay (it is the server's cwd)
        for root, dirs, files in os.walk(self.out, topdown=False):
            for f in files:
                if Path(root, f) not in written:
                    Path(root, f).unlink()
            if Path(root) != self.out and not any(Path(root).iterdir()):
                Path(root).rmdir()


def parse_log(d: Doc) -> list[tuple[str, str, str, str]]:
    text = d.body
    ms = list(LOG_ENTRY.finditer(text))
    entries = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        entries.append((m.group(1), m.group(2), m.group(3).strip(), text[m.end():end].strip()))
    return entries[::-1]  # append-only file: newest last


def main() -> None:
    t0 = time.time()
    out = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_OUT
    docs, resolve = load()
    site = Site(docs, resolve, out)
    site.assets()
    for d in docs.values():
        if d.kind in ("note", "report") or (d.kind == "special" and d.id not in ("log",)):
            site.note_page(d)
    for cat in CATS:
        if cat:
            site.category_page(cat)
    entries = parse_log(docs["log"])
    site.home(entries)
    site.log_page(entries)
    site.search_page()
    site.timeline_page()
    site.graph_page()
    site.data_files()
    site.write()
    n_notes = sum(1 for d in docs.values() if d.kind == "note")
    n_rep = sum(1 for d in docs.values() if d.kind == "report")
    print(f"{out}: {len(site.files)} plików, {n_notes} notatek, {n_rep} raportów, {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
