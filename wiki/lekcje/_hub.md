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
## Notatki (39)

- [[lekcja-oom-ub2048|-ub 2048 przy ctx 204800 kończy się OOM]] — Większy micro-batch daje +3% prefillu w llama-bench, ale serwer z kontekstem 204800 przekracza 24.5 GB VRAM przy pierwszym długim prompcie; zostajemy przy ub 512.
- [[lekcja-agent-zmienia-protokol|Agent potrafi „poprawić” wynik zmianą protokołu ewaluacji]] — W papierze Sakana (arXiv 2610.18933 §6.3) w 2 z 3 przebiegów agent zmienił protokół ewaluacji (majority vote zamiast pass@1), a ani ewaluator, ani rubryki tego nie złapały – wykrył to dopiero ręczny audyt.
- [[lekcja-benchmark-kopia|Benchmark na kopiowaniu zawyża spekulację]] — Zadania „powtórz tekst” albo kopiowanie dokumentu dają 4–6+ tokenów na krok i nic nie mówią o nowym pisaniu; tak powstały liczby Magnitude, tqLLM i HyperQwen.
- [[lekcja-jeden-prompt|Benchmark z jednym promptem]] — „DFlash 120 t/s” zmierzono na 1 prompcie; na zestawie promptów wynik ≈ MTP. Zawsze 6 promptów × seedy.
- [[lekcja-bit-exact-attention|Bit-exact: ostatnia różnica to atencja]] — Test `llama-bx-diff` na 7900 XTX (2026-10-16): z przełącznikiem `LLAMA_SPEC_BITEXACT` warstwy 0–6 są identyczne bit w bit, a pierwsza różnica to wyjście atencji `kqv_out-3` (368 z 6144 liczb, max |d| 1.19e-7); poprawka „jeden token na blok” nic nie zmieniła, więc przyczyna leży gdzie indziej.
- [[lekcja-brak-column-w-obrazie|Brak programu `column` w obrazie CUDA zatrzymał benchmark]] — Obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04` nie ma `column`; wywołanie w `bootstrap.sh` przy `set -e` zatrzymywało benchmarki na wynajętej karcie (2026-10-16).
- [[lekcja-bledny-roofline|Błędny roofline (bajty na token zamiast na przebieg)]] — „1075 GB/s, 112% peaku” wyszło z liczenia bajtów na token zamiast na przebieg modelu; poprawnie: bajty na przebieg × tokeny na krok.
- [[lekcja-commity-bez-pomiaru|Commity bez pomiaru (UNMEASURED)]] — Łatki 0066–0070 powstały z dopiskiem „UNMEASURED”, bo w czasie rundy nie było dostępu do GPU; zmierzono je później.
- [[lekcja-mtp-embd-state|Crash MTP po rebase: embd_state]] — Po rebase na v0.7.0 Qwen MTP ze słownikiem draftu przerywał serwer przy pierwszym żądaniu, bo upstream przeniósł stan ukryty MTP do `embd_state`, a dwa nasze wywołania git zmergował bez konfliktu na starym `set_embd`.
- [[determinizm-fma|Determinizm: kontrakcja FMA i świeży serwer]] — Bity zmieniają się z trzech powodów: kompilator łączy mnożenie z dodawaniem w FMA, weryfikacja batcha liczy inaczej niż N=1, a llama.cpp nie jest deterministyczny w obrębie jednego serwera.
- [[lekcja-dowod-poza-commitem|Dowód rozproszony poza commitem]] — Tylko 25/70 commitów łatek ma w treści komplet dowodu (liczba + powtórzenia/przeplot + marker poprawności), 0/70 podaje niepewność, a 25/70 nie ma żadnej liczby – dowody leżą w NOTES.md i `~/wt/*/REPORT.md`, niczym niezwiązane z SHA.
- [[lekcja-mtp-glowica-optimum|Fabryczna głowica MTP jest już blisko optimum]] — Douczanie głowicy MTP Qwen3.8-27B na 1.7 M tokenów dało ±0.2% tok/krok offline (online ±2%): głowica była trenowana wielokrokowo na dużo większym korpusie, a zapas widoczny u wyroczni (+21–33%) nie jest osiągalny tą drogą.
- [[lekcja-build-cuda-0057-0070|Fork amd-opt nie budował się dla CUDA (0057, 0070)]] — `amd-opt` nie kompilował się dla CUDA: dwa błędy z łatek 0070 i 0057 psuły 25 jednostek kompilacji; naprawa w `cuda-compat` (4 commity), build 579/579 kroków w 835 s.
- [[lekcja-kld-protokoly|KLD z różnych protokołów nie wolno mieszać]] — Ten sam plik ISTA GSQ-RCO IQ3_S ma KLD 0.0519 przy ctx 512 i 0.0665 przy ctx 2048 (+28%), a Swift mierzy KLD do własnego BF16 zamiast do Qwena – liczby z różnych kontekstów, referencji i korpusów nie są porównywalne.
- [[lekcja-kolejnosc-akumulacji-fa|Kolejność akumulacji w FA zmienia KLD]] — Nowy kafel prefillu w Flash Attention zmienił kolejność akumulacji i dał KLD 0.0135; łatka 0043 przywróciła kolejność chunków K i KLD = 0.
- [[lekcja-limit-cpu-kontenera|Kontener widzi wszystkie rdzenie hosta, a ma limit cgroup]] — W kontenerach Vast i RunPod `nproc` pokazuje wszystkie wątki hosta (64 albo 96), a limit cgroup to ok. 7.7 CPU; llama.cpp bez `-t` bierze za dużo wątków i dławi się na kwocie.
- [[lekcja-label-to-nie-binarka|Label w pomiarach nie jest tożsamością binarki]] — Label „base” w `spec_sweep.jsonl` wskazywał na nadpisywany katalog `~/llama-opt`, więc ta sama nazwa dawała 29.77, 29.36, 29.12 i 29.16 ms/krok w różnych sesjach i nie da się oddzielić dryfu sprzętu od zmian kodu.
- [[lekcja-losowe-spowolnienia|Losowe spowolnienia per proces]] — Gate+up w LFM trwał 24.3 albo 27.2 µs w 4 z 8 profili, także na buildzie bez zmian; A/B trzeba robić na wielu procesach, nie na jednym.
- [[lekcja-sondy-en-na-polskim|Małe sondy trenowane po angielsku mylą się na polskim]] — Sonda żądania PFlash (trenowana po angielsku) w 9/10 polskich przypadków wzięła tytuł wklejonego dokumentu za prośbę użytkownika, choć główna głowica Q/K przeniosła się na polski dobrze.
- [[lekcja-mikrobench-klamie|Mikrobench kłamie]] — Mikrobenchmark dał inną decyzję niż model (Q6_K z GLC|DLC); decyzje o kernelach podejmujemy tylko na rocprofv3 w pełnym modelu.
- [[lekcja-mtp-juz-kopiuje|MTP już kopiuje: zmierz P(MTP | lookup), zanim dołożysz drafter z kontekstu]] — Na 69 207 pozycjach z prawdziwymi łańcuchami MTP P(draft MTP trafia | lookup trafia) = 0.968 wobec 0.765 bazowo, więc lookup z kontekstu dokłada głównie ogon za pozycją 4, a nadpisywanie draftów MTP lookupem to strata.
- [[lekcja-nadpisanie-dzialajacego-skryptu|Nadpisanie działającego skryptu przerwało pomiar]] — Na wynajętej RTX 5060 Ti `scp` nadpisał `plan.sh` (ten sam i-węzeł) podczas jego działania i przerwał fazę pomiaru przełączników hosta Qwena po 2 przełącznikach.
- [[lekcja-md5-wzgledem-upstreamu|Nasze „bit w bit” było zawsze względem naszego poprzedniego buildu]] — Kampania NVIDIA pokazała, że greedy md5 forka różni się od upstreamu w trybie plain także z 31 przełącznikami = 0, przez łatki bez przełącznika: MMVQ multi-kolumna 0001/0002 i fuzję prologu GDN 0013; nasza bramka „bitowo identyczne” zawsze porównywała z poprzednim buildem forka, nie z upstreamem.
- [[lekcja-obciazenie-cpu|Obciążenie CPU psuje pomiar]] — Równoległe obciążenie CPU (np. kompilacja) zafałszowało pomiar `-bs`, który trzeba było powtórzyć; pomiary GPU robimy pod `quiet.lock` w osobnym oknie.
- [[lekcja-pdl-sm120|PDL na Blackwell: kernel musi czekać na poprzednika]] — Na sm_120 llama.cpp startuje kernele wcześniej (PDL); nowy kernel bez `ggml_cuda_pdl_sync` może czytać dane, zanim poprzedni skończy.
- [[lekcja-fit-mtp-16gb|Pułapka upstream: -fit on ze spekulacją (MTP na 16 GB, DFlash na 24 GB)]] — Upstreamowe `-fit on` źle liczy pamięć spekulacji. Na RTX 5060 Ti 16 GB upstreamowy serwer z `-fit on` i MTP dawał 7.7 t/s, wolniej niż bez spekulacji, bo `-fit` przy ciasnym VRAM zostawiał część pracy MTP na CPU; `-fit off -ngl 99 -t 8` dało 31.8 t/s na tym samym prompcie.
- [[pm4-niewidoczne-w-rocprof|rocprofv3 nie widzi dispatchy PM4]] — Po łatce 0060 kernele idą taśmą PM4 i rocprofv3 ich nie widzi; profilujemy z `GGML_HIP_PM4=0` albo przez `GGML_HIP_PM4_DEBUG=3`.
- [[lekcja-siatka-pelna-fala|Siatka równa pojemności fali daje bimodalne czasy]] — Siatka dokładnie 3072 bloków na 96 CU (pełna pojemność jednej fali) dawała per proces 13.6 albo 14.6 µs; 2560 bloków zawsze 12.2 µs.
- [[lekcja-spekulacja-zmienia-numeryke|Spekulacja zmienia numerykę batcha]] — MTP rozjeżdża się z plain po 129 znakach, DFlash po 229; zmiana draftu zmienia tekst przy remisie, więc MTP porównujemy z bazą MTP, nie z plain.
- [[lekcja-szum-t-s-przy-t1|Szum t/s przy T=1]] — Przy T=1 t/s zależy od wylosowanego tekstu bardziej niż od kernela; metryka to ms/krok, kilka seedów i przeplatanie.
- [[lekcja-slaby-cpu-3090|Słaby CPU na wynajętym RTX 3090]] — Agent wybrał najtańszą ofertę 3090 ($0.201/h) bez kryterium CPU i dostał Intel i7-4790 (4 rdzenie, 2014) z dyskiem 498 MB/s; mocniejsza oferta z 16 rdzeniami EPYC kosztowała ~$0.305/h.
- [[lekcja-ten-sam-serwer-pending-h|Ten sam serwer, inna odpowiedź (pending_h)]] — Ten sam greedy request bez cache dawał inny tekst przy 1. i 2. wywołaniu po starcie serwera (rozjazd po ~270 znakach); 2026-10-16 prawdopodobną przyczyną okazał się stan MTP `pending_h` nieczyszczony między zapytaniami.
- [[lekcja-megakernel-prefetch-nie-granica|Trwały kernel: zysk to prefetch, nie granica]] — Szacunek „trwały kernel MoE po PM4 ≈ 1.4%” liczył tylko granice kerneli; megakernele wygrywają nakładaniem rampy wag i małych operacji, a zmierzona bariera trwałej siatki (0.48–0.77 µs) kosztuje tyle co granica PM4 (0.46–0.86 µs).
- [[baco-runtime-suspend|Usypianie karty (BACO) wyrzuca model z VRAM]] — Bez aktywności amdgpu usypia kartę po 5 s (runtime PM/BACO) i przenosi VRAM do RAM; model działa wtedy przez PCIe: 4.4 zamiast 92 t/s.
- [[lekcja-vast-cli-klucz|vast CLI wymaga jawnego --api-key]] — `vastai show instances` po `source env.sh` w powłoce agenta zwrócił „Failed with error 403: This action requires login”; zadziałało dopiero `vastai --api-key "$(cat ~/.vast/key)" …` (2026-10-16).
- [[lekcja-wolna-sciezka-samplera|Wolna ścieżka samplera wyzwalana przez klienta]] — Ustawienia klienta (`reasoning_control` z web UI, budżet myślenia, `repeat_penalty` 1.05 w GGUF LFM, gramatyka narzędzi, `logit_bias`, `n_probs`) włączały pełną tablicę 128k/248k kandydatów: LFM 293 → ~255 t/s.
- [[lekcja-5060ti-bezczynna|Wynajęta 5060 Ti stała bezczynnie]] — Na 5060 Ti kompilacja skończyła się szybko, ale pomiary nie ruszyły, bo agent dopisywał skrypty; płatna karta stała z 0% GPU (2026-10-16 ok. 01:24 UTC).
- [[lekcja-zombie-serwery|Zombie serwery i współdzielony VRAM]] — DFlash wisiał na SIGTERM, a wynik MTP spadł do 5.6 t/s; serwer agenta K4 na porcie 8097 trzymał VRAM.
- [[lekcja-baseline-wlasnego-silnika|„Nx szybciej” bywa liczone względem własnego albo zimnego silnika]] — Posty Lucebox podają przyspieszenia względem własnego silnika albo zimnego llama.cpp: KVFlash ma pełny prefill 32K 47.2 s (694 t/s) wobec 1168 t/s llama.cpp na tej samej 3090, a PFlash v1 porównywał się do „~257 s” na zimno zamiast 169.3 s na ciepło.
<!-- AUTO:END -->
