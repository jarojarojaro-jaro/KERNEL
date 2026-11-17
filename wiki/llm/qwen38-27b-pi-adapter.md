---
typ: llm
tags: [llm, lora, rl, grpo, agenci, qwen, telegram]
aktualizacja: 2026-11-18
zrodlo: https://x.com/ClementDelangue/status/2122784279604383914 (Telegram „gpu”, 2026-11-18); huggingface.co/harness-hub/Qwen3.8-27B-pi-adapted (karta modelu, adapter 637,6 MB); huggingface.co/blog/harness-hub/harness-adapters (2026-11-06); omp = oh-my-pi (fork pi coding agent, `strings` binarki omp 18.22.0)
status: aktualne
---
# Qwen3.8-27B-pi-adapted: LoRA wytrenowana RL-em pod agenta pi — nasz model bazowy, dużo mniej wywołań narzędzi

**Hugging Face wytrenował adapter LoRA (r = 32, 0,64 GB) do Qwen3.8-27B, czyli naszego modelu bazowego, uczeniem ze wzmocnieniem (RL) wewnątrz agenta pi. Pod pi: SWE-bench Pro (hard 51) 29,4 → 62,7%, Terminal-Bench 2.1 39,5 → 55,8%, 55–62% mniej wywołań narzędzi. Nasz omp to fork pi, więc to najbliższy nam gotowy „dostrojony pod agenta” model, ale trzeba to sprawdzić na naszym stosie i w omp.**

**Liczby** (karta modelu; pi, T 0,8, myślenie wyłączone, 1 próba, parowane z bazą):

| test | zadań | baza | adapter (krok 160) | różnica | zyskane / stracone |
|---|---|---|---|---|---|
| Terminal-Bench 2.1 | 86 | 39,5% | 55,8% | +16,3 ± 9,1 pp | 16 / 2 (p = 0,0013) |
| ten sam, 68 zadań niewybieranych do checkpointu | 68 | 39,7% | 55,9% | +16,2 ± 10,6 | 13 / 2 |
| SWE-bench Pro (hard 51) | 51 | 29,4% | 62,7% | +33,3 ± 14,2 | 18 / 1 (p = 7,6e-05) |

Uczciwie raportowane: przedziały, test znaku, osobny podzbiór niewybierany do checkpointu. Słabość: checkpoint wybierano częściowo na SWE-bench Pro.

**Przepis** (filar trening, [[trening-llm-mapa]]):
- **Metoda:** AsyncGRPO (TRL), 8 rolloutów na zadanie, T 0,8, do 50 kroków agenta.
- **LoRA:** r 32, α 64, na q/k/v/o/gate/up/down; lr 2e-5.
- **Długość:** 160 kroków (z planowanych 1000).
- **Sprzęt:** 2 × B200 (vLLM + trener).
- **Nagroda:** weryfikator zadania + 0,1 × (1 − wywołania/15), tylko dla poprawnych rozwiązań. Stąd mniej wywołań narzędzi.
- **Dane:** 750 zadań scale800 + 300 TermGrade. Środowiska z blogu to zadania budowane z publicznych sesji agentów (Repo2RLEnv):
  - repair, build i extend; wzorcem jest praca oryginalnego agenta;
  - testy pisze nauczyciel LLM i są sprawdzane mutacjami.
- **Ochrona przed oszukiwaniem nagrody:** safeagents, proxy z regułami między harnessem a modelem. Blokuje edycję testów, czytanie gradera, szukanie odpowiedzi w Hubie i czytanie tokenów; zablokowana próba dostaje 0. Przyłapali to już w kroku 0.

**Co to znaczy dla nas:**
1. **Inny harness = inne zachowanie** (blog: ten sam model różnie działa w różnych agentach). omp ma własne narzędzia (np. edycje hashline), więc zysk z pi nie przenosi się automatycznie. Trzeba to zmierzyć w omp.
2. **Inna baza:** adapter trenowano na BF16 `Qwen/Qwen3.8-27B`. Produkcja to Qwen3.8-27B-**Uncensored** w Q4_K_M. Karta modelu: „lower-bit quants drift further”, a wersji GGUF nie oceniano ponownie.
3. **Koszt w naszym silniku:**
   - Bez scalania LoRA dokłada ~0,64 GB odczytu na token (+4% bajtów, ~−4% dekodu) oraz 7 × 64 par małych mnożeń na krok. Z K-114 wiemy, że małe kernele kosztują 4–15 × swoje bajty [INFERENCE: realnie więcej niż −4%].
   - Po scaleniu i ponownej kwantyzacji koszt jest zerowy, ale to nowy plik wag, a głowica MTP (blk.64) nie była trenowana. Akceptacja draftu może spaść.
4. **Pomysł treningowy:** ten sam przepis na naszych sesjach omp (`~/kernel/archiwum`, tysiące tur agenta) dałby adapter „pod omp”. Koszt: 2 × B200 kilka godzin [INFERENCE]. Najpierw K-120, czyli sprawdzić, czy gotowy adapter pi w ogóle pomaga w omp.

**Zmiana modelu na produkcji (topka, Enigma) to decyzja właściciela.** Test: K-120 w [[KOLEJKA-TESTOW]].

## Powiązane
- [[peft-lora-warianty]]
- [[trening-llm-mapa]]
- [[sensenova-loop-9b]]
- [[2026-11-17-k114-nvidia-sufit]]
