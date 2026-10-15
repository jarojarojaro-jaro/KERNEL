# 07 — Nasze metody: klasyfikacja 70 łatek, playbook i uogólnienie na inne modele i GPU

Data: 2026-10-15. Materiał wyłącznie lokalny: `~/KERNEL/qwen-opt/` (NOTES.md, STATUS-NEXT.md, 70 łatek, `research/`, `tools/`), `~/llama-master` (historia gałęzi `amd-opt` i 25 gałęzi `opt-*`), `~/telefon/`, `~/KERNEL/monitor/`. GPU nie było używane. Odwołania w nawiasach (`plik:linia`) prowadzą do źródeł z listy na końcu. `[INFERENCE]` oznacza mój wniosek bez bezpośredniego pomiaru. Wszystkie źródła są z 2026-10-09…15, więc żadne nie jest starsze niż 12 miesięcy.

## 1. TL;DR

- **70 łatek, z czego 45 bitowo identycznych.** Do tego 6 daje te same tokeny (sampler), 3 zmieniają tylko drafty (rozkład wyjścia bez zmian), 3 to poprawki, 7 zmienia numerykę. Spośród tych 7 tylko 4 przeszły bramkę KLD: 0008, 0013, 0037 i 0055. Kernel FA `kvq` dla q4_0 (0011) zmienia tekst greedy Qwena, a **KLD dla Qwena nigdy nie zmierzono**. To luka do zamknięcia.
- **Gdzie przenosi się 70 łatek:**

  | klasa | liczba | co to znaczy |
  |---|---|---|
  | MODEL | 22 | zależne od architektury modelu: GDN, MTP, MoE, LFM2 conv |
  | AMD-RDNA3 | 18 | specyficzne dla gfx1100: WMMA, DPP, VOPD, buffer resource, GLC/DLC, PM4 |
  | GEN-CUDA/HIP | 12 | wspólny kod ggml-cuda, który kompiluje się też dla NVIDIA, ale nigdy nie był tam testowany |
  | GEN-host | 10 | CPU/host, przenosi się na każdy backend |
  | VK-RDNA | 5 | Vulkan na RDNA, poza domyślną ścieżką |
  | — | 3 | narzędzia |

- **Skąd się wziął zysk** (rozkład oszczędności czasu kroku, `[INFERENCE]` dla podziału wewnątrz grup):

  | model | zmiana kroku | MODEL | AMD-RDNA3 | ogólne |
  |---|---|---|---|---|
  | Qwen3.8-27B (MTP, 6 promptów × 3 seedy, T=1) | 41.7 → 27.74 ms | ~48% (GDN, MTP) | ~30% (MMVQ K1, PM4, DPP) | ~22% (host, q8_1, fuzje wspólne) |
  | LFM2.5-24B-A2B (llama-bench) | 5.07 → 3.40 ms/token | ~56% (MoE ~34%, LFM2 conv ~22%) | ~28% (sam PM4) | reszta |

- **Dowód transferu „inny model, ten sam GPU”:** LFM2.5 na forku, przed jakąkolwiek pracą pod LFM, miał tg128 169.3 → 198.3 t/s (+17%) wyłącznie dzięki łatkom z kampanii Qwena. Kampania pod LFM (~11 h zegarowych) dodała 198 → 295 t/s (+49%). W drugą stronę: łatki LFM dały Qwenowi tylko PM4 (+4.9%) i sampler (+6–8% w ścieżkach UI i narzędzi).
- **Konfiguracja daje najwięcej względem gołego dekodowania.** Upstream Vulkan na Qwenie: bez spekulacji 38.8 t/s, z MTP n=4 85.6 t/s, czyli ×2.2 bez żadnej łatki. Nasze łatki dokładają na to +27–60%, zależnie od benchmarku. Do tego jedna pułapka systemowa (runtime suspend/BACO) obniżała wynik do **4.4 t/s**. Dla produktu oznacza to, że „config + gates” na komputerze użytkownika dają większość efektu „wow”, a kampanie kernelowe dają ostatnie +30–70%.
- **Proces jest powtarzalny i opisany w commitach.** Pętla wygląda tak:
  - profil rocprofv3 per token;
  - ranking kerneli i przerw;
  - hipoteza z budżetem w µs;
  - łatka z przełącznikiem env;
  - `test-backend-ops` i bramka bitowa (greedy md5 na świeżym serwerze, hash logitów) albo bramka KLD;
  - przeplatane A/B;
  - wpis w NOTES z wynikami negatywnymi.

  Każdy commit zawiera zmierzone przed → po, ale 5 commitów (0066–0070) powstało jako „UNMEASURED” i zostało zmierzonych później.
- **Koszt** `[INFERENCE z timestampów]`: ~60 h zegarowych w 6.4 dnia kalendarzowego (2026-10-09 13:16 → 10-15 22:01). Qwen zajął ~40 h zegarowych (≈60–120 agento-godzin, ~15 gałęzi roboczych `opt-*` z 25 w repo), LFM ~11 h (≈15–30 agento-godzin). GPU: **6.8 h samych przebiegów `spec_sweep`** (182 konfiguracje, mediana 2.15 min) plus bench, profile i KLD, łącznie ok. 20–35 GPU-h.
- **Brakuje bazy dla Ollama i LM Studio.** Nie ma lokalnie żadnego pomiaru. Najbliższe „stockowe” punkty to stary build z 1 września (59.2 t/s, MTP n=3), upstream e60eff95f (68.6 t/s EN, MTP n=3) oraz upstream bez spekulacji (36.6–38.8 t/s). Teza „40–60 t/s w stockowych narzędziach” jest zgodna z tymi liczbami, ale niezmierzona.
- **Minimum, żeby to uprzemysłowić:**
  1. farma GPU per arch z kolejką i lockami;
  2. harness testów (op-level, bitowy, ISA);
  3. serwis bramki poprawności (greedy md5 na świeżym serwerze, hash logitów, KLD z kanarkami, sampler-harness);
  4. baza benchmarków z przeplatanym A/B i sparowanym CI;
  5. pakowanie przepisów jako rodzin łatek z predykatami stosowalności i tabelami z tunera, plus bot rebase na upstream.

  Połowa tego istnieje jako skrypty (`loo.py`, `kld_gate.py`, `kt.py`, `spec_sweep.py`, `samp_ab.py`, `det_probe.py`), ale jeszcze nie była uruchomiona na GPU (LOO, kanarki, Kernel Tuner).

## 2. Ustalenia

### 2.1 Klasyfikacja wszystkich 70 łatek

Baza: upstream llama.cpp `e60eff95f` z 2026-10-09 (`git log`), gałąź `amd-opt` @ `f61994f58` (`STATUS-NEXT.md:6`). Opisy i zyski pochodzą z wiadomości commitów (`patches/llama.cpp-amd-opt/*.patch`) oraz NOTES.md.

**Legenda.**

Zależność:
- **GEN-host**: CPU/host, działa dla każdego modelu i backendu.
- **GEN-CUDA/HIP**: wspólny kod `ggml-cuda` bez strażników HIP. Kompiluje się dla NVIDIA (warp 32), ale był testowany tylko na gfx1100. Sprawdziłem to grepem po łatkach: brak `GGML_USE_HIP`/RDNA w dodanych liniach.
- **AMD-RDNA3**: intrynsyki lub strojenie gfx11, czyli WMMA iu8, DPP/permlanex16, VOPD, buffer resource, GLC|DLC, liczba CU, PM4/ROCr.
- **VK-RDNA**: backend Vulkan na AMD RDNA.
- **MODEL**: GDN (qwen35), MTP, MoE, LFM2 shortconv.

Poprawność:
- **BIT**: bitowo identyczne (greedy md5 na świeżym serwerze, hash logitów, test-backend-ops).
- **SAME-TOK**: te same tokeny i kandydaci (harness CPU i serwer).
- **DIST**: zmienia drafty, ale weryfikacja jest bez zmian, więc rozkład wyjścia też.
- **KLD**: numeryka zmieniona i bramkowana KLD.
- **NUM?**: numeryka zmieniona, bez osobnej bramki.
- **FIX**: poprawka.

Kolumna „Upstream?” to moja ocena `[INFERENCE]`: „tak” znaczy mała, ogólna zmiana z testem, „średnio” znaczy, że wymaga uogólnienia lub testów na CUDA, „niski” znaczy, że zależy od wnętrzności sterownika albo jest duża zmiana core.

