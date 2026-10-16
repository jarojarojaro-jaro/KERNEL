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
## Notatki (35)

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
- [[2026-10-16-backtest-regul-fabryki|2026-10-16: backtest reguł fabryki na historii (X1 z 15f)]] — Reguły fabryki v1 puszczone na prawdziwych danych (tylko CPU): R21 łapie 1/1 incydent (wiersz 15, 5.6 t/s) z 0 fałszywymi alarmami na 194 i 182 wierszach `spec_sweep.jsonl` (wcześniej 5/182 przez podciąg „lfm”); X1 przechodzi.
- [[2026-10-16-kompresja-skal-offline|2026-10-16: bezstratna kompresja skal kwantów (offline, odrzucona)]] — Pomiar entropii skal na prawdziwych plikach: dla naszych K-quantów (UD-Q4_K_XL) bezstratna kompresja skal oszczędziłaby najwyżej 2.19% bajtów – za mało na nowy typ ggml; dla NVFP4 w GGUF −5.4% (kod CSF-like) do −8% (entropia), odłożone.
- [[2026-10-16-bit-exact|2026-10-16: bitowo identyczna spekulacja (MTP == plain greedy) — OSIĄGNIĘTE]] — Na 7900 XTX z `LLAMA_SPEC_BITEXACT=1 GGML_HIP_BITEXACT_FA_ZERO_MASKED=1` (gałąź `batch-invariant`) greedy Qwen3.8-27B daje ten sam tekst z MTP i bez: md5 obu `74952fd5c918b0486194c21d3ee0576c` (2783 znaki, 0 różnic); pełna walidacja PASS, a na flagach produkcyjnych bitexact MTP 107.0 t/s ≈ produkcja 107.5/107.8 t/s.
- [[2026-10-16-budzet-lfm-megakernel|2026-10-16: budżet tokenu LFM pod megakernel (offline)]] — Rachunek z nagłówka GGUF i taśmy PM4 (bez GPU): LFM2.5 Q5_K_M na XTX czyta 1.777 GB/token, a 3404 µs/token dzieli się na strumień 1953 µs, narzut matvec 698 µs, małe kernele 534 µs i host ~220 µs.
- [[2026-10-16-kvq-cuda|2026-10-16: E1 – port `kvq` na CUDA (Ampere+)]] — Kernel `fattn-kvq-mma.cu` (commit `f08dc78bb`, gałąź `kvq-cuda`, wyłącznik `GGML_CUDA_KVQ=0`) podnosi tg64@64k na 3090 o +36.8% (Qwen) i +30.4% (LFM), MTP@59k o +27.6%; próg kill +10% daleko przekroczony, koszt ~$0.94.
- [[2026-10-16-lookup-kopiowalnosc|2026-10-16: kopiowalność naszych workloadów (symulacja CPU)]] — Symulacja CPU na 524 743 tokenach odpowiedzi Qwena i 7.2 M tokenów wyjść agenta omp: lookup z kontekstu trafia 1–17% pozycji czatu i 27–60% wyjść agenta; nadpisywanie głowy (HYB) szkodzi, doklejanie ogona (EXT) pomaga tylko na edycjach.
- [[2026-10-16-nemotron-3090|2026-10-16: Nemotron 3.5 Bolt na RTX 3090 (Vast)]] — Kampania na wynajętym RTX 3090 (~2.3 h, ≈ $0.52) z Nemotronem 3.5 Bolt i drafterem DFlash: tuned 141.1 t/s vs A0 87.2 i A1 131.4; przerwana przez limit zapytań agenta, więc KLD i A/B przełączników zostały niezrobione.
- [[2026-10-16-nvfp4-skala-globalna-sim|2026-10-16: NVFP4 ze skalą globalną i bez (symulacja CPU)]] — Symulacja na prawdziwych wagach BF16 Qwen3.8-27B: dodanie skali globalnej per tensor do kwantyzatora NVFP4 ggml obniża błąd wag o 22–35%, ale nawet wtedy NVFP4 RTN jest o 12–17% gorszy od Q4_0 RTN przy tych samych 4.5 bpw.
- [[2026-10-16-kampania-nvidia|2026-10-16: pierwsza kampania na kartach NVIDIA (Vast)]] — Faza 0 E2/E4 zakończona: trzy karty (RTX 3090, 5060 Ti, 3060) równolegle, ≈ $2.77 z $5; łatki budują się i działają na NVIDIA, dają ×1.4–2.0 na Qwen/LFM, ale greedy nie jest bitowo równy upstreamowi.
- [[2026-10-16-pflash-pilot-cpu|2026-10-16: pilot CPU selekcji PFlash v2 po polsku i angielsku]] — Kopia selekcji PFlash v2 na CPU ($0): głowica Q/K przenosi się na polski, ale sonda żądania trenowana po angielsku wskazała pytanie jako top-1 w 1/10 przypadków PL wobec 10/10 EN.
- [[2026-10-16-mtp-pl-pilot|2026-10-16: pilot douczania głowicy MTP (wynik negatywny)]] — Douczanie wbudowanej głowicy MTP Qwen3.8-27B na naszym Q4 (RunPod A40, 3.50 h, $2.14) nie dało zysku: offline najlepszy przebieg +0.2%, online n=4 PL-proza +2.3% i pozostałe klasy 0 do −1.7%.
- [[2026-10-16-rebase-v070|2026-10-16: rebase 70 łatek na llama.cpp v0.7.0]] — Łatki przeniesione z `e60eff95f` na tag `v0.7.0` (141 commitów upstreamu później): 69 przeniesionych (60 czysto, 9 z konfliktami), 1 porzucona, bo już jest w upstreamie; build HIP OK, pełna weryfikacja na GPU do zrobienia.
- [[stan-2026-10-15|Stan zainstalowany 2026-10-15 (70 łatek)]] — Pomiar finalny po rundzie 6: Qwen3.8-27B 109.0 t/s, Uncensored 115.5, LFM2.5 293.7, LFM Uncensored 267.3; build `~/llama-opt`, gałąź `amd-opt` @ f61994f58.
<!-- AUTO:END -->
