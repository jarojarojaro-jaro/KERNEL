# 51. Małe kernele weryfikacji: rms_norm, FA kvq, GDN (XTX, Qwen3.8-27B)

Data: 2026-10-21. Agent SmallOps. Podstawa: ślad `~/qwen-opt/klab/traces/now1/off` (raport 47, rocprofv3, PM4=0,
104 kroki, 31.24 ms/krok). Zero zmian w topce, zero buildów llama. Mikrobenche w `~/qwen-opt/smallops/`
(`cold/` moje, `fa/` i `gdn/` od workerów DeepSeek `so-fa` / `so-gdn`, przejrzane przeze mnie).

## Werdykt

| pozycja | ms/krok | praca czy czekanie | dźwignia (sufit) | status |
|---|---|---|---|---|
| `rms_norm_mul_f32_unrolled<5>` (129.5×/krok, 5 wierszy) + 1 wiersz (20×) | 0.67 | **praca kernela**: 4.5–4.7 µs w każdym scenariuszu mikrobencha, także w pełni na ciepło | skrócenie ścieżki krytycznej kernela do ~2.3–2.8 µs (podłoga kernela 1×1024 wątków w tym samym benchu) → **≤0.26 ms/krok** | atrybucja faz w kolejce (r3) |
| `flash_attn_ext_kvq<256,8,q4_0>` (20×/krok) | 0.56 | **praca kernela**, ~18–20 µs stałego kosztu niezależnego od długości KV | epilog (łączenie warpów) = 59 % instrukcji, wykonywany szeregowo przez 1 z 8 warpów; wariant bitowo zgodny → szac. −3…−5 µs/launch = **0.06–0.10 ms/krok** | pomiar w kolejce (r2) |
| `gated_delta_net_cuda<128,f,f,l2_qk,lag>` (48×/krok) | 0.72 | praca: 14.7 µs vs podłoga bajtów 7.86 µs (53 % pasma) | łańcuch 10 wierszy z `ds_bpermute`+`lgkmcnt(0)`; warianty bitowe v1/v2 → szac. 0.3–1.2 µs/launch = **≤0.06 ms/krok** | pomiar w kolejce (r2) |

**Żadnego zwycięzcy do IntegTopka3 w tym oknie** (kolejka GPU: runda 1 czekała 63 min; rundy 2 i 3 nadal w kolejce
przy limicie czasu). Nic nie jest gotowe do bramki md5/E0.

## 1. rms_norm_mul_f32_unrolled: to jest praca, nie czekanie za MMVQ

Ślad (PM4=0): norma 5-wierszowa trwa 4.44–4.52 µs (mediana) po każdym typie dużego MMVQ; 3.68 µs (p10 2.44) po
`h2d_scatter`. Norma 1-wierszowa (draft): 5.8 µs po MMVQ, 2.32 µs po innej normie. Raporty 24u/37 czytały to jako
„karę za dużym MMVQ" (zimne wagi/TLB albo zegar).

Mikrobench `cold/cold.hip` (`#include "norm.cu"` z topki, ten sam kernel `<5>` co w libggml-hip; strumień 300 MB
> 96 MB Infinity Cache jako zastępca MMVQ; 130 wektorów wag co 2 MB jak w gguf; rocprofv3, 300 powtórzeń/scenariusz,
job `so-cold1`):

| scenariusz | co jest zimne | norma p10 / p50 / p90 µs |
|---|---|---|
| A strumień → norma | wszystko | 4.60 / 4.68 / 4.96 |
| B strumień → norma → **druga norma** | tylko wagi drugiej normy (kod, kernargi, x ciepłe) | 4.56 / 4.68 / 4.80 |
| C strumień → dotknięcie wag → norma | kod | 4.60 / 4.64 / 4.80 |
| D strumień **nontemporal** → norma | to co A, ale strumień nie powinien wypychać L2/MALL | 4.44 / 4.52 / 4.72 |
| E mały kernel → norma (bez strumienia) | nic | 4.44 / 4.48 / 4.56 |
| F strumień → dotknięcie x → norma | kod, wagi | 4.52 / 4.56 / 4.76 |

