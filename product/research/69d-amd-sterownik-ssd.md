# 69d – Błąd sterownika AMD Adrenalin: ciągłe zapisy SSD (atieclxx.exe)

Data: 2026-11-09. Status: research, bez testów GPU, bez pobrań.

## TL;DR
- **NEW** (cały temat; w KB brak wcześniejszych notatek o atieclxx/ReBAR: grep `wiki/`, `product/research/` = 0 trafień).
- Błąd dotyczy tylko Windows: usługa *AMD External Events Utility* (`atieclxx.exe` + `atiesrxx.exe`) stale zapisuje na dysk systemowy z prędkością 0.3–1.5 MB/s (typowo). 5 MB/s pochodzi z jednego niepotwierdzonego zgłoszenia, a „432 GB/dzień” to tylko 5 MB/s × 24 h, czyli najgorszy przypadek zapisów hosta, a nie zapisów NAND.
- AMD potwierdziło błąd (forum, październik). 8.11 przedstawiciel AMD na Reddit, za Neowin, podał przyczynę: interakcja z filtrem PCIe Microsoftu; wyłączenie ReBAR ma omijać problem. Poprawka jest w walidacji. **Numer „26.11.1” NIE jest potwierdzony w żadnym źródle, które przeczytałem.** Źródła mówią „przyszły sterownik, bez daty”.
- Wersje: zgłoszenia obejmują **26.6.4 → 26.10.2**, więc nie tylko 26.10.x. Ta sama wersja (26.10.2) działa u jednych źle, u innych dobrze, a jeden właściciel 7900 XTX nie ma problemu. Sam numer wersji NIE wystarcza do rozpoznania.
- Enigma: **nigdy nie rekomendować wyłączania ReBAR.** Zalecenie: jednorazowy pomiar zapisów `atieclxx` w hardware scanie i ostrzeżenie oparte na pomiarze, a nie tylko na wersji.
- Nasz serwer Linux: nie dotyczy (amdgpu, brak atieclxx). ReBAR jest aktywny (BAR0 = 32 GiB).

