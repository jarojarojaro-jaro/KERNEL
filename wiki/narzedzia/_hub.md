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
## Notatki (17)

- [[kld-canary|Bramka KLD i kanarki (kld_gate.py, kld_canary.sh, perturb_gguf.py)]] — Trzy narzędzia: `kld_gate.py` porównuje dwa logi `llama-perplexity --kl-divergence`, `perturb_gguf.py` robi celowo uszkodzone kopie GGUF, a `kld_canary.sh` sprawdza, że bramka łapie prawdziwe szkody.
- [[det-probe|det_probe.py (sonda determinizmu)]] — Sprawdza, które zdarzenie serwera psuje powtarzalność greedy: wysyła to samo zapytanie bez cache przed i po innych zapytaniach i pokazuje, gdzie wyjścia się rozjeżdżają.
- [[gdnemu-isadiff|gdnemu.py i isadiff.py (dowód bitowości z ISA)]] — Symboliczny emulator gfx11 wave32 wykonujący skompilowany ISA kerneli GDN bez GPU oraz `isadiff.py`, który sprawdza, że każdy kernel bazowy jest bajtowo identyczny w nowym buildzie.
- [[gpu-keepawake|gpu-keepawake (trzymanie GPU w stanie aktywnym)]] — 12-liniowy program HIP, który trzyma kontekst KFD, żeby runtime PM amdgpu nie uśpił karty (BACO); uruchamiany przez `run-llm.sh`, gdy runtime suspend jest włączony.
- [[greedy-check|greedy.sh / greedy_check.sh — bramka md5]] — Skrypty uruchamiają świeży serwer i zapisują tekst greedy (T=0) w trybie plain i MTP; md5 musi się zgadzać z bazą, żeby łatka była „bitowo identyczna”.
- [[kt-harness|Kernel Tuner harness (kt/)]] — Rusztowanie Kernel Tunera dla gorących kerneli dekodu na gfx1100: `mmvq_n1`, `moe_gate_up`, `moe_down`, `gdn`; tylko `tune` dotyka GPU.
- [[llama-bx-diff|llama-bx-diff (pierwszy rozjeżdżający się węzeł)]] — Program z gałęzi `batch-invariant`: znajduje pierwszy węzeł grafu, którego wynik dla tokenu różni się między zwykłym dekodem (token po tokenie) a weryfikacją N tokenów w jednym batchu.
- [[loo-py|loo.py (leave-one-out łatek)]] — Narzędzie leave-one-out serii `amd-opt`: plan (CPU, git), runner GPU, buildy z revertami i raport ze sparowanym 95% CI.
- [[pm4-soak|pm4_soak.py (test wytrzymałościowy serwera)]] — Soak test działającego llama-server: wiele zapytań czatu o mieszanej długości, powtarzane zapytania greedy muszą się zgadzać, follow-upy ćwiczą cache promptu; kod wyjścia 1 przy błędzie lub rozjeździe.
- [[reactor-monitor|REACTOR (monitor terminalowy)]] — Pełnoekranowy monitor GPU/CPU/LLM w terminalu dla serwera z RX 7900 XTX, w czystym Pythonie 3.12 (tylko stdlib) z 24-bitowymi kolorami ANSI.
- [[run-llm-sh|run-llm.sh — start produkcyjnego serwera]] — Jeden skrypt, który uruchamia zoptymalizowany llama-server na RX 7900 XTX z naszymi ustawieniami dla każdego modelu.
- [[samp-ab|samp_ab.py (A/B samplera)]] — Skrypt A/B szybkich ścieżek samplera: wysyła do działającego llama-server zapytania w stylu web UI i omp, wypisuje t/s dekodu i md5 wyjścia z ustalonym seedem.
- [[serve-bench|serve_bench.py i quick_quality.py — pierwsze narzędzia (2026-10-09)]] — Pierwszy benchmark end-to-end projektu i szybki test jakości; dziś zastąpione przez spec_sweep, ale ich wyniki (59.2 → 92 t/s) są punktem startowym.
- [[skrypty-chmury|Skrypty chmury (~/qwen-opt/cloud)]] — Zestaw skryptów bash do kampanii na wynajętych kartach Vast; każdy domyślnie tylko wypisuje komendy, a wykonuje je dopiero z `--go`.
- [[spec-sweep|spec_sweep — główny pomiar t/s i ms/krok]] — Standardowy benchmark projektu: restartuje serwer dla każdej konfiguracji i mierzy t/s, ms/krok, tokeny na krok i akceptację draftu na stałym zestawie promptów PL/EN.
- [[ss-zrzut-ekranu|ss (zrzut ekranu z Windowsa na serwer)]] — Funkcja PowerShella `ss` w profilu użytkownika: zapisuje obrazek ze schowka jako PNG i kopiuje go przez `scp` do `/tmp` na serwerze, żeby agent mógł go przeczytać.
- [[wiki-py|wiki.py (narzędzie tej bazy wiedzy)]] — Skrypt tylko ze stdlib do utrzymania wiki: `lint` (błędy → kod wyjścia 1), `index` (odświeża listy w `_hub.md` i `index.md`), `search` (tytuły, streszczenia, tagi).
<!-- AUTO:END -->
