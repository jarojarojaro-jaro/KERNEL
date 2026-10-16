---
typ: hub
tags: [lekcje, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Lekcje

**Lekcje z błędów i pułapek: co poszło źle, jak to rozpoznać, jak uniknąć.**

Lekcje procesowe (z korekt użytkownika) mają prefiks `proces-`.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (25)

- [[lekcja-oom-ub2048|-ub 2048 przy ctx 204800 kończy się OOM]] — Większy micro-batch daje +3% prefillu w llama-bench, ale serwer z kontekstem 204800 przekracza 24.5 GB VRAM przy pierwszym długim prompcie; zostajemy przy ub 512.
- [[lekcja-jeden-prompt|Benchmark z jednym promptem]] — „DFlash 120 t/s” zmierzono na 1 prompcie; na zestawie promptów wynik ≈ MTP. Zawsze 6 promptów × seedy.
- [[lekcja-bit-exact-attention|Bit-exact: ostatnia różnica to atencja]] — Test `llama-bx-diff` na 7900 XTX (2026-10-16): z przełącznikiem `LLAMA_SPEC_BITEXACT` warstwy 0–6 są identyczne bit w bit, a pierwsza różnica to wyjście atencji `kqv_out-3` (368 z 6144 liczb, o ~1·10⁻⁷).
- [[lekcja-brak-column-w-obrazie|Brak programu `column` w obrazie CUDA zatrzymał benchmark]] — Obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04` nie ma `column`; wywołanie w `bootstrap.sh` przy `set -e` zatrzymywało benchmarki na wynajętej karcie (2026-10-16).
- [[lekcja-bledny-roofline|Błędny roofline (bajty na token zamiast na przebieg)]] — „1075 GB/s, 112% peaku” wyszło z liczenia bajtów na token zamiast na przebieg modelu; poprawnie: bajty na przebieg × tokeny na krok.
- [[lekcja-commity-bez-pomiaru|Commity bez pomiaru (UNMEASURED)]] — Łatki 0066–0070 powstały z dopiskiem „UNMEASURED”, bo w czasie rundy nie było dostępu do GPU; zmierzono je później.
- [[lekcja-mtp-embd-state|Crash MTP po rebase: embd_state]] — Po rebase na v0.7.0 Qwen MTP ze słownikiem draftu przerywał serwer przy pierwszym żądaniu, bo upstream przeniósł stan ukryty MTP do `embd_state`, a dwa nasze wywołania git zmergował bez konfliktu na starym `set_embd`.
- [[determinizm-fma|Determinizm: kontrakcja FMA i świeży serwer]] — Bity zmieniają się z trzech powodów: kompilator łączy mnożenie z dodawaniem w FMA, weryfikacja batcha liczy inaczej niż N=1, a llama.cpp nie jest deterministyczny w obrębie jednego serwera.
- [[lekcja-build-cuda-0057-0070|Fork amd-opt nie budował się dla CUDA (0057, 0070)]] — `amd-opt` nie kompilował się dla CUDA: dwa błędy z łatek 0070 i 0057 psuły 25 jednostek kompilacji; naprawa w `cuda-compat` (4 commity), build 579/579 kroków w 835 s.
- [[lekcja-kolejnosc-akumulacji-fa|Kolejność akumulacji w FA zmienia KLD]] — Nowy kafel prefillu w Flash Attention zmienił kolejność akumulacji i dał KLD 0.0135; łatka 0043 przywróciła kolejność chunków K i KLD = 0.
- [[lekcja-losowe-spowolnienia|Losowe spowolnienia per proces]] — Gate+up w LFM trwał 24.3 albo 27.2 µs w 4 z 8 profili, także na buildzie bez zmian; A/B trzeba robić na wielu procesach, nie na jednym.
- [[lekcja-mikrobench-klamie|Mikrobench kłamie]] — Mikrobenchmark dał inną decyzję niż model (Q6_K z GLC|DLC); decyzje o kernelach podejmujemy tylko na rocprofv3 w pełnym modelu.
- [[lekcja-obciazenie-cpu|Obciążenie CPU psuje pomiar]] — Równoległe obciążenie CPU (np. kompilacja) zafałszowało pomiar `-bs`, który trzeba było powtórzyć; pomiary GPU robimy pod `quiet.lock` w osobnym oknie.
- [[lekcja-pdl-sm120|PDL na Blackwell: kernel musi czekać na poprzednika]] — Na sm_120 llama.cpp startuje kernele wcześniej (PDL); nowy kernel bez `ggml_cuda_pdl_sync` może czytać dane, zanim poprzedni skończy.
- [[pm4-niewidoczne-w-rocprof|rocprofv3 nie widzi dispatchy PM4]] — Po łatce 0060 kernele idą taśmą PM4 i rocprofv3 ich nie widzi; profilujemy z `GGML_HIP_PM4=0` albo przez `GGML_HIP_PM4_DEBUG=3`.
- [[lekcja-siatka-pelna-fala|Siatka równa pojemności fali daje bimodalne czasy]] — Siatka dokładnie 3072 bloków na 96 CU (pełna pojemność jednej fali) dawała per proces 13.6 albo 14.6 µs; 2560 bloków zawsze 12.2 µs.
- [[lekcja-spekulacja-zmienia-numeryke|Spekulacja zmienia numerykę batcha]] — MTP rozjeżdża się z plain po 129 znakach, DFlash po 229; zmiana draftu zmienia tekst przy remisie, więc MTP porównujemy z bazą MTP, nie z plain.
- [[lekcja-szum-t-s-przy-t1|Szum t/s przy T=1]] — Przy T=1 t/s zależy od wylosowanego tekstu bardziej niż od kernela; metryka to ms/krok, kilka seedów i przeplatanie.
- [[lekcja-slaby-cpu-3090|Słaby CPU na wynajętym RTX 3090]] — Agent wybrał najtańszą ofertę 3090 ($0.201/h) bez kryterium CPU i dostał Intel i7-4790 (4 rdzenie, 2014) z dyskiem 498 MB/s; mocniejsza oferta z 16 rdzeniami EPYC kosztowała ~$0.305/h.
- [[lekcja-ten-sam-serwer-pending-h|Ten sam serwer, inna odpowiedź (pending_h)]] — Ten sam greedy request bez cache dawał inny tekst przy 1. i 2. wywołaniu po starcie serwera (rozjazd po ~270 znakach); 2026-10-16 prawdopodobną przyczyną okazał się stan MTP `pending_h` nieczyszczony między zapytaniami.
- [[baco-runtime-suspend|Usypianie karty (BACO) wyrzuca model z VRAM]] — Bez aktywności amdgpu usypia kartę po 5 s (runtime PM/BACO) i przenosi VRAM do RAM; model działa wtedy przez PCIe: 4.4 zamiast 92 t/s.
- [[lekcja-vast-cli-klucz|vast CLI wymaga jawnego --api-key]] — `vastai show instances` po `source env.sh` w powłoce agenta zwrócił „Failed with error 403: This action requires login”; zadziałało dopiero `vastai --api-key "$(cat ~/.vast/key)" …` (2026-10-16).
- [[lekcja-wolna-sciezka-samplera|Wolna ścieżka samplera wyzwalana przez klienta]] — Ustawienia klienta (`reasoning_control` z web UI, budżet myślenia, `repeat_penalty` 1.05 w GGUF LFM, gramatyka narzędzi, `logit_bias`, `n_probs`) włączały pełną tablicę 128k/248k kandydatów: LFM 293 → ~255 t/s.
- [[lekcja-5060ti-bezczynna|Wynajęta 5060 Ti stała bezczynnie]] — Na 5060 Ti kompilacja skończyła się szybko, ale pomiary nie ruszyły, bo agent dopisywał skrypty; płatna karta stała z 0% GPU (2026-10-16 ok. 01:24 UTC).
- [[lekcja-zombie-serwery|Zombie serwery i współdzielony VRAM]] — DFlash wisiał na SIGTERM, a wynik MTP spadł do 5.6 t/s; serwer agenta K4 na porcie 8097 trzymał VRAM.
<!-- AUTO:END -->
