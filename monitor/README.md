# REACTOR – monitor GPU/CPU/LLM w terminalu

Pełnoekranowy monitor na żywo dla tego serwera (Radeon RX 7900 XTX + Ryzen 7 5700X),
pomyślany pod uruchamianie lokalnych LLM. Czysty Python 3.12 (tylko biblioteka
standardowa), surowe sekwencje ANSI: 24-bitowe kolory, znaki braille'a i bloki.

## Co pokazuje

- **GPU** (`/sys/class/drm/card*/device` + hwmon amdgpu): obciążenie GPU i kontrolera
  pamięci, VRAM zajęty/całkowity, temperatury edge / junction / mem, pobór mocy
  względem limitu (285 W), zegary sclk/mclk (z oznaczeniem GFXOFF w spoczynku), obroty
  wentylatora, łącze PCIe, aktualny poziom DPM, procesy trzymające GPU (KFD) z ich VRAM.
- **CPU**: obciążenie każdego z 16 wątków (animowany „equalizer”), suma, load average,
  temperatura Tctl (k10temp), temperatura NVMe, częstotliwość średnia i maksymalna,
  RAM (dużymi cyframi obok TOTAL/TCTL/FREQ, pasek z wykresem i w nagłówku) i swap.
- **Procesy**: top procesów wg CPU (z RSS).
- **I/O**: przepustowość dysków (odczyt/zapis) i sieci (pobieranie/wysyłanie).
- **LLM**: gdy działa `llama-server` – nazwa modelu (z `-m` w linii poleceń albo z logu)
  i **faza na żywo**:
  - `PREFILL 1006 t/s · 8 648 tok · 94% · 8.6 s` z paskiem postępu i ETA – z linii
    `prompt processing, n_tokens = …, progress = …, t = … s / … tokens per second`, które
    serwer wypisuje po każdym ubatchu, gdy prefill trwa > 3 s (krótszy prefill: czas od
    startu żądania); duże cyfry pokazują wtedy t/s prefillu, a wykres „prompt” jego historię
    (szczyt ▲);
  - `DECODE 109 t/s` – tokeny/s liczone co 0,25 s z `n_decoded` z `GET /slots` (okno 1 s),
    a bez `/slots` z linii `tg_3s` w `~/qwen-opt/logs/latest.log`;
  - `IDLE` + ostatni prompt (`last prompt 9 200 tok @ 1016 t/s`; `~` = szacunek do czasu
    linii `prompt eval time` na końcu żądania); n_gen, szczyt, ostatnie `eval` / `prompt`
    tok/s, średnia z 2 minut.

  `/slots` jest odpytywane z osobnego wątku tylko w trakcie żądania (≤ 4 Hz, timeout
  100 ms, po błędzie 1 s przerwy, błędy są ciche); serwer odpowiada między krokami
  dekodowania, w trakcie dużego batcha prefillu nie odpowiada (wtedy dane z logu).
- **Duże liczby**: obciążenie GPU %, temperatura junction, moc W, tokeny/s (oraz CPU %,
  Tctl, częstotliwość) rysowane dużą czcionką blokową, kolor zależny od wartości.
- **Historia**: każda kluczowa metryka ma wykres z ostatnich ~2 minut (punkt co 0,5 s,
  średnia z 2 próbek), wypełniony gradientem od zimnych (cyjan) do gorących (róż/czerwień)
  wartości, ze świecącą górną krawędzią.
