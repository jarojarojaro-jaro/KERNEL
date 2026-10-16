---
typ: hub
tags: [eksperymenty, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Eksperymenty

**Rundy optymalizacji i kampanie pomiarowe z datą, warunkami i werdyktem.**

Werdykty: scalone / wycofane / negatywne. Wyniki negatywne zapisujemy, żeby do nich nie wracać bez nowego pomysłu.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (26)

- [[2026-10-09-pierwsze-pomiary|2026-10-09: pierwsze pomiary Qwen3.8-27B (59 → 92 t/s)]] — Pierwszy dzień: od starego buildu użytkownika (59.2 t/s) do 85.5 t/s na ROCm i 91.8 t/s na Vulkanie dzięki aktualizacji llama.cpp, wielokolumnowemu MMVQ, cache q8_1 i słownikowi draftu 64k.
- [[2026-10-10-sweep-mtp-dflash|2026-10-10: długość draftu MTP, temperatura i DFlash vs MTP]] — Sweep na Vulkanie przy 285 W: n=5 bez p_min zostaje dla MTP, temperatura prawie nie ma wpływu, a DFlash na szerszym zestawie nie jest szybszy od MTP (wcześniejsze „120 t/s” to był jeden prompt).
- [[2026-10-12-vulkan-krok-po-kroku|2026-10-12 (rano): Vulkan krok po kroku]] — Ostatnia runda pod Vulkan przed przejściem na ROCm: łatki MMVQ Vulkan skróciły krok o ~5%, adaptacyjna długość draftu nie dała nic.
- [[2026-10-12-cache-promptu-i-a7|2026-10-12: cache promptu, długi kontekst po `kvq` i testy bez zmian w kodzie (A7)]] — Cache promptu llama-server działa dobrze na domyślnych ustawieniach; testy flag bez zmian w kodzie (A7) dały szum, a `-ub 2048` kończył się OOM.
- [[2026-10-12-fuzje-a3-a6|2026-10-12: fuzje A3–A6 i draft MTP jednym grafem]] — Dzień fuzji na ROCm: liczba kerneli weryfikacji 2156 → 972, krok Qwena 41.7 → 35.67 ms (74.8 → 88.1 t/s).
- [[2026-10-12-rocm-vs-vulkan|2026-10-12: ROCm vs Vulkan — cały czas odpowiedzi i długi kontekst]] — Pomiar całego czasu odpowiedzi (prefill + 1000 tokenów) pokazał, że ROCm wygrywa wszędzie poza krótkimi promptami; po nim ROCm został stałym backendem.
- [[2026-10-12-mtp-trening-faza1|2026-10-12: trening głowicy MTP — faza 1 (wykonalność)]] — Sprawdziliśmy, czy samodestylacja głowicy MTP ma sens: dane, ekstraktor i lustro PyTorch działają, a pomiar akceptacji wskazuje +5–11% tok/krok; rekomendacja GO dla pilota 2 M tokenów.
- [[2026-10-13-k1-mmvq|2026-10-13: K1 — MMVQ wielokolumnowe pod RDNA3]] — Strojenie MMVQ do weryfikacji (buffer resource, waves_per_eu, DPP, GLC|DLC) skróciło krok Qwena 35.67 → 33.17 ms (88.1 → 94.7 t/s), bitowo identycznie.
- [[2026-10-13-k2-male-kernele|2026-10-13: K2 — małe kernele weryfikacji i draftu]] — Seria małych kerneli (para MMVQ, rms_norm i argmax z DPP, fuzje GDN) plus poprawka clamp q8_1: Qwen 33.17 → 32.14 ms/krok (97.8 t/s), bitowo identycznie.
- [[2026-10-13-k3-host|2026-10-13: K3 — narzut CPU w pętli spekulacji]] — Trzy zmiany po stronie hosta (asynchroniczne wejścia, osobny scheduler draftu, top-k bez pełnej tablicy) zdjęły ~1.1 ms z kroku: Qwen 30.97 ms/krok, 101.5 t/s.
- [[2026-10-13-k4-i-hw-queues|2026-10-13: K4 (weryfikacja 9–16 tokenów) i GPU_MAX_HW_QUEUES]] — Kernel WMMA dla 9–16 kolumn przyspieszył szeroką weryfikację, ale draft ≥ 8 dalej przegrywał przez osobny klif w SSM_CONV; zmienna `GPU_MAX_HW_QUEUES` (pomysł ze Straty) nic nie dała.
- [[2026-10-13-s2-s4|2026-10-13: S2 (draft IQ4_XS) i S4 (stan GDN z opóźnieniem)]] — Draft MTP w IQ4_XS i cofanie stanu GDN przez przeliczenie: Qwen 30.97 → 29.36 ms/krok (102.9 t/s), Uncensored → 28.27 ms/krok (106.1 t/s).
- [[lfm-runda-1|2026-10-14: LFM runda 1 (łatki 0048–0052)]] — Sampler kar, q8_1 z normy, fuzje shortconv i MoE down oraz 2 wiersze na blok w MMVQ: LFM tg128 197.4 → 220.4 t/s, serwer 172.9 → 218.6 t/s (+26%), bitowo identycznie.
- [[lfm-runda-2|2026-10-14: LFM runda 2 (0053–0054) i przejście na KV q8_0]] — Użytkownik zdecydował, że LFM używa KV q8_0; fuzje routera MoE i shortconv w in_proj dały tg128 221.3 → 244.1 t/s, bitowo identycznie.
- [[lfm-runda-3|2026-10-14: LFM runda 3 (0055–0059)]] — Kernel `kvq` dla KV q8_0 (jedyna zmiana numeryki, przyjęta po bramce KLD) plus trzy fuzje bitowe i zbiorczy upload: LFM przy 98k 152.4 → 191.4 t/s (+25.6%), przy 0 241.1 → 262.1.
- [[lfm-baza|2026-10-14: LFM2.5-24B-A2B — pomiar bazowy]] — Pierwszy pomiar LFM2.5 na naszym forku: 173 t/s w czacie, a łatki z kampanii Qwena same dały +17% względem upstreamu (tg128 169.3 → 198.3).
- [[2026-10-14-prefill-k5-t3|2026-10-14: prefill (K5 + T3) oraz S3 i koszty hosta (0047)]] — Runda prefillu dała +5–15% szybsze wczytywanie długich promptów przy tych samych logitach; okno uwagi MTP (S3) okazało się negatywne, a koszty hosta w pętli spekulacji zeszły z 236 do 6 µs.
- [[lfm-runda-4-pm4|2026-10-14: runda 4 — replay PM4 (0060–0064)]] — Odtwarzanie grafu dekodowania jako bufora PM4 skróciło granicę kernela z ~2.75 do ~0.5–0.9 µs: LFM 259.3 → 293.6 t/s, Qwen MTP 103.7 → 108.8 t/s, bitowo identycznie.
- [[2026-10-14-t1-t2-draft|2026-10-14: T1 (historia conv z opóźnieniem) i T2 (adaptacyjna długość draftu)]] — T1 usunęło klif przy drafcie ≥ 8 (bitowo), ale głębsze drafty i tak nie są szybsze; T2 (długość wyceniana kosztem) nie pobiło stałego n=4, więc zostało opt-in.
- [[qwen-runda-5|2026-10-15: Qwen runda 5 (gałąź opt-qwen5) — same wyniki negatywne]] — Runda 5 nie dała łatki: GDN fast nie był bitowy, podwójny bufor MMQ zwalniał, szeroki blok DFlash był wolniejszy; za to ablacja MMQ wskazała epilog jako prawdziwe ograniczenie prefillu.
- [[runda-6|2026-10-15: runda 6 — epilog MMQ, GDN fast, narzędzia]] — Trzy gałęzie przygotowane offline i zmierzone w oknie GPU: epilog MMQ scalony (+2.2% pp4096 Qwena), GDN fast bitowy, ale w szumie (nie scalony), narzędzia LOO / kanarki KLD / Kernel Tuner gotowe, ale jeszcze nieuruchomione na GPU.
- [[2026-10-15-sampler|2026-10-15: sampler bez wolnych ścieżek (0065–0069)]] — Web UI, budżet myślenia, `logit_bias` i gramatyka narzędzi omp po cichu włączały pełne sortowanie 128k/248k kandydatów; po łatkach LFM ~255 → ~293 t/s i Qwen MTP +6–8% w tych ścieżkach, przy tych samych tokenach.
- [[2026-10-16-bit-exact|2026-10-16: bitowo identyczna spekulacja (MTP == plain greedy), w toku]] — Projekt trybu `LLAMA_SPEC_BITEXACT=1`, w którym greedy z MTP daje ten sam tekst co bez spekulacji; dziś na XTX plain i MTP mają różne md5 (c4708318 vs 6f14e814), bo ta sama pozycja jest liczona innym kernelem przy N=1 i N≥2.
- [[2026-10-16-kampania-nvidia|2026-10-16: pierwsza kampania na kartach NVIDIA (Vast), w toku]] — Faza 0 E2/E4: czy łatki forka działają poprawnie i dają zysk na NVIDIA; trzy karty (RTX 3060, 5060 Ti, 3090) jedna po drugiej, budżet ≤ $8, plan ~$2.5.
- [[2026-10-16-rebase-v070|2026-10-16: rebase 70 łatek na llama.cpp v0.7.0]] — Łatki przeniesione z `e60eff95f` na tag `v0.7.0` (141 commitów upstreamu później): 69 przeniesionych (60 czysto, 9 z konfliktami), 1 porzucona, bo już jest w upstreamie; build HIP OK, pełna weryfikacja na GPU do zrobienia.
- [[stan-2026-10-15|Stan zainstalowany 2026-10-15 (70 łatek)]] — Pomiar finalny po rundzie 6: Qwen3.8-27B 109.0 t/s, Uncensored 115.5, LFM2.5 293.7, LFM Uncensored 267.3; build `~/llama-opt`, gałąź `amd-opt` @ f61994f58.
<!-- AUTO:END -->
