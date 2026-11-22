#!/usr/bin/env python3
"""Plan porządków wiki Kernela: „co gdzie” (TSV), duplikaty, kandydaci na sprzeczności i nieaktualne.

    python3 tools/plan_porzadkow.py mapa [--tsv plan.tsv]       # każda notatka: stara → nowa / scal / archiwum
    python3 tools/plan_porzadkow.py duplikaty [--prog 0.30]     # pary TF-IDF + grupy o tym samym źródle
    python3 tools/plan_porzadkow.py nieaktualne                 # „aktualne”, a treść wskazuje stan sprzed zmian
    python3 tools/plan_porzadkow.py liczby plan.tsv             # notatki na część przed i po

Reguły: folder → część z tools/czesci.py (DAWNE), potem wyjątki per notatka (WYJATKI: inna część), SCAL (B → A: treść B
dopisana do A, B do archiwum, linki do B prowadzą do A) i ARCHIWUM (wycofana, linki do następcy). Plan liczy się od
nowa przy każdym `porzadki.py wykonaj`, więc nowe notatki trafiają do części same; po porządkach (dawnych folderów już
nie ma) plan jest pusty. Reguła dla notatki, której już nie ma, to ostrzeżenie, nie błąd. Tylko stdlib.
"""
from __future__ import annotations

import argparse
import collections
import math
import re
import sys
from pathlib import Path

# ---- wyjątki od reguły folderu: stara ścieżka → (nowa część, powód)
WYJATKI: dict[str, tuple[str, str]] = {}


def _w(czesc: str, powod: str, *sciezki: str) -> None:
    for s in sciezki:
        WYJATKI[s] = (czesc, powod)


_w("modele", "notatka o modelu (jedna notatka na model)",
   "llm/daisyrose-27b", "llm/inkling-2-mini", "llm/sensenova-loop-9b", "repo/rsr-27b", "nvidia/nvfp4")
_w("narzedzia", "nasze skrypty chmury to narzędzie", "chmura/harness-chmurowy")
_w("karty", "parametry kart do rachunków: część kart", "nvidia/karty-nvidia-parametry")
_w("testy", "wyniki pomiarów z datą", "nvidia/nvidia-wyniki-2026-10-16")
_w("optymalizacje", "technika przyspieszenia z werdyktem", "nvidia/latki-na-nvidia", "nvidia/fa-kv-kwantyzowane-cuda",
   "nvidia/l2-persist", "rocm/trwala-siatka-bez-pm4")
# metody: pomiar → testy, techniki → optymalizacje, reszta zostaje
_w("testy", "metoda pomiaru, zestaw albo metryka (część testów)",
   "metody/pomiar-abba", "metody/ms-na-krok", "metody/zestaw-copy-mvs", "metody/zestaw-odlozony", "metody/metryka-prozy-e0",
   "metody/jakosc-mini", "metody/evalplus-jakosc-kodu", "metody/kld-po-polsku", "metody/xtxbench-szybki-ab",
   "metody/sweep-wariantow-kernela", "metody/mikrobench-granicy-kernela", "metody/skill-io-metodyka", "metody/aob-v1",
   "metody/koszt-szerokosci-weryfikacji", "metody/ksztalt-ruchu-agentowego", "metody/sufit-pasma-i-mapa-czasu",
   "metody/skill-io-sufity")
_w("optymalizacje", "technika przyspieszenia (jedna notatka na technikę)",
   "metody/agr-lookup-zgodny-z-mtp", "metody/akv-cache-agentow", "metody/drzewo-weryfikacji-gdn-wy",
   "metody/fly-stratna-weryfikacja", "metody/glowica-draftu-rerank", "metody/kontroler-szerokosci-draftu",
   "metody/prog-draftu-od-kosztu-wiersza", "metody/sprzezone-probkowanie-draftu", "metody/strata-kva",
   "metody/siatka-checkpointow-gdn", "metody/strumien-on-wyrocznia", "metody/wspolny-poczatek-promptu",
   "metody/dcq-kotwica-stanu-gdn", "metody/budzet-megakernela-qwen-xtx", "metody/model-kosztu-weryfikacji-moe",
   "metody/skill-io-dzwignie", "metody/jak-przyspieszylismy-nvidia")
