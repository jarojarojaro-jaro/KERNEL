# 50a. MMVQ Q4_K n=5: kernel strumieniowy (MmvqQ4K)

Gałąź `mmvq-q4k` (worktree `~/wt/mmvq-q4k`, baza `mmvq-big` 69f14108b), commit **130cd006c**. Zmiana tylko w `ggml/src/ggml-cuda/mmvq.cu`: nowy kernel `mul_mat_vec_q_stream` i hak w `mul_mat_vec_q_switch_fusion`.
- Przełącznik runtime: `GGML_HIP_MMVQ_Q4K_STREAM=1`, domyślnie wyłączony.
- Kompilacja: `MMVQ_R3_STREAM_Q4K=1`, domyślnie wkompilowany.
- Mikrobench: `~/qwen-opt/mmvq-q4k/` (`bench.hip`, `mk.sh`, `isa2.sh`, `r1..r5.jobs`). Logi: `~/qwen-opt/queue/logs/q4k{1..5}-*.log`.
- GPU: tylko kolejka, PM4=0 dla mikrobenchu, bez błędów amdgpu.

## Werdykt

- **Kernel strumieniowy Q4_K n=5: wygrana, bitowo zgodny na wszystkich kształtach produkcyjnych.**
  - Plain −3…−6%, pary (qkv+gate, ffn) −10…−21%, down+bias −15% względem 69f14108b.
  - Szacunek `[SZACUNEK]` z czasów trasy klab `now1`: **−0.28 ms/krok względem topki**, −0.29 ms względem 69f14108b (~1%).
- **69f14108b (pipe + 8 fal, raport 46) netto nic nie daje.** Raport 46 mierzył tylko launche plain, a pipelining pogarsza launche fused:
  - para qkv+gate +16% czasu, down+bias +19%, ffn para +6%, out+bias +7% względem topki;
  - netto +0.01 ms/krok `[SZACUNEK]`;
  - zgłoszone IntegTopka2.
- **Grupowanie wierszy na rezydentne fale (kernel „persistent”, siatka = liczba slotów): KILL.**
  - up 17408 +16%, qkvz +8% (dla nsm=48 i 16 fal/SM).
  - Sprzętowy dispatch bloków balansuje lepiej niż statyczny podział.
  - W kernelu zostaje pętla po grupach, launcher daje 1 grupę na falę.
- **Prefetch wag o 2 iteracje: KILL.** vmcnt jest w kolejności, więc czekanie na y czeka też na starszy prefetch. Wariant z y o 2 do przodu się spilluje (256 VGPR, scratch).
- **rpb 8, NI 2/8, fale 6/7/9/10/12 (stary kernel): KILL.** rpb 2 pomaga tylko launchom fused w starym kernelu: to objaw tego samego problemu z waitami.

## Przyczyna (ISA)

Pętla `use_pipeline` z 69f14108b czeka na swój prefetch na trzy sposoby:
1. Loady y idą po prefetchu wag, a vmcnt schodzi w kolejności wydania. Czekanie na y = czekanie na wagi następnej iteracji.
2. Kopia `w = wn` czeka na load, zanim pójdą następne loady. Widać to jako `vmcnt(0..7)` w latchu, głównie w instancjach fused/bias.
3. Fałszywe zależności:
   - `v_mad_u64_u32` do offsetu iteracji czyta nieużywany starszy rejestr, który bywa celem trwającego loadu;
   - ścieżki wyjścia z pętli łączą się z back edge, więc pass waitcnt dokłada `vmcnt(1)` na głowie pętli.

Kernel strumieniowy (ten sam mapping lane → blok/int, ta sama kolejność akumulacji, ten sam `mmvq_tsum`):
- y bieżącej (lub z YPF następnej) iteracji, potem `sched_barrier`, potem wagi następnej iteracji, potem `sched_barrier`, potem unpack+dot;
- dwa sloty wag (ping-pong, pętla rozwinięta ×2) i jednolita liczba iteracji, bez wyjścia w środku;
- offsety iteracji w `soffset` (SGPR, przez `readfirstlane`/asm), voffset niezmienny w pętli;
- bias ładowany raz przed wagami. W wersji per grupa LLVM przenosił go przez pętlę kopią, która czekała na wszystko;
- YPF (y o iterację do przodu): 234 VGPR, 6 fal. W pętli czeka tylko do `vmcnt(28)`, czyli y i wagi następnej iteracji są w locie podczas liczenia.

## Pasmo (mikrobench cache-cold, kopie > 640 MB, ABAB, mediana 7 rund, sufit 926 GB/s)

