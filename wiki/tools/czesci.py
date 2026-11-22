"""Jedna definicja części wiki Kernela (folder → typ, tytuł, opis, wygląd, dawne foldery, pola tabel).

Czytają ją: tools/wiki.py (FOLDERS: lint, index, huby), tools/porzadki.py (przenosiny, scalanie, streszczenia hubów),
tools/tabele.py (tabele zbiorcze z pól frontmattera) i tools/site/build.py (kategorie, kolory, nawigacja).
Nowa część = nowy wpis tutaj + `porzadki.py zasiej` (folder z hubem) + `wiki.py index`.
"""
from __future__ import annotations

# folder → opis części. Kolejność = kolejność w index.md, na stronie i w przypomnieniu hubów.
#   typ      wartość `typ:` notatek w folderze (lint pilnuje zgodności)
#   tytul    nagłówek huba i etykieta na stronie;  opis: jedno zdanie do index.md i huba
#   dawne    foldery sprzed porządków 2026-11 (mapowanie w kernel-wiki-co-gdzie.tsv)
#   grupa    sekcja nawigacji strony;  ikona, kolor: wygląd na stronie (assets/icons.svg)
#   pola     pola frontmattera, z których tabele.py składa tabele zbiorcze części
#   recall   False = poza przypomnieniem sesji (archiwum; mozg_sesji: dopisz folder do `pomin`)
CZESCI: dict[str, dict] = {
    "decyzje": dict(typ="decyzja", tytul="Decyzje", grupa="Decyzje i zasady", ikona="flag", kolor="#ff7a1a",
                    opis="Decyzje i korekty właściciela: wiążą i mają pierwszeństwo przed resztą wiki",
                    dawne=["decyzje"]),
    "modele": dict(typ="model", tytul="Modele", grupa="Modele", ikona="cube", kolor="#a99bff",
                   opis="Jedna notatka na model (też drafter, kwant): rozmiar, kwant, gdzie działa, najlepsze wyniki",
                   dawne=["modele"], pola=["model", "rozmiar", "kwant", "karty"]),
    "llm": dict(typ="llm", tytul="LLM: trening i jakość", grupa="Modele", ikona="flask", kolor="#c38bff",
                opis="Trening, dostrajanie, edycje wag i jakość modeli (poza optymalizacją silnika)",
                dawne=["llm"]),
    "karty": dict(typ="karta", tytul="Karty, maszyny i chmura", grupa="Sprzęt i stos", ikona="chip", kolor="#e3a07a",
                  opis="Jedna notatka na kartę, maszynę albo dostawcę chmury: parametry, sufity, stan, najlepsze wyniki",
                  dawne=["karty", "chmura"], pola=["karta", "vram", "pasmo", "gdzie", "stan"]),
    "stos": dict(typ="stos", tytul="Silnik i stos GPU", grupa="Sprzęt i stos", ikona="layers", kolor="#ff5f6d",
                 opis="Nasz fork llama.cpp i gałęzie, ROCm/HIP/PM4/KFD, CUDA, sterowniki i architektury",
                 dawne=["rocm", "nvidia"]),
    "optymalizacje": dict(typ="optymalizacja", tytul="Speedupy i optymalizacje", grupa="Wyniki", ikona="zap",
                          kolor="#4ecdc4",
                          opis="Jedna notatka na technikę, kernel albo łatkę: werdykt (przyjete, odrzucone, w-toku), zysk, dowód",
                          dawne=["kernele", "latki"], pola=["technika", "werdykt", "zysk", "dowod", "karta", "model", "k"]),
    "testy": dict(typ="test", tytul="Testy i pomiary", grupa="Wyniki", ikona="checks", kolor="#f5b841",
                  opis="Eksperymenty i pomiary z datą (warunki, wynik, przyrost) i metoda pomiaru; kolejka w KOLEJKA-TESTOW",
                  dawne=["eksperymenty"], pola=["model", "karta", "wynik", "warunki", "wyniki", "k"]),
    "metody": dict(typ="metoda", tytul="Metody pracy", grupa="Decyzje i zasady", ikona="book", kolor="#6fd08c",
                   opis="Jak pracujemy: playbook, bramki poprawności, fabryka, dowód z profilu",
                   dawne=["metody"]),
    "lekcje": dict(typ="lekcja", tytul="Lekcje", grupa="Decyzje i zasady", ikona="bulb", kolor="#ffd84d",
                   opis="Lekcje z błędów: objaw, przyczyna, jak robić poprawnie",
                   dawne=["lekcje"]),
    "research": dict(typ="research", tytul="Research i źródła", grupa="Research i źródła", ikona="filesearch",
                     kolor="#7f8cff",
                     opis="Raporty, zwiady i linki od właściciela z werdyktem; rejestr przebadanych źródeł w ZRODLA",
                     dawne=["research"]),
    "ekosystem": dict(typ="ekosystem", tytul="Ekosystem: silniki, repo, firmy", grupa="Research i źródła",
                      ikona="users", kolor="#c9a27e",
                      opis="Cudze silniki i repozytoria, konkurencja, firmy i ludzie: jedna notatka na podmiot",
                      dawne=["repo", "ludzie-firmy"]),
    "produkt": dict(typ="produkt", tytul="Produkt", grupa="Produkt", ikona="package", kolor="#ff8fa3",
                    opis="Enigma: plan produktu, strona, aplikacja, przepisy per klasa VRAM",
                    dawne=["produkt"]),
    "narzedzia": dict(typ="narzedzie", tytul="Narzędzia", grupa="Narzędzia", ikona="wrench", kolor="#52c7e8",
                      opis="Nasze skrypty i narzędzia: pomiar, bramki, kolejka GPU, chmura, wiki",
                      dawne=["narzedzia"]),
    "archiwum": dict(typ="archiwum", tytul="Archiwum", grupa="Narzędzia", ikona="history", kolor="#8a8580",
                     opis="Notatki scalone i wycofane (status nieaktualne, pole zastapiona_przez); poza przypomnieniem",
                     dawne=[], recall=False),
}

