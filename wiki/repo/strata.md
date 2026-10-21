---
typ: repo
tags: [repo, spekulacja, moe, metodologia]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/qwen-opt/research/strata/README.md:1-34,194; ~/KERNEL/qwen-opt/research/strata/issues.md:1-20; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:82; ~/KERNEL/product/research/21d-kv-na-dysku.md:76-88; ~/KERNEL/product/research/21g-nowe-silniki.md:218-272,291-297; ~/KERNEL/product/research/21n-strata-020-gyro.md:7-10
status: aktualne
---
# Strata (Niko1221/Strata)

**Silnik C++/CUDA/HIP pod jeden model MoE z offloadem (HEAD `a0116b27`, 2026-10-12, tag v0.1.43.1), studiowany jako wzór metodologii autora.**

Repo: 1892 commity w 19 dni, 49 tagów. Model docelowy: Qwen3.8-Flash-Next (125B MoE, ok. 6B aktywnych, 48 warstw: 36 GDN + 12 sparse attention, 512 ekspertów top-10, tablica n-gram 28.8 GB, głowica MTP). Otwarty PR #2231: bitowo identyczne poprawki decode na RX 7900 XTX, +11.7% chat / +14.3% agent decode, KL 0.0000. Standard autora: zmiana domyślnej ścieżki musi dać bajtowo identyczne wyjście na czterech modelach i przejść A/B prędkości; wszystko, co zmienia bity, jest opt-in. Dla nas: chunked GDN (WY) dał −39% na gfx1100 (#888, odrzucone) oraz odkrycie, że warstwa MTP w UD-Q4_K_XL jest cała w Q6_K (≈ 335 MiB). Raporty cząstkowe: `timeline`, `kernels`, `spec-host`, `prefill`, `method`, `issues`, `update-v0.1.44`.

Session files (v0.1.45, 21d): tmp + fsync + rename, fingerprint modelu i konfiguracji, O_DIRECT, tylko najgłębszy checkpoint; „0.2.0” nie istnieje ([[raport-21d-kv-na-dysku]]).

v0.1.44.1–0.1.45 (21g, 2026-10-19): ścieżka Qwen3.6-35B-A3B, dekod R9700 83.2 → 117.8 t/s (llama.cpp 82), bitowo; fuzje = nasze 0049/0051/0053/0056; `--parallel` vs `llama-server -np` ×1.14 / 1.61 / 1.53 / 1.56 dla N = 1 / 2 / 4 / 8; domyślny chunk 4096 zmienia bity (KL 0.004); Flash-Next 125B na XTX + 96 GB RAM ≈ 80 t/s, prefill 1810 t/s przy 98K (#2938); PR #3064 [[bariera-lds-rdna3]].

0.2.0-beta (`3d1fb480`, 21n): 55% zmian to aplikacja, silnik 6%; dla gfx1100 nic nowego; Gyro-S to plik dla 32 GB ([[raport-21n-strata-gyro]]).

0.2.1–0.2.2 (`011c9e60`, 10-21, silnik 0.1.47; R57b): Gyro na Arc/Mac, trellis NVIDIA +17% (3060) / P100 +30%, pula CPU per NUMA, role kart Main/Helper/Off; silnik ~11% zmian od 0.2.0-beta, dla gfx1100 nic do prędkości. Lekcja `86d10ed8`: flaga hosta podnoszona po `graphLaunch` = deadlock na HIP (8/41 → 0/46). Domyślne wagi = ISTA-DASLab GSQ-RCO GGUF. XTX (społeczność): IQ3_S 62.3 t/s, prefill 128K 926 → 1687 z tabelą hipBLASLt. „Qwen3.8-Flash” = hostowane API, lokalnie tylko Flash-Next ([R57b](../../product/research/57b-strata-qwen38-flash.md)).

## Powiązane
- [[repo/_hub|repo]]
- [[tensorfold]]
- [[lucebox]]
- [[zgodnosc-bitowa-md5]]
- [[wylacznik-w-kazdej-latce]]
