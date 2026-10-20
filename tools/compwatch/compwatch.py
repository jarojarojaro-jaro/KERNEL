#!/usr/bin/env python3
"""compwatch: codzienny wywiad konkurencji (LocalMaxxing, GitHub, Hugging Face).

Porównuje bieżący stan ze stanem z ostatniego raportu (~/.cache/compwatch/state.json)
i z wersjami zapisanymi w wiki/ZRODLA.md. Przy delcie pisze
product/research/watch/YYYY-MM-DD.md, dopisuje linię do INDEX.md, robi commit i push.
Konfiguracja: config.json obok. Opis: README.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import glob
import hashlib
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
KERNEL = HERE.parents[1]
CACHE = Path(os.environ.get("COMPWATCH_CACHE", "~/.cache/compwatch")).expanduser()
OUT_DIR = KERNEL / "product/research/watch"
UA = "compwatch/1.0 (+https://github.com/jarojarojaro-jaro/KERNEL/tree/main/tools/compwatch)"
TIER_W = {"core": 1.0, "catalog": 0.6, "candidate": 0.4}

TODAY = dt.date.today()
NOW = dt.datetime.now(dt.timezone.utc)


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def one_line(s: str | None, n: int = 200) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip().replace("|", "/")
    return s if len(s) <= n else s[: n - 1] + "…"


def http_json(url: str, headers: dict | None = None, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r), dict(r.headers)


def kw_hits(text: str, keywords: list[str]) -> list[str]:
    t = (text or "").lower()
    return [k for k in keywords if k in t]


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
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
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
    ok = subprocess.run([p, "auth", "status"], capture_output=True, text=True).returncode == 0
    return p if ok else None


def gh_graphql(gh: str, query: str) -> dict:
    p = subprocess.run([gh, "api", "graphql", "-f", f"query={query}"], capture_output=True, text=True, timeout=180)
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
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
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
    if report.get("lmx_tops") and (first or any(x.section == "lmx" for x in items)):
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
    if report.get("gh"):
        L += ["| repo | baza (ZRODLA / raport) | HEAD | commity od bazy | nowe od " + ("bazy" if first else "ostatniego raportu") + " | nowe wydania |",
              "|---|---|---|---|---|---|"]
        for r, d, rels, n_new, hl in sorted(report["gh"], key=lambda t: (t[0].get("tier", "C"), t[0]["slug"].lower())):
            base = f"`{r['base'][0][:9]}` {r['base'][1][:10]} ({r['base'][2]})" if r.get("base") else f"brak sha w rejestrze (okno {cfg['first_run_days']} dni)"
            head = r.get("head") or {}
            L.append(f"| [{r['slug']}]({d['url']}) | {base} | `{(head.get('oid') or '')[:9]}` {(head.get('committedDate') or '')[:10]} | "
                     f"{r.get('since_base') if r.get('base') and r.get('since_base') is not None else '—'} | {n_new} | {', '.join(x['tagName'] for x in rels) or '—'} |")
        L.append("")
        kws = cfg["github"]["keywords"]
        for r, d, rels, n_new, hl in report["gh"]:
            if not rels and not hl:
                continue
            L += [f"### {r.get('name') or r['slug']}", ""]
            for x in rels[:4]:
                L.append(f"- [{x['tagName']}]({x['url']}) {(x.get('publishedAt') or '')[:10]}{' (pre-release)' if x.get('isPrerelease') else ''}: {one_line(x.get('name') or '', 100)}")
                for s in release_excerpt(x.get("description") or "", kws):
                    L.append(f"  - „{s}”")
            if len(rels) > 4:
                L.append(f"- … i {len(rels) - 4} starszych wydań: {', '.join(x['tagName'] for x in rels[4:])}")
            for n in hl[:6]:
                L.append(f"- commit `{n['oid'][:9]}` {n['committedDate'][:10]}: {one_line(n['messageHeadline'], 120)}")
            L.append("")
    else:
        L += ["Brak zmian.", ""]

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
            "Raporty dzienne `tools/compwatch/compwatch.py` (cron 06:30, `nice -n 19`). Jedna linia na raport; "
            "pierwsza pozycja „Do sprawdzenia” w skrócie.\n\n")
    lines = idx.read_text().splitlines() if idx.exists() else head.rstrip("\n").split("\n") + [""]
    date = fname[:10]
    lines = [ln for ln in lines if not ln.startswith(f"- [{date}]")]
    lead = re.sub(r"\*\*|\[|\]\([^)]*\)", "", top[0].title) if top else "brak pozycji"
    lines.append(f"- [{date}]({fname}): {n} pozycji; top: {one_line(lead, 160)}")
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="raport na stdout, bez zapisu stanu, plików i gita")
    ap.add_argument("--no-git", action="store_true", help="zapisz raport, ale bez commit/push")
    ap.add_argument("--force", action="store_true", help="zapisz raport nawet bez istotnej delty")
    a = ap.parse_args()

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
    report = {"notes": [], "lmx_requests": 0, "gh_calls": 0, "hf_calls": 0}
    items: list[Item] = []

    dig = files_digest(cfg)
    if state.get("files") and dig != state["files"]:
        changed = sorted(k for k in set(dig) | set(state["files"]) if dig.get(k) != state["files"].get(k))
        items.append(Item(20, "meta", f"Zmienione źródła naszych liczb: {', '.join(f'`{c}`' for c in changed)} — zaktualizuj `config.json → nasze`, jeśli padł nowy rekord.",
                          None, "porównać z `nasze` w config.json"))
    catalog_check(cfg, report)

    rows = lmx_fetch(cfg, state, report)
    lmx_analyze(cfg, state, rows, items, report, first)
    github_scan(cfg, state, items, report, first)
    hf_scan(cfg, state, items, report, first)

    significant = any(x.score >= cfg["report_min_score"] for x in items)
    last = dt.date.fromisoformat(state["last_report"]) if state.get("last_report") else None
    digest = bool(items) and last is not None and (TODAY - last).days >= cfg["digest_days"]
    write = first or significant or digest or a.force
    log(f"pozycje: {len(items)}, istotne: {significant}, lmx zapytań: {report['lmx_requests']}, gh: {report['gh_calls']}, hf: {report['hf_calls']}")

    if a.dry_run:
        sys.stdout.write(render(cfg, items, report, first))
        return 0
    if not write:
        # Zapisujemy tylko licznik zapytań LocalMaxxing; drobne delty kumulują się do raportu.
        old = json.loads(sf.read_text()) if sf.exists() else {"version": 1}
        old.setdefault("lmx", {})["requests"] = state["lmx"]["requests"]
        old["last_run"] = NOW.isoformat()
        sf.write_text(json.dumps(old, ensure_ascii=False, indent=1))
        log("brak istotnej delty – bez raportu")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{TODAY.isoformat()}.md"
    (OUT_DIR / fname).write_text(render(cfg, items, report, first))
    ranked = sorted(items, key=lambda x: -x.score)
    idx = update_index(ranked, fname, len(items))
    state.update(last_report=TODAY.isoformat(), last_run=NOW.isoformat(), files=dig)
    sf.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    log(f"raport: {OUT_DIR / fname}")
    if not a.no_git:
        res = publish([OUT_DIR / fname, idx], f"watch {TODAY.isoformat()}: wywiad konkurencji ({len(items)} pozycji)")
        log(f"git: {res}")
        if not res.startswith("ok"):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
