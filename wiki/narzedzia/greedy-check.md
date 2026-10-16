---
typ: narzedzie
tags: [narzedzia, poprawnosc, md5]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/fusion/greedy.sh:1-5; ~/KERNEL/qwen-opt/greedy_check.sh:1-9; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:228,244; ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:143-151
status: aktualne
---
# greedy.sh / greedy_check.sh — bramka md5

**Skrypty uruchamiają świeży serwer i zapisują tekst greedy (T=0) w trybie plain i MTP; md5 musi się zgadzać z bazą, żeby łatka była „bitowo identyczna”.**

- `tools/fusion/greedy.sh BIN_DIR LIB_DIR OUT_PREFIX [qwen|unc|lfm]` — aktualna wersja; `MODES` (domyślnie „plain mtp”, dla LFM „plain”), `KV` (q4_0, LFM q8_0), `PORT` (domyślnie 18433); uruchamiać pod `flock`.
- `greedy_check.sh` — starsza wersja z 2026-10-09 (Qwen, plain + MTP/DFlash, prompt o tablicy haszującej).
- Bazy po instalacji 2026-10-15: Qwen plain `c4708318…`, MTP `6f14e814…`, LFM `894e56e4…`.
- Towarzyszy jej hash logitów (`lh.sh` + `logit_hash.cpp`): FNV pełnych logitów 64 kroków przy głębokości 0 i 3000; dla prefillu `logits_hash` na 2048 tokenach.
- W harnessie chmurowym ten sam schemat porównuje base / fork / fork-safe na kartach NVIDIA.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[zgodnosc-bitowa-md5]]
- det-probe
- [[nvidia-wyniki-2026-10-16]]
- [[serializacja-gpu]]
