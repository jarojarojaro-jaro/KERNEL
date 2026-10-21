# 24a: bariera tylko-LDS na gfx1100 (`GGML_HIP_LDS_BARRIER`)

Data: 2026-10-19. Gałąź `lds-barrier` (`~/wt/ldsbar`), commity `949c4ecd2` + `94e4c92c8` (poprawka abortu), baza `eb7509cb9` topka. Build `~/wt/ldsbar/build-hip` (gfx1100, Release).

## Werdykt

**Nie rozstrzygnięty: brak pomiaru „on”.** Pierwszy job z kolejki (02-ldsbar-jobA, wersja `949c4ecd2`) przy `GGML_HIP_LDS_BARRIER=1` przerywał **każdy** proces na starcie: `hip_global.cpp:209 Cannot create GlobalVar Obj for symbol: _ZL25ggml_hip_lds_barrier_mask`. Zmierzone wyszły tylko ramiona „off”. Poprawka jest w `94e4c92c8`, zbudowana i sprawdzona statycznie, ale na GPU jeszcze nie uruchomiona. Domyślnie wyłączone, w produkcji nic się nie zmienia. **Do topki nie wchodzi**, dopóki nie przejdzie md5 i ABBA.

Przyczyna: `__attribute__((used))` na `static __constant__ int` sprawia, że clang zostawia zmienną wewnętrzną po stronie urządzenia (`internal addrspace(4) constant`, symbol `LOCAL`). Wynikają z tego dwa błędy:
- runtime HIP nie znajduje symbolu, więc `hipMemcpyToSymbol` kończy się abortem, a nie zwraca błędu (obsługa błędu w `upload` nie pomaga);
- odczyt maski zostaje zwinięty do wartości domyślnej 0.

Bez `used` referencja z funkcji hosta eksternalizuje zmienną: jest `externally_initialized`, symbol `GLOBAL`, a odczyt zostaje. Pierwsza próba naprawy z sesji 1, czyli `asm("" : "+s"(ptr))` na adresie, usuwała tylko drugi objaw i kosztowała odczyt przy każdej barierze. Teraz jest zbędna, więc ją usunąłem.

## Co jest w kodzie

- `ggml_cuda_lds_barrier<site>()` w `common.cuh`. Ścieżka LDS to `fence(release, workgroup, "local")` + `s_barrier` + `fence(acquire, workgroup, "local")`, a w ISA `s_waitcnt lgkmcnt(0); s_barrier` **bez `buffer_gl0_inv`**. Przy wyłączonym przełączniku zostaje stare `__syncthreads()`.
- Przełączniki: `GGML_HIP_LDS_BARRIER=1` włącza wszystkie miejsca, `GGML_HIP_LDS_BARRIER_MASK=<bity>` wybiera je pojedynczo: 1 kvq, 2 tile, 4 vec, 8 mmq, 16 mmvq, 32 mma, 64 misc (block_reduce, norm, softmax, fattn-common). Maska trafia przy inicjalizacji urządzenia do `__constant__` w każdej jednostce translacji. W logu pojawia się wtedy `LDS-only barrier site mask 0x..`.
- Maska jest czytana raz na kernel (`s_getpc` + `s_load_b32`, wyciągnięte przed pętle), a każda bariera ma dwa warianty wybierane skokiem skalarnym.
- Przegląd bezpieczeństwa: każda zamieniona bariera porządkuje wyłącznie LDS. Bariery sąsiadujące z `__threadfence`/`atomicAdd` (bilety q8 w mmvq, `ssm_conv` w mmvq:3477) zostały jako `__syncthreads()`. W mma nie ma `cp_async`, bo HIP go nie obsługuje.

## Liczby (zmierzone)