| # | Zmiana | Kategoria | Zależność (klasa) | Szczegóły zależności | Zmierzony zysk | Poprawność | Upstream? |
|---|---|---|---|---|---|---|---|
| 0001 | MMVQ 2–8 kolumn (weryfikacja spekulacji), szerokie ciągłe odczyty, człon min z ds.y | kernel | AMD-RDNA3 | ścieżka tylko HIP; Q4_K/Q5_K/Q6_K/IQ4_XS/IQ4_NL; każdy model ze spekulacją | Q5_K 8 kol. 296→621 GB/s; z 0002: MTP 68.6→82.3 t/s EN (+20%) | BIT | średnio (tabela per-arch w mmvq) |
| 0002 | MMVQ wielokolumnowe: i-quants, Q2_K, wiersze/blok per typ | kernel | AMD-RDNA3 | IQ1–IQ3, Q2_K | Q2_K 8 kol. 132→272 GB/s | BIT | średnio |
| 0003 | cache q8_1 aktywacji dla kolejnych MUL_MAT z tym samym src1 | kernel | GEN-CUDA/HIP | dowolny model (Q/K/V, gate/up) | +2–4% e2e | BIT | tak |
| 0004 | `--spec-draft-vocab`: głowica draftu na N najczęstszych tokenach | speculative | MODEL | MTP / duży słownik (248k); idea ogólna dla każdego draftera | +7.5% (64k); 16k −5% | DIST (weryfikacja bez zmian) | tak (feature) |
| 0005 | usunięcie lokalnego include strojenia | tooling | — | higiena | — | n/d | n/d |
| 0006 | Vulkan: small-M matvec ścieżką float, WG 256 | kernel | VK-RDNA | AMD RDNA, m=48 (ssm_alpha/beta) | 13.6→8.6 µs/wyw. (~0.5 ms/krok) | NUM? (nie bramkowane osobno) | tak (Vulkan) |
| 0007 | Vulkan: MMVQ fast path K-quants/IQ4_XS, hoisting dekodowania | kernel | VK-RDNA | K-quants; RDNA3/4 | q4_K 6 kol. 614→690 GB/s; 0007–0010: ms/krok −5.2% | BIT | tak (Vulkan) |
| 0008 | Vulkan: Q6_K przez integer-dot MMVQ od 4 kolumn | kernel | VK-RDNA | Q6_K (lm_head) | lm_head n=6 1.9→1.3 ms | KLD 0.0042 (szum b6/b512 0.0036) | tak (Vulkan) |
| 0009 | Vulkan: float matvec dla m<4096 przy >4 kol. | kernel | VK-RDNA | małe K/V proj. | q6_K m=1024 18.1→9.7 µs | NUM? (float vs q8_1; nie bramkowane osobno) | tak (Vulkan) |
| 0010 | Vulkan: 2 wiersze/WG przy 8 kolumnach | kernel | VK-RDNA | RDNA3/4 | mieszane, np. q5_K 5120×17408 109.4→101.8 µs | BIT | tak (Vulkan) |
| 0011 | FA `kvq`: czyta KV q4_0 wprost, cała grupa GQA × ≤8 tokenów, WMMA | KV | AMD-RDNA3 | WMMA gfx11; KV q4_0; GQA; każdy model z atencją | 94k: 43.0→70.9 t/s (+65%); warstwa 32k n=5 913→111 µs | NUM (inny tekst greedy; KLD dla Qwena nie mierzony) | średnio |
| 0012 | epilog bias/residual ADD w MMVQ wielokolumnowym | kernel | GEN-CUDA/HIP | każdy model ze spekulacją | z 0013–0014 (A3–A5): 41.7→37.71 ms/krok, 74.8→83.3 t/s | BIT | tak |
| 0013 | fuzja prologu GATED_DELTA_NET (alpha/beta, l2 q/k, gather stanu) | kernel | MODEL | GDN (qwen35/3.8) | część A3–A5 (−8 uruchomień/warstwę) | KLD 0.0067 (szum bazy 0.0098) | średnio (por. upstream PR #29187) |
| 0014 | concat stanu conv + snapshoty + gather w SSM_CONV | KV | MODEL | GDN/conv hybrydy (stan rekurencyjny) | część A3–A5 (−7 uruchomień/warstwę) | BIT | średnio |
| 0015 | producenci (norm/GLU/unary*mul) piszą q8_1 dla MMVQ | kernel | GEN-CUDA/HIP | dowolny model | 1308→1052 kerneli; 37.73→37.04 ms (+2%) | BIT | tak |
| 0016 | GDN alpha/beta MMVQ szablon po liczbie tokenów | kernel | MODEL | GDN | 9.05→6.1 µs; 425→286 µs/weryfikację | BIT | średnio |
| 0017 | IMROPE/MROPE w fuzji RMS_NORM+MUL+ROPE; bramka bez cont | kernel | GEN-CUDA/HIP | modele M-RoPE (rodzina Qwen-VL/3.5+), graf qwen35 | 1052→1004 kerneli; 31.53→31.17 ms | BIT | tak |
| 0018 | poprawka wyścigu FA (cherry-pick upstream #30103) | kernel | GEN-CUDA/HIP | fix | — | FIX | już upstream |
| 0019 | rotacja Hadamarda q/k (rotowany KV) w norm+rope | KV | GEN-CUDA/HIP | rotowany KV cache (FWHT) | 1004→972 kerneli; 31.17→31.01 ms | BIT | tak |
| 0020 | drafty MTP jako jeden rozwinięty graf (argmax+get_rows na GPU) | speculative | MODEL | MTP (qwen35), wymaga 0004 | 36.39→35.67 ms; 86.4→88.0 t/s; +180 MiB | BIT (drafty identyczne) | średnio |
| 0021 | MMVQ RDNA3: buffer resource, waves_per_eu per (typ,n), pipelining Q6_K, DPP butterfly | kernel | AMD-RDNA3 | ISA gfx11 | z 0022: 35.67→33.17 ms, 88.1→94.7 t/s (+7.5%) | BIT | niski–średni (intrynsyki HIP) |
| 0022 | MMVQ RDNA3: odczyty wag GLC|DLC | kernel | AMD-RDNA3 | polityka cache gfx11 | mmvq 22.95→22.08 ms/weryfikację | BIT | niski–średni |
| 0023 | clamp (d,sum) q8_1 do ±65504 | kernel | GEN-CUDA/HIP | fix NaN (por. upstream #23606) | — | FIX (bitowy na danych skończonych) | tak |
| 0024 | para MMVQ: dwa MUL_MAT tego samego src1 jedną siatką | kernel | GEN-CUDA/HIP | gate/up, qkv/z | z 0025–0026: 972→911 kerneli | BIT | tak |
| 0025 | rms_norm*mul(+q8_1) rozwinięte, redukcje DPP | kernel | AMD-RDNA3 | DPP; hidden 2048–8192 | 5.87→4.51 µs | BIT (po jawnym łańcuchu fmaf) | średnio |
| 0026 | argmax: 16 ładowań w locie + DPP | kernel | AMD-RDNA3 | DPP; drafty greedy | 16.8→4.3 µs | BIT | średnio |
| 0027 | GDN: silu(z)·rms_norm(x)·w + q8_1 jednym kernelem | kernel | MODEL | GDN; DPP | 2.68+1.84→1.87 µs; K2 łącznie 33.17→32.14 ms, 94.7→97.8 t/s | BIT | średnio |
| 0028 | GDN: SSM_CONV + alpha/beta jedną siatką | kernel | MODEL | GDN | 4.68+4.90→5.54 µs (~0.33 ms/krok) | BIT | średnio |
| 0029 | asynchroniczne wysyłanie wejść grafu | scheduler-graph | GEN-host | ggml-backend, każdy backend | 32.20→31.89 ms; K3 łącznie 32.14→30.97 ms, 97.8→101.5 t/s | BIT | tak |
| 0030 | łańcuch draftu MTP na własnym schedulerze | scheduler-graph | MODEL | MTP (wzorzec: naprzemienne grafy) | 31.89→31.59 ms | BIT | tak |
| 0031 | top-k bez pełnej tablicy kandydatów; leniwa kopia samplera | sampler-server | GEN-host | CPU, każdy model | sample+accept 645→140 µs; 31.68→31.19 ms | SAME-TOK | tak |
| 0032 | przekwantyzowanie głowicy/bloku MTP przy ładowaniu | speculative | MODEL | MTP | 30.97→29.76 ms; t/s +1–3% (akceptacja −2–3%) | DIST (zmienia drafty, nie weryfikację) | średnio |
| 0033 | GATED_DELTA_NET_LAG: cofanie przez replay stanu z opóźnieniem | KV | MODEL | GDN + spekulacja | GDN 793→638 µs; VRAM stanów 748→195 MiB; →29.36 ms, 102.9 t/s | BIT | średnio–niski (duża zmiana core) |
| 0034 | GDN_LAG: układ lag info | KV | MODEL | GDN | część S4 | BIT | j.w. |
| 0035 | GDN_LAG: prefetch następnego wiersza | kernel | MODEL | GDN | 661→638 µs/weryfikację | BIT | j.w. |
| 0036 | GDN_LAG: stan czytany z wiersza cache | KV | MODEL | GDN | część S4 | BIT | j.w. |
| 0037 | WMMA small-N 9–16 kolumn | kernel | AMD-RDNA3 | WMMA iu8 gfx11; K-quants | n=9 49.2→32.1 ms; nieaktywne przy n=4 | KLD 0.0122–0.0128 (baza 0.0124±0.0006) | średnio |
| 0038 | historia conv z opóźnieniem (bez snapshotów) | KV | MODEL | GDN/conv hybrydy | draft 8: 1391→832 kerneli, 40.8→37.2 ms/krok; n=4: 0 | BIT | średnio |
| 0039 | adaptacyjna długość draftu wyceniana kosztem (opt-in) | speculative | GEN-host | każda spekulacja łańcuchowa | 103.6 vs n=4 102.7 (szum) — nie domyślne | DIST | niski |
| 0040 | MMQ RDNA3: węższy kafel, gdy CU stoją | kernel | AMD-RDNA3 | logika ogólna, próg zależny od liczby CU | pp2048 1059→1080 (+2%) | BIT | tak |
| 0041 | warstwa MTP liczy tylko K/V dla wierszy bez wyjścia | speculative | MODEL | MTP qwen35 | prefill 6.6k 913→936, 29.5k 870→897 | BIT | tak |
| 0042 | FA MMA D=256 (prefill): Q w SRAM, bez spilli | kernel | AMD-RDNA3 | limit 256 VGPR; D=256 | 40.2→49.0 TFLOPS; FA 32k 4.36→3.42 s | BIT (z 0043) | tak |
| 0043 | FA MMA: chunki K w kolejności | kernel | GEN-CUDA/HIP | fix numeryki | KLD 0.0135→0 dla 0042 | FIX | tak |
| 0044 | perf cases test-backend-ops dla kształtów Qwena | tooling | — | testy | — | n/d | tak |
| 0045 | GDN prefill: normalizacja l2 q/k raz na (głowa, token) | kernel | MODEL | GDN | pp2048 1082→1108 (+2.4%) | BIT | średnio |
| 0046 | okno atencji warstwy MTP (WIP, opt-in) | speculative | MODEL | MTP | negatywny: W=8192 105→90 t/s | zmienia akceptację | nie |
| 0047 | koszty hosta pętli spec. (seq_rm po indeksie, szybka maska KQ) | sampler-server | GEN-host | CPU, każdy model, długi ctx | rollback 236→6 µs; 29.36→28.94 ms, 102.6→104.2 t/s | BIT | tak |
| 0048 | szybkie top-k także za samplerem kar | sampler-server | GEN-host | każdy model z repeat_penalty (np. domyślne GGUF LFM) | LFM serwer 5.79→5.11 ms/tok (+13%) | SAME-TOK | tak |
| 0049 | norma FFN pisze q8_1 dla gate/up ekspertów | kernel | MODEL | MoE (kod wspólny CUDA/HIP) | 5.067→4.979 ms/tok (+1.8%) | BIT | tak |
| 0050 | LFM2 shortconv: b·x i c·conv w SSM_CONV + q8_1 | kernel | MODEL | LFM2 shortconv | 4.979→4.800 ms (+3.7%) | BIT | średnio |
| 0051 | MoE: down + ważenie + residual jednym MMVQ | kernel | MODEL | MoE (kod wspólny) | 4.817→4.642 ms (+3.8%) | BIT | tak |
| 0052 | MMVQ 1 kolumna: 2 wiersze/blok dla K-quants | kernel | AMD-RDNA3 | strojenie gfx11; każdy model | 4.610→4.509 ms (+2.2%) | BIT | tak (tabela per-arch) |
| 0053 | MoE routing: norma + router F32 + top-k jednym kernelem | kernel | MODEL | MoE; DPP; atomowy ticket | 4.451→4.246 ms (+4.8%) | BIT | średnio |
| 0054 | LFM2 in_proj MMVQ z konwolucją jako ogon ticketu | kernel | MODEL | LFM2; tylko RDNA | 4.231→4.100 ms (+3.2%) | BIT | niski–średni |
| 0055 | kvq czyta też KV q8_0 (D 64/128) | KV | AMD-RDNA3 | WMMA gfx11; KV q8_0 | 98k: 6.561→5.462 ms (+20%); d0 +0.5% | KLD 0.044196 vs 0.044171 (PASS) | średnio |
| 0056 | gate/up(+GLU) pisze q8_1 wejścia down | kernel | GEN-CUDA/HIP | MoE i gęste FFN (warp 32) | 4.070→3.973 ms (+2.4%) | BIT | tak |
| 0057 | wejście atencji jednym kernelem (norm+rope+FWHT+SET_ROWS q8_0) | KV | GEN-CUDA/HIP | rotowany KV q8_0; każdy model z atencją | 4.043→3.907 ms (+3.5%) | BIT | tak |
| 0058 | combine kvq robi FWHT wyjścia + q8_1 | KV | AMD-RDNA3 | rotowany KV + kvq | 3.928→3.879 ms (+1.3%) | BIT | średnio |
| 0059 | zbiorczy upload wejść (1 H2D + scatter) | scheduler-graph | GEN-CUDA/HIP | każdy model | 3.840→3.806 ms (+0.9%) | BIT | tak |
| 0060 | replay grafu dekodowania jako bufor PM4 na własnej kolejce ROCr | scheduler-graph | AMD-RDNA3 | ROCr/AQL vendor packet, loader ext.; każdy model | LFM 3.887→3.424 ms (+13.5%); Qwen 29.16→27.80 ms (+4.9%) | BIT | niski (wnętrzności ROCr) |
| 0061 | PM4_DEBUG: czasy taśmy i dispatchy | tooling | AMD-RDNA3 | diagnostyka (rocprofv3 nie widzi PM4) | — | n/d | z 0060 |
| 0062 | conv in_proj 4 wiersze/blok (siatka ≠ 3072 = pojemność fal) | kernel | AMD-RDNA3 | 96 CU; LFM2 | 3.458→3.402 ms (+1.6%), znika rozrzut per proces | BIT | średnio |
| 0063 | przełączniki przez `ggml_cuda_env_switch` | tooling | — | refaktor | — | n/d | n/d |
| 0064 | MMVQ 1 kolumna: Q8_0 w ścieżce 2 wierszy | kernel | AMD-RDNA3 | Q8_0 | LFM Uncensored 3.933→3.706 ms (+6.1%) | BIT | tak (tabela per-arch) |
| 0065 | serwer ignoruje `reasoning_control` klienta | sampler-server | GEN-host | web UI llama-server | LFM (żądanie z UI) 255→291 t/s | zmiana zachowania API | nie (obejście, zastąpione przez 0066) |
| 0066 | szybkie top-k z samplerem budżetu myślenia | sampler-server | GEN-host | każdy model z budżetem | Qwen MTP 99.3→107.0; LFM 256.9→292.9 | SAME-TOK | tak |
| 0067 | szybkie top-k przy n_probs>0 | sampler-server | GEN-host | logprobs | brak osobnego pomiaru | SAME-TOK | tak |
| 0068 | szybkie top-k za logit_bias (≤64 tokeny) | sampler-server | GEN-host | każdy model | Qwen MTP 98.9→105.4; LFM 257.1→292.6 | SAME-TOK | tak |
| 0069 | szybkie top-k z gramatyką (bez grammar_first) | sampler-server | GEN-host | tool calling/agenci | Qwen MTP 104.8→113.2; LFM 254.2→294.3 | SAME-TOK | tak |
| 0070 | MMQ (prefill) Q4_K/Q5_K: epilog skal w parach VOPD | kernel | AMD-RDNA3 | VOPD + WMMA iu8 gfx11 | Qwen pp4096 1099.5→1123.2 (+2.2%) | BIT (dowód + logity) | średnio |

**Podsumowanie liczbowe** (z tabeli):

| przekrój | wynik |
|---|---|
| kategoria | kernel 38, KV (w tym stan rekurencyjny) 10, sampler-server 8, speculative 6, scheduler-graph 4, tooling 4 |
| zależność | MODEL 22, AMD-RDNA3 18, GEN-CUDA/HIP 12, GEN-host 10, VK-RDNA 5, narzędzia 3 |
| poprawność | BIT 45, SAME-TOK 6, NUM/KLD 7 (bramka KLD: 0008, 0013, 0037, 0055; bez osobnej bramki: 0006, 0009, 0011), DIST 3, FIX 3, inne 6 |
| przełączniki | 27 env w runtime, 2 CLI, 22 tylko w buildzie (8 revertuje się czysto, 14 ma konflikty), 14 nie dotyczy prędkości (`tools/loo/loo-plan.md:3-6`, stan na 65 łatek) |
| model docelowy | Qwen: 0001–0047 (bez 5 łatek Vulkan); LFM: 0048–0064; oba: sampler 0065–0069; Qwen prefill: 0070 |

**Rozkład zysku Qwena** (spec_sweep, 6 promptów × 3 seedy, T=1, Qwen UD-Q4_K_XL, ms/krok; `NOTES.md:183,224,231,239,255,274,279,285,293,329,375`, `STATUS-NEXT.md:10`):

| etap | łatki | ms/krok | t/s | Δ ms | klasa dominująca |
|---|---|---|---|---|---|
| ROCm 2026-10-12 (po 0001–0005, KV q4_0, MTP n=4, słownik 64k) | — | 41.7 | 74.5 | — | — |
| A3–A5: epilog, prolog GDN, conv | 0012–0014 | 37.71 | 83.3 | −4.0 | MODEL (GDN) + GEN (epilog) |
| A6: producenci q8_1, IMROPE, FWHT | 0015–0019 | 36.38 | 86.4 | −1.33 | GEN-CUDA/HIP |
| graf draftu MTP | 0020 | 35.67 | 88.1 | −0.71 | MODEL (MTP) |
| K1: MMVQ wielokolumnowe | 0021–0022 | 33.17 | 94.7 | −2.50 | AMD-RDNA3 |
| K2: małe kernele (DPP, para, GDN) | 0023–0028 | 32.14 | 97.8 | −1.03 | mieszane |
| K3: host | 0029–0031 | 30.97 | 101.5 | −1.17 | GEN-host |
| S2: draft IQ4_XS | 0032 | 29.76 | +1–3% | −1.21 | MODEL (MTP) |
| S4: lag/replay GDN | 0033–0036 | 29.36 | 102.9 | −0.40 | MODEL (GDN) |
| S3+T1: host pętli spekulacji | 0047 | 28.94 | 104.2 | −0.42 | GEN-host |
| PM4 replay | 0060 | 27.80 | 108.8 | −1.36 | AMD-RDNA3 |
| stan końcowy | 70 łatek | 27.74 | 109.0 | Σ −14 | — |

Rozkład wg klasy `[INFERENCE: podział wewnątrz grup K2/A3–A6 szacowany z µs w commitach]`: MODEL ≈ 6.7 ms (48%), AMD-RDNA3 ≈ 4.2 ms (30%), ogólne ≈ 3.1 ms (22%). Przed tym punktem startowym MMVQ 2–8 kolumn (RDNA3) dało 68.6 → 82.3 t/s (+20%), cache q8_1 (ogólne) +2–4%, a słownik draftu (MTP) +7.5% (`NOTES.md:42-47,82-88`).

**Rozkład zysku LFM2.5** (llama-bench tg128, ms/token, przeplatane A/B; suma przyrostów z różnych sesji, więc przybliżona; `NOTES.md:345-375`):

| grupa | łatki | Δ ms/token | udział |
|---|---|---|---|
| fuzje MoE (routing, down+reduce, q8_1 z normy i gate/up) | 0049, 0051, 0053, 0056 | −0.565 | ~34% |
| PM4 replay | 0060 | −0.463 | ~28% |
| fuzje LFM2 shortconv | 0050, 0054, 0062 | −0.366 | ~22% |
| atencja (kvq q8_0, attn_prep, combine+FWHT) | 0055, 0057, 0058 | −0.207 | ~12% |
| MMVQ n=1 2 wiersze + zbiorczy upload | 0052, 0059 | −0.135 | ~8% |
| sampler kar (serwer, osobno) | 0048 | 5.79 → 5.11 ms (+13%) | host |

### 2.2 Playbook: co faktycznie robiliśmy

#### 2.2.1 Profilowanie (kolejność kroków)

1. **Odtworzenie bazy i sufitu.** Najpierw wynik end-to-end na świeżym serwerze (`serve_bench.py`, potem `spec_sweep.py`), potem sufit pasma.
   - Qwen: `mul_mat_vec_q` czyta wagi z 81–88% z 960 GB/s (`NOTES.md:54`).
   - LFM: ~1.8 GB/token, czyli próg ~1.9 ms (~500 t/s) (`NOTES.md:338`).
   - Telefon: ten sam schemat, czyli sufit pasma i sufit SDOT przed jakąkolwiek zmianą (`PROMPT-minicpm-speed.md`, Etap 0).
2. **Mapa czasu per token lub krok.** Trace rocprofv3 pod llama-bench albo pod serwerem (`prof_serve.sh`, `trace_breakdown.py`, `tok.py`), z następującym podziałem:
   - kernele/token i µs/wywołanie;
   - GB/s per miejsce wywołania;
   - suma przerw między kernelami;
   - liczba kerneli na krok.

   Przykład dla LFM: 720 kerneli/token, mediana przerwy 3.1 µs, 3.77 ms pracy z 5.05 ms (`lfm-decode.md`, Phase A).
3. **Klasyfikacja strat** w trzech kubełkach:
   - pasmo, czyli zły GB/s w matvec;
   - narzut uruchomień: Qwen ~2000 kerneli × 3.2 µs ≈ 16% (`NOTES.md:57`);
   - host, czyli sampler, maski i rollback (`NOTES.md:278`, `0047`).
4. **Mikrobenchmark granicy kernela** przed dużą inwestycją:

   | ścieżka | koszt granicy |
   |---|---|
   | HIP graph | 2.53–2.75 µs |
   | każda ścieżka AQL | ≥ 2.08 µs |
   | PM4 IB | 0.46–0.86 µs |

   Ten pomiar uzasadnił 0060 (`NOTES.md:358,373`).
5. **Ablacja zamiast zgadywania.** Build `-DGGML_MMQ_ABLATION` pokazał, że prefill to ~66% vec_dot/epilog, a nie ładowania. To zatrzymało pracę nad prefetchem i skierowało ją na epilog (0070) (`qwen-round5.md`, P0).
6. **Decyzje z rocprofv3 w modelu, nie z mikrobencha.** Mikrobench mylił się co do Q6_K i GLC|DLC (`NOTES.md:247-248`).

#### 2.2.2 Pętla hipoteza → łatka → bramka → A/B

1. **Hipoteza z budżetem.** Każdy pomysł ma szacunek w µs albo ms/krok przeliczony na t/s. Przykład ze Straty: „1 ms/krok ≈ +2.9% t/s” (`research/strata/README.md:178-179`).
2. **Gałąź i worktree na rundę.** Było 25 gałęzi `opt-*`, a `~/wt` ma 40+ katalogów.
3. **Łatka z przełącznikiem.** Jest `GGML_HIP_*=0` / `LLAMA_*=0`, a od 0024 wspólny `ggml_cuda_env_switch`. A/B robi się w jednej binarce, więc odpada zmienna „inny build”.
4. **Testy op-level:**
   - `test-backend-ops` dla zmienionych opów;
   - nowe przypadki dla każdej fuzji (MUL_MAT_PAIR, RMS_NORM_GATE, MOE_DOWN_REDUCE, NORM_ROUTER_TOPK, SHORTCONV, ATTN_PREP, FFN_GATE_UP_DOWN, SSM_CONV_LAG_CACHE_FUSION);
   - harness bitowy na 2000 wierszy z wartościami skrajnymi (0025).
5. **Bramka poprawności**, w dwóch odmianach:
   - **Bitowa**: greedy md5 (plain i MTP, oba modele) na świeżym serwerze, hash FNV pełnych logitów 64 kroków przy głębokości 0 i 3000 (`lfm-decode-round2.md:7`), a dla prefillu logity 2048 tokenów.
   - **Numeryka**: `llama-perplexity --kl-divergence` względem referencji f16-KV (wikitext-2, 3×16k, ubatch 1 = kernele dekodowania). PASS, gdy ΔKLD ≤ 2σ, Δsame-top ≥ −2σ i KLD99.9 ≤ 1.25× (`tools/kld-canary.md`). Sampler: harness CPU (312k wektorów) i `samp_ab.py` na serwerze (`NOTES.md:384`).
6. **Przeplatane A/B:**
   - llama-bench `-r 5` × 3 rundy albo spec_sweep 2 rundy;
   - metryką jest **ms/krok**, a nie t/s, bo t/s przy T=1 zależy od wylosowanego tekstu (`NOTES.md:168`);
   - ABBA i sparowany 95% CI w `loo.py`.
7. **Decyzja i zapis.** Zmianę scalamy tylko przy realnym zysku. Przykład odrzucenia: GDN fast był bitowy, ale +0.15% to szum, więc nie scaliliśmy (`NOTES.md:398`). Wyniki negatywne trafiają do NOTES z liczbami.
8. **Po instalacji:** greedy md5 = baza (`STATUS-NEXT.md:16`) i soak (`pm4_soak.py`: ~4 min na model, mieszane długości, cache, follow-upy).

#### 2.2.3 Narzędzia, które zbudowaliśmy

| narzędzie | ścieżka | rola | stan |
|---|---|---|---|
| `serve_bench.py`, `quick_quality.py`, `greedy_check.sh`, `results.jsonl` | `qwen-opt/` | pierwsze pomiary e2e i jakości (09.10) | używane, 49 wpisów |
| `spec_sweep.sh/.py`, `sweep_summary.py`, `spec_sweep.jsonl` | `qwen-opt/` | t/s, ms/krok, tok/krok, akceptacja; 6 promptów PL/EN × seedy; restart serwera i SIGKILL po 15 s | 182 konfiguracje |
| `long_ctx_bench.py`, `cache_bench.py` | `qwen-opt/` | prefill/decode 1.7k–94k; scenariusze cache promptu | używane |
| `tools/fusion/greedy.sh`, `lh.sh` + `logit_hash.cpp` | `tools/fusion`, `~/wt/lfm*-prof` | bramka bitowa (md5 tekstu, hash logitów) | używane w każdym commicie |
| `prof_serve.sh`, `trace_breakdown.py`, `kernel_bw.py`, `tok.py`, `steps.py` | `qwen-opt/`, `tools/fusion` | rocprofv3 per token/krok, GB/s per wywołanie | używane |
| `mmvq-bench/` (`mmvq_bench.cpp`, `mm_dump.cpp`, `verify_mmvq.py`) | `qwen-opt/mmvq-bench` | mikrobench „na zimno” (> 96 MB Infinity Cache), bitowy dump | używane, wnioski weryfikowane w modelu |
| `det_probe.py` | `qwen-opt/` | determinizm w obrębie jednego serwera | wykrył problem upstream |
| `pm4_soak.py`, `GGML_HIP_PM4_DEBUG=1/2/3` | `qwen-opt/`, łatka 0061 | soak bezpieczeństwa i czasy taśmy PM4 | używane |
| `samp_ab.py` + harness CPU samplera | `qwen-opt/`, `~/wt/samp-harness` | sampler slow == fast | używane |
| `loo.py` (leave-one-out) | `tools/` | ABBA, sparowany CI, flagi NEUTRAL / REMOVAL FASTER | dry-run/fake OK; **GPU niewykonane** (~3.8 h + buildy) |
| `kld_gate.py`, `kld_canary.sh`, `perturb_gguf.py` | `tools/` | bramka KLD z kanarkami, które muszą FAIL | sprawdzone na prawdziwych logach; **kanarki GPU niewykonane** (~2 h) |
| `kt/kt.py` (Kernel Tuner) | `tools/kt` | 39 kształtów MMVQ n=1, MoE, GDN; 53 warianty; ISA harnessu = produkcja | kompilacja i ISA OK; **strojenie GPU niewykonane** |
| `gdnemu.py`, `gdncmp.py`, `isadiff.py` | `research/round6/gdn-isa-tools` | symboliczna emulacja ISA i diff ISA (dowód bitowości offline) | używane w rundzie 6 |
| `run-llm.sh`, `gpu-power.sh`, `gpu-powercap.service`, `gpu-keepawake/` | `qwen-opt/` | launcher, limit 285 W, brak usypiania karty | produkcyjne |
| REACTOR | `KERNEL/monitor/` | monitor TUI: GPU, CPU, t/s z logu llama-server, tylko odczyt sysfs | produkcyjne, ~3.3% rdzenia |
| locki `/tmp/gpu.lock`, `/tmp/quiet.lock`, porty 18433–18499 | `tools/README.md` | serializacja GPU między agentami | konwencja |

#### 2.2.4 Tryby awarii, które trafiliśmy (z liczbami)

| # | problem | objaw | obejście lub reguła | źródło |
|---|---|---|---|---|
| 1 | Kontrakcja FMA przez kompilator | rozwinięta suma x·x: 1 ulp w ~4% wierszy; GDN fast: 94 vs 83 FMA, inny md5 | jawny łańcuch `fmaf`, `ggml_cuda_no_contract`, nie ruszać źródła starego kernela; diff ISA | `0025`, `0027`, `qwen-round5.md` |
| 2 | Kolejność akumulacji w FA | nowy kafel prefillu: KLD 0.0135 | 0043: chunki K w kolejności, potem KLD = 0 | `0043` |
| 3 | Determinizm w obrębie serwera | ten sam greedy request daje inny tekst przy 1. i 2. wywołaniu (rozjazd po ~270 znakach); upstream też | greedy md5 **zawsze na świeżym serwerze** | `NOTES.md:377` |
| 4 | Spekulacja zmienia numerykę batcha | MTP rozjeżdża się z plain po 129 znakach, DFlash po 229; zmiana draftu zmienia tekst przy remisie | porównywać MTP z bazą MTP, nie z plain | `qwen-round5.md`, `NOTES.md:287` |
| 5 | Wolna ścieżka samplera wyzwalana przez klienta | `reasoning_control` z web UI, budżet myślenia, `repeat_penalty` 1.05 w GGUF LFM, gramatyka narzędzi, `logit_bias`, `n_probs`: pełna tablica 128k/248k kandydatów; LFM 293 → ~255 t/s | 0048, 0065–0069 | `NOTES.md:345,381-392` |
| 6 | rocprofv3 nie widzi dispatchy PM4, liczniki PMC zwracają 0 | brak widoku per kernel po 0060 | własne znaczniki czasu w taśmie (0061) | `0061`, `NOTES.md:256` |
| 7 | Mikrobench kłamie | Q6_K, GLC|DLC: inna decyzja niż w modelu | decyzje tylko z rocprofv3 w modelu | `NOTES.md:247` |
| 8 | Zombie serwery i współdzielony VRAM | DFlash wisi na SIGTERM, wynik MTP 5.6 t/s; serwer agenta K4 na porcie 8097 trzymał VRAM | SIGKILL po 15 s, locki, osobne porty, `pgrep` przed startem | `NOTES.md:160,300` |
| 9 | Runtime suspend (BACO) | VRAM ląduje w GTT, 4.4 t/s zamiast 92 | `power/control=on` (root) albo trzymanie kontekstu KFD (`gpu-keepawake`) | `NOTES.md:122-126` |
| 10 | Szum t/s przy T=1 | t/s zależy od wylosowanego tekstu bardziej niż od kernela | metryka ms/krok, seedy, przeplatanie | `NOTES.md:168` |
| 11 | Siatka = dokładnie pojemność fal (3072 bloki na 96 CU) | bimodalne 13.6 / 14.6 µs per proces | 4 wiersze/blok (0062) | `NOTES.md:378` |
| 12 | Błędny roofline | „1075 GB/s, 112% peaku” liczone na token zamiast na przebieg | bajty na przebieg modelu × tok/krok | `NOTES.md:104` |
| 13 | Benchmark z jednym promptem | „DFlash 120 t/s” to 1 prompt; na zestawie ≈ MTP | zawsze 6 promptów × seedy | `NOTES.md:158` |
| 14 | OOM i termika | `-ub 2048` daje OOM przy 204k; junction 106°C; karta na limicie mocy | limit 285 W, ub 512 | `NOTES.md:118,218` |
| 15 | Obciążenie CPU psuje pomiar | pomiar `-bs` do powtórki | `quiet.lock`, osobne okno pomiarowe | `NOTES.md:169` |
| 16 | Commity bez pomiaru | 0066–0070 z dopiskiem „UNMEASURED” (brak GPU) | stan pomiaru jako metadane commita; zmierzone później | łatki 0066–0070 |
| 17 | Losowe spowolnienia per proces | gate+up 24.3 → 27.2 µs w 4/8 profili, także na buildzie bez zmian | A/B na wielu procesach, nie na jednym | `NOTES.md:359` |

#### 2.2.5 Szacunek godzin (agenci, GPU)

Źródła: daty autorskie 70 commitów (`git log e60eff95f..amd-opt`), mtime raportów, znaczniki `spec_sweep.jsonl` i `results.jsonl`. Gałęzie robocze (opt-k1…k5, s2…s4, t2, lfm…lfm4, samp, qwen5, gdn6, mmq6, tools6) pokazują równoległych agentów. Rozbicie na agento-godziny to `[INFERENCE]`.

| okno (UTC) | praca | h zegarowe | wskaźniki |
|---|---|---|---|
| 10-09 13:16–18:51 | Qwen: baza, MMVQ 2–8, cache q8_1, słownik draftu (0001–0005) | ~5.6 | 49 pomiarów w `results.jsonl` |
| 10-10 ~19–23:30 | moc/BACO, sweep MTP/DFlash, research `drafters/algorithms/stepcost` | ~4 | 21 sweepów |
| 10-12 11:30–22:00 | Vulkan 0006–0010, FA kvq, fuzje A3–A6, graf MTP | ~10.5 | 35 sweepów |
| 10-13 11:55–24:00 | K1, K2, K3, S2, S4, K4, T1 | ~12 | 52 sweepy |
| 10-14 00:00–03:15 | T2, prefill K5/T3, S3 | ~3.2 | — |
| 10-14 11:40–23:00 | LFM: baza i rundy 1–4 (0048–0064) | ~11.3 | 74 sweepy (razem z Qwenem) |
| 10-15 00:15–22:00 | sampler 0065–0069, Qwen r5/r6, tools6, 0070 | ~14 | rundy offline (ISA) w czasie zakazu GPU |
| **razem** | | **~60** | |

| model | h zegarowe | agento-h `[INFERENCE ×1.5–3]` | GPU-h `[INFERENCE]` | łatek |
|---|---|---|---|---|
| Qwen3.8-27B (z Vulkanem i prefillem) | ~40 | ~60–120 | ~15–25 | ~47 + 0070 |
| LFM2.5-24B-A2B | ~11 | ~15–30 | ~5–10 | 17 |
| wspólne (sampler, narzędzia) | ~9 | ~15–25 | ~2 | 5 + narzędzia |

Dolna granica GPU: suma sesji `spec_sweep` to 6.8 h (182 konfiguracje, mediana 2.15 min). Kolejka czekająca na GPU: LOO ~3.8 h + buildy, kanarki KLD ~2 h, Kernel Tuner (`tools/README.md`).

### 2.3 Analiza uogólnienia

#### 2.3.1 Macierz uogólnienia (rodziny łatek × cel)

Legenda:
- **AUTO**: działa bez pracy, wymaga tylko bramki i A/B;
- **TUNE**: ten sam kod, potrzebne strojenie parametrów lub tabel (Kernel Tuner);
- **PORT**: przepisanie na inną ISA lub inny backend;
- **N/A**: nie dotyczy (inna ścieżka upstream albo brak instrukcji).

Ocena oparta na: strażnikach HIP i DPP w łatkach (grep), listach typów w commitach oraz notatkach o gfx12 i gfx1030 z `research/tensorfold/kernels.md:250-252` i `research/strata`. Ocena dla innych GPU to `[INFERENCE]`, bo nic poza gfx1100 nie było mierzone.

| rodzina | łatki | inny model, ten sam 7900 XTX | inne RDNA3 (7900 XT/GRE, 7800/7700, W7900) / RDNA3.5 (gfx1151) | RDNA4 (gfx1200/1201) | RDNA2 (gfx1030) | NVIDIA (CUDA) | Apple Metal | Vulkan (dowolny GPU) |
|---|---|---|---|---|---|---|---|---|
| F1 host, sampler, pętla spekulacji | 0029, 0031, 0039, 0047, 0048, 0065–0069 | AUTO | AUTO | AUTO | AUTO | AUTO | AUTO | AUTO |
| F2 spekulacja na poziomie grafu (słownik draftu, graf łańcucha, requant draftu, K/V-only) | 0004, 0020, 0030, 0032, 0041 | AUTO dla rodziny qwen35 z MTP; inne MTP: PORT grafu | AUTO | AUTO | AUTO | AUTO (ggml_argmax/get_rows) `[INFERENCE]` | AUTO, jeśli opy są w Metal `[INFERENCE]` | j.w. |
| F3 stan rekurencyjny lag/replay (GDN, conv) | 0014, 0033–0038 | AUTO dla hybryd GDN (Qwen3.5/3.6/3.8, Qwen3-Next `[INFERENCE]`); Mamba/LFM2 + spekulacja: PORT | AUTO | AUTO (bez WMMA) | AUTO | kompiluje się (kod wspólny), niesprawdzone | PORT (nowy op `GATED_DELTA_NET_LAG`) | PORT |
| F4 eliminacja kwantyzacji q8_1 i fuzje wspólne | 0003, 0012, 0015, 0017, 0019, 0024, 0056, 0057, 0059 | AUTO, gdy wzorzec grafu pasuje | AUTO | AUTO | AUTO | kompiluje się; zysk mniejszy, bo tańsza granica grafu CUDA `[INFERENCE]` | N/A (inny backend) | PORT (Vulkan ma własne fuzje) |
| F5 MMVQ strojone pod gfx11 (wiersze/blok, waves_per_eu, buffer resource, GLC|DLC) | 0001, 0002, 0021, 0022, 0052, 0062, 0064 | AUTO (kształty: TUNE) | TUNE (liczba CU 96 vs 84/80/60/54/40; gfx1151 inna pamięć) | TUNE + test ISA | TUNE | N/A (ścieżka CUDA upstream) | N/A | N/A (odpowiednik: 0007–0010) |
| F6 kernele WMMA (FA kvq, small-N 9–16, MMQ epilog VOPD) | 0011, 0037, 0055, 0058, 0070 | AUTO (KV q4_0 / q8_0, D 64/128/256) | AUTO + TUNE | PORT (inny układ operandów WMMA gfx12) | N/A (brak WMMA) | N/A (mma FA upstream) | N/A | N/A |
| F7 granica kernela: PM4 replay | 0060–0061 | AUTO (każdy przechwycony graf) | AUTO `[INFERENCE]` | PORT/test (pakiety PM4 per generacja) | PORT/test | N/A (graf CUDA ~0.8 µs/węzeł, `repos/29-cuda-rust.md:51`) | odpowiednik ICB `[INFERENCE]` | N/A |
| F8 fuzje GDN (Qwen) | 0013, 0016, 0027, 0028, 0035, 0045 | tylko rodzina qwen35 | AUTO (DPP: tylko HIP) | AUTO/TUNE | AUTO | częściowo kompiluje się; DPP nie | PORT | PORT |
| F9 fuzje MoE (routing, down+reduce) | 0049, 0051, 0053 | AUTO dla MoE z dopasowanym wzorcem `topk_moe` (64/4 testowane) | AUTO | AUTO | AUTO | kompiluje się | PORT | PORT |
| F10 fuzje LFM2 shortconv | 0050, 0054, 0062 | tylko rodzina LFM2 | AUTO + TUNE (0062: liczba CU) | TUNE | TUNE | 0050 kompiluje się, 0054 tylko RDNA | PORT | PORT |
| F11 Vulkan RDNA | 0006–0010 | AUTO | AUTO | AUTO (RDNA3/4 w kodzie) | TUNE | N/A | N/A | tylko AMD |
| F12 prefill: kafle MMQ/FA | 0040, 0042, 0043, 0045 | AUTO | TUNE (CU) | TUNE | TUNE | 0043 AUTO | N/A | N/A |

**Wnioski z macierzy:**
- Na **innym modelu na tym samym GPU** automatycznie przenosi się F1, F4, F5, F6, F7, F11 i F12. To jest właśnie zmierzone +17% dla LFM (tg128 169.3 → 198.3 t/s, `NOTES.md:339`). Nowej kampanii wymagają tylko nowe wzorce architektury (MoE, conv, MTP innego typu).
- Na **innym RDNA3** kod się kompiluje, ale progi zależne od liczby CU (0040, 0052, 0062: siatka 3072 = 96 CU × 32 fale) trzeba przestroić. Na to wystarczy Kernel Tuner z bramką bitową, bez agenta piszącego kernele.
- **RDNA4** wymaga przepisania rodziny F6 (WMMA gfx12), a **RDNA2** jej nie ma.
- Na **NVIDIA** w całości przenoszą się F1 i F2, a F3, F4, F9 kompilują się, ale są niesprawdzone. Rodziny F5, F6, F7 nie mają sensu, bo upstream CUDA jest głównym celem ggml i ma własne strojone ścieżki.
- **Metal i Vulkan** dostają tylko F1 i F2. Reszta to nowa kampania na innym backendzie.

#### 2.3.2 Co wymaga nowej kampanii agentów

- **Nowa architektura modelu** (nowy wzorzec grafu): fuzje typu F8/F9/F10, prolog i epilog warstwy, stan rekurencyjny dla spekulacji. LFM pokazał koszt ~11 h zegarowych na model na znanym GPU z gotową infrastrukturą (cache q8_1, producenci, env switch, narzędzia).
- **Nowa architektura GPU:** od nowa trzeba zrobić:
  - mikrobench granicy kernela;
  - sufit pasma;
  - strojenie MMVQ;
  - kernele macierzowe (WMMA/MMA);
  - ścieżkę graph replay.

  Dla Qwena na gfx1100 zajęło to większość z ~40 h. Na nowej arch spodziewam się podobnego rzędu, ale bez gotowych prymitywów DPP/WMMA `[INFERENCE]`.
- **Nowy backend** (Metal, Vulkan, SYCL): wszystko poza F1/F2, w innym języku shaderów.

#### 2.3.3 Jak mogłaby wyglądać „biblioteka przepisów”

Przepis = rodzina łatek + predykat stosowalności + przestrzeń parametrów + bramka + reguła domyślności:

```yaml
recipe: mmvq_n1_rows            # F5
applies_if:
  backend: hip
  arch: [gfx1100, gfx1101, gfx1102, gfx1151]
  op: MUL_MAT ncols_dst=1
  types: [Q4_K, Q5_K, Q6_K, Q8_0]
params:
  ROWS: [1, 2, 4]
  NWARPS: [1, 2, 4, 8]          # przestrzeń z tools/kt
  shape_class: from_gguf        # kt.py shapes -> shapes.json
gate: bitwise_vs_production     # kt.py: tolerancja vs float64 + test bitowy
default_rule: ">=3% w przeplatanym A/B, nie gorzej na żadnym kształcie"   # reguła Straty
switch: GGML_HIP_MMVQ_N1_ROWS
```

| rodzina | parametry | generator lub tuner | bramka |
|---|---|---|---|
| matvec (MMVQ n=1…16) | arch, typ kwantu, ncols, wiersze/blok, nwarps, waves_per_eu, szerokość ładowań, polityka cache | `kt.py` (39 kształtów z GGUF, 53 warianty) | bitowa vs produkcja (ta sama kolejność sum per wiersz) |
| eliminacja q8_1 i fuzje elementwise | wzorzec grafu (norm→mul→rope→fwht→q8_1), hidden, head_dim | matcher wzorców w `ggml-cuda.cu` + szablony | BIT + nowy przypadek test-backend-ops |
| MoE decode | n_experts, n_used, funkcja bramki, ffn_dim | szablony (0051, 0053) | BIT + TOPK_MOE z NaN/−inf |
| stan rekurencyjny + spekulacja | wymiary stanu, d_conv, typ (GDN/conv/Mamba) | nowy op + CPU reference | BIT (greedy MTP 4/8/12, cache restore) |
| atencja decode na kwantyzowanym KV | typ KV, D, GQA, ncols ≤ 16, instrukcja macierzowa | szablon per arch (WMMA gfx11 / gfx12 / mma) | KLD (bramka 2σ) |
| graph replay | arch (PM4 per generacja, CUDA graph, ICB) | runtime moduł | BIT + soak |
| host/sampler | — | — | SAME-TOK harness + serwer |
| config | backend, spekulacja (typ, n, słownik), KV, ub, ctx, moc/BACO | sweep na maszynie użytkownika | greedy md5 / KLD tylko dla zmian KV |

Dzisiejszy stan jest daleko od tego modelu. 14 z 22 łatek, które istnieją tylko w buildzie, ma konflikty revertu (`loo-plan.md:5`), a `mmvq.cu` dotyka 20 kolejnych łatek. Łatki są stosem liniowym na jednym commicie upstream, a nie niezależnymi rodzinami.

#### 2.3.4 Ile zysku dostanie użytkownik z innym GPU lub modelem

(a) to sam config, (b) to config z naszymi łatkami ogólnymi (F1–F4, bez kampanii), (c) to kampania per arch lub per model. Wszystkie wartości są względem upstream llama.cpp z tym samym modelem. Liczby dla innych GPU to `[INFERENCE]` oparte na udziałach z §2.1.

| scenariusz | (a) config | (b) + łatki ogólne | (c) kampania | podstawa |
|---|---|---|---|---|
| Qwen3.8-27B, 7900 XTX (nasz przypadek) | ×1.8–2.2 vs brak spekulacji (38.8 → 85.6 t/s, Vulkan MTP n=4); +18% za samą aktualizację llama.cpp | ok. +8–12% na krok (≈22% z 14 ms) | 109 t/s: +27% vs najlepszy upstream config, ok. ×1.6 vs upstream ROCm MTP n=3 | `NOTES.md:42-48`, §2.1 |
| inny model, ten sam 7900 XTX (np. MoE bez MTP) | KV q8_0 vs q4_0, BACO, sampler bez kar | **+17%** (zmierzone na LFM: łatki z Qwena) | +49% więcej (LFM 198 → 295 tg128), razem ×1.74 | `NOTES.md:339,375` |
| inna karta RDNA3 / RDNA3.5 | j.w. | +10–15% po przestrojeniu tunerem | +30–60%, kilka godzin tunera + ewentualnie 1–2 dni agenta | `[INFERENCE]` |
| RDNA4 (R9700, 9070 XT) | j.w. | +5–10% (F1, F4, F5 po strojeniu) | nowa kampania WMMA gfx12 i PM4; +30–60% | `[INFERENCE]`; gfx12 WMMA ≠ gfx11 (`tensorfold/kernels.md:252`) |
| NVIDIA RTX 30/40/50 | **główna dźwignia**: spekulacja (MTP/DFlash), KV, FA | +2–5% typowo; +13–15% w ścieżkach samplera z karami, gramatyką, UI | +10–30% `[INFERENCE]`: upstream CUDA jest najlepiej strojony; reszta przewagi konkurencji pochodzi z draftera | L40S, 27B: llama.cpp 71 vs vLLM 96 vs TensorFold 152 t/s (`tensorfold/issues.md:34`) |
| Apple Metal | spekulacja, KV | F1/F2: +2–15% (jak wyżej) | nowa kampania Metal | M5 Max: mlx_lm 32–33 vs TensorFold 151 t/s kod (`tensorfold/qwen27.md:340`) |
| telefon (CPU ARM, MiniCPM) | wątki, repack, `-ub`, flagi builda | — | prefill 35 → 100, decode 9 → 17–18 t/s (dane użytkownika; lokalnie mam tylko prompt, bez logów wyników) | `telefon/PROMPT-minicpm-speed.md` |

### 2.4 Bazy porównawcze (ten sam sprzęt: RX 7900 XTX, gfx1100)

| konfiguracja | Qwen3.8-27B t/s | LFM2.5-24B-A2B t/s | benchmark | źródło |
|---|---|---|---|---|
| stary build b356fa262 (2026-09-01), ROCm, MTP n=3 | 59.2 (mix) / 58.2 (EN) | — | serve_bench, T=0, 256 tok. | `NOTES.md:10,42` |
| upstream e60eff95f ROCm, bez spekulacji | ~36.6–38.6 | tg128 169.3 (KV q4_0) | serwer / llama-bench | `NOTES.md:47,339`, `repos/30-hipfire.md` |
| upstream e60eff95f ROCm, MTP n=3 | 68.6 (EN) | n/d (brak MTP) | serve_bench T=0 | `NOTES.md:43` |
| upstream ROCm, DFlash2 n=7 | 97.7 (EN) | — | serve_bench T=0 | `NOTES.md:45` |
| upstream Vulkan RADV: bez spek. / MTP n=4 / DFlash2 n=6 | 38.8 / 85.6* / 127* (kod EN) | — | serve_bench | `NOTES.md:48` |
| fork, przed pracą pod LFM | — | tg128 198.3; serwer 173 | llama-bench / spec_sweep | `NOTES.md:335,339` |
| **fork amd-opt (70 łatek)** | **109.0** (T=1, 6 × 3), tg128 bez spek. 43.2, pp4096 1115 | **293.7** (serwer), tg128 289.7–294.8, pp4096 6175; 98k: 213 | spec_sweep / llama-bench | `STATUS-NEXT.md:8-14` |
| hipfire (konkurent, ten sam GPU, ich własny kwant MQ4 15 GB) | AR 50.8–54.3; MTP 76.4 (1 prompt); DFlash kod 307.9 (1 prompt); prefill ~3000 (W4A4, stratny) | — | ich liczby | `repos/30-hipfire.md` |
| **Ollama** | **brak pomiaru** | **brak pomiaru** | — | luka |
| **LM Studio** | **brak pomiaru** | **brak pomiaru** | — | luka |

\* mieszanka EN+PL.

**Uwagi do porównywalności:**
- 59.2 i 109.0 to różne benchmarki: serve_bench przy T=0 kontra spec_sweep przy T=1. T=1 jest dla spekulacji trudniejsze (MTP n=5: T=0 86.3 vs T=1 81.1, `NOTES.md:151,154`), więc różnica nie jest zawyżona `[INFERENCE]`.
- Nie ma pomiaru upstream na spec_sweep przy T=1. Najbliższy to ROCm z 2026-10-12 (z 0001–0005): 74.5 t/s.
- „Stockowe narzędzia 40–60 t/s” (teza użytkownika) pasuje do tych liczb: bez spekulacji ~37–39 t/s, stary build z MTP 59 t/s. Nie sprawdziłem jednak, co domyślnie robią Ollama i LM Studio (backend, spekulacja, KV), bo zadanie ograniczało mnie do materiału lokalnego. **Do zmierzenia** tym samym `spec_sweep` z OpenAI-compatible endpointem.

## 3. Co to znaczy dla naszego produktu

### 3.1 Rekomendacje

1. **Podzielić „optymalizację przez noc” na trzy warstwy i uczciwie je nazwać:**

   | warstwa | gdzie działa | co zawiera | szacowany zysk |
   |---|---|---|---|
   | L1 config | lokalnie, minuty | wybór backendu, spekulacji (typ, n, słownik draftu), KV, `-ub`, kontekst; naprawa BACO i limitu mocy; sampler bez wolnych ścieżek | to daje ×1.5–2.2 vs naiwna instalacja |
   | L2 tuning | lokalnie, godziny | Kernel Tuner po gotowej przestrzeni wariantów, tylko konfiguracje bitowo równe produkcji; przeplatane A/B | +5–15% na znanej rodzinie arch |
   | L3 przepis | u nas, kampania | nowe kernele i fuzje dla (arch, model), dostarczane jako paczka | +30–70% dla pary, którą przerobiliśmy |

   Ekran „before → after” powinien pokazywać, z której warstwy pochodzi zysk.
2. **Zacząć od par (arch, rodzina modelu), na których mamy dowód:**
   - gfx1100 z rodziną qwen35 (GDN + MTP);
   - gfx1100 z MoE w stylu LFM2.

   Dla innych kart RDNA3 obiecywać tylko L1+L2, dopóki nie zmierzymy ich na prawdziwym sprzęcie.
3. **Wydzielić i upstreamować rzeczy ogólne:**
   - sampler 0031, 0048, 0066–0069;
   - host spec-loop 0047;
   - clamp q8_1 0023;
   - async i zbiorcze wejścia 0029, 0059;
   - cache i producenci q8_1 0003, 0015.

   Każda łatka w upstream to jedna łatka mniej do rebase'owania, a samplera nie warto trzymać jako wyróżnika, bo dotyczy wszystkich GPU. Wyróżnikiem zostają przepisy L3 i fabryka (harness, bramki, baza wyników).
4. **Zamknąć luki poprawności przed produktem:**
   - KLD dla 0011 na Qwenie;
   - uruchomić kanarki KLD (`kld_canary.sh all`) i LOO (`loo.py run`);
   - dodać do spec_sweep alarm akceptacji: spadek tok/krok > 3% przy tym samym seedzie (`repos/15-tokamax.md:90`).
5. **Reguła produktu: na komputerze użytkownika domyślnie tylko zmiany BIT/SAME-TOK.** Zmiany numeryki (np. KV q4_0 vs q8_0: KLD 0.128 vs 0.044) wymagają jawnej zgody, tak jak zrobił użytkownik przy KV q8_0 dla LFM (`NOTES.md:354`).
6. **Wbudować w aplikację nasze lekcje o awariach:**
   - BACO/keepawake;
   - SIGKILL dla zawieszonych serwerów;
   - świeży serwer do testu greedy;
   - wykrywanie wolnych ścieżek samplera (`reasoning_control`, kary, gramatyka).

   To wszystko są realne problemy użytkownika końcowego, nie tylko laboratorium.

### 3.2 Minimalne narzędzia wewnętrzne do uprzemysłowienia

| # | komponent | co musi robić | co już mamy | czego brakuje |
|---|---|---|---|---|
| 1 | **Farma GPU + kolejka** | per arch (gfx1100, gfx1201, gfx1030, gfx1151, sm_86/89/120, Apple M); locki, porty, sprzątanie procesów, kontrola mocy i termiki, keepawake | `flock /tmp/gpu.lock`, porty 18433–18499, `gpu-keepawake`, limit 285 W, REACTOR | wiele maszyn i scheduler; AMD w chmurze bywa rzadkie, więc część farmy musi być własna `[INFERENCE]` |
| 2 | **Harness testów** | matryca buildów (arch × backend), `test-backend-ops` subsety, nowe przypadki per fuzja, test row-invariance `op(n) == n × op(1)`, harness bitowy kernela, diff ISA, emulator ISA | test-backend-ops + nasze przypadki, `isadiff.py`, `gdnemu.py`, `mm_dump` | CI per arch, test padded width, test NaN/−inf w routerze (`repos/15-tokamax.md:87-90`) |
| 3 | **Serwis bramki poprawności** | (i) greedy md5 plain+spec na świeżym serwerze; (ii) hash logitów 64 kroków na 2 głębokościach; (iii) KLD vs referencja f16 per (model, kwant) z kanarkami; (iv) harness samplera; (v) soak; (vi) alarm akceptacji | `greedy.sh`, `lh.sh`, `kld_gate.py` + `kld_canary.sh` + `perturb_gguf.py`, `samp_ab.py`, `pm4_soak.py`, `det_probe.py` | usługa z API i magazynem referencji (ref .kld LFM to 6.3 GB, `NOTES.md:370`); kanarki nieuruchomione |
| 4 | **Baza benchmarków** | schemat: commit, zestaw łatek, env, sha256 modelu, kwant, backend, sterownik/ROCm, GPU (PCI id, limit mocy, temperatury), ctx, prompty, seed, T; metryki: t/s, ms/krok, tok/krok, akceptacja, pp, VRAM, kernele/token, suma przerw; ABBA + sparowany CI + próg ≥3% (reguła Straty) | `results.jsonl`, `spec_sweep.jsonl`, `long_ctx.jsonl`, statystyka `loo.py` | jedna baza zamiast plików jsonl; pola sprzętowe i termiczne; status „UNMEASURED” jako pole |
| 5 | **Adaptery profilera** | rozkład kroku per token dla rocprofv3, nsys, Metal; widok PM4/replay; jedna linia rozkładu na żądanie | `trace_breakdown.py`, `tok.py`, `PM4_DEBUG` | NVIDIA i Apple; liczniki PMC (dziś 0 na gfx1100) |
| 6 | **Pakowanie przepisów** | rodziny łatek z predykatami (arch, arch modelu, typy kwantów, KV), tabele z tunera (`kt-table-<arch>.inc`), env switch, build per arch, podpisane artefakty; LOO do usuwania martwych łatek; bot rebase na upstream | 70 łatek `git am` na `e60eff95f`, `loo.py`, `kt.py table` | warstwa manifestów i predykatów; rebase (upstream zmienia się codziennie, a `mmvq.cu` dotyka 20 łatek) |
| 7 | **Orkiestracja agentów** | worktree na hipotezę, ledger (NOTES z wynikami negatywnymi), zakaz scalania bez pomiaru, kolejka GPU | konwencje w NOTES i STATUS, `~/wt/*` | formalny ledger i stan pomiaru; wspólny indeks pomysłów (`repos/21-ako4all.md:136`) |

### 3.3 Ryzyka

- **Dryf upstream.** 70 łatek siedzi na jednym commicie z 2026-10-09. Konflikty skupiają się w `mmvq.cu`, `ggml-cuda.cu` i `llama-memory-recurrent`. Bez bota rebase i bez upstreamowania koszt utrzymania rośnie z każdą łatką.
- **PM4 zależy od wnętrzności ROCr** (vendor packet, loader extension, hidden kernargs ROCclr). Aktualizacja sterownika może go zepsuć. Potrzebny jest fallback i soak przy każdej wersji ROCm.
- **Kod „GEN-CUDA/HIP” nigdy nie był uruchomiony na NVIDIA.** Fuzje z ticketami atomowymi i aliasowaniem buforów (0053, 0054, 0057) to obszar ryzyka cichych błędów.
- **Bramka KLD przepuszcza błędy poniżej ~0.005 KLD** (2σ, `kld-canary.md`). Kanarki mają dopiero zmierzyć, gdzie leży ta granica.
- **Brak pomiaru Ollama i LM Studio.** Marketingowe „before” musi być zmierzone tym samym harnessem, inaczej łatwo o nieuczciwe porównanie.
- **Hipotezy co do innych GPU.** Zysk na innych kartach to w całości `[INFERENCE]`. Pierwszy pomiar może pokazać, że część łatek RDNA3 na RDNA3.5/4 przegrywa (Strata: ten sam przełącznik +6% na jednej karcie i −21% na innej, `strata/method.md`).

### 3.4 Otwarte pytania

1. Ile z 70 łatek daje mierzalny zysk osobno? Odpowie `loo.py`, którego jeszcze nie uruchomiliśmy.
2. Jaki jest KLD 0011 (`kvq` q4_0) na Qwenie względem f16 KV i względem starego kernela tile?
3. Jak duży jest zysk (b) na NVIDIA? W maszynie jest RTX 5060 Ti (`hardware/rx-7900-xtx.md:36,105`), więc da się to zbadać lokalnie bez chmury.
4. Czy kampania L3 da się wykonać w ~11 h na nowy model także na nowej arch, czy potrzebna jest najpierw ~40-godzinna kampania „bazowa” per arch?
5. Jaki jest rzeczywisty baseline Ollama i LM Studio na tych samych GGUF (domyślny backend, spekulacja, KV)?

## 4. Źródła (lokalne)

- `~/KERNEL/qwen-opt/NOTES.md`: log optymalizacji; linie cytowane wyżej
- `~/KERNEL/qwen-opt/STATUS-NEXT.md`: stan końcowy 2026-10-15, wyniki 109.0 / 115.5 / 293.7 / 267.3 t/s
- `~/KERNEL/qwen-opt/README.md`: odtworzenie, baza `e60eff95f`
- `~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/0001…0070-*.patch`: wiadomości commitów, diffstaty, grep strażników HIP i DPP
- `~/llama-master`: `git log e60eff95f..amd-opt` (daty 70 commitów), 25 gałęzi `opt-*`, `tools6`
- `~/KERNEL/qwen-opt/spec_sweep.jsonl` (182 wpisy, 2026-10-10…14), `results.jsonl` (49 wpisów, 2026-10-09), `cache_bench.jsonl`
- `~/KERNEL/qwen-opt/tools/README.md`, `tools/loo/loo-plan.md`, `tools/kld-canary.md`, `tools/kt/`
- `~/KERNEL/qwen-opt/research/round6/test-tooling.md`, `gdn-bitwise.md`, `mmq-epilogue.md`, `gdn-isa-tools/`
- `~/KERNEL/qwen-opt/research/qwen-round5.md`, `lfm-decode.md`, `lfm-decode-round2.md`, `lfm-decode-round3.md`, `lfm-decode-round4.md`, `lfm-kv-q4-vs-q8.md`
- `~/KERNEL/qwen-opt/research/strata/README.md`, `strata/method.md`; `research/tensorfold/README.md`, `issues.md`, `kernels.md`, `qwen27.md`, `spec-host.md`
- `~/KERNEL/qwen-opt/research/repos/30-hipfire.md`, `15-tokamax.md`, `21-ako4all.md`, `29-cuda-rust.md`, `11-vllm-xpu-kernels.md`
- `~/KERNEL/benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md`
- `~/KERNEL/hardware/rx-7900-xtx.md`: druga karta RTX 5060 Ti
- `~/KERNEL/monitor/README.md`: REACTOR
- `~/telefon/PROMPT-minicpm-speed.md`, `~/telefon/PROMPT-optymalizacja-modeli.md`: ten sam playbook przeniesiony na CPU ARM
