---
typ: research
tags: [research, kwanty, kld]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/57g-quantalloc-ear.md:9-20
status: aktualne
---
# Raport 57g: EAR w llama-perplexity + alokacja per tensor dla 24 GB (research)

**EAR (Σmin(p,q) = 1 − TV) jest na gałęzi `kld-ear` (`cb9aefbbf`). Dotychczasowe wyjście KLD jest bajtowo identyczne (CPU, LFM 2.6B), a identyczne logity dają 99.9985 %. Alokacje tylko z szybkimi typami MMVQ: −1.0 GB daje +5.6 % t/s z bajtów (IQ4_XS) wobec +4.6 % UD-Q4_K_M. Jakość niezmierzona: brak BF16, zakaz pobierania, zasada „nie zmieniamy kwantów” (2026-10-21).**

- IQ4_XS 818 GB/s vs Q4_K 738 w profilu topki: przy tych samych bajtach IQ4_XS jest szybszy. Jakość (SLQ γ²) może iść odwrotnie.
- Przygotowane, nieuruchomione: `qa.jobs`, `buildA.sh` (`57g-skrypty/`).

## Powiązane
- [[research/_hub|research]]
- [[raport-57a-gsq-rco]]
- [[raport-16e-kwanty-kld]]
- [[kwanty-gguf]]
