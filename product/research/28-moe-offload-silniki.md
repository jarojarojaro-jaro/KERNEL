# 28 — Silniki MoE-offload: TideLM, Xolotl (linia 0xBakeer)

Data: 2026-10-20. Czytane (tylko README/docs przez raw/API, nic nie klonowane, nic nie uruchamiane):
TideLM `raspy135/tideLM@92e1b186` (README, docs/adaptive-experts.md, docs/decode-dynamic-depth.md,
docs/gotchas.md — 134 sekcje, RESULTS.md), Xolotl `Indras-Mirror/Xolotl@c3324f89` (README, README.strata.md,
docs/xolotl/BENCHMARKS.md), przodek `0xBakeer/deepseek-v41-flash-spark@45a0caff` (tylko drzewo plików).
Project Maya pominięty (ZRODLA wiersz 49).

## Werdykt w skrócie

**Oba silniki są stratne z założenia.** Ich prędkości biorą się z tego, że model nie liczy tych ekspertów,
których wybrałby router (TideLM podstawia eksperta rezydentnego, Xolotl przesuwa routing biasem w stronę VRAM),
oraz z kwantyzacji 2–3 bit. Przy dokładnym routingu Xolotl sam podaje **~3,5 tok/s**. Dla naszych modeli
(gęsty 27B i LFM w całości w VRAM) offload nie daje nic. Z rzeczy przenośnych zostają: dynamiczna głębokość
draftu, cache prefiksów na dysku i lista odrzuconych eksperymentów.

## Tabela

| źródło | deklaracja | zweryfikowane? | bezstratne? | dla nas teraz | dla produktu później |
|---|---|---|---|---|---|
| TideLM (2× DGX Spark) | DS-V4.1-Flash 25,9/42,8 tok/s (proza/kod), GLM-5.3 12–19 tok/s | spójne z ich własnymi logami bench; 66% ekspertów rezydentnych, MXFP4; spekulacja DSpark/MTP daje ×2 (22→44 tok/s na pythonie, decode-dynamic-depth) | **NIE**: braki zastępowane „next-best resident”; własny pomiar GLM: **KL 0,11–0,17, top-1 ~89%** względem modelu dokładnego; same „hot reads” obniżają KL o 42%, ale nie do zera | dynamiczna głębokość MTP (bezstratna), prefiksy na dysku | wzorzec: uczony zbiór rezydentny + adaptacja; jako tryb bezstratny to tylko polityka cache |
| Xolotl (fork Strata, RTX 4090 + 90 GB DDR4) | 552B DS-V4.1 26,8 tok/s; Qwen3.8-Flash-Next 127,8; Qwen3.8-27B 98,5 | arytmetyka zgadza się tylko przy biasie: ~38 ms/token = ~19 ms część gęsta Q8 + eksperci prawie wyłącznie z VRAM-LRU (1,3–1,6 tys. z 15 360); **dokładny routing = 3,5 tok/s** (ich README.strata) | **NIE**: `--route-bias 1.0`, `--route-bias-file 0.6` domyślnie; ppl na kodzie 2,38 → 2,87; quant GSQ ~2,4 bpw (152 GiB / 552B); 27B to IQ3_S | 27B 98,5 tok/s to IQ3_S, więc nieporównywalne z naszym bezstratnym | nie do kopiowania, bo stratny; wartościowy jako punkt odniesienia konkurencji |
| 0xBakeer ds-v41-flash-spark | baza TideLM (te same pliki: gotchas, keep-sets, tune) | – | keep-sets = przycinanie (stratne) | nic | nic |

### Arytmetyka pasma (czy 27 tok/s jest realne)

- DS-V4.1: 152 GiB / 552B ≈ 2,4 bpw. Aktywne ≈ 6 z 384 ekspertów × 40 warstw + część gęsta. [INFERENCE] ~20–30B aktywnych,
  czyli **~6–9 GB na token**. Przy 27 tok/s daje to 160–240 GB/s. Mieści się w VRAM 4090 (1 TB/s), ale nie w PCIe 4.0 x16 (~25 GB/s).
  27 tok/s wymaga więc, by niemal wszystko trafiało w VRAM, a to zapewnia bias routera. Po wyłączeniu biasu
  ~3,5 tok/s ≈ 25 GB/s / ~7 GB (PCIe-bound). Liczby są spójne, a źródłem prędkości jest **zmiana modelu**, nie inżynieria.
- **Górna granica bezstratna** dla Podkrętu (24 GB VRAM + 64 GB RAM, PCIe4):
  `tok/s ≤ B_miss / bajty_chybień_na_token`, gdzie dla ekspertów liczonych na CPU B_miss ≈ pasmo RAM (DDR5 2-kan. ~60–80 GB/s),
  a dla ekspertów przesyłanych na GPU ≈ PCIe (~25 GB/s).
  Przykład [INFERENCE]: MoE ~125B z ~10B aktywnych w Q4 (~5,6 GB/token). Przy 50% trafień w VRAM zostaje ~2,8 GB/token
  z RAM liczone na CPU, czyli **≤ ~20–25 tok/s**. DS-Flash 552B w Q4 (~300 GB) nie mieści się w 64 GB RAM, więc idzie z NVMe
  (~5–7 GB/s) i daje **< 2 tok/s**. Spekulacja MTP pomaga przy MoE mniej, bo weryfikacja k tokenów dotyka więcej ekspertów.

