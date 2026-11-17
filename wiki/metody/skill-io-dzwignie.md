---
typ: metoda
tags: [metody, dzwignie, spekulacja, prefill, cache, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — references/levers.md:1-87, SKILL.md:112-140 (kolejność dźwigni, gdy dźwignia zawodzi); nasze liczby: [[REKORDY]], notatki eksperymentów w Powiązanych
status: aktualne
---
# Dźwignie wg skill-io (levers.md): każda z naszym statusem i spodziewanym zyskiem na XTX

**Ze 29 dźwigni stosujemy 19. Pięć nas nie dotyczy (MoE, torch, pamięć zunifikowana). Trzy odrzuca reguła „tylko bezstratnie”. Częściowo zrobione są dwie: długość draftu per kontekst (czeka na decyzję o bramce, K-008/K-046) i rozmiar chunku prefillu (K-048, K-106). Kolejność dźwigni z SKILL.md (`:112-133`): cache JIT → grafy → spekulacja → współbieżność i KV → prefill → wątki i kafle → praca nad kernelem.**

| dźwignia (levers.md) | ich dowód | u nas | spodziewane na XTX |
|---|---|---|---|
| cache JIT/kompilacji (`:12`) | start 113 → 43 s | tak: kernele HIP AOT; cache requantu MTP 39,8 → 6,5 s | 0 (start 6,1 s) |
| mmap wolny (`:15`), 1 worker kompilacji (`:16`) | 26 min → s | n/d (llama.cpp, bez torch) | 0 |
| TTFT krótki = harmonogram + 1 przebieg (`:17`) | – | tak: K-003, szablon 0,8 ms, tokenizacja 0,3 ms, reszta to checkpointy GDN | ~0,1 s/żądanie (koszt checkpointów) |
| grafy dekodu (`:21-24`) | 14,4 → 28,4 t/s | tak: taśma PM4 + grafy HIP; PM4 +6,4% przy 1,7k ([[pm4-replay]]) | wykorzystane |
| przycięta głowica draftu (`:26-28`) | +27% (512/1940 bloków) | tak: słownik 64k IQ4_XS | wykorzystane |
| długość draftu per współbieżność/kontekst (`:29-32`) | B390 128k: 1 draft 29,6 vs 3: 15,5 | częściowo: n=4 stałe; DRAFT_N=3 proza +4,3%; dynamiczna +3,9% | +3,9…4,8% (K-008, decyzja właściciela) |
| akceptacja per głębokość (`:33`) | 14% na głęb. 2 | zmierzone: PL 0,64 / 0,46 / 0,35 / 0,30 | – |
| spekulacja może przegrać (`:34-36`) | M4 6,35 → 3,25 | u nas zawsze wygrywa (plain 43 vs 120 t/s); lookup neutralny (K-002) | 0 |
| weryfikacja atencją typu dekod (`:37`) | 75,7 → 82,6 t/s | tak: `kvq` ([[fattn-kvq]]) | nowy układ +1,5…3% przy ≥ 94k (K-012) |
| próbkowanie na GPU (`:38`) | +10% c1 | tak: `LLAMA_GPU_VERIFY=1`; NVIDIA fork T=1 traci 7–13% | Enigma NVIDIA (K-004) |
| mniej bajtów na wagę (`:39`) | AWQ-INT4 > FP8 na Ampere | **odrzucone**: zakaz zmiany kwantu | – |
| wątki/split-K per karta (`:40-42`) | 48,5 → 56,9 | tak: sweep wariantów FA (83), MMQ w kolejce (K-009) | prefill +2…4% |
| fuzja pod grafami nic nie daje (`:43`) | 3 × 0% | potwierdzone u nas (LaunchCut, x54 → K-092) | 0 |
| typ KV (`:44-46`) | q8_0 45,4 → 27,0 t/s przy 16 z 64 warstw KV | KV q4_0 + `kvq` szybkie; FA83 na f16 −2,4% | – |
| sloty stanu hybrydy (`:50-52`) | 1 → N żądań | `-np 2` na XTX odrzucone; NVIDIA `-np 4` + MTP nie startuje (K-061) | n/d (1 użytkownik) |
| pula KV N × ctx + soak (`:53`) | 4 × 256K | 1 × 262 144, soak S6 1205 żądań | – |
| cache prefiksów jawnie, `cached_tokens` > 0 (`:54-56`) | TTFT 36 → 0,45 s | tak: cache-ram 40960, CACHE_SHARE_MIN, cachesave; tura 13,4 → 12,0 s | wykorzystane; dalej K-006 |
| pamięć poza alokatorem (`:57`) | OOM | tak: lean reserve 1,07 → 0,08 GiB | – |
| zapas ≥ 1,5 GB (`:58`) | livelock | **ryzyko**: szczyt 23 398 z 24 560 MiB, czyli ~1,1 GiB zapasu | – |
| chunk prefillu vs blokada dekodu (`:62-64`) | stall 7,1 → 1,95 s za −4% | ub 512; wpływ na drugi wątek niezmierzony | K-106 |
| szybsza biblioteka atencji (`:65-67`) | +7…18% | tak: FA D256 wariant 83, +5,8% przy 128k | wykorzystane |
| int8/fp8 prefill (`:68`) | 1,89×, NLL +0,17% | **odrzucone** (stratne) | – |
| MoE: progi paddingu (`:69-72`) | +7…22% | n/d (gęsty 27B) | – |
| profil po etapach (`:73`) | GEMM 40% już na sufitcie | tak: 24v (FA 53% fillu 255k), MMQ 63–81% prefillu | – |
| test bitowy per M (`:77-79`) | „−4%” kernel dawał złe wyniki | tak: `test-backend-ops` + md5 | – |
| czytać ISA (`:80`) | LM head 4,05 → 1,72 ms | tak: `isa.sh`, FA83 spill 220 VGPR → 0 | – |
| płoty pamięci na nowych GPU (`:81`) | Xe3 | n/d | – |
| odrzucone na Xe: prefetch, LUT, async (`:82-87`) | 0 / gorzej | u nas też KILL: PM4-PDL, prefetch L2 MMVQ | – |

**Reguła „gdy dźwignia zawodzi”** (SKILL.md `:136-140`):
- Fuzja nic nie daje pod grafami → czas siedzi w głównych kernelach.
- Wyższa akceptacja nie daje t/s → draft kosztuje za dużo; mierzyć czas kroku.
- Dziwny wynik → najpierw podejrzewać pomiar.

U nas to samo wychodzi z sufitów: luka 26,9 vs 19,2 ms/krok leży w kernelach i drafcie, nie w akceptacji (K-111).

## Powiązane
- [[skill-io-przeglad]]
- [[skill-io-sufity]]
- [[KOLEJKA-TESTOW]]
- [[2026-11-08-fa-d256-prefill]]
- [[2026-11-14-k002-k003-k013-xtx]]