Wnioski:
- Zimne wagi, zimny kod (I$/L2) i „pierwszy kernel po strumieniu" nie tłumaczą czasu. **Norma 5-wierszowa kosztuje
  ~4.5 µs sama z siebie.** Nontemporal strumień daje −0.16 µs (3 %, na granicy szumu).
- Podłoga w tym samym benchu: `touch_k` (1 blok × 1024 wątki, odczyt 20 KB + redukcja) 2.28 µs, `small_k` (1×1024,
  zapis 100 KB) 2.80 µs. Norma jest więc **~2 µs nad podłogą** i to jest jej ścieżka krytyczna (ładowanie → DPP →
  LDS + bariera 32 fal → DPP → rsqrt → 5 grup q8_1 z dzieleniem IEEE (11× `v_div_*`) → zapisy).
- ISA `<5>` (produkcja): 915 instrukcji, 5.3 KB kodu, 38 VGPR, 189 `s_delay_alu`, 22 `v_div_scale`, 26 DPP,
  10 `s_waitcnt`, scratch 0. Ładowania x i w są już wystawione razem na początku (komentarz w kodzie się zgadza).
- Pomysł z zadania „połączyć kolejne normy z tym samym wejściem" nie ma zastosowania: normy unrolled to attn_norm/ffn_norm
  (wejście jednej zależy od wyniku poprzedniej warstwy), a normy Q/K (`rms_norm_mul_rope`) rozdziela MMVQ K/V
  (sekwencja w śladzie: Q-proj → rope_norm(Q) → K-proj → fwht → V-proj → rope_norm(K) → set_rows ×2 → FA).
- Sufit: (4.5 − ~2.4) µs × 130 ≈ **0.27 ms/krok** przy PM4=0. W PM4 norma i tak stoi na ścieżce krytycznej (raport 37:
  bez normy −0.68 ms ≈ bez granicy −0.73 ms), więc skrócenie jej latencji przechodzi 1:1. [INFERENCE]

Następny krok (zbudowany, w kolejce jako `smallops/r3.jobs`, job `so3-norm`): te same scenariusze A/E z wariantami
tylko do pomiaru: `NORMV_SKIP_Q8` (bez kopii q8_1), `NORMV_SKIP_RED` (bez redukcji blokowej), oba, oraz kontrola bez
przełączników (`cold/norm_v.cu`, binarki `cold_{nov,q8,red,both}`). To wskaże, czy celować w ogon q8_1 (dzielenia,
2×5 DPP na grupę), czy w barierę 1024 wątków. Bitowo zgodne kierunki: wspólne `1/d` liczone raz zamiast dzielenia
przez `d` nie jest bitowe; bitowe są: mniej fal (wirtualne warpy, ta sama kolejność DPP), DPP zamiast LDS w drugiej
redukcji jest już użyte.

## 2. FA kvq przy n=5: stały koszt to epilog

Geometria ze śladu: verify n=5 → siatka (2 kafle × nsplit 8–9 × 4 głowy KV) = 64–72 bloki po 256 wątków, 2 jednostki
(256 wierszy KV) na blok; draft n=1 → (1 × 16 × 4), 1 jednostka/blok. Mediany 27.1 µs (n=5) i 22.7 µs (n=1),
kontekst 1.8–2.3k. KV warstwy przy 2k ≈ 2.4 MB ≈ 2.6 µs przy 926 GB/s. Poprzednik zawsze `set_rows` (mały), więc to nie
czekanie za MMVQ. Czas nie rośnie z KV na tym zakresie → stały koszt ~18–20 µs/launch.

