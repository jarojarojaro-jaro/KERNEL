"""Small Markdown -> HTML renderer for the wiki (stdlib only).

Covers what the notes and reports use: ATX headings, paragraphs, nested lists (task boxes too),
tables (alignment, `|` inside code / wikilinks / `\\|`), fenced code, block quotes, rules, HTML
comments (dropped), bold / italic / strike, code spans, links, bare URLs and [[wikilinks]].
All text is escaped; raw HTML in the source is shown as text.
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
HR = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])(\s+|$)(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
QUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")
WIKILINK = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]*))?\]\]")
MDLINK = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])+)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
URL = re.compile(r"\bhttps?://[^\s<>()\[\]`]+[^\s<>()\[\]`.,;:!?'\"”»]")
CODE = re.compile(r"(`+)(.+?)\1", re.S)
BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|__(?=\S)(.+?)(?<=\S)__")
ITALIC = re.compile(r"(?<![\w*\\])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])")
STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
COMMENT = re.compile(r"<!--.*?-->", re.S)
PH = re.compile(r"\x00(\d+)\x00")


@dataclass
class Ctx:
    """Link hooks supplied by the site builder.

    wikilink(target) -> (href, label, note_id) or None for a dead link.
    href(url) -> rewritten href (report / note page), None to render the link text as a path,
                 or the url itself for external links.
    code(text) -> href for a code span that names a known file (report), else None.
    """

    wikilink: Callable[[str], tuple[str, str, str] | None]
    href: Callable[[str], str | None]
    code: Callable[[str], str | None] = lambda s: None
    headings: list[tuple[int, str, str]] = field(default_factory=list)
    _slugs: dict[str, int] = field(default_factory=dict)

    def slug(self, text: str) -> str:
        s = slugify(text)
        n = self._slugs.get(s, 0)
        self._slugs[s] = n + 1
        return f"{s}-{n}" if n else s


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.lower().replace("ł", "l"))
    s = re.sub(r"[^\w\s-]", "", "".join(c for c in s if not unicodedata.combining(c)))
    return re.sub(r"[\s_]+", "-", s).strip("-")[:60] or "sekcja"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- inline


def inline(text: str, ctx: Ctx, links: bool = True, store: list[str] | None = None) -> str:
    nested = store is not None
    store = store if nested else []

    def keep(fragment: str) -> str:
        store.append(fragment)
        return f"\x00{len(store) - 1}\x00"

    def code(m: re.Match) -> str:
        body = m.group(2)
        if len(m.group(1)) > 1 or body.startswith(" "):
            body = body.strip()
        target = ctx.code(body) if links else None
        tag = f"<code>{esc(body)}</code>"
        return keep(f'<a class="path" href="{esc(target)}">{tag}</a>' if target else tag)

    def wiki(m: re.Match) -> str:
        target, anchor, label = m.group(1).strip(), m.group(2) or "", (m.group(3) or "").strip()
        hit = ctx.wikilink(target)
        if not hit:
            return keep(f'<span class="wl dead" title="brak notatki">{esc(label or target)}</span>')
        href, title, nid = hit
        text = label or title
        if anchor:
            href += "#" + slugify(anchor[1:])
        if not links:
            return keep(f'<span class="wl">{esc(text)}</span>')
        return keep(f'<a class="wl" href="{esc(href)}" data-n="{esc(nid)}">{esc(text)}</a>')

    def mdlink(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        inner = inline(label, ctx, links=False, store=store)
        if not links:
            return keep(inner)
        target = ctx.href(url)
        if target is None:
            return keep(f'<span class="path" title="{esc(url)}">{inner}</span>')
        ext = target.startswith(("http://", "https://"))
        attrs = ' target="_blank" rel="noopener" class="ext"' if ext else ""
        return keep(f'<a href="{esc(target)}"{attrs}>{inner}</a>')

    def bare(m: re.Match) -> str:
        url = m.group(0)
        if not links:
            return keep(esc(url))
        short = re.sub(r"^https?://(www\.)?", "", url)
        short = short if len(short) <= 60 else short[:57] + "…"
        return keep(f'<a href="{esc(url)}" target="_blank" rel="noopener" class="ext">{esc(short)}</a>')

    text = CODE.sub(code, text)
    text = WIKILINK.sub(wiki, text)
    text = MDLINK.sub(mdlink, text)
    text = URL.sub(bare, text)
    text = esc(text).replace("\\|", "|").replace("\\*", "*").replace("\\_", "_")
    text = BOLD.sub(lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    text = STRIKE.sub(r"<del>\1</del>", text)
    text = re.sub(r" {2,}\n|\\\n", "<br>", text)
    if nested:
        return text
    for _ in range(4):  # placeholders nest (link label with code)
        if "\x00" not in text:
            break
        text = PH.sub(lambda m: store[int(m.group(1))], text)
    return text


def plain(text: str) -> str:
    """Markdown inline -> plain text (for summaries, search, titles)."""
    text = WIKILINK.sub(lambda m: (m.group(3) or m.group(1)).strip(), text)
    text = MDLINK.sub(r"\1", text)
    text = re.sub(r"`+([^`]*)`+", r"\1", text)
    text = re.sub(r"\*\*|__|~~", "", text)
    text = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"\1", text)
    return text.replace("\\|", "|")


# ---------------------------------------------------------------- blocks


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, i, depth_code, depth_wl = [], [], 0, 0, 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("\\|")
            i += 2
            continue
        if c == "`":
            depth_code ^= 1
        elif s.startswith("[[", i) and not depth_code:
            depth_wl += 1
        elif s.startswith("]]", i) and depth_wl and not depth_code:
            depth_wl -= 1
        if c == "|" and not depth_code and not depth_wl:
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    cells.append("".join(cur).strip())
    return cells


NUMERIC = re.compile(r"^[~≈<>+\-−]?\s*\**[\d.,  ]+\**\s*(%|×|x|t/s|ms|s|GB|GiB|MB|W|\$)?\**$")


def table(lines: list[str], ctx: Ctx) -> str:
    head = split_row(lines[0])
    aligns = []
    for c in split_row(lines[1]):
        c = c.strip()
        aligns.append("center" if c.startswith(":") and c.endswith(":") else "right" if c.endswith(":") else "")
    out = ['<div class="table-wrap"><table><thead><tr>']
    for i, c in enumerate(head):
        a = aligns[i] if i < len(aligns) else ""
        out.append(f'<th{f" style=\"text-align:{a}\"" if a else ""}>{inline(c, ctx)}</th>')
    out.append("</tr></thead><tbody>")
    for ln in lines[2:]:
        cells = split_row(ln)
        cells += [""] * (len(head) - len(cells))
        out.append("<tr>")
        for i, c in enumerate(cells[: max(len(head), len(cells))]):
            a = aligns[i] if i < len(aligns) else ""
            cls = ' class="num"' if NUMERIC.match(c) else ""
            out.append(f'<td{cls}{f" style=\"text-align:{a}\"" if a else ""}>{inline(c, ctx)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def starts_block(line: str) -> bool:
    return bool(
        FENCE.match(line) or HEADING.match(line) or HR.match(line) or LIST_ITEM.match(line) or QUOTE.match(line)
    )


def blocks(lines: list[str], ctx: Ctx) -> str:
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].replace("\t", "    ")
        if not line.strip():
            i += 1
            continue
        if m := FENCE.match(line):
            fence, lang, ind = m.group(2), m.group(3), len(m.group(1))
            body = []
            i += 1
            while i < n and not lines[i].strip().startswith(fence[0] * len(fence)):
                body.append(lines[i][ind:] if lines[i][:ind].strip() == "" else lines[i])
                i += 1
            i += 1
            cls = f' class="lang-{esc(lang)}"' if lang else ""
            label = f'<span class="code-lang">{esc(lang)}</span>' if lang else ""
            out.append(f'<div class="code">{label}<pre><code{cls}>{esc(chr(10).join(body))}</code></pre></div>')
            continue
        if m := HEADING.match(line):
            level, text = len(m.group(1)), m.group(2)
            sid = ctx.slug(plain(text))
            ctx.headings.append((level, sid, plain(text)))
            out.append(f'<h{level} id="{sid}"><a class="anchor" href="#{sid}" aria-hidden="true">#</a>{inline(text, ctx)}</h{level}>')
            i += 1
            continue
        if HR.match(line):
            out.append("<hr>")
            i += 1
            continue
        if "|" in line and i + 1 < n and TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1]:
            j = i + 2
            while j < n and lines[j].strip() and "|" in lines[j]:
                j += 1
            out.append(table(lines[i:j], ctx))
            i = j
            continue
        if QUOTE.match(line):
            body = []
            while i < n and (q := QUOTE.match(lines[i])):
                body.append(q.group(1))
                i += 1
            out.append(f"<blockquote>{blocks(body, ctx)}</blockquote>")
            continue
        if LIST_ITEM.match(line):
            html_, i = list_block(lines, i, ctx)
            out.append(html_)
            continue
        para = [line.strip()]
        i += 1
        while i < n and lines[i].strip() and not starts_block(lines[i]) and not (
            "|" in lines[i] and i + 1 < n and TABLE_SEP.match(lines[i + 1])
        ):
            para.append(lines[i].strip() if not lines[i].endswith("  ") else lines[i].lstrip())
            i += 1
        out.append(f"<p>{inline(chr(10).join(para), ctx)}</p>")
    return "\n".join(out)


def list_block(lines: list[str], i: int, ctx: Ctx) -> tuple[str, int]:
    first = LIST_ITEM.match(lines[i])
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start = int(first.group(2)[:-1]) if ordered else 1
    items: list[list[str]] = []
    loose = False
    n = len(lines)
    while i < n:
        m = LIST_ITEM.match(lines[i])
        if not m or len(m.group(1)) != base or m.group(2)[0].isdigit() != ordered:
            break
        content_ind = len(m.group(1)) + len(m.group(2)) + max(1, len(m.group(3)))
        body = [m.group(4)]
        i += 1
        while i < n:
            ln = lines[i].replace("\t", "    ")
            if not ln.strip():
                # blank: item continues only if the next non-blank line is indented under the item
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and indent_of(lines[j]) > base and not (
                    LIST_ITEM.match(lines[j]) and indent_of(lines[j]) == base
                ):
                    body.extend([""] * (j - i))
                    loose = loose or not LIST_ITEM.match(lines[j])
                    i = j
                    continue
                break
            ind = indent_of(ln)
            if ind > base:
                body.append(ln[min(ind, content_ind):])
                i += 1
                continue
            if starts_block(ln) or ("|" in ln and i + 1 < n and TABLE_SEP.match(lines[i + 1])):
                break
            body.append(ln.strip())  # lazy continuation
            i += 1
        items.append(body)
    tag = "ol" if ordered else "ul"
    attrs = f' start="{start}"' if ordered and start != 1 else ""
    out = [f"<{tag}{attrs}>"]
    for body in items:
        task = ""
        if not ordered and (tm := re.match(r"^\[([ xX])\]\s+", body[0])):
            task = f'<span class="task{" done" if tm.group(1) != " " else ""}" aria-hidden="true"></span>'
            body[0] = body[0][tm.end():]
        inner = blocks(body, ctx)
        if not loose and inner.startswith("<p>"):
            end = inner.find("</p>")
            inner = inner[3:end] + inner[end + 4:]
        cls = ' class="task-item"' if task else ""
        out.append(f"<li{cls}>{task}{inner}</li>")
    out.append(f"</{tag}>")
    return "".join(out), i


def render(md: str, ctx: Ctx) -> str:
    md = COMMENT.sub("", md)
    return blocks(md.split("\n"), ctx)
