# 68: Synteza — co jeszcze przyspieszy XTX w final mode (2026-11-07)

**Na decode GEMV jesteśmy na szczycie (81–88% pasma vs najlepsze publiczne 69–87%), żaden publiczny wynik 27B na XTX nie przebija naszych 120,8 / 118,3 t/s; realne rezerwy to atencja przy weryfikacji MTP przy długim kontekście (verify 2× wolniejszy od pojedynczego kafla), atencja prefillu przy głębokim kontekście, koszty hosta przy przełączaniu sesji agenta i dynamiczna głębokość draftu MTP.**

Raporty: [68a](68a-rdna3-kernele.md) (kernele RDNA3), [68b](68b-spekulacja-nowe.md) (spekulacja), [68c](68c-dlugi-kontekst-gdn.md) (długi kontekst / GDN), [68d](68d-swieze-od-spolecznosci.md) (świeże od społeczności). Wszystkie zyski poniżej to szacunki; status = stan w chwili pisania.

## Ranking (bezstratne)

| # | Pomysł | Źródła | Szacunek dla nas | Status |
|---|---|---|---|---|
| 1 | **Atencja weryfikacji MTP do czasu pojedynczego kafla** (`kvq` ONCE=1 → ONCE=2: K dekwantowane raz, para warpów) | 66, 68a, 68c | atencja przy 98k 318,8 → cel ~172 µs/warstwę; decode 196–255k sufit +12…16% | ONCE=1 zmierzone: bit-identyczne, FA przy 199k −6,1% (KILL jako cel kernela), e2e 94k +0,9%, 199k +1,8%; ONCE=2 zbudowane, **niezmierzone** (`eksperymenty/2026-11-08-kvq-once-profil`) |
| 2 | **Prefill FA D256 dla RDNA3** (#31746 + sweep 24v + V/K w układzie WMMA przy konwersji) | 68a #1, 68c #1, 68d #1 | fill 255k 465 → ~490–570 t/s (+5…22%) | kod gotowy (`fa-d256` 32292cc0a, `GGML_HIP_FA_D256_VAR`), **niezmierzony** (`eksperymenty/2026-11-08-fa-d256-prefill`) |
| 3 | **Huge pages dla `--cache-ram` + #30137 (bez zero-fill zapisu)** | 68c #3, 68d #3 | −2…5 s i −0,1…0,35 s na przełączenie wątku agenta | kod gotowy (`l1-cachesave` 3152b0bfa, `LLAMA_SERVER_CACHE_HUGE`), **niezbudowany i niezmierzony** (`eksperymenty/2026-11-08-cachesave-30137`) |
| 4 | **Cache tokenizacji + parser O(n)** | 66, XtxHostL1 | tokenizacja przy 90k+ 123–187 → 1,3–2,1 ms; parser CPU 36,1 → 0,98 s | GPU A→B (bez A2): tokenizacja 14,0 → 6,6 ms, tura −85 ms, md5 =, decode 0% (`eksperymenty/2026-11-08-l1-tokenizacja-parser`) |
| 5 | **Dynamiczna głębokość draftu MTP** (luka Gumbela, decyzja przed weryfikacją) | 68b #1 | +3,9% ogółem (czat PL +4,8%) | **czeka na decyzję użytkownika**: bramka „wymuszanie tokenów + KLD” zamiast md5 (68b #2) |
| 6 | Natywne q4_0 K/V w prefillu FA (#31802) | 68a #3, 68d #2 | −~1 GiB VRAM przy 262k, prefill ≥128k +1…3% | w zakresie XtxFaPrefill, jeśli tani |
| 7 | Pochodna maska KQ w kernelu (rdna-boosts) | 68c #2, 66 poz. 9 | decode 199–255k +0,5…1,5%, −256 MiB VRAM i pinned RAM | do zlecenia |
| 8 | GDN verify chunkwise/WY w fp32 | 68b #3 | +1,1…1,7% przy każdym ctx | bramka KLD; do zlecenia |
| 9 | Fuzja gate/up+GLU w MMQ dla RDNA3 (#29948) | 68a #2 | prefill ≤32k +2…4% | do zlecenia; ryzyko (wariant MoE był wolniejszy na RDNA3) |
| 10 | ~~Q6_K MMQ: skale jednym `int`~~ | 66 poz. 4 | **zmierzone 0,0%** (pp4096 1000,7 → 1000,6; md5 =) | **KILL**, `wiki/eksperymenty/2026-11-07-q6k-mmq-skale.md` |

Tanie sprawdzenia (bez zmian w kodzie): FCLK pod obciążeniem w eco trzyma 2000 MHz (porównać log stock vs eco — bez dotykania napięć), `amd-evicted-vram` w fdinfo przy 262k, licznik odczytów KV w `kvq` (rocprofv3).

## Stan po zakończeniu testów (2026-11-08 01:30, polecenie użytkownika)
Zmierzone: Q6_K (KILL), profil kroku, ONCE=1, podziały `kvq` (KILL), L1 (A→B bez A2). Gotowe, niezmierzone: ONCE=2 (`kvq-once2b.jobs`), FA D256 (`fa-d256.jobs`), cachesave (`cachesave.jobs`, wymaga buildu), okno draftu (`mtpw.jobs`, spodziewany KILL — przegrało 14.10), xtxbench (`validate.jobs`). Nic nie wdrożone.

2026-11-09: xtxbench zwalidowany — czas OK (A/A szum ≤0,15% decode, 3,9 min/wariant), md5 decode z migawek niewiarygodne (`wiki/metody/xtxbench-szybki-ab`). Profil (§ notatka kvq-once): stała część kroku 26,3 ms, FA = 100% nachylenia (0,66 / 5,70 / 11,32 ms przy 1,7k / 94k / 199k), FA draftu ~1,3 ms, maska KQ na hoście 355 µs przy 199k.

## Wyniki negatywne tej rundy
- Dobór podziałów `kvq` (blocks_per_sm, min. tokenów na podział): domyślne 2 bloki/SM optymalne, reszta +0…30% wolniej (XtxKvOnce).
- Drzewo draftów na sprzężonym łańcuchu: +1,6% przy dzisiejszym koszcie wiersza (68b).
- Globalny cache sufiksów: +0,1% tokenów (68b); format emisji AgSpec: nic do poprawy (68b).
- Ponowny trening głowicy MTP: niezależny retrening (rwmacy v8) — parytet na ruchu agentowym (68b).

## Odłożone (stratne)
Chunked GDN w f16 (#24561), `--cache-reuse-hybrid` (#29918, KL 0,008–0,82), SuffixReplay, Nucleus SD, 8-bit KV celu, QSA — szczegóły w 68b/68c §parked.

## Powiązane
- [63-SYNTEZA](63-SYNTEZA.md), [66-SYNTEZA](66-SYNTEZA.md)
- `wiki/eksperymenty/2026-11-06-final-mode.md`, `wiki/kernele/kv-raz-na-weryfikacje.md`
