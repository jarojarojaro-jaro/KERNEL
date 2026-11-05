# 64 — RX 7900 XTX: czy bezpiecznie obniżyć maksymalny zegar shaderów (sclk cap)? Research przed jakąkolwiek zmianą

Data: 2026-11-05. Karta: **Sapphire PULSE RX 7900 XTX** (`1002:744c` rev c8, subsystem `1da2:471e`, VBIOS `113-3E4710U-O4W`), Navi31 / gfx1100 / SMU (MP1) 13.0.0, PMFW `0x004e8200` (78.130.0). Jądro **6.8.0-138-generic** (Ubuntu 24.04), `amdgpu.ppfeaturemask=0xfff7ffff`.
Zakres: tylko odczyty (sysfs `cat`, `journalctl`, źródła jądra, internet). Żadnych zapisów do sysfs, żadnej pracy na GPU, nic jako root. Drafty `~/qwen-opt/thermal/xtx-eco` i `sweep.sh` **nie** są zainstalowane ani uruchomione.
Oznaczenia: `[INFERENCE]` to wniosek, którego nie zmierzyłem ani nie znalazłem wprost w źródle. Linki do kodu prowadzą do drzewa Ubuntu z tagiem `Ubuntu-6.8.0-138.138`, czyli dokładnie naszego jądra (numery linii sprawdziłem w pobranym pliku). Skróty:
- **U-PPT** = [smu_v13_0_0_ppt.c @ Ubuntu-6.8.0-138.138](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138)
- **U-SMU** = [amdgpu_smu.c](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c?h=Ubuntu-6.8.0-138.138)
- **U-PM** = [amdgpu_pm.c](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138)
- **U-DEV** = [amdgpu_device.c](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/amdgpu/amdgpu_device.c?h=Ubuntu-6.8.0-138.138)
- **IF** = [smu13_driver_if_v13_0_0.h @ v6.8](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/inc/pmfw_if/smu13_driver_if_v13_0_0.h), w Ubuntu-138 identyczny.

---

## 0. Werdykt w skrócie

**Obniżenie samego maksymalnego zegara shaderów nie uszkodzi karty.** Fizycznie to ruch w bezpieczną stronę: niższa częstotliwość, niższe napięcie, mniej watów i niższe temperatury. Nie znalazłem żadnego zgłoszenia trwałego uszkodzenia ani zawieszeń po obniżeniu `OD_SCLK` na Navi31 (§4).

**Na naszym jądrze 6.8 jest jednak potwierdzony przez AMD błąd sterownika i firmware'u, który sprawia, że obecne drafty są niebezpieczne dla polityki wentylatora:**
- `s 1 X` + `c` wysyła do firmware'u tablicę OD, w której jest zaznaczona tylko sekcja zegara;
- firmware (PMFW) traktuje tę maskę jako **pełną** listę nadpisanych ustawień, więc **po cichu wraca do fabrycznego sterowania wentylatorem**;
- `fan_curve` w sysfs dalej pokazuje 100% (§3.2);
- w drugą stronę działa to tak samo: commit krzywej wentylatora z timera (przy przejściu load↔idle) po cichu zdejmuje limit zegara;
- poprawka jest dopiero w mainline v7.4-rc1. Nie ma jej w Ubuntu 6.8.0-138 ani w najnowszym 6.8.0-149.

Nasz `fan.sh` sprawdza tylko odczyt z sysfs (pamięć podręczną sterownika), więc **takiej utraty krzywej nigdy by nie wykrył**. Zostałaby do następnej zmiany stanu load↔idle.

| Dźwignia | Werdykt | Ryzyko dla sprzętu | Ryzyko operacyjne na 6.8 |
|---|---|---|---|
| **Limit sclk** (`s 1`) 2400…1800 | **TAK, po poprawkach z §10** (jeden zapisujący, każdy commit niesie krzywą wentylatora i `s 1`, weryfikacja fizyczna) | bardzo niskie | **wysokie bez poprawek**: wentylator po cichu wraca na fabryczną politykę (~1800–2970 RPM zamiast 3500), a pomiar traci sens |
| Limit sclk 1600 | dopuszczalny, ale bez zysku sprawności (§9) | bardzo niskie | jak wyżej |
| Limit sclk 1200 | dopuszczalny według sterownika; **nie zalecam**, bo nie daje zysku sprawności, a grozi spadkiem dekodowania | niskie | jak wyżej |
| **Limit mocy** (`power1_cap`) 272–303 W | TAK, najprostsza dźwignia: przy ≤ 303 W sterownik wysyła zwykły komunikat SMU i **nie dotyka tablicy OD** | bardzo niskie | niskie; zakres tylko 272–285 W |
| Limit mocy > 303 W | NIE (przechodzi przez tablicę OD z samą maską PPT, czyli ten sam błąd) | — | wysokie |
| **Profil** (`pp_power_profile_mode`) | **NIE ruszać.** KFD/ROCm sam włącza COMPUTE (widać `COMPUTE*`), a `manual` z draftu wyłącza to automatyczne przełączanie | brak | średnie: ręczny `manual` psuje automatykę; jest też raport twardego zawieszenia przy `high` + OD |
| **Undervolt** (`vo`) | **NIE teraz** | niskie dla krzemu, **wysokie dla stabilności** (ciche złe wyniki, hang, potem reset GPU) | wysokie; przy limicie zegara i tak jest po cichu przycinany (§9) |
| Zegar pamięci (`m`) | **NIGDY** | — | zgłoszenia crashy i hangów |

Niezależnie od tego termika karty jest dziś zdrowa. Przy 283–288 W i wentylatorze 100%: hotspot 63–68 °C, edge 47–50 °C, różnica 15–18 °C, VRAM 70–74 °C. Stary alarm „106 °C i różnica 40 °C” pochodzi z 2026-10-09: fabryczny wentylator, prefill 196k. **Repaste nie jest dziś potrzebny.** Jedna kontrola z §13 rozstrzygnie, czy przy prefillu 196k różnica wraca.

---

## 1. Jak to działa: co pokazują pliki sysfs na NASZEJ karcie (odczyt 2026-11-05)