| Sprawdzenie | Wynik |
|---|---|
| Przerwany job 02-ldsbar-jobA (`949c4ecd2`), Qwen q4_0 KV, llama-bench `-r 2`: ramiona off A … A | pp4096 **1126.5 / 1124.8**, pp16384 **1073.1 / 1071.2** t/s (ramiona B = on: abort) |
| Rekord topki pp4096 dla porównania (REKORDY) | 1123.2 / 1115 → łatka przy „off” nie odstaje (bez ABBA względem topki) |
| `94e4c92c8`: symbol maski w 146 code objectach gfx1100 `libggml-hip.so` | **GLOBAL** w 146/146 (wcześniej LOCAL) |
| Rejestracja na hoście | 146 wywołań `__hipRegisterVar`, nazwa `_ZL25ggml_hip_lds_barrier_mask` w `.rodata` |
| ISA `94e4c92c8`, s_barrier bez `gl0_inv` / wszystkie: mmq | 90/180 (pętla K: 4 bariery na iterację, każda w dwóch wariantach), **1 odczyt maski na kernel** (15 kerneli, 15 odczytów) |
| fattn-tile / fattn-vec / fattn-kvq | 3076/6152 (250 kerneli), 200/400 (40), 61/122 (8) |
| Build | lokalnie `-j2` (rbuild: serwer nieosiągalny), OK |

## Nie zrobione (GPU wstrzymane)

- test-backend-ops MUL_MAT / FLASH_ATTN_EXT przy `GGML_HIP_LDS_BARRIER=1`.
- greedy md5 przy on i off: Qwen plain c4708318 / MTP 6f14e814, LFM 894e56e4.
- llama-bench pp4096 + pp16384 ABBA z ramieniem on, dla Qwen i LFM.
- spec_sweep, 5 seedów, ABBA, ms/krok.

Joby do kolejki GPU (format `name|timeout|cwd|command`; greedy na porcie 18434):
- `12-ldsbar-jobA|900|/tmp/ldsbar|bash /tmp/ldsbar/jobA.sh`: tbo, md5 Qwen on, ABBA Qwen.
- `13-ldsbar-jobB|900|/tmp/ldsbar|bash /tmp/ldsbar/jobB.sh`: md5 Qwen off, md5 LFM off/on, ABBA LFM.
- `14-ldsbar-sweep|1500|/tmp/ldsbar|bash /tmp/ldsbar/job3-sweep.sh`: spec_sweep 0 1 1 0.

Wyniki trafiają do `/tmp/ldsbar/out/`.

## Adopt / kill

- **Adopt: nie teraz.** Brak pomiaru. Kryteria przyjęcia: md5 identyczne przy on, test-backend-ops bez FAIL, pp4096 przy on co najmniej +1% w ABBA bez spadku ms/krok w spec_sweep, a „off” nie wolniejszy od `~/llama-topka`.
- **Kill:** jeśli pp4096 przy on mieści się w szumie (<1%), mimo że ISA potwierdza zniknięcie `gl0_inv`.
- Po wygranej warto rozważyć stałą kompilacji (`-DGGML_HIP_LDS_BARRIER_DEFAULT=127` + `if constexpr`). Narzut runtime jest już mały (1 odczyt skalarny na kernel), ale zostaje kod obu wariantów.

## Do bazy wiedzy

1. **`__attribute__((used))` na `static __constant__`/`__device__` w HIP psuje `hipMemcpyToSymbol`.** Zmienna zostaje wewnętrzna na urządzeniu (symbol `LOCAL`, odczyt zwinięty do inicjalizatora), a runtime robi abort: `hip_global.cpp:209 Cannot create GlobalVar Obj for symbol`. Bez `used` clang sam eksternalizuje zmienną używaną przez hosta: symbol `GLOBAL`, `externally_initialized`. Sprawdzenie: `llvm-readelf --syms` na code objectach z `.hip_fatbin` (kolumna Bind). Źródło: ten raport, `common.cuh:71-74`.
2. Bariera tylko-LDS w llama.cpp/HIP: ISA potwierdza, że na gfx1100 znika `buffer_gl0_inv` we wszystkich zamienionych miejscach (mmq 90/90). Wpływ na wydajność **niezmierzony**. Wiki `kernele/bariera-lds-rdna3.md` zostaje ze statusem `do-sprawdzenia`.
3. Code objecty z `libggml-hip.so` da się wyciągnąć bez `roc-obj`: sekcja `.hip_fatbin` → nagłówki `__CLANG_OFFLOAD_BUNDLE__` → wpisy `gfx1100` → `llvm-objdump -d --mcpu=gfx1100`. Spis barier dla 5 obiektów zajmuje około 1 s, a `hipcc -S` pojedynczej instancji mmq około 11 min.
