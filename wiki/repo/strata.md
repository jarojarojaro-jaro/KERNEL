---
typ: repo
tags: [repo, spekulacja, moe, metodologia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/research/strata/README.md:1-34,194; ~/KERNEL/qwen-opt/research/strata/issues.md:1-20; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:82; ~/KERNEL/product/research/21d-kv-na-dysku.md:76-88
status: aktualne
---
# Strata (Niko1221/Strata)

**Silnik C++/CUDA/HIP pod jeden model MoE z offloadem (HEAD `a0116b27`, 2026-10-12, tag v0.1.43.1), studiowany jako wzór metodologii autora.**

Repo: 1892 commity w 19 dni, 49 tagów. Model docelowy: Qwen3.8-Flash-Next (125B MoE, ok. 6B aktywnych, 48 warstw: 36 GDN + 12 sparse attention, 512 ekspertów top-10, tablica n-gram 28.8 GB, głowica MTP). Otwarty PR #2231: bitowo identyczne poprawki decode na RX 7900 XTX, +11.7% chat / +14.3% agent decode, KL 0.0000. Standard autora: zmiana domyślnej ścieżki musi dać bajtowo identyczne wyjście na czterech modelach i przejść A/B prędkości; wszystko, co zmienia bity, jest opt-in. Dla nas: chunked GDN (WY) dał −39% na gfx1100 (#888, odrzucone) oraz odkrycie, że warstwa MTP w UD-Q4_K_XL jest cała w Q6_K (≈ 335 MiB). Raporty cząstkowe: `timeline`, `kernels`, `spec-host`, `prefill`, `method`, `issues`, `update-v0.1.44`.

Session files (v0.1.45, 21d): tmp + fsync + rename, fingerprint modelu i konfiguracji, O_DIRECT, tylko najgłębszy checkpoint; „0.2.0” nie istnieje ([[raport-21d-kv-na-dysku]]).

## Powiązane
- [[repo/_hub|repo]]
- [[tensorfold]]
- [[lucebox]]
- [[zgodnosc-bitowa-md5]]
- [[wylacznik-w-kazdej-latce]]
