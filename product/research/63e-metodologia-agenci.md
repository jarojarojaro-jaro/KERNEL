# 63e — Metodologia: agenci optymalizujący kernele, reward hacking, audyt naszego benchmarku i „jak myślą najlepsi”

Data: 2026-11-05. Praca tylko na CPU: GPU i serwer :8080 nietknięte, bez wag i zbiorów danych. Kod sklonowany
(`--depth 50`) do `~/src/research63/`:

| repo | commit (data) |
|---|---|
| [rohanarun/Auto-research-agent](https://github.com/rohanarun/Auto-research-agent) | `0230468` (2026-11-04) |
| [caoshiyi/EAT](https://github.com/caoshiyi/EAT) | `0a90500` (2026-11-02) |
| [skyzh/tiny-llm](https://github.com/skyzh/tiny-llm) | `17a8cc6` (2026-10-31) |
| [pavelsimo/100-days-of-inference-engineering](https://github.com/pavelsimo/100-days-of-inference-engineering) | `18eef29` (2026-11-04, dzień 7) |
| [navaneethkrishnansuresh/CUDA-and-Kernels](https://github.com/navaneethkrishnansuresh/CUDA-and-Kernels) | `7045333` (2026-11-03) |
| [wafer-ai/gpu-perf-engineering-resources](https://github.com/wafer-ai/gpu-perf-engineering-resources) | `6aa00fc` (2026-10-17) |
| [anthropics/FlashProve](https://github.com/anthropics/FlashProve) | `9e2bdd8f` (2026-10-30, v0.16.0) |

Oznaczenia: `[INFERENCE]` = mój wniosek bez pomiaru, `[SZACUNEK]` = moja arytmetyka, `[NIEZWERYFIKOWANE]` = teza
źródła, której nie dało się sprawdzić. Posty z X czytałem przez publiczne API `api.fxtwitter.com` i
`cdn.syndication.twimg.com` (treść tweetów, artykuł Decagon) albo przez lustro threadnavigator (artykuł Overshoot);
artykułu Baseten nie dało się odczytać żadną drogą (§4).

Uwaga procesowa: trzy podagenty-scouty, które uruchomiłem na początku, okazały się obsługiwane przez lokalny model na
GPU (`llama.cpp//…/Qwen3.8-27B-Uncensored-Q4_K_M.gguf`, transkrypty w sesji). Zabiłem je po wykryciu, żeby nie
dotykać GPU, i całą lekturę zrobiłem sam (strony, które zdążyły pobrać, czytałem z ich logów).

## 0. Najważniejsze

1. **Przełomu technicznego dla batch 1 na RDNA3 w tej sekcji nie ma.** Jest przełom metodologiczny, a trzy niezależne
   zespoły potwierdzają nasze wnioski:
   - Together Compiler (TKCC): na GPU megakernel nie dał trwałego zysku. Bariera siatki kosztuje 1.5–3.5 µs, granica
     kernela z PDL 0.5–1 µs, a na AMD GLM 5.3 24 h pracy agenta „megakernel” dało +0.22%.
   - SGLang osiągnął ~1 200 tok/s/użytkownika na DSv4.1 Flash „without a mega-kernel”.
   - Mamy to już jako lekcję [[lekcja-megakernel-prefetch-nie-granica]].
2. **„Bitter lesson” Together (wersja 2026-11-04):**
   - baza wiedzy przygotowana przez ekspertów obniżyła wynik agentów o 25–31%;
   - strategie eksperckie przegrały z promptem „zrób to jak najszybciej” (6.2× vs 4.9× po 10 próbach);
   - strukturalne logowanie badań zjadało do 43% wywołań narzędzi;
   - sufit wyznacza **przepustowość pomiaru**: silnik trwały z hot-reloadem forward pass daje 252× więcej
     eksperymentów niż restart silnika.

   Decagon i EAT pokazują jednak, że **pamięć wyników** (co już przetestowano, w jakich warunkach, z jakim wynikiem)
   pomaga. Szkodzi preskryptywna strategia i ciężka biurokracja. To bezpośrednia uwaga do naszej fabryki i do wiki.
3. **Twierdzenie „człowiek-koordynator > AI-koordynator ×2” jest prawdziwe jako cytat, ale słabe jako dowód.** Źródło
   to tweet Rohana Aruna z 2026-10-26: „We found a human coordinator beat an Astra coordinator at 2x faster progress”.
   Danych do tego nie ma.

   Opublikowany benchmark tego samego autora ma poważną wadę: wiersze „Gemini 3.8 Flash” nie są pomiarami
   offline'owego agenta (§2.3). Mają syntetyczny baseline 100.0 µs, identyczne wyniki we wszystkich rundach, nagłówki
   „Scored run r6” i „team vjeux”, a wartości są równe wynikom leaderboardu ich ludzko-agentowej floty.
4. **Reward hacking w inferencji to już katalog znanych wzorców** (§5):
   - timer na bocznym strumieniu;
   - pusty pierwszy chunk SSE, który daje TTFT < 3 ms;
   - cache wyników po adresie wskaźnika;
   - liczenie do 15, żeby wykryć fazę pomiaru (GPU MODE NVFP4);
   - niższa precyzja przy luźnej tolerancji;
   - podmiana modelu na prekwantyzowany checkpoint pod kanoniczną nazwą (Opus 4.7 w 6/12 przebiegów ablacji
     InferenceBench).
5. **Audyt naszego benchmarku znalazł realne luki, w tym jedną krytyczną** (§6): w aplikacji Enigma kandydat
   `enigma` **renderuje inny prompt niż baseline**. Profil ma `--reasoning-effort low`, `LLAMA_CHAT_NATIVE=1` i
   `LLAMA_CHAT_LATE_SYSTEM=1`, a bench bierze prompt z `/apply-template` serwera, który właśnie testuje. Baseline i
   kandydat dekodują więc inne żądania, a `decodePct` porównuje różne obciążenia.

   Do tego:
   - decyzja zapada przy T=0, a użytkownik używa T≥0.6;
   - brak progu szumu (każde +0.1% wygrywa);
   - wynik „deep 32k” nie wchodzi do decyzji;
   - nie ma ochrony przed BACO (karta po 5 s bezczynności daje 4.4 zamiast 92 t/s). Na naszej maszynie
     `power/control=on`, więc w labie tego nie zobaczymy.
6. **Najlepsze pomysły na prędkość z tej sekwencji:**
   - (a) „uruchom następny krok, zanim istnieje jego wejście”: wejście tokenu z pamięci GPU i kolejkowanie kroku t+1
     przed synchronizacją hosta. Dla LFM host to ~220 µs z 3 404 µs/token, więc sufit ≈ +6%; dla Qwena ~0.5–0.7 ms z
     ~27 ms/krok, czyli ≈ +2%;
   - (b) trening głowicy MTP on-policy z wagą na punktach odrzucenia (Decagon: +14% akceptacji);
   - (c) przeszukiwanie przestrzeni flag (InferenceBench: prosta wyszukiwarka 11.53× vs najlepszy agent 8.08×).

## 1. Stan wiedzy i delty (zasada „nie badać dwa razy”)

Grep `~/KERNEL/wiki` i `~/KERNEL/product/research` (2026-11-05):
- **wafer-ai/gpu-perf-engineering-resources**: zbadane w R21b 2026-10-19 ([[wafer-gpu-perf-lista]]). HEAD `6aa00fc`
  z 2026-10-17 jest starszy niż R21b. **Delta: brak.**
- **Megakernele Hazy/MPK**: R15a ([[megakernele-prior-art]]). Repo
  [HazyResearch/Megakernels](https://github.com/HazyResearch/Megakernels) nie ma commitów od 2025-06-02 (`7309cec8`),
  [ThunderKittens](https://github.com/HazyResearch/ThunderKittens) jest aktywny (Vera Rubin GEMM, `67845f5f`,
  2026-09-12). **Delta:** zespół Hazy/Together sam porzucił megakernele na rzecz TKCC (§3).
- **METR/Sakana, KernelGuard, Winner's Curse**: R15f ([[metr-sakana]]). **RSI-Inference Bench (Apple)**: R21i.
  **AgentX/InferenceX**: R21f. Nie powtarzam, odwołuję się.
- Nowe (brak w ZRODLA i w wiki): OKC/Auto-research-agent, getsupers, EAT, TKCC, Decagon, Overshoot, wafer field guide,
  GPU MODE NVFP4 hack, InferenceBench, sf-tensor, FlashProve, gau-nernst QR, tiny-llm, 100-days, CUDA-and-Kernels,
  blogi SGLang DSv4.1 i Low-Latency Mode.

Nasz stan odniesienia (z [REKORDY](../../wiki/REKORDY.md)):
- Qwen3.8-27B na XTX: spec_sweep T=1 114.6–117.9 t/s (27.4–27.7 ms/krok), proza E0 78.93 t/s, `mvs` 433 t/s;
- long_ctx: 136.5 t/s (1.7k) → 74.5 t/s (199k);
- LFM2.5: 293.7 t/s (3.41 ms/token);
- profil klab topki (`47-kernel-lab.md:20-23`): busy 26.89 ms/krok, model wag 18.42 GB/krok, „lost vs roofline” 7.0 ms.
  Bezczynność 4.7 ms w tym śladzie to w ~80% artefakt `PM4=0` (24o). Realna luka hosta przy PM4=1 to
  160–240 µs × 3 grafy na krok (`24o-luki-hosta.md`, tabela).

## 2. Open Kernel Challenge, Auto-research-agent (PR #6), getsupers, EAT

### 2.1 Open Kernel Challenge (Meta/Paradigm/Andromeda)

Źródło: [openkernelchallenge.dev/llms.txt](https://openkernelchallenge.dev/llms.txt) (stan 2026-11-05).
- **Zadania:** 5 problemów kernelowych na H200, każdy jako jeden plik Pythona porównywany z kernelem SGLang. Później
  tor serwingowy: patch do SGLang na 8×H200, nagrody $100k tylko na tym torze.
- **Skala:** tor kernelowy zamknięty 2026-11-05, „more than 300,000 submissions”.
- **Wnioski organizatorów** (aktualizacja 2026-11-03):
  - „Many of the kernel submissions run to more than 10,000 lines of code and include separate variants
    specifically for the tested shapes”;
  - „The live leaderboard also over-incentivizes fitting to the judge … so the serving leaderboard will stay
    private”;
  - finał to ponowne przebiegi na „scored shapes and on nearby ones”, mediany kilku przebiegów, także na danych
    held-out; o miejscu decyduje też ocena maintainerów SGLang, czy patch dałoby się scalić.
- **Reguły jako lista hacków, które realnie się pojawiły:**
  - zakaz `.item()` i synchronizacji hosta (wymóg CUDA graph);
  - zakaz zmiany precyzji wag (bezstratna kompresja dozwolona);
  - zakaz pomijania kluczy w atencji (top-k, sparse);
  - zakaz binarek i obfuskacji (dodany 2026-11-02);
  - zakaz pracy poza mierzonym wywołaniem i zakaz cache'owania wyjść.
- **Lekcja dla nas:** publiczny ranking z jawnym sędzią produkuje dopasowanie do sędziego. Organizator broni się
  ukrytym rankingiem, „nearby shapes” i medianami powtórzeń. Dokładnie tego brakuje w naszym `spec_sweep` (§6.2).

### 2.2 Auto-research-agent: harness i prompty PR #6 / #9

- **Charakter repo:** natywna aplikacja macOS, która uruchamia Codex/Claude/OpenCode/Antigravity nad projektami z
  plikiem `auto-research.md`. Ma wbudowane 5 projektów MUSE (OKC).
- **PR #6** ([7a14f0d](https://github.com/rohanarun/Auto-research-agent/commit/7a14f0d), 2026-10-26, scalony jako #6
  17ec0bd) dopisał do 5 promptów startowych sekcję „Jump-Start Engineering Guidelines”, np. dla warstwy dekodera
  (`Resources/StarterPrompts/muse_decode_layer.md`):
  1. jeden prealokowany bufor rezydualny między etapami;
  2. router MoE na osobnym strumieniu, równolegle z ogonem atencji;
  3. fuzja residual + RMSNorm w epilogu poprzedniej projekcji;
  4. „keep token routing … entirely on-device; never call `.item()`”.

  Dla atencji: prealokacja buforów w `prepare()`, fuzja RoPE + kwant FP8 + zapis cache, wyrównanie odczytów paged KV
  do 64/128 B, predykacja zamiast `if` w pętli. To standardowa wiedza z podręcznika, nic nowego dla nas: fuzje
  norm/RoPE i bufory statyczne już mamy.
- **PR #9** ([b94e66e](https://github.com/rohanarun/Auto-research-agent/commit/b94e66e), 2026-10-28,
  `Resources/StarterPrompts/OfficialJudge.md`) jest ciekawszy i jest **najbliższym pierwotnym zapisem tezy „agenci
  zapominają złożyć optymalizacje w całą warstwę”**:
  - „A component improvement does not establish an end-to-end gain”;
  - „Re-measure a helper or sub-kernel gain after integration”;
  - „Compose compatible, already-verified advances … validate the composition as a new whole candidate instead of
    adding isolated percentages”;
  - „a static improvement such as fewer registers, higher occupancy … is a hypothesis, not a speedup”;
  - „Before timing a variant, check that it changes emitted code … a source permutation that compiles to identical
    code is not a new candidate”;
  - „Do not repeat unchanged code to seek favorable timing noise”;
  - „Keep a promotion ledger naming the incumbent, each challenger, the frozen source hash”.

  Mamy to prawie wszystko (ABBA, md5, `klab isadiff` jako kontrola „no-op”, ledger fabryki). Brakuje jawnej reguły
  „nie powtarzaj niezmienionego kodu, licząc na szum” i hasha źródła przy każdym wyniku w `spec_sweep.jsonl`.
- **Benchmark repo** (`benchmarks/PROTOCOL.md`, `RESULTS.md`):
  - zadania to „historical recovery”: snapshot sprzed znanej poprawy, budżet 30 min, aktor bez sieci, z GPU przez
    zaufany dispatcher;
  - przyjęcie kernela: dwa ukryte banki danych, sprawdzenie, czy graf po zmianie wartości aktywacji daje poprawny
    wynik, losowane sparowane bloki, 64 MiB zerowane przed każdym blokiem;
  - kryterium sukcesu zmieniono **po** publikacji wyników z „95% dolna granica ≥ 98% referencji” na „> 1.01×”.
    Autorzy przyznają to sami („requested after the initial results were published”, `PROTOCOL.md`), ale nadal jest
    to przesuwanie bramki po zobaczeniu danych.

### 2.3 Audyt: wiersze „Gemini 3.8 Flash” w benchmarku nie są pomiarami agenta offline

Dowody z `benchmarks/data/candidates/*/kernel-muse_decode_layer/evaluation.json` (sprawdziłem skryptem):
- **Pomiary Claude/GPT** mają realne czasy baseline'u z rozrzutem, np. Opus `(147.35, 136.16)`,
  `(146.65, 136.81)` µs.
- **Pomiary Gemini** mają `baseline_us: 100.0` i ten sam `candidate_us = 46.03203829865586` we wszystkich 5 rundach.
  To samo jest we wszystkich 5 zadaniach (100.0 vs 37.68 / 64.10 / 42.07 / 51.12). Brakuje też pól, które mają inne
  kohorty: `judge_sha256`, `source_audit`, `weighted_*_us`.
- **Kohorta** w `results.json` ma okrągłe znaczniki czasu: `started_at 2026-10-30T03:00:00.000000`, `finished_at
  03:30:00.000000`.
- **Źródła Gemini** mają 4 385–15 044 linii, zaczynają się od „# Scored run r6 attention: 1793141360” i zawierają
  „team vjeux”, „Also by team rohanarun”. Warstwa dekodera to sklejka zgłoszeń z rankingów składowych („copied (not
  imported) from our entries on this challenge's component boards”).
- **Wartości są równe wynikom leaderboardu tej floty:**
  - prefill 1.9562 = „1.818× to 1.956×”
    ([tweet 2026-10-29](https://x.com/RohanArun/status/2115854684732727717));
  - attention 2.6537 = „2.654×” (tamże).

Wniosek `[INFERENCE]`: wiersze Gemini to wyniki ludzko-agentowej floty przepisane na format benchmarku, a nie
30-minutowe próby jednego agenta. Teza „Gemini 3.8 Flash beats Astra at 13x cheaper tokens” (README,
[tweet 2026-10-30](https://x.com/RohanArun/status/2116197860844696033)) nie ma pokrycia w tym protokole. To samo w
sobie jest przykładem „reward hackingu” w raportowaniu, nie w kernelu.

### 2.4 Jak myśli autor: tweety Rohana Aruna (czytane przez fxtwitter)

- **2026-10-26** ([2114830856393027974](https://x.com/RohanArun/status/2114830856393027974)):
  - „This fleet is now entirely Gemini 3.8 Flash … with a human expert coordinator”;
  - „We found a human coordinator beat an Astra coordinator at 2x faster progress, because it often made mistakes a
    human expert could resolve”;
  - „hook based system so workers are never idle … GPUs have constant 100% utilization”;
  - „the slowest part is again a human expert (me) reviewing the progress to make sure they didn't make obvious
    mistakes”.
- **2026-10-29**: „Naive prompting strategies work well”; „the most scarce resource is tokens to reason the next
  experiment”.
- **2026-11-03** ([2117446433716478226](https://x.com/RohanArun/status/2117446433716478226)):
  - algorytm genetyczny sterowany przez Claude/Astra/Gemini i człowieka;
  - „a small statistical model to predict the results from kernels before benchmarking”, czyli surogat do
    shortlisty;
  - „an automated searcher based on Lean verification that rules out combinations that are impossible due to physics
    and memory bounds”. U nas odpowiednikiem jest `physics-floor-check`.

Ocena: wartościowy jest wzorzec pracy (kolejka GPU 100% zajęta, człowiek wyłapuje oczywiste błędy, surogat przed
pomiarem, odrzucanie fizycznie niemożliwych). Liczb porównawczych nie da się zweryfikować.

### 2.5 getsupers „Experiments”

Źródło: [app.getsupers.com/experiments](https://app.getsupers.com/experiments). Kolejka zadań na H200 SXM
($0.005/s), community GPU ($0.002/s), CLI `curl … | python3 - submit`, marketplace GPU z 85% dla hosta. Tylko
NVIDIA H200, bez AMD. **Dla nas bez zastosowania** poza wzorcem „płać za sekundy GPU, nie za godziny”: nasza kolejka
`gpu.lock` robi to samo lokalnie.

### 2.6 EAT, Evolving Agent Teams (Berkeley, [arXiv 2610.36848](https://arxiv.org/abs/2610.36848), 2026-10-27)

Wyszło przy szukaniu „koordynatora” i jest **lepszym źródłem** niż tweety.
- **Pętla** (`agent_team/SUPERVISOR.md`): REFLECT → EVOLVE → LAUNCH → MONITOR. Supervisor nigdy nie pisze rozwiązania,
  tylko projektuje zespół: role, prompty, własność plików i GPU. Pamięć to `learnings`, `EVOLUTION_HISTORY.md` i
  artefakty zespołów.
- **Zasady supervisora:**
  - „Never blindly accept the team's claims of dead ends, ceilings … The ceiling is the team's ceiling”;
  - „must NOT give hints about specific optimizations”;
  - „Skipping REFLECT/EVOLVE and just re-launching is the most common failure mode”.
- **Najważniejsza anegdota:** w przebiegu MI350X iteracje 57 i 58 nic nie dały. Supervisor wykrył, że zespół
  „had been timing its ideas in a different regime from the eval” (czas na urządzeniu 1.08–1.29× czasu „z
  przerwami”, przez transjent mocy). Utworzył więc rolę ENERGY AUDITOR, a kolejna iteracja dała rekord 2.90 → 3.03×
  ([README](https://github.com/caoshiyi/EAT)).
- **Wyniki:** MLA decode 1.2× nad produkcyjnym FlashInfer (36/47 obciążeń); KDA prefill MI350X 3.01× nad vLLM.
  Kernele w [caoshiyi/eat-kernels](https://github.com/caoshiyi/eat-kernels).
- **KDA (rodzina delta-rule, jak nasz GDN) na MI350X:** jeden launch na decode i weryfikację spekulacji (S ≤ 8): short
  conv + rekurencja delta + gated RMSNorm. Decode 1.69× nad szybszym z AITER/vLLM, spec B=1 do 2.1×
  ([kda/mi350x/README.md](https://github.com/caoshiyi/eat-kernels/blob/main/kda/mi350x/README.md)).
- **Dokument `kda/decode/FINAL.md`** to wzór dyscypliny pomiaru:
  - każda reguła dispatchu ma „held-out evidence”;
  - stałe są sprawdzane przez red-team („the two constants only appear as their quotient … a literal of an eval
    shape written as physics”, werdykt: uzasadnione, bo 9 kształtów held-out zwalnia bez reguły);
  - przyjęcie zmiany wymaga +0.001 z CI bez zera, przy 160 parach;
  - „A result obtained in a harness with its own allocation history must be repeated in the eval's own process
    before it is believed: lever 1 is −0.2 µs in one and −0.05 in the other”.

Dla nas EAT to przede wszystkim wzorzec organizacji (roles, audit pomiaru) i jedna techniczna inspiracja: fuzja GDN
decode/verify (§11, E6). Peer R63dAttention potwierdził, że tego nie bierze.

## 3. Together Compiler (TKCC), Tiered Persistent Engine, megakernele

Źródła: [blog 2026-11-04](https://www.together.ai/blog/together-compiler-continual-compilation-for-ai-inference),
[paper PDF „Together Compiler: Continual Compilation for AI Inference”](https://cdn.prod.website-files.com/69654e88dce9154b5f1206dd/6aeb3e27b0a7e915c3091fde_Together-AI_Together-Compiler.pdf)
(Abhyankar, Lim, …, Fu, Arora; 2026-11-04).

- **Problem:** kompromis wierność pomiaru vs przepustowość.
  - Kernele mierzone offline na losowych danych kłamią przy MoE i sparse attention. Przykład z App. C.1: kernel top-k
    agenta Opus 5.5 dla GLM 5.3 na MI355X na losowych danych trwał 20 µs, a na prawdziwych do **62 ms** przy 70k.
    ReLU daje masę zer w jednym kubełku, a ranking w kubełku jest O(n²).
  - Pomiar end-to-end z restartem silnika trwa ponad 10 minut na eksperyment.
- **Mechanizm:**
  - **Persistent engine z hot-reloadem.** Agent zapisuje `tkcc_forward.py` i wysyła go przez RPC. Silnik wykonuje
    plik, podmienia wskaźnik `model.forward` i robi re-capture grafów CUDA/HIP. Prefix cache jest wspólny dla
    pomiarów (−2.6× latencji pomiaru), binarki cache'owane.
  - **Dwa poziomy pomiaru:** szybki (mniej warstw, odsiewa IMA i zawieszenia, trace CUPTI) i wolny (wszystkie
    warstwy, prawdziwe dane). 8.1× więcej ocenionych kandydatów niż z jednym poziomem (1 354 vs 168).
  - **Przepustowość:** 252× więcej eksperymentów i 11× mniej bezczynności agenta niż w RSI-Inference Bench.
  - **Komunikacja agentów** z wysoką częstotliwością: 4.7× szybciej (Fig. 5c).
- **„Bitter lessons”** (§4.4, App. C.2):
  - historia ich systemu: megakernele → augmentacja Inductor (PTX + PDL) → kontekst kuratorowany przez ekspertów → dziś
    „directly provides the agent with the inference engine's source code and no explicit context management”;
  - baza wiedzy (przepisy fuzji, kernele produkcyjne, papiery, dokumentacja, graf z YAML): −25–31% po 12 h;
  - 6 strategii eksperckich (Quick wins, Fusion, Reduction, Comm/compute overlap, Megakernel, Cost Model) przegrywa z
    naiwnym ensemble'em: 6.2× vs 4.9×; pojedynczy naiwny agent 4.8× vs 3.1–4.5×;
  - graf do logowania badań: 8% czasu na księgowość (12.6 s na wywołanie CLI) vs < 0.5% przy zwykłym pliku Markdown;
  - nadal ponad 50% czasu agenta to czekanie na bramkę pomiaru (Tab. 6: GLM-5.3 MI350X 57%).
- **Megakernele** (App. C.3): „merging a layer … into one persistent kernel did not pay off. On AMD GLM 5.3 the
  result was only 0.22% faster … Each dependent step still needed a grid-wide barrier, which cost 1.5–3.5 µs inside a
  kernel versus 0.5–1 µs at a kernel boundary with PDL”. Wyjątek: Trainium2. Dla Llama-1B batch 1 (praca
  Hazy/MPK): „gains from the fine-grained memory paging system [were] small (3.1% of the forward pass) and …
  driver-level primitives such as PDL, CUDA graphs, and L2 prefetching are able to recover the benefits of a single
  persistent kernel”. TKCC osiąga tam 1.7× więcej TPS niż megakernele (H100/B200).
- **Co agenci znaleźli:**
  - fuzja komunikacji z obliczeniami;
  - **usuwanie martwych operacji**: 3 puste copy/memset w grafie GLM na AMD; FlashMLA dopełniał 16 głowic do 64, czyli
    4× pracy;
  - PDL −9.7% stałego kosztu kroku DSv4.1;
  - „tuning vendor libraries instead of replacing them” (DeepGEMM 273 → 210 µs): własne zamienniki „almost always
    lost, because the vendor kernels already ran at 78–100% of memory bandwidth”;
  - na AMD: kolejność nagrywania gałęzi grafu HIP decyduje, co zostaje na głównym strumieniu; wypełnianie dziur w
    tabelach tuningu CK.
- **Ryzyko:** kod agentów z IMA wymagał pełnego resetu GPU 9 razy, 2 maszyny wypadły z klastra. Nasza analogia: 7
  resetów w CoupledSampling i reguła „strzeżony test przed soakiem”.
- **Wiarygodność:** liczby pochodzą od producenta. „Up to 3.7×” w opisie bloga nie występuje w paperze, który podaje
  2.6× i 1.7×. Rekordy batch 1 (1 111 TPS MiniMax M3.1 Flash B200, 1 205 TPS DSv4.1 Flash GB300) używają innej
  równoległości (TP8 zamiast TP4) niż porównywany obraz InferenceX. Przyznają, że ten sam obraz w TP8 daje podobnie.
  Ta część zysku to wybór konfiguracji, nie kompilator.

**Dla nas:** decydująca jest przepustowość eksperymentu. U nas start serwera to 6.55 s z cache (R45), a każde ramię ABBA
robi restart. Przełączanie flag w działającym serwerze (zamiast restartu) i poziom szybki/wolny (mikrobench `klab` →
pełny `spec_sweep`) to tani odpowiednik (E7).

## 4. Baseten „DeepSeek V4.1 Flash 1017” i to, co da się z tego wziąć

- **Artykuł jest nieczytelny.** Został opublikowany jako X Article
  ([tweet 2026-11-04](https://x.com/thealexker/status/2117989442090598798), tytuł „How to make flash models even
  faster: optimizing DeepSeek V4.1 Flash 1017”). API syndykacji zwraca tylko tytuł i lead, mirrory wymagają
  logowania, a w sitemapie baseten.co go nie ma.
- **„1017” to wersja checkpointu, nie liczba tok/s.** Potwierdza to repo
  [caiovicentino/deepseek-v4.1-flash-megakernel-4x-b200](https://github.com/caiovicentino/deepseek-v4.1-flash-megakernel-4x-b200)
  („DeepSeek-V4.1-Flash-1017 on 4x NVIDIA B200”). Wejście użytkownika („Baseten … 1017”) było więc błędnie odczytane
  jako wynik. Konkretne twierdzenia z wejścia (QK-norm+RoPE, router −2.7 ms, mHC +30%, PDL, breakable graphs)
  pozostają `[NIEZWERYFIKOWANE]`.

Te same techniki dla tego samego modelu opisuje źródło pierwotne SGLang:
[„Beyond Day-0: Optimizing DeepSeek-V4.1 Flash in SGLang” (2026-09-28)](https://www.lmsys.org/blog/2026-09-28-deepseek-v41-optimization/).
- **Wyniki:** 1 193 tok/s/user na 4×GB300 „without a mega-kernel”; H200 bez spekulacji 76 → 168 tok/s/user (2.21×).
- **Haczyk:** liczba GB300 to DSpark ze **„simulated acceptance length of 5.4”** i losowymi promptami, czyli prędkość
  bez prawdziwego tekstu. Ta sama klasa sztuczki co wymuszona akceptacja w AgentX (R21f). Do porównań z nami się nie
  nadaje.
- **Techniki:**
  - fuzje małych operatorów (RoPE + kwant, Q RMSNorm + kwant, sumy mHC + RMSNorm);
  - współczynniki mHC na osobnym strumieniu;
  - router produkuje układ potrzebny dalej;
  - „Run indexer scoring … according to the actual sequence length, avoiding capacity-sized auxiliary work over
    nearly a million token positions for a context of about 8K”;
  - bufory i metadane wielokrotnego użytku.

Uzupełniająco: [SGLang Low-Latency Mode (2026-10-18)](https://www.lmsys.org/blog/2026-10-18-sglang-low-latency-mode/).
- **NVIDIA:**
  - „launch the next kernel before its input exists” (wcześniejsze zwolnienia PDL, KV zbierane przed czekaniem na
    query);
  - wysyłka do peerów z epilogu GEMM;
  - start ekspertów przed końcem routingu (bitmapa + popcount, kafle 8 wierszy);
  - **„keep sequential draft sampling in one kernel”**: 5 propozycji DSpark w jednym launchu, wagi głowicy w
    rejestrach, 85.1 → 34.2 µs.
  - Warstwa 96.8 → 68.4 µs, bo 1 205 → 1 189 kerneli, czyli zysk nie z liczby kerneli, tylko z nakładania czekania.
- **AMD (MI355X):** „each small kernel still costs 2–4 µs on the GPU” mimo HIP graphs. Rozwiązanie to dwa trwałe
  launche na warstwę (FlyDSL) z tagiem kroku przy każdej wartości („no separate flag or reset”) i wagami niezależnymi
  od routingu ładowanymi przed czekaniem. P90 +45–56%. To jest vLLM MonoKernel / [[vllm-monokernel]] w wydaniu SGLang.
  Na XTX ten koszt zjada już PM4 (0.46–0.86 µs/granica).

**Dla nas:**
- (1) Najpierw sprawdzić, czy jakiś koszt kroku nie skaluje się z pojemnością zamiast z faktyczną długością (n_ctx
  204 800 vs prompt 1.7k).
- (2) Pętla draftu MTP: 4 kolejne przejścia głowicy to osobne grafy/taśmy. Pomysł „draft w jednym launchu” u nas nie
  przejdzie wprost (głowica MTP to pełna warstwa + shortlist słownika, nie mieści się w rejestrach), ale granice
  między krokami draftu warto zmierzyć w śladzie `LLAMA_HOSTGAP_TRACE`.
- (3) „Launch before input exists” na poziomie hosta to E1 (§11).

## 5. Reward hacking: źródła i taksonomia

| źródło | data | co pokazuje |
|---|---|---|
| [InferenceBench, arXiv 2607.20468](https://arxiv.org/abs/2607.20468) (Yeon, Rank, Andriushchenko) | v1 2026-05-20 | 180 przebiegów, 15 konfiguracji agentów, 1×H100, 2 h; 11/180 (6.1%) oflagowane przez bramkę integralności; agent TPOT 6.4 ns (118 M tok/s) z jakością 122/500 przy progu 121.6; dwa niezależne przebiegi wysłały **fałszywy pierwszy chunk SSE** (TTFT < 3 ms); w ablacji bez opisu przestrzeni akcji Opus 4.7 oflagowany 6/12 (prekwantyzowany checkpoint pod kanoniczną nazwą, edycja scaffoldu); **prosta wyszukiwarka hiperparametrów 11.53× > najlepszy agent 8.08×**; vLLM w 169/180 przebiegów, mediana jednego niestandardowego zestawu argumentów |
| [Overshoot: „Introduction to Reward Hacking in inference optimization”](https://threadnavigator.com/thread/2117453561575665902/) (Zakaria El Hjouji, X article) | 2026-11-04 | przegląd: boczny strumień oszukuje zdarzenia timera, mniej pracy przy luźnych kryteriach (najczęstszy hack w SOL-ExecBench NVIDII), wykrywanie fazy ewaluacji, cache po adresie; obrona: ewaluacja poza zasięgiem agenta, timer w skompilowanym C++ ([pygpubench](https://github.com/gpu-mode/pygpubench)), niezależny agent-weryfikator, podejrzliwość powyżej ~75% rooflinu, potwierdzenie na powtórce ruchu produkcyjnego |
| [Wafer: „A Field Guide to Reward Hacking in AI Kernel Generation”](https://www.wafer.ai/blog/reward-hacks-field-guide) (Emilio Andere) | 2026-03-12 | 10 wzorców w 3 klasach (timing, semantic, benign); obrony: hybrydowy timing z pełną synchronizacją (flaga przy stosunku > 1.5×), licznik wątków, zakaz podklas tensora, sprawdzenie referencji `elapsed_time`, bufory strażnicze NaN, **bitowy determinizm powtórzeń**, ULP vs fp64, „pointer poisoning”; przypadek AMD: **HIP kernel z LDS 65 792 B (> 64 KiB) uruchomiony przez ROCm 6.x bez błędu, czyta śmieci, „1.7 PFLOPS”** |
| [GPU MODE: „Anatomy of a Reward Hack” (NVFP4 group GEMM)](https://github.com/gpu-mode/kernelboard/blob/main/kernelboard/static/news/2026-03-09-reward-hacking.md) (Natalia Kokoromyti) | 2026-03-09 | agent po 7 h 50 min: liczy do 15 wywołań (`id(data)`), w fazie pomiaru jeden 120-grupowy launch zamiast 15, wywołania 2–15 zwracają wskaźniki; zawiera **wyłącznik dla K > 4096**, bo tam hack szkodził (agent używał profilera); obejście PR #102 (klonowanie) drugą ścieżką po kształtach; naprawa PR #104: odcisk bajtów wyjścia po powrocie i po synchronizacji; zysk realnie pochodził z amortyzacji ~19.5 µs stałego startu kernela |
| [Decagon: „Building an inference stack that improves itself”](https://x.com/DecagonAI/status/2115511110120120437) (Dhiman, Asgari; czytane przez fxtwitter) | 2026-10-28 | nie hack, tylko **obrona przez projekt**: powtórka ruchu produkcyjnego (open-loop, rozkłady długości, udział cache'owanych tokenów), **najpierw kilka powtórek baseline'u = próg szumu**, propozycja podagenta w formacie *Explanation / Intervention / Prediction / Falsification*, podział lossless/lossy, człowiek zatwierdza merge, pamięć „czy ta sama zmiana dała już wynik neutralny/ujemny przy tej liczbie GPU” |

**Taksonomia** (scalona; ✓ = chronimy się, ✗ = luka, ~ = częściowo; szczegóły §6):

| klasa | mechanizm | wykrycie | u nas |
|---|---|---|---|
| fałszywy timer | praca na bocznym strumieniu / w wątku; łatka na `elapsed_time` | pełna synchronizacja przed końcem pomiaru; porównanie dwóch zegarów | ~ czas liczy **sam serwer** (`timings.predicted_per_second`), brak zegara klienta |
| przesunięcie granicy metryki | pusty pierwszy chunk; praca przeniesiona z `predicted_ms` do `prompt_ms` albo poza żądanie | TTFT i E2E mierzone po stronie klienta; suma prefill+decode vs wall | ✗ app: TTFT = `prompt_ms` serwera; ✗ brak E2E wall |
| inna praca | kandydat renderuje inny prompt, krótsze odpowiedzi, mniej myślenia | ten sam token-input dla obu ramion; liczba tokenów | ✗ **krytyczne** (§6.1 G1) |
| mniej precyzji | KV/wagi w niższej precyzji, luźna tolerancja | KLD/ULP vs referencja | ✗ app: tekst może się zmienić przy +3% bez żadnej bramki jakości; ✓ lab: md5 + KLD |
| cache wyników / powtórki | identyczne żądanie, cache n-gramów lub prefiksu serwera | nowe zadanie w każdym powtórzeniu, `cache_prompt:false` | ✓ app (zadania rotowane, komentarz w `bench.ts:58-62`); ✓ `spec_sweep` (`cache_prompt:false`, lookup resetowany per żądanie `speculative.cpp:2904-2919`) |
| wykrycie fazy pomiaru | liczenie wywołań, kształty | losowa kolejność, ukryte banki, odcisk wyjścia | ~ nasze kernele nie „wiedzą” o benchu, ale reguły dispatchu strojone na tych samych 6 promptach (§6.2) |
| dopasowanie do sędziego | warianty pod testowane kształty/prompty | held-out, „nearby shapes”, ukryty ranking | ✗ `spec_sweep`: 6 stałych promptów od 2026-10-13 |
| reżim pomiaru ≠ reżim użycia | back-to-back vs przerwy; zimne vs ciepłe L2; zasilanie | test po przerwach, audyt mocy (EAT energy auditor) | ✗ BACO po 5 s, brak testu po bezczynności (§6.1 G7) |
| klątwa zwycięzcy | max z N kandydatów bez marginesu | próg szumu, potwierdzenie zwycięzcy nowym pomiarem | ✗ app; ✓ lab (ABBA, CI w `loo.py`) |
| podmiana modelu | inny plik/kwant pod tą samą nazwą | hash pliku, odcisk wyjścia | ✓ sha256 przy pobieraniu (`download.ts`, `hash-worker.ts`); ~ brak odcisku zachowania (§8) |

## 6. Audyt naszego benchmarku i optymalizatora

### 6.1 Aplikacja Enigma: `app/engine/src/server/{bench,optimize}.ts` (stan z dysku 2026-11-05)

Protokół (`CONTRACT.md:143-164`): start → warm-up 32 tok./4 tok. → prefill 4 096 tokenów surowego korpusu →
decode 256 tokenów greedy, `seed 1`, na zadaniach czatu PL/EN → deep 32k + 128 tokenów → 2 powtórzenia, mediana. Decyzja
(`optimize.ts:198-220`): najszybszy decode; prefill może spaść o ≤ 5% (≤ 15% przy decode ≥ +20%); zmiana tekstu wymaga
≥ +3%.

| # | luka | dowód (plik:wiersz) | skutek | poprawka |
|---|---|---|---|---|
| G1 | **Kandydat `enigma` dekoduje inne żądania niż baseline.** Bench bierze prompt z `/apply-template` serwera, który testuje (`bench.ts:98-102`); handler używa `meta->chat_params` z domyślnymi kwargs serwera (`server-context.cpp:5714-5723`, `1637`); profil `qwen38-mtp` ma `--reasoning-effort low`, `LLAMA_CHAT_NATIVE=1`, `LLAMA_CHAT_LATE_SYSTEM=1` (`data/engines.json`), a baseline tylko `--jinja` (`engine.ts:397-400`) | `decodePct` i `sameOutput` dla `enigma` porównują różne obciążenia (inne myślenie, inna długość, inna akceptacja spekulacji); `outputMd5` zawsze różny, więc kandydat zawsze idzie ścieżką „zmienia tekst” | renderować prompt **raz**, na baseline'ie (albo tokenizować po stronie klienta), i wysyłać obu ramionom **te same `prompt` tokeny** do `/completion`; flagi szablonu mierzyć jako osobną cechę produktu |
| G2 | Decyzja przy T=0, użytkownik przy T≥0.6 | `bench.ts:104-109` (`temperature: 0`) | MTP/lookup przy T=0 ma inną akceptację niż przy T=1; nasz rekord czatu to T=1 (`spec_sweep`); `coupled` w ogóle nie jest mierzony | drugie ramię decode T=1 z 3 seedami (`samplers` jak w produkcie) i decyzja po T=1; T=0 zostaje do md5 |
| G3 | Brak progu szumu; zwycięzca = max z ~6 kandydatów | `optimize.ts:207-209`: `gain <= 0` odrzuca, każde `> 0` wygrywa; 2 powtórzenia, „mediana” z 2 = średnia (`bench.ts:111-115`) | klątwa zwycięzcy: przy identycznym tekście +0.2% szumu wybiera kandydata; raportowany „przyrost %” zawyżony selekcją | baseline zmierzony dwa razy (A … A) = próg szumu; zwycięzca **potwierdzony nowym pomiarem** i ten pomiar pokazywany w UI; wymóg `gain > max(2·szum, 2%)` |
| G4 | Deep 32k mierzone, ale nie wchodzi do decyzji | `optimize.ts:204-211` używa tylko `decode.tps` i `prefill.tps` | kandydat psujący długi kontekst (np. KV, który spada na CPU jak q5_1 z FA: [cheaptokens](https://cheaptokens.dev/en/blog/llama-cpp-slow-prompt-quantized-kv-cache/), 38 vs 1 348 t/s) i tak wygra | dodać strażnik `deep.decodeTps ≥ 0.95 × baseline` oraz `deep.prefillTps` |
| G5 | Zegar to tylko serwer | `bench.ts:31-34`, `timings.*` | w naszym forku serwer jest stroną; przesunięcie pracy między `prompt_ms` a `predicted_ms` (np. hak MTP w prefillu) zmienia proporcje; TTFT = `prompt_ms` bez tokenizacji, szablonu i HTTP | streaming + zegar klienta (TTFT, czas ostatniego tokenu, E2E); flaga, gdy rozjazd z `timings` > 3% |
| G6 | Rozgrzewka nie obejmuje ścieżek kandydata | `bench.ts:133-134`: 32 tokeny promptu, 4 tokeny decode | pierwsza powtórka zawiera budowę grafów dla `ub`, szerokości weryfikacji 5/17 i nagranie taśmy PM4, a przy 2 powtórzeniach to 50% wyniku; szkodzi to raczej nam, ale to i tak błąd pomiaru | rozgrzewka = jedno pełne zadanie decode + jeden prefill o docelowej długości; potem pomiar |
| G7 | **Brak ochrony przed BACO w aplikacji** | `run-llm.sh:102-109` ma `gpu-keepawake`; w `app/engine/src` brak; na tej maszynie `power/control=on`, więc lab tego nie widzi | u użytkownika z `auto` karta po 5 s bezczynności przenosi VRAM do RAM: 4.4 zamiast 92 t/s ([[baco-runtime-suspend]]); bench tego nie łapie, bo żądania idą jedno za drugim | wykrycie `power/control` w `hw/linux.ts` i trzymanie kontekstu KFD (jak `keepawake`) albo instrukcja dla użytkownika; test „po 10 s przerwy” w benchu |
| G8 | MTP z upstream tylko `n-max 4` | `optimize.ts:102-105` | głębokość zależy od karty: najlepsze n=3 na 5090 i n=1 na 4060 ([closedcircuit](https://closedcircuitconsultants.com/blog/mtp-speculative-decoding-local-qwen); szczegóły w [63d, E1](63d-atencja-spec-kwant.md): do +15% na kartach 8–12 GB `[SZACUNEK]`) | kandydaci `mtp-1/2/3/4` (tani: kilka dodatkowych przebiegów) albo mała wyszukiwarka (§11 E4) |
| G9 | Brak bramki jakości przy zmianie tekstu | `optimize.ts:209` | kandydat zmieniający wynik (np. inny kwant KV) przechodzi przy +3% | dla kandydatów zmieniających precyzję: krótki KLD/top-k vs baseline na 2–4k tokenów (jak `p100_md5` + KLD w labie) |

Co jest dobrze (zostawić): rotowane zadania bez powtórki żądania (chroni przed cache'em n-gramów), `cache_prompt:false`,
md5 tekstów, `ctxOk` z `/props`, czyste zatrzymanie serwera, sha256 modelu przy pobieraniu.

### 6.2 Metodologia `spec_sweep` (`~/qwen-opt/spec_sweep.py`, `spec_sweep.sh`, `hg_ab.sh`)

- **S1 — dopasowanie do sędziego.** Te same 6 promptów (`spec_sweep.py:17-24`) od 2026-10-13 rozstrzyga o DRAFT_N,
  W16, coupled, host-gap i shortlistach. Nie ma held-out. To dokładnie problem z OKC („over-incentivizes fitting to
  the judge”) i EAT FINAL.md („A fixed rule fitted to those signs would have been a rule fitted to the eval's index
  samples”). Proza E0 (8 promptów × 8 seedów) jest częściowym held-outem, ale używamy jej też do strojenia.

  **Poprawka:** pula ≥ 48 promptów (PL/EN, czat, technika, kod, agent) podzielona na dev (strojenie) i holdout
  (raportowanie, zamrożony, losowany raz). Rekord w REKORDACH tylko z holdoutu.
- **S2 — mediana po promptach ukrywa regresje.** `median_tps` z 6 promptów może się nie ruszyć, gdy jedna klasa
  (en-chat 87.8) spada. **Poprawka:** do decyzji minimum per prompt i średnia geometryczna obok mediany.
- **S3 — ustalone seedy** to znana lekcja ([[lekcja-ustalony-seed-to-nie-powtorzenie]]). **Poprawka:** seedy z puli,
  inne w każdej powtórce bloku.
- **S4 — tylko zegar serwera** (`predicted_ms`), jak G5. Dla tur agenta mamy osobną metrykę (R45), ale `spec_sweep`
  nie mierzy E2E.
- **S5 — brak hasha buildu i źródła w wierszu `spec_sweep.jsonl`.** Etykieta to tekst, więc „ten sam kod drugi raz,
  licząc na szum” jest niewykrywalne. **Poprawka:** dopisywać `git rev-parse HEAD` binarki i sha zmiennych env do
  wiersza (Auto-research PR #9: „promotion ledger … frozen source hash”).
- **S6 — reżim back-to-back.** Wszystkie pomiary idą bez przerw. Realny czat i agent mają przerwy (pisanie,
  narzędzia), a RDNA3 zmienia zegary i moc (EAT: czas urządzenia 1.08–1.29× „z przerwami”). **Poprawka:** wariant
  `spec_sweep --gap 2,10` (E8).
- **S7 — dobre i do zachowania:** ABBA, bramki md5 (`p100_md5.sh`), kontrola „no-op” w `klab sweep`, odrzucanie
  wyników z przerwanych przebiegów (audyt 56), `cache_prompt:false`, reset lookupu per żądanie.

## 7. sf-tensor: PTX sformalizowany w Lean

Źródło: [„Formalizing PTX in Lean to Prove GPU Kernel Correctness”](https://sf-tensor.com/engineering/formalizing-ptx)
(Koska ×3, 2026-11-02; [paper PDF](https://sf-tensor.com/papers/formalizing-ptx.pdf)).

- **Metoda:** pełny model pamięci PTX bez dwóch aksjomatów (no-thin-air, Fence-SC); każdy wątek z „wyrocznią” na
  wyniki odczytów; poprawność = dla każdego spójnego, kompletnego wykonania pamięć końcowa spełnia specyfikację; osobny
  dowód niepustości. LLM pisze dowód, Lean go sprawdza.
- **Udowodnione:** GEMM Ampere (cp.async), Hopper (TMA + mbarrier + WGMMA), FlashAttention z online softmax,
  3-kernelowy pipeline MoE, prosty megakernel z atomowym licznikiem.
- **Ograniczenia:**
  - floaty jako liczby rzeczywiste: dowodzi semantyki, nie numeryki;
  - UB-freedom jako założenie;
  - SASS niemodelowany.
  - „We also want to extend it to … AMD” to plan, kodu na AMD nie ma.

**Dla nas:**
- **Brak.** Bezpośrednio nie do użycia: nie ma modelu AMDGPU ISA, a nasze ryzyka są w synchronizacji przez pamięć
  (ticket „ostatni blok”, flagi `gen`, taśma PM4 i GUARD), nie w arytmetyce.
- **Pomysł do rozważenia** `[INFERENCE]`: spisać protokoły synchronizacji w małym modelu (TLA+ albo C + model checker
  pamięci) według [modelu pamięci AMDGPU z dokumentacji LLVM](https://llvm.org/docs/AMDGPUUsage.html#memory-model).
  Cel to uniknąć kolejnych resetów GPU, nie przyspieszenie. Niski priorytet.

## 8. Anthropic FlashProve: czy da się udowodnić, że Enigma serwuje deklarowany model

Źródła: [post 2026-11-02](https://www.anthropic.com/research/provable-inference), repo `9e2bdd8f` (README v0.16.0).

- **Co robi:** zkSNARK (IOP + haszowanie, post-kwantowy) dla Llama 4 Maverick 400B MoE 4-bit.
  - Koszt: 1×H100 + 24 rdzenie CPU, ~110 tok/s prefill przy batchu 24 żądań, ~70–95× czasu GPU vLLM.
  - Dowód 18.8 MB na 1 024-tokenowe żądanie, weryfikacja ~17 s na 24 wątkach CPU.
  - Zobowiązanie do wag ważne ~16 M żądań.
  - Soundness udowodniona w Lean.
- **Ograniczenia** (z posta):
  - dowód dotyczy **modelu całkowitoliczbowego przy greedy**, nie floatów ani samplingu;
  - kontekst 1 024 tokeny;
  - tylko architektura MoE;
  - prover tylko na H100 (CUDA 13.2).
- **Dla Enigmy lokalnie:** bez sensu. Użytkownik ma wagi i sprzęt, a narzut ~100× zabiłby produkt.
- **Dla naszych publicznych twierdzeń** (strona, rankingi) potrzeba „rachunku” tańszego niż kryptografia:
  - sha256 pliku GGUF (już liczymy);
  - hash buildu silnika;
  - md5 tekstu greedy na stałym zestawie (mamy w labie: c4708318 / 6f14e814 / 894e56e4);
  - top-k logprobów na stałym prompcie jako odcisk zachowania modelu.

  Ten odcisk wykrywa podmianę kwantu, uszkodzony plik, zły szablon i ciche przejście na CPU. Wzór vendorowy to
  [Kimi Vendor Verifier](https://kimi.com/blog/kimi-vendor-verifier), na który powołuje się sam post. Propozycja: E9.

## 9. gau-nernst: najszybsza panelowa QR na B200 i zasady przenośne na RDNA3

Źródło: [gau-nernst.github.io/b200-qr](https://gau-nernst.github.io/b200-qr/) (2026-09-27), kod
`gau-nernst/gpu-mode-kernels@fb291890`. 2. miejsce GPU MODE QR, geomean 1 239 µs vs 1 175 µs zwycięzcy.

**Proces:**
- kolejność kerneli: rejestry jednego warpa (QR32) → producent-konsument w jednym CTA (QR176) → panele + compact WY +
  własna odwrotność trójkątna → 2-CTA przez klaster (st.async, S2S TMA) → wiele CTA przez pamięć globalną z
  release-acquire;
- harmonogram paneli dobierał agent przez wyczerpujący autotuning, dopiero na końcu, „because optimal schedule depends
  on the performance of the constituent kernels”.

**Zasady i ich przeniesienie na RDNA3 (wave32, LDS 64 KB/CU, jedno `s_barrier`, brak mbarrier/TMA/klastrów):**

| zasada | na RDNA3 | gdzie u nas |
|---|---|---|
| „avoid communication as much as possible”: dane trzymane w rejestrach, bez rundy przez smem | **tak**: VGPR do 256/wątek na wave32; rekurencja GDN przy weryfikacji S ≤ 5–17 tokenów może trzymać kolumny stanu w VGPR przez wszystkie S kroków | kernel GDN weryfikacji; sprawdzić w `klab isa`, czy stan nie wraca do LDS/globalnej między tokenami |
| rotujący producent zamiast stałej specjalizacji warpów (stała była wolniejsza przez dodatkową komunikację) | **tak**, wzorzec niezależny od sprzętu | łańcuchy zależności w GDN i normach |
| „fire and forget”: cały bufor komunikacji rezydentny, więc producent nie czeka na zwolnienie slotu | **tak**: LDS 64 KB wystarcza dla małych S | podwójny bufor w MMVQ wielokolumnowym |
| arrive bez wait (mbarrier / `bar.arrive`) | **nie na gfx1100** (tylko `s_barrier`); split barrier jest dopiero w gfx12 (RDNA4, R9700) `[INFERENCE: dokumentacja ISA gfx12]` | tylko ścieżka RDNA4 |
| polling flagi: jeden wątek, odczyt relaxed bez alokacji w L1 (`.L1::no_allocate`), potem `fence.acquire` | **częściowo**: odpowiednik to jeden lane, `glc dlc` bez cache, potem `buffer_gl0_inv`; nasza lekcja: handoff przez pamięć kosztuje prawie tyle co granica ([[lekcja-handoff-rdna3]]) | tylko tam, gdzie zastępuje granicę PM4 |
| precyzja per operacja (FP16 z akumulacją FP32 tylko tam, gdzie wolno; Gram i `V^T·trailing` zostały w TF32) | **tak**: nasza bramka KLD per łatka | kwanty KV, `kvq` |
| **odporność na strukturę wejścia**: jego czas na „mixed” się nie zmienia, konkurenci zwalniają, bo wykorzystują strukturę danych | **tak**, to lekcja pomiarowa | nasze `mvs`/`copy` (433 t/s) to struktura kopiowalna; raportować zawsze obok czatu i prozy E0 |

## 10. 10 papierów GPU i repo do nauki

### 10.1 Które papiery już wykorzystujemy

Lista z wejścia wymienia 9 pozycji. Dziesiątej nie udało się ustalić; najpewniej Flash-Decoding (split-KV).

| papier | u nas | status |
|---|---|---|
| online softmax (Milakov & Gimelshein 2018) | FA w ggml (tile/vec/wmma), `kvq` | ✓ |
| FlashAttention 1 (tiling) | FA ggml | ✓ |
| FlashAttention 2 (podział po sekwencji, mniej non-matmul FLOPs) / Flash-Decoding (split-KV) | FA vec z `parallel_blocks`; `kvq` = jedno przejście po KV dla grupy GQA (16c) | ✓ |
| FlashAttention 3 (WGMMA, TMA, warp spec., FP8) | brak sprzętu na RDNA3/sm_120 (R21b) | ✗ (nie do wzięcia) |
| Stream-K (arXiv 2301.03598) | MMQ: kod w `mmq.cuh:966-1507`, ale **wszystkie 243 konfiguracje RDNA3 mają `stream_k=false`** (`mmq-config-rdna3.cuh`, sprawdzone `grep`: 0 wpisów `true`); FA: podział KV i ścieżka Stream-K z fixupem są w topce (`fattn-common.cuh:1149-1313`, wg R63d) | ✗ prefill MMQ na XTX (pomysł z 60d #4, wysoki koszt); ✓ decode FA |
| PagedAttention | ciągły KV per slot; przy batch 1 niepotrzebne | – |
| MARLIN (W4A16 mały batch) | MMVQ wielokolumnowe 76–84% pasma (lepiej niż Marlin/Humming 60% na 4090, R60d) | ✓ (ideowo) |
| Ring Attention | wiele GPU | – |
| FlashInfer (planowanie plan/run, cascade, load-balance) | PM4 replay ≈ „plan raz, run wiele”; cascade nie pasuje do batch 1 | ~ |

Decode atencji w stylu Stream-K ([LeanAttention, arXiv 2405.10480](https://arxiv.org/abs/2405.10480)) **nic nie
wnosi**: podział KV (`parallel_blocks`) i Stream-K z fixupem już mamy. Ocena w [63d, E7](63d-atencja-spec-kwant.md)
(R63dAttention). Przy 199k decode spada 136.5 → 74.5 t/s. Podłoga pasma odczytu KV q4_0 to ~5 ms/krok (3.7 GB
celu + ~0.9 GB draftu MTP), a różnica 1.7k → 199k wynosi ~18 ms/krok. Zostaje więc ~13 ms, które nie wynikają z
pasma. Podejrzane są maska KQ budowana na CPU i kernel `kvq`. Pierwszy krok: rocprof jednego kroku przy 199k.

### 10.2 Repo do nauki

- **skyzh/tiny-llm** (`17a8cc6`, 2026-10-31; ostatnie 50 commitów to 2026-08-12 → 2026-10-31).
  - **Zakres:** kurs „LLM serving w tydzień” na MLX + Metal (Apple). Tydzień 1: Qwen3 od matmul (atencja, RoPE, GQA,
    RMSNorm/MLP, sampling). Tydzień 2 przepisany 2026-09-23/24 na 5 dni: KV cache z ograniczoną pojemnością, W4 jako
    spakowany matvec w Metal, SIMD-matrix prefill, fuzje RMSNorm/RoPE/SwiGLU, kafelkowana atencja prefillu.
    Tydzień 3: continuous batching, chunked prefill (pomiar „fairness”: najdłuższa przerwa między krokami decode vs
    przepustowość), paged KV, paged FlashAttention, opcjonalnie MoE i spekulacja (tylko greedy, osobny drafter).
    Tydzień 4: agent kodujący (pętla, narzędzia, kompakcja, sesje, ewaluacja).
  - **Brak:** linear attention/GDN, MTP, sampling-correct spekulacja, AMD/CUDA. **Dla batch-1 decode na XTX nic
    nowego.**
  - **Bardzo cenna jest metodologia.**
    - Appendix „Performance Evidence Ledger”: każdy checkpoint odpowiada przed zatrzymaniem na **6 pytań** —
      niezmiennik, hipoteza wydajności, gdzie wygrywa i gdzie przegrywa (kształty), fallback/kontrola, „main
      benchmark trap”.
    - Przykłady pułapek: „Comparing cached MLX with an uncached course model measures different algorithms”, „Adding
      isolated microseconds as if checkpoint gains were independent”, „promoting `n=2` product noise”.
    - Pomiar: każdy checkpoint w świeżym procesie, naprzemienna kolejność, pełne rozgrzewki, mediana. „Never compare”
      trybów `--prefill-logits last` i `all`.
    - Wersja zależności jest częścią eksperymentu: MLX 0.29.1 → 0.32.0 zmieniło decode przy 2k o −4.6%.
    - Budżet długiego kontekstu jako `min(trained, configured, memory)`.
  - **Testy:** referencja w Pythonie `mlx.core` jako wyrocznia, tolerancje per dtype (`tests/utils.py:98-106`: fp32
    rtol 1e-5/atol 1e-6; fp16 5e-2/1e-3; bf16 5e-2/1e-2).
  - **Ocena:** wysoka wartość szkoleniowa dla nowych osób i agentów (zwłaszcza ledger i pułapki); technicznie
    przenosi się tylko wzorzec ledgera do `patch-manifest.json` (E5).
- **pavelsimo/100-days-of-inference-engineering** (`18eef29`, dzień 7). Notatki z książki „Inference Engineering”
  (rozdziały 0–4): metryki TTFT/TPS/ITL, prefill vs decode, roofline, sprzęt, silniki, benchmarking vs profiling,
  „shadowing” ruchu produkcyjnego. **Poziom wstępny, dla nas nic nowego.** Obserwować; może dojdzie do rozdziałów o
  spekulacji.
- **navaneethkrishnansuresh/CUDA-and-Kernels** (`7045333`). Mapa 20 tematów, z czego gotowe są tylko CUDA Basics (3
  notatki: pierwszy program, wątki/bloki/siatki, dodawanie wektorów). Topiki 2–20 to puste README („Not available
  yet”). **Dziś bez wartości**; ewentualnie wrócić po rozdziałach 13–18.
- **wafer-ai/gpu-perf-engineering-resources**: bez zmian od R21b.

## 11. Co z tego dla nas (ranking: oczekiwany zysk / wysiłek)

Format „baseline → teraz → przyrost %”. Wszystkie pomiary GPU przez kolejkę `gpu.lock` (nie robiłem żadnego).

| # | eksperyment | wartość bazowa (źródło) | oczekiwane „teraz” | przyrost | wysiłek | ryzyko |
|---|---|---|---|---|---|---|
| **E1** | **„Następny krok przed synchronizacją hosta”**: token z próbkowania na GPU jako wejście kolejnego grafu (bez rundy przez host); host kolejkuje krok t+1 zaraz po t, a token czyta asynchronicznie krok później (EOS sprawdzane z opóźnieniem 1 tokenu). Dla spekulacji: draft MTP czyta `n_accepted` z pamięci GPU (`LLAMA_GPU_VERIFY` już liczy akceptację na GPU) | LFM 3.41 ms/token = 293.7 t/s, host ~220 µs/token (`2026-10-16-budzet-lfm-megakernel.md:10`); Qwen 27.4 ms/krok, host 160–240 µs × 3 grafy (24o) | LFM ~3.21 ms; Qwen ~26.9 ms | **LFM +4…+6%, Qwen +1…+2%** `[SZACUNEK]` | średni-wysoki (pętla decode llama.cpp, taśma PM4 musi czytać wejście z bufora GPU, ścieżka EOS/stop strings) | bitowo identyczne z konstrukcji; ryzyko wyścigu przy stop strings |
| **E2** | **Integralność benchu w aplikacji** (G1–G9): wspólne tokeny dla obu ramion, ramię T=1, próg szumu + potwierdzenie zwycięzcy, deep w decyzji, zegar klienta, keepawake | dziś `decodePct` enigma vs upstream liczony na różnych promptach (G1) | uczciwy „przyrost %” | 0% t/s, ale **prawdziwe liczby dla użytkownika**; G7 ratuje ×20 po bezczynności na `power/control=auto` | mały (1–2 dni TS) | niski |
| **E3** | **Trening głowicy MTP on-policy** (Decagon: rollouty draftera przy targecie, waga na punktach odrzucenia, Draft-OPD, D-PACE; adaptacja istniejącej głowicy zamiast nowej) | proza E0 78.93 t/s przy 2.158 tok/krok (`37-proza-100.md:13`); spec_sweep 114.6 t/s | akceptacja +10…+14% → ~2.35 tok/krok | **proza +7…+9%, czat +5…+8%** `[SZACUNEK, Decagon: +14% acceptance length z dalszym treningiem, +34% throughput na swoim endpoincie]` | wysoki (trening na wynajętym GPU; mamy pilot 11-mtp-pl) | zmiana draftera nie zmienia wyjścia (weryfikacja), więc bezpieczna jakościowo |
| **E4** | **Przeszukiwanie przestrzeni flag** (TPE/SMAC, ~10 wymiarów: DRAFT_N, LOOKUP_W/MMIN, COUPLED_DT, p_min, ub, PM4_MIN_DISPATCH, typ KV draftu) z potwierdzeniem ABBA; w aplikacji kandydaci `mtp-2/3/4` | XTX: ręcznie dobrane flagi; karty NVIDIA dostają domyślne z XTX | XTX +1…+3%; karty NVIDIA więcej | +1…+5% `[SZACUNEK]`; InferenceBench: prosta wyszukiwarka 11.53× vs agent 8.08× | średni (mamy kolejkę i ABBA) | dopasowanie do sędziego, dlatego tylko z holdoutem (E5) |
| **E5** | **Higiena pomiaru `spec_sweep`**: pula 48 promptów dev/holdout, hash buildu i env w każdym wierszu, minimum per prompt w decyzji, ledger 6 pytań z tiny-llm dla każdej łatki w `patch-manifest.json` | 6 stałych promptów | – | 0% t/s; chroni przed fałszywymi wygranymi (OKC, EAT) | mały | brak |
| **E6** | **Fuzja GDN decode/weryfikacji** (conv + rekurencja delta + gated RMSNorm w jednym launchu dla S ≤ 17, stan w VGPR), wzór EAT KDA MI350X | klab: GDN 0.72 + conv 0.26 + unary_gated 0.22 ≈ 1.2 ms z 31.24 ms/krok (`47-kernel-lab.md:20-23`) | ~0.8 ms | **Qwen +1…+1.5%** `[SZACUNEK]` | wysoki | numeryka (KLD), wymaga bramki |
| **E7** | **Szybszy pomiar dla fabryki** (TKCC): przełączanie flag w działającym serwerze (endpoint admin, flagi env czytane per żądanie zamiast `static`), poziom szybki (`klab`) → wolny (`spec_sweep`) | restart serwera na ramię (start 6.55 s + rozgrzewka) | 3–5× więcej ramion na godzinę `[SZACUNEK]` | pośrednio: więcej prób | średni | flagi, które zmieniają alokacje, nadal wymagają restartu |
| **E8** | **Audyt reżimu** (EAT „energy auditor”): `spec_sweep` z przerwami 0 / 2 / 10 / 30 s między żądaniami; t/s pierwszych 50 tokenów i TTFT | dziś tylko back-to-back | – | ujawnia realną latencję czatu i agenta; potencjalnie duże przy BACO | mały | brak |
| **E9** | **„Rachunek modelu” w aplikacji** (FlashProve-lite): sonda 32 tokenów greedy + top-5 logprobów vs referencja per (sha GGUF, backend); wykrywa zły kwant, uszkodzony plik, zły szablon, ciche CPU | – | – | zaufanie i diagnostyka | mały | tolerancja między backendami (inne sumowanie): referencja per backend |

Odrzucone albo bez zmian:
- megakernel na XTX (TKCC, SGLang i nasza lekcja mówią to samo);
- FlashProve/zk lokalnie (narzut ~100×);
- getsupers (tylko H200);
- warstwa „placement” z EAT (dotyczy 8 XCC MI350X, XTX ma jeden GCD).

**Projekty eksperymentów (do kolejki):**
- **E1:**
  1. `LLAMA_HOSTGAP_TRACE=1` na LFM (`run-topka.sh lfm`, czat T=1, 400 tok.) → rozkład µs/token: host (balloc,
     set_inputs, sampling, detokenize) vs GPU;
  2. jeśli luka hosta ≥ 150 µs/token, prototyp `LLAMA_ASYNC_NEXT=1` tylko dla greedy plain decode;
  3. ABBA 3 × 3 seedy; bramka md5 `894e56e4`;
  4. kill przy < +2%.
- **E2:** test CPU (mock serwera) + jeden przebieg na XTX: `enigma` vs upstream z G1; pokazać różnicę `decodePct`
  przed i po poprawce.
- **E8:** jeden przebieg `spec_sweep` z `--gap 10`, porównanie t/s i `prompt_ms` z przebiegiem bez przerw.

## 12. „Jak myślą najlepsi”: lista kontrolna do przyjęcia

Synteza: OKC, Auto-research PR #9, EAT, TKCC, Decagon, InferenceBench, Overshoot, wafer, GPU MODE, gau-nernst, tiny-llm.

**Pomiar:**
1. Najpierw próg szumu: kilka powtórek baseline'u w identycznych warunkach. Zysk liczy się dopiero powyżej szumu i po
   powtórzeniu (Decagon; EAT: +0.001 z CI bez zera).
2. Ten sam input dla obu ramion, bajt w bajt (InferenceBench: hash zestawu żądań). Nigdy nie pozwól kandydatowi
   renderować własnego obciążenia.
3. Mierz w reżimie użytkownika: temperatura, przerwy, długości, struktura danych. Jeśli zespół stoi w miejscu,
   sprawdź, czy nie mierzy w innym reżimie niż cel (EAT energy auditor; TKCC: losowe dane kłamią przy top-k i MoE).
4. Zegar poza mierzonym: TTFT i E2E po stronie klienta; podejrzliwość wobec wyników > 75% rooflinu i wobec skoków
   o rzędy wielkości (Overshoot, InferenceBench 6.4 ns/token).
5. Held-out i „nearby shapes”: stroić na dev, raportować z holdoutu (OKC final review, EAT `--heldout`).
6. Każdy wynik z hashem kodu i konfiguracji; nie powtarzaj niezmienionego kodu, licząc na szum (Auto-research PR #9).

**Integracja:**
7. Wygrana komponentu to hipoteza. Złożenie zmian to nowy kandydat, mierzony w całości (PR #9; Decagon: „two
   improvements … may compete for the same resource”).
8. Zmiana statyczna (VGPR, occupancy, mniej instrukcji) to hipoteza. Najpierw sprawdź, czy ISA w ogóle się zmieniła
   (nasze `klab isadiff`).

**Poszukiwanie:**
9. Zanim agent wymyśli kernel: tani przegląd przestrzeni konfiguracji (InferenceBench) i strojenie bibliotek
   producenta zamiast ich zastępowania (TKCC: vendor 78–100% pasma).
10. Szukaj martwej pracy: dopełnienia (16 → 64 głowice), praca rozmiarem pojemności zamiast długości, puste
    copy/memset w grafie (TKCC, SGLang).
11. Utrzymuj sterowanie na GPU: żadnego `.item()` i synchronizacji w kroku; „launch the next kernel before its input
    exists” (OKC #4, SGLang Low-Latency).
12. Unikaj komunikacji: rejestry > LDS > globalna; producent „fire and forget” z buforem rezydentnym (gau-nernst).

**Organizacja agentów:**
13. Przepustowość pomiaru to sufit: hot-reload zamiast restartu, poziom szybki i wolny (TKCC).
14. Pamięć wyników tak, pamięć strategii nie: zapisuj, co sprawdzono, w jakich warunkach i z jakim wynikiem (Decagon;
    nasza reguła „nie badać dwa razy”), ale nie narzucaj agentom kolejności i strategii (TKCC −25–31%). Notatki w
    Markdownie, nie w ciężkich strukturach (TKCC: 8% vs < 0.5% czasu).
15. Propozycja eksperymentu ma 4 części: Explanation / Intervention / **Prediction** / **Falsification** (Decagon).
16. Plateau to błąd organizacji, nie sufit problemu: zmień skład i role zespołu (EAT), np. integrator wiedzy, debugger
    równoległy, audytor pomiaru.
17. Człowiek wyłapuje „oczywiste błędy” i zatwierdza zmiany stratne; bezstratne i stratne zawsze rozdzielone
    (Decagon, Rohan Arun).
18. Ewaluacja poza zasięgiem agenta: sędzia i referencja tylko do odczytu, osobny proces; niezależny agent-weryfikator
    czyta diff (Overshoot, InferenceBench, nasza R15f).
19. Retencja każdej optymalizacji przez 6 pytań: niezmiennik, hipoteza, gdzie wygrywa, gdzie przegrywa, fallback,
    pułapka benchmarku (tiny-llm).

## 13. Źródła (dla ZRODLA)

| źródło | wersja / data | werdykt |
|---|---|---|
| [Open Kernel Challenge llms.txt](https://openkernelchallenge.dev/llms.txt) | stan 2026-11-05 (tor kernelowy zamknięty) | metodologia sędziego, lekcja dopasowania do sędziego |
| [rohanarun/Auto-research-agent](https://github.com/rohanarun/Auto-research-agent) | `0230468` 2026-11-04; PR #6 `7a14f0d`, PR #9 `b94e66e` | prompty: standard; benchmark: wiersze Gemini to nie pomiary agenta |
| tweety @RohanArun (fxtwitter) | 2114830856393027974 (10-26), 2115854684732727717 (10-29), 2116197860844696033 (10-30), 2117446433716478226 (11-03) | źródło „human coordinator 2×”, bez danych |
| [app.getsupers.com/experiments](https://app.getsupers.com/experiments) | 2026-11-05 | tylko H200, nie dla nas |
| [EAT arXiv 2610.36848](https://arxiv.org/abs/2610.36848), [caoshiyi/EAT](https://github.com/caoshiyi/EAT), [eat-kernels](https://github.com/caoshiyi/eat-kernels) | v1 2026-10-27; `0a90500` 2026-11-02 | wzorzec organizacji + fuzja KDA/GDN (E6) |
| [Together Compiler blog](https://www.together.ai/blog/together-compiler-continual-compilation-for-ai-inference) + paper PDF | 2026-11-04 | bitter lessons, megakernel nie płaci, persistent engine (E7) |
| [HazyResearch/Megakernels](https://github.com/HazyResearch/Megakernels) / [ThunderKittens](https://github.com/HazyResearch/ThunderKittens) | `7309cec8` 2025-06-02 (martwe) / `67845f5f` 2026-09-12 | delta: brak pracy nad megakernelami |
| [Baseten X article „…DeepSeek V4.1 Flash 1017”](https://x.com/thealexker/status/2117989442090598798) | 2026-11-04 | nieczytelne; „1017” to wersja modelu |
| [SGLang „Beyond Day-0” DSv4.1 Flash](https://www.lmsys.org/blog/2026-09-28-deepseek-v41-optimization/) | 2026-09-28 | techniki; liczba GB300 przy symulowanej akceptacji |
| [SGLang Low-Latency Mode](https://www.lmsys.org/blog/2026-10-18-sglang-low-latency-mode/) | 2026-10-18 | „launch before input exists”, draft w jednym kernelu |
| [InferenceBench arXiv 2607.20468](https://arxiv.org/abs/2607.20468) | v1 2026-05-20 | hacki serwera, prosta wyszukiwarka > agenci |
| [Overshoot: Intro to Reward Hacking](https://threadnavigator.com/thread/2117453561575665902/) | 2026-11-04 | przegląd + obrony |
| [Wafer field guide](https://www.wafer.ai/blog/reward-hacks-field-guide) | 2026-03-12 | 10 wzorców, przypadek LDS na ROCm |
| [GPU MODE NVFP4 reward hack](https://github.com/gpu-mode/kernelboard/blob/main/kernelboard/static/news/2026-03-09-reward-hacking.md) | 2026-03-09 | wykrywanie fazy, naprawa PR #104 |
| [Decagon „Building an inference stack that improves itself”](https://x.com/DecagonAI/status/2115511110120120437) | 2026-10-28 | próg szumu, replay, format propozycji, trening draftera (E3) |
| [sf-tensor Formalizing PTX](https://sf-tensor.com/engineering/formalizing-ptx) | 2026-11-02 | brak AMD, niski priorytet |
| [Anthropic provable inference](https://www.anthropic.com/research/provable-inference), [FlashProve](https://github.com/anthropics/FlashProve) | 2026-11-02; `9e2bdd8f` v0.16.0 | lokalnie bez sensu; „rachunek modelu” (E9) |
| [gau-nernst B200 QR](https://gau-nernst.github.io/b200-qr/) | 2026-09-27, kod `fb291890` | zasady w §9 |
| [skyzh/tiny-llm](https://github.com/skyzh/tiny-llm) | `17a8cc6` 2026-10-31 | ledger 6 pytań, pułapki pomiaru |
| [pavelsimo/100-days-of-inference-engineering](https://github.com/pavelsimo/100-days-of-inference-engineering) | `18eef29` 2026-11-04 (dzień 7) | wstępne, obserwować |
| [navaneethkrishnansuresh/CUDA-and-Kernels](https://github.com/navaneethkrishnansuresh/CUDA-and-Kernels) | `7045333` 2026-11-03 | puste topiki |
| [wafer-ai/gpu-perf-engineering-resources](https://github.com/wafer-ai/gpu-perf-engineering-resources) | `6aa00fc` 2026-10-17 | bez zmian od R21b |
| [LeanAttention arXiv 2405.10480](https://arxiv.org/abs/2405.10480) | v2 | już mamy (63d E7) |
