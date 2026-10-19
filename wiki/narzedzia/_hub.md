---
typ: hub
tags: [narzedzia, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Narzędzia

**Nasze skrypty i narzędzia: do czego służą, jak je uruchomić, gdzie lądują wyniki.**

Większość leży w `qwen-opt/` i `qwen-opt/tools/` (repo KERNEL) oraz `~/qwen-opt/` na serwerze. Harness chmurowy: [[chmura/_hub|Chmura]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (27)

- [[co-stats|`co_stats.py`: statyczny audyt kerneli (VGPR, spille, fale)]] — `21l-skrypty/co_stats.py OUT.csv <lib.so|*.co|*.hsaco>` czyta wszystkie kernele z bundli HIP (także skompresowanych CCOB) i zapisuje per kernel VGPR, SGPR, spille, LDS i fale/SIMD; reguła fal gfx1100 = min(16, ⌊1536 / ⌈VGPR⌉₂₄⌋), zgodna z kompilatorem i RGA (raport 21l, 2026-10-19).
- [[hip-fatbin-extract|`tools/re/hip_fatbin_extract.py`: code objects z `.hip_fatbin`]] — Skrypt w czystym Pythonie (CPU) wyciąga z sekcji `.hip_fatbin` biblioteki HIP nieskompresowane bundle `__CLANG_OFFLOAD_BUNDLE__` (jeden na jednostkę kompilacji) i zapisuje każdy wpis `hipv4-amdgcn-*` jako `<outdir>/<idx>.<target>.co`; `--filter SUBSTR` zostawia tylko obiekty zawierające nazwę kernela (raport 23a, 2026-10-19).
- [[agentx-harness|AgentX harness (SemiAnalysis, AIPerf)]] — `agentx-harness==1.0.11` (na AIPerf NVIDIA, wrapper `python3 -m infx.bench agentic`) odtwarza 393 sesje Claude Code z zachowanymi długościami, hashami bloków 64 tokenów, drzewem subagentów i przerwami na narzędzia, ale z syntetyczną treścią; c = liczba żywych drzew sesji, punkt ≥ 900 s (oficjalnie 1 h) na świeżym serwerze (raport 21f, 2026-10-19).
- [[att-gfx1100|ATT (thread trace) na gfx1100]] — Śledzenie instrukcji fali (ATT) działa na RX 7900 XTX w ROCm 10.0: `rocprofv3 --att --att-target-cu 1 --att-simd-select 0 --kernel-include-regex … --kernel-iteration-range …` z `GGML_HIP_PM4=0`; skrypt `att_model.sh` i parser `attsum.py` w `~/wt/lfmmoe-prof/` (2026-10-18).
- [[kld-canary|Bramka KLD i kanarki (kld_gate.py, kld_canary.sh, perturb_gguf.py)]] — Trzy narzędzia: `kld_gate.py` porównuje dwa logi `llama-perplexity --kl-divergence`, `perturb_gguf.py` robi celowo uszkodzone kopie GGUF, a `kld_canary.sh` sprawdza, że bramka łapie prawdziwe szkody.
- [[rs64-firmware-re|Deasemblacja firmware CP/MES gfx11 (RS64 = RV64)]] — Jak czytać firmware MEC/MES gfx11: parsowanie nagłówka v2 (`fwparse.py`), deasemblacja capstone RV64C, propagacja znanych bitów do nazw rejestrów (`rs64kb.py`); apertura SH – indeks rejestru × 4 od `0x1_0002_0000_0000` (raport 23d, 2026-10-19).
- [[det-probe|det_probe.py (sonda determinizmu)]] — Sprawdza, które zdarzenie serwera psuje powtarzalność greedy: wysyła to samo zapytanie bez cache przed i po innych zapytaniach i pokazuje, gdzie wyjścia się rozjeżdżają.
- [[fabryka-cli|Fabryka v1: CLI `factory`]] — `~/qwen-opt/factory/` (Python stdlib, 2394 linie `fk/` + CLI, 36 reguł w 1141 liniach, 57 testów OK w 29.5 s na CPU) zamraża kartę twierdzenia przed pomiarem, mierzy kaskadą G0–G5 i zapisuje werdykt do `ledger.jsonl` z łańcuchem sha256; zbudowane 2026-10-16 bez GPU.
- [[gdnemu-isadiff|gdnemu.py i isadiff.py (dowód bitowości z ISA)]] — Symboliczny emulator gfx11 wave32 wykonujący skompilowany ISA kerneli GDN bez GPU oraz `isadiff.py`, który sprawdza, że każdy kernel bazowy jest bajtowo identyczny w nowym buildzie.
- [[gpu-keepawake|gpu-keepawake (trzymanie GPU w stanie aktywnym)]] — 12-liniowy program HIP, który trzyma kontekst KFD, żeby runtime PM amdgpu nie uśpił karty (BACO); uruchamiany przez `run-llm.sh`, gdy runtime suspend jest włączony.
- [[greedy-check|greedy.sh / greedy_check.sh — bramka md5]] — Skrypty uruchamiają świeży serwer i zapisują tekst greedy (T=0) w trybie plain i MTP; md5 musi się zgadzać z bazą, żeby łatka była „bitowo identyczna”.
- [[kb|kb: szybkie wyszukiwanie w bazie wiedzy]] — `kb search <pytanie>` i `kb facts <pytanie> [--max|--min]` (`~/.local/bin/kb`) przeszukują cały `~/KERNEL` (wiki, raporty, `NOTES.md`) i zwracają odpowiedź z `plik:linia`. Na 80 prawdziwych pytaniach recall@5 wynosi 0.963, a zapytanie trwa 10–70 ms.
- [[kt-harness|Kernel Tuner harness (kt/)]] — Rusztowanie Kernel Tunera dla gorących kerneli dekodu na gfx1100: `mmvq_n1`, `moe_gate_up`, `moe_down`, `gdn`; tylko `tune` dotyka GPU.
- [[llama-bx-diff|llama-bx-diff (pierwszy rozjeżdżający się węzeł)]] — Program z gałęzi `batch-invariant`: znajduje pierwszy węzeł grafu, którego wynik dla tokenu różni się między zwykłym dekodem (token po tokenie) a weryfikacją N tokenów w jednym batchu.
- [[loo-py|loo.py (leave-one-out łatek)]] — Narzędzie leave-one-out serii `amd-opt`: plan (CPU, git), runner GPU, buildy z revertami i raport ze sparowanym 95% CI.
- [[pm4-soak|pm4_soak.py (test wytrzymałościowy serwera)]] — Soak test działającego llama-server: wiele zapytań czatu o mieszanej długości, powtarzane zapytania greedy muszą się zgadzać, follow-upy ćwiczą cache promptu; kod wyjścia 1 przy błędzie lub rozjeździe.
- [[landing-qa|QA landingu: `app/landing/scripts/qa/`]] — Cztery skrypty puppeteer-core po CDP (Chrome bez GPU, `.tools/chrome-swgl`, port 18499): hydracja, hero pod obciążeniem, axe i zrzuty ekranu.
- [[reactor-monitor|REACTOR (monitor terminalowy)]] — Pełnoekranowy monitor GPU/CPU/LLM w terminalu dla serwera z RX 7900 XTX, w czystym Pythonie 3.12 (tylko stdlib) z 24-bitowymi kolorami ANSI.
- [[run-llm-sh|run-llm.sh — start produkcyjnego serwera]] — Jeden skrypt, który uruchamia zoptymalizowany llama-server na RX 7900 XTX z naszymi ustawieniami dla każdego modelu.
- [[samp-ab|samp_ab.py (A/B samplera)]] — Skrypt A/B szybkich ścieżek samplera: wysyła do działającego llama-server zapytania w stylu web UI i omp, wypisuje t/s dekodu i md5 wyjścia z ustalonym seedem.
- [[serve-bench|serve_bench.py i quick_quality.py — pierwsze narzędzia (2026-10-09)]] — Pierwszy benchmark end-to-end projektu i szybki test jakości; dziś zastąpione przez spec_sweep, ale ich wyniki (59.2 → 92 t/s) są punktem startowym.
- [[skrypty-chmury|Skrypty chmury (~/qwen-opt/cloud)]] — Zestaw skryptów bash do kampanii na wynajętych kartach Vast; każdy domyślnie tylko wypisuje komendy, a wykonuje je dopiero z `--go`.
- [[spec-sweep|spec_sweep — główny pomiar t/s i ms/krok]] — Standardowy benchmark projektu: restartuje serwer dla każdej konfiguracji i mierzy t/s, ms/krok, tokeny na krok i akceptację draftu na stałym zestawie promptów PL/EN.
- [[ss-zrzut-ekranu|ss (zrzut ekranu z Windowsa na serwer)]] — Funkcja PowerShella `ss` w profilu użytkownika: zapisuje obrazek ze schowka jako PNG i kopiuje go przez `scp` do `/tmp` na serwerze, żeby agent mógł go przeczytać.
- [[gpu-guard|Strażnik GPU: `qwen-opt/tools/gpu-guard.sh`]] — Skrypt odpytuje co 2 s log jądra i sensory XTX; przy zagrożeniu zabija wszystkie `llama-server` / `llama-bench` / `llama-perplexity` / `test-backend-ops` / `magnitude-engine` poza produkcją na :8080, zapisuje powód do `gpu-guard.log` i kończy się kodem 3, który budzi agenta głównego.
- [[umr-offline-pm4|umr offline: dekodowanie taśmy PM4 bez roota]] — umr zbudowany bez roota (`apt download` + `dpkg -x`) dekoduje offline pakiety PM4, AQL i pola rejestrów gfx1100: `umr -f gfx11_vm_test -df plik.bin`; nie dekoduje słowa inicjatora `DISPATCH_DIRECT` (Mesa `ac_parse_ib.c` też nie) (raport 21l, 2026-10-19).
- [[wiki-py|wiki.py (narzędzie tej bazy wiedzy)]] — Skrypt tylko ze stdlib do utrzymania wiki: `lint` (błędy → kod wyjścia 1), `index` (odświeża listy w `_hub.md` i `index.md`), `search` (deleguje do [[kb]], gdy `kb` jest w PATH; bez niego tytuły, streszczenia, tagi).
<!-- AUTO:END -->