Analiza `so-fa` (przejrzana, ISA z libggml-hip i z kopii; liczby statyczne):
- kernel: 30.1 KB `.text`, 4610 instrukcji, 255 VGPR (5 fal/SIMD), 497 `s_waitcnt`, 11 `s_barrier`, 32 WMMA, scratch 0;
- **epilog (łączenie 8 warpów w LDS + zapis) = 16.9 KB / 2706 instrukcji = 59 %**; pętla KV 1305 instrukcji × 2
  iteracje; prolog 599;
- łączenie idzie w 8 fazach `if (warp == w) {128 f32 += w LDS}; __syncthreads()` — w każdej fazie aktywny 1 z 8 warpów,
  a blok ma cały CU dla siebie (64 bloki / 96 CU), więc latencja LDS jednego warpa jest w pełni odsłonięta.

Warianty (kopia `fa/fattn-kvq.cu`, parametr szablonu `VAR`, domyślnie kod produkcyjny; bez przełączników ISA wszystkich
5 instancji identyczna z oryginałem — sprawdzone przez workera):
- `VAR=1`: każdy warp zapisuje swoje częściowe wyniki w kawałkach po 64 D, jedna bariera, wszystkie 256 wątków
  sumuje warpy rosnąco → 18.7 KB, 2931 instrukcji;
- `VAR=2`: 1 + stałe softmaxu kolumny raz na blok zamiast 8× `exp2` + 16 odczytów LDS na (kolumna, d);
- oba **bitowo zgodne** (ta sama kolejność dodawania warpów; bench porównuje bajty `dst_tmp`+`dst_meta` z epilogiem
  produkcyjnym w tym samym procesie).

Ocena workera −3…−5 µs/launch (`VAR=1`) to model, nie pomiar. Pomiar: `smallops/r2.jobs` (`so2-fa-var1`, `so2-fa-var2`,
`so2-fa-skipepi`; kolumny us_base/us_var ciepło i zimno, n=1 i 5, ctx 2k/8k/32k, nsplit ×0.5…×4, `bitexact`).
Zmiana nsplit/kafli nie jest bitowa (kolejność łączenia) — nie ruszana. Zysk przy 20 launchach: 0.06–0.10 ms/krok.

## 3. GDN (kernel, nie bank)

Produkcja: `gated_delta_net_cuda<128, KDA=false, keep_rs=false, l2_qk=true, lag=true, 4>` (q/k normalizowane w
kernelu, bo n_tokens=5 < 32), siatka (48,1,8) × (32,4) = 384 bloki, 84 VGPR, 5.5 KB kodu, 1024 instrukcje.
- Model bajtów (`so-gdn`): 7.28 MB unikalnego ruchu/launch (stan 3.15 MB odczyt + 3.15 MB zapis + wiersze zaległe,
  q/k/v) = **7.86 µs** przy 926 GB/s; zmierzone 14.7 µs = 53 % pasma.
- Ścieżka: 10 wierszy szeregowo (5 powtórka + 5 nowych), 12 `ds_bpermute` + 12 `s_waitcnt lgkmcnt(0)` na wiersz
  (redukcje `warp_reduce_sum<8>` przez LDS-permute), ~2650 cykli/wiersz; q/k czytane 8× (raz na blok z osi z).
- Wcześniej (raport 41, `re-gdn-verify`): prefetch + DPP + stan b128 = −1.5 % kernela (−0.22 µs), neutralne e2e.
  Największy kawałek (powtórka 5 wierszy) to bank — u GdnBank3, nie ruszałem.
- Warianty bitowe (kopia `gdn/gated_delta_net.cu`): v1 8 warpów/blok (192 bloki, połowa duplikacji q/k), v2 DPP
  zamiast `ds_bpermute`, v3 stan z `slc dlc`, v12 = v1+v2. Szacunek 0.3–1.2 µs/launch → ≤0.06 ms/krok.
  Pomiar: job `so2-gdn` w `smallops/r2.jobs`.

## 4. Czy to czekanie/launch? Odpowiedź dla PM4