# produkt: techniki i silnik poza planem produktu
_w("optymalizacje", "technika z werdyktem (K-085, K-081, opóźnienia topki)",
   "produkt/cache-sesji-na-dysku", "produkt/tryb-stratny-pflash", "produkt/opoznienia-ttft")
_w("stos", "funkcja naszego silnika (topka)", "produkt/bezpieczenstwo-tokenow-specjalnych")
_w("testy", "metoda i wynik benchmarku Enigmy", "produkt/enigma-uczciwy-benchmark")
# research: wyniki z kart → testy, próby jednej techniki → optymalizacje, narzędzia → narzedzia
_w("testy", "raport z wynikami pomiarów na kartach (część testów)",
   "research/benchmarki-przed-po-2026-10-19", "research/raport-09-chmura-3060", "research/raport-09-chmura-3090",
   "research/raport-09-chmura-5060ti", "research/raport-26-kolejka-gpu", "research/raport-27-3090-final",
   "research/raport-29-4060ti", "research/raport-31-3060-3080", "research/raport-31-3090", "research/raport-31-4060ti",
   "research/raport-31-4070ti", "research/raport-31-5060ti", "research/raport-35-xtx-eksperymenty",
   "research/raport-56-orca-3090", "research/raport-wyniki-xtx-2026-10-19", "research/raport-24e-nvidia-runda",
   "research/raport-43-integracja", "research/raport-16f-xtx-szybkie", "research/raport-21a-dspine",
   "research/raport-36-xtx-roadmap", "research/raport-37-proza-100", "research/raport-40-akceptacja-prozy")
_w("optymalizacje", "próba jednej techniki z werdyktem (przyjęta albo odrzucona)",
   "research/raport-24b-draft-pelny-slownik", "research/raport-24c-wiele-zapytan", "research/raport-24d-lfm-lookup",
   "research/raport-24f-mmvq-fa", "research/raport-24h-kv-jeden-przebieg", "research/raport-24i-sciezka-agenta",
   "research/raport-24j-router", "research/raport-24k-koszt-weryfikacji", "research/raport-24l-fuzja-norm",
   "research/raport-24m-weryfikacja-gpu", "research/raport-24n-mmvq-n5", "research/raport-24o-luki-hosta",
   "research/raport-24p-sprzezone-t1", "research/raport-24q-adaptacyjna-spekulacja", "research/raport-24r-mmvq-pasmo",
   "research/raport-24s-drzewa-proza", "research/raport-24t-entropia-wag", "research/raport-24u-norm-quant",
   "research/raport-24v-prefill-fa", "research/raport-24w-pair2", "research/raport-38-ckpt-vram",
   "research/raport-44-spec-route", "research/raport-46-mmvq-big", "research/raport-48-norma-gdn-bank",
   "research/raport-49-mmvq-ogon-1024", "research/raport-50a-mmvq-q4k", "research/raport-50b-mmvq-q5k",
   "research/raport-50c-mmvq-q6k", "research/raport-50d-mmvq-iq4xs", "research/raport-51-male-kernele",
   "research/raport-53-draft-shortlist", "research/raport-54-mniej-granic", "research/raport-65-vram-rezerwa-mtp")
_w("narzedzia", "raport o naszym narzędziu", "research/raport-25-buildfarm", "research/raport-47-kernel-lab")
# repo: nasze gałęzie i fork → stos (reszta repo to cudze: ekosystem)
_w("stos", "nasz fork llama.cpp albo jego gałąź",
   "repo/amd-opt", "repo/amd-opt-v070", "repo/batch-invariant", "repo/cuda-v070", "repo/galezie-rund",
   "repo/llama-cpp-fork", "repo/mtp-train", "repo/nemotron-3090", "repo/opt-gdn6", "repo/opt-mmq6", "repo/opt-qwen5",
   "repo/opt-samp", "repo/tools6")

