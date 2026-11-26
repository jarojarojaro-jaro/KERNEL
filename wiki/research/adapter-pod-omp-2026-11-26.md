---
typ: research
tags: [research, llm, trening, rl, lora, agenci, omp, harness]
aktualizacja: 2026-11-26
zrodlo: x.com/yb2698/status/2125568461581750447 (panel JARO 2026-11-26); huggingface.co/spaces/trl-lib/trl-recipes recipes/harness-adapters/Inkling-2-Mini (recipe.yaml, README, commit a8f4321); harness-hub-community-adapters.hf.space (/api/state); huggingface.co/harness-hub/Qwen3.8-27B-pi-adapted; vastai search offers 2026-11-26; lokalne sesje ~/.omp/agent/sessions, ~/kernel/sesje
status: aktualne
---
# Research: dotrenować nasze modele pod nasz harness (omp)?

**Werdykt: tak, ale w trzech krokach i od najtańszego. omp to fork agenta pi, a harness-hub właśnie trenuje otwarcie adaptery pi dla obu naszych modeli bazowych (Qwen3.8-27B: gotowy, Inkling 2 Mini: kandydat ckpt 130). Najpierw mierzymy ich gotowe adaptery w omp na naszym zestawie zadań, potem tani własny trening SFT na udanych trajektoriach naszego lokalnego modelu, a pełny RL jak u nich (setki GPU-godzin) dopiero, gdy pierwsze dwa kroki pokażą zysk.**

## Co robi harness-hub (stan 2026-11-25)
- **Przepis:** TRL AsyncGRPO + LoRA r=32, lr 2e-5, 8 rolloutów na zadanie, T 0,8, do 50 kroków agenta, nagroda = weryfikator zadania + 0,1 × (1 − wywołania/15). Zadania: 750 scale800 + 300 TermGrade, zbudowane z publicznych sesji agentów (Repo2RLEnv), proxy safeagents blokuje oszustwa (edycja testów, czytanie gradera). Sprzęt: 2 GPU na harness (vLLM rollouty + trener), B300 albo 2× H200.
- **Inkling 2 Mini:** LoRA tylko na atencji (q/k/v/o), eksperci zamrożeni; myślenie wyłączone. 35–75 min na krok. Wyniki pass@1, małe próby (szum ok. ±4 pkt):

| adapter | Terminal-Bench 2.1 | SWE-bench Pro hard51 | efekt uboczny |
|---|---|---|---|
| Inkling pi ckpt 130 (kandydat) | 54,0 → 56,3 | 70,6 → 72,5 | −22% wywołań na rozwiązane, −18…−23% tokenów |
| Inkling hermes ckpt 80 | 57,5 → 60,9 | 72,0 → 68,6 | −26% wywołań na SBP |
| Inkling pi-low (effort 0,2) ckpt 10 | 54,0 → 60,2 | = | trwa |
| **Qwen3.8-27B pi (gotowy)** | 39,5 → 55,8 | 29,4 → 62,7 | −55…62% wywołań |

- Wnioski: na mocnej bazie (Inkling) zysk to głównie **krótsze sesje** (mniej wywołań i tokenów, czyli szybszy agent przy tej samej prędkości silnika), na słabszej (Qwen 27B) także **dużo więcej rozwiązanych zadań**. Checkpointy Inklinga (z GGUF) są w publicznym bucket `harness-hub/community-adapters-checkpoints`.

## Co mamy my
- **Dane:** 845 plików sesji omp na Jarvie (256 w `~/.omp/agent/sessions`, 589 w `~/kernel/sesje`; 2 GB), **110 783 wywołań narzędzi**. Producent: prawie wyłącznie Claude (opus-5-5 99 302 wpisów modelu, haiku, fable), trochę DeepSeek; lokalny Qwen występuje tylko w replayach testowych.
- **Problem 1, licencja:** trening naszego modelu na wyjściach Claude to destylacja modelu Anthropic; warunki dostawcy ograniczają użycie wyjść do trenowania konkurencyjnych modeli. **Nie używamy tych sesji jako danych SFT** bez sprawdzenia warunków przez JARO (przypuszczam, że to blokuje).
- **Problem 2, prywatność:** w wynikach narzędzi są prompty sudo, adresy LAN, nazwy kluczy, prywatne treści; przed jakimkolwiek wyjściem poza nasze maszyny trzeba czyścić.
- **Problem 3, weryfikatory:** większość sesji to research i benchmarki, a nie zadania z testem; RL potrzebuje zadań, które da się automatycznie ocenić.
- **Co się nadaje:** zadania (prompty i repozytoria) z naszych sesji jako **zestaw zadań**, a trajektorie generuje nasz lokalny model w omp (samodestylacja, czysta licencyjnie).

## Opcje i koszt (ceny Vast 2026-11-26 01:50: A100 80 GB od 1,13 $/h, 2× A100 80 GB od 2,25 $/h, H200 od 5,07 $/h, H100 SXM 6,67 $/h, RTX PRO 6000 od 1,14 $/h)

| krok | co | koszt | ryzyko |
|---|---|---|---|
| **0. Zestaw testowy omp** | 30–50 zadań z naszych repo z automatycznym sprawdzeniem (testy, md5, build), uruchamianych przez omp z modelem na :8080; miara: rozwiązane, wywołania, tokeny, czas | 0 $, ok. 1 dzień pracy agenta, karta: XTX z kolejki | bez tego żaden trening nie ma oceny |
| **1. Gotowe adaptery pi** | Qwen3.8-27B pi (0,64 GB, K-120) i Inkling pi ckpt 130 (LoRA tylko atencji, mała) w omp: baza vs adapter na zestawie z kroku 0; prędkość z `--lora` i po scaleniu | 0 $ (pobranie ok. 1 GB, wymaga „tak”) | baza z cenzurą vs nasza bez cenzury; MTP po scaleniu |
| **2. Samodestylacja SFT** | nasz model rozwiązuje zadania w omp wiele razy (XTX, noc), zostawiamy udane trajektorie, LoRA SFT na nich | ok. 5–15 $ (A100 80 GB 4–8 h) + noce XTX | mały zysk bez sygnału nagrody |
| **3. RL jak harness-hub** | AsyncGRPO na naszych zadaniach z weryfikatorem, safeagents | Inkling: 35–75 min/krok × 100–160 kroków na 2 GPU ≈ 120–400 GPU-h ≈ 300–2000 $; Qwen 27B podobny rząd | koszt, reward hacking, dryf kwantyzacji Q4_K_M |

## Rekomendacja
1. Robię krok 0 teraz (zestaw zadań omp + skrypt oceny), bo jest potrzebny do wszystkiego, co dalej.
2. Krok 1 po „tak” na pobranie dwóch adapterów (ok. 1 GB, wyjątek od zasady „pracuj na tych co masz”).
3. Krok 2 dopiero gdy krok 1 pokaże, że adapter pi w omp coś daje; krok 3 tylko z osobnym budżetem.
4. Do zapytania JARO: czy wolno uczyć na wyjściach Claude (warunki Anthropic) — domyślnie nie.

## Powiązane
- [[qwen38-27b-pi-adapter]]
- [[trening-llm-mapa]]
- [[cspd-soft-prompt]]
- [[inkling-2-mini]]
