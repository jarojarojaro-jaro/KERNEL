# Wynajem RX 7900 XTX online – ustalenia (2026-10-09)

**Wniosek: wynajmować się nie opłaca – testy robimy na własnej karcie (RX 7900 XTX na Ubuntu Server).**

| Dostawca | Stan | Uwagi |
|---|---|---|
| Salad Cloud | jedyny realny, od $0.066/h ([computeprices](https://computeprices.com/providers/salad/gpus/rx-7900-xtx), 6.10.2026) | kontenery na cudzych domowych GPU – brak roota, brak wyboru sterownika/jądra, profilery GPU raczej nie działają → nie nadaje się do pracy nad kernelami |
| DataCrunch | wpis „1RX7900XTX” w cloud-mercato to pomyłka – w środku RTX A6000 ([link](https://pcr.cloud-mercato.com/providers/datacrunch/flavors/1rx7900xtx.10v)) | |
| Vast.ai | strona karty istnieje ([link](https://vast.ai/pricing/gpu/RX-7900-XTX)), brak ofert w październiku 2026 | |
| RunPod | brak Radeonów | |
| AMD Developer Cloud, TensorWave, Hot Aisle | tylko Instinct MI300X+ (CDNA, wave64) | inna architektura – wyniki nie przenoszą się na RDNA3 |

Dodatkowo: chmurowa sesja Claude Code ma tylko wyjście HTTPS przez proxy, więc i tak nie zalogowałaby się po SSH na wynajęty serwer.

## Plan zamiast wynajmu
Na serwerze z 7900 XTX:
```bash
git clone https://github.com/jarojarojaro-jaro/KERNEL && cd KERNEL && git checkout research-notes
claude remote-control
```
Sesja pojawia się w aplikacji Claude Code → Claude buduje llama.cpp, benchmarkuje i profiluje bezpośrednio na prawdziwej karcie (a przy okazji ma dostęp do RTX 5060 Ti jako referencji CUDA).

Alternatywa: Claude przygotowuje skrypty, użytkownik uruchamia je i wkleja wyniki (zaczynając od `scripts/sysinfo.sh`).