# ---- scalenia: B → A (stare ścieżki obu); treść B dopisana do A, B do archiwum, linki do B prowadzą do A
SCAL: dict[str, tuple[str, str]] = {
    "ludzie-firmy/firma-vast-ai": ("chmura/vast-ai", "ten sam dostawca dwa razy (firma i chmura)"),
    "ludzie-firmy/firma-runpod": ("chmura/runpod", "ten sam dostawca dwa razy (firma i chmura)"),
    "ludzie-firmy/firma-salad": ("chmura/salad", "ten sam dostawca dwa razy (firma i chmura)"),
    "ludzie-firmy/firma-magnitude": ("repo/magnitude", "ten sam konkurent dwa razy (firma i repo)"),
    "repo/cuda-compat-galaz": ("nvidia/cuda-compat", "ta sama gałąź cuda-compat dwa razy"),
    "chmura/harness-chmurowy": ("narzedzia/skrypty-chmury", "te same skrypty ~/qwen-opt/cloud dwa razy"),
    "produkt/produkt-analiza-platformy": ("metody/analiza-platformy", "analiza platformy dwa razy (plan i metoda)"),
    "research/raport-11-mtp-pl-pilot": ("eksperymenty/2026-10-16-mtp-pl-pilot", "ten sam raport 11 dwa razy"),
    "research/raport-12-bit-exact": ("eksperymenty/2026-10-16-bit-exact", "ten sam raport 12 dwa razy"),
    "research/raport-13-rocm-10-1": ("rocm/rocm-10-1", "ten sam raport 13 dwa razy"),
    "research/raport-14-nemotron-3090": ("eksperymenty/2026-10-16-nemotron-3090", "ten sam raport 14 dwa razy"),
    "research/raport-16a-pm4-pdl": ("eksperymenty/2026-10-18-pm4-pdl-x1", "ten sam raport 16a dwa razy"),
    "research/raport-16b-lookup-tail": ("eksperymenty/2026-10-18-lookup-ogon", "ten sam raport 16b dwa razy"),
    "research/raport-16c-kvq-cuda": ("eksperymenty/2026-10-16-kvq-cuda", "ten sam raport 16c dwa razy"),
    "research/raport-16d-magnitude-vs-nasz": ("eksperymenty/2026-10-16-magnitude-vs-fork", "ten sam raport 16d dwa razy"),
    "research/raport-16e-kwanty-kld": ("eksperymenty/2026-10-18-e1-kwanty-27b-kld", "ten sam raport 16e dwa razy"),
    "research/raport-16g-lfm-moe-pasmo": ("eksperymenty/2026-10-18-lfm-moe-pasmo", "ten sam raport 16g dwa razy"),
    "research/raport-16h-fabryka-v1": ("metody/fabryka-v1", "ten sam raport 16h dwa razy"),
    "research/raport-16j-magnitude-vulkan-xtx": ("eksperymenty/2026-10-18-magnitude-vulkan-xtx", "ten sam raport 16j dwa razy"),
    "research/raport-16k-sprzezone-probkowanie": ("eksperymenty/2026-10-18-sprzezone-probkowanie-mtp",
                                                  "ten sam raport 16k dwa razy"),
    "research/raport-17-gpu-page-fault": ("eksperymenty/2026-10-19-page-faulty-gpu-analiza", "ten sam raport 17 dwa razy"),
    "research/raport-19-kb-wyszukiwanie": ("narzedzia/kb", "raport 19 opisuje narzędzie kb"),
    "research/raport-20-build-topka": ("eksperymenty/2026-10-19-build-topka", "ten sam raport 20 dwa razy"),
    "research/raport-21j-flameox": ("repo/flameox", "repo i raport o nim to jeden podmiot"),
    "research/raport-21k-smokinggun": ("repo/smokinggun", "repo i raport o nim to jeden podmiot"),
    "research/raport-23b2-bariery-lds": ("research/raport-23b-re-kernele-amd", "druga część tego samego RE kerneli AMD"),
    "research/raport-23f-podrecznik-gpu": ("metody/podrecznik-gpu", "podręcznik GPU dwa razy"),
    "research/raport-24a-bariera-lds": ("kernele/bariera-lds-rdna3", "ta sama technika (bariera tylko LDS) dwa razy"),
    "research/raport-32b-deepinfer": ("repo/deepinfer", "repo i raport o nim to jeden podmiot"),
    "research/raport-32e-safe-special": ("produkt/bezpieczenstwo-tokenow-specjalnych", "SAFE_SPECIAL dwa razy"),
    "research/raport-39f-nvidia-flare": ("repo/nvidia-flare", "repo i raport o nim to jeden podmiot"),
    "research/raport-45-opoznienia": ("produkt/opoznienia-ttft", "opóźnienia topki dwa razy"),
    "research/raport-52-eagle4": ("repo/eagle-4", "repo i raport o nim to jeden podmiot"),
    "research/raport-67-kampania-nvidia": ("eksperymenty/2026-11-07-kampania-nvidia-vast", "kampania 67 dwa razy"),
    "research/runda-6-raporty": ("eksperymenty/runda-6", "runda 6 dwa razy"),
    "nvidia/nvidia-wyniki-2026-10-16": ("eksperymenty/2026-10-16-kampania-nvidia", "ta sama kampania 2026-10-16 dwa razy"),
    "modele/qwen38-27b-inferencex": ("research/raport-21f-inferencex", "wpis InferenceX to część raportu 21f, nie model"),
}

