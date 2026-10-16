#!/usr/bin/env python3
"""Narzędzie bazy wiedzy KERNEL/wiki (tylko stdlib).

  python3 wiki/tools/wiki.py lint [folder]   # błędy -> kod wyjścia 1; folder zawęża raport
  python3 wiki/tools/wiki.py index           # odświeża listy w _hub.md i index.md
  python3 wiki/tools/wiki.py search słowa…   # szuka w tytułach, streszczeniach, tagach
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent
REPO = WIKI.parent

# folder -> (typ, opis do index.md)
FOLDERS: dict[str, tuple[str, str]] = {
    "decyzje": ("decyzja", "Decyzje i korekty użytkownika (wiążące)"),
    "modele": ("model", "Modele i kwanty"),
    "karty": ("karta", "Karty GPU: używane i planowane"),
    "rocm": ("rocm", "Stos AMD: ROCm, HIP, ROCr, PM4, rocprof"),
    "nvidia": ("nvidia", "Stos NVIDIA: CUDA, sm_xx, poprawki zgodności"),
    "kernele": ("kernel", "Nasze kernele: rodziny, zysk, poprawność, wyłącznik"),
    "latki": ("latka", "Łatki llama.cpp i gałęzie"),
    "metody": ("metoda", "Jak pracujemy: playbook, bramki, pomiar"),
    "eksperymenty": ("eksperyment", "Rundy i pomiary z datą"),
    "lekcje": ("lekcja", "Lekcje z błędów"),
    "narzedzia": ("narzedzie", "Nasze skrypty i narzędzia"),
    "chmura": ("chmura", "Wynajem GPU i harness chmurowy"),
    "repo": ("repo", "Repozytoria i projekty: cudze i nasze"),
    "research": ("research", "Streszczenia raportów"),
    "produkt": ("produkt", "Plan produktu i decyzje produktowe"),
    "ludzie-firmy": ("firma", "Firmy, dostawcy, ludzie"),
}
STATUSES = {"aktualne", "do-sprawdzenia", "nieaktualne"}
REQUIRED = ("typ", "tags", "aktualizacja", "zrodlo", "status")
AUTO_START, AUTO_END = "<!-- AUTO:START -->", "<!-- AUTO:END -->"
SKIP_DIRS = {"tools", ".obsidian", ".git", ".trash"}

SECRET_PATTERNS = [
    ("klucz RunPod rpa_", re.compile(r"rpa_[A-Za-z0-9]{16,}")),
    ("64-hex przy key/token", re.compile(r"(?i)(key|token|secret|api)[^\n]{0,20}\b[0-9a-f]{64}\b")),
    ("OpenAI/Anthropic sk-", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("HuggingFace hf_", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("klucz LocalMaxxing bhk_", re.compile(r"\bbhk_[A-Za-z0-9]{8,}")),
    ("klucz prywatny", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Bearer token", re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}")),
    ("e-mail", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("adres IPv4", re.compile(r"(?<![\w.])(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.])")),
]
# Numery wersji wyglądają jak IPv4 (np. cuBLAS 12.8.5.5); takie słowo tuż przed liczbą zwalnia dopasowanie.
VERSION_HINT = re.compile(r"(?i)(wersj\w*|version|cublas|cuda|rocm|driver|sterownik\w*|v)\W{0,3}$")
# Prawdziwe klucze z dysku: porównywane dosłownie, nigdy nie wypisywane.
SECRET_FILES = [Path.home() / ".vast" / "key", Path.home() / ".runpod" / "key"]

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
MDLINK_RE = re.compile(r"\]\(([^)\s]+)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Note:
    def __init__(self, path: Path):
        self.path = path
        self.rel = path.relative_to(WIKI).as_posix()
        self.folder = self.rel.split("/")[0] if "/" in self.rel else ""
        self.name = path.stem
        self.text = path.read_text(encoding="utf-8")
        self.meta, self.body, self.fm_ok = parse_frontmatter(self.text)
        m = re.search(r"^# (.+)$", self.body, re.M)
        self.title = m.group(1).strip() if m else ""
        self.summary = ""
        if m:
            for line in self.body[m.end():].splitlines():
                if line.strip():
                    s = re.fullmatch(r"\*\*(.+)\*\*", line.strip())
                    self.summary = s.group(1).strip() if s else ""
                    break
        self.links = [l.strip() for l in LINK_RE.findall(strip_code(self.text))]

    @property
    def is_hub(self) -> bool:
        return self.name == "_hub" or self.rel == "index.md"

    @property
    def tags(self) -> list[str]:
        raw = self.meta.get("tags", "").strip()
        return [t.strip().strip("'\"") for t in raw.strip("[]").split(",") if t.strip()]


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, bool]:
    if not text.startswith("---\n"):
        return {}, text, False
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text, False
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[end + 5:], True


def load_notes() -> list[Note]:
    notes = []
    for root, dirs, files in os.walk(WIKI):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f.endswith(".md"):
                notes.append(Note(Path(root) / f))
    return notes


def build_resolver(notes: list[Note]):
    by_path = {n.rel[:-3]: n for n in notes}
    by_name: dict[str, list[Note]] = {}
    for n in notes:
        by_name.setdefault(n.name, []).append(n)

    def resolve(target: str) -> Note | None:
        t = target.strip().removesuffix(".md")
        if "/" in t:
            return by_path.get(t)
        hits = by_name.get(t, [])
        return hits[0] if len(hits) == 1 else None

    return resolve, by_name


def lint(only: str | None = None) -> int:
    notes = load_notes()
    resolve, by_name = build_resolver(notes)
    errors: list[str] = []
    warnings: list[str] = []
    secrets = []
    for p in SECRET_FILES:
        try:
            v = p.read_text().strip()
            if len(v) >= 16:
                secrets.append(v)
        except OSError:
            pass

    for name, hits in by_name.items():
        if len(hits) > 1 and name != "_hub":
            errors.append(f"duplikat nazwy '{name}': " + ", ".join(h.rel for h in hits))

    inbound: dict[str, int] = {n.rel: 0 for n in notes}
    for n in notes:
        e = lambda msg: errors.append(f"{n.rel}: {msg}")
        if n.folder and n.folder not in FOLDERS:
            e(f"nieznany folder '{n.folder}'")
        if not n.fm_ok:
            e("brak frontmattera")
        else:
            for k in REQUIRED:
                if not n.meta.get(k):
                    e(f"brak pola '{k}'")
            typ = n.meta.get("typ", "")
            want = "hub" if n.is_hub else FOLDERS.get(n.folder, ("", ""))[0]
            if typ and want and typ != want:
                e(f"typ '{typ}', oczekiwany '{want}'")
            if n.meta.get("status") and n.meta["status"] not in STATUSES:
                e(f"status '{n.meta['status']}' spoza {sorted(STATUSES)}")
            if n.meta.get("aktualizacja") and not DATE_RE.match(n.meta["aktualizacja"]):
                e("aktualizacja nie w formacie RRRR-MM-DD")
            if n.folder and n.folder not in n.tags:
                e(f"tags bez tagu folderu '{n.folder}'")
        if not n.title:
            e("brak tytułu '# …'")
        elif not n.summary:
            e("brak streszczenia (**jedno zdanie** zaraz pod tytułem)")
        if not n.is_hub and not re.search(r"^## Powiązane", n.body, re.M):
            warnings.append(f"{n.rel}: brak sekcji '## Powiązane'")
        for target in n.links:
            hit = resolve(target)
            if hit is None:
                e(f"martwy link [[{target}]]")
            elif hit is not n and not n.is_hub:
                inbound[hit.rel] += 1
        for href in MDLINK_RE.findall(strip_code(n.text)):
            if re.match(r"^[a-z]+:", href) or href.startswith("#"):
                continue
            target = (n.path.parent / href.split("#")[0]).resolve()
            target_dec = Path(re.sub(r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), str(target)))
            if not (target.exists() or target_dec.exists()):
                e(f"martwy link do pliku ({href})")
        for label, rx in SECRET_PATTERNS:
            for m in rx.finditer(n.text):
                if label == "adres IPv4" and VERSION_HINT.search(n.text[max(0, m.start() - 20):m.start()]):
                    continue
                e(f"wzorzec sekretu: {label}")
                break
        for s in secrets:
            if s in n.text:
                e("zawiera prawdziwy klucz z ~/.vast lub ~/.runpod")
        words = len(re.findall(r"\w+", n.body))
        if not n.is_hub and n.rel != "AUDYT.md" and words > 450:  # AUDYT.md: generowana tabela audytu liczb
            warnings.append(f"{n.rel}: {words} słów (cel 50–200)")

    for n in notes:
        if not n.is_hub and inbound[n.rel] == 0:
            warnings.append(f"{n.rel}: sierota (linkuje do niej tylko hub)")
    for f in FOLDERS:
        if not (WIKI / f / "_hub.md").exists():
            errors.append(f"{f}/: brak _hub.md")
    if not (WIKI / "index.md").exists():
        errors.append("brak index.md")
    if only:
        prefix = only.rstrip("/") + "/"
        errors = [x for x in errors if x.startswith(prefix)]
        warnings = [x for x in warnings if x.startswith(prefix)]
    for w in warnings:
        print("WARN ", w)
    for err in errors:
        print("ERROR", err)
    scope = f" (tylko {only})" if only else ""
    print(f"{len(notes)} notatek, {len(errors)} błędów, {len(warnings)} ostrzeżeń{scope}")
    return 1 if errors else 0


def replace_auto(path: Path, content: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if AUTO_START not in text or AUTO_END not in text:
        text = text.rstrip("\n") + f"\n\n{AUTO_START}\n{AUTO_END}\n"
    pre, rest = text.split(AUTO_START, 1)
    _, post = rest.split(AUTO_END, 1)
    new = f"{pre}{AUTO_START}\n{content.rstrip()}\n{AUTO_END}{post}"
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def index() -> int:
    notes = load_notes()
    changed = 0
    counts = {}
    for folder in FOLDERS:
        members = sorted((n for n in notes if n.folder == folder and not n.is_hub),
                         key=lambda n: n.title.lower())
        counts[folder] = len(members)
        hub = WIKI / folder / "_hub.md"
        if not hub.exists():
            continue
        lines = [f"## Notatki ({len(members)})", ""]
        lines += [f"- [[{n.name}|{n.title}]] — {n.summary}" for n in members]
        changed += replace_auto(hub, "\n".join(lines))
    lines = ["## Kategorie", ""]
    for folder, (_, desc) in FOLDERS.items():
        lines.append(f"- [[{folder}/_hub|{folder}]] — {desc} ({counts.get(folder, 0)})")
    recent = sorted((n for n in notes if not n.is_hub),
                    key=lambda n: (n.meta.get("aktualizacja", ""), n.rel), reverse=True)[:15]
    lines += ["", "## Ostatnio aktualizowane", ""]
    lines += [f"- {n.meta.get('aktualizacja', '?')} [[{n.name}|{n.title}]]" for n in recent]
    total = sum(counts.values())
    lines += ["", f"Razem {total} notatek. Wygenerowano {dt.date.today().isoformat()} przez `tools/wiki.py index`."]
    changed += replace_auto(WIKI / "index.md", "\n".join(lines))
    print(f"zaktualizowano {changed} plików")
    return 0


def search(words: list[str]) -> int:
    if not words:
        print("użycie: wiki.py search słowa…")
        return 2
    qs = [w.lower() for w in words]
    scored = []
    for n in load_notes():
        hay_hi = f"{n.name} {n.title} {' '.join(n.tags)}".lower()
        hay_lo = n.summary.lower()
        body = n.body.lower()
        score = sum(3 * hay_hi.count(q) + 2 * hay_lo.count(q) + min(body.count(q), 3) for q in qs)
        if score:
            scored.append((score, n))
    for score, n in sorted(scored, key=lambda x: -x[0])[:15]:
        print(f"{score:3d}  {n.rel}  — {n.summary or n.title}")
    return 0 if scored else 1


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"lint", "index", "search"}:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "lint":
        return lint(sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == "index":
        return index()
    return search(sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
