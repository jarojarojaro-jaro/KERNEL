#!/usr/bin/env python3
"""Tabele zbiorcze z pól frontmattera (nie ręcznie): najlepsze wyniki model × karta, bilans optymalizacji.

  python3 tools/tabele.py            # pisze tabele (bloki TABELE w notatkach) i wypisuje błędy pól
  python3 tools/tabele.py --sucho    # tylko sprawdza pola i mówi, co by zmienił

Pola (tools/czesci.py, `pola` części; wartości bez „: ” w środku):
  model: qwen3-8-27b                  nazwa notatki modelu (modele/<model>.md)
  karta: rx-7900-xtx                  nazwa notatki karty (karty/<karta>.md)
  wynik: <model> | <karta> | <liczba> <jednostka> | <metryka>; <warunki> | <RRRR-MM-DD>
  wyniki:                             kilka wyników w jednej notatce, każdy jak `wynik`
    - <model> | <karta> | … 
  technika: <krótka nazwa>            optymalizacja, kernel, łatka
  werdykt: przyjete | odrzucone | w-toku
  zysk: +5,6% fill 255k (466,3 → 492,5 t/s)
  dowod: <notatka albo plik:wiersz>   k: K-080 (pozycja w KOLEJKA-TESTOW)

Wynik:
  testy/najlepsze-wyniki.md               najlepszy wynik każdej trójki (model, karta, metryka) ze źródłem i warunkami
  optymalizacje/bilans-optymalizacji.md   techniki według werdyktu: zysk, karta, model, K, dowód
  modele/<model>.md, karty/<karta>.md     blok „Wyniki z notatek” z wierszami tego modelu albo tej karty
Bloki między <!-- TABELE:START --> i <!-- TABELE:END --> pisze tylko ten skrypt; reszta notatki jest ręczna.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import czesci as C  # noqa: E402
from wiki import WIKI, load_notes  # noqa: E402

START, END = "<!-- TABELE:START -->", "<!-- TABELE:END -->"
NAJLEPSZE = "testy/najlepsze-wyniki"
BILANS = "optymalizacje/bilans-optymalizacji"
MNIEJ_LEPIEJ = {"ms", "s", "gib", "mib", "gb", "w", "ms/krok", "ms/tok"}
WERDYKT_TYTUL = {"przyjete": "Przyjęte (w produkcji albo w przepisie)", "w-toku": "W toku",
                 "odrzucone": "Odrzucone (z powodem w notatce)"}
DZIS = dt.date.today().isoformat()


def lista_pola(text: str, klucz: str) -> list[str]:
    """Punkty listy blokowej `klucz:` z frontmattera (wiki.py czyta tylko linie `klucz: wartość`)."""
    if not text.startswith("---\n") or (k := text.find("\n---\n", 4)) < 0:
        return []
    out, w = [], False
    for linia in text[4:k].splitlines():
        if re.match(rf"{re.escape(klucz)}\s*:\s*$", linia):
            w = True
        elif w and re.match(r"\s+-\s+", linia):
            out.append(re.sub(r"^\s+-\s+", "", linia).strip().strip("'\""))
        elif w and linia.strip():
            w = False
    return out


def wynik(tekst: str, notatka: str, bledy: list[str]) -> dict | None:
    cz = [c.strip() for c in tekst.split("|")]
    if len(cz) != 5:
        bledy.append(f"{notatka}: wynik ma {len(cz)} pól zamiast 5 (model | karta | liczba jednostka | metryka; warunki | data)")
        return None
    m = re.match(r"([+-]?\d+(?:[.,]\d+)?)\s*(.*)$", cz[2])
    if not m:
        bledy.append(f"{notatka}: wynik bez liczby: {cz[2]}")
        return None
    metryka, _, warunki = cz[3].partition(";")
    if not re.match(r"\d{4}-\d{2}-\d{2}$", cz[4]):
        bledy.append(f"{notatka}: data wyniku nie w formacie RRRR-MM-DD: {cz[4]}")
    return {"model": cz[0], "karta": cz[1], "wartosc": float(m.group(1).replace(",", ".")), "liczba": m.group(1),
            "jednostka": m.group(2).strip(), "metryka": metryka.strip(), "warunki": warunki.strip(), "data": cz[4],
            "notatka": notatka}


def zbierz():
    notes = [n for n in load_notes() if not n.is_hub and not n.rel.startswith("archiwum/")]
    nazwy = {n.name: n for n in notes}
    bledy: list[str] = []
    uwagi: list[str] = []
    wyniki, optym = [], []
    for n in notes:
        if n.rel[:-3] in (NAJLEPSZE, BILANS):
            continue
        teksty = ([n.meta["wynik"]] if n.meta.get("wynik") else []) + lista_pola(n.text, "wyniki")
        for t in teksty:
            w = wynik(t, n.name, bledy)
            if w:
                for pole in ("model", "karta"):
                    if w[pole] not in nazwy:
                        uwagi.append(f"{n.rel}: {pole} `{w[pole]}` bez notatki (dopisz modele/ albo karty/{w[pole]}.md)")
                wyniki.append(w)
        if n.meta.get("werdykt") or n.meta.get("technika"):
            werdykt = n.meta.get("werdykt", "")
            if werdykt not in C.WERDYKTY:
                bledy.append(f"{n.rel}: werdykt `{werdykt}` spoza {C.WERDYKTY}")
            optym.append({"notatka": n.name, "tytul": n.title, "technika": n.meta.get("technika") or n.title,
                          "werdykt": werdykt, "zysk": n.meta.get("zysk", ""), "karta": n.meta.get("karta", ""),
                          "model": n.meta.get("model", ""), "k": n.meta.get("k", ""), "dowod": n.meta.get("dowod", ""),
                          "streszczenie": n.summary})
    return notes, nazwy, wyniki, optym, bledy, uwagi


def najlepsze(wyniki: list[dict]) -> list[dict]:
    best: dict[tuple, dict] = {}
    for w in wyniki:
        klucz = (w["model"], w["karta"], w["metryka"].lower(), w["jednostka"].lower())
        mniej = w["jednostka"].lower() in MNIEJ_LEPIEJ
        b = best.get(klucz)
        if b is None or (w["wartosc"] < b["wartosc"] if mniej else w["wartosc"] > b["wartosc"]) \
                or (w["wartosc"] == b["wartosc"] and w["data"] > b["data"]):
            best[klucz] = w
    return sorted(best.values(), key=lambda w: (w["model"], w["karta"], w["metryka"].lower()))


def _krotko(nazwy: dict, x: str) -> str:
    """Krótki tytuł notatki modelu albo karty (bez nawiasów i dopisku po dwukropku) albo sam identyfikator."""
    n = nazwy.get(x)
    return re.split(r"\s*[(:]", n.title)[0].strip() if n else x


def _nazwa(nazwy: dict, x: str) -> str:
    """Komórka tabeli: link bez etykiety (`|` etykiety rozbiłby tabelę Markdown), krótki tytuł obok dla wyszukiwania."""
    return f"{_krotko(nazwy, x)} [[{x}]]" if x in nazwy else x


def _kom(s: str) -> str:
    return (s or "").replace("|", "/").replace("\n", " ").strip()


def tabela_wynikow(rows: list[dict], nazwy: dict, bez: str = "") -> list[str]:
    kol = [k for k in ("model", "karta") if k != bez]
    out = ["| " + " | ".join(kol + ["metryka", "najlepszy", "warunki", "data", "źródło"]) + " |",
           "|" + "---|" * (len(kol) + 5)]
    for w in rows:
        out.append("| " + " | ".join([_nazwa(nazwy, w[k]) for k in kol]
                                     + [_kom(w["metryka"]), f"**{w['liczba']} {w['jednostka']}**", _kom(w["warunki"]),
                                        w["data"], f"[[{w['notatka']}]]"]) + " |")
    return out


def blok_najlepszych(best: list[dict], nazwy: dict) -> str:
    linie = [f"Wygenerowano {DZIS} przez `tools/tabele.py` z pól `wynik`/`wyniki` {len(best)} trójek; "
             "poprawiaj notatkę źródłową, nie tę tabelę.", ""]
    for model in sorted({w["model"] for w in best}):
        rows = [w for w in best if w["model"] == model]
        linie += [f"## {_krotko(nazwy, model)}: najlepsze wyniki na kartach", ""]
        linie += tabela_wynikow(rows, nazwy, bez="model") + [""]
    return "\n".join(linie)


def blok_bilansu(optym: list[dict], nazwy: dict) -> str:
    linie = [f"Wygenerowano {DZIS} przez `tools/tabele.py` z pól `technika`, `werdykt`, `zysk`, `dowod` ({len(optym)} "
             "technik); poprawiaj notatkę techniki, nie tę tabelę.", ""]
    for werdykt in C.WERDYKTY:
        rows = sorted((o for o in optym if o["werdykt"] == werdykt), key=lambda o: o["technika"].lower())
        if not rows:
            continue
        linie += [f"## {WERDYKT_TYTUL[werdykt]} ({len(rows)})", "",
                  "| technika | zysk | karta | model | K | dowód | notatka |", "|---|---|---|---|---|---|---|"]
        for o in rows:
            dowod = o["dowod"]
            dowod = f"[[{dowod}]]" if dowod and "/" not in dowod.split(":")[0] and dowod in nazwy else _kom(dowod)
            linie.append(f"| {_kom(o['technika'])} | {_kom(o['zysk'])} | {_kom(o['karta'])} | {_kom(o['model'])} | "
                         f"{_kom(o['k'])} | {dowod} | [[{o['notatka']}]] |")
        linie.append("")
    return "\n".join(linie)


def wstaw(tekst: str, blok: str) -> str:
    b = f"{START}\n{blok.rstrip()}\n{END}"
    if START in tekst and END in tekst:
        pre, rest = tekst.split(START, 1)
        return pre + b + rest.split(END, 1)[1]
    m = re.search(r"^## Powiązane[ \t]*$", tekst, re.M)
    return (tekst[:m.start()] + b + "\n\n" + tekst[m.start():]) if m else tekst.rstrip("\n") + "\n\n" + b + "\n"


def notatka_zbiorcza(rel: str, tytul: str, stresz: str, tags: str, powiazane: list[str], blok: str) -> str:
    folder = rel.split("/")[0]
    p = WIKI / f"{rel}.md"
    if p.exists():
        return wstaw(p.read_text(encoding="utf-8"), blok)
    linki = "\n".join(f"- {x}" for x in [f"[[{folder}/_hub|{C.CZESCI[folder]['tytul']}]]", *powiazane])
    return (f"---\ntyp: {C.CZESCI[folder]['typ']}\ntags: [{folder}, {tags}]\naktualizacja: {DZIS}\n"
            f"zrodlo: wiki/tools/tabele.py (pola frontmattera notatek)\nstatus: aktualne\n---\n# {tytul}\n\n**{stresz}**\n\n"
            f"{START}\n{blok.rstrip()}\n{END}\n\n## Powiązane\n{linki}\n")


def generuj(sucho: bool = False) -> dict:
    """Tabele z pól (bez wypisywania): {zmienione, bledy, uwagi, wynikow, najlepszych, technik}. Woła je też
    `wiki.py index`, więc tabela nadąża za notatkami bez osobnego kroku."""
    notes, nazwy, wyniki, optym, bledy, uwagi = zbierz()
    best = najlepsze(wyniki)
    pliki: dict[str, str] = {}
    if best:
        pliki[NAJLEPSZE] = notatka_zbiorcza(
            NAJLEPSZE, "Najlepsze wyniki: model × karta (tabela z notatek)",
            "Najlepszy zmierzony wynik każdej pary model i karta dla każdej metryki, z warunkami, datą i notatką źródłową; "
            "generuje tools/tabele.py.", "wyniki, rekordy, tabela", ["[[REKORDY]]", "[[KOLEJKA-TESTOW]]"],
            blok_najlepszych(best, nazwy))
    if optym:
        pliki[BILANS] = notatka_zbiorcza(
            BILANS, "Bilans optymalizacji: przyjęte, w toku, odrzucone (tabela z notatek)",
            "Każda technika, kernel i łatka z werdyktem, zyskiem, kartą, modelem i dowodem; generuje tools/tabele.py.",
            "speedupy, werdykty, tabela", ["[[KOLEJKA-TESTOW]]", "[[wyniki-negatywne]]"], blok_bilansu(optym, nazwy))
    for n in notes:
        pole = "model" if n.folder == "modele" else "karta" if n.folder == "karty" else ""
        if not pole:
            continue
        ident = n.meta.get(pole) or n.name
        rows = [w for w in best if ident and w[pole] == ident]
        if not rows and START not in n.text:
            continue
        blok = [f"## Wyniki z notatek ({len(rows)})", "",
                f"Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, {DZIS}); pełna tabela: "
                f"[[najlepsze-wyniki]].", ""]
        blok += tabela_wynikow(rows, nazwy, bez=pole) if rows else ["Brak wyników z polami."]
        if pole == "karta":
            techs = [o for o in optym if o["karta"] == ident]
            if techs:
                blok += ["", "Optymalizacje na tej karcie ([[bilans-optymalizacji]]): " + "; ".join(
                    f"[[{o['notatka']}|{_kom(o['technika'])}]] ({o['werdykt']}{', ' + _kom(o['zysk']) if o['zysk'] else ''})"
                    for o in techs) + "."]
        pliki[n.rel[:-3]] = wstaw(n.text, "\n".join(blok))
    zmienione = []
    for rel, tekst in pliki.items():
        p = WIKI / f"{rel}.md"
        if not p.exists() or p.read_text(encoding="utf-8") != tekst:
            zmienione.append(rel)
            if not sucho:
                p.write_text(tekst, encoding="utf-8")
    return {"zmienione": zmienione, "bledy": bledy, "uwagi": uwagi, "wynikow": len(wyniki), "najlepszych": len(best),
            "technik": len(optym)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sucho", action="store_true")
    a = ap.parse_args()
    r = generuj(a.sucho)
    for b in r["bledy"]:
        print("BŁĄD POLA", b)
    for u in r["uwagi"]:
        print("UWAGA", u)
    print(f"wyników {r['wynikow']} (najlepszych trójek {r['najlepszych']}), technik {r['technik']}, "
          f"{'do zmiany' if a.sucho else 'zmienione'} {len(r['zmienione'])}: {', '.join(r['zmienione']) or '-'}")
    return 1 if r["bledy"] else 0


if __name__ == "__main__":
    sys.exit(main())