# ---- archiwum: wycofane, linki prowadzą do następcy (stara → (następca albo "", powód))
ARCHIWUM: dict[str, tuple[str, str]] = {
    "eksperymenty/2026-10-19-plan-e1-rsr27b": ("KOLEJKA-TESTOW", "plan niewykonany, zastąpiony pozycją K-074"),
    "eksperymenty/2026-10-19-plan-retro-rsr-0070": ("KOLEJKA-TESTOW", "plan niewykonany, zastąpiony pozycją K-060"),
    "nvidia/backlog-testow-nvidia": ("KOLEJKA-TESTOW", "backlog ze stanem 2026-11-07, pozycje są w kolejce K-…"),
    "produkt/kv-na-dysku-polityka": ("decyzje/2026-10-19-kv-tylko-w-ram", "status nieaktualne, zastąpiona decyzją KV tylko w RAM"),
    # decyzje uchylone późniejszymi (żywa tura 22.11 dostała w przypomnieniu „nie testujemy na naszym XTX”):
    # archiwum = status nieaktualne + następca, poza przypomnieniem (pomin: archiwum)
    "decyzje/2026-10-16-bez-lokalnego-gpu": ("kernel-od-a-do-z", "uchylona: od 19.11 testy na XTX na polecenie JARO "
                                             "(mapa Kernela, „Czego nie robię bez zgody”; kolejka K-… na XTX)"),
    "decyzje/2026-10-15-zakaz-gpu-w-nocy": ("", "czasowy zakaz z 15.10 (od 00:45 do 02:00), minął tej samej nocy"),
    "decyzje/2026-10-16-saluki-bonsai-na-3060": ("decyzje/2026-11-14-saluki-usuniety", "Saluki usunięty 14.11"),
    "decyzje/2026-10-20-chmura-wstrzymana": ("chmura/vast-ai", "uchylona: od 17.11 testy na Vaście ze zgodą i budżetem "
                                             "JARO (K-114, K-118, Colab od 22.11)"),
}

KORZEN_PLIKI = {"KOLEJKA-TESTOW", "REKORDY", "ZRODLA", "AUDYT", "KONWENCJE", "log", "index"}