## Techniki: co to da nam teraz (27B gęsty + MTP, LFM w VRAM, gfx1100)

| technika | efekt dla nas |
|---|---|
| Dynamiczna głębokość draftu (wybór 3/5 co 60 tokenów, próg 3% zysku, estymacja d5 z nasyconych kroków) | **jedyna realna**. Bezstratna (greedy identyczny). U nich: kod +21% (depth 5), proza depth 5 −10%, więc adaptacja daje ~max z obu. Dla 27B MTP: oczekuj +5–15% na mieszanym ruchu względem stałej głębokości [INFERENCE] |
| Cache prefiksów na dysku (O_DIRECT, segmenty przyrostowe) | 6K prefiks w 0,2 s zamiast 19 s u nich. U nas prefill 27B jest szybki, więc zysk tylko przy długich czatach wielosesyjnych. llama-server ma `--slot-save-path`, wystarczy go podłączyć |
| LOOP_BREAK (wyklucza token, który powtarza cykl 12. raz) | **zmienia rozkład**, gdy zadziała; ich pętle otwierały głównie podstawione eksperty. Dla nas nic, a łamałoby regułę bezstratności |
| KV FP8/FP4 | stratne (FP8 +0,002–0,005 NLL, FP4 KL +0,004–0,010). Pamięć KV dla 27B i tak nie jest u nas wąskim gardłem → nic |
| FP4 grouped-MoE kernel (Triton, GB10) | nic: gfx1100 nie ma FP4, a LFM już ma fuzje MoE (wiki/kernele/fuzje-lfm-moe) |
| „chunk-invariant” referencja (`tools/v41_ref.py`) | lekcja: bit-exactness kończy się na 512 tokenach przez kafelkowanie cuBLAS. Nasz rygor „bezstratny” musi mierzyć KL/top-1 względem referencji, nie md5 przy innym chunku |

## Odrzucone eksperymenty (gotchas), które oszczędzają nam pracę

- „Skipping a missing expert costs more than substituting it”, „Top-p expert pruning 0,90 jest za darmo, 0,85 nie”: każde przycinanie ekspertów jest mierzalnie stratne. Nie wracamy do tego dla LFM.
- „Dense fp4/fp8 head buy ~5% decode and cost structure”: lm_head w FP8 nie wchodzi.
- „A wider verify block makes utilization better and decode slower”, „Skipping DSpark can save a pass and lose throughput”, „Markov candidate shortlists cost acceptance”: nie poszerzać bloku weryfikacji ponad horyzont trenowania MTP, nie skracać słownika draftu.
- „Profiler overstates small kernels ~10x”, „One boot per arm cannot resolve a 2 ms change”: zgodne z naszą metodyką A/B.
- „A per-request timestamp in the prompt defeats the exact-match prefix cache”: zastosowanie do szablonów czatu Podkrętu.

## Akcje (ranking)

1. **Dynamiczna głębokość MTP dla Qwen3.8-27B** w naszym llama.cpp: polityka z `engine/spec_depth.py` (TideLM). Najpierw tani pomiar stałych głębokości 1–5 na kodzie i prozie na XTX.
2. Podłączyć zapis/odczyt slotów KV na dysku w Podkręcie (wieloczatowość). Niski koszt.
3. Do estymatora (raport 04 §3.2): wzór na górną granicę bezstratnego MoE-offload powyżej. Komunikat produktowy: „duże MoE z offloadem tylko bezstratnie, czyli ~kilka–20 tok/s”.
4. Nie portować niczego z route-bias, podstawiania, LOOP_BREAK ani KV FP4.

## Do bazy wiedzy

- Xolotl 27 tok/s na 4090 = bias routingu do VRAM + quant ~2,4 bpw; dokładny routing 3,5 tok/s (ppl kod 2,38 → 2,87).
- TideLM: podstawianie brakujących ekspertów, GLM KL 0,11–0,17 / top-1 ~89% względem dokładnego; rezydencja jest największą dźwignią jakości.
- Dynamiczna głębokość draftu (3/5) jest bezstratna; depth 5 wygrywa na kodzie (+21%), przegrywa na prozie (−10%).
- Górna granica bezstratnego offloadu: tok/s ≤ pasmo (RAM ~70 / PCIe ~25 / NVMe ~6 GB/s) ÷ bajty chybionych ekspertów na token.
- Bit-exactness przy zmianie chunku/kafelka GEMM nie istnieje; do weryfikacji „bezstratności” używać KL/top-1.