# Pliki w korzeniu (rejestry, nie części): zostają na miejscu, linkują je huby części.
KORZEN = {"KOLEJKA-TESTOW": "testy", "REKORDY": "testy", "ZRODLA": "research", "AUDYT": "", "KONWENCJE": "",
          "log": "", "index": ""}

# Wartości pól tabel (frontmatter; jedna linia `klucz: wartość`, lista `wyniki:` jako punkty `  - …`).
WERDYKTY = ("przyjete", "odrzucone", "w-toku")

FOLDERS: dict[str, tuple[str, str]] = {f: (d["typ"], d["opis"]) for f, d in CZESCI.items()}
DAWNE: dict[str, str] = {stary: f for f, d in CZESCI.items() for stary in d.get("dawne", [])}
POZA_PRZYPOMNIENIEM = tuple(f for f, d in CZESCI.items() if d.get("recall") is False)

# Na czas przenosin (porzadki.py plan): dawne foldery, które jeszcze mają notatki, przechodzą lint ze swoim typem.
# Po ostatniej przenosinie i `porzadki.py napraw-huby` folderów już nie ma i słownik nic nie dodaje: wtedy go usuń.
PRZEJSCIOWE: dict[str, tuple[str, str]] = {
    "chmura": ("chmura", "Wynajem GPU (przenoszone do karty/)"), "rocm": ("rocm", "Stos AMD (przenoszone do stos/)"),
    "nvidia": ("nvidia", "Stos NVIDIA (przenoszone do stos/)"), "kernele": ("kernel", "Kernele (przenoszone do optymalizacje/)"),
    "latki": ("latka", "Łatki (przenoszone do optymalizacje/)"), "eksperymenty": ("eksperyment", "Eksperymenty (przenoszone do testy/)"),
    "repo": ("repo", "Repozytoria (przenoszone do ekosystem/ i stos/)"), "ludzie-firmy": ("firma", "Firmy (przenoszone do ekosystem/)"),
}


def foldery(wiki) -> dict[str, tuple[str, str]]:
    """FOLDERS dla wiki.py: części plus dawne foldery, które jeszcze istnieją na dysku (przenosiny w toku)."""
    return FOLDERS | {f: v for f, v in PRZEJSCIOWE.items() if (wiki / f).is_dir()}
