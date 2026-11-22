#!/usr/bin/env python3
"""Porządki wiki Kernela: przenosiny, scalanie, archiwum, huby części (cienki adapter na wiedza.py i wiki.py).

  python3 tools/porzadki.py wykonaj --sucho              # plan z reguł (tools/plan_porzadkow.py) i raport, nic nie zmienia
  python3 tools/porzadki.py wykonaj                      # cały porządek jednym poleceniem: plan, przenosiny, scalenia,
                                                         # archiwum, linki w wiki i w repo, huby, tabele, index, lint,
                                                         # commit „porządki wiki: …” (lint z błędem = wszystko cofnięte)
  python3 tools/porzadki.py cofnij                       # git revert ostatniego commitu porządków
  python3 tools/porzadki.py zasiej                       # foldery i huby części z tools/czesci.py (tylko brakujące)
  python3 tools/porzadki.py plan PLIK.tsv [--akcje przenies,scal,archiwum,hub] [--tylko S1,S2…] [--limit N]
                                          [--repo] [--sucho]
  python3 tools/porzadki.py przenies STARA CZESC         # jedna notatka do innej części (ta sama nazwa pliku)
  python3 tools/porzadki.py scal B A [--bez-tresci]      # treść B dopisana do A, B do archiwum, linki do B → A
  python3 tools/porzadki.py archiwizuj STARA --powod "…" [--nastepca X]
  python3 tools/porzadki.py napraw-huby                  # hub pustego dawnego folderu: linki do niego → hub części, plik usunięty
  python3 tools/porzadki.py streszczenie CZESC "tekst"   # blok „Najważniejsze” w _hub.md części (do 1500 znaków)

Silnik przenosin i przepisywania linków `[[nazwa]]`, `[[folder/nazwa|tekst]]`, `[[x#sekcja]]` to wiedza.py skarbca
Jarva (`przenies_notatki`, `przepisz_linki`, `wstaw_streszczenie`; JARVO_WIEDZA = katalog wiedza.py, domyślnie
~/dev/JARVO/wiedza, bez niego wiedza/ najnowszej instalacji Jarva). Ten plik dokłada tylko to, czego wiki Kernela wymaga
ponad skarbiec Jarva: `typ` i tag folderu z czesci.py, archiwum ze `status: nieaktualne`, huby `_hub.md`. TSV planu:
kolumny stara, nowa, akcja, cel, powod (akcje: przenies, scal, archiwum, hub; zostaje i korzen pomijane). `--repo`
przepisuje też odwołania `wiki/<stara>` w plikach repo poza wiki (md, json, sh, py, ts, js, txt).
`wykonaj` zapisuje plan w tools/porzadki-plan.tsv i raport w tools/porzadki-raport.md (oba w commicie); wymaga czystego
wiki/ i czystych plików repo, które przepisze (inaczej commit zabrałby cudzą pracę), i nie rusza niczego innego.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import czesci as C  # noqa: E402
from wiki import WIKI, REPO, AUTO_START, AUTO_END  # noqa: E402


def _katalog_wiedzy() -> str:
    kandydaci = [os.environ.get("JARVO_WIEDZA", ""), str(Path.home() / "dev" / "JARVO" / "wiedza")]
    kandydaci += sorted((str(p.parent) for p in (Path.home() / ".local/share/jarvo/program/app").glob("*/wiedza/wiedza.py")),
                        key=lambda s: Path(s).stat().st_mtime, reverse=True)
    return next((k for k in kandydaci if k and (Path(k) / "wiedza.py").is_file()), kandydaci[1])


sys.path.insert(0, _katalog_wiedzy())
import wiedza as W  # noqa: E402

ARCH = "archiwum"
DZIS = dt.date.today().isoformat()
REPO_SUFIKSY = {".md", ".json", ".sh", ".py", ".ts", ".js", ".txt"}
REPO_POMIN = {"wiki", "node_modules", ".git", "vendor", "dist", "build", ".svelte-kit"}


def skarbiec() -> "W.Skarbiec":
    return W.Skarbiec(WIKI, Path(tempfile.gettempdir()) / "wiki-porzadki-stan")


# ---- frontmatter: zmiany w miejscu (linie `klucz: wartość`), bez przepisywania reszty nagłówka
def fm_ustaw(tekst: str, zmiany: dict[str, str]) -> str:
    if not tekst.startswith("---\n") or (koniec := tekst.find("\n---\n", 4)) < 0:
        return tekst
    linie = tekst[4:koniec].split("\n")
    for k, v in zmiany.items():
        i = next((i for i, l in enumerate(linie) if re.match(rf"{re.escape(k)}\s*:", l)), None)
        if i is None:
            linie.append(f"{k}: {v}")
        else:
            linie[i] = f"{k}: {v}"
    return "---\n" + "\n".join(linie) + tekst[koniec:]


def fm_pole(tekst: str, k: str) -> str:
    m = re.search(rf"^{re.escape(k)}\s*:\s*(.*)$", tekst.split("\n---\n", 1)[0], re.M)
    return m.group(1).strip() if m else ""


def tagi_po(tekst: str, stary: str, nowy: str) -> str:
    tagi = [t.strip() for t in fm_pole(tekst, "tags").strip("[]").split(",") if t.strip()]
    tagi = [nowy] + [t for t in tagi if t not in (stary, nowy)]
    return "[" + ", ".join(tagi) + "]"


def dopasuj_do_czesci(rel: str, stary_folder: str, extra: dict[str, str] | None = None) -> None:
    """Przeniesiona notatka: `typ` części, tag folderu zamiast tagu dawnego folderu, bez linku do huba dawnego folderu
    (bez_linku_huba)."""
    p = WIKI / f"{rel}.md"
    t = p.read_text(encoding="utf-8")
    folder = rel.split("/", 1)[0]
    zmiany = {"typ": C.CZESCI[folder]["typ"], "tags": tagi_po(t, stary_folder, folder), **(extra or {})}
    p.write_text(bez_linku_huba(fm_ustaw(t, zmiany), stary_folder), encoding="utf-8")


# ---- operacje
def przenies_wiele(mapa: dict[str, str], dodatkowe: dict[str, dict] | None = None,
                   przekieruj: dict[str, str] | None = None, repo: bool = False) -> dict:
    """Notatki stara → nowa jednym przebiegiem wiedza.przenies_notatki (linki we wszystkich notatkach), potem typ i tagi."""
    for s, n in mapa.items():
        cz = n.split("/", 1)[0]
        if cz not in C.CZESCI:
            raise ValueError(f"`{n}`: `{cz}` nie jest częścią z czesci.py")
    wynik = W.przenies_notatki(skarbiec(), mapa, przekieruj=przekieruj)
    for s, n in mapa.items():
        dopasuj_do_czesci(n, s.split("/", 1)[0], (dodatkowe or {}).get(s))
    if repo:
        wynik["repo"] = przepisz_repo({s: (przekieruj or {}).get(s) or n for s, n in mapa.items()})
    return wynik


def archiwum_dla(s: str) -> str:
    return f"{ARCH}/{s.rsplit('/', 1)[-1]}"


def archiwizuj(sciezki: list[str], powod: str, nastepca: str = "", repo: bool = False) -> dict:
    if not powod.strip():
        raise ValueError("podaj powód")
    if nastepca and not (WIKI / f"{nastepca}.md").is_file():
        raise ValueError(f"następca `{nastepca}` nie istnieje")
    dod = {"status": "nieaktualne", "wycofano": DZIS, "powod": " ".join(powod.split())}
    if nastepca:
        dod["zastapiona_przez"] = nastepca
    return przenies_wiele({s: archiwum_dla(s) for s in sciezki}, {s: dod for s in sciezki},
                          {s: nastepca for s in sciezki} if nastepca else None, repo)


def _czesci_tresci(tekst: str) -> tuple[str, str, str, str]:
    """(tytuł, streszczenie, treść bez tytułu/streszczenia/Powiązanych, frontmatter)."""
    fm, body = (tekst.split("\n---\n", 1) + [""])[:2] if tekst.startswith("---\n") else ("", tekst)
    m = re.search(r"^# (.+)$", body, re.M)
    tytul = m.group(1).strip() if m else ""
    reszta = body[m.end():] if m else body
    s = re.match(r"\s*\*\*(.+?)\*\*[ \t]*\n", reszta)
    stresz = s.group(1).strip() if s else ""
    reszta = reszta[s.end():] if s else reszta
    reszta = re.split(r"^## Powiązane[ \t]*$", reszta, maxsplit=1, flags=re.M)[0].strip()
    return tytul, stresz, reszta, fm


def scal(b: str, a: str, bez_tresci: bool = False, powod: str = "", repo: bool = False) -> dict:
    """B do A: treść B (bez tytułu i Powiązanych) jako sekcja A przed „## Powiązane”, źródła B dopisane do A,
    B do archiwum (`zastapiona_przez: A`), linki do B prowadzą do A."""
    pa, pb = WIKI / f"{a}.md", WIKI / f"{b}.md"
    if not pa.is_file() or not pb.is_file():
        raise ValueError(f"nie ma `{a}` albo `{b}`")
    tb = pb.read_text(encoding="utf-8")
    ta = pa.read_text(encoding="utf-8")
    if not bez_tresci:
        tytul, stresz, reszta, _ = _czesci_tresci(tb)
        blok = f"## Ze scalonej notatki: {tytul}\n\n" + (f"{stresz}\n\n" if stresz else "") + reszta + "\n\n"
        m = re.search(r"^## Powiązane[ \t]*$", ta, re.M)
        ta = (ta[:m.start()] + blok + ta[m.start():]) if m else ta.rstrip("\n") + "\n\n" + blok
        zr = "; ".join(x for x in (fm_pole(ta, "zrodlo"), fm_pole(tb, "zrodlo")) if x)
        ta = fm_ustaw(ta, {"zrodlo": zr, "aktualizacja": DZIS})
        pa.write_text(ta, encoding="utf-8")
    return archiwizuj([b], powod or f"scalona z {a}", a, repo)


def przepisz_repo(cele: dict[str, str], sucho: bool = False) -> dict:
    """`wiki/<stara>.md` i `wiki/<stara>` w plikach repo poza wiki → nowa ścieżka. `sucho`: tylko lista plików."""
    if not cele:
        return {"pliki": 0, "zamian": 0, "lista": []}
    wzor = re.compile(r"wiki/(" + "|".join(re.escape(s) for s in sorted(cele, key=len, reverse=True)) + r")(?=\.md|[^\w/-]|$)")
    lista, zamian = [], 0
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in REPO_POMIN and not (Path(root) == REPO and d == WIKI.name)]
        for f in files:
            p = Path(root) / f
            if p.suffix not in REPO_SUFIKSY or p.stat().st_size > 2_000_000:
                continue
            try:
                t = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            nowy, ile = wzor.subn(lambda m: "wiki/" + cele[m.group(1)], t)
            if ile:
                if not sucho:
                    p.write_text(nowy, encoding="utf-8")
                lista.append(p.relative_to(REPO).as_posix())
                zamian += ile
    return {"pliki": len(lista), "zamian": zamian, "lista": lista}


# ---- huby
def zasiej() -> list[str]:
    nowe = []
    for folder, d in C.CZESCI.items():
        hub = WIKI / folder / "_hub.md"
        if hub.exists():
            continue
        hub.parent.mkdir(parents=True, exist_ok=True)
        rejestry = [k for k, cz in C.KORZEN.items() if cz == folder]
        linki = "".join(f"- [[{r}]]\n" for r in rejestry)
        hub.write_text(
            f"---\ntyp: hub\ntags: [{folder}, hub]\naktualizacja: {DZIS}\nzrodlo: wiki/tools/czesci.py; wiki/tools/wiki.py index\n"
            f"status: aktualne\n---\n# {d['tytul']}\n\n**{d['opis']}.**\n\n"
            f"Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.\n\n"
            + (f"Rejestry tej części:\n{linki}\n" if linki else "")
            + f"{AUTO_START}\n{AUTO_END}\n", encoding="utf-8")
        nowe.append(f"{folder}/_hub")
    return nowe


def bez_linku_huba(tekst: str, stary: str) -> str:
    """Link do huba dawnego folderu znika z notatki (punkt listy pusty po nim: cały punkt). Nowego linku do huba części
    nie dopisujemy: hub i tak listuje swoje notatki (wiki.py index), a nazwa części w linku („[[optymalizacje/_hub|Speedupy
    i optymalizacje]]”) dopasowywała każde pytanie z tym słowem do każdej notatki części. Pomiar 22.11 na kopii (34 i 22
    pytania, hit@5): z takim linkiem 0,912 → 0,882 i 0,909 → 0,864, bez niego 0,912 i 0,909 jak przed porządkami."""
    if not stary:
        return tekst
    tekst = re.sub(rf"(?:hub:\s*)?\[\[{re.escape(stary)}/_hub(?:\|[^\]]*)?\]\][ \t]*[,;·]?[ \t]*", "", tekst)
    return re.sub(r"^[ \t]*[-*][ \t]*\n", "", tekst, flags=re.M)


def napraw_huby() -> dict:
    """Hub dawnego folderu (folder spoza czesci.py bez notatek): linki do niego (index.md, notatki, które zostały) →
    hub części-następcy, plik huba usunięty, pusty folder też."""
    sk = skarbiec()
    zbior, znane = sk.mapa()
    stare = {}
    for d in sorted(p for p in WIKI.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name != "tools"):
        if d.name in C.CZESCI:
            continue
        reszta = [p for p in d.rglob("*.md") if p.name != "_hub.md"]
        if not reszta and (d / "_hub.md").exists() and d.name in C.DAWNE:
            stare[f"{d.name}/_hub"] = f"{C.DAWNE[d.name]}/_hub"
    out = {"usuniete_huby": sorted(stare), "linki": 0}
    if stare:
        rozw = lambda c: sk.rozwiaz(c, znane, zbior)  # noqa: E731
        for rel in sorted(zbior - set(stare)):
            p = sk.plik(rel)
            t = p.read_text(encoding="utf-8")
            nowy, ile = W.przepisz_linki(t, stare, rozw, {})
            if ile:
                p.write_text(nowy, encoding="utf-8")
                out["linki"] += ile
        for h in stare:
            (WIKI / f"{h}.md").unlink()
            try:
                (WIKI / h.split("/")[0]).rmdir()
            except OSError:
                pass
    return out


def streszczenie(czesc: str, tekst: str) -> str:
    hub = WIKI / czesc / "_hub.md"
    if not hub.is_file():
        raise ValueError(f"nie ma huba `{czesc}/_hub.md`")
    tekst = "\n".join(l.rstrip() for l in tekst.strip().splitlines())
    if not tekst or len(tekst) > W.MAX_STRESZCZENIA_HUBA or "<!--" in tekst:
        raise ValueError(f"streszczenie: od 1 do {W.MAX_STRESZCZENIA_HUBA} znaków, bez komentarzy HTML")
    if (sekret := W.zawiera_sekret(tekst)):
        raise ValueError(f"streszczenie zawiera sekret ({sekret})")
    t = hub.read_text(encoding="utf-8")
    fm, body = t.split("\n---\n", 1)
    body = W.wstaw_streszczenie(body, tekst)
    hub.write_text(fm_ustaw(fm + "\n---\n", {"streszczono": DZIS, "aktualizacja": DZIS}) + body, encoding="utf-8")
    return f"{czesc}/_hub"


# ---- plan z TSV
def wczytaj_plan(plik: Path) -> list[dict]:
    linie = plik.read_text(encoding="utf-8").splitlines()
    naglowek = linie[0].split("\t")
    return [dict(zip(naglowek, l.split("\t"))) for l in linie[1:] if l.strip()]


def wykonaj_plan(plik: Path, akcje: set[str], tylko: set[str], limit: int, repo: bool, sucho: bool) -> dict:
    wiersze = [w for w in wczytaj_plan(plik) if w["akcja"] in akcje and (not tylko or w["stara"] in tylko)]
    wiersze = [w for w in wiersze if (WIKI / f"{w['stara']}.md").is_file()]       # już zrobione: pomijane
    if limit:
        wiersze = wiersze[:limit]
    przen = {w["stara"]: w["cel"] for w in wiersze if w["akcja"] == "przenies"}
    scal_ = [(w["stara"], w["cel"], w["powod"]) for w in wiersze if w["akcja"] == "scal"]
    arch = [(w["stara"], w["cel"], w["powod"]) for w in wiersze if w["akcja"] == "archiwum"]
    if sucho:
        return {"przenies": len(przen), "scal": len(scal_), "archiwum": len(arch), "sucho": True}
    zasiej()
    out = {"przenies": 0, "scal": 0, "archiwum": 0, "linkow": 0}
    if przen:
        r = przenies_wiele(przen, repo=repo)
        out["przenies"], out["linkow"] = r["przeniesione"], r["linkow"]
    stare_na_nowe = {w["stara"]: w["cel"] for w in wczytaj_plan(plik) if w["akcja"] in ("przenies", "zostaje")}
    for b, a, powod in scal_:
        a = a if (WIKI / f"{a}.md").is_file() else next((s for s, n in stare_na_nowe.items() if n == a), a)
        r = scal(b, a, powod=powod, repo=repo)
        out["scal"] += 1
        out["linkow"] += r["linkow"]
    for s, nast, powod in arch:
        nast = nast if (WIKI / f"{nast}.md").is_file() else next((x for x, n in stare_na_nowe.items() if n == nast), "")
        r = archiwizuj([s], powod, nast, repo)
        out["archiwum"] += 1
        out["linkow"] += r["linkow"]
    if "hub" in akcje:
        out["huby"] = napraw_huby()
    return out


# ---- jedno polecenie: plan z reguł, raport, wykonanie, lint, commit, cofnięcie
ZNAK = "porządki wiki:"
PLIK_PLANU, PLIK_RAPORTU = TOOLS / "porzadki-plan.tsv", TOOLS / "porzadki-raport.md"


def _git(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)


def _brudne(sciezki: list[str]) -> list[str]:
    """Zmienione albo nieśledzone pliki (bez planu i raportu porządków) wśród ścieżek repo."""
    r = _git("status", "--porcelain", "--untracked-files=all", "--", *sciezki)
    wlasne = {PLIK_PLANU.relative_to(REPO).as_posix(), PLIK_RAPORTU.relative_to(REPO).as_posix()}
    return [l[3:] for l in r.stdout.splitlines() if l[3:] not in wlasne]


def przeglad(wiersze: list[dict]) -> dict:
    """Co zrobi plan: akcje, części przed i po, konflikty, pliki repo do przepisania i ich stan w git."""
    import collections
    istnieje = lambda rel: (WIKI / f"{rel}.md").is_file()          # noqa: E731
    akcje = collections.Counter(w["akcja"] for w in wiersze)
    przed = collections.Counter(w["stara"].split("/")[0] if "/" in w["stara"] else "(korzeń)" for w in wiersze
                                if not w["stara"].endswith("/_hub"))
    po = collections.Counter("(korzeń)" if w["akcja"] == "korzen" else ARCH if w["akcja"] in ("scal", "archiwum")
                             else w["nowa"].split("/")[0] for w in wiersze if w["akcja"] != "hub" and not w["stara"].endswith("/_hub"))
    bledy = []
    for w in wiersze:
        if w["akcja"] == "przenies" and istnieje(w["cel"]):
            bledy.append(f"cel przenosin już istnieje: {w['stara']} → {w['cel']}")
        if w["akcja"] == "przenies" and w["cel"].split("/")[0] not in C.CZESCI:
            bledy.append(f"`{w['cel']}`: część spoza czesci.py")
    cele = {w["stara"]: w["cel"] for w in wiersze if w["akcja"] in ("przenies", "scal", "archiwum") and w["cel"]}
    cele |= {w["stara"]: archiwum_dla(w["stara"]) for w in wiersze if w["akcja"] == "archiwum" and not w["cel"]}
    repo = przepisz_repo(cele, sucho=True)
    brudne = _brudne(["wiki"]) + _brudne(repo["lista"]) if (REPO / ".git").exists() else ["(repo bez git)"]
    return {"akcje": dict(akcje), "przed": dict(sorted(przed.items())), "po": dict(sorted(po.items())), "bledy": bledy,
            "repo": repo, "brudne": brudne}


def raport(wiersze: list[dict], p: dict, wynik: dict | None = None) -> str:
    l = [f"# Porządki wiki: {'wykonane' if wynik else 'plan (na sucho)'} {DZIS}", "",
         "Akcje: " + ", ".join(f"{k} {v}" for k, v in sorted(p["akcje"].items())), "",
         "| część | przed | po |", "|---|---|---|"]
    for cz in sorted(set(p["przed"]) | set(p["po"])):
        l.append(f"| {cz} | {p['przed'].get(cz, 0)} | {p['po'].get(cz, 0)} |")
    l += ["", f"Pliki repo poza wiki z odwołaniami do przenoszonych notatek: {p['repo']['pliki']} "
              f"({p['repo']['zamian']} odwołań): " + ", ".join(p["repo"]["lista"][:40])]
    l += ["", "Scalenia (B → A):"] + [f"- {w['stara']} → {w['cel']}: {w['powod']}" for w in wiersze if w["akcja"] == "scal"]
    l += ["", "Archiwum:"] + [f"- {w['stara']} (następca: {w['cel'] or 'brak'}): {w['powod']}" for w in wiersze
                             if w["akcja"] == "archiwum"]
    import plan_porzadkow as P
    if P.OSTRZEZENIA:
        l += ["", "Ostrzeżenia planu:"] + [f"- {o}" for o in P.OSTRZEZENIA]
    if p["bledy"]:
        l += ["", "BŁĘDY (nic nie zostanie zrobione):"] + [f"- {b}" for b in p["bledy"]]
    if p["brudne"]:
        l += ["", "Niezacommitowane pliki, których dotknie porządek (najpierw commit albo stash, potem jeszcze raz):"]
        l += [f"- {b}" for b in p["brudne"][:60]]
    if wynik:
        l += ["", f"Wynik: {wynik}"]
    l += ["", "Pełny plan: tools/porzadki-plan.tsv (stara, nowa, akcja, cel, powód)."]
    return "\n".join(l) + "\n"


def wykonaj(sucho: bool) -> int:
    import plan_porzadkow as P
    wiersze = P.plan(WIKI)
    P.zapisz_tsv(wiersze, PLIK_PLANU)
    p = przeglad(wiersze)
    zmian = sum(v for k, v in p["akcje"].items() if k in ("przenies", "scal", "archiwum", "hub"))
    if sucho or p["bledy"] or (p["brudne"] and zmian):
        tekst = raport(wiersze, p)
        PLIK_RAPORTU.write_text(tekst, encoding="utf-8")
        print(tekst)
        return 1 if p["bledy"] or (p["brudne"] and zmian and not sucho) else 0
    if not zmian:
        print("Plan pusty: wiki już jest w częściach z tools/czesci.py.")
        return 0
    start = _git("rev-parse", "HEAD").stdout.strip()
    dotkniete = ["wiki", *p["repo"]["lista"]]

    def cofnij_zmiany(powod: str) -> int:
        _git("checkout", start, "--", *dotkniete)
        _git("clean", "-fdq", "-e", PLIK_PLANU.name, "-e", PLIK_RAPORTU.name, "--", "wiki")
        print(f"COFNIĘTE ({powod}): wiki i pliki repo jak w {start[:9]}.", file=sys.stderr)
        return 1

    try:
        wynik = wykonaj_plan(PLIK_PLANU, {"przenies", "scal", "archiwum", "hub"}, set(), 0, repo=True, sucho=False)
        wynik.pop("_mapa", None)
    except Exception as e:                       # noqa: BLE001 (każdy błąd w trakcie = stan sprzed porządków)
        return cofnij_zmiany(f"{type(e).__name__}: {e}")
    for krok in (["index"], ["lint"]):
        r = subprocess.run([sys.executable, str(TOOLS / "wiki.py"), *krok], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-1000:], file=sys.stderr)
            return cofnij_zmiany(f"wiki.py {krok[0]}: kod {r.returncode}")
        wynik[krok[0]] = (r.stdout.strip().splitlines() or [""])[-1]
    PLIK_RAPORTU.write_text(raport(wiersze, p, wynik), encoding="utf-8")
    _git("add", "-A", "--", *dotkniete)
    tytul = (f"{ZNAK} {wynik['przenies']} przeniesionych, {wynik['scal']} scalonych, {wynik['archiwum']} w archiwum, "
             f"{p['repo']['pliki']} plików repo (tools/porzadki.py wykonaj)")
    r = _git("commit", "-q", "-m", tytul, "-m", "Raport: wiki/tools/porzadki-raport.md. Cofnięcie: python3 tools/porzadki.py cofnij.")
    if r.returncode:
        print(r.stdout + r.stderr, file=sys.stderr)
        return cofnij_zmiany("git commit")
    print(PLIK_RAPORTU.read_text(encoding="utf-8"))
    print(f"Commit: {_git('rev-parse', '--short', 'HEAD').stdout.strip()} „{tytul}”. Cofnięcie: python3 tools/porzadki.py cofnij")
    return 0


def cofnij() -> int:
    for linia in _git("log", "-n", "200", "--format=%H\t%s").stdout.splitlines():
        sha, _, temat = linia.partition("\t")
        if temat.startswith(ZNAK):
            if _brudne(["wiki"]):
                print("wiki/ ma niezacommitowane zmiany: najpierw commit albo stash.", file=sys.stderr)
                return 1
            r = _git("revert", "--no-edit", sha)
            print((r.stdout + r.stderr).strip() or f"cofnięto {sha[:9]} „{temat}”")
            return r.returncode
    print("Nie ma commitu porządków do cofnięcia.", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Porządki wiki Kernela (adapter na wiedza.py)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("wykonaj")
    p.add_argument("--sucho", action="store_true")
    sub.add_parser("cofnij")
    sub.add_parser("zasiej")
    p = sub.add_parser("plan")
    p.add_argument("tsv", type=Path)
    p.add_argument("--akcje", default="przenies,scal,archiwum,hub")
    p.add_argument("--tylko", default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--repo", action="store_true")
    p.add_argument("--sucho", action="store_true")
    p = sub.add_parser("przenies")
    p.add_argument("stara")
    p.add_argument("czesc")
    p.add_argument("--repo", action="store_true")
    p = sub.add_parser("scal")
    p.add_argument("b")
    p.add_argument("a")
    p.add_argument("--bez-tresci", action="store_true")
    p.add_argument("--repo", action="store_true")
    p = sub.add_parser("archiwizuj")
    p.add_argument("sciezki", nargs="+")
    p.add_argument("--powod", required=True)
    p.add_argument("--nastepca", default="")
    p.add_argument("--repo", action="store_true")
    sub.add_parser("napraw-huby")
    p = sub.add_parser("streszczenie")
    p.add_argument("czesc")
    p.add_argument("tekst")
    a = ap.parse_args()
    if a.cmd == "wykonaj":
        return wykonaj(a.sucho)
    if a.cmd == "cofnij":
        return cofnij()
    try:
        if a.cmd == "zasiej":
            r = zasiej()
        elif a.cmd == "plan":
            r = wykonaj_plan(a.tsv, set(a.akcje.split(",")), {x for x in a.tylko.split(",") if x}, a.limit, a.repo, a.sucho)
        elif a.cmd == "przenies":
            s = W._norm(a.stara)
            r = przenies_wiele({s: f"{a.czesc}/{s.rsplit('/', 1)[-1]}"}, repo=a.repo)
        elif a.cmd == "scal":
            r = scal(W._norm(a.b), W._norm(a.a), a.bez_tresci, repo=a.repo)
        elif a.cmd == "archiwizuj":
            r = archiwizuj([W._norm(s) for s in a.sciezki], a.powod, W._norm(a.nastepca) if a.nastepca else "", a.repo)
        elif a.cmd == "napraw-huby":
            r = napraw_huby()
        else:
            r = streszczenie(a.czesc, a.tekst)
    except ValueError as e:
        print(f"błąd: {e}", file=sys.stderr)
        return 1
    if isinstance(r, dict):
        r.pop("_mapa", None)
    print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
