#!/usr/bin/env python3
"""compwatch: codzienny zwiad (LocalMaxxing, GitHub, Hugging Face, otwarte rankingi, arXiv, blogi RSS/Atom).

Porównuje bieżący stan ze stanem z ostatniego raportu (~/.cache/compwatch/state.json)
i z wersjami zapisanymi w wiki/ZRODLA.md. Przy delcie pisze
product/research/watch/YYYY-MM-DD.md, dopisuje linię do INDEX.md, robi commit i push (bez `--no-git`).
Konfiguracja: config.json obok. Opis: README.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import fcntl
import glob
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
KERNEL = HERE.parents[1]
CACHE = Path(os.environ.get("COMPWATCH_CACHE", "~/.cache/compwatch")).expanduser()
OUT_DIR = Path(os.environ.get("COMPWATCH_OUT") or KERNEL / "product/research/watch").expanduser()
UA = "compwatch/1.1 (+https://github.com/jarojarojaro-jaro/KERNEL/tree/main/tools/compwatch)"
TIER_W = {"core": 1.0, "catalog": 0.6, "candidate": 0.4}

TODAY = dt.date.today()
NOW = dt.datetime.now(dt.timezone.utc)
# Błędy sieci i formatu jednego źródła: URLError, HTTPError, TimeoutError, ConnectionResetError (⊂ OSError),
# RemoteDisconnected/IncompleteRead (⊂ HTTPException), JSONDecodeError (⊂ ValueError), zły XML (ParseError).
# Wcześniej łapane były tylko URLError/TimeoutError/JSONDecodeError, więc zerwane połączenie kończyło cały przebieg.
NET_ERR = (OSError, http.client.HTTPException, ValueError, ET.ParseError)


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def one_line(s: str | None, n: int = 200) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip().replace("|", "/")
    return s if len(s) <= n else s[: n - 1] + "…"


def http_get(url: str, headers: dict | None = None, timeout: int = 60) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), dict(r.headers)


def http_json(url: str, headers: dict | None = None, timeout: int = 60):
    raw, h = http_get(url, {"Accept": "application/json", **(headers or {})}, timeout)
    return json.loads(raw), h


def kw_hits(text: str, keywords: list[str]) -> list[str]:
    t = (text or "").lower()
    return [k for k in keywords if k in t]


def kw_score(title: str, body: str, patterns: list) -> tuple[float, list[str], float]:
    """Wzorce `[regex, waga]` (config.json → research_keywords) → (suma wag, trafienia, najwyższa waga trafienia).
    Trafienie w tytule liczy się ×1.5."""
    score, hits, strongest = 0.0, [], 0.0
    for pat, w in patterns:
        m = re.search(pat, title or "", re.I)
        in_title = m is not None
        m = m or re.search(pat, body or "", re.I)
        if not m:
            continue
        score += w * (1.5 if in_title else 1.0)
        hits.append(m.group(0).lower())
        strongest = max(strongest, w)
    return score, hits, strongest


class Item:
    """Jedna pozycja delty; `score` ustala kolejność w „Do sprawdzenia”."""

    def __init__(self, score: float, section: str, title: str, caveat: str | None = None, next_step: str | None = None):
        self.score, self.section, self.title, self.caveat, self.next_step = score, section, title, caveat, next_step


# ---------------------------------------------------------------- LocalMaxxing

def card_of(row_hw: dict, cards: list[dict]) -> dict | None:
    text = " ".join(str(row_hw.get(k) or "") for k in ("gpuName", "chipVendor", "chipFamily", "chipVariant"))
    for c in cards:
        if re.search(c["re"], text, re.I):
            return c
    return None


def model_of(names: list[str], models: list[dict]) -> dict | None:
    for m in models:
        if any(re.search(m["re"], n or "", re.I) for n in names):
            return m
    return None


def engine_key(eng: dict) -> str:
    name = (eng.get("engineName") or "").strip()
    ver = (eng.get("engineVersion") or "").strip()
    repo = (eng.get("engineRepository") or "").strip()
    slug = re.sub(r"^https?://(www\.)?github\.com/", "", repo).strip("/").removesuffix(".git")
    if name.lower() in ("", "custom", "other"):
        m = re.match(r"[A-Za-z][A-Za-z0-9_+-]*", ver)
        name = slug.split("/")[-1] if slug else (f"custom:{m.group(0)}" if m else "custom")
    if slug and slug.lower() not in ("ggml-org/llama.cpp", "ggerganov/llama.cpp", "vllm-project/vllm", "sgl-project/sglang"):
        return f"{name.lower()} ({slug})"
    return name.lower()


def compact_run(r: dict, cfg: dict) -> dict:
    eng, hw, mdl, ef = r.get("engine") or {}, r.get("hardware") or {}, r.get("model") or {}, r.get("engineFlags") or {}
    base = (mdl.get("baseModel") or {}).get("hfId") or mdl.get("hfId")
    spec = ef.get("specMethod") or ("MTP" if ef.get("mtpEnabled") else ("spec" if ef.get("specDecoding") else ""))
    dc = r.get("decodeCeiling") or {}
    return {
        "id": r.get("id"), "date": (r.get("createdAt") or "")[:10], "tok": r.get("tokSOut"),
        "model": mdl.get("hfId"), "base": base,
        "gpu": hw.get("gpuName") or " ".join(x for x in (hw.get("chipFamily"), hw.get("chipVariant")) if x) or hw.get("hwClass"),
        "gpus": hw.get("gpuCount"), "hw": hw,
        "engine": engine_key(eng), "engine_raw": one_line(f"{eng.get('engineName') or ''} {eng.get('engineVersion') or ''}", 60),
        "repo": eng.get("engineRepository"), "quant": eng.get("quantization"), "backend": eng.get("backend"),
        "verified": bool(r.get("verifiedRun")), "pt": r.get("promptTokens"), "ot": r.get("outputTokens"),
        "prompt": cfg["localmaxxing"]["prompts"].get(r.get("promptSha256") or "", "własny prompt"),
        "batch": r.get("batchSize"), "spec": spec, "spec_n": ef.get("specNumTokens"), "mal": ef.get("specMeanAcceptedLength"),
        "util": dc.get("measuredUtilization"), "user": (r.get("user") or {}).get("username"),
        "notes": one_line(r.get("notes"), 160),
    }


def run_desc(c: dict) -> str:
    spec = f"{c['spec']}" + (f" n={c['spec_n']}" if c.get("spec_n") else "") + (f" mal {c['mal']:.2f}" if isinstance(c.get("mal"), (int, float)) else "")
    v = "verified" if c["verified"] else "NIEzweryfikowany"
    return (f"{c['tok']:.1f} t/s · {c['engine_raw'] or c['engine']} · {c['quant'] or '?'} · {spec or 'bez spekulacji'} · "
            f"{c['user'] or '?'} · {c['date']} · {v} · run `{c['id']}`")


def caveat_lmx(c: dict, ours: dict | None) -> str:
    mal = f", mal {c['mal']:.2f}" if isinstance(c.get("mal"), (int, float)) else ""
    canon = "; kanon = T=0, myślenie wł." if c["prompt"] != "własny prompt" else "; T nieznane"
    them = (f"oni: {c['prompt']} ({c['pt']} tok. promptu, {c['ot']} wyj.{canon}), "
            f"{c['quant'] or '?'}, {c['spec'] or 'bez spekulacji'}{mal}, {c['gpus'] or 1}×GPU, batch {c['batch']}, licznik klienta HTTP")
    if not c["verified"]:
        them += ", NIEzweryfikowany"
    us = f"my: {ours['metric']} ({ours['tok']} t/s, `{ours['src']}`)" if ours else "nasz pomiar na tej karcie: brak"
    return f"Jabłka do jabłek: {them}; {us}."


def lmx_fetch(cfg: dict, state: dict, report: dict) -> list[dict]:
    lm = cfg["localmaxxing"]
    day = TODAY.isoformat()
    used = state.setdefault("lmx", {}).setdefault("requests", {})
    for d in [d for d in used if d < (TODAY - dt.timedelta(days=30)).isoformat()]:
        del used[d]
    raw_dir = CACHE / "lmx" / day
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict] = {}
    for q in lm["queries"]:
        got, total = [], 0
        for page in range(q.get("max_pages", 1)):
            params = dict(q["params"])
            if page:
                if total <= len(got):
                    break
                params["offset"] = str(page * int(params.get("limit", 50)))
            f = raw_dir / (f"{q['name']}.json" if not page else f"{q['name']}.p{page + 1}.json")
            if f.exists():
                data = json.loads(f.read_text())
            else:
                if used.get(day, 0) >= lm["daily_max"]:
                    report["notes"].append(f"LocalMaxxing: limit {lm['daily_max']} zapytań/dzień wyczerpany, pominięto `{q['name']}` (strona {page + 1}).")
                    break
                url = lm["base"] + "?" + urllib.parse.urlencode(params)
                if used.get(day, 0):
                    time.sleep(lm["spacing_s"])
                used[day] = used.get(day, 0) + 1
                report["lmx_requests"] += 1
                try:
                    data, _ = http_json(url)
                except NET_ERR as e:
                    report["notes"].append(f"LocalMaxxing `{q['name']}`: błąd {one_line(str(e), 120)}.")
                    break
                f.write_text(json.dumps(data))
            got += data.get("rows") or []
            total = data.get("total") or 0
        if total > len(got):
            report["notes"].append(f"LocalMaxxing `{q['name']}`: pobrano {len(got)} z {total} wierszy (ranking malejąco po t/s, więc brakuje najwolniejszych).")
        for r in got:
            rows[r["id"]] = r
    report["lmx_rows"] = len(rows)
    return list(rows.values())


def lmx_analyze(cfg: dict, state: dict, rows: list[dict], items: list[Item], report: dict, first: bool) -> None:
    lst = state.setdefault("lmx", {})
    seen: dict = lst.setdefault("runs", {})
    engines: dict = lst.setdefault("engines", {})
    cards = {c["key"]: c for c in cfg["cards"]}
    ours = {(o["card"], o["model"]): o for o in cfg["nasze"]}

    fresh = []
    for r in rows:
        c = compact_run(r, cfg)
        card = card_of(c["hw"], cfg["cards"])
        model = model_of([c["base"], c["model"]], cfg["models"])
        if not card and not model:
            continue
        c["card"] = card["key"] if card and (c["gpus"] in (None, 1)) else None
        c["mkey"] = model["key"] if model else (c["base"] or "?").split("/")[-1]
        c["tier"] = model["tier"] if model else "other"
        c.pop("hw")
        if c["id"] not in seen:
            fresh.append(c)

    # Najlepszy dotąd per (karta, model, V|A) – liczone z historii (stan) przed dodaniem nowych.
    def best(pool, card, mkey, verified_only):
        cand = [x for x in pool if x.get("card") == card and x.get("mkey") == mkey and (x["verified"] or not verified_only)
                and isinstance(x.get("tok"), (int, float))]
        return max(cand, key=lambda x: x["tok"], default=None)

    old_pool = list(seen.values())
    report["lmx_new"] = len(fresh)
    report["lmx_tops"] = []

    beat_seen: set = set()
    for c in sorted(fresh, key=lambda x: -(x.get("tok") or 0)):
        if not isinstance(c.get("tok"), (int, float)):
            continue
        card = cards.get(c["card"]) if c.get("card") else None
        tw = TIER_W.get(c["tier"], 0.3)
        o = ours.get((c["card"], c["mkey"]))
        vmul = 1.0 if c["verified"] else 0.6
        # 1) bije nasz pomiar; niezweryfikowane tylko z sensowną długością wyjścia.
        #    Jedna pozycja na (karta, model, silnik) – kolejne runy tego samego silnika z wagą ×0.3.
        if card and o and c["tok"] > o["tok"] and (c["verified"] or (c["ot"] or 0) >= 128):
            pct = 100.0 * (c["tok"] / o["tok"] - 1)
            dup = (c["card"], c["mkey"], c["engine"]) in beat_seen
            beat_seen.add((c["card"], c["mkey"], c["engine"]))
            items.append(Item((60 + min(60, pct)) * card["w"] * tw * vmul * (0.3 if dup else 1.0), "lmx",
                              f"**{card['label']} / {c['mkey']}: {c['tok']:.1f} t/s > nasze {o['tok']} (+{pct:.0f}%)** — {run_desc(c)}",
                              caveat_lmx(c, o),
                              "rozłożyć na kwant / szerokość drafu / mal / pasmo i sprawdzić tę dźwignię u nas (≤10 min GPU)"))
        # 2) nowy top per karta
        if card and (c["verified"] or card.get("unverified")) and not first:
            prev = best(old_pool, c["card"], c["mkey"], c["verified"])
            if prev is None or c["tok"] > prev["tok"]:
                firstv = prev is None and c["verified"]
                sc = (45 + (15 if firstv else 0)) * card["w"] * tw * vmul
                was = f"poprzednio {prev['tok']:.1f} ({prev['engine']})" if prev else ("pierwszy verified run" if c["verified"] else "pierwszy run")
                items.append(Item(sc, "lmx", f"Nowy top {card['label']} / {c['mkey']} ({'verified' if c['verified'] else 'wszystkie'}): {run_desc(c)}; {was}",
                                  caveat_lmx(c, o), "sprawdzić notes / repo silnika; czy da się odtworzyć na naszej karcie"))
        old_pool.append(c)

    # 3) nowe silniki (na naszych modelach albo naszych kartach)
    known = set(engines.get("all", []))
    new_eng: dict[str, dict] = {}
    for c in fresh:
        if c["engine"] not in known and (c["engine"] not in new_eng or (c.get("tok") or 0) > (new_eng[c["engine"]].get("tok") or 0)):
            new_eng[c["engine"]] = c
    if not first:
        for e, c in new_eng.items():
            hot = c["tier"] == "core" or c.get("card") in ("XTX", "R9700")
            where = f"{cards[c['card']]['label'] if c.get('card') else c['gpu']} / {c['mkey']}"
            items.append(Item(50 if hot else 25, "lmx", f"Nowy silnik w bazie: **{e}** ({where}) — {run_desc(c)}"
                              + (f"; repo {c['repo']}" if c.get("repo") else ""),
                              caveat_lmx(c, ours.get((c.get("card"), c["mkey"]))),
                              "przeczytać repo/notes; czy działa na gfx1100 / sm_86; dopisać do config.json → github.repos"))
    engines["all"] = sorted(known | set(new_eng))

    for c in fresh:
        seen[c["id"]] = c

    # Stan (tabela top per karta) – w raporcie bazowym i w każdym raporcie z deltą LocalMaxxing.
    pool = list(seen.values())
    for card in cfg["cards"]:
        for m in [m for m in cfg["models"] if m["tier"] == "core"] + [{"key": k} for k in sorted({x["mkey"] for x in pool if x.get("card") == card["key"] and x["tier"] == "catalog"})]:
            bv = best(pool, card["key"], m["key"], True)
            ba = best(pool, card["key"], m["key"], False) if card.get("unverified") else None
            if bv or ba:
                o = ours.get((card["key"], m["key"]))
                report["lmx_tops"].append((card, m["key"], bv, ba, o))
                # Przebieg bazowy: najlepszy verified run na karcie bez naszego pomiaru też trafia do „Do sprawdzenia”.
                if first and bv and not o and m.get("tier") == "core":
                    items.append(Item(70 * card["w"], "lmx", f"**{card['label']} / {m['key']}: top verified {bv['tok']:.1f} t/s** (nasz pomiar: brak) — {run_desc(bv)}",
                                      caveat_lmx(bv, None), "zmierzyć tę kartę u nas przy najbliższej kampanii chmurowej albo rozłożyć ich dźwignię"))
    report["lmx_engines_first"] = sorted(new_eng) if first else []


# ---------------------------------------------------------------- GitHub

def gh_bin() -> str | None:
    p = shutil.which("gh") or str(Path("~/.local/bin/gh").expanduser())
    if not Path(p).exists():
        return None
    try:
        ok = subprocess.run([p, "auth", "status"], capture_output=True, text=True, timeout=60).returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
    return p if ok else None


def gh_graphql(gh: str, query: str) -> dict:
    try:
        p = subprocess.run([gh, "api", "graphql", "-f", f"query={query}"], capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise RuntimeError("gh api graphql: brak odpowiedzi w 180 s") from None
    try:
        out = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        out = {}
    if p.returncode != 0 and not out.get("data"):
        raise RuntimeError(one_line(p.stderr or p.stdout, 300))
    return out.get("data") or {}


def repo_list(cfg: dict, report: dict) -> list[dict]:
    g = cfg["github"]
    repos = {r["slug"].lower(): dict(r) for r in g["repos"]}
    text = (KERNEL / g["registry"]).read_text()
    for m in re.finditer(r"github(?:\.com)?[/ ]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", text):
        slug = m.group(1).rstrip(".,;:)")
        if slug.lower() not in repos:
            repos[slug.lower()] = {"slug": slug, "tier": "C", "auto": True}
    return list(repos.values())


def baseline_candidates(cfg: dict, repos: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """sha z kolumny wersji w ZRODLA.md i w sekcjach „Do bazy wiedzy” raportów → {slug: [(sha, plik:linia)]}."""
    g = cfg["github"]
    sources: list[tuple[str, list[tuple[int, str]]]] = []
    reg = KERNEL / g["registry"]
    sources.append((g["registry"], list(enumerate(reg.read_text().splitlines(), 1))))
    for f in sorted(glob.glob(str(KERNEL / g["baseline_sections"]))):
        lines, keep, inside = Path(f).read_text(errors="replace").splitlines(), [], False
        for i, ln in enumerate(lines, 1):
            if ln.startswith("## "):
                inside = ln.lower().startswith("## do bazy wiedzy")
            elif inside:
                keep.append((i, ln))
        if keep:
            sources.append((str(Path(f).relative_to(KERNEL)), keep))
    out: dict[str, list] = {r["slug"]: [] for r in repos}
    for fname, lines in sources:
        for i, ln in lines:
            if not ln.startswith("|"):
                continue
            cells = ln.split("|")
            if len(cells) < 4:
                continue
            low = cells[1].lower()
            for r in repos:
                if r["slug"].lower() in low:
                    for sha in re.findall(r"`([0-9a-f]{7,40})`", cells[2]):
                        out[r["slug"]].append((sha, f"{fname}:{i}"))
    return out


REPO_Q = """%s: repository(owner: %s, name: %s) {
  nameWithOwner url isArchived
  defaultBranchRef { name target { ... on Commit { oid committedDate messageHeadline } } }
  releases(first: 8, orderBy: {field: CREATED_AT, direction: DESC}) { nodes { tagName name publishedAt isDraft isPrerelease url description } }
  refs(refPrefix: "refs/tags/", first: 5, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) { nodes { name } }
  %s
}"""
HIST_Q = """%s: repository(owner: %s, name: %s) { defaultBranchRef { target { ... on Commit {
  base: history(since: %s) { totalCount }
  news: history(first: 40, since: %s) { totalCount nodes { oid committedDate messageHeadline } }
} } } }"""


def github_scan(cfg: dict, state: dict, items: list[Item], report: dict, first: bool) -> None:
    g = cfg["github"]
    kws = g["keywords"]
    gs = state.setdefault("gh", {})
    rstate: dict = gs.setdefault("repos", {})
    sha_dates: dict = gs.setdefault("sha_dates", {})
    repos = repo_list(cfg, report)
    gh = gh_bin()
    if not gh:
        report["notes"].append("GitHub: `gh` niezalogowany – pominięto (tryb bez autoryzacji: 60 zapytań/h nie wystarcza na pełny przegląd; zaloguj `gh auth login`).")
        report["gh"] = []
        return
    cands = baseline_candidates(cfg, repos)
    jq = json.dumps

    # 1) migawka repo + rozwiązanie sha bazowych (paczki po 6 repo)
    snap: dict[str, dict] = {}
    for i in range(0, len(repos), 6):
        parts = []
        for j, r in enumerate(repos[i:i + 6]):
            owner, name = r["slug"].split("/", 1)
            objs = " ".join(f'b{k}: object(expression: {jq(sha)}) {{ ... on Commit {{ oid committedDate }} }}'
                            for k, (sha, _) in enumerate(cands[r["slug"]]) if f"{r['slug']}@{sha}" not in sha_dates)
            parts.append(REPO_Q % (f"r{i + j}", jq(owner), jq(name), objs))
        try:
            data = gh_graphql(gh, "query {\n" + "\n".join(parts) + "\n}")
        except RuntimeError as e:
            report["notes"].append(f"GitHub GraphQL: {e}")
            data = {}
        report["gh_calls"] += 1
        for j, r in enumerate(repos[i:i + 6]):
            d = data.get(f"r{i + j}")
            if not d:
                continue
            snap[r["slug"]] = d
            for k, (sha, _) in enumerate(cands[r["slug"]]):
                key = f"{r['slug']}@{sha}"
                if key not in sha_dates:
                    o = d.get(f"b{k}")
                    sha_dates[key] = o["committedDate"] if o else None

    # 2) baza (ZRODLA/raport) = najnowszy rozwiązywalny sha
    for r in repos:
        best = None
        for sha, where in cands[r["slug"]]:
            dte = sha_dates.get(f"{r['slug']}@{sha}")
            if dte and (best is None or dte > best[1]):
                best = (sha, dte, where)
        r["base"] = best

    # 3) historia od bazy i od ostatniego raportu (tylko gdzie HEAD się zmienił)
    todo = []
    for r in repos:
        d = snap.get(r["slug"])
        head = ((d or {}).get("defaultBranchRef") or {}).get("target") or {}
        r["head"] = head
        prev = rstate.get(r["slug"], {})
        if not head or head.get("oid") == prev.get("head"):
            continue
        window = (NOW - dt.timedelta(days=cfg["first_run_days"])).isoformat()
        since_new = prev.get("head_date") or (r["base"][1] if r["base"] else window)
        since_base = r["base"][1] if r["base"] else since_new
        bump = lambda s: (dt.datetime.fromisoformat(s.replace("Z", "+00:00")) + dt.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        todo.append((r, bump(since_base), bump(since_new)))
    for i in range(0, len(todo), 8):
        parts = []
        for j, (r, sb, sn) in enumerate(todo[i:i + 8]):
            owner, name = r["slug"].split("/", 1)
            parts.append(HIST_Q % (f"h{j}", jq(owner), jq(name), jq(sb), jq(sn)))
        try:
            data = gh_graphql(gh, "query {\n" + "\n".join(parts) + "\n}")
        except RuntimeError as e:
            report["notes"].append(f"GitHub GraphQL (historia): {e}")
            data = {}
        report["gh_calls"] += 1
        for j, (r, _, _) in enumerate(todo[i:i + 8]):
            t = (((data.get(f"h{j}") or {}).get("defaultBranchRef") or {}).get("target") or {})
            r["since_base"] = (t.get("base") or {}).get("totalCount")
            r["news"] = t.get("news") or {"totalCount": 0, "nodes": []}

    # 4) delty
    rows = []
    for r in repos:
        slug, d = r["slug"], snap.get(r["slug"])
        prev = rstate.get(slug, {})
        if d is None:
            if not r.get("auto"):
                report["notes"].append(f"GitHub `{slug}`: repo niedostępne (usunięte, prywatne albo zmiana nazwy).")
            continue
        tier = g["tiers"].get(r.get("tier", "C"), 15)
        head = r["head"]
        rels = [x for x in ((d.get("releases") or {}).get("nodes") or []) if not x.get("isDraft")]
        seen_tags = set(prev.get("releases", []))
        if r.get("release_ignore"):
            rels = [x for x in rels if not re.search(r["release_ignore"], x["tagName"])]
        if r.get("ignore_releases"):
            new_rels = []
        elif prev:
            new_rels = [x for x in rels if x["tagName"] not in seen_tags]
        else:
            since = r["base"][1] if r["base"] else (NOW - dt.timedelta(days=cfg["first_run_days"])).isoformat()
            new_rels = [x for x in rels if (x.get("publishedAt") or "") > since]
        news = r.get("news") or {"totalCount": 0, "nodes": []}
        n_new = news.get("totalCount") or 0
        hl = [n for n in news.get("nodes", []) if kw_hits(n["messageHeadline"], kws)]
        label = r.get("name") or slug
        if n_new or new_rels:
            rows.append((r, d, new_rels, n_new, hl))
        if new_rels:
            x = new_rels[0]
            body = " ".join((y.get("description") or "") + " " + (y.get("name") or "") for y in new_rels)
            hits = kw_hits(body, kws)
            perf = re.search(r"\d+(\.\d+)?\s*(t/s|tok/s|tokens/s|%|×|x\b)", body)
            more = f" (+{len(new_rels) - 1} wcześniejszych: {', '.join(y['tagName'] for y in new_rels[1:4])}{'…' if len(new_rels) > 4 else ''})" if len(new_rels) > 1 else ""
            items.append(Item(tier + min(15, 2 * len(hits)) - (5 if all(y.get("isPrerelease") for y in new_rels) else 0), "gh",
                              f"**{label}** wydanie [{x['tagName']}]({x['url']}) ({(x.get('publishedAt') or '')[:10]}): {one_line(x.get('name') or '', 80)}{more}",
                              "Jabłka do jabłek: liczby z notatek wydania – deklaracja autora, inna karta/model/kwant/T; u nas niezmierzone." if perf else None,
                              "przejrzeć zmiany pod HIP/gfx1100, spekulację, KV, nasze modele"))
        elif n_new:
            sc = tier * 0.4 + min(20, 3 * len(hl))
            items.append(Item(sc, "gh", f"**{label}**: +{n_new} commitów od {'ostatniego raportu' if prev else 'bazy'}"
                              + (f"; m.in.: {'; '.join(one_line(n['messageHeadline'], 70) for n in hl[:3])}" if hl else ""),
                              None, "przejrzeć `git log` pod kątem słów kluczowych"))
        tags = [x["tagName"] for x in rels]
        rstate[slug] = {"head": head.get("oid"), "head_date": head.get("committedDate"),
                        "releases": (tags + [t for t in prev.get("releases", []) if t not in tags])[:60],
                        "tags": [t["name"] for t in ((d.get("refs") or {}).get("nodes") or [])]}
    report["gh"] = rows
    report["gh_repos"] = len(snap)


def release_excerpt(body: str, kws: list[str], n: int = 3) -> list[str]:
    lines = []
    for ln in (body or "").splitlines():
        s = re.sub(r"^[#>*\-\s]+", "", ln).strip()
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        if len(s) < 12 or s.lower().startswith(("full changelog", "what's changed", "new contributors", "<")):
            continue
        lines.append(s)
    hot = [s for s in lines if kw_hits(s, kws)]
    pick = (hot + [s for s in lines if s not in hot])[:n]
    return [one_line(s, 220) for s in pick]


# ---------------------------------------------------------------- Hugging Face

def hf_scan(cfg: dict, state: dict, items: list[Item], report: dict, first: bool) -> None:
    h = cfg["hf"]
    seen: dict = state.setdefault("hf", {}).setdefault("seen", {})
    cutoff = (NOW - dt.timedelta(days=cfg["first_run_days"])).isoformat()
    found = []
    for author in h["authors"]:
        url = "https://huggingface.co/api/models?" + urllib.parse.urlencode(
            {"author": author, "filter": "gguf", "sort": "createdAt", "direction": "-1", "limit": h["limit"]})
        try:
            data, _ = http_json(url)
        except NET_ERR as e:
            report["notes"].append(f"HF `{author}`: błąd {one_line(str(e), 120)}.")
            continue
        report["hf_calls"] += 1
        for m in data:
            rid = m["id"]
            if rid in seen:
                continue
            seen[rid] = m.get("createdAt")
            names = [rid] + [t.split(":", 1)[1] for t in m.get("tags", []) if t.startswith("base_model:")]
            mdl = model_of(names, cfg["models"])
            if not mdl or (first and (m.get("createdAt") or "") < cutoff):
                continue
            found.append((mdl, rid, (m.get("createdAt") or "")[:10]))
    report["hf"] = sorted(found, key=lambda x: (x[2]), reverse=True)
    for mdl, rid, date in report["hf"]:
        items.append(Item({"core": 30, "catalog": 15}.get(mdl["tier"], 10), "hf",
                          f"HF GGUF [{rid}](https://huggingface.co/{rid}) ({date}) — {mdl['key']}", None,
                          "sprawdzić kwanty/KLD i czy zmienia wybór pliku dla karty"))


# ---------------------------------------------------------------- otwarte rankingi (feeds)
# Każdy adapter zwraca wiersze w jednym formacie:
# {id, date, tok, model, gpu, multi, engine, quant, cond, url}; `cond` opisuje warunki pomiaru źródła
# (trafia do linii „jabłka do jabłek”).

def feed_get(feed: dict, url: str, fs: dict, report: dict, tag: str = "") -> tuple[object | None, bool]:
    """GET z ETag/If-Modified-Since, limitem dziennym źródła i surową kopią w ~/.cache/compwatch/feeds/<nazwa>/.
    Zwraca (dane, zmienione). Przy 304 albo wyczerpanym limicie czyta ostatnią kopię."""
    day = TODAY.isoformat()
    used = fs.setdefault("requests", {})
    for d in [d for d in used if d < (TODAY - dt.timedelta(days=30)).isoformat()]:
        del used[d]
    cache = fs.setdefault("cache", {}).setdefault(url, {})
    raw_dir = CACHE / "feeds" / re.sub(r"[^A-Za-z0-9.-]+", "-", feed["name"]).strip("-")
    raw_dir.mkdir(parents=True, exist_ok=True)
    last = Path(cache["raw"]) if cache.get("raw") else None
    load_last = lambda: (json.loads(last.read_text()), False) if last and last.exists() else (None, False)
    if used.get(day, 0) >= feed.get("daily_max", 1):
        return load_last()
    hdr = {}
    if cache.get("etag") and last and last.exists():
        hdr["If-None-Match"] = cache["etag"]
    if cache.get("last_modified") and last and last.exists():
        hdr["If-Modified-Since"] = cache["last_modified"]
    used[day] = used.get(day, 0) + 1
    report["feed_requests"][feed["name"]] = report["feed_requests"].get(feed["name"], 0) + 1
    try:
        data, h = http_json(url, hdr, timeout=180)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return load_last()
        report["notes"].append(f"{feed['name']}: HTTP {e.code} dla {url}.")
        return load_last()
    except NET_ERR as e:
        report["notes"].append(f"{feed['name']}: błąd {one_line(str(e), 120)}.")
        return load_last()
    f = raw_dir / f"{day}{tag}.json"
    f.write_text(json.dumps(data))
    for old in sorted(raw_dir.glob("*.json")):
        if old.stem[:10] < (TODAY - dt.timedelta(days=30)).isoformat():
            old.unlink()
    cache.update(raw=str(f), etag=h.get("ETag") or h.get("Etag"), last_modified=h.get("Last-Modified"))
    return data, True


def feed_llm_speed(feed: dict, fs: dict, report: dict) -> tuple[list[dict], str]:
    ptr, _ = feed_get(feed, feed["url"], fs, report, ".pointer")
    if not ptr:
        return [], ""
    version = ptr.get("version", "?")
    data_url = urllib.parse.urljoin(feed["url"], ptr["files"]["json"])
    if fs.get("version") == version and fs.get("cache", {}).get(data_url, {}).get("raw"):
        data = json.loads(Path(fs["cache"][data_url]["raw"]).read_text())
    else:
        data, _ = feed_get(feed, data_url, fs, report, ".data")
    if not data:
        return [], version
    fs["version"] = version
    out = []
    for r in data.get("rows", []):
        if r.get("batch_size") not in (None, 1) or r.get("workload") == "concurrent-decode" or not r.get("decode_tps"):
            continue
        hw = r.get("hardware") or ""
        mtp = "wł." if re.search(r"mtp-on", r.get("model") or "", re.I) else "nie zapisane (pole MTP brak)"
        out.append({
            "id": f"{r['run_id']}:{r['workload']}:{r.get('prompt_tokens')}", "date": r.get("date"), "tok": r["decode_tps"], "model": r.get("model"),
            "gpu": hw.split(" + ")[0], "multi": bool(re.match(r"\s*\d+\s*[x×]", hw)),
            "engine": f"{r.get('runtime') or '?'}", "engine_raw": one_line(f"{r.get('runtime') or ''} {r.get('runtime_version') or ''}", 50),
            "quant": r.get("quant"), "url": r.get("run_url"),
            "cond": (f"llm-speed {r['workload']} ({r.get('prompt_tokens')}→{r.get('output_tokens')} tok., stałe prompty), "
                     f"{r.get('runtime')} {r.get('runtime_version') or ''}, {r.get('quant') or '?'}, MTP {mtp}, podpisany run, licznik klienta"),
        })
    return out, version


def feed_llmcheck(feed: dict, fs: dict, report: dict) -> tuple[list[dict], str]:
    data, _ = feed_get(feed, feed["url"], fs, report)
    if not data:
        return [], ""
    out = []
    for r in data.get("benchmarks", []):
        if r.get("provenance") not in ("sourced", "community") or not r.get("tps"):
            continue
        key = "|".join(str(r.get(k)) for k in ("model", "quant", "chip", "ram", "engine", "date", "tps", "source"))
        out.append({
            "id": hashlib.sha1(key.encode()).hexdigest()[:16], "date": r.get("date"), "tok": r["tps"], "model": r.get("model"),
            "gpu": f"{r.get('chip') or ''}", "multi": False, "engine": (r.get("engine") or "?").lower(), "engine_raw": r.get("engine") or "?",
            "quant": r.get("quant"), "url": r.get("source"),
            "cond": f"llmcheck {r.get('provenance')} ({r.get('ram')} GB), {r.get('engine')}, {r.get('quant') or '?'}, warunki wg źródła (prompt/ctx/T nieznane)",
        })
    return out, data.get("version", "?")


def feed_llmconf(feed: dict, fs: dict, report: dict) -> tuple[list[dict], str]:
    data, _ = feed_get(feed, feed["url"], fs, report)
    if not data:
        return [], ""
    out = []
    for r in data.get("entries", []):
        if not r.get("tokS"):
            continue
        out.append({
            "id": r["id"], "date": r.get("date") or r.get("reviewedAt"), "tok": r["tokS"], "model": r.get("variantId"),
            "gpu": (r.get("gpuId") or "").replace("-", " "), "multi": False,
            "engine": (r.get("runtime") or "?").split()[0].lower(), "engine_raw": r.get("runtime") or "?",
            "quant": r.get("quant"), "url": r.get("sourceUrl"),
            "cond": (f"{r.get('publisher') or r.get('provenance')} przez LLM Configurator, {r.get('runtime')}, ctx {r.get('contextLength')}, "
                     f"{r.get('quant') or '?'}, {r.get('offloadState') or ''}"),
        })
    return out, data.get("generatedAt", "?")[:10]


def feed_kyuz0(feed: dict, fs: dict, report: dict) -> tuple[list[dict], str]:
    data, _ = feed_get(feed, feed["url"], fs, report)
    if not data:
        return [], ""
    out = []
    for j in data.get("jobs", []):
        if j.get("status") != "complete":
            continue
        gen = sorted((p for p in j.get("points", []) if p.get("series") == "generation"), key=lambda p: p.get("starting_depth") or 0)
        if not gen:
            continue
        b, st, sv, sub = j.get("benchmark") or {}, j.get("stack") or {}, j.get("serving") or {}, j.get("subject") or {}
        spec = sv.get("speculative_method") or "bez spekulacji"
        if sv.get("draft_tokens"):
            spec += f" n={sv['draft_tokens']}"
        deep = gen[-1]
        out.append({
            "id": j["id"], "date": (j.get("completed_at") or "")[:10], "tok": gen[0]["mean"], "model": sub.get("model"),
            "gpu": (j.get("platform") or {}).get("hardware_label") or "", "multi": False,
            "engine": (st.get("engine_name") or "?").lower(), "engine_raw": one_line(f"{st.get('engine_name')} {st.get('engine_version') or ''}", 50),
            "quant": sub.get("quant"), "url": feed["home"],
            "cond": (f"kyuz0 {b.get('workload_label') or b.get('workload_id')}: T={(b.get('sampling') or {}).get('temperature')}, "
                     f"gen {b.get('tg')} tok. przy pustym kontekście (przy {deep.get('starting_depth')}: {deep['mean']:.1f} t/s), "
                     f"{spec}, {st.get('runtime_name')} {st.get('runtime_version') or ''}, {sub.get('quant')}, licznik klienta API"),
        })
    return out, max((x["date"] for x in out), default="?")


FEED_ADAPTERS = {"llm_speed": feed_llm_speed, "llmcheck": feed_llmcheck, "llmconf": feed_llmconf, "kyuz0": feed_kyuz0}


def feeds_scan(cfg: dict, state: dict, items: list[Item], report: dict) -> None:
    cards = {c["key"]: c for c in cfg["cards"]}
    ours = {(o["card"], o["model"]): o for o in cfg["nasze"]}
    fstate = state.setdefault("feeds", {})
    for feed in cfg.get("feeds", []):
        fs = fstate.setdefault(feed["name"], {})
        seen: dict = fs.setdefault("seen", {})
        engines = set(fs.get("engines", []))
        baseline = not fs.get("baseline_done")
        rows, version = FEED_ADAPTERS[feed["type"]](feed, fs, report)
        fw = feed.get("w", 1.0)
        fresh, beat_seen, matched, ids = [], set(), [], set()
        for r in rows:
            card = None if r["multi"] else card_of({"gpuName": r["gpu"]}, cfg["cards"])
            model = model_of([r["model"] or ""], cfg["models"])
            if not card and not model:
                continue
            r["card"] = card["key"] if card else None
            r["mkey"] = model["key"] if model else r["model"]
            r["tier"] = model["tier"] if model else "other"
            matched.append(r)
            if r["id"] not in seen and r["id"] not in ids and isinstance(r.get("tok"), (int, float)):
                ids.add(r["id"])
                fresh.append(r)
        rows = matched
        src = f"[{feed['name']}]({feed['home']})"
        desc = lambda r: (f"{r['tok']:.1f} t/s · {r['engine_raw']} · {r['quant'] or '?'} · {r['date']}"
                          + (f" · [run]({r['url']})" if r.get("url") and r["url"] != feed["home"] else "") + f" · źródło {src}")
        pool = list(seen.values())
        for r in sorted(fresh, key=lambda x: -x["tok"]):
            card = cards.get(r["card"]) if r["card"] else None
            tw = TIER_W.get(r["tier"], 0.3)
            o = ours.get((r["card"], r["mkey"]))
            cav = f"Jabłka do jabłek: oni: {r['cond']}; " + (f"my: {o['metric']} ({o['tok']} t/s, `{o['src']}`)." if o else "nasz pomiar na tej karcie: brak.")
            if card and o and r["tok"] > o["tok"]:
                pct = 100.0 * (r["tok"] / o["tok"] - 1)
                dup = (r["card"], r["mkey"], r["engine"]) in beat_seen
                beat_seen.add((r["card"], r["mkey"], r["engine"]))
                items.append(Item((60 + min(60, pct)) * card["w"] * tw * fw * (0.3 if dup else 1.0), "feeds",
                                  f"**{card['label']} / {r['mkey']}: {r['tok']:.1f} t/s > nasze {o['tok']} (+{pct:.0f}%)** — {desc(r)}", cav,
                                  "rozłożyć warunki (prompt, kwant, spekulacja); jeśli porównywalne – sprawdzić dźwignię u nas"))
            if card and not baseline:
                prev = max((x for x in pool if x.get("card") == r["card"] and x.get("mkey") == r["mkey"]), key=lambda x: x["tok"], default=None)
                if prev is None or r["tok"] > prev["tok"]:
                    was = f"poprzednio {prev['tok']:.1f} ({prev['engine']})" if prev else "pierwszy wiersz dla tej pary"
                    items.append(Item(45 * card["w"] * tw * fw, "feeds", f"Nowy top {card['label']} / {r['mkey']}: {desc(r)}; {was}", cav,
                                      "sprawdzić warunki źródła; czy da się odtworzyć u nas"))
            if not baseline and r["engine"] not in engines:
                engines.add(r["engine"])
                items.append(Item(25 * fw, "feeds", f"Nowy silnik w {src}: **{r['engine_raw']}** ({r['gpu']} / {r['mkey']}) — {desc(r)}", cav,
                                  "przeczytać opis silnika; czy działa na gfx1100 / sm_86"))
            pool.append({"card": r["card"], "mkey": r["mkey"], "tok": r["tok"], "engine": r["engine"]})
        for r in fresh:
            seen[r["id"]] = {"card": r["card"], "mkey": r["mkey"], "tok": r["tok"], "engine": r["engine"], "date": r["date"]}
            engines.add(r["engine"])
        fs["engines"] = sorted(engines)
        fs["baseline_done"] = True
        # Tabela najlepszych wierszy per (karta, model) ze zbioru – tylko w przebiegu bazowym źródła (raport dzienny = sama delta).
        tops = []
        if rows and baseline:
            best: dict = {}
            for r in rows:
                if not r.get("card") or r.get("tier") not in ("core", "catalog") or not isinstance(r.get("tok"), (int, float)):
                    continue
                k = (r["card"], r["mkey"])
                if k not in best or r["tok"] > best[k]["tok"]:
                    best[k] = r
            order = {c["key"]: i for i, c in enumerate(cfg["cards"])}
            tops = [(cards[k[0]], k[1], v, ours.get(k)) for k, v in sorted(best.items(), key=lambda kv: (order[kv[0][0]], kv[0][1]))]
        report["feeds"].append({"feed": feed, "version": version, "rows": len(rows), "fresh": fresh, "baseline": baseline, "tops": tops})


def render_feeds(cfg: dict, report: dict, top: list[Item], ranked: list[Item]) -> list[str]:
    L = ["## Otwarte rankingi", ""]
    L.append("Zapytania dziś: " + ", ".join(f"{f['name']} {report['feed_requests'].get(f['name'], 0)} (limit {f.get('daily_max', 1)})" for f in cfg.get("feeds", []))
             + ". Pobrania warunkowe (ETag) – niezmieniony plik nie jest ściągany ponownie.")
    L.append("")
    rest = [x for x in ranked if x.section == "feeds" and x not in top]
    if rest:
        L += ["Pozostałe pozycje:", ""] + [f"- {x.title}" + (f"\n  - {x.caveat}" if x.caveat else "") for x in rest] + [""]
    for fr in report["feeds"]:
        f = fr["feed"]
        L += [f"### {f['name']}", "", f"Źródło: [{f['home']}]({f['home']}), wersja {fr['version'] or '?'}; licencja: {f['licence']}. {f.get('attribution', '')}".rstrip(), ""]
        L.append(f"Wiersze (nasze karty lub modele): {fr['rows']}; nowe względem stanu: {len(fr['fresh'])}" + (" (przebieg bazowy źródła)." if fr["baseline"] else "."))
        L.append("")
        if fr["tops"]:
            L += ["| karta | model | najlepszy wiersz | warunki źródła | nasz pomiar (inne warunki!) |", "|---|---|---|---|---|"]
            for card, mk, r, o in fr["tops"]:
                L.append(f"| {card['label']} | {mk} | {r['tok']:.1f} · {one_line(r['engine_raw'], 40)} · {r['quant'] or '?'} · {r['date']} | {one_line(r['cond'], 140)} | "
                         + (f"{o['tok']} ({one_line(o['metric'], 60)})" if o else "brak") + " |")
            L.append("")
        if fr["fresh"] and not fr["baseline"]:
            L += [f"- {r['gpu']} / {r['mkey']}: {r['tok']:.1f} t/s · {r['engine_raw']} · {r['quant'] or '?'} · {r['date']}" for r in sorted(fr["fresh"], key=lambda x: -x["tok"])[:15]]
            L.append("")
    return L


# ---------------------------------------------------------------- arXiv

ARXIV_NS = {"a": "http://www.w3.org/2005/Atom", "os": "http://a9.com/-/spec/opensearch/1.1/", "ar": "http://arxiv.org/schemas/atom"}


def arxiv_scan(cfg: dict, state: dict, items: list[Item], report: dict, first: bool) -> None:
    """Oficjalne API arXiv: kategorie × frazy z `arxiv.query_terms`, okno od ostatniego przebiegu (z zakładką na
    opóźnienie ogłoszeń), najwyżej `max_pages` zapytań co `spacing_s` s; duplikaty po identyfikatorze arXiv."""
    ax = cfg["arxiv"]
    st = state.setdefault("arxiv", {})
    seen: dict = st.setdefault("seen", {})
    known = set(re.findall(r"arXiv[ :]*(\d{4}\.\d{4,5})", (KERNEL / cfg["github"]["registry"]).read_text(), re.I))
    since = (dt.datetime.fromisoformat(st["last_run"]) - dt.timedelta(days=ax["overlap_days"])) if st.get("last_run") \
        else NOW - dt.timedelta(days=ax["first_days"])
    since = max(since, NOW - dt.timedelta(days=ax["max_days"]))
    query = ("(" + " OR ".join(f"cat:{c}" for c in ax["categories"]) + ") AND ("
             + " OR ".join(f'abs:"{t}"' for t in ax["query_terms"]) + f") AND submittedDate:[{since:%Y%m%d%H%M} TO {NOW:%Y%m%d%H%M}]")
    report.update(arxiv_since=since.strftime("%Y-%m-%d %H:%M UTC"), arxiv_calls=0, arxiv_total=0, arxiv_fetched=0, arxiv_new=0, arxiv_known=0)
    entries: list = []
    for page in range(ax["max_pages"]):
        if page:
            time.sleep(ax["spacing_s"])
        url = ax["api"] + "?" + urllib.parse.urlencode({"search_query": query, "start": page * ax["page_size"], "max_results": ax["page_size"],
                                                         "sortBy": "submittedDate", "sortOrder": "descending"})
        report["arxiv_calls"] += 1
        try:
            raw, _ = http_get(url, {"Accept": "application/atom+xml"}, timeout=90)
            root = ET.fromstring(raw)
        except NET_ERR as e:
            report["notes"].append(f"arXiv: błąd {one_line(str(e), 120)} (strona {page + 1}).")
            break
        got = root.findall("a:entry", ARXIV_NS)
        if any("/api/errors" in (e.findtext("a:id", "", ARXIV_NS)) for e in got):
            report["notes"].append(f"arXiv: API odrzuciło zapytanie: {one_line(got[0].findtext('a:summary', '', ARXIV_NS), 160)}.")
            break
        report["arxiv_total"] = int(root.findtext("os:totalResults", "0", ARXIV_NS) or 0)
        entries += got
        if not got or len(entries) >= report["arxiv_total"]:
            break
    report["arxiv_fetched"] = len(entries)
    if report["arxiv_total"] > len(entries):
        report["notes"].append(f"arXiv: pobrano {len(entries)} z {report['arxiv_total']} wyników okna (limit `arxiv.max_pages`); "
                               "brakuje najstarszych, wrócą przy szerszym limicie.")
    for e in entries:
        aid = re.sub(r"v\d+$", "", (e.findtext("a:id", "", ARXIV_NS) or "").rsplit("/abs/", 1)[-1])
        if not aid or aid in seen:
            continue
        pub = (e.findtext("a:published", "", ARXIV_NS) or "")[:10]
        seen[aid] = pub or TODAY.isoformat()
        if aid in known:
            report["arxiv_known"] += 1
            continue
        report["arxiv_new"] += 1
        title = one_line(e.findtext("a:title", "", ARXIV_NS), 200)
        body = re.sub(r"\s+", " ", (e.findtext("a:summary", "", ARXIV_NS) or "") + " " + (e.findtext("ar:comment", "", ARXIV_NS) or ""))
        sc, hits, strongest = kw_score(title, body, cfg["research_keywords"])
        if strongest < ax["min_strong"] or sc < ax["min_score"]:
            continue
        code = re.search(r"https?://(?:www\.)?github\.com/[\w.-]+/[\w.-]+", body)
        cat = (e.find("ar:primary_category", ARXIV_NS).get("term") if e.find("ar:primary_category", ARXIV_NS) is not None else "")
        items.append(Item(min(ax["max_score"], sc + (ax["code_bonus"] if code else 0)), "arxiv",
                          f"arXiv [{aid}](https://arxiv.org/abs/{aid}) ({pub}{', ' + cat if cat else ''}): **{title}**"
                          + (f" · kod: {code.group(0).rstrip('.')}" if code else ""), None,
                          f"trafienia: {', '.join(dict.fromkeys(hits))} → abstrakt i kod; mechanizm, liczby, sprzęt; delta vs `wiki/ZRODLA.md`"))
    for k in [k for k, v in seen.items() if v < (TODAY - dt.timedelta(days=ax["seen_days"])).isoformat()]:
        del seen[k]
    st["last_run"] = NOW.isoformat()


# ---------------------------------------------------------------- blogi (RSS/Atom)

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_date(s: str | None) -> dt.datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def feed_entries(root: ET.Element) -> list[dict]:
    """Wpisy RSS 2.0 (`item`) i Atom (`entry`) w jednym formacie {id, title, link, date, text}."""
    out = []
    for e in root.iter():
        if _local(e.tag) not in ("item", "entry"):
            continue
        f: dict = {"title": "", "link": "", "id": "", "date": "", "text": [], "cats": []}
        for c in e:
            n = _local(c.tag)
            if n == "title":
                f["title"] = "".join(c.itertext())
            elif n == "link":
                if c.get("href") and c.get("rel", "alternate") == "alternate":
                    f["link"] = c.get("href")
                elif not c.get("href") and (c.text or "").strip():
                    f["link"] = c.text.strip()
            elif n in ("guid", "id"):
                f["id"] = (c.text or "").strip()
            elif n in ("pubDate", "published", "date") or (n == "updated" and not f["date"]):
                f["date"] = (c.text or "").strip()
            elif n in ("description", "summary", "content", "encoded"):
                f["text"].append("".join(c.itertext()))
            elif n == "category":
                f["cats"].append(c.get("term") or (c.text or ""))
        text = html.unescape(re.sub(r"<[^>]+>", " ", " ".join(f["text"])))
        out.append({"id": f["id"] or f["link"], "title": one_line(html.unescape(f["title"]), 200), "link": f["link"],
                    "date": parse_date(f["date"]), "text": re.sub(r"\s+", " ", text)[:4000] + " " + " ".join(f["cats"])})
    return out


def rss_scan(cfg: dict, state: dict, items: list[Item], report: dict, first: bool) -> None:
    """Blogi inżynierskie (config.json → rss.feeds): jedno warunkowe GET na źródło, nowe wpisy po id/linku,
    trafne = wzorce `research_keywords` (źródła `all: true` piszą tylko o inferencji, więc liczy się każdy wpis)."""
    rc = cfg["rss"]
    rstate = state.setdefault("rss", {})
    report.update(rss=[], rss_calls=0)
    for feed in rc["feeds"]:
        fs = rstate.setdefault(feed["name"], {})
        seen: dict = fs.setdefault("seen", {})
        baseline = not fs.get("baseline_done")
        hdr = {"Accept": "application/atom+xml, application/rss+xml, application/xml;q=0.9, */*;q=0.5"}
        if fs.get("etag"):
            hdr["If-None-Match"] = fs["etag"]
        if fs.get("last_modified"):
            hdr["If-Modified-Since"] = fs["last_modified"]
        row = {"feed": feed, "entries": 0, "new": 0, "status": "ok"}
        report["rss"].append(row)
        report["rss_calls"] += 1
        try:
            raw, h = http_get(feed["url"], hdr, timeout=90)
            entries = feed_entries(ET.fromstring(raw))
        except urllib.error.HTTPError as e:
            row["status"] = "bez zmian (304)" if e.code == 304 else f"HTTP {e.code}"
            if e.code != 304:
                report["notes"].append(f"RSS {feed['name']}: HTTP {e.code} dla {feed['url']}.")
            continue
        except NET_ERR as e:
            row["status"] = "błąd"
            report["notes"].append(f"RSS {feed['name']}: błąd {one_line(str(e), 120)}.")
            continue
        fs.update(etag=h.get("ETag") or h.get("Etag"), last_modified=h.get("Last-Modified"))
        row["entries"] = len(entries)
        # Pamiętamy wpisy z ostatnich `max_age_days`; starsze pomijamy bez zapisu (archiwalne wpisy kanału nie puchną w stanie).
        # Przebieg bazowy źródła ocenia tylko `first_days`, resztę okna zapisuje jako widzianą.
        horizon = NOW - dt.timedelta(days=rc["max_age_days"])
        fresh_from = NOW - dt.timedelta(days=rc["first_days"]) if baseline else horizon
        for x in entries:
            if not x["id"] or x["id"] in seen or (x["date"] and x["date"] < horizon):
                continue
            seen[x["id"]] = (x["date"] or NOW).date().isoformat()
            if (x["date"] and x["date"] < fresh_from) or (baseline and not x["date"]):
                continue
            sc, hits, strongest = kw_score(x["title"], x["text"], cfg["research_keywords"])
            if feed.get("all"):
                sc += rc["all_base"]
            elif strongest < rc["min_strong"]:
                continue
            sc *= feed.get("w", 1.0)
            if sc < rc["min_score"]:
                continue
            row["new"] += 1
            items.append(Item(min(rc["max_score"], sc), "rss",
                              f"{feed['name']}: **[{x['title']}]({x['link']})** ({x['date'].date().isoformat() if x['date'] else 'bez daty'})", None,
                              (f"trafienia: {', '.join(dict.fromkeys(hits))} → " if hits else "") + "przeczytać; mechanizm i liczby → notatka, test bez karty albo `K-…`"))
        for k in [k for k, v in seen.items() if v < (TODAY - dt.timedelta(days=2 * rc["max_age_days"])).isoformat()]:
            del seen[k]
        fs["baseline_done"] = True


def render_research(cfg: dict, report: dict, top: list[Item], ranked: list[Item]) -> list[str]:
    cap, L = cfg["report_section_max"], []
    if "arxiv_calls" in report:
        ax = cfg["arxiv"]
        L += ["## arXiv", "",
              f"Zapytania: {report['arxiv_calls']} (co {ax['spacing_s']:.0f} s), kategorie {', '.join(ax['categories'])}, okno od {report['arxiv_since']}: "
              f"{report['arxiv_total']} prac, nowych {report['arxiv_new']}, trafnych {sum(1 for x in ranked if x.section == 'arxiv')}, "
              f"już w `wiki/ZRODLA.md` {report['arxiv_known']}.", ""]
        rest = [x for x in ranked if x.section == "arxiv" and x not in top]
        L += [f"- {x.title} *(waga {x.score:.0f})*" for x in rest[:cap]]
        if len(rest) > cap:
            L.append(f"- … i {len(rest) - cap} słabszych (zapisane w stanie, nie wrócą)")
        L += [""] if rest else []
    if report.get("rss"):
        L += ["## Blogi (RSS/Atom)", "",
              "Źródła: " + "; ".join(f"[{r['feed']['name']}]({r['feed']['home']}) {r['status']}, wpisów {r['entries']}, nowych trafnych {r['new']}"
                                     for r in report["rss"]) + ".", ""]
        rest = [x for x in ranked if x.section == "rss" and x not in top]
        L += [f"- {x.title} *(waga {x.score:.0f})*" for x in rest[:cap]]
        if len(rest) > cap:
            L.append(f"- … i {len(rest) - cap} słabszych")
        L += [""] if rest else []
    return L


# ---------------------------------------------------------------- raport

def files_digest(cfg: dict) -> dict[str, str]:
    out = {}
    for pat in cfg["nasze_files"]:
        for f in sorted(glob.glob(str(KERNEL / pat))):
            out[str(Path(f).relative_to(KERNEL))] = hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16]
    return out


def catalog_check(cfg: dict, report: dict) -> None:
    f = KERNEL / "app/landing/src/lib/data/models.json"
    if not f.exists():
        return
    names = sorted({m["name"] for m in json.loads(f.read_text()).get("models", [])})
    miss = [n for n in names if not model_of([n.replace(" ", "-")], cfg["models"])]
    if miss:
        report["notes"].append("Modele z katalogu (`app/landing/src/lib/data/models.json`) bez wzorca w `config.json → models`: "
                               + ", ".join(miss) + ".")


def render(cfg: dict, items: list[Item], report: dict, first: bool) -> str:
    L = [f"# Wywiad konkurencji — {TODAY.isoformat()}", ""]
    L.append(f"Wygenerowane przez `tools/compwatch/compwatch.py` ({dt.datetime.now():%H:%M} czasu lokalnego). "
             + ("**Przebieg bazowy**: delta względem wersji w `wiki/ZRODLA.md` i sekcji „Do bazy wiedzy” raportów; LocalMaxxing = stan wyjściowy. "
                if first else "Delta względem ostatniego raportu. ")
             + "Dane LocalMaxxing to zgłoszenia użytkowników (treść należy do autorów, brak licencji danych): tylko do wewnętrznej analizy, bez republikacji w produkcie.")
    L.append("")
    ranked = sorted(items, key=lambda x: -x.score)
    L += ["## Do sprawdzenia", ""]
    top = [x for x in ranked if x.score >= cfg["report_min_score"]][: cfg["top_items"]] or ranked[: min(5, len(ranked))]
    if not top:
        L.append("Brak pozycji.")
    for i, x in enumerate(top, 1):
        L.append(f"{i}. {x.title} *(waga {x.score:.0f})*")
        if x.caveat:
            L.append(f"   - {x.caveat}")
        if x.next_step:
            L.append(f"   - → {x.next_step}")
    L.append("")

    # LocalMaxxing
    L += ["## LocalMaxxing", ""]
    L.append(f"Zapytania dziś: {report['lmx_requests']} (limit {cfg['localmaxxing']['daily_max']}/dzień), wiersze: {report.get('lmx_rows', 0)}, "
             f"nowe względem stanu (nasze karty lub modele): {report.get('lmx_new', 0)}.")
    L.append("")
    lmx_items = [x for x in ranked if x.section == "lmx" and x not in top]
    if lmx_items:
        L += ["Pozostałe pozycje:", ""] + [f"- {x.title}" + (f"\n  - {x.caveat}" if x.caveat else "") for x in lmx_items] + [""]
    if report.get("lmx_tops") and first:
        L += ["### Najlepsze runy per karta (1×GPU, cała zebrana historia)", "",
              "| karta | model | najlepszy verified | najlepszy dowolny | nasz pomiar (inne warunki!) |", "|---|---|---|---|---|"]
        for card, mk, bv, ba, o in report["lmx_tops"]:
            f = lambda c: f"{c['tok']:.1f} · {one_line(c['engine_raw'] or c['engine'], 40)} · {c['quant'] or '?'} · {c['spec'] or '—'} · {c['date']}" if c else "—"
            L.append(f"| {card['label']} | {mk} | {f(bv)} | {f(ba) if card.get('unverified') else 'n/d'} | "
                     + (f"{o['tok']} ({one_line(o['metric'], 60)})" if o else "brak") + " |")
        L += ["", "Każda liczba z tej tabeli wymaga sprawdzenia „jabłka do jabłek” (prompt kanoniczny T=0 vs nasz spec_sweep T=1, kwant, szerokość drafu, licznik klienta vs serwera) – `32d §3`.", ""]
        nocard = [c["label"] for c in cfg["cards"] if not any(t[0]["key"] == c["key"] for t in report["lmx_tops"])]
        if nocard:
            L += [f"Bez runów dla naszych modeli w zebranych danych: {', '.join(nocard)}.", ""]
    if report.get("lmx_engines_first"):
        L += ["Silniki widoczne w danych (stan wyjściowy): " + ", ".join(f"`{e}`" for e in report["lmx_engines_first"]) + ".", ""]

    # GitHub
    L += ["## GitHub", ""]
    L.append(f"Repozytoria: {report.get('gh_repos', 0)} (lista: `config.json → github.repos` + wszystkie `github.com/...` z `wiki/ZRODLA.md`). Zapytania GraphQL: {report['gh_calls']}.")
    L.append("")
    cap = cfg["report_section_max"]
    if report.get("gh"):
        hot = sorted((t for t in report["gh"] if t[2] or t[4]), key=lambda t: (t[0].get("tier", "C"), t[0]["slug"].lower()))
        quiet = sorted((t for t in report["gh"] if not t[2] and not t[4]), key=lambda t: -t[3])
        if hot:
            L += ["| repo | baza (ZRODLA / raport) | HEAD | commity od bazy | nowe od " + ("bazy" if first else "ostatniego raportu") + " | nowe wydania |",
                  "|---|---|---|---|---|---|"]
            for r, d, rels, n_new, hl in hot:
                base = f"`{r['base'][0][:9]}` {r['base'][1][:10]} ({r['base'][2]})" if r.get("base") else f"brak sha w rejestrze (okno {cfg['first_run_days']} dni)"
                head = r.get("head") or {}
                L.append(f"| [{r['slug']}]({d['url']}) | {base} | `{(head.get('oid') or '')[:9]}` {(head.get('committedDate') or '')[:10]} | "
                         f"{r.get('since_base') if r.get('base') and r.get('since_base') is not None else '—'} | {n_new} | {', '.join(x['tagName'] for x in rels) or '—'} |")
            L.append("")
        if quiet:
            L += ["Same commity, bez wydań i bez słów kluczowych w nagłówkach: "
                  + ", ".join(f"{r['slug']} (+{n_new})" for r, _, _, n_new, _ in quiet) + ".", ""]
        kws = cfg["github"]["keywords"]
        for r, d, rels, n_new, hl in hot[:cap]:
            L += [f"### {r.get('name') or r['slug']}", ""]
            for x in rels[:3]:
                L.append(f"- [{x['tagName']}]({x['url']}) {(x.get('publishedAt') or '')[:10]}{' (pre-release)' if x.get('isPrerelease') else ''}: {one_line(x.get('name') or '', 100)}")
                for s in release_excerpt(x.get("description") or "", kws, 2):
                    L.append(f"  - „{s}”")
            if len(rels) > 3:
                L.append(f"- … i {len(rels) - 3} starszych wydań: {', '.join(x['tagName'] for x in rels[3:])}")
            for n in hl[:4]:
                L.append(f"- commit `{n['oid'][:9]}` {n['committedDate'][:10]}: {one_line(n['messageHeadline'], 120)}")
            L.append("")
        if len(hot) > cap:
            L += [f"Szczegóły pominięte (limit `report_section_max` = {cap}): " + ", ".join(t[0]["slug"] for t in hot[cap:]) + ".", ""]
    else:
        L += ["Brak zmian.", ""]

    # Otwarte rankingi
    if report.get("feeds"):
        L += render_feeds(cfg, report, top, ranked)

    # arXiv i blogi
    L += render_research(cfg, report, top, ranked)

    # HF
    L += ["## Hugging Face: nowe repo GGUF (" + ", ".join(cfg["hf"]["authors"]) + ")", ""]
    if report.get("hf"):
        L += [f"- [{rid}](https://huggingface.co/{rid}) — {date}" for _, rid, date in report["hf"]]
        if first:
            L.append(f"\n(przebieg bazowy: tylko repo z ostatnich {cfg['first_run_days']} dni)")
    else:
        L.append("Brak nowych repo dla modeli z katalogu i kandydatów.")
    L.append("")

    if report["notes"]:
        L += ["## Uwagi", ""] + [f"- {n}" for n in report["notes"]] + [""]
    return "\n".join(L).rstrip() + "\n"


def update_index(top: list[Item], fname: str, n: int) -> Path:
    idx = OUT_DIR / "INDEX.md"
    head = ("# Wywiad konkurencji: indeks raportów\n\n"
            "Raporty dzienne `tools/compwatch/compwatch.py` (timer systemd 06:30, `nice`). Jedna linia na raport; "
            "pierwsza pozycja „Do sprawdzenia” w skrócie.\n\n")
    lines = idx.read_text().splitlines() if idx.exists() else head.rstrip("\n").split("\n") + [""]
    label = fname.removesuffix(".md")
    lines = [ln for ln in lines if not ln.startswith(f"- [{label}](")]
    lead = re.sub(r"\*\*|\[|\]\([^)]*\)", "", top[0].title) if top else "brak pozycji"
    lines.append(f"- [{label}]({fname}): {n} pozycji; top: {one_line(lead, 160)}")
    idx.write_text("\n".join(lines).rstrip("\n") + "\n")
    return idx


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(KERNEL), *args], capture_output=True, text=True, timeout=300)


def publish(paths: list[Path], msg: str) -> str:
    rel = [str(p.relative_to(KERNEL)) for p in paths]
    for attempt in (1, 2):
        f = git("fetch", "-q", "origin")
        if f.returncode != 0:
            return f"git fetch nieudany: {one_line(f.stderr, 200)}"
        behind = git("rev-list", "--count", "HEAD..@{u}").stdout.strip()
        if behind not in ("", "0"):
            p = git("pull", "--rebase", "--autostash", "-q")
            if p.returncode != 0:
                git("rebase", "--abort")
                return f"git pull --rebase nieudany: {one_line(p.stderr, 200)}"
        git("add", "--", *rel)
        if git("diff", "--cached", "--quiet", "--", *rel).returncode != 0:
            c = git("commit", "-q", "-m", msg, "--", *rel)
            if c.returncode != 0:
                return f"git commit nieudany: {one_line(c.stderr + c.stdout, 200)}"
        p = git("push", "-q", "origin", "HEAD")
        if p.returncode == 0:
            return "ok " + git("rev-parse", "--short", "HEAD").stdout.strip()
    return f"git push nieudany: {one_line(p.stderr, 200)}"


def write_summary(path: Path, cfg: dict, items: list[Item], report: dict, first: bool, report_path: Path | None, t0: float) -> None:
    """Podsumowanie przebiegu w JSON dla przekazania dalej (np. skrzynka sesji Kernel): raport, liczby per źródło, top."""
    ranked = sorted(items, key=lambda x: -x.score)
    top = [x for x in ranked if x.score >= cfg["report_min_score"]][: cfg["top_items"]] or ranked[:5]
    plain = lambda s: one_line(re.sub(r"\*\*|\[|\]\([^)]*\)", "", s), 220)
    data = {
        "data": TODAY.isoformat(), "czas": dt.datetime.now().isoformat(timespec="seconds"), "sekundy": round(time.monotonic() - t0),
        "raport": str(report_path) if report_path else None,
        "raport_w_repo": str(report_path.relative_to(KERNEL)) if report_path and report_path.is_relative_to(KERNEL) else None,
        "bazowy": first, "pozycje": len(items), "istotne": sum(x.score >= cfg["report_min_score"] for x in items),
        "sekcje": dict(Counter(x.section for x in items)), "nowe": report["counts"], "zapytania": report["calls"],
        "top": [{"waga": round(x.score), "sekcja": x.section, "tytul": plain(x.title)} for x in top],
        "uwagi": report["notes"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(path)


def main() -> int:
    global OUT_DIR
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="raport na stdout, bez zapisu stanu, plików i gita")
    ap.add_argument("--no-git", action="store_true", help="zapisz raport, ale bez commit/push")
    ap.add_argument("--force", action="store_true", help="zapisz raport nawet bez istotnej delty")
    ap.add_argument("--out", type=Path, help="katalog raportu i INDEX.md zamiast product/research/watch (poza repo = bez gita)")
    ap.add_argument("--summary", type=Path, help="zapisz podsumowanie przebiegu (JSON) pod tą ścieżką")
    a = ap.parse_args()
    if a.out:
        OUT_DIR = a.out.expanduser().resolve()
    t0 = time.monotonic()

    CACHE.mkdir(parents=True, exist_ok=True)
    lock = open(CACHE / "lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("inny przebieg trwa – wychodzę")
        return 0
    cfg = json.loads((HERE / "config.json").read_text())
    sf = CACHE / "state.json"
    state = json.loads(sf.read_text()) if sf.exists() else {"version": 1}
    first = not state.get("last_report")
    report = {"notes": [], "lmx_requests": 0, "gh_calls": 0, "hf_calls": 0, "feed_requests": {}, "feeds": []}
    items: list[Item] = []

    dig = files_digest(cfg)
    if state.get("files") and dig != state["files"]:
        changed = sorted(k for k in set(dig) | set(state["files"]) if dig.get(k) != state["files"].get(k))
        items.append(Item(20, "meta", f"Zmienione źródła naszych liczb: {', '.join(f'`{c}`' for c in changed)} — zaktualizuj `config.json → nasze`, jeśli padł nowy rekord.",
                          None, "porównać z `nasze` w config.json"))
    catalog_check(cfg, report)

    # Każde źródło osobno: błąd jednego (zmiana API, zerwane połączenie) trafia do „Uwag”, reszta przebiegu idzie dalej.
    steps = [("LocalMaxxing", lambda: lmx_analyze(cfg, state, lmx_fetch(cfg, state, report), items, report, first)),
             ("GitHub", lambda: github_scan(cfg, state, items, report, first)),
             ("Hugging Face", lambda: hf_scan(cfg, state, items, report, first)),
             ("otwarte rankingi", lambda: feeds_scan(cfg, state, items, report)),
             ("arXiv", lambda: arxiv_scan(cfg, state, items, report, first)),
             ("RSS", lambda: rss_scan(cfg, state, items, report, first))]
    for name, step in steps:
        try:
            step()
        except Exception as e:  # noqa: BLE001 – jedno źródło nie może zatrzymać zwiadu
            report["notes"].append(f"{name}: przebieg źródła przerwany ({type(e).__name__}: {one_line(str(e), 160)}); pozostałe źródła działały.")
            log(f"{name}: {type(e).__name__}: {e}")

    report["counts"] = {"localmaxxing": report.get("lmx_new", 0), "github": len(report.get("gh") or []), "hf": len(report.get("hf") or []),
                        "rankingi": sum(len(f["fresh"]) for f in report["feeds"]), "arxiv": report.get("arxiv_new", 0),
                        "rss": sum(r["new"] for r in report.get("rss") or [])}
    report["calls"] = {"localmaxxing": report["lmx_requests"], "github": report["gh_calls"], "hf": report["hf_calls"],
                       "rankingi": sum(report["feed_requests"].values()), "arxiv": report.get("arxiv_calls", 0), "rss": report.get("rss_calls", 0)}
    significant = any(x.score >= cfg["report_min_score"] for x in items)
    last = dt.date.fromisoformat(state["last_report"]) if state.get("last_report") else None
    digest = bool(items) and last is not None and (TODAY - last).days >= cfg["digest_days"]
    write = first or significant or digest or a.force
    log(f"pozycje: {len(items)} {dict(Counter(x.section for x in items))}, istotne: {significant}, nowe: {report['counts']}, "
        f"zapytania: {report['calls']}, {time.monotonic() - t0:.0f} s")

    if a.dry_run:
        sys.stdout.write(render(cfg, items, report, first))
        if a.summary:
            write_summary(a.summary, cfg, items, report, first, None, t0)
        return 0
    if not write:
        # Zapisujemy tylko liczniki zapytań (LocalMaxxing, feeds); drobne delty kumulują się do raportu.
        old = json.loads(sf.read_text()) if sf.exists() else {"version": 1}
        old.setdefault("lmx", {})["requests"] = state.get("lmx", {}).get("requests", {})
        for name, fs in state.get("feeds", {}).items():
            old.setdefault("feeds", {}).setdefault(name, {})["requests"] = fs.get("requests", {})
        old["last_run"] = NOW.isoformat()
        sf.write_text(json.dumps(old, ensure_ascii=False, indent=1))
        if a.summary:
            write_summary(a.summary, cfg, items, report, first, None, t0)
        log("brak istotnej delty – bez raportu")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Drugi raport tego samego dnia (np. nowe źródło) nie nadpisuje pierwszego.
    fname, n = f"{TODAY.isoformat()}.md", 1
    while state.get("last_report") == TODAY.isoformat() and (OUT_DIR / fname).exists():
        n += 1
        fname = f"{TODAY.isoformat()}-{n}.md"
    (OUT_DIR / fname).write_text(render(cfg, items, report, first))
    ranked = sorted(items, key=lambda x: -x.score)
    idx = update_index(ranked, fname, len(items))
    state.update(last_report=TODAY.isoformat(), last_run=NOW.isoformat(), files=dig)
    sf.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    log(f"raport: {OUT_DIR / fname}")
    if a.summary:
        write_summary(a.summary, cfg, items, report, first, OUT_DIR / fname, t0)
    if not a.no_git and not OUT_DIR.is_relative_to(KERNEL):
        log(f"git: pominięty (katalog raportu {OUT_DIR} jest poza repo)")
    elif not a.no_git:
        res = publish([OUT_DIR / fname, idx], f"watch {TODAY.isoformat()}: wywiad konkurencji ({len(items)} pozycji)")
        log(f"git: {res}")
        if not res.startswith("ok"):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