def czesci(wiki: Path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import czesci as C  # noqa: E402
    return C


OSTRZEZENIA: list[str] = []


def notatki(wiki: Path) -> list[str]:
    return sorted(p.relative_to(wiki).as_posix()[:-3] for p in wiki.rglob("*.md")
                  if not any(c.startswith(".") or c == "tools" for c in p.relative_to(wiki).parts))


def plan(wiki: Path) -> list[dict]:
    C = czesci(wiki)
    wszystkie = notatki(wiki)
    nowa_sciezka: dict[str, str] = {}
    for s in wszystkie:
        if "/" not in s:
            continue
        folder, nazwa = s.split("/", 1)
        czesc = WYJATKI.get(s, (C.DAWNE.get(folder, folder), ""))[0]
        nowa_sciezka[s] = f"{czesc}/{nazwa}"
    out = []
    for s in wszystkie:
        if "/" not in s:
            out.append(dict(stara=s, nowa=s, akcja="korzen", cel="",
                            powod="rejestr w korzeniu, zostaje (link z huba części)" if s in KORZEN_PLIKI else "korzeń"))
            continue
        folder, nazwa = s.split("/", 1)
        if nazwa == "_hub":
            nowy = C.DAWNE.get(folder, folder)
            akcja = "zostaje" if nowy == folder else "hub"
            out.append(dict(stara=s, nowa=f"{nowy}/_hub", akcja=akcja, cel=f"{nowy}/_hub",
                            powod="hub części" if akcja == "zostaje" else f"hub dawnego folderu: linki → {nowy}/_hub, plik usunięty"))
            continue
        if s in SCAL and SCAL[s][0] in nowa_sciezka and SCAL[s][0] not in SCAL and SCAL[s][0] not in ARCHIWUM:
            a, powod = SCAL[s]
            cel = nowa_sciezka[a]
            out.append(dict(stara=s, nowa=f"scal z {cel}", akcja="scal", cel=cel, powod=powod))
            continue
        if s in ARCHIWUM:
            nast, powod = ARCHIWUM[s]
            nast = nowa_sciezka.get(nast, nast) if nast in nowa_sciezka or "/" not in nast else ""
            out.append(dict(stara=s, nowa="archiwum", akcja="archiwum", cel=nast, powod=powod))
            continue
        nowa = nowa_sciezka[s]
        if s in WYJATKI:
            powod = WYJATKI[s][1]
        elif nowa == s:
            powod = f"część {folder} bez zmian"
        else:
            powod = f"folder {folder} → część {nowa.split('/')[0]}"
        out.append(dict(stara=s, nowa=nowa, akcja="zostaje" if nowa == s else "przenies", cel=nowa, powod=powod))
    znane = set(wszystkie)
    OSTRZEZENIA.clear()
    if any((wiki / f).is_dir() for f in C.DAWNE if f not in C.CZESCI):      # przed porządkami: reguły mają cel
        for d in (WYJATKI, SCAL, ARCHIWUM):
            OSTRZEZENIA.extend(f"reguła dla notatki, której nie ma: {s}" for s in d if s not in znane)
        OSTRZEZENIA.extend(f"scalenie {s} → {a} pominięte: celu nie ma albo sam jest scalany" for s, (a, _) in SCAL.items()
                           if s in znane and (a not in znane or a in SCAL or a in ARCHIWUM))
    return out


def zapisz_tsv(wiersze: list[dict], plik: Path) -> None:
    linie = ["stara\tnowa\takcja\tcel\tpowod"] + [f"{w['stara']}\t{w['nowa']}\t{w['akcja']}\t{w['cel']}\t{w['powod']}"
                                                   for w in wiersze]
    plik.write_text("\n".join(linie) + "\n", encoding="utf-8")


def cmd_mapa(a) -> int:
    wiersze = plan(a.wiki)
    if a.tsv:
        zapisz_tsv(wiersze, a.tsv)
    else:
        sys.stdout.write("stara\tnowa\takcja\tcel\tpowod\n" + "".join(
            f"{w['stara']}\t{w['nowa']}\t{w['akcja']}\t{w['cel']}\t{w['powod']}\n" for w in wiersze))
    licz = collections.Counter(w["akcja"] for w in wiersze)
    print(f"{len(wiersze)} notatek: " + ", ".join(f"{k} {v}" for k, v in sorted(licz.items())), file=sys.stderr)
    for o in OSTRZEZENIA:
        print("UWAGA", o, file=sys.stderr)
    return 0


def cmd_liczby(a) -> int:
    przed = collections.Counter(s.split("/")[0] if "/" in s else "(korzeń)" for s in notatki(a.wiki))
    po = collections.Counter()
    for linia in a.tsv.read_text(encoding="utf-8").splitlines()[1:]:
        stara, nowa, akcja, cel, _ = linia.split("\t")
        if akcja == "hub":
            continue
        klucz = "(korzeń)" if akcja == "korzen" else ("archiwum" if akcja in ("scal", "archiwum") else nowa.split("/")[0])
        po[klucz] += 1
    print("przed:", dict(sorted(przed.items())))
    print("po:", dict(sorted(po.items())), "razem", sum(po.values()))
    return 0


# ---- duplikaty
def _tokeny(t: str) -> list[str]:
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"\[\[[^\]]*\]\]", " ", t)
    return [w for w in re.findall(r"[a-ząćęłńóśźż0-9][a-ząćęłńóśźż0-9_.-]{2,}", t.lower()) if not w.replace(".", "").isdigit()]


def _tresci(wiki: Path) -> dict[str, tuple[dict, str]]:
    out = {}
    for s in notatki(wiki):
        if "/" not in s or s.endswith("/_hub"):
            continue
        t = (wiki / f"{s}.md").read_text(encoding="utf-8")
        fm = {}
        if t.startswith("---\n") and (k := t.find("\n---\n", 4)) > 0:
            for linia in t[4:k].splitlines():
                if ":" in linia and not linia.startswith((" ", "-")):
                    x, v = linia.split(":", 1)
                    fm[x.strip()] = v.strip()
            t = t[k + 5:]
        out[s] = (fm, t)
    return out