## Fakty ze źródłami
| # | Fakt | Źródło | Status |
|---|---|---|---|
| 1 | Proces `atieclxx.exe` („AMD External Events Client Module”), ścieżka `C:\Windows\System32\config\systemprofile\AppData\Local\AMD\atieclxx.exe`; na zrzucie ~450 KB/s zapisu | [wccftech](https://wccftech.com/amd-acknowledges-radeon-driver-bug-causing-constant-ssd-writes-fix-in-the-works/) | NEW, fakt (zrzut użytkownika) |
| 2 | Typowo 0.3–1.5 MB/s; 5 MB/s to jedno zgłoszenie z Reddita, którego Comss nie znalazł na forum AMD | [windowsforum (za Comss)](https://windowsforum.com/news/amd-radeon-ssd-write-bug-how-to-check-atieclxx-exe-on-windows-10-and-11.450605/), [comss](https://www.comss.ru/page.php?id=22686) | NEW |
| 3 | Wersje ze zgłoszeniami: 26.6.4 (RX 7800 XT, 600 MB w 10 min), 26.7.1/26.8.1/26.10.1 (RX 9060 XT, do 1.5 MB/s), 26.9.2/26.10.1 (RX 9070 XT, 0.3 MB/s); 26.10.2 u jednego OK, u innych nie; 7900 XTX: jeden bez problemu | windowsforum, tabela Comss; [forum AMD (26.6.4)](https://pcforum.amd.com/s/question/0D5Pd00001gfN5PKAU/atieclxx-amd-external-events-client-module-causes-excessive-disk-readwrite-and-performance-stutters) | NEW, anegdoty |
| 4 | AMD_Matt (październik): „We're looking into it…future driver release” | [forum AMD, wątek 26.10.1](https://pcforum.amd.com/s/question/0D5Pd0000214MBjKAM/amd-software-adrenalin-edition-26101-driver-release-notes) (cytat za wccftech) | NEW |
| 5 | AMD_Vik: poprawka prawdopodobnie zacommitowana, mogła nie zdążyć przed cutoffem | [reddit r/buildapc](https://www.reddit.com/r/buildapc/s/DNyqdtSvAV) (za wccftech) | NEW |
| 6 | Przyczyna: interakcja External Events Utility z filtrem PCIe Microsoftu; obejście: wyłączyć ReBAR; „low-risk fix” w walidacji, bez daty i numeru wersji | [Neowin](https://www.neowin.net/news/old-amd-windows-chipset-driver-bug-that-quietly-degrades-ssds-now-back-on-gpus) (za windowsforum, aktualizacja 8.11) | NEW; wtórne źródło, nie czytałem posta AMD bezpośrednio |
| 7 | Release notes 26.10.2 (30.10) nie wspominają o błędzie | [RN-RAD-WIN-26-10-2](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-10-2.html) (za wccftech) | NEW |
| 8 | Zatrzymanie usługi może zepsuć FreeSync, hotkeye Adrenalina, hot-plug monitorów i profile kolorów; nie usuwać pliku | wccftech, windowsforum | NEW |
| 9 | Precedens z XI 2025: ta sama usługa dopisywała log w `EEUDumps` przy przesuwaniu okien | windowsforum (za Tom's Hardware) | NEW |
| 10 | Pojedyncze zgłoszenia stutterów i dropoutów audio, które znikają po wyłączeniu usługi; bez kontrolowanych testów | windowsforum | NEW, anegdota |
| 11 | Krąży też nieoficjalne obejście: kopiowanie starych plików sterownika szyny PCI AMD. Jest ryzykowne i AMD go nie zatwierdziło | windowsforum (za Neowin) | NEW |

**Sprawdzenie liczb:** 5 MB/s × 86 400 s = 432 GB/dzień, a 1.5 MB/s daje 130 GB/dzień. To zapisy hosta przy pracy 24/7. Dla dysku 640 TBW (Kingston NV3 2 TB) oznacza to wyczerpanie limitu po ~4 latach przy 5 MB/s albo ~13.5 roku przy 1.5 MB/s (Comss). Tych liczb nie należy traktować jak prognozy.

## (b) Nasz serwer Linux: weryfikacja
- `lsmod`: moduł `amdgpu` jest załadowany (6 użytkowników). `atieclxx.exe` i `atiesrxx.exe` to wyłącznie binaria Windows z pakietu Adrenalin. Stos Linux (amdgpu KMD + Mesa/ROCm) nie ma odpowiednika usługi „External Events”. Filtr PCIe Microsoftu istnieje tylko w Windows. Wniosek: serwer jest **nie dotyczy** (fakt co do modułu; brak odpowiednika usługi oceniam [INFERENCE], ale z wysoką pewnością).
- ReBAR na naszym XTX jest aktywny: `/sys/class/drm/card0/device/resource`, BAR0 = 32.0 GiB (VRAM 24 GB zaokrąglone do potęgi 2). Nic nie zmieniamy.

## (a) Enigma na Windows + AMD
- **ReBAR: nigdy nie wyłączać i nigdy tego nie radzić.** Przy ładowaniu wag (mmap→VRAM) i przy offloadzie KV/warstw ReBAR pozwala CPU mapować całą VRAM. Bez niego okno BAR ma 256 MB i transfery idą przez staging. Wpływ na tokeny na sekundę w samym dekodowaniu, gdy cały model siedzi w VRAM, jest mały. Wpływ na czas ładowania modelu i na tryby z częściowym offloadem może być zauważalny [INFERENCE: nie mierzyliśmy, a dane gamingowe nie przenoszą się na LLM]. W porównaniu z kosztem tego obejścia sam błąd jest drobny.
- Zatrzymanie usługi (odwracalne) to łagodniejsze obejście niż ReBAR. Decyzję zostawiamy jednak użytkownikowi, bo zatrzymanie psuje FreeSync i hotkeye. Enigma nie powinna sama zatrzymywać usług.
- Detekcja na podstawie samej wersji daje fałszywe alarmy, bo ta sama wersja raz działa źle, raz dobrze. Lepiej sprawdzić wersję i zmierzyć zapisy.
- Enigma NVIDIA (3090/4090/5090): nie dotyczy, bo to wyłącznie usługa AMD.

## (c) Zużycie SSD a nasza polityka KV
- KNOWN: [raport-21d](../../wiki/research/raport-21d-kv-na-dysku.md):10,19 ustala budżet zapisu KV ≤ 10 GB/dzień, a decyzja użytkownika z 2026-10-19 brzmi: KV/sesje tylko w RAM.
- NEW: przy 0.3–1.5 MB/s błąd AMD sam generuje 26–130 GB/dzień, czyli 2.6–13× nasz cały budżet. Jeśli Enigma kiedykolwiek włączy KV-na-dysku na Windows/AMD, użytkownik z tym błędem przekroczy budżet niezależnie od nas. To kolejny argument za domyślnym „KV w RAM” i za tym, żeby w UX mówić, kto zapisuje na dysk (Enigma kontra sterownik).

## Propozycja UX Enigma (do decyzji, nie implementować)
**Hardware scan → karta „Dysk / sterownik GPU”** (tylko Windows i GPU AMD):
1. Odczyt wersji Adrenalin z rejestru (klucz klasy display, `DriverVersion` / `RadeonSoftwareVersion`). Jeśli wersja mieści się w [26.6.x, ostatnia bez poprawki], scan uruchamia krok 2.
2. Pomiar 30 s w bezczynności: bajty zapisu procesu `atieclxx.exe`, przez `GetProcessIoCounters` lub licznik PDH `\Process(atieclxx)\IO Write Bytes/sec`. Uwaga: zapisy mogą być przypisane do procesu System; jeśli licznik pokazuje 0, ostrzeżenia nie ma, więc nie straszymy fałszywie.
3. Próg: ≥ 0.2 MB/s średnio. Wtedy pojawia się żółte ostrzeżenie: „Sterownik AMD (wersja X) zapisuje ~Y GB/dzień na dysk systemowy. To znany błąd AMD, poprawka w drodze. Zalecamy: zaktualizuj sterownik po wydaniu poprawki. Tymczasowo możesz zatrzymać usługę *AMD External Events Utility* (może wyłączyć FreeSync/hotkeye). **Nie wyłączaj Resizable BAR**: spowolni ładowanie modeli.” Do tego link do wątku AMD. Bez automatycznych akcji.
4. Ostrzeżenie znika, gdy wersja ≥ wersja z poprawką. Numer wersji wpisujemy dopiero po opublikowaniu release notes; nie zgadujemy „26.11.1”.
5. Osobny check: ReBAR wyłączony (rozmiar okna BAR ≤ 256 MB, odczytany przez DXGI/ADL) → informacja „włącz ReBAR/Above 4G w BIOS dla szybszego ładowania”. Ten check jest niezależny od opisanego błędu.

## Testowalne pomysły
Wzorzec V(w, ctx) nie ma tu zastosowania: temat nie wpływa na szerokość weryfikacji ani na t/s naszego serwera. Oczekiwany zysk na XTX = 0.

| Pomysł | Oczekiwany zysk | Test | Kill | Pobrania |
|---|---|---|---|---|
| Wpływ ReBAR na LLM (ładowanie, offload) | 0 na serwerze; dane do decyzji UX | Na wynajętej maszynie Windows+AMD (nie na naszym serwerze): czas ładowania Q4_K_M 27B oraz t/s pp/tg przy ReBAR on/off, ten sam BIOS i temperatura | różnica < 5% we wszystkim → w UX zostaje tylko informacja | brak (model już mamy na tej maszynie) |
| Prototyp detektora (pkt 2 UX) | wiarygodność ostrzeżenia | Windows+AMD z błędem: porównać licznik PDH z resmon | licznik nie widzi zapisów (przypisane do System) → zostaje tylko detekcja wersji z miękkim komunikatem | brak |

## Ryzyka
- Większość danych to anegdoty i źródła wtórne. Przyczynę (filtr PCIe MS) znamy z drugiej ręki, przez Neowin.
- Numer wersji z poprawką jest nieznany, a twarda lista wersji szybko się zestarzeje.
- Polecenie w UX zatrzymania usługi może zepsuć FreeSync, a winę użytkownik przypisze Enigmie.

## Wiersz do ZRODLA (propozycja)
| 2026-11-08 | AMD Adrenalin: ciągłe zapisy SSD przez atieclxx.exe (26.6.4–26.10.2, Windows) | https://wccftech.com/amd-acknowledges-radeon-driver-bug-causing-constant-ssd-writes-fix-in-the-works/ ; https://windowsforum.com/news/amd-radeon-ssd-write-bug-how-to-check-atieclxx-exe-on-windows-10-and-11.450605/ | 69d | nie dotyczy serwera; UX ostrzeżenie Enigma |