Ścieżka: `/sys/class/drm/card0/device/`. Dokumentacja jądra: [docs.kernel.org – GPU Power/Thermal Controls](https://docs.kernel.org/gpu/amdgpu/thermal.html).

### 1.1 `pp_od_clk_voltage` (OverDrive = tablica OD w firmware)
```
OD_SCLK:  0: 500Mhz   1: 2885Mhz
OD_MCLK:  0: 97Mhz    1: 1250MHz
OD_VDDGFX_OFFSET: 0mV
OD_RANGE: SCLK 500..5000 Mhz, MCLK 97..1500 MHz, VDDGFX_OFFSET -450..0 mv
```
- `OD_SCLK 0/1`: dolna i górna granica zegara shaderów (GFXCLK), w które firmware może wejść. `1: 2885` to sufit (pole `GfxclkFmax` tablicy OD). Karta nigdy nie pracuje na nim długo, bo wcześniej zatrzymuje ją limit mocy (§2). Wypisywane z kopii sterownika ([U-PPT#n1369](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1369)). **To nie jest stan firmware'u**: pokazuje to, co sterownik ostatnio zapisał lub przygotował (§3.2).
- `OD_MCLK`: granice zegara pamięci GDDR6 (1250 MHz = 20 Gb/s na pin, 384 bity → 960 GB/s). Nie ruszamy.
- `OD_VDDGFX_OFFSET`: przesunięcie całej krzywej napięcie–częstotliwość („voltage = voltage calculated from v/f curve + overdrive vddgfx offset”, [U-PM#n684](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n684)). 0 = fabrycznie.
- `OD_RANGE`: zakres, który sterownik w ogóle przyjmie (z tabeli VBIOS `OverDriveLimitsMin/BasicMax`). **5000 MHz to nie jest bezpieczny zakres**, tylko granica walidacji. Literówka typu `4000` byłaby żądaniem podkręcenia, więc skrypt musi sam ograniczać wartości do ≤ 2885.
- Polecenia: `s 0|1 MHz`, `m 0|1 MHz`, `vo mV`, `r` (przywróć), `c` (zatwierdź) ([U-PM#n767](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n767)).

### 1.2 `pp_dpm_sclk`, `pp_dpm_mclk`, `pp_dpm_fclk`, `pp_dpm_socclk`, `pp_dpm_dcefclk`, `pp_dpm_pcie`
Bezczynnie:
```
sclk: 0: 500Mhz  1: 0Mhz *  2: 2371Mhz
mclk: 96* / 456 / 772 / 1249
fclk: 601* / 1000 / 1200 / 1600 / 2000 / 2201 / 2251 / 2301
socclk: 500* / 1500   dcefclk: 145* / 1563   pcie: 2.5GT/s x1 / 5.0GT/s x4 / 16.0GT/s x16 *
```
Pod obciążeniem (15:31:16–22, inny job q63 na tej karcie): `sclk` 2402–2429 MHz z `*`.
- Na RDNA3 zegar shaderów jest **drobnoziarnisty** (fine-grained). Firmware wybiera dowolną częstotliwość między min a max. Sterownik pokazuje `0: min`, sztuczną linię `1: bieżący *` i `2: max` ([U-PPT#n1297](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1297)).
- `2: 2371` to **etykieta „Game Clock” z VBIOS, a nie sufit**. Sterownik celowo zastępuje nią prawdziwy max, „aligned with Window setting”, i uprzedza, że rzeczywisty zegar może ją przekraczać ([U-PPT#n606](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n606)).
- `1: 0Mhz *` przy bezczynności: włączone GFXOFF (rdzeń wyłączony). To nie awaria.
- Bieżąca wartość pochodzi z metryk firmware'u (średni zegar przed lub po deep sleep). W naszym logu z 2026-10-18 19 ze 119 próbek ma > 2800 MHz, a max to **3079 MHz, ponad `OD_SCLK 1: 2885`** ([`~/qwen-opt/logs/sweep-gpu.csv`](../../../qwen-opt/logs/sweep-gpu.csv), np. 21:44:39). Pojedyncza próbka może więc przekroczyć sufit OD. Weryfikacja limitu musi patrzeć na **medianę z kilku–kilkunastu sekund pod stałym obciążeniem**, nie na pojedynczy odczyt [INFERENCE co do mechanizmu].
- `mclk`/`fclk`/`socclk`: osobne domeny DPM (pamięć, Infinity Fabric, SoC). `s 1` ich nie zmienia (sterownik edytuje tylko `GfxclkFmax`, §3.1).
- `pcie`: 16 GT/s x16 – pełna prędkość łącza.

### 1.3 `pp_power_profile_mode`
Aktywny `5 COMPUTE*` (gwiazdka). Kolumny to heurystyki menedżera aktywności: `MinActiveFreqType/MinActiveFreq`, `BoosterFreqType/BoosterFreq`, `PD_Data_*` (jak szybko i jak agresywnie podnosić zegar). Profil **nie jest limitem zegara ani mocy**, tylko zmienia zachowanie przy narastaniu obciążenia ([docs: pp_power_profile_mode](https://docs.kernel.org/gpu/amdgpu/thermal.html#pp-power-profile-mode), pola: [v6.8 L2401-L2470](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c#L2401-L2470)).
- COMPUTE włącza się **automatycznie**: KFD (ROCm) przy pierwszej kolejce procesu woła `amdgpu_amdkfd_set_compute_idle(false)` i dalej `amdgpu_dpm_switch_power_profile(COMPUTE)` ([amdgpu_amdkfd.c#n711](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd.c?h=Ubuntu-6.8.0-138.138#n711)).
- Działa to tylko wtedy, gdy poziom **nie** jest `manual` ani `perf_determinism` ([U-SMU#n2335](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c?h=Ubuntu-6.8.0-138.138#n2335)).
- Na SMU 13.0.0 z nowym PMFW COMPUTE dokłada bit POWER_SAVING („SMU 13.0.0 optimizations when ROCm is active”, [U-PPT#n2596](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n2596), commit [f8cd72728bdc](https://github.com/torvalds/linux/commit/f8cd72728bdcf72d01305c8245b039f0ca9ea088)).

### 1.4 `power_dpm_force_performance_level` = `auto`, `power_dpm_state` = `performance`
- `auto`: firmware sam wybiera zegary w granicach limitów. `manual` daje ręczne poziomy i profile. `high`/`low` przypinają zegary ([docs](https://docs.kernel.org/gpu/amdgpu/thermal.html#power-dpm-force-performance-level)).
- **Edycja OD na SMU13 nie wymaga `manual`**: w `od_edit_dpm_table` nie ma sprawdzenia poziomu. Zdanie „first select manual” z dokumentacji to pozostałość po starszych generacjach ([U-PM#n710](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n710) vs [U-PPT#n1653](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1653)).
- `power_dpm_state` to stary interfejs (battery/balanced/performance) i na SMU13 nic nie robi ([docs](https://docs.kernel.org/gpu/amdgpu/thermal.html#power-dpm-state)).

### 1.5 `pp_features` (maska funkcji firmware'u)
`high 0x0003ebb8 low 0x71ffffff`. Włączone są m.in. `DPM_GFXCLK`, `DPM_UCLK`, `DPM_FCLK`, `GFXOFF`, `THROTTLERS`, `FW_CTF` (sprzętowe wyłączenie przy krytycznej temperaturze), `FAN_CONTROL`, `MEM_TEMP_READ`. Wyłączone są `GFX_DCS`, `GFX_EDC` i `SMARTSHIFT`. Bit `0x80000` w `ppfeaturemask=0xfff7ffff` wyłącza GFX_DCS. Bit `0x4000` (`PP_OVERDRIVE_MASK`) włącza OD, bez niego plików OD w ogóle nie ma ([v6.8 amdgpu_smu.c L654](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c#L654)).

### 1.6 `gpu_od/fan_ctrl/*` (ta sama tablica OD)
```
fan_curve: 0: 25C 40% | 1: 40C 40% | 2: 50C 100% | 3: 65C 100% | 4: 80C 100%   (krzywa "idle" z fan.sh)
           OD_RANGE: hotspot 25..100 C, 15..100 %
acoustic_limit_rpm_threshold 3600 (500..3600), acoustic_target_rpm_threshold 1800 (500..3600)
fan_minimum_pwm 15 (15..100), fan_target_temperature 85 (25..105)
```
- `fan_curve`: 5 punktów (temperatura **hotspotu** → % PWM) ([docs fan_curve](https://docs.kernel.org/gpu/amdgpu/thermal.html#fan-curve)). Zapis punktów przełącza firmware w tryb `FAN_MODE_MANUAL_LINEAR` ([U-PPT#n1795](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1795)).
- `acoustic_*`, `fan_minimum_pwm`, `fan_target_temperature`: parametry trybu **automatycznego**. Każdy zapis do nich ustawia `FanMode = AUTO` ([U-PPT#n1817](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1817) i analogicznie n1839/n1861/n1883). To pułapka z 2026-10-18 (§5).
- Fabryczny tryb auto trzyma docelowo 85 °C (hotspot) z celem akustycznym 1800 RPM. Dokładnie to widzieliśmy przed `fan.sh`: ~1850 RPM, junction 85–88 °C ([`~/KERNEL/qwen-opt/NOTES.md:146`](../../qwen-opt/NOTES.md)).
- Na 6.8 **nie ma** `fan_zero_rpm_enable`, który doszedł w 6.13 ([Phoronix](https://www.phoronix.com/news/Linux-6.13-AMDGPU-Zero-Fan)). Dlatego wentylator stoi do ~70 °C hotspotu nawet przy krzywej 100% ([lekcja-wentylator-rdna3](../../wiki/lekcje/lekcja-wentylator-rdna3.md)).

### 1.7 `hwmon/hwmon2/*`
| plik | wartość (bezczynnie → obciążenie) | znaczenie |
|---|---|---|
| `power1_average` | 5 W → 281–288 W | moc chipu (PPT) według firmware'u, nie całej karty |
| `power1_cap` / `_default` / `_min` / `_max` | 285 / 303 / 272 / 402 W | limit ustawiony przez `gpu-powercap.service`, domyślny z VBIOS, min i max (max 402 tylko dlatego, że OD jest włączone) |
| `temp1/2/3_input` | edge 30→49, **junction (hotspot)** 33→66, mem 48→72 °C | krawędź, najgorętszy punkt rdzenia, pamięć |
| `temp1/2/3_crit`, `_emergency` | edge 100/105, junction **110/115**, mem **108/113** °C | `crit` = próg dławienia, `emergency` = wyłączenie ASIC ([docs hwmon](https://www.kernel.org/doc/html/v6.8/gpu/amdgpu/thermal.html#hwmon-interfaces)) |
| `fan1_input` | 0 → 3514–3545 RPM | rzeczywiste obroty; 0 bezczynnie = zero-RPM |
| `pwm1` | 0 → **255** | bieżące wypełnienie PWM; 255 = 100%. Dobry fizyczny test, czy działa krzywa 100% (§10) |
| `pwm1_enable` | 2 (auto) | na RDNA3 ręczny `pwm1` jest odrzucany; wentylator steruje się tylko przez `fan_curve` ([lekcja](../../wiki/lekcje/lekcja-wentylator-rdna3.md)) |
| `in0_input` (vddgfx) | 55 → 850–864 mV | napięcie rdzenia. **Bezpośredni pomiar efektu V/F przy limicie zegara** |
| `freq1_input` (sclk), `freq2_input` (mclk) | Hz | to samo co `*` w `pp_dpm_*` |

### 1.8 `gpu_metrics` (binarny, v1.3, 120 B)
Układ: `struct gpu_metrics_v1_3` ([kgd_pp_interface.h v6.8 L635-L705](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/include/kgd_pp_interface.h#L635-L705)), wypełniany w [v6.8 smu_v13_0_0_ppt.c L2028-L2107](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c#L2028-L2107). Dekoder (tylko odczyt):
```python
import struct; b=open('/sys/class/drm/card0/device/gpu_metrics','rb').read(); H=lambda o: struct.unpack_from('<H',b,o)[0]
print('edge/hot/mem C', H(4),H(6),H(8), '| vrgfx/vrsoc/vrmem', H(10),H(12),H(14), '| gfx% umc%', H(16),H(18), '| W', H(22),
      '| gfxclk avg/cur', H(40),H(54), '| uclk cur', H(58), '| throttle 0x%x' % struct.unpack_from('<I',b,68)[0],
      '| fan', H(72), '| pcie x%d %.1fGT/s' % (H(74),H(76)/10), '| mV soc/gfx/mem', H(104),H(106),H(108),
      '| indep 0x%x' % struct.unpack_from('<Q',b,112)[0])
```
Odczyt pod obciążeniem (15:31): edge 49, hotspot 66, mem 72, VR 48–52 °C; gfx 99%, umc 72%; 283 W; gfxclk 2429 MHz; uclk 1249; fan 3531; PCIe x16 16 GT/s; Vgfx 860 mV, Vsoc 923, Vmem 803; `throttle_status 0x00010002`, `indep 0x1000000001`.
- Bit 16 = `THROTTLER_PPT0`, czyli **karta jest ograniczona limitem mocy**. To potwierdza §2. Bit 1 = `THROTTLER_TEMP_HOTSPOT` ([IF L186-L207](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/inc/pmfw_if/smu13_driver_if_v13_0_0.h#L186-L207); bity niezależne od ASIC: [amdgpu_smu.h](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/inc/amdgpu_smu.h)).
- Bit hotspotu jest ustawiony także bezczynnie przy 47 °C, więc nie oznacza realnego dławienia (do 110 °C daleko). Najpewniej zgłasza aktywność regulatora temperatury firmware'u [INFERENCE].
- `energy_accumulator` (offset 24) jest na naszym PMFW zawsze nieważny, bo Ubuntu-138 zwraca UINT_MAX dla PMFW > 0x004e1e00 (różnica Ubuntu vs v6.8 w U-PPT). Do J/token trzeba całkować `power1_average`.

---

## 2. Jak RDNA3 wybiera zegar i co zmienia limit sclk

- **DPM prowadzi firmware (PMFW), nie sterownik.** Sterownik podaje tylko granice (OD Fmin/Fmax, soft limity), limit mocy PPT i maskę profilu.
- PMFW podnosi zegar, dopóki nie zadziała któryś ogranicznik: **PPT0** (moc), TDC (prąd), temperatury edge/hotspot/mem/VR albo górna granica `GfxclkFmax` (lista ograniczników: [U-PPT#n280](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n280)).
- AMD (karta referencyjna): „Game Frequency is the expected GPU clock when running typical gaming applications, set to typical TGP”, a „Boost … maximum frequency achievable … running a bursty workload” ([AMD claims GD-147/GD-151](https://www.amd.com/en/legal/claims/gaming-details.html); referencja: game 2300, boost 2500 MHz, TBP 355 W, [amd.com](https://www.amd.com/en/products/graphics/desktops/radeon/7000-series/amd-radeon-rx-7900xtx.html)).
- Nasza PULSE: Game Clock w VBIOS 2371 MHz (etykieta w `pp_dpm_sclk`), sufit OD 2885 MHz, domyślny PPT 303 W (`power1_cap_default`). Inny egzemplarz PULSE ma sufit 2930 przy boost 2525 według TechPowerUp ([drm/amd#3131](https://gitlab.freedesktop.org/drm/amd/-/issues/3131)).
- **Dlaczego siedzimy na 285 W przy ~2400–2436 MHz:**
  - Przy prefillu i dekodowaniu spekulatywnym (MTP) obciążenie jest tak duże, że ogranicznikiem jest moc. Widać to w `throttle_status` bit PPT0 (§1.8) i w logach: 278–288 W przy 2385–2463 MHz ([`~/qwen-opt/thermal/q63-stock.csv`](../../../qwen-opt/thermal/q63-stock.csv): 39 s pod obciążeniem ≥ 250 W).
  - Moc dynamiczna rośnie jak ~C·V²·f, a napięcie rośnie z częstotliwością po krzywej V/F. PMFW ustala się tam, gdzie P(f, V(f)) = 285 W [INFERENCE, standardowa fizyka DVFS].
- **Co zmienia limit `s 1 X`:**
  - Sterownik ustawia **tylko** `GfxclkFmax = X` i bit funkcji GFXCLK ([U-PPT#n1659](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1659)). Krzywej V/F nie edytuje; `vo` to osobne pole.
  - Firmware dobiera napięcie z własnej krzywej dla częstotliwości, na której faktycznie pracuje ([U-PM#n684](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n684)). Limit jest więc **czystą górną granicą DPM**, a niższa częstotliwość pociąga za sobą niższe napięcie.
  - Pomiar na innej 7900 XTX: limit 2200 → śr. 761 mV, 1800 → 695 mV, bez limitu → 841 mV ([szafranski, power-and-undervolt.md](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning/blob/main/docs/power-and-undervolt.md), surowe: [clock-cap-sweep.jsonl](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning/blob/main/data/clock-cap-sweep.jsonl)).
  - X ≥ ~2440: w stałym prefillu nic się nie zmienia, bo i tak rządzi PPT. Przycięte są tylko krótkie skoki (do 3079 MHz w naszym logu) [INFERENCE].
  - X < ~2440 (2400, 2200 …): PMFW musi zejść niżej, napięcie spada, moc spada poniżej 285 W, a wydajność na wat rośnie (§9).
  - Sterownik nie porównuje X z Game/Boost Clock. X poniżej Game Clock to po prostu niższy sufit, a etykieta w `pp_dpm_sclk` zostaje 2371 [INFERENCE z kodu: brak ścieżki odświeżającej `gfx_table` przy commicie, [U-PPT#n1900](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1900)].
- Niezależnie od OD firmware **zawsze** dławi przy hotspot 110 °C i mem 108 °C, a przy 115 / 113 °C wyłącza ASIC (`FW_CTF` włączone, §1.5). Limit zegara tego nie wyłącza.

---

## 3. Kod sterownika 6.8.0-138: co robią `s 1`, `c` i `r`

### 3.1 `s 1 X`
- Walidacja ([U-PPT#n1653](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1653)):
  - X musi mieścić się w `[OverDriveLimitsMin.GfxclkFmax, OverDriveLimitsBasicMax.GfxclkFmax]` = OD_RANGE 500..5000;
  - musi też być spełnione `GfxclkFmin ≤ GfxclkFmax`;
  - innego progu nie ma, więc 1200 jest legalne.
- Ustawia tylko `GfxclkFmax` i `FeatureCtrlMask |= GFXCLK_BIT` (bit 7, [IF L671-L677](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/inc/pmfw_if/smu13_driver_if_v13_0_0.h#L671-L677)).
- **Nic jeszcze nie idzie do firmware'u**: zmiana zostaje w kopii sterownika (pod `adev->pm.mutex`, [amdgpu_dpm.c v6.8 L1092-L1111](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/amdgpu_dpm.c#L1092-L1111)).
- Zapis w trakcie resetu lub suspendu zwraca `-EPERM` ([U-PM#n759](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n759)).

### 3.2 `c` – commit, czyli JEDNA tablica z krzywą wentylatora, i błąd maski
- Krzywa wentylatora, zegary, offset napięcia, PPT i ustawienia akustyczne to **jedna struktura `OverDriveTable_t`** o rozmiarze 140 B ([IF L695-L727](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/inc/pmfw_if/smu13_driver_if_v13_0_0.h#L695-L727)). Dotyczy to zarówno `pp_od_clk_voltage`, jak i `gpu_od/fan_ctrl/fan_curve` ([U-PM#n3627](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n3627)).
- Commit ([U-PPT#n1900](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1900)–n1931):
  1. porównuje (`memcmp`) tablicę roboczą z ostatnio wysłaną. **Jeśli nic się nie zmieniło, nic nie robi** ([#n1909](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1909)), a przygotowane bity maski zostają;
  2. w przeciwnym razie wysyła **całą** tablicę komunikatem `TransferTableDram2Smu` ([smu_cmn.c v6.8 L860-L900](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/smu_cmn.c#L860-L900)) z `FeatureCtrlMask` = bity edytowane od ostatniego wysłania;
  3. **zeruje maskę** ([#n1920](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1920));
  4. potem tylko `READJUST_POWER_STATE` ([U-PM#n825](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n825)), co może ponownie wysłać maskę profilu.
  - Commit **nie** przełącza GFXOFF, **nie** wyłącza ani nie przeładowuje DPM i **nie** robi resetu. Jedyne blokady to `pm.mutex` i `message_lock` SMU, nie blokady kolejek obliczeniowych.
- **Błąd (potwierdzony przez AMD, nienaprawiony w 6.8).** Commit [6027db7db773](https://github.com/torvalds/linux/commit/6027db7db773714f2e05df82093276f2a52a1fba) „drm/amd/pm: preserve committed OD features for SMU 13.0.0/13.0.7” (AMD, Closes [drm/amd#3625](https://gitlab.freedesktop.org/drm/amd/-/issues/3625), Cc: stable): *„PMFW treats FeatureCtrlMask as the complete set of active OD features. Uploads containing only newly edited bits can drop earlier settings.”*
  - Drugi commit [44d0d3031e47](https://github.com/torvalds/linux/commit/44d0d3031e47973ed65fd327669d5e2eaaf6c565): *„On import it resets every feature whose bit is clear back to its default value”*, a *„the driver's cached user table still reports the offset through pp_od_clk_voltage”*.
  - Na naszym jądrze oznacza to:
    - **A. `s 1 X` + `c` przy wyzerowanej masce** (normalny stan pod stałym obciążeniem: `fan.sh` nie pisze, gdy stan się nie zmienia, [`fan.sh:36-39`](../../../qwen-opt/tools/fan.sh)). Wysyłany jest tylko bit GFXCLK. Firmware **resetuje sterowanie wentylatorem do fabrycznego auto**, a `fan_curve` dalej pokazuje „25C 100%”. `fan.sh` porównuje tylko tekst z sysfs (`p0`, [`fan.sh:35-38`](../../../qwen-opt/tools/fan.sh)), więc **nie naprawi tego** aż do przejścia load→idle.
    - **B. Commit krzywej przez `fan.sh`** (przy każdej zmianie load↔idle i po resecie GPU) wysyła tylko bit FAN_CURVE. Firmware **zdejmuje limit zegara** (wraca 2885, ograniczone dalej przez 285 W), a `OD_SCLK` dalej pokazuje limit. Termicznie to bezpieczne (stan fabryczny), ale dane pomiarowe są wtedy fałszywe.
    - **C. Ponowienie identycznego commitu nie naprawia stanu**, bo memcmp pomija wysyłkę ([#3625 note_3706709](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_3706709)).
  - Reprodukcje na RDNA3 (szczegóły w §4): 7800 XT, 7900 GRE (Navi31, SMU 13.0.0), 7900 XTX Nitro+ i 7900 XT/XTX w CoreCtrl #460: „fan curve reverts to auto … while UI shows curve”.
  - Status poprawki:
    - jest w mainline **v7.4-rc1**;
    - nie ma jej w stable 7.3.y / 7.2.y / 6.18.y / 6.12.y / 6.6.y ([stable tree](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=linux-7.3.y));
    - nie ma jej w Ubuntu `6.8.0-138` ani w `6.8.0-149` (w pliku Ubuntu-138 jest 0 wystąpień `user_od_feature_mask`; sprawdziłem w pobranym pliku);
    - backport do 7.2.y „did not apply” ([#3625 note_3717956](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_3717956)).
- **Obejście na 6.8 (potwierdzone pomiarem w #3625):** przygotować **wszystkie** sekcje (5 punktów krzywej oraz `s 1 X`) i wysłać **jeden** `c`. Wtedy maska zawiera FAN_CURVE|GFXCLK i oba ustawienia działają ([#3625 note_3706709](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_3706709) „Workaround for users”, [note_2631479](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_2631479)). Tak robią LACT (przygotowuje wszystko, potem commituje) i amdgpu-clocks (jeden `c`) (§7).
- Wyścig z timerem: `s 1 X` i `c` to osobne zapisy. Commit timera między nimi zatwierdzi także przygotowane `s 1`. Wynik jest wtedy poprawny (oba bity), ale niedeterministyczny, więc potrzebny jest wspólny `flock` (§10).

### 3.3 `r`
- `r` w `pp_od_clk_voltage` kopiuje **całą** tablicę fabryczną, krzywą wentylatora też, i przez `fallthrough` **od razu ją wysyła**. Następujące `c` niczego już nie robi ([U-PPT#n1887](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n1887)).
  - Maska przy tym wysłaniu to bity przygotowane wcześniej (zwykle 0). Firmware wraca więc na fabryczne wszystko, wentylator także.
  - `fan.sh` tym razem wykryje zmianę, bo sysfs pokaże krzywą fabryczną, i ponownie zapisze krzywą w ≤ 1 s, jeśli pętla akurat działa. Przerwa między uruchomieniami usługi wynosi ~2 s (`ExecMainExit` 15:31:04 → następne wyzwolenie 15:31:06).
  - **Okno na fabrycznym auto trwa więc ~1–3 s, w najgorszym razie ~30 s** [INFERENCE z `systemctl show`]. Samo w sobie nie jest niebezpieczne (to fabryczna polityka), ale jest zbędne.
- `r` w `fan_ctrl/fan_curve` przywraca tylko sekcję wentylatora, ustawia `FanMode=AUTO` i commituje z samym FAN_CURVE, więc zgodnie z §3.2 B także zdejmuje limit sclk ([U-PM#n3596](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/amdgpu_pm.c?h=Ubuntu-6.8.0-138.138#n3596)).
- **Wniosek:** do zdjęcia limitu nie używać `r`, tylko „krzywa + `s 1 2885` + jeden `c`” (§10).

### 3.4 Reset GPU, suspend, restart
| zdarzenie | limit sclk + krzywa | limit mocy 285 W | źródło |
|---|---|---|---|
| restart / przeładowanie modułu | **utracone** (tablica z VBIOS) | wraca 303 W, `gpu-powercap.service` ustawia 285 | [U-PPT#n2195](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n2195) |
| **reset GPU (mode1)** | **utracone, a sysfs pokazuje stan fabryczny** (`in_suspend=false` → tablica użytkownika = fabryczna; `restore_dpm_user_profile` wychodzi wcześnie) | najpewniej zachowany (`smu_resume` w Ubuntu ponownie ustawia `current_power_limit`) [INFERENCE co do kolejności] | [U-DEV#n5451](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/amdgpu/amdgpu_device.c?h=Ubuntu-6.8.0-138.138#n5451), [U-SMU#n446](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c?h=Ubuntu-6.8.0-138.138#n446), [U-SMU#n2122](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c?h=Ubuntu-6.8.0-138.138#n2122) |
| S3/S4/runtime PM resume | zachowane i wysłane ze wszystkimi bitami (tylko 5 z 6 punktów krzywej) | zachowany | [U-PPT#n2239](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n2239) |

- Mainline (v6.15 i master) nadal **nie** przywraca OD po resecie GPU. Odtwarza tylko limity PPT ([master amdgpu_smu.c](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c)).
- Commity „restore user customized OD settings” z 2021 ([92cf050868c9](https://github.com/torvalds/linux/commit/92cf050868c962bc712b5682b8a0ed04d3dfec3d)) dotyczą SMU11 i wyłącznie resume.
- Po resecie limit sclk znika, czyli wraca bezpieczny stan fabryczny. Krzywą odtwarza nasz timer (sysfs pokazuje fabryczną, więc `p0` się nie zgadza). **Limitu sclk po resecie NIE przywracamy**: reset oznacza koniec testu (zasada [2026-10-19-bezpieczenstwo-sprzetu](../../wiki/decyzje/2026-10-19-bezpieczenstwo-sprzetu.md)).

### 3.5 Niezgodność wersji interfejsu (dmesg: „SMU driver if version not matched”, 0x3D vs 0x40)
- To tylko `dev_info` i nie blokuje działania ([smu_v13_0.c v6.8 L280-L296](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0.c#L280-L296)).
- Mainline do v6.15 nadal ma 0x3D ([v6.15 IF L27](https://github.com/torvalds/linux/blob/v6.15/drivers/gpu/drm/amd/pm/swsmu/inc/pmfw_if/smu13_driver_if_v13_0_0.h#L27)), a `OverDriveTable_t` jest bajtowo taki sam w v6.8, Ubuntu-138 i v6.15.
- AMD nie publikuje nagłówka 0x40, więc układu tablicy w firmware nie da się sprawdzić. Nasze zapisy krzywej działają fizycznie (3500 RPM, `pwm1=255`), a `GfxclkFmax` (offset 22) leży przed polami wentylatora (offset 32+). Układ jest najpewniej zgodny [INFERENCE].

---

## 4. Znane incydenty i zgłoszenia (szukane: drm/amd, amd-gfx, LACT, CoreCtrl, ROCm, Reddit, L1T, Phoronix)

| # | Karta / jądro | Co się stało | Dotyczy nas? | Źródło |
|---|---|---|---|---|
| 1 | 7800 XT, 7.2.9 | fan curve + `c`, potem `vo`/`s` + `c` → **krzywa porzucona**, wentylator ~1200 RPM (cel akustyczny), sysfs dalej pokazuje krzywą; odwrotna kolejność → zegar/offset porzucone (2569→2245 MHz); ponowienie nie pomaga; jeden wspólny `c` działa | **tak** (ten sam kod 13.0.x, ten sam commit naprawczy obejmuje 13.0.0) | [#3625 note_3706709](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_3706709) |
| 2 | **7900 GRE (Navi31, SMU 13.0.0)**, 6.11 | `s 1 2000; c`, potem `power1_cap` powyżej domyślnego → limit zegara ignorowany, choć sysfs pokazuje 2000 | tak, jeśli PPT > 303 W (nie robimy tego) | [#3625 note_2631467](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_2631467) |
| 3 | **7900 XTX Nitro+**, 6.10 | trzeba nakładać ustawienia 2–3×, żeby wszystkie zadziałały | tak | [#3625 note_2564513](https://gitlab.freedesktop.org/drm/amd/-/issues/3625#note_2564513) |
| 4 | Navi31 | zapis `fan_curve` / `fan_minimum_pwm` / `fan_target_temperature` „often results in the custom clock being completely ignored” | tak | [#3131 note_2449987](https://gitlab.freedesktop.org/drm/amd/-/issues/3131#note_2449987), [#3131 note_2415553](https://gitlab.freedesktop.org/drm/amd/-/issues/3131#note_2415553) |
| 5 | 7900 XTX Nitro+ Vapor-X, 6.10 | zapis `acoustic_*`/`fan_minimum_pwm`/`fan_target_temperature` → wszystko z `pp_od_clk_voltage` ignorowane | tak (to nasza pułapka akustyczna z 18.10) | [LACT#329](https://github.com/ilya-zlobintsev/LACT/issues/329#issuecomment-2165977129) |
| 6 | 7900 XT/XTX, CoreCtrl | profil: krzywa wentylatora wraca na auto (~2500→1600 RPM), UI pokazuje krzywą | tak | [CoreCtrl#460](https://gitlab.com/corectrl/corectrl/-/work_items/460), [CoreCtrl Known issues](https://gitlab.com/corectrl/corectrl/-/wikis/Known-issues) |
| 7 | 7900 XTX Nitro+, 6.7 | PPT 402 W, potem `s 1 3050; c` → PPT spada do ~350 W | nie (nie podnosimy PPT) | [#2356 note_2250693](https://gitlab.freedesktop.org/drm/amd/-/issues/2356#note_2250693) |
| 8 | 7900 XTX (PULSE!) 6.7 | crashe w grach przy fabrycznym sufitcie 2930 MHz; **obniżenie max sclk pomaga** (Gentoo wiki) | obniżanie to kierunek stabilizujący | [#3131](https://gitlab.freedesktop.org/drm/amd/-/issues/3131), [Gentoo AMDGPU](https://wiki.gentoo.org/wiki/AMDGPU) |
| 9 | LACT #452 „target clock” | RDNA3 przypięte do ~game clock przy `manual` + ponownie nakładanych p-states; **błąd LACT 0.7.0**, naprawiony w ff55dc7; nie dotyczy bezpośredniego sysfs | nie | [LACT#452](https://github.com/ilya-zlobintsev/LACT/issues/452#issuecomment-2606421831), [fix](https://github.com/ilya-zlobintsev/LACT/commit/ff55dc7634d40dfb1d15d2b8c7908e201b98b641) |
| 10 | 7900 XTX, 6.16 | `power_dpm_force_performance_level=high` + OD → twarde zawieszenie i reboot; limit 2950→2450 w `auto` stabilny | trzymać `auto` | [LACT#707](https://github.com/ilya-zlobintsev/LACT/issues/707) |
| 11 | RDNA3 | zapis `m` (zegar pamięci) → crash lub migotanie, potem hang (DCN3.2) | nie ruszamy `m` | [LACT#520](https://github.com/ilya-zlobintsev/LACT/issues/520), [amd-gfx 2026-11](https://www.mail-archive.com/amd-gfx@lists.freedesktop.org/msg153956.html) |
| 12 | 7900 XTX, LACT 0.8.5 | max clock kasował `vo` i odwrotnie; **regresja LACT**, nie sterownika | nie | [LACT#925](https://github.com/ilya-zlobintsev/LACT/issues/925) |
| 13 | 7900 XTX, llama.cpp Vulkan | sweep limitu 2400/2200/2000/1800 MHz: **0 komunikatów amdgpu na krok**, 30 min soaku przy 2200 bez błędów, perplexity bez zmian | bardzo zbliżone (ten sam model Qwen3.8-27B) | [szafranski](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning/blob/main/docs/power-and-undervolt.md) |

- **Hangi, timeouty ringu, mode1, błędy SMU po obniżeniu OD_SCLK na Navi31:** nie znalazłem żadnego zgłoszenia. Trafienia „SMU: I'm not done with your previous command” dotyczą iGPU i MODE2 ([Arch BBS](https://bbs.archlinux.org/viewtopic.php?id=310517)). Brak zgłoszeń nie jest dowodem, ale mechanizm (górna granica DPM) jest najprostszą zmianą OD.
- **Trwałe uszkodzenia:** brak jakichkolwiek zgłoszeń po obniżeniu zegara. Udokumentowane uszkodzenia termiczne 7900 XTX to wada komory parowej **kart referencyjnych MBA** ([Tom's Hardware](https://www.tomshardware.com/news/amd-faulty-thermal-solution-7900-xtx-throttling), [igor'sLAB](https://www.igorslab.de/en/amd-radeon-rx-7900xtx-reference-cards-mba-and-the-hotspot-multiple-batches-of-vapor-chamber-affected-the-replacement-begins/)). Nasza PULSE ma własny cooler Sapphire (`1da2:471e`, `pci.ids`), a nie MBA.
- Szczegółowe notatki z badań (tymczasowe): notatki sesji `64-incidents.md`, `64-kernel-od.md`, `64-tools-dpm.md`, `64-perf-watt.md`. Najważniejsze fakty z nich są w tym raporcie.

---

## 5. Nasza historia

- **2026-10-18 23:25: reset mode1** (awaria taśmy PM4, raport 17) **wyzerował krzywą OD** ([17-gpu-page-fault.md:22](17-gpu-page-fault.md), [lekcja-wentylator-rdna3](../../wiki/lekcje/lekcja-wentylator-rdna3.md)). Zgadza się to z kodem z §3.4: po resecie tablica jest fabryczna.
- **Pułapka akustyczna**: zapis `acoustic_target` po krzywej przełączył SMU13 w tryb auto. Wentylator stał na ~1800 RPM przy pamięci 88–90 °C ([lekcja](../../wiki/lekcje/lekcja-wentylator-rdna3.md)). To ten sam mechanizm co §3.2 i zgłoszenie #5 w §4 (`FanMode=AUTO` + maska).
  - Dzisiejszy draft `xtx-eco sclk` wywołałby **tę samą pułapkę inną drogą**: tylko bit GFXCLK, więc firmware przechodzi na fabryczne auto (§3.2 A).
- **`fan.sh`** ([`~/qwen-opt/tools/fan.sh`](../../../qwen-opt/tools/fan.sh)) pisze tylko krzywą (słusznie). Pod obciążeniem `ensure()` nic nie zapisuje, dopóki tekst sysfs się zgadza (l. 36-39), więc **nie wykryje utraty krzywej w firmware** (§3.2). Przy `r` wykryje, bo sysfs pokazuje krzywą fabryczną. Okno na auto wynosi ~1–3 s, maksymalnie ~30 s (§3.3).
- **Timer i obciążenie PM4:** od 2026-10-20 (początek dziennika) `xtx-fan` zrobił **426 commitów tablicy OD** (213 × load, 213 × idle, `journalctl -t xtx-fan`), także podczas produkcji z taśmami PM4. W `journalctl -k` dla bootów −9…0 **nie ma ani jednego „GPU reset begin”**. Trafienia w bootach −7/−6 to page faulty z 2026-10-21 opisane w [lekcja-nie-zabijaj-pm4-w-trakcie](../../wiki/lekcje/lekcja-nie-zabijaj-pm4-w-trakcie.md) (przyczyną był `exit()` w handlerze sygnału, nie SMU). Ta sama ścieżka `TransferTableDram2Smu` pod obciążeniem obliczeniowym ma więc u nas setki bezproblemowych wywołań.
- **`gpu-guard.sh`** ([`~/qwen-opt/tools/gpu-guard.sh`](../../../qwen-opt/tools/gpu-guard.sh)):
  - **nie reaguje na zmiany OD ani zegara**;
  - reaguje na log jądra (page fault, timeout ringu, reset, MES) i temperatury: hotspot ≥ 100, VRAM ≥ 98, wentylator < 2500 RPM przy busy ≥ 50% i hotspot ≥ 80 lub VRAM ≥ 82 °C przez 20 s;
  - utratę krzywej złapie dopiero, gdy będzie gorąco, a wtedy zabija serwery (oprócz :8080) sygnałem TERM, a po 3 s KILL;
  - dla buildów bez `pm4-teardown` to ryzyko page faultu przy zabijaniu w trakcie taśmy ([lekcja](../../wiki/lekcje/lekcja-nie-zabijaj-pm4-w-trakcie.md)).
  - Realny łańcuch awarii z draftem [INFERENCE]: `s 1` → firmware zdejmuje krzywą → ~1800 RPM → VRAM ≥ 82 °C → guard zabija serwer sweepu → możliwy fault PM4 lub reset.
- **Termika wtedy i teraz:**
  - 2026-10-09 (fabryczny wentylator ~2970 RPM, prefill 196k, 281 W): edge 66, junction **106**, VRAM 76 °C, różnica ~40 °C ([`~/KERNEL/qwen-opt/NOTES.md:118-120`](../../qwen-opt/NOTES.md)).
  - Przy 285 W i ~1850 RPM: junction 85–88 (max 90), edge 64–67 (NOTES:146, 170).
  - 2026-10-18 przy wentylatorze ~3410 RPM: 252–295 W, edge 53–58, junction 72–80, mem 76–78, **różnica mediana 21, max 24 °C** ([`sweep-gpu.csv`](../../../qwen-opt/logs/sweep-gpu.csv)).
  - **Dziś** przy 3500 RPM, 278–288 W: edge 47–50, junction 63–68, mem 70–74, **różnica 15–18 °C** ([`q63-stock.csv`](../../../qwen-opt/thermal/q63-stock.csv)); na żywo 15:31: 283 W, edge 49, hotspot 66, mem 72, `pwm1` 255.
  - Wniosek w §13.

---

## 6. Interakcja z replayem PM4

- Zegarami steruje SMU/PMFW (osobny mikrokontroler MP1). Taśmy PM4 wykonuje CP/MES. Commit OD to jeden komunikat do SMU ([smu_cmn.c](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/pm/swsmu/smu_cmn.c#L860-L900)), bez GFXOFF i bez resetu (§3.2). Zmiany częstotliwości w trakcie taśmy i tak zachodzą bez przerwy: na żywo sclk skacze 18 → 2406 MHz w 1 s (§1.7, próbka 15:31:15–16).
- Niższy zegar wydłuża taśmę proporcjonalnie. Krok dekodowania trwa ~28–30 ms ([pm4-replay](../../wiki/kernele/pm4-replay.md)), a limit czasu taśmy to 10 s ([lekcja-timeout-tasmy-to-skutek](../../wiki/lekcje/lekcja-timeout-tasmy-to-skutek.md)). Nawet przy 1200 MHz (×2) zostaje ponad 100× zapasu.
- Hipotezy awarii PM4 z raportu 17 (wywłaszczenie kolejki, PRIV, ewikcja SVM) nie mają związku z DPM. Termikę jako przyczynę wykluczono już wtedy ([17-gpu-page-fault.md:127](17-gpu-page-fault.md)).
- Jedyne realne ryzyko PM4 przy tym teście to **sposób zatrzymywania serwera** (jeden SIGTERM przy bezczynności, `sweep.sh:18-24` robi to dobrze) i **zabicie przez guard** (§5). Nie samo DPM.

---

## 7. Jak robią to narzędzia

- **LACT** ([amd.rs L1129-L1417 @ d11618a](https://github.com/ilya-zlobintsev/LACT/blob/d11618abe13f121a1298f01575d6ce5c0c9ba3b1/lact-daemon/src/server/gpu_controller/amd.rs#L1129-L1417)):
  - przełącza poziom na `manual` i pisze `r`, potem przygotowuje `s/m/vo`, punkty krzywej, opcje akustyczne i limit mocy, na końcu wysyła wszystkie commity: najpierw wentylator, zegary na końcu ([amdgpu-sysfs-rs mod.rs L840-L855](https://github.com/ilya-zlobintsev/amdgpu-sysfs-rs/blob/da58cda74a514a259f81b7b42e8652c58c22b33b/src/gpu_handle/mod.rs#L840-L855));
  - pierwszy `c` niesie wszystkie bity, więc to de facto obejście, któremu CoreCtrl przypisuje sukces ([Known issues](https://gitlab.com/corectrl/corectrl/-/wikis/Known-issues));
  - nakłada ustawienia ponownie po resume i po uevencie `drm`;
  - na 6.8 reset GPU nie wysyła ueventu (uevent „wedged” doszedł w 2025, [6fe52b63f569](https://github.com/torvalds/linux/commit/6fe52b63f569)), więc LACT reset najpewniej przeoczy [INFERENCE];
  - pułapki: #452, #925 (błędy LACT), `manual` z profilami.
- **CoreCtrl**: sam autor oficjalnie uznaje OD na RX 7000 za „completely broken at the driver/firmware level” i odsyła do LACT ([Known issues](https://gitlab.com/corectrl/corectrl/-/wikis/Known-issues)).
- **amdgpu-clocks** ([skrypt L235-L300](https://github.com/sibradzic/amdgpu-clocks/blob/906127368b371b0cd0fa1328ca4cb4c50dbf3b7a/amdgpu-clocks#L235-L300)):
  - wysyła wszystkie `s/m/vo` i **jeden** `c`;
  - przywraca, zapisując zapamiętane wartości z powrotem (nie przez `r`);
  - unit systemd `oneshot` z `ExecStop=restore` i hakiem `system-sleep` po resume;
  - po resecie GPU nic nie robi;
  - punktów `fan_curve` nie dotyka.
- **Windows Adrenalin „Max Frequency”**:
  - [INFERENCE] zapisuje tę samą strukturę PMFW `OverDriveTable_t`, bo to jedyny interfejs OD firmware'u (IF), a sterownik Linux celowo wyrównał raportowane zegary do „Window setting” ([U-PPT#n606](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n606));
  - AMD opisuje suwak napięcia jako „an offset to the entire voltage-frequency curve” ([AMD DH3-020](https://www.amd.com/en/resources/support-articles/faqs/DH3-020.html));
  - nie znalazłem źródła pierwotnego potwierdzającego popularną tezę, że „Max Frequency to tylko miękki cel”;
  - na Linuksie średnia z pomiaru pod limitem wypada 10–70 MHz **poniżej** limitu (szafranski), a pojedyncze próbki mogą go przekraczać (nasz log, §1.2).

---

## 8. Trwałość, natychmiastowy rollback, restart

- Nic z OD nie przetrwa restartu: po załadowaniu modułu tablica jest fabryczna. **Restart to zawsze pewny powrót do stanu fabrycznego** (sufit 2885, wentylator auto). Potem `gpu-powercap.service` ustawia 285 W, a `xtx-fan.timer` po 20 s krzywą.
- Po **resecie GPU** limit sclk znika (bezpieczny kierunek), krzywą przywraca timer, a limit mocy najpewniej zostaje (§3.4).
- **Natychmiastowy rollback limitu (bez `r`):** w jednym `flock`-u zapisać 5 punktów bieżącej krzywej, potem `s 1 2885`, potem jeden `c`, i sprawdzić fizycznie (§10). `r` też działa natychmiast, ale na chwilę zdejmuje krzywą wentylatora (§3.3).
- Awaryjnie, gdy stan jest niepewny: zatrzymać obciążenie (jeden SIGTERM przy bezczynności serwera). Bez obciążenia limit zegara i wentylator nie mają znaczenia. Ostatecznością jest restart.

---

## 9. Czego się spodziewać: W vs MHz vs t/s

**Pomiar najbliższy naszemu** (7900 XTX, Qwen3.8-27B, llama.cpp **Vulkan/RADV**, a nie ROCm, PPT 272 W, limit przez `pp_od_clk_voltage`) ([szafranski: power-and-undervolt.md](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning/blob/main/docs/power-and-undervolt.md), [clock-cap-sweep.jsonl](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning/blob/main/data/clock-cap-sweep.jsonl)):

| limit sclk | realny sclk | mV | prefill t/s (19k tok.) | moc prefill | perf/W prefill | decode t/s (spekulatywny) | moc decode | J/token decode |
|---|---|---|---|---|---|---|---|---|
| bez (3045) | 2417 | 841 | 688 (100%) | 267 W | 100% | 58.25 | 271.8 W | 4.666 |
| 2400 | 2328 | 809 | 662 (96%) | 241 W | 107% | 58.01 (99.6%) | 266.6 | 4.596 |
| 2200 | 2166 | 761 | 620 (90%) | 208 W | 116% | 56.47 (96.9%) | 246.4 | 4.364 |
| 2000 | 1972 | 713 | 566 (82%) | 180 W | 122% | 54.08 (92.8%) | 223.6 | 4.134 |
| 1800 | 1790 | 695 | 518 (75%) | 164 W | 123% | 51.14 (87.8%) | 211.4 | 4.133 |

- Prefill skaluje się prawie 1:1 z rzeczywistym zegarem, bo jest ograniczony obliczeniami. Około 1800 MHz napięcie dochodzi do podłogi ~695 mV, **więc poniżej ~1900–2000 MHz sprawność przestaje rosnąć** (2000 → 1800: +0.6%).
- Dekodowanie spekulatywne też siedzi na limicie mocy: u nich i u nas (MTP, §1.8 bit PPT0 przy dekodowaniu q63), więc traci 3–12%.
- Czysty dekod (bez spekulacji) jest ograniczony pasmem pamięci. Dane z NVIDIA: RTX 3090 bez spadku do ~70% mocy i −18% zegara rdzenia, potem gwałtowny spadek przy 480 MHz ([jeanfbrito](https://jeanfbrito.github.io/posts/rtx-3090-power-limit-sweet-spot/)). 6×3090: prefill 85/60/26% przy 250/200/150 W, dekod 97/94/86% ([llmgarage](https://llmgarage.ai/power-limit-tokens-per-second-benchmark)).
- Limit mocy na tej samej 7900 XTX: 303 → 272 W daje −2.2% t/s, −9.9% W i −8 °C (szafranski).
- Wpływ na undervolt: przy limicie 2200 offset poniżej −100 mV jest po cichu przycinany (VDDGFX 715 → 705 mV dla −75 → −200 mV), a sysfs i tak pokazuje żądaną wartość (szafranski). Undervolt i limit zegara się nie sumują.

**Prognoza dla nas** [INFERENCE] (ROCm, 285 W, prefill ~2436 MHz; proporcje z tabeli powyżej):

| limit | realny sclk | prefill | moc prefill | dekod MTP | temperatury |
|---|---|---|---|---|---|
| bez (2885) | ~2436 | 100% | ~285 W | 100% | hotspot ~66, mem ~72 (dziś) |
| 2400 | ~2340–2370 | ~96–97% | ~255–260 W | ~99–100% | −3…−5 °C |
| 2200 | ~2170 | ~89–90% | ~220–225 W | ~97% | −8…−10 °C |
| 2000 | ~1975 | ~81–82% | ~190–195 W | ~93% | −12…−15 °C |
| 1800 | ~1790 | ~74% | ~170–175 W | ~88% | −15 °C |
| 1600 | ~1590 | ~65% | ~150–155 W (ekstrapolacja) | ~80–85% | bez zysku sprawności |
| 1200 | ~1190 | ~49% | ~115–125 W | ryzyko spadku dekodu | bez sensu |

Optimum sprawności leży w **2000–2200 MHz**. Poniżej 1800 jest tylko chłodniej, a nie oszczędniej.

---

## 10. Konkretne poprawki (do wdrożenia przez Main/użytkownika; tu tylko opis)

### 10.1 Zasada nadrzędna na jądrze 6.8: JEDEN zapisujący, JEDEN commit, wszystkie sekcje
Wdrożone jako pliki w §12. W implementacji funkcja nazywa się `xtx_apply`, stan to `/run/xtx-eco/cap`, a blokada `/run/lock/xtx-od.lock`; odmowa commitu dotyczy faultów i resetów w całym bieżącym boocie. Szkic poniżej opisuje zasadę.

Wspólna funkcja (np. w `fan.sh` albo osobnym `/usr/local/sbin/xtx-od`), wywoływana **wyłącznie pod `flock /run/xtx-od.lock`**, zarówno przez timer wentylatora, jak i przez `xtx-eco`:
```bash
od_apply() {   # $1 = load|idle ; cap from /run/xtx-eco.sclk (missing = stock 2885)
  local cap; cap=$(cat /run/xtx-eco.sclk 2>/dev/null || echo 2885)
  write_5_points "$1"                          # all 5 fan_curve points -> FAN_CURVE bit + FAN_MODE_MANUAL_LINEAR
  echo "s 1 $cap" > $dev/pp_od_clk_voltage     # GFXCLK bit (stock 2885 too)
  echo c > $od/fan_curve                       # ONE commit: mask = FAN_CURVE|GFXCLK
}
```
- `fan.sh set_curve` → `od_apply` (dzięki temu przejście load↔idle nie zdejmuje już limitu; §3.2 B).
- `xtx-eco sclk M` → zapis `M` do `/run/xtx-eco.sclk`, potem `od_apply load` (dzięki temu limit nie zdejmuje już krzywej; §3.2 A).
- **Wymuszenie wysłania przy naprawie:** identyczna tablica nie zostanie wysłana (§3.2 C). Po wykryciu rozjazdu zmienić punkt 0 krzywej o 1 °C (25 ↔ 26 °C), co jest nieszkodliwe, i ponowić `od_apply`. `p0()` w `fan.sh` musi akceptować 25C i 26C.
- **Nigdy** nie pisać `acoustic_*`, `fan_minimum_pwm`, `fan_target_temperature`, `m`, `vo` ani `r` (§3.2, §4 #5, #11).

### 10.2 `xtx-eco` (draft [`~/qwen-opt/thermal/xtx-eco`](../../../qwen-opt/thermal/xtx-eco))
| linia | dziś | zmiana |
|---|---|---|
| 22 | zakres 1200..2885 | **1600..2885** (poniżej ~1800 nie ma zysku sprawności, §9; 1200 nic nie daje); `2885` jako twardy sufit zostaje, bo chroni przed literówką typu `4000` |
| 23 | `echo "s 1 $m"; echo c` | `od_apply` z §10.1 pod `flock`, potem **weryfikacja z §10.4**; przy błędzie: `stock` i `exit 3` |
| 24-26 | `profile N` ustawia `manual` | **usunąć**: `manual` wyłącza automatyczny profil COMPUTE z KFD ([U-SMU#n2335](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c?h=Ubuntu-6.8.0-138.138#n2335)); jest też raport hangu z poziomem innym niż `auto` + OD ([LACT#707](https://github.com/ilya-zlobintsev/LACT/issues/707)) |
| 28 | `reset`: `r` + `c` + `auto` + 285 W | zamienić na `stock`: `rm /run/xtx-eco.sclk; od_apply load`, czyli krzywa + `s 1 2885` + jeden `c`; **bez `r`**; zapis 285 W jest zbędny, ale nieszkodliwy (≤ 303 W idzie zwykłym komunikatem SMU, [U-PPT#n3031](https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/noble/tree/drivers/gpu/drm/amd/pm/swsmu/smu13/smu_v13_0_0_ppt.c?h=Ubuntu-6.8.0-138.138#n3031)), więc usunąć dla prostoty |
| nowe | — | **odmowa commitu, gdy GPU ma problem**: jeśli `journalctl -k --since "$(cat /run/xtx-eco.since)"` zawiera `amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES)` → nie commitować, tylko `stock`, `exit 3` |
| 12-16 `status` | odczyt OD | dopisać `pwm1`, `in0_input`, medianę sclk z 5 s i ostrzeżenie „OD readback = pamięć sterownika, nie firmware” |

### 10.3 `sweep.sh` (draft [`~/qwen-opt/thermal/sweep.sh`](../../../qwen-opt/thermal/sweep.sh))
- **l. 15 i 25:** `eco reset` → `eco stock` (bez `r`).
- **l. 14:** dodać warunek startu: `gpu-guard.sh` działa (`pgrep -f gpu-guard.sh`), w `journalctl -k` od startu bootu nie ma resetu, `fan.sh` jest w nowej wersji z §10.1. Inaczej `exit 2`.
- **l. 35** (po każdej zmianie ramienia): po 30 s soaku sprawdzenie fizyczne z §10.4 i drugie na końcu okna pomiaru. Kolumny `cap_ok,fan_ok` w `results.csv`. Przy porażce: jedna próba naprawy (wymuszone wysłanie, §10.1), a jeśli nie pomoże, `eco stock`, ramię oznaczone jako nieważne i **koniec sweepu**, bez powtarzania.
- **Kolejność ramion:** `stock 2400 2200 2000 1800 2000 2400 stock` (kroki ≤ 200–400 MHz, symetrycznie, żeby odróżnić efekt od dryfu). 1600 tylko jako opcjonalny ogon, gdy 1800 się sprawdzi; **bez 1200**.
- **`tlog.sh`:** dopisać `pwm1`, `in0_input` (mV), `gpu_busy_percent` i `throttle_status` z `gpu_metrics`. Zamiast twardego `hwmon2` użyć `$d/hwmon/hwmon*`, bo numer hwmon może się zmienić po restarcie.
- **J/token:** liczyć osobno dla okna dekodowania i okna prefillu. Dziś `tel` uśrednia W z obu okien (l. 46-47), a dzieli tylko przez t/s dekodowania.
- **Zatrzymanie:** zostaje jeden SIGTERM przy bezczynności (l. 18-24); to zgodne z [lekcja-nie-zabijaj-pm4-w-trakcie](../../wiki/lekcje/lekcja-nie-zabijaj-pm4-w-trakcie.md).

### 10.4 Weryfikacja fizyczna (nie ufać tekstowi sysfs)
Pod stałym obciążeniem (busy ≥ 90% przez ≥ 10 s):
- **Limit działa:** mediana `pp_dpm_sclk *` z 10 s ≤ cap + 50 MHz (u szafranskiego śr. 10–70 MHz poniżej limitu), a `power1_average` spada zgodnie z §9. Dla cap < 2400: moc < 270 W.
- **Krzywa działa:** jeśli `fan1_input` > 0, to `pwm1` ≥ 240 i `fan1_input` ≥ 3200 RPM (dziś 255 / 3514–3545). Jeśli `fan1_input` = 0, to hotspot < 70 °C (zero-RPM). W przeciwnym razie krzywa została porzucona.
- **Sanity sterownika:** `OD_SCLK 1:` = cap i punkt 0 `fan_curve` zgodny ze stanem. To warunek konieczny, ale niewystarczający.

### 10.5 `gpu-guard.sh`
- Dodać **ostrzeżenie** (bez zabijania): `pwm1` < 230 przy `fan1_input` > 0 i busy ≥ 50% przez 20 s, czyli „krzywa porzucona”. Tego dziś nie widzi, dopóki karta nie jest gorąca.
- Na pierwsze ostrzeżenie sweep reaguje sam przez `eco stock`.

---

## 11. Bezpieczny protokół testu

0. **Przed:** wdrożone §10.1–10.5; `gpu-guard` działa; `journalctl -k -b 0` bez resetów i faultów; zanotowany stan bazowy: `pp_od_clk_voltage`, `fan_curve`, `power1_cap`=285, `pwm1`/RPM/`in0` pod obciążeniem przy stock (dziś: 255 / ~3520 / ~860 mV). GPU wolne (kolejka), serwer sweepu na osobnym porcie, nie :8080.
1. **Test samego mechanizmu (5 min, krótki serwer):** stock → `xtx-eco sclk 2400` → sprawdzenie §10.4 po 30 s → `xtx-eco stock` → §10.4. Potem **celowo** przejście load→idle→load (20 s bez obciążenia) przy limicie 2400 i sprawdzenie, czy po `od_apply` z timera limit **i** krzywa nadal działają. To bezpośredni test błędu z §3.2 na naszej karcie. Jeśli którakolwiek kontrola nie przejdzie: stop, raport, żadnego sweepu.
2. **Sweep:** `stock 2400 2200 2000 1800 2000 2400 stock`, soak 360 s na ramię, kontrole po 30 s i na końcu każdego ramienia.
3. **Warunki natychmiastowego stopu** (`eco stock`, jeden SIGTERM przy bezczynności, koniec): każdy wpis amdgpu w `journalctl -k` (page fault, timeout ringu, reset, MES, „Failed to upload overdrive table”), nieudana kontrola §10.4 po jednej naprawie, hotspot ≥ 90 °C, VRAM ≥ 85 °C, różnica hotspot−edge ≥ 35 °C.
4. **Po:** `xtx-eco stock` + kontrola §10.4 przy stock; `OD_SCLK 1: 2885`; `pwm1` 255 pod obciążeniem. W razie jakiejkolwiek niepewności restart przywraca wszystko (§8).

---

## 12. Wdrożenie (2026-11-05: tylko pliki, nic nie zainstalowane ani uruchomione)

Pliki w `~/qwen-opt/thermal/` (poza repo). Wszystkie przeszły `bash -n` i ShellCheck 0.10.0 (zostały tylko świadome SC2015 `a && b || fail`). Logikę `xtx_verify` i `xtx_cap` oraz kolejność zapisów `xtx_apply` sprawdziłem na atrapach plików w `/tmp` (bez sysfs).

| plik | rola |
|---|---|
| `xtx-od.sh` → `/usr/local/lib/xtx-od.sh` | **jedyny zapisujący OD**: `xtx_apply load\|idle [force]` pod `flock /run/lock/xtx-od.lock`; 5 punktów krzywej + `s 1 <cap>` + **jeden** `c` (§10.1); readback sterownika; `force` przełącza punkt 0 między 25 a 26 °C, żeby wymusić wysłanie (§3.2 C); `xtx_verify` = kontrola fizyczna z §10.4 (≥ 10 próbek przy busy ≥ 90%, mediana sclk ≤ cap + 50, ostatnie 5 próbek: `pwm1` ≥ 240 i ≥ 3200 RPM albo 0 RPM przy hotspot < 70 °C); limit trzymany w `/run/xtx-eco/cap` (tmpfs, więc restart = stock) |
| `xtx-eco` → `/usr/local/sbin/xtx-eco` | `status`, `sclk 1600..2885`, `stock` (bez `r`), `verify`; po nieudanej kontroli jedno wymuszone wysłanie, potem `stock` i exit 3; brak kontroli przy braku obciążenia = exit 4; odmawia ustawienia limitu po jakimkolwiek faultcie lub resecie amdgpu w tym boocie; bez `profile`, `manual`, PPT i `r` |
| `fan.sh.new` → `/usr/local/sbin/xtx-fan` | dotychczasowy `fan.sh` (te same krzywe i progi), ale każdy commit przez `xtx_apply` z bieżącym limitem; `p0` akceptuje 25 i 26 °C; nowe: przy obciążeniu, jeśli wentylator kręci się z `pwm1` < 230 przez 10 s, jedno wymuszone wysłanie na przebieg; `auto` = pełny `r` (zegar + wentylator). Różnice: `fan.sh.diff` (względem zainstalowanego `~/qwen-opt/tools/fan.sh`, który zostaje nietknięty) |
| `sweep.sh` | ramiona `stock 2400 2200 2000 1800 2000 2400 stock`; warunki startu: nowy `xtx-fan`, `bugcheck.PASS`, brak faultów w boocie; uruchamia `gpu-guard`, jeśli go nie ma; po każdej zmianie limitu `xtx-eco verify` po 30 s i na końcu soaku; `journalctl -k` co 10 s i po każdym ramieniu; hotspot ≥ 90 / VRAM ≥ 85 °C → abort; abort = obciążenie off → `stock` → jeden SIGTERM; W i J/token osobno dla dekodowania i prefillu |
| `bugcheck.sh` (+ `bugcheck.jobs`) | ~5 min, test §11 krok 1 na naszej karcie: stock (mediana ≥ 2300, czyli test rozróżnia), A: `sclk 2200` pod obciążeniem → wentylator dalej 100%, B: 30 s bezczynności → commity timera idle i load z limitem 2200 → limit dalej działa, A2: `sclk 2000`, C: `stock` → mediana ≥ 2300; naprawa w trakcie = FAIL; wynik w `bugcheck.PASS` / `bugcheck.FAIL` |
| `INSTALL.sh` (sudo, raz) | backup do `/var/backups/xtx-eco/<czas>/`, instalacja trzech plików root:root, `tmpfiles.d` + `/run/xtx-eco`, reguła sudoers tylko dla `/usr/local/sbin/xtx-eco` (`visudo -cf` i `visudo -c`), `xtx-fan.service` przestawiony na `/usr/local/sbin/xtx-fan` (timer bez zmian), walidacja `xtx-eco status`; nie pisze do GPU |
| `UNINSTALL.sh` (= `/usr/local/sbin/xtx-eco-uninstall`) | `xtx-eco stock`, przywrócenie najstarszego backupu (stan sprzed instalacji; fallback: dawny unit z `~/qwen-opt/tools/fan.sh`), usunięcie plików i reguły sudoers, `visudo -c`, restart usługi wentylatora |

Kolejność dla użytkownika: `sudo ~/qwen-opt/thermal/INSTALL.sh` → `run-jobs.sh ~/qwen-opt/thermal/bugcheck.jobs` → (tylko przy PASS) `run-jobs.sh ~/qwen-opt/thermal/eco.jobs`. `go.sh` zostaje wyłączony.

## 13. Termika niezależnie od limitu – czy potrzebny repaste?

- Dziś przy 100% wentylatora i 285 W różnica hotspot−edge wynosi **15–18 °C** (q63-stock, na żywo 15:31), a 2026-10-18 maksymalnie 24 °C. To w normie: zdrowa karta referencyjna ma Δ13 °C ([TechSpot](https://www.techspot.com/news/97120-amd-aware-radeon-rx-7900-xtx-temperature-issues.html)); XTX w LLM przy 303 W ma Δ21, a przy długim prefillu Δ≈22 ([victoralcazardev](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/docs/measurements/thermals-power.md)); ≥ 30–40 °C to sygnał problemu z kontaktem lub komorą ([HotHardware](https://hothardware.com/news/overclocker-pinpoints-radeon-rx-7900-xtx-temperature-delta-flaw)).
- 106 °C i Δ40 z 2026-10-09 to jedyny taki pomiar. Była wtedy fabryczna krzywa i ~2970 RPM. Z wentylatorem 100% tego obciążenia (prefill 196k) **jeszcze nie powtórzyliśmy**.
- Długie prefille na innej XTX przy 303 W dochodziły do hotspotu 100–106 °C (victoralcazardev), więc wysoki hotspot przy bardzo długim prefillu nie musi oznaczać wady. Δ40 jest jednak wyraźnie powyżej tamtych Δ≈22 [INFERENCE].
- **Rekomendacja:** repaste nie teraz. W protokole (przy stock, wentylator 100%, `gpu-guard` aktywny) jeden kontrolowany prefill ≥ 100k–196k tokenów przez ≥ 5 min z logiem Δ:
  - Δ ≤ 25 °C i hotspot ≤ 90 °C → sprawa zamknięta;
  - Δ ≥ 35 °C albo Δ rosnąca bez stabilizacji → oględziny docisku i pasty (karta Sapphire: najpierw sprawdzić warunki gwarancji, plomby śrub). Do tego czasu przy takich obciążeniach używać limitu 2200–2400 albo 272 W.
- Ochrona sprzętowa działa niezależnie od nas: dławienie przy hotspot 110 / mem 108 °C, wyłączenie przy 115 / 113 °C (`FW_CTF` włączone, §1.5, §1.7).
