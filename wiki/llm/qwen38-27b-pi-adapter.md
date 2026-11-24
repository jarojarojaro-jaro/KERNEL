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

## Aktualizacja 2026-11-18: adapter pod OpenCode (przepis v2)

Źródło: huggingface.co/harness-hub/Qwen3.8-27B-opencode-adapted; x.com/yb2698/status/2123043263041155473. Właściciel: „mega ważne”.

**Najważniejsze dla nas: adapter bez myślenia dorównuje bazie z myśleniem na maksymalnym wysiłku (`xhigh`), ale generuje 6–8 × mniej tokenów.** Przy dekodzie ograniczonym pasmem tokeny to czas. Przykład:
- mediana na zadanie SWE-bench Pro: 31,8k → 3,9k tokenów, czyli przy naszych ~120 t/s ~265 s → ~33 s samego dekodu;
- Terminal-Bench: 15,8k → 2,6k tokenów;
- wywołania modelu: 44 → 18 i 14 → 12.

Taki zysk daje sam model, bez żadnego kernela.

| test (OpenCode, 1 próba, 100 kroków) | baza | baza z myśleniem | adapter | adapter z myśleniem |
|---|---|---|---|---|
| SWE-bench Pro (hard 51) | 35,3% | 47,1% | **51,0%** | 54,9% |
| Terminal-Bench 2.1 | 47,0% | 55,4% | **53,0%** | 56,6% |

**Uczciwie:**
- parowane różnice z bazą: SWE-bench Pro +15,7 ± 13,9 pp (p = 0,057), Terminal-Bench +6,0 ± 10,7 (p = 0,38), na 66 zadaniach niewybieranych do checkpointu +13,6 (p = 0,035);
- słabiej niż pi (tam p < 0,002);
- myślenie włączone w adapterze nic istotnego nie dodaje (8/6, 13/10), a daje ~6 × więcej tokenów.

**Przepis:** ten sam co pi (AsyncGRPO, LoRA r 32, lr 2e-5, nagroda + 0,1 za oszczędność wywołań, 2 × B200, 150 kroków), harness OpenCode 2.2.7. Skrypt jest już publiczny w TRL: `examples/async_grpo_harbor`. Bariera dla naszego własnego adaptera pod omp to dziś koszt GPU, nie kod.

## Aktualizacja 2026-11-19: adapter pod Hermes (Nous Research)

Źródło: huggingface.co/harness-hub/Qwen3.8-27B-hermes-adapted; x.com/yb2698/status/2123421903784136769.

| test (Hermes, 1 próba) | baza | baza z myśleniem | adapter | adapter z myśleniem |
|---|---|---|---|---|
| SWE-bench Pro (hard 51) | 29,4% | 45,1% | **43,1%** | 51,0% |
| Terminal-Bench 2.1 | 44,7% | 58,8% | **58,8%** | 57,6% |

- Parowane różnice: SWE +13,7 ± 13,3 pp (p = 0,092), TB +14,1 ± 11,4 (p = 0,029).
- Bez myślenia adapter jest jak baza z myśleniem `xhigh`, przy 3,5–4,4 × mniej tokenów.
- To trzeci harness z tym samym przepisem: pi, OpenCode, Hermes. Wzorzec się powtarza: celowany LoRA zastępuje myślenie i tnie tokeny.
- Dla K-120: do porównania w omp wybieramy najbliższy harness, czyli pi (omp to jego fork).

**Zmiana modelu na produkcji (topka, Enigma) to decyzja właściciela.** Test: K-120 w [[KOLEJKA-TESTOW]].

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

Blog „Harness adapters” (huggingface.co/blog/harness-hub/harness-adapters, 2026-11-06) uczy więcej niż „czy adapter pomoże w omp”. Trzy warstwy mają u nas odpowiedniki.
- **Serwowanie: jedna baza, wiele adapterów.** Jeden vLLM trzyma wagi bazowe raz, a każde żądanie wybiera adapter po nazwie. Nowy adapter ładuje się obok starego bez przerwy, a 9 checkpointów oceniono w 1 zadaniu za ~5 USD zamiast ~90 USD po scaleniu. llama-server ma to samo: pole `lora` per żądanie i `/lora-adapters` (`~/praca/llama-duo/tools/server/README.md:605,1201-1236`). Ostrzeżenie: żądania z innym zestawem LoRA nie idą w jednym batchu. Topka i Enigma mogłyby więc trzymać jeden plik Qwena i adapter na harness, bez drugiej kopii 16 GB.
- **Dane z sesji agentów (Repo2RLEnv):** zadania wybierają same reguły, bez LLM. `repair` to sprawdzenie, które padło, a po edycjach przeszło bez nowej instalacji. Testy pisane przez LLM zostają tylko wtedy, gdy przechodzą na oryginale dwa razy, padają na zaślepce i łapią wstrzyknięte błędy (mutacje). Mamy tysiące tur omp w `~/kernel/archiwum`, więc ta sama droga daje nasze zadania RL i nasz zestaw testów agenta.
- **Bramka agenta (safeagents):** proxy między harnessem a modelem sprawdza każde wywołanie narzędzia regułami w 10–20 ms. Blokuje edycję testów, czytanie gradera, `curl` do hosta spoza rozmowy i `echo $HF_TOKEN`. Zablokowana próba dostaje 0, a złapali ją już w kroku 0. U nas bramki przeglądu ([[metody/_hub|metody]]) działają po fakcie, a w przypadku Enigma Turbo agent zrobił „zielone” testy na własnych założeniach ([[enigma-turbo-gemini-2026-11-20]]). Reguły „nie ruszaj testów ani bramki” można sprawdzać automatycznie, zanim wywołanie się wykona.
- **Wniosek o tokenach:** adapter bez myślenia = baza z `xhigh` przy 3,5–8 × mniej tokenów. Dla użytkownika liczy się czas zadania, czyli tokeny / t/s, a Enigma mierzy tylko t/s.

## Powiązane
- [[peft-lora-warianty]]
- [[trening-llm-mapa]]
- [[sensenova-loop-9b]]
- [[2026-11-17-k114-nvidia-sufit]]