| kształt | GB/s topka → 69f14108b → stream | % sufitu (stream) | bitowo |
|---|---|---|---|
| up 17408×5120 | 663 → 779 → **800** | 86 | tak |
| qkv 10240×5120 | 694 → 715 → **757** | 82 | tak |
| para qkv+gate 10240+6144 ×5120 | 731 → 630 → **797** | 86 | tak |
| down+bias 5120×17408 | 794 → 669 → **787** | 85 | tak |
| q 12288×5120 | 719 → 752 → **772** | 83 | tak |
| para ffn 2×17408×5120 | 766 → 717 → **802** | 87 | tak |
| g 6144×5120 | 667 → 659 → **688** | 74 | tak |
| out+bias 5120×6144 | 675 → 631 → 622 | 67 | tak |
| qkvz 16384×5120 | 722 → 771 → **796** | 86 | tak |

- Kolumny: topka = `-DMMVQ_R3_PIPE_Q4K=0` (q4k1-nopipe), 69f14108b = baza benchu, stream = binarka końcowa (`q4k4-fin`, 9 rund; drugi przebieg `q4k4-fina` ±0.5%). Kontrola A/A ±0.6% (`q4k4-finoff`, `q4k1-same0`).
- Pozostałe typy (Q5_K, IQ4_XS, Q6_K) bez zmian: ±0.3%, bitowo tak.
- k/v 1024 (stary kernel) +1.7% w benchu z wkompilowanym streamem, w `finoff` −0.2%. `[INFERENCE]` To narzut hosta przy 8 µs launchach w benchu (bez grafów); w produkcji PM4/grafy go nie widzą.
- 1024-wierszowe k/v (256 bloków) zostają na starym kernelu (`MMVQ_R3_STREAM_MIN_BLOCKS=512`), bo to obszar MmvqBig3.

## Bramki

- Bitowa zgodność wyjścia na wszystkich kształtach: tak (FNV wyjść, każdy wariant, każda runda).
- Pierwszy smoke (f33a96476, PM4=0, przełącznik 1): plain c4708318 OK, **MTP 5272e0d3 ≠ 6f14e814**. Bramka i ABBA się nie uruchomiły (`q4k5-*`).
  - Przyczyna: hak w `switch_fusion` przekazywał `fusion` bez `pair_block0`, bo oryginał ustawia go dopiero później. W launchach par wszystkie bloki liczyły drugą macierz.
  - Mikrobench tego nie złapał: sam ustawia `pair_block0` i woła launcher bezpośrednio.
  - Poprawka: 130cd006c.
- Powtórka: smoke, md5 (Qwen c4708318 / 6f14e814, LFM 894e56e4) dla przełącznika 0 i 1, E0 ABBA prose+mvs (ta sama binarka, A=0, B=1) w `r6.jobs`. Wyniki: `~/qwen-opt/queue/logs/q4k6-*.log`, `~/qwen-opt/mmvq-q4k/logs/x50a2-*`. **STATUS: w kolejce w chwili pisania** (limit czasu agenta).
- Adopcja tylko po PASS `/tmp/p100-gate/mmvq50a2.PASS` i ABBA bez regresji.

## Następne kroki

- out+bias 5120×6144 (1 tensor, 0.02 ms) i down+bias: wariant z 2 wierszami na falę. W starym kernelu rpb 2 dawało down+bias 807 GB/s.
- Ten sam wzorzec dla Q5_K/Q6_K. MmvqIQ4XS doszedł do tego samego niezależnie (`mmvq_ring_step`, 862cdfbcc).
- Rozjazd bench vs trasa dla Q4_K plain 17408 (topka: bench 663, trasa 747 GB/s) jest niewyjaśniony. Wagę ma E0, nie szacunek.

## Do bazy wiedzy

- Na gfx1100 vmcnt schodzi w kolejności wydania. W pętli z prefetchem kolejność wydania jest częścią algorytmu: najpierw to, na co czekamy w tej iteracji, potem prefetch. Pilnuje tego `__builtin_amdgcn_sched_barrier(0)`.
- Każdy load przenoszony przez back edge pętli (kopia, phi z wyjścia pętli, `v_mad_u64_u32` ze śmieciowym hi) zamienia prefetch w `s_waitcnt vmcnt(N)` na głowie pętli lub w latchu. Trzeba sprawdzać waity w ISA pętli, nie tylko VGPR i occupancy.
- Launche fused (para, bias) to osobne instancje z innym schedulingiem. Wariant mierzony tylko na plain potrafi je spowolnić o 15–20% (69f14108b).
- Statyczne „persistent” rozłożenie wierszy na rezydentne fale przegrywa ze sprzętowym dispatchem dla MMVQ n=5. `multiProcessorCount` na XTX = 48 (WGP).
- Mikrobench bez `cpuheavy --quiet` przy kompilacji psuje cudze ABBA. `mk.sh` używa go teraz.
- Mikrobench, który woła własny launcher z ręcznie złożonymi argumentami fusion, nie testuje haka produkcyjnego. Pierwsza bramka to zawsze smoke MTP: n=5 w ogóle występuje tylko tam.
