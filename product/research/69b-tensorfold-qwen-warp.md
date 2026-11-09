# 69b: TensorFold (delta od `cde4fe7`) i qwen-warp (delta od `146a654`)

Data: 2026-11-09. Klony: `~/src/research69/TensorFold` (HEAD `abc39af1`, 2026-11-08, v1.2.5 + Unreleased), `~/src/research69/qwen-warp` (HEAD `689901c`, 2026-11-07, v0.8.0). Bez GPU, bez buildów i bez pobierania wag.

## TL;DR

- **qwen-warp (49 commitów, 0.6.0 → 0.8.0): najważniejsza nowość dla 3090 to DFlash2 w silniku.** Blokowy drafter `incoai/Qwen3.8-27B-DFlash2` (W4A16, 1.15–1.4 GiB) działa w jednym grafie CUDA na cykl (weryfikacja T=8). Na RTX 3090 przy 350 W, przez serwer, z KV bf16 i dla zachłannego dekodowania: kod 183.9 → 276.7 t/s (×1.51), matematyka ×1.38, proza ×0.96, 8 promptów czatu ×1.34, 12 zadań ×1.07. **Na turach agenta z kopiowaniem jest −31% (230 wobec 334 t/s).** Drafter nie mieści się przy długim kontekście (KV draftera 20 KiB/token, pozycje absolutne, bez bufora pierścieniowego), więc z kontekstem 262k na 24 GB nie działa. NEW.
- **Wielu użytkowników:** `--profile multiuser` (5 slotów), GEMV W4 z 16 wierszami na jedno przejście po wagach daje 425 / 441 t/s sumarycznie przy 4 / 8 klientach, wobec 155 t/s dla jednego. NEW.
- **Liczby długiego kontekstu (94–133 t/s przy 32k–262k), KV int4 z WHT i jedno przejście KV na weryfikację są bez zmian.** KNOWN (R63a §14).
- **TensorFold (1023 commity, v1.2.3–v1.2.5): gfx1100 nadal bez wsparcia i bez pomiarów** („as we have no AMD GPU”, CHANGELOG #1694). HIP rośnie tylko na gfx1151/gfx1201. Drafter DFlash2 na HIP już się ładuje (#2477), ale serwer go nie używa. Nie ma żadnej nowej liczby dla Qwen3.8-27B na NVIDIA. DSpine występuje tylko jako negatywny wynik treningowy („DSpine-style spine… within ±0.002 of the control”). Werdykt: nic do adopcji na XTX.
- **Twierdzeń „1.75× nad DFlash2” i „3.3×” nie ma w żadnym z tych repo.** Jedyne „1.75x” to skalowanie qwen-warp przy 2 klientach z obrazami (PERFORMANCE.md:327), czyli inna metryka. Twierdzenia te należą do tematu DSpine (R69a) [INFERENCE].

## 1. qwen-warp: fakty (delta)

Sprzęt we wszystkich pomiarach: jedna RTX 3090 24 GB (sm_86), limit mocy 350 W, ta sama karta obsługuje pulpit (~0.6 GiB) (`docs/PERFORMANCE.md:6`). Model: `ukisai/Swift-1.5-Qwen3.8-27b-INT4` (W4A16 compressed-tensors, 19.48 GB według HF API). To **nie jest** nasz Q4_K_M, więc porównania t/s z naszym forkiem obarcza różnica w kwantyzacji.

| Obszar | Fakt | Źródło | NEW/KNOWN |
|---|---|---|---|
| DFlash2 w silniku | Drafter 5-warstwowy W4A16 z selektorem kandydatów, 7 tokenów na blok, cały cykl to jeden graf CUDA (verify T=8 + accept + drafter), bez pracy hosta między cyklami | `docs/ARCHITECTURE.md` (diff), commit `a4f1e4f` | NEW |
| Cykl (nsys, kod) | 21.0 ms = verify T=8 + accept 18.6 ms + drafter 2.50 ms; GEMV W4 osiągają 820–855 GB/s (92–96% z 891 GB/s) | PERFORMANCE.md §5 | NEW |
| Tokeny na cykl | 4.48 (drafter W4 w silniku) wobec 2.98 dla MTP k=3; kod 5.87 / matematyka 5.50 / proza 3.81 (drafter eager); akceptacja na pozycjach 1→7 spada od 0.87 do 0.26 | §5 | NEW |
| Serwer, KV bf16 | kod 276.7 / proza 113.4 / matematyka 254.0 wobec MTP+ogon 183.9 / 118.0 / 183.9; 8 promptów czatu 210.5 wobec 156.8 (×1.34); 12 zadań ×1.07 | §5 „In the server” | NEW |
| Serwer, KV int4 | kod ×1.50, proza ×1.10, matematyka ×1.42, czat ×1.35, 12 zadań ×1.11 | §5 | NEW |
| Gdzie DFlash2 przegrywa | Kopiowanie promptu: ogon lookup daje 6.6 tok/cykl, DFlash2 4.2 (327 wobec 193 t/s); syntetyczny ślad agenta −31% (230 wobec 334) | §5 „Where it is not faster”; IDEAS.md | NEW. Zgodne z naszą lekcją, że kopia wygrywa z lookupem |
| Pamięć | Drafter 1.15 GiB (codebooki na hoście) / 1.4 GiB plus 20 KiB KV na token kontekstu; `--profile long` (196 608) się nie mieści, maksimum to ok. 125k | USAGE.md:328-338; IDEAS.md | NEW |
| Dokładność | Każda trasa jest dokładna względem własnej weryfikacji. Między kształtami partii (T=4..8 wobec 8) remisy bf16 rozstrzygają się inaczej: 8/11 promptów ma identyczne ids | §5 „Exactness” | NEW. Ta sama klasa zjawiska co nasze GPU verify |
| Kampania kerneli | +1…2.5% (wynik 1.019×); wcześniejsze 1.049× było artefaktem pętli po EOS. Lookup w trasie DFlash2 jest domyślnie wyłączony (`SMK_DF_LOOKUP=1`); głowa z draftowym słownikiem nie zadziałała | §5 „Kernel work” | NEW. Lekcja metodyczna (zgodna z `lekcja-benchmark-kopia`) |
| Batching | GEMV `k_w4` z dwoma kaflami n8 (16 wierszy na jedno przejście po wagach, bity wiersza niezależne od liczby wierszy); 16 wierszy kosztuje ok. 3 ms GEMV więcej niż 8; cykl 1 wiersza 17.3 ms, 8 wierszy 23.7 ms | §7, ARCHITECTURE.md | NEW |
| Wielu użytkowników | 5 slotów: 154 / 278 / 425 / 441 t/s przy C = 1/2/4/8; na jedno żądanie 163 → 98 t/s; „największe k, które się mieści, wygrywa przy każdym B” (`K_BY_B`) | §7 | NEW |
| Wizja | ViT bf16 na GPU: 16 / 65 / 220 ms na obraz 448² / 1024×768 / 1080p; +888 MiB VRAM | §6 | NEW (dla Enigmy jest to informacja poboczna) |
| Długi kontekst | 262 144 z KV int4 i `--host-tables` (23 227 MiB); dekodowanie 94–133 t/s przy 32k–262k; prefill 963 t/s przy 262k | PERFORMANCE.md:14-18 | KNOWN (R63a) |
| Zasilanie i zegary | Jedynie limit 350 W. Brak blokady zegarów, brak undervoltu, brak testów innych limitów („other power limits: not measured”, :22) | PERFORMANCE.md:6,22 | NEW (negatywne: nic do przeniesienia) |

### Porównanie z naszym 3090 (Enigma)

- Nasz fork kvqlean: 79.97 t/s przy n_ctx 262144 i 340 W (`wiki/produkt/final-recipes-nvidia.md:28`). Prompt jest krótki, ale bufor ma pełny rozmiar. qwen-warp przez serwer z MTP: 155 t/s w czacie przy `--max-model-len 16384`. **To nie jest porównanie tych samych warunków**: inna kwantyzacja (W4A16 g128, a u nas UD-Q4_K_XL), inny n_ctx, inne prompty, 350 W wobec 340 W.
- Pozostaje jednak różnica rzędu ×1.5–2 w dekodzie przy porównywalnej wadze 4-bit [INFERENCE]. Wspiera to KNOWN wniosek z R63a, że mamy zapas na 3090: GEMV ich W4 osiąga 92–96% pasma.
- Kontrola przed jakąkolwiek decyzją to test Q1 poniżej: jeden wynajęty 3090 i oba silniki w tej samej sesji.

## 2. TensorFold: fakty (delta v1.2.3–v1.2.5)

| Fakt | Źródło | NEW/KNOWN |
|---|---|---|
| gfx1100 nie jest ani uruchamiany, ani mierzony. Rekordy HIP pochodzą od kontrybutorów („as we have no AMD GPU”) | CHANGELOG.md (#1694) | KNOWN (status utrzymany) |
| HIP: drafter DFlash2 ładowany jako MLX affine-4 g64 i walidowany względem targetu, ale „the server doesn't use the drafter” | CHANGELOG (#2477, #2314) | NEW (ale na XTX nic z tego nie wynika) |
| gfx1151: rundy lane >4 wierszy używają ponownie wag z cache; 27B przy 16 strumieniach na kodzie z ~51 do 75 t/s | #1694 | NEW (Strix) |
| gfx1151: ogon residual+norm daje +1.1% na 27B; MTP w graf z próbkowaniem +4–12% przy T=1 (Qwen3.5/3.6) | #2247, #2455 | NEW (Strix) |
| gfx1151 Flash Next: nowy kernel rzadkiej atencji, prefill o 29–41% krótszy; `madvise(RANDOM)` na tabeli n-gramów daje 35.8 zamiast 24.4 t/s przy pierwszym żądaniu | #1877, #1615 | NEW (Strix) |
| RDNA 3.5: dot2 zaokrągla −0 inaczej niż +0, więc wprowadzono poprawkę bitowej niezmienności kafla prefill | CHANGELOG 1.2.x | NEW (ciekawostka dla naszej deterministyczności na RDNA3 [INFERENCE]) |
| gfx12 (R9700): kafel WMMA z krokiem K=64, LDS ze swizzlingiem i barierą tylko na LDS; epilog silu×up w produkcie WMMA; zysk 3–4% na Qwen3-8B BF16 | #e0b001e1.., c2b77bce | NEW (gfx12, nie gfx11) |
| Metal: Qwen3.8-27B MLX 8-bit czyta kody bezpośrednio: prefill +18% (649→768 t/s przy 2K), dekod +7.6% na M5 Ultra | #2518 | NEW (Apple) |
| Metal: KV w stronach puli (opt-in), Ornith-1.5-122B MoE na M5 Ultra, Nanbeige4.3-33B INT4 (KL 0.0044) | #2283, #1125, #1782 | NEW (Apple) |
| Intel XPU: kontrakt kerneli na Arc Pro B70 przez Level Zero; LFM3-1.7B na Iris Xe; 27B XPU ze wspólnym `shape.h` | #2155, #1696, #1425 | NEW (Intel) |
| CUDA: `TF_QWEN_REQUEST_STARTS=1` na GB10 z 27B+DFlash2: tury 2–6 trwają 0.72–1.33 s zamiast 1.78–2.10 s; przy tej opcji odpowiedź może się różnić | CHANGELOG 1.2.x | NEW (cache prefiksu; nie bezstratne bitowo) |
| CUDA: rollback dzieli bajty z logiem weryfikacji, co daje −147 MiB na strumień dla 27B | #2447 | NEW (pamięć, wiele strumieni) |
| DSpine: „spine w stylu DSpine”: zysk w granicach ±0.002 kontroli (Kolibri) | `docs/recipes/training-a-drafter.md:130` | NEW. Słaby, niezależny sygnał przeciw DSpine jako dźwigni |
| Nowych liczb dla 27B na 3090/4090/5090 brak; Ampere 8.6 od 1.0.5 | grep diffu `cde4fe7..HEAD` | KNOWN |

## 3. Istotność

- **XTX:** z TensorFold nic. Z qwen-warp mamy dwa sygnały metodyczne. (1) Blokowy drafter wygrywa z MTP na tekście nowym, a przegrywa na kopiowaniu, co potwierdza KNOWN [[lekcja-benchmark-kopia]]. Na naszym miksie agentowym (dużo kopii, lookup W16) zysk netto jest niepewny. (2) „Największe k, które się mieści” przy batchingu.
- **Enigma NVIDIA (3090):** qwen-warp to obecnie najmocniejszy publiczny punkt odniesienia dla 27B na 3090. Konkretnie: DFlash2 nie działa przy 262k na 24 GB (brak bufora pierścieniowego). Dla przepisu 262k zostaje MTP + lookup, czyli nasz układ. Do portu w `enigma-cuda-fork` nadają się:
  - (a) GEMV W4 z dwoma kaflami n8, który współdzieli zdekwantyzowany fragment między 16 wierszy (u nas odpowiednik to MMVQ multi-kolumnowe dla W16);
  - (b) jeden graf na cały cykl spekulacyjny bez pracy hosta, gdzie ich narzut serwera wynosi 2–6%;
  - (c) jedno przejście KV na grupę (KNOWN).

## 4. Testowalne pomysły

Model kosztu V(w, ctx) z `wiki/metody/koszt-szerokosci-weryfikacji.md`: na XTX V8 = 26.6 ms, V5 = 24.1 ms przy 2k, a krok serwerowy MTP4 to 29.6 ms.

| # | Pomysł | Oczekiwany zysk u nas | Test | Kryterium odrzucenia | Pobranie |
|---|---|---|---|---|---|
| Q1 | Referencja qwen-warp na wynajętym 3090 obok forka kvqlean, w tej samej sesji (ABBA, limit 340/350 W) | 0 dla produktu, ale kalibruje nasz zapas na 3090 (szacunek ×1.5–2 [INFERENCE]) | `serve.py --profile long --max-model-len 262144 --prompt-lookup 0` i fork; prompty z 67c (czat, mvs, kopia 64k, 190k); t/s i TTFT | Jeśli warp < 1.15× forka przy równym kontekście, zamykamy temat portu | Swift-1.5 INT4: 19.48 GB (na wynajętej maszynie, nie lokalnie) |
| Q2 | DFlash2 przy ≤ 64k na 3090 (warp `--drafter dflash2`), mierzone na naszym agentowym replayu | Ich dane: czat ×1.07–1.34, agent −31%. U nas przy lookupie W16 [INFERENCE]: −10…+10% | Ten sam replay agentowy co dla `spec_sweep`, zachłannie, z oboma drafterami | Jeśli replay agentowy nie przekracza +5% albo kopia 64k jest gorsza od MTP, zamykamy temat | DFlash2: 3.85 GB bf16 (HF `incoai/Qwen3.8-27B-DFlash2`), plus kwantyzacja W4A16 lokalnie na wynajmie |
| Q3 | DFlash2 na XTX (cost model): T=8 → V8 + drafter ~2.6 ms ≈ 29.2 ms/cykl przy 2k; τ 4.5 wobec naszego ~3.5 | Kod/matematyka do +25…30%, proza ~0, kopia na minusie. Bez routera netto nieznane [INFERENCE] | Tylko po pozytywnym Q2. Wymaga portu draftera do llama.cpp (duża praca); router „kopia → MTP+lookup” | Q2 negatywne lub Δ na replayu < +5% | jw. 3.85 GB |
| Q4 | 16-wierszowe przejście po wagach (dwa kafle n8) w MMVQ forka CUDA dla W16 | Na 3090 [INFERENCE]: koszt W16 bliżej W8 (+3 ms zamiast +6), czyli kilka % na mvs | microbench `test-backend-ops` MUL_MAT n=8/16 przed i po + spec_sweep | < +3% mvs na 3090 | nic |
| Q5 | `-np 4/5` + k zależne od B (`K_BY_B`) dla wariantu wielu użytkowników w Enigmie | Suma ×2.7–2.9 przy 4–8 klientach (ich dane); u nas `-np 4` z MTP się nie uruchamia (67c A13) | Najpierw naprawić start `-np 4` z MTP; potem C = 1/2/4/8 | suma przy C=4 < 1.5× C=1 | nic |

## 5. Ryzyka

- Wszystkie liczby qwen-warp to pojedyncze lub dwukrotne przebiegi jednego autora na jednej karcie 350 W z pulpitem. Pochodzą od dostawcy, nie od nas.
- DFlash2 jest tylko zachłanny (próbkowanie wraca do MTP), a nasz produkt działa przy T=1 i T=0. Przy T=1 zysk nieznany.
- Trasy DFlash2 i MTP mogą dawać różne ids przy remisach bf16. Sam drafter jest bezstratny względem własnej weryfikacji, ale zmiana szerokości weryfikacji zmienia bity, co jest KNOWN klasą zjawiska.
- `TF_QWEN_REQUEST_STARTS` w TensorFold zmienia odpowiedzi, więc to nie jest optymalizacja bezstratna.

## 6. Wiersze do ZRODLA

| Źródło | Wersja | Raport | Werdykt | Liczby | Do sprawdzenia |
|---|---|---|---|---|---|
| qwen-warp (tuan3w) | `689901c` v0.8.0 (11-07) | R69b | DFlash2 w grafie: ×1.34 czat, −31% agent/kopia; przy 262k się nie mieści; multiuser 441 t/s | 3090 350 W: 276.7 kod, 155 czat MTP | ring buffer draftera, router kopii |
| TensorFold (delta) | `abc39af1` v1.2.5+ (11-08) | R69b | gfx1100 dalej brak; HIP DFlash2 ładowany, nieużywany; DSpine-spine ±0.002 | gfx1151 27B 16 strumieni 51→75 t/s | gfx1100 / `--drafter` na HIP |
| HF incoai/Qwen3.8-27B-DFlash2 | 11-09 (API) | R69b | drafter używany przez warp/HyperQwen | 3.85 GB | port GGUF |

## Źródła

- https://github.com/tuan3w/qwen-warp: `docs/PERFORMANCE.md` §5–7 i :6,14-22; `docs/USAGE.md:200,255-338`; `docs/ARCHITECTURE.md`; `docs/IDEAS.md`; commity `a4f1e4f`, `c07d0e7`, `9825d74`.
- https://github.com/ashhart/TensorFold: `CHANGELOG.md:5-673` (Unreleased, 1.2.5, 1.2.4, 1.2.3); `docs/recipes/training-a-drafter.md:130`.
- https://huggingface.co/api/models/ukisai/Swift-1.5-Qwen3.8-27b-INT4 (19.48 GB); https://huggingface.co/api/models/incoai/Qwen3.8-27B-DFlash2 (3.85 GB).
- KB: `wiki/repo/qwen-warp.md`, `wiki/repo/tensorfold.md`, `wiki/ZRODLA.md:21,51,60,240-241`, `wiki/produkt/final-recipes-nvidia.md:23-28`, `product/research/67c-nvidia-backlog-testow.md:76-99`, `wiki/metody/koszt-szerokosci-weryfikacji.md`.
