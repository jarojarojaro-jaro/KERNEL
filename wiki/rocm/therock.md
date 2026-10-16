---
typ: rocm
tags: [rocm, therock, dystrybucja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/research_notes/Optymalizacja kerneli na AMD/rocm_stack.md:14-15,46; ~/KERNEL/product/research/03-silniki-i-stack.md:71,91,361-367,608,676; ~/KERNEL/product/research/08-analiza-platformy-latek.md:17,55; ~/KERNEL/product/research/13-rocm-10.1.md:4,243
status: aktualne
---
# TheRock: system budowania i wydań ROCm

**Od ROCm 7.14 (2026-07-15) AMD buduje i wydaje ROCm przez otwarty system TheRock: Core SDK, instalator Runfile (kilka wersji obok siebie), pakiety DEB/RPM, koła Pythona per rodzina gfx i tarballe.**

Co ma dla nas znaczenie:
- **Tarball per rodzina:** ROCm 10.1 dla gfx110X ściągnięty jako `therock-dist-linux-gfx110X-all-10.1.0.tar.gz` i rozpakowany bez sudo do `~/opt/rocm-10.1`.
- **Paczki per gfx (raport 03):** core ok. 700 MB, biblioteki ok. 100 MB, device-gfx1100 ok. 50 MB; nightly 10.x dla Linux i natywnego Windows. Lemonade i Strata budują paczki llama.cpp HIP z TheRock tylko dla danej rodziny (183–654 MB), zamiast fatbinu wszystkich archów (947 MB `ggml-hip.dll`).
- **Strata na Windows** dołącza biblioteki ROCm 10.2.0a20260930 z TheRock (zip HIP 604 MB), więc użytkownik potrzebuje tylko sterownika Adrenalin.
- **Windows w TheRock:** ROCR-Runtime, amdsmi, rocprofiler-sdk i hipFile mają status „Unsupported”; HIP na Windows idzie przez PAL. Dlatego PM4 (0060) i profilowanie rocprofv3 nie przenoszą się na Windows.

Otwarte pytanie produktowe (raport 03): budować własne paczki ROCm z TheRock czy wziąć gotowe z `lemonade-sdk/llamacpp-rocm`.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rocm-stos]]
- [[hip-na-windows]]
- raport-03-silniki
- strata