def cmd_duplikaty(a) -> int:
    tresci = _tresci(a.wiki)
    tf = {s: collections.Counter(_tokeny(t)) for s, (_, t) in tresci.items()}
    df = collections.Counter(w for c in tf.values() for w in c)
    n = len(tf)
    odwr = collections.defaultdict(list)
    for s, c in tf.items():
        v = {w: (1 + math.log(x)) * math.log(n / df[w]) for w, x in c.items() if df[w] < n * 0.3}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1
        for w, x in v.items():
            odwr[w].append((s, x / norma))
    pary = collections.Counter()
    for lst in odwr.values():
        if len(lst) > 60:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                x, y = sorted((lst[i][0], lst[j][0]))
                pary[(x, y)] += lst[i][1] * lst[j][1]
    print(f"## Pary podobnej treści (TF-IDF cosinus ≥ {a.prog})")
    for (x, y), v in sorted(pary.items(), key=lambda kv: -kv[1]):
        if v < a.prog:
            break
        print(f"{v:.2f}\t{x}\t{y}")
    print("\n## Grupy o tym samym pierwszym źródle (product/research/…)")
    grupy = collections.defaultdict(list)
    for s, (fm, _) in tresci.items():
        z = re.findall(r"product/research/([\w.+-]+?\.md)", fm.get("zrodlo", ""))
        if z:
            grupy[z[0]].append(s)
    for z, lst in sorted(grupy.items()):
        if len(lst) > 1:
            print(f"{z}\t{len(lst)}\t" + " ; ".join(lst))
    return 0


# ---- kandydaci na nieaktualne: status aktualne, a streszczenie albo początek treści mówi o stanie zastąpionym
# (wzorzec, opis, foldery: puste = wszystkie, data: tylko notatki z aktualizacją wcześniejszą)
ZASTAPIONE = [
    (r"produkc\w*[^.\n]{0,60}(amd-opt|run-llm\.sh|f61994f58|70 łatek)", "produkcja = amd-opt/run-llm.sh (od 2026-11-09 topka-q70)",
     (), "2026-11-09"),
    (r"(od 2026-11-05 produkcja|produkcja[^.\n]{0,30}topka-q63)", "produkcja = topka-q63 (od 2026-11-09 topka-q70)",
     (), "2026-11-09"),
    (r"\b109(\.0)? t/s\b[^.\n]{0,80}(rekord|najlep)|(rekord|najlep)\w*[^.\n]{0,80}\b109(\.0)? t/s",
     "rekord Qwen XTX 109 t/s (2026-11-05: 120.58 t/s spec_sweep T=1, REKORDY)", (), "2026-12-31"),
    (r"saluki", "Saluki usunięty 2026-11-14 (decyzja)", ("decyzje", "modele", "karty", "produkt"), "2026-11-14"),
]


def cmd_nieaktualne(a) -> int:
    for s, (fm, t) in sorted(_tresci(a.wiki).items()):
        if fm.get("status") != "aktualne":
            continue
        streszczenie = next((l for l in t.splitlines() if l.startswith("**")), "")
        for rx, opis, foldery, data in ZASTAPIONE:
            if (foldery and s.split("/")[0] not in foldery) or fm.get("aktualizacja", "") >= data:
                continue
            if re.search(rx, streszczenie, re.I) or re.search(rx, t[:1500], re.I):
                print(f"{s}\t{fm.get('aktualizacja', '')}\t{opis}")
                break
    return 0



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--wiki", type=Path, default=Path(__file__).resolve().parent.parent)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("mapa")
    p.add_argument("--tsv", type=Path)
    p = sub.add_parser("duplikaty")
    p.add_argument("--prog", type=float, default=0.30)
    sub.add_parser("nieaktualne")
    p = sub.add_parser("liczby")
    p.add_argument("tsv", type=Path)
    a = ap.parse_args()
    return {"mapa": cmd_mapa, "duplikaty": cmd_duplikaty, "nieaktualne": cmd_nieaktualne, "liczby": cmd_liczby}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
