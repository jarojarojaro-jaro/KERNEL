# Środowisko treningowe `~/qwen-opt/.venv-train` i dane `~/qwen-opt/mtp-train` — przepis na odtworzenie

Stan po odchudzeniu 2026-10-19: venv 17 → 6.3 GB, mtp-train 9.6+ → 8.5 GB (łącznie ~70 GB zwolnione tego dnia z całego dysku).

## Venv
- Python 3.12.14 (uv-managed, `uv venv --python 3.12 .venv-train`), uv 0.12.15.
- Dokładna lista pakietów: `venv-train.freeze.txt` (49 pozycji, przed odchudzeniem). Kluczowe: `torch==2.14.1+rocm7.14`, `triton-rocm==3.8.0`, `rocm==7.14.1`, `rocm-sdk-core`, `rocm-sdk-libraries`, `gguf==0.19.0`, `numpy==2.5.4`, `sentencepiece==0.2.2`.
- **Odchudzenie:** odinstalowane 24 pakiety `rocm-sdk-device-gfx*` dla innych kart (gfx90a/908/942/950, gfx10xx, gfx1101–1103, gfx115x, gfx120x, gfx1250); zostaje tylko `rocm-sdk-device-gfx1100` (RX 7900 XTX). Sprawdzone: `torch 2.14.1+rocm7.14`, matmul fp16 2048² na RX 7900 XTX działa.
- Odtworzenie: `uv pip install --python .venv-train/bin/python -r venv-train.freeze.txt` (indeks kół ROCm jak przy pierwszej instalacji), potem `uv pip uninstall` wszystkich `rocm-sdk-device-gfx*` poza gfx1100. Pobranie kilku GB przy ~1 MB/s ≈ 1–2 h.

## Dane `~/qwen-opt/mtp-train`
- `data/raw.tar.zst` (2.6 GB; było `data/raw/` 3.5 GB: WildChat-1M, oasst2, aya, self-oss-instruct): spakowane zstd -10, lista 66 plików sprawdzona 1:1 z archiwum. Rozpakowanie: `tar -I zstd -xf raw.tar.zst`.
- `data/ext_p1`, `data/ext_par` (1.2 GB): gotowe dane treningowe (wygenerowane na A40, $2.14) — zostają.
- `cache/*.f16.npy` (3.0 GB): osadzenia/głowica w f16 wyciągnięte z GGUF — zostają (decyzja użytkownika), odtwarzalne skryptami z `mtp-train/`.
- Usunięte: `smoke/qwen35-0.8b-hf` (1.7 GB, model do testu rozruchu; wynik w `mtp-train/RESULTS.md` §1).
- Wynik pilota: raport `product/research/11-mtp-pl-pilot.md`, notatka `wiki/eksperymenty/2026-10-16-mtp-pl-pilot.md`. Głowica `out/…mtpPL.mtp-head.gguf` (362 MB) zostaje; pełny plik odtwarza `writeback.py apply`.