- PM4=0: między każdą parą dispatchy stoi luka 3.28 µs (p10 3.20, p90 3.5), **tak samo** po dużym MMVQ (32 034 luk) i po
  małym kernelu (44 199) → 945 dispatchy × 3.28 = 3.17 ms/krok luk. Czasy trwania kerneli w śladzie nie zawierają tej
  luki.
- PM4 usuwa koszt CPU launchu, ale nie granicę (bariera + rozruch następnego kernela): raport 37 zmierzył 2.3–4.0 µs na
  usuniętą granicę w taśmie PM4. Dla trzech pozycji z tego raportu czas w śladzie to praca kernela, a nie luka.
- W mikrobenchu luka po strumieniu 300 MB wynosi 7.7 µs vs 3.1 µs po małym kernelu (dłuższe zakończenie dużego
  dispatchu); w śladzie produkcji tego nie widać (3.28 vs 3.28) — artefakt benchu, bez wniosków.

## 5. Odrzucone / bez zastosowania

- Fuzja norm o wspólnym wejściu — brak takich par wśród unrolled (§1).
- Nontemporal strumień wag jako sposób na „karę po MMVQ" — w mikrobenchu −0.16 µs na normie; dodatkowo raport 23b:
  `slc|dlc` w MMVQ n=1 Q5_K pogorszył sam MMVQ (12.9 → 14.4 µs). Nie warto.
- Hipoteza zimnego kodu (I$/L2) dla normy — obalona (B i C jak A).

## Pliki

- `~/qwen-opt/smallops/cold/` — `cold.hip`, `mk.sh` (przez `cpuheavy`), `cold.py` (parser rocprof), `norm_v.cu`
  (kopia z przełącznikami tylko do pomiaru), `tr1/` (ślad rundy 1).
- `~/qwen-opt/smallops/fa/REPORT.md`, `gdn/REPORT.md` — pełne analizy workerów; `r1.jobs`, `r2.jobs`, `r3.jobs`.
- Logi kolejki: `~/qwen-opt/queue/logs/{so-cold1,so2-*,so3-norm}.log`.

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| wyniki | rms_norm_mul_f32_unrolled<5> to praca kernela, nie czekanie | Mikrobench (strumień 300 MB → norma, ta sama binarka kernela co topka): 4.5–4.7 µs na zimno, z ciepłymi wagami, z ciepłym kodem, po nontemporal strumieniu i bez strumienia. Podłoga kernela 1×1024 wątków w tym samym benchu 2.3–2.8 µs. Sufit skrócenia ≈ 0.27 ms/krok (raport 51 §1) |
| wyniki-negatywne | „Kara po dużym MMVQ" dla norm to nie zimne wagi ani zimny kod | Scenariusze B (druga norma, ciepły kod) i C (ciepłe wagi) = A (4.68/4.64/4.68 µs). Nontemporal strumień −0.16 µs. Hipotezy z 24u nieaktualne dla normy 5-wierszowej (raport 51 §1) |
| wyniki | FA kvq: stały koszt ~18–20 µs/launch to epilog | `flash_attn_ext_kvq<256,8,q4_0>`: 30 KB kodu, epilog łączenia warpów 59 % instrukcji, 8 faz z 1 aktywnym warpem na barierę. Wariant bitowy (`VAR=1/2`, kawałki po 64 D, jedna bariera) w `~/qwen-opt/smallops/fa` — niezmierzony w tym oknie (raport 51 §2) |
| metody | Luki między dispatchami w śladzie PM4=0 | 3.28 µs p50 niezależnie od poprzednika (po dużym MMVQ i po małym kernelu), 945 dispatchy/krok = 3.17 ms/krok; czasy kerneli w rocprofv3 ich nie zawierają (raport 51 §4) |
| metody | Mikrobench małego kernela z kodem topki | `#include "norm.cu"` (albo innego .cu) w benchu + link `-lggml-hip -lggml-base` z `~/llama-topka/bin`; flagi z `build-hip/.../flags.make`; scenariusze rozdzielone kernelem-znacznikiem `marker_k<S>` i parsowane z rocprofv3 (`smallops/cold/cold.py`) |
