---
typ: lekcja
tags: [lekcje, vast, chmura, nvidia, pomiar, moc]
aktualizacja: 2026-11-17
zrodlo: właściciel 2026-11-17 („nie możemy brać takich kart z aż tak zaniżoną mocą, to nie ma sensu”); K-114 qwen-opt/cloud/k114/res/{3090,3060}/gpu.csv i smi.csv; qwen-opt/cloud/hostguard.sh; qwen-opt/cloud/hosty-zle.txt
status: aktualne
---
# Lekcja: na Vaście bierzemy tylko karty z pełną mocą — sprawdzenie przed pobraniem modelu, zły host na czarną listę

**Na Vaście bierzemy tylko hosty z pełną mocą karty: sprawdzenie `nvidia-smi` przed pobraniem modelu, zły host od razu usuwamy i dopisujemy do czarnej listy.**

Hosty Vast potrafią mocno dławić kartę. W K-114:
- 3090: limit mocy 250 z 420 W, pamięć pod obciążeniem 5001 z 9751 MHz → 23% sufitu dekodu;
- 3060: przyklejona do 135 z 170 W przy 85 °C.

**Takie liczby nie mówią nic o karcie** (właściciel 2026-11-17). Odrzucamy host od razu, za centy, i bierzemy następną ofertę.

**Reguła** (KERNEL-SESJA.md → Vast; próg 85% ostatecznie, właściciel 2026-11-17 17:53, wcześniej 95%). Zaraz po starcie instancji, przed pobraniem modelu, sprawdzić `nvidia-smi`. Host odpada, gdy:
- `power.limit` < 85% `power.default_limit`;
- `clocks.max.mem` < 85% specyfikacji (`skill-io/karty.json → mem_clock_mhz`);
- temperatura bez obciążenia ≥ 80 °C.

Odrzucony host: `vastai destroy instance <id> -y`, a `machine_id` trafia do `qwen-opt/cloud/hosty-zle.txt`.

**Wynik z ograniczonej karty** idzie najwyżej jako „dolna granica”, osobno, nigdy jako pomiar karty.

**W skryptach:**
- `qwen-opt/cloud/hostguard.sh` (wspólny dla runnerów):
  - `hg_pick "<GPU>"` wybiera najtańsze oferty, pomija hosty z czarnej listy;
  - `hg_check` robi bramkę, usuwa instancję i dopisuje host do listy.
- `k114/launch.sh "RTX 3090" <label>` próbuje do 3 ofert. Hosty, które utknęły w „loading” albo odrzucają SSH, też idą na listę.
- `k114/summ.py` po pomiarze oznacza `LIMITED HOST`, gdy limit mocy albo mediana zegara pamięci pod obciążeniem spadnie < 85%.

**Pułapka:** host 3090 pokazywał bez obciążenia `clocks.max.mem` 9751 MHz (pełne), a pod obciążeniem trzymał 5001. Bramka przed pobraniem złapałaby go dopiero po limicie mocy (250/420 W). Dlatego obowiązuje też kontrola po pomiarze (smi.csv → `summ.py`).

**Sprawdzone na mockach** (2026-11-17), werdykt `hg_check`:
- 250/420 W → zły;
- 135/170 W → zły;
- 84 °C bez obciążenia → zły;
- pamięć 5001/9751 → zły;
- 5060 Ti 180/180 W, 14001 MHz, 38 °C → dobry.

`hg_pick` nie zwraca oferty hosta 27243 (3060 z K-114).

## Powiązane
- [[lekcja-limit-mocy-hosta]]
- [[lekcja-limit-mocy-285w]]
- [[lekcja-vastai-destroy-pyta]]
- [[2026-11-17-k114-nvidia-sufit]]
- [[skill-io-pulapki]]