- **Rdzeń 3D**: obracający się, cieniowany torus (siatka w znakach braille'a).
  Prędkość obrotu = obciążenie GPU, kolor = temperatura junction, świetlna fala
  biegnąca po pierścieniu i pulsowanie = tokeny/s z llama-server.

## Wygląd

Każda sekcja to osobna „karta” z zaokrągloną ramką w swoim kolorze (GPU – róż/pomarańcz,
CPU – cyjan/fiolet, LLM – limonka, I/O – pomarańcz, procesy – fiolet), kolorową
etykietą z ikoną i lekko zabarwionym tłem. Po górnej krawędzi każdej karty co kilka
sekund przebiega błysk, a w prawym górnym rogu miga dioda aktywności (szybciej przy
większym obciążeniu sekcji; pusta ○ = brak llama-server). Paski mają gradient i jasną
końcówkę, słupki 16 wątków CPU mają opadające znaczniki szczytu, tytuł w nagłówku
mieni się kolorami. Lokalnie paski i liczby płynnie interpolują między próbkami.

Jeśli tło terminala jest przezroczyste/akrylowe albo zabarwienie kart nie pasuje do
motywu, użyj `--no-tint` (lub klawisza `t`) – wtedy widać tło terminala.

Monitor tylko **czyta** pliki sysfs/procfs i log oraz robi `GET /slots` na
`127.0.0.1:<port z linii poleceń llama-server>` – nigdy nie zapisuje do sysfs, nie
otwiera `/dev/kfd` ani `/dev/dri` i nie wywołuje `rocm-smi`.

## Uruchomienie

```bash
python3 ~/KERNEL/monitor/reactor.py              # lokalnie 15 fps, przez SSH 4 fps; układ 1
python3 ~/KERNEL/monitor/reactor.py --no-3d      # lżejszy tryb bez bryły 3D
python3 ~/KERNEL/monitor/reactor.py --fps 10     # inna liczba klatek animacji na sekundę
python3 ~/KERNEL/monitor/reactor.py --layout 3   # od razu widok „core”
```

Opcje: `--fps N` (1–60, animacja; dane i tak są rysowane 4 razy na sekundę), `--no-3d`,
`--no-tint`, `--layout {1,2,3}`, `--link {auto,local,ssh}` (tryb SSH, domyślnie gdy jest
ustawione `SSH_CONNECTION`), `--log ŚCIEŻKA` (inny log llama-server), `--no-slots` (bez
`GET /slots`, tylko log), `--duration S` (wyjście po S sekundach – do testów),
`--stats PLIK` (statystyki klatek i bajtów w JSON przy wyjściu – do testów).

Zalecany rozmiar terminala to co najmniej **100x30** (najlepiej ok. 160x45).
Przy mniejszym oknie panele chowają wykresy, a poniżej 60x18 pojawia się komunikat.

### Przez SSH z Windows

Najlepiej użyć **Windows Terminal** (obsługuje 24-bitowe kolory i synchronizowane
odświeżanie) z czcionką zawierającą znaki braille'a i bloki, np. **Cascadia Mono**
(domyślna w Windows Terminal) lub Cascadia Code. Klasyczna konsola `powershell.exe`
(conhost) też zadziała, ale wykresy i torus mogą wyglądać gorzej. Przykład:

```powershell
ssh -t jaro@serwer "python3 ~/KERNEL/monitor/reactor.py"
```

Przez SSH (`SSH_CONNECTION` ustawione) monitor sam przechodzi w tryb lekki: klatki
tylko razem z danymi (4 fps), wartości bez interpolacji, rdzeń 3D w 3 odcieniach zamiast
16. Stopka pokazuje `ssh-lite`, nagłówek – rzeczywiste fps i kB/s wysyłane do terminala.

Opóźnienie: wcześniej terminal przez SSH nie nadążał (1,3–1,9 MB na 10 s), nadmiar
czekał w buforach sshd/TCP (okno kanału SSH to ~2 MB, więc kolejka tty jest pusta)
i obraz spóźniał się o sekundy. Teraz po każdej klatce idzie zapytanie DSR `ESC[5n`;
terminal odpowiada `ESC[0n` dopiero, gdy przetworzy wszystko przed nim. Dopóki odpowiedź
nie wróci (albo kolejka tty ma > 8 KB), klatki samej animacji są pomijane, a klatka
z nowymi danymi idzie bez animacji, jedna naraz – reszta się scala. Zapis do terminala
jest nieblokujący, więc próbkowanie nie staje.

## Klawisze

| Klawisz      | Działanie                                              |
|--------------|--------------------------------------------------------|
| `q`, Ctrl+C  | wyjście (terminal zostaje przywrócony)                 |
| `p`, spacja  | pauza animacji (dane dalej się odświeżają)             |
| `+` / `-`    | więcej / mniej klatek animacji na sekundę (2–60)       |
| `1`          | układ „reactor”: rdzeń 3D + LLM, GPU, CPU, I/O, procesy |
| `2`          | układ „data”: bez 3D, większe wykresy LLM i I/O        |
| `3`          | układ „core”: duży torus na środku, kluczowe liczby po bokach |
| `t`          | włącz/wyłącz zabarwione tło kart                       |
| `r`          | pełne przerysowanie ekranu                             |

## Obciążenie

Rysowanie jest różnicowe na poziomie komórek: wysyłane są tylko zmienione komórki,
kolor SGR tylko gdy się zmienia (spacja ignoruje kolor tekstu, pełny blok – tło),
a zmienione komórki wiersza idą kolorami (jedno SGR na kolor, przeskoki kursorem).
Wykresy przesuwają się tylko przy nowym punkcie historii (2 Hz). Dane czytane 4 razy na
sekundę z otwartych deskryptorów (`pread`), lista procesów co 2 s, temperatura NVMe co
10 s (jej odczyt blokuje ok. 25 ms). Nagłówek pokazuje własne CPU, rzeczywiste fps i kB/s.

Pomiar 2026-11-06, 200x55, 10 s (`script`, `nice`), przy pracującym llama-server
(GPU ~99%, trwające żądania): przez SSH (domyślnie) **267–280 KB / 10 s** (wcześniej
1,79–1,81 MB), CPU 2,6–2,9% rdzenia (wcześniej 3,0–3,3%), klatka średnio 3,8–4,2 ms,
maks. 9,1 ms; z pustym logiem 233 KB (wcześniej 1,76 MB); z `--no-3d` 147 KB. Lokalnie
(15 fps) 0,95–1,0 MB (wcześniej 1,82–1,88 MB), ale CPU 5,9–6,9% (diff komórek kosztuje).
Emulowany wolny terminal (40 KB/s, RTT 40 ms): zmiana w logu na ekranie po 0,07–0,10 s
(wcześniej zaległość rosła do 30 s); przy 15 KB/s po 0,13–0,24 s.

## Pliki

- `reactor.py` – punkt wejścia: terminal (kontrola przepływu), różnicowy renderer
  komórek, układy paneli, animacja, klawisze.
- `sensors.py` – odczyt sysfs/procfs, śledzenie logu llama-server, wątek `GET /slots`.
- `gfx.py` – paleta, sekcje (karty), paski, wykresy z gradientem, duże cyfry.
- `core3d.py` – renderer torusa 3D w znakach braille'a.
- `test_sensors.py` – testy parsowania logu i `/slots` (linie z prawdziwych logów
  + odtworzenie wszystkich `~/qwen-opt/logs/server-*.log`): `python3 test_sensors.py`.
