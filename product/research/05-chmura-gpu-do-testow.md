# 05 — Chmura GPU jako laboratorium testowe: dostawcy, ceny, programy darmowe, ograniczenia, strategia

Data: 2026-10-15. Researcher: R5CloudGpu. Nie użyto GPU, nie zakładano kont, nie użyto kluczy API.

Konwencje:
- Ceny są w USD/GPU-h, chyba że zaznaczono inaczej.
- „mediana/min” dla Vast.ai pochodzi z publicznego feedu JSON z 2026-10-15 21:30 UTC ([feed][vast-feed]).
- `[INFERENCE]` oznacza mój wniosek bez bezpośredniego potwierdzenia.
- `(>12 mies.)` oznacza źródło starsze niż 12 miesięcy, więc możliwie nieaktualne.

## 1. TL;DR

- **NVIDIA consumer jest tani i dostępny od ręki, ceny spadły poniżej 0.10 $/h.** Vast.ai na 2026-10-15 ma mediany on-demand:
  - RTX 3060 0.08 $;
  - RTX 3090 0.23 $;
  - RTX 4090 0.51 $;
  - RTX 5060 Ti 0.16 $;
  - RTX 5070 0.29 $;
  - RTX 5090 0.73 $ (445 ofert).

  Salad i Clore są jeszcze tańsze: 3090 kosztuje 0.09 $/h na najniższym priorytecie ([vast-feed], [salad-pricing], [clore-pricing]). Cała macierz 8 kart NVIDIA przez 80 h/mies. to ok. **190 $/mies.**
- **Konsumenckie Radeony praktycznie nie istnieją w chmurze godzinowej z dostępem root.** Na Vast.ai jest zero ofert AMD (feed: 80 modeli, wszystkie NVIDIA; strona RX 7900 XTX: „No current offers”). RunPod ma tylko MI300X. Wyjątki:
  - **SaladCloud** ma RX 7800 XT, 7900 XT, 7900 XTX, 9060 XT i 9070 XT za 0.04–0.17 $/h, ale tylko w kontenerze WSL2, bez `/dev/kfd` i bez SSH ([salad-amd], [cp-amd]).
  - **Hostkey** ma bare metal z RX 7900 XTX (pre-order) oraz Radeon AI PRO R9700 (RDNA4, gfx1201) za €0.471/h ([hostkey-radeon]).
  - **GigaGPU (UK)** ma RX 9070 XT, R9700 i Ryzen AI Max+ 395 w abonamencie miesięcznym z root ([gigagpu]).
- **Intel Arc: brak podaży godzinowej.** Jedyna sensowna opcja to dedyk GigaGPU z Arc Pro B60 (ten sam krzem Battlemage co B580) za £129/mies. lub B70 za £179/mies. Intel Tiber AI Cloud ma wyłącznie Gaudi i Max ([gigagpu-b60], [tiber]). Najtaniej jest **kupić B580**: €270 używany ([pp-b580]).
- **Apple: dedykowane Mac mini w Scaleway**, z 24-godzinnym minimum wynikającym z licencji Apple:
  - M4 16 GB: €0.22/h (€149/mies.);
  - M4 Pro 64 GB: €0.49/h ([scaleway-mac]).

  GitHub macOS runners **nie mają Metal/MPS** ([gh-runners]), więc do testów GPU się nie nadają.
- **Profilery i zegary.** Na kontenerach Vast, RunPod i Salad nie da się:
  - użyć Nsight Compute (`ERR_NVGPUCTRPERM`), bo wymaga `CAP_SYS_ADMIN` lub ustawienia na hoście;
  - użyć rocprofv3 z licznikami;
  - zablokować zegarów przez `nvidia-smi -lgc`.

  Działają: **Vast VM** (KVM, „CUDA profiling with hardware counters” według dokumentacji), TensorDock VM, bare metal (Hostkey, GigaGPU, Hetzner GEX) oraz AMD Developer Cloud (VM) ([vast-docker], [vast-vm], [nv-ctrperm], [rocprof-cap]).
- **Programy darmowe dla Radeon/Arc praktycznie nie istnieją.**
  - AMD daje $100 kredytu na MI300X (ważny 30 dni) w AMD Developer Cloud ([amd-devcloud]).
  - AMD „Radeon Test Drive” (W7800, W7900, R9700) to maks. 14 dni, wyłącznie do ewaluacji, a użycie komercyjne jest zakazane ([amd-cloud-access]).
  - Duże kredyty (Google do $350k, AWS do $200k, Azure do $150k) obejmują tylko datacenter GPU, nie konsumenckie karty ([gcp-startup], [aws-activate], [ms-startups]).
- **Kupno sprzętu jest w 2026 drogie, bo trwa kryzys pamięci (DRAM/GDDR7).** Używane karty, mediana eBay sold z 90 dni:
  - RTX 3090: €1,224;
  - RTX 4090: €2,185;
  - RX 7900 XTX: €837;
  - RX 9070 XT: €694;
  - RTX 3060: €257.

  Nowa RTX 5090 kosztuje ok. $7,400 ([pcprice-*], [vcp-5090], [gpu-shortage]). **Wynajem NVIDIA jest więc dużo tańszy niż zakup. Zakup ma sens tylko dla AMD, Intela i Apple, których nie da się wynająć z root.**
- **Szum pomiarowy.** Ten sam SKU na różnych hostach różni się średnio o 8% (maks. 22%) w zadaniach compute-bound, ale tylko ~1% w zadaniach memory-bound ([sinha-sc22], >12 mies.). Decode LLM jest memory-bound `[INFERENCE]`, więc metoda „interleaved A/B na tym samym hoście” jest odporna. Absolutnych t/s między hostami nie wolno porównywać.
- **Rekomendacja w skrócie:**
  - NVIDIA wynajmujemy (Vast: Docker do benchmarków, VM do profilowania);
  - AMD RDNA2/3/4 i Intel Arc kupujemy (mała ława testowa) plus Hostkey R9700 jako RDNA4 z root;
  - Apple wynajmujemy w Scaleway;
  - Salad służy jako walidacja „Windows/WSL2 u gracza”;
  - od bety społeczność opt-in, bo nasi użytkownicy i tak tuningują nocami na swoim sprzęcie.

  Budżety: **MVP ≈ 500–600 $/mies.** + jednorazowo ok. €1.5–2k; **beta ≈ 1.2–1.5k $/mies.**; **launch ≈ 2.5–3.5k $/mies.** Szczegóły w sekcji 3.

## 2. Ustalenia

### 2.1 Dostawcy: przegląd

| dostawca | model | typ dostępu | konsumenckie NVIDIA | AMD Radeon | Intel Arc | API/agent | uwagi |
|---|---|---|---|---|---|---|---|
| **Vast.ai** | marketplace hostów | Docker (domyślnie) lub **KVM VM** (`vms_enabled=true`) | GTX 10xx–RTX 50xx, ~80 modeli | **0 ofert** (filtr `gpu_arch=amd` istnieje) | brak | CLI/SDK, skill `vastai`, wtyczki dla Claude Code/Codex/Cursor, `AGENTS.md` i `vast-capabilities` na instancji, publiczny feed cen JSON | on-demand, interruptible (licytacja, „często 50%+ taniej”), reserved (do −50%) ([vast-agents], [vast-types], [vast-feed]) |
| **RunPod** | Community Cloud (hosty) i Secure Cloud (DC) | kontener (Pod), Serverless, Clusters | 3070…5090, A4000–A6000, L4, L40S | tylko **MI300X** (Secure, $2.39) | brak | REST API, `runpodctl`, oficjalny MCP (~50 narzędzi, hostowany `mcp.getrunpod.io`) | kontenery bez privileged ([runpod-pricing], [runpod-mi300x], [runpod-mcp], [runpod-prof] >12 mies.) |
| **SaladCloud** | sieć domowych gamingowych PC | kontener w **WSL2**, bez SSH (web terminal) | 3060…5090, laptopy | **RX 7800 XT / 7900 XT / 7900 XTX / 9060 XT / 9070 XT** | brak | API, skills, docs MCP | 4 priorytety cenowe, wywłaszczanie ([salad-pricing], [salad-amd], [salad-ssh]) |
| **TensorDock** | marketplace | **KVM VM** (także Windows VM) | 3090, 4090, A4000, A6000, L40… | brak | brak | REST API | cennik na stronie z 2024-07 (>12 mies.), ceny live są w dashboardzie ([tensordock]) |
| **Clore.ai** | marketplace, ~6.8k GPU | kontener | 3060…5090 (19.5% floty to RTX 50) | brak dGPU | brak | publiczne API rynku | spot zwykle w cenie on-demand ([clore-pricing]) |
| **Hostkey** (NL) | dedyk lub VPS, godzinowo i miesięcznie | **bare metal, root, IPMI** | A5000, 4090, 5090, A6000 | **RX 7900 XTX (4×, pre-order), R9700 €0.471/h** | brak | API | jedyny znaleziony bare-metal RDNA4 z rozliczeniem godzinowym ([hostkey-radeon], [hostkey-gpu]) |
| **GigaGPU** (UK) | dedyk miesięczny | **bare metal, root** | 3050…5090, RTX 6000 PRO | **RX 9070 XT, R9700, Ryzen AI Max+ 395** (£299) | **Arc Pro B60 £129, B70 £179** | portal | rozliczenie miesięczne, wdrożenie <24 h ([gigagpu], [gigagpu-b60], [gigagpu-b70], [gigagpu-395]) |
| **Hetzner** | dedyk GEX | bare metal, root, IPMI | RTX PRO 4000 Blackwell SFF (GB203, 70 W, 432 GB/s), RTX PRO 6000 | brak | brak | Robot API | GEX45: €214/mies. + €209 za setup ([hetzner-gex], [gex45-news], [rtxpro4000]) |
| **Scaleway** | Mac mini as-a-service | bare metal macOS | — | — | — | API | M1 do M4 Pro, minimum 24 h ([scaleway-mac]) |
| **AWS** | EC2 | VM | brak konsumenckich | **G4ad (V520, RDNA1): blokada nowych uruchomień od 2026-09-01, koniec 2027-08-31** | brak | pełne | mac-m4 / mac-m4pro na Dedicated Host, 24 h minimum ([aws-g4ad], [aws-mac]) |
| **Azure** | VM | VM | brak konsumenckich | **NGads V620** (RDNA2 Navi21, do 1/4–1 GPU) | brak | pełne | seria pod cloud gaming/VDI; ROCm na Linuksie w tej VM niezweryfikowany `[INFERENCE]` ([azure-v620], [azure-v620-price]) |
| **AMD Developer Cloud** | DigitalOcean / Vultr | VM | — | **MI300X** 1× lub 8× | — | jak DO | $100 kredytu na start ([amd-devcloud]) |
| Lambda | DC | VM | brak (V100, A100, H100, B200) | — | — | API | H100 $3.99 ([lambda-pricing]) |
| Paperspace (DO) | DC | VM / notebook | brak konsumenckich | — | — | — | od $0.45 ([gd-paperspace]) |
| Jarvislabs | DC | VM | L4 $0.44 | — | — | — | ([jarvis]) |
| OVHcloud | DC | VM | L4 $1.00, L40S $1.80 | — | — | API | ([ovh]) |
| Thunder Compute | **GPU-over-TCP** (wirtualizacja w warstwie CUDA) | VM | A6000 $0.35 | — | — | CLI | **do ~2× wolniej w nietypowych obciążeniach, nie nadaje się do pomiarów kerneli** ([thunder-how], [thunder-pricing]) |
| Hyperbolic, Shadeform, Prime Intellect | agregatory | zależnie od partnera | zależnie od partnera | — | — | API | Shadeform: „30+ clouds”, bez marży ([shadeform], [gd-hyperbolic]) |
| CoreWeave, Fluidstack, Cudo | DC na kontrakt | k8s / bare metal | — | — | — | — | nie dla nas ([gd-coreweave], [gd-fluidstack], [gd-cudo]) |
| Akash, Genesis Cloud | — | — | — | — | — | — | ceny nie wyrenderowały się lub fetch zawiódł, **niezweryfikowane** ([akash]) |

### 2.2 Tabela cen (USD/GPU-h, chyba że zaznaczono)

Źródła kolumn:
- **Vast**: min / mediana on-demand oraz liczba ofert, feed z 2026-10-15 21:30 UTC ([vast-feed]).
- **Salad**: priorytet Lowest / High ([salad-pricing], AMD z [cp-amd] i [cp-7900xtx]).
- **Clore**: mediana oraz przedział p10–p90, snapshot z 2026-08-24 ([clore-pricing]).
- **RunPod**: „od”, czyli najtańszy wariant (zwykle Community), według computeprices z 2026-10-15 ([cp-runpod]); oraz cena z widoku runpod.io/pricing z 2026-10-08 ([runpod-pricing]). Ten widok to prawdopodobnie Secure Cloud `[INFERENCE]`.
- **Inne**: źródła w komórkach.

| GPU | Vast min / mediana (n) | Salad Lowest / High | Clore mediana (p10–p90) | RunPod od / runpod.io | inne |
|---|---|---|---|---|---|
| RTX 3060 12GB | 0.034 / **0.081** (103) | od 0.015 (Lowest) | 0.04 (0.03–0.07) | — | — |
| RTX 3090 24GB | 0.082 / **0.228** (162) | 0.090 / 0.170 | 0.09 (0.07–0.21) | 0.22 / 0.50 | TensorDock 0.20 (>12 mies.); GigaGPU £159/mies. |
| RTX 4060 Ti | 0.114 / **0.153** (26) (feed: 8 GB) | **16 GB**: 0.080 / 0.140 | 8 GB: 0.06 (0.04–0.12) | — | — |
| RTX 4070 | 0.147 / **0.176** (13); 4070S 0.094 / 0.166 (49) | 0.070 / 0.150 | 0.07 (0.04–0.20) | — | — |
| RTX 4080 | 0.254 / **0.329** (17); 4080S 0.387 / 0.403 | 0.110 / 0.230 | 4080S 0.12 (0.09–0.17) | 0.27 / — | — |
| RTX 4090 | 0.139 / **0.507** (318) | 0.160 / 0.330 | 0.20 (0.14–0.42) | 0.34 / 0.89 | TensorDock 0.35 (>12 mies.); GigaGPU £279/mies. |
| RTX 5060 Ti 16GB | 0.121 / **0.165** (163) | 0.070 / 0.150 | 0.06 (0.04–0.10) | — | — |
| RTX 5070 | 0.170 / **0.294** (12) | 0.080 / 0.165 | 0.11 (0.07–0.29) | — | — |
| RTX 5070 Ti | 0.121 / 0.403 (50) | 0.100 / 0.225 | 0.13 (0.10–0.25) | — | — |
| RTX 5080 | 0.200 / **0.335** (100) | 0.150 / 0.260 | 0.17 (0.12–0.62) | 0.39 / — | — |
| RTX 5090 32GB | 0.374 / **0.734** (445) | 0.250 / 0.500 | 0.29 (0.25–0.77) | 0.69 / 1.19 | GigaGPU £359–399/mies. ([gigagpu-5090]) |
| RTX A4000 | 0.072 / 0.121 (100) | — | — | 0.17 / — | TensorDock 0.10 (>12 mies.) |
| RTX A5000 | 0.188 / 0.221 (11) | — | — | 0.16 / 0.27 | — |
| RTX A6000 | 0.361 / 0.401 (8) | — | ~0.36 | 0.33 / 0.59 | Thunder 0.35; TensorDock 0.45 (>12 mies.) |
| L4 | 0.200 / 0.268 (17) | — | — | 0.59 / 0.59 | Jarvis 0.44; Modal 0.80; HF Spaces 0.80; OVH 1.00 ([modal], [hf-gpus]) |
| L40S | 0.467 / 0.641 (79) | — | ~0.50 | 0.79 / 1.09 | Modal 1.95; HF 1.80; OVH 1.80 |
| **MI300X** | brak | — | — | — / **2.39** (Secure) | Vultr 1.75 (8×), Hot Aisle 2.99, AMD Dev Cloud/DO 1.99 ([cp-amd], [amd-devcloud-price]) |
| **MI210** | brak | — | — | — | FireVM 1.37/h (kontrakt miesięczny) ([cp-amd]) |
| **Radeon PRO W7900** | brak | — | — | — | **tylko AMD Radeon Test Drive** (Colfax/Comino/ELSA), za darmo, ≤14 dni, ewaluacja ([amd-cloud-access]) |
| **RX 7900 XTX** | **0 ofert** ([vast-7900xtx]) | **0.066 / 0.168** | — | — | Hostkey 4× bare metal (pre-order, cena niepodana) ([hostkey-radeon]) |
| RX 9070 XT | 0 | od 0.070 | — | — | GigaGPU dedyk (cena tylko w portalu); gpuperhour: 0 ofert ([gpuperhour-9070]) |
| Radeon AI PRO R9700 (gfx1201) | 0 | — | — | — | **Hostkey €0.471/h**; GigaGPU ~£199/mies. `[INFERENCE: z tabeli porównawczej na stronie B70]` |
| Arc Pro B60 / B70 | 0 | — | — | — | GigaGPU £129 / £179 za miesiąc; Zed Up (DE) wynajem fizycznej karty B60 od €199 za 2 tyg. ([zedup-b60]) |
| Mac mini M4 / M4 Pro | — | — | — | — | Scaleway €0.22/h (M4 16GB) / €0.49/h (M4 Pro 64GB), 24 h min.; AWS mac-m4pro ~$1.97/h ([scaleway-mac], [aws-mac]) |

Wnioski z tabeli:
- Pokrycie dla konsumenckich NVIDIA jest bardzo dobre.
  - RTX 5090 ma 445 ofert, 4090 ma 318, 5060 Ti 163, 3090 162.
  - Rzadkie są pojedyncze SKU: 4070 (13 ofert), 5070 (12), RTX 4060 (2).
- Pozycja „RTX 4060 Ti” w feedzie Vast ma 8 GB. Wariant 16 GB (ważny dla LLM) pewnie znajdziemy na Vast, filtrując po `gpu_ram`, oraz na Salad (16 GB) `[INFERENCE]`.
- Vast w 2024 ogłosił się „pierwszym marketplace z AMD” ([vast-amd-pr], >12 mies.), ale w 2026-10 nie ma tam żadnego AMD.

### 2.3 Gdzie realnie dostać Radeon i Arc (szczegóły)

**AMD RDNA (konsumenckie i pro)**

| opcja | GPU / gfx | dostęp | profilery / zegary | cena | ocena dla nas |
|---|---|---|---|---|---|
| SaladCloud | RX 7800 XT (gfx1101), 7900 XT/XTX (gfx1100), 9060 XT (gfx1200), 9070 XT (gfx1201) | kontener w WSL2; `/dev/dxg`, **brak `/dev/kfd` i `/dev/dri`**; image musi mieć ROCm ≥7.1 i `librocdxg` od hosta; bez SSH, jest web terminal | nie: brak natywnego amdgpu, `rocm-smi` „exit 0 nawet bez GPU”; Vulkan w WSL2 dla AMD niepewny `[INFERENCE]` | 0.04–0.17 $/h | **dobra walidacja „czy działa i ile t/s na Windowsie gracza”**. Nie nadaje się do tuningu kerneli, PM4, rocprof ani strojenia BACO/zegarów ([salad-amd], [salad-ssh]) |
| Hostkey (NL) | R9700 (RDNA4, gfx1201, 32 GB); 4× RX 7900 XTX | bare metal, root | pełne (własny kernel i sterownik) `[INFERENCE]` | R9700 €0.471/h; XTX: pre-order | **najlepszy wynajmowany RDNA4**. R9700 to ten sam Navi48 co 9070 XT, tylko z 32 GB ([hostkey-radeon]) |
| GigaGPU (UK) | RX 9070 XT, R9700, Ryzen AI Max+ 395 (gfx1151, 96 GB) | bare metal, root, Ubuntu | pełne | 395: £299/mies.; R9700 ~£199 `[INFERENCE]`; 9070 XT: cena w portalu | dobre na długie kampanie RDNA4 i Strix Halo ([gigagpu], [gigagpu-395]) |
| AMD Radeon Test Drive | W7800, W7900 (gfx1100), R9700 | zdalna stacja | pełne `[INFERENCE]` | za darmo, ≤14 dni, po akceptacji | **tylko ewaluacja, użycie komercyjne zabronione** ([amd-cloud-access]) |
| Azure NGads V620 | Radeon PRO V620 (RDNA2 Navi21, gfx1030) | VM, partycje 1/4–1 GPU | niezweryfikowane; seria pod gaming/VDI | NG8ads (1/4 GPU) $0.635/h; NG32ads (1 GPU) $2.54/h | jedyne RDNA2 w hyperscalerze. Wymaga testu, czy Linux i ROCm działają `[INFERENCE]` ([azure-v620], [azure-v620-price]) |
| AWS G4ad | Radeon Pro V520 (RDNA1, gfx1011) | VM | — | $0.3785/h | **wycofywane**: blokada nowych uruchomień od 2026-09-01, koniec 2027-08-31 ([aws-g4ad]) |

**Intel Arc**:
- Brak godzinowej chmury. Intel Tiber AI Cloud oferuje Gaudi 2/3 oraz Max 1100/1550, bez Arc. Free tier zniknął ([tiber], [tiber-free] >12 mies.).
- Realne opcje:
  - GigaGPU: Arc Pro B60 24 GB (Xe2, 20 Xe-cores, 456 GB/s), czyli BMG-G21 jak B580, za £129/mies.; B70 32 GB za £179/mies. ([gigagpu-b60], [gigagpu-b70]);
  - Zed Up (DE): wynajem fizycznej karty B60 od €199 za 2 tyg. do €499 za 6 mies. ([zedup-b60], 11 mies.);
  - zakup B580 za ~€270 używany ([pp-b580]).

**Apple**:
- Scaleway: dedykowane Mac mini, bez hypervisora.
  - M4-S (16 GB): €0.22/h lub €149/mies.;
  - M4-M (32 GB): €0.29/h lub €199/mies.;
  - M4 Pro M4-XL (64 GB): €0.49/h lub €335/mies.;
  - obowiązuje minimum 24 h ([scaleway-mac], [macly-24h]).
- AWS: mac-m4 ~$1.23/h, mac-m4pro ~$1.97/h, oba z 24-godzinnym minimum ([aws-mac], [aws-mac-price]).
- GitHub macOS runners: „Metal Performance Shaders not supported” ([gh-runners]).

### 2.4 Programy darmowe i kredytowe

| program | co daje | kto kwalifikuje się | przydatność dla nas |
|---|---|---|---|
| **AMD AI Developer Program → AMD Developer Cloud** | **$100 kredytu** na MI300X, ważny 30 dni; dodatkowe kredyty za publiczne projekty | członkowie programu, „open-source developers”; wymagana karta płatnicza | test HIP i ROCm na CDNA3. **Warunki: nie wolno „use AMD Developer Cloud to provide a service to a third-party”** ([amd-devcloud], [amd-openclaw]) |
| AMD Cloud Evaluation, ścieżka „25 h” | ~25 h / ~$50, wygasa po 10 dniach | po akceptacji | jw. ([amd-cloud-access]) |
| AMD Instinct Evaluation Program | dostęp do MI300X/MI325X u partnerów CSP | startupy, firmy | ewentualnie później, odpowiedź w 2 tyg. ([amd-cloud-access]) |
| **AMD Radeon Test Drive** | W7800, W7900, R9700, do 14 dni | po akceptacji; „commercial use strictly prohibited” | szybki test W7900 lub R9700, nie do produkcji tuningu ([amd-cloud-access]) |
| AMD AI & HPC Cluster | do 1 roku na MI210–MI325 | uczelnie i non-profit | nie (chyba że przez partnera akademickiego) |
| Google TRC | darmowe **TPU** | badacze | **bezużyteczne**: TPU, nie GPU ([trc]) |
| Google for Startups Cloud | $2k (MVP); $200k lub $350k (AI-first, Seed–A) | startupy z finansowaniem | tylko DC GPU (L4, A100, H100), bez konsumenckich ([gcp-startup]) |
| AWS Activate | Founders do $5k (start $1k); Portfolio do $200k | pre-Series B, do 10 lat istnienia | DC GPU plus EC2 Mac ([aws-activate]) |
| Microsoft for Startups | do $150k (z kodem od inwestora); bez niego ~$1k → $5k | startupy | Azure NGads V620 (RDNA2) mogłoby zjeść te kredyty `[INFERENCE]` ([ms-startups], [ms-tiers]) |
| NVIDIA Inception | brak gotówki; kredyty partnerów, rabaty na enterprise GPU | startupy, za darmo | wymagany do Lambda Startup Credits ([nv-inception]) |
| Lambda | Research Grant do $5k (akademicy); Startup do $7.5k (członkowie Inception) | jw. | tylko DC GPU ([lambda-credits]) |
| Modal | **$30/mies. za darmo**; Startup do $25k (lub $50k) | każdy / startupy Seed–A | szybkie testy L4 i L40S, bez konsumenckich ([modal], [modal-startup]) |
| Hugging Face | ZeroGPU: połowa lub całe RTX Pro 6000 Blackwell, tylko Gradio; granty na Spaces „for a cool demo” | konta >30 dni, PRO | demo, nie lab ([hf-zerogpu], [hf-gpus]) |
| GitHub Actions GPU | Linux 4-core T4 **$0.052/min** (~$3.12/h); tylko plany Team/Enterprise | — | drogie i stary Turing; jako CI lepszy self-hosted runner `[INFERENCE]` ([gh-pricing]) |
| **Intel / Arc** | **brak programu** z dostępem do Arc | — | — |

### 2.5 Ograniczenia praktyczne dla naszej metody

**Root, liczniki, profilery**
- **Vast Docker.**
  - W „docker options” dozwolone są tylko `-e`, `-h` i `-p`. Nie ma `--privileged` ani `--cap-add` ([vast-docker]).
  - Docker-in-Docker jest wyłączony ([vast-tech]).
  - Nsight Compute wymaga uprawnień admina lub `CAP_SYS_ADMIN` dla aplikacji albo trybu „unrestricted” ustawionego na hoście. Wniosek: na kontenerach Vast/RunPod `ncu` prawie zawsze zwraca `ERR_NVGPUCTRPERM` `[INFERENCE]` ([nv-ctrperm], [spheron-prof]).
  - Pułapka: `ncu --query-metrics` zwraca exit 0 mimo błędu, co wykryto na RTX 5090 w WSL2 ([yotta-ncu]).
- **Vast VM (KVM).**
  - Dokumentacja Vast wprost obiecuje „CUDA Performance Profiling with full system access and hardware counters”, `ptrace` i systemd/Docker.
  - Koszty: mniejsza pula maszyn, wolniejszy start, tylko SSH ([vast-vm], [vast-vm2]).
- **RunPod.** Kontenery nie są privileged. Społeczność potwierdza, że Nsight Compute nie działa; Nsight Systems tak ([runpod-prof], >12 mies.).
- **ROCm.**
  - rocprofv3 z licznikami w Dockerze wymaga `--cap-add SYS_ADMIN`, `/dev/kfd` i `/dev/dri`. `perf_event_paranoid` ustawia się na hoście ([rocprof-cap]).
  - Na Salad jest tylko `/dev/dxg`, więc ani rocprof, ani nasza ścieżka PM4 nie wchodzą w grę ([salad-amd]).
  - Nasze łatki AMD (PM4 graph replay, DPP, buffer resource) zakładają natywny sterownik amdgpu na Linuksie. Strojenie pułapki runtime suspend/BACO, która obniżała wydajność do 4.4 t/s, wymaga root na hoście ([07-nasze-metody]; wymóg root `[INFERENCE]`).

**Zegary**: `nvidia-smi -lgc` w nieuprzywilejowanym kontenerze jest odrzucane. Potrzebny jest `--privileged` albo VM lub bare metal ([lgc-ci]). Na Vast można przynajmniej **filtrować po** `gpu_max_power` (limit mocy), `pci_gen`, `pcie_bw`, `gpu_mem_bw`, `cpu_ghz`, `driver_version`, `cuda_vers`, `reliability`, `datacenter`, `vms_enabled` i `gpu_arch` ([vast-search]).

**Docker vs VM vs bare metal**

| środowisko | benchmark t/s | md5 greedy / KLD | ncu / rocprof liczniki | lock zegarów | własny sterownik / jądro |
|---|---|---|---|---|---|
| Vast / RunPod / Clore, kontener | tak | tak | nie `[INFERENCE]` | nie | nie (sterownik hosta, wybór przez filtr) |
| Salad (WSL2) | tak (ścieżka WSL2) | tak | nie | nie | nie (ROCm ≥7.1 w obrazie) |
| Vast VM / TensorDock VM | tak | tak | **tak** (Vast deklaruje) | prawdopodobnie tak `[INFERENCE]` | tak w gościu |
| Hostkey / GigaGPU / Hetzner bare metal | tak | tak | tak | tak | tak |
| AMD Dev Cloud (DO VM, MI300X) | tak | tak | prawdopodobnie tak `[INFERENCE]` | ? | częściowo |

**Noisy neighbours i powtarzalność**
- **Vast.**
  - GPU są przydzielane wyłącznie jednemu najemcy.
  - CPU i RAM są przydzielane proporcjonalnie do udziału GPU w maszynie, z burstem. Przy rywalizacji gwarantowany jest tylko baseline, a przy przekroczeniu RAM grozi OOM ([vast-docker]).
  - Przy wysokim t/s (np. LFM 294 t/s) host-overhead CPU jest istotny, więc noisy neighbour po stronie CPU realnie wpływa na wynik `[INFERENCE]`.
- **Zmienność krzemu.** W klastrach z identycznym SKU średnia wariancja wynosi 8% (maks. 22%), outliery są do 1.5× wolniejsze. Zadania memory-bound (PageRank) mają ~1%, a wyniki są stałe w czasie ([sinha-sc22], >12 mies.).
- **Hosty marketplace różnią się**: limitami mocy, PCIe (od x16 Gen4 po risery x1), chłodzeniem i wersją sterownika ([hn-vast-pcie] >12 mies., [vast-search]). Zdarzają się „verified” hosty z siecią na poziomie 1% deklaracji ([trustpilot-vast]).
- **Wniosek metodyczny `[INFERENCE]`.** Każdy wynik zapisujemy razem z fingerprintem hosta:
  - `nvidia-smi -q` (power limit, zegary, PCIe link) lub `amd-smi`;
  - CPU, sterownik, kernel.

  Raportujemy **przyspieszenie A/B na tym samym hoście w tej samej sesji**, nie absolutne t/s. Dopiero mediana z ≥3 hostów trafia do bazy jako „typowe t/s dla SKU”.
- **Unikać** Thunder Compute (GPU-over-TCP, do ~2× spowolnienia) do pomiarów kerneli ([thunder-how]).

**Licencja**: EULA sterownika GeForce zabrania „datacenter deployment” poza blockchainem ([nv-eula], >12 mies.). To ryzyko po stronie hostów marketplace (podaż może zniknąć), nie nasze. Dla produkcyjnego backendu lepsze są karty Pro/DC `[INFERENCE]`.

**Dane cenowe**: feed Vast można cytować z atrybucją, ale „bulk collection … index, benchmark, or derivative product requires a data license” ([vast-pricing]). Jeśli aplikacja ma pokazywać ceny chmury, potrzebna jest licencja.

### 2.6 Alternatywa A: własne laboratorium z używanych kart (ceny 2026-10)

Kontekst: AI wysysa moce produkcyjne HBM i GDDR, przez co ceny nowych kart w 2026 rosną. RTX 5090 w USA przekroczyła $5k, a w skrajnych przypadkach $6.4–9.5k ([gpu-shortage], [vcp-5090]). Mac mini zdrożał: od 2026-05 startuje od $799 (16 GB, 512 GB), wcześniej $599 ([macrumors-mini]).

| karta | arch / gfx | używana: mediana eBay sold (90 dni) | nowa (US) | komentarz |
|---|---|---|---|---|
| RTX 3060 12GB | Ampere sm_86 | **€257** (€236–280, n=1378) | — | ([pp-3060]) |
| RTX 3090 | sm_86 | **€1,224** (€1,136–1,312) | ~$1,555–1,680 | drożej niż XTX, bo 24 GB do AI ([pp-3090]) |
| RTX 4060 Ti 16GB | Ada sm_89 | ~$500–780 (aktywne oferty) | ~$600+ | brak twardej mediany ([ebay-4060ti]) |
| RTX 4090 | sm_89 | **€2,185** | — | ([pp-4090]) |
| RTX 5090 | Blackwell sm_120 | €2,229 (n=27, mało transakcji) | ~$7,444 | ([pp-5090], [vcp-5090]) |
| RX 6700 XT | RDNA2 gfx1031 | ~$325 (oferta eBay) | $799 (anomalia) | ([vcp-6700xt]) |
| RX 7800 XT | RDNA3 gfx1101 | **€501** | $990 | ([pp-7800xt]) |
| RX 7900 XTX | RDNA3 gfx1100 | **€837** (€765–927) | $1,821 | już mamy ([pp-7900xtx], [vcp-7900xtx]) |
| RX 9070 XT | RDNA4 gfx1201 | **€694** (€618–753) | $815 | najpopularniejszy AMD w Steam ([pp-9070xt]) |
| Arc B580 | Xe2 BMG-G21 | **€270** (€258–306) | $370 | ([pp-b580]) |
| Mac mini M4 16GB | Apple M4 | ~$650–800 (oferty i transakcje eBay) | od $799 (512 GB) | ([ebay-mini], [macrumors-mini]) |

Porównanie kosztów `[INFERENCE]`:

| karta | zakup | wynajem ciągły (730 h × mediana Vast) | zwrot zakupu |
|---|---|---|---|
| RTX 3090 | €1,224 | ~$166/mies. | ~7–8 mies. |
| RTX 4090 | €2,185 | ~$370/mies. | ~6 mies. |
| RTX 5090 | — | ~$535/mies. | — |

Ale nikt nie potrzebuje karty 24/7. Przy 80–150 h/mies. wynajem 3090 to $18–34 miesięcznie, więc **kupowanie NVIDIA się nie opłaca**.

Inaczej wygląda AMD, Intel i Apple: nie ma dla nich chmury z root.

| karta | zakup | wynajem | zwrot zakupu |
|---|---|---|---|
| RX 9070 XT | €694 | Hostkey R9700 €0.471/h | po ~1,470 h |
| Arc B580 | €270 | GigaGPU B60 £129/mies. | po ~2 mies. |
| Mac mini M4 | ~$700 | Scaleway €149/mies. | po ~5 mies. |

Do tego potrzebna jest 1–2 ławy testowe (PC z PSU 850 W+, PCIe x16 Gen4). Drożejący DDR5 podnosi ich koszt do ~€800–1,200 za sztukę `[INFERENCE]`.

### 2.7 Alternatywa B: sieć urządzeń społeczności (opt-in)

Precedensy:
- **LocalScore** (Mozilla Builders, na llamafile/llama.cpp): publiczna baza wyników. Zbiera CPU, GPU, OS, RAM i metryki (prefill, gen, TTFT) ([localscore-gh], [localscore-readme], [localscore-latest]). Leaderboard dla Llama 3.1 8B Q4_K_M ma ~374 akceleratory ([markaicode-ls], wtórne).
- **Wątki-tablice wyników llama.cpp**: Vulkan #10879, ROCm #15021, SYCL #23313. Wymagają ręcznego wklejania wyników ([llama-vk], [llama-rocm], [llama-sycl]).
- **make-localllm-easier #101** (2026-10-10): projekt o bardzo podobnym celu doszedł do tego samego wniosku. Konsumenckie RX „not offered by clouds; community reports needed”, a „pierwsze przejście” w chmurze kosztuje ~$200–300 ([mle-101]).
- **SaladCloud to w praktyce skomercjalizowany „BOINC dla GPU”**: płaci właścicielom domowych PC za idle i ma także Radeony. To dowód, że gracze godzą się udostępniać GPU za wynagrodzenie ([salad-pricing]).

Kluczowa obserwacja `[INFERENCE]`: **nasz produkt sam z siebie uruchamia nocny tuning na sprzęcie użytkownika.** Sieć urządzeń nie musi więc niczego „pożyczać”. Wystarczy, że użytkownik zaznaczy „udostępnij anonimowe wyniki”: fingerprint sprzętu, sterownik, model, wybrane flagi lub łatki, przyspieszenie A/B oraz wynik bramki md5/KLD. Każdy użytkownik z rzadką kartą (RX 6700 XT, Arc A770, laptop 4060, M1 Max) staje się węzłem laboratorium.

Wymogi:
- uruchamiamy tylko **podpisane** buildy i konfiguracje; nigdy kod od innych użytkowników;
- zero plików osobistych; zgodność z RODO (my w EU): zgoda, minimalizacja danych, usuwanie na żądanie;
- konfiguracja trafia jako domyślna dla SKU dopiero po N≥3 niezależnych potwierdzeniach z tymi samymi md5 i podobnym przyrostem.

## 3. Co to znaczy dla naszego produktu

### 3.1 Rekomendowana strategia laboratorium

1. **NVIDIA wynajmujemy, nie kupujemy.**
   - Vast.ai jako podstawa: Docker do benchmarków i bramek md5/KLD, **VM** (`vms_enabled=true`) do sesji z `ncu` i lockiem zegarów.
   - Agent może sterować Vast przez CLI, skill lub plugin (`--raw` JSON), a RunPod przez oficjalny MCP.
   - RunPod i Salad jako zapas podaży.
   - Przy każdym hoście zapis fingerprintu; tylko A/B w obrębie hosta.
2. **AMD: nasz XTX plus zakup RDNA4, plus wynajem bare metal.**
   - RDNA3 (gfx1100): mamy.
   - RDNA4: kupić używaną **RX 9070 XT** (€694). Do równoległych kampanii i RDNA4 z 32 GB: **Hostkey R9700** (€0.471/h, root).
   - RDNA2: w becie kupić RX 6700 XT; opcjonalnie sprawdzić Azure V620 (gfx1030).
   - Strix Halo (gfx1151): GigaGPU £299/mies. dopiero w becie.
3. **Intel: kupić Arc B580** (€270).
   - Alternatywa: GigaGPU B60 jako zdalny bare metal z tym samym krzemem; drożej już po 2 miesiącach.
4. **Apple: Scaleway.**
   - M4-S 16 GB na stałe (€149/mies.); M4 Pro 64 GB na dni kampanii.
   - Od bety rozważyć zakup używanego Mac mini M4 (~$700), bo zwraca się po ~5 mies.
5. **Salad jako „test u gracza”**: kontener WSL2 na Windowsie, NVIDIA plus 5 klas Radeon za grosze. Weryfikuje, że build i bramka przechodzą poza laboratorium. Nie służy do tuningu.
6. **MI300X: tylko darmowe $100 AMD** do sanity-checku wspólnego kodu HIP na CDNA3. To nie jest rynek naszego produktu. Uwaga na zakaz „service to a third party”: kod tuningu dla produktu komercyjnego to szara strefa. **Zapytać AMD** (devcloudrequests@amd.com).
7. **Od bety: sieć opt-in z aplikacji** (sekcja 2.7). Na launch to główne źródło danych dla długiego ogona SKU, w tym laptopów i starych kart.

### 3.2 Dokładna lista kart do pokrycia najpierw

Kryteria:
- udział w Steam Hardware Survey (wrzesień 2026, [steam-hw]): RTX 5070 6.15%, 5060 4.40%, 5060 Ti 4.06%, 4060 3.89%, 3060 3.66%, 4060 Ti 2.85%, 4070 2.11%, 5080 1.98%, RX 9070 XT 1.42%, RX 9060 XT 0.77%, RX 7800 XT 0.59%, RX 7900 XTX 0.40%, 5090 0.40%, 3090 0.32%;
- pokrycie architektury i gfx;
- klasa VRAM ważna dla LLM;
- dostępność w wynajmie.

**MVP: 12 celów**

| # | karta | arch / gfx | VRAM | dlaczego | skąd |
|---|---|---|---|---|---|
| 1 | RTX 3060 12GB | Ampere sm_86 | 12 | #5 w Steam, najtańsze 12 GB | Vast 0.08 $ |
| 2 | RTX 3090 | sm_86 | 24 | ulubiona karta entuzjastów LLM, 24 GB | Vast 0.23 $ |
| 3 | RTX 4060 Ti 16GB | Ada sm_89 | 16 | 2.85%, popularne 16 GB | Vast (filtr `gpu_ram`) / Salad |
| 4 | RTX 4070 (lub 4070 SUPER) | sm_89 | 12 | 2.11% (+1.74% SUPER) | Vast 0.17–0.18 $ |
| 5 | RTX 4090 | sm_89 | 24 | flagowiec Ada | Vast 0.51 $ |
| 6 | RTX 5060 Ti 16GB | Blackwell sm_120 | 16 | #3 w Steam | Vast 0.16 $ |
| 7 | RTX 5070 | sm_120 | 12 | **#1 w Steam** | Vast 0.29 $ |
| 8 | RTX 5090 | sm_120 | 32 | flagowiec Blackwell | Vast 0.73 $ |
| 9 | RX 7900 XTX | RDNA3 gfx1100 | 24 | nasza baza (109 t/s Qwen) | własna |
| 10 | RX 9070 XT | RDNA4 gfx1201 | 16 | najpopularniejszy Radeon | zakup + Hostkey R9700 |
| 11 | Arc B580 | Xe2 | 12 | jedyny realny Arc | zakup |
| 12 | Mac mini M4 16GB (+ M4 Pro 64GB okazjonalnie) | Apple M4 | 16 / 64 | macOS/Metal | Scaleway |

**Beta: +10**
- NVIDIA 8 GB (dla tej klasy VRAM potrzebny inny dobór modeli):
  - RTX 5060 8GB (#2 w Steam);
  - RTX 4060 8GB;
  - RTX 3060 Ti lub 3070 8GB.
- Wyższe NVIDIA:
  - RTX 5080;
  - RTX 5070 Ti;
  - RTX 4080 / 4080 SUPER;
  - RTX 3080 10GB.
- AMD:
  - RX 7800 XT (gfx1101; zakup €501);
  - RX 9060 XT 16GB (gfx1200; Salad, ewentualnie zakup);
  - RX 6700 XT (RDNA2 gfx1031; zakup ~$325).
- Dodatkowo: Ryzen AI Max+ 395 / Strix Halo (gfx1151, GigaGPU) oraz Apple M4 Pro / M-Max na dłużej.

**Launch (głównie przez sieć społeczności)**:
- karty: RX 6600 / 6600 XT, RX 7600, RX 7900 XT, Arc A770 / B570, Apple M1, M2, M3 (Pro/Max/Ultra);
- **laptopy**: RTX 4060 Laptop to 3.50% Steamu, a w chmurze laptopów nie ma;
- GTX 16xx i RTX 20xx z fallbackiem.

### 3.3 Budżet miesięczny (3 fazy)

Założenia `[INFERENCE]`:
- ceny mediany Vast on-demand z 2026-10-15;
- kampania tuningowa to ~10 GPU-h na parę (model × GPU), czyli jedna noc;
- regresja nocna to 1 h na kartę;
- euro przeliczam ~1:1.1;
- koszty tokenów agentów LLM **nie są** wliczone, a prawdopodobnie przewyższą koszty GPU.

**MVP (mies. 0–3)**

| pozycja | wyliczenie | $/mies. |
|---|---|---|
| NVIDIA 8 kart × 80 h (Vast on-demand) | suma median 2.34 $/h × 80 h = 187 $ | ~190 |
| narzut: sesje VM do `ncu`, storage, nieudane hosty | ~+30% | ~60 |
| Apple: Scaleway M4-S na stałe + M4 Pro przez 5 dni | €149 + 5×24×€0.49 ≈ €208 | ~230 |
| RDNA4 overflow: Hostkey R9700, 60 h | 60 × €0.471 ≈ €28 | ~30 |
| Salad walidacja Windows/WSL2: 6 klas × 20 h | ~0.15 $/h | ~20 |
| MI300X | kredyt AMD $100 | 0 |
| **razem** | | **≈ 500–600** |
| jednorazowo | RX 9070 XT €694 + Arc B580 €270 + ława testowa ~€800–1,200 | **≈ €1.8–2.2k** |

**Beta (mies. 3–9): ~22 karty, regresja nocna, sieć opt-in w pilocie**

| pozycja | wyliczenie | $/mies. |
|---|---|---|
| kampanie NVIDIA: 4 modele × 12 kart × 10 h = 480 h | × ~0.30 $ | ~145 |
| regresja NVIDIA: 8 kart × 30 nocy × 1 h = 240 h | × ~0.30 $ | ~70 |
| profilowanie w VM: ~100 h | × ~0.40 $ | ~40 |
| stały runner CI Blackwell: reserved 5090 (~0.73 $ × 730 h × ~0.6) | lub zakup 5060 Ti 16GB (~$474–680) | ~0–320 |
| Apple: Scaleway M4-S + M4 Pro na stałe (lub zakup Mac mini) | €149 + €335 | ~530 (lub ~0 po zakupie) |
| Hostkey R9700 / GigaGPU 395 | ~100 h lub 1 mies. | ~50–330 |
| Salad, macierz Windows | | ~50 |
| backend sieci opt-in (VPS, DB, object storage) | `[INFERENCE]` | ~50–150 |
| **razem** | | **≈ 1.2–1.5k** |
| jednorazowo | RX 7800 XT €501, RX 6700 XT ~$325, RTX 3060 €257 (8-osobowa ława 8 GB/12 GB), ewentualnie Mac mini M4 ~$700 | **≈ €1.5–2.5k** |

**Launch (mies. 9+): katalog ~10 modeli/mies., ~25 SKU wynajmowanych, reszta przez społeczność**

| pozycja | wyliczenie | $/mies. |
|---|---|---|
| kampanie: 10 modeli × 15 kart × 10 h = 1,500 h | × 0.30 $ | ~450 |
| regresja: 15 kart × 30 × 1 h = 450 h | | ~135 |
| profilowanie w VM: 200 h | | ~80 |
| 2 stałe runnery CI (reserved) | 2 × ~250–320 | ~550 |
| Apple: 2–3 Maki (zakup lub Scaleway) + dni M-Max/Ultra | | ~300–700 |
| własna ława AMD/Intel: prąd i amortyzacja | ~6 kart × 300 W × 50% × 730 h ≈ 660 kWh | ~150–250 |
| Salad / TensorDock Windows VM, testy dystrybucji | | ~100 |
| sieć społeczności: backend i nagrody niegotówkowe (np. darmowy Pro) | | ~300–800 |
| **razem** | | **≈ 2.5–3.5k** |

Porównanie: AWS lub Azure z kredytów startupowych nie pokryją kart konsumenckich. Kredyty warto wziąć na backend i ewentualnie na Azure V620 (RDNA2).

### 3.4 Ryzyka

- **Podaż AMD i Intel w chmurze jest punktowa.** Opiera się na jednym hoście w NL (Hostkey), jednym w UK (GigaGPU) i Salad (WSL2). Każdy może zniknąć; AWS już wycofuje G4ad bez ogłoszenia ([aws-g4ad]). Mitigacja: własne karty plus sieć opt-in.
- **Salad ≠ natywny Linux ROCm.** Wyniki z Salad nie są reprezentatywne dla naszych łatek PM4/HIP. Etykietować je jako „WSL2-path”.
- **Absolutne t/s z marketplace są zaszumione**: power limit, PCIe, CPU, sterownik. Raportować tylko A/B w obrębie hosta, a „typowe t/s” jako medianę z ≥3 hostów.
- **Prawne**:
  - AMD Dev Cloud: zakaz usług dla osób trzecich; Radeon Test Drive: zakaz komercji;
  - licencja na dane cen Vast;
  - EULA GeForce po stronie hostów;
  - RODO dla sieci opt-in.
- **Ceny sprzętu.** Kryzys pamięci ma trwać do końca 2027 ([gpu-shortage]). Zakupy RDNA4 i Arc zrobić teraz, póki używane są tańsze od nowych. Ceny wynajmu mogą jednak wzrosnąć, bo popyt na 24–32 GB rośnie.
- **Interruptible/spot** na Vast lub Salad przerywa kampanie nocne. Potrzebny checkpoint kampanii (stan tunera, wyniki A/B) oraz wznowienie na innym hoście.

### 3.5 Otwarte pytania

1. Czy Vast VM faktycznie pozwala na `ncu --set full` i `nvidia-smi -lgc` na RTX 50xx? Wymaga jednego testu za ~$1 po rejestracji (zgoda użytkownika na konto i płatność).
2. Czy Azure NGads V620 przyjmuje Linuksa z ROCm 7.x i daje pełne GPU (NG32ads)? To jedyna droga do RDNA2 w hyperscalerze.
3. Czy AMD zgodzi się na użycie Developer Cloud do tuningu dla produktu komercyjnego? Czy zamiast tego da „partner access” do Radeonów (np. ISV program)?
4. Ceny GigaGPU (RX 9070 XT, R9700) i Hostkey (4× RX 7900 XTX) widać tylko w portalu. Potrzebna wycena.
5. Jak duży jest „ogon” kart użytkowników LLM w porównaniu ze Steamem? Wskazówką byłby rozkład z LocalScore; gracze ≠ użytkownicy lokalnych LLM `[INFERENCE]`.

## 4. Źródła

- [vast-feed]: https://storage.googleapis.com/vast-public-gpu-pricing/gpu-pricing-public.json (pobrany 2026-10-15, `updated: 2026-10-15T21:30:18Z`)
- [vast-pricing]: https://vast.ai/pricing
- [vast-agents]: https://docs.vast.ai/guides/get-started/agents
- [vast-types]: https://docs.vast.ai/guides/instances/choosing/instance-types.md
- [vast-docker]: https://docs.vast.ai/guides/instances/docker-environment
- [vast-tech]: https://docs.vast.ai/guides/reference/faq/technical.md
- [vast-vm]: https://docs.vast.ai/guides/instances/virtual-machines
- [vast-vm2]: https://docs.vast.ai/linux-virtual-machines
- [vast-search]: https://docs.vast.ai/cli/reference/search-offers.md
- [vast-7900xtx]: https://vast.ai/pricing/gpu/RX-7900-XTX
- [vast-amd-pr]: http://vast.ai/press-release/vast-ai-first-gpu-rental-marketplace-amd-support (2024-05, >12 mies.)
- [runpod-pricing]: https://www.runpod.io/pricing (updated 2026-10-08)
- [runpod-mi300x]: https://www.runpod.io/gpu-models/mi300x (updated 2026-08-27)
- [runpod-mcp]: https://docs.runpod.io/get-started/mcp-servers ; https://www.runpod.io/blog/runpod-just-got-native-in-your-ai-ide
- [runpod-prof]: https://www.answeroverflow.com/m/1225015304682471454 (>12 mies.)
- [cp-runpod]: https://computeprices.com/providers/runpod (oraz /gpus/rtx4090, rtx3090, rtx5090, rtx4080, rtx5080, rtxa4000, rtxa5000, rtxa6000, l4, l40s, mi300x; 2026-10-15)
- [salad-pricing]: https://salad.com/pricing/
- [salad-amd]: https://docs.salad.com/container-engine/reference/amd-gpus (2026-09-10)
- [salad-ssh]: https://salad.mintlify.app/container-engine/explanation/core-concepts/faqs ; https://docs.salad.com/container-engine/tutorials/performance/high-performance-apps
- [cp-amd]: https://computeprices.com/gpus/category/amd (2026-10-15)
- [cp-7900xtx]: https://computeprices.com/gpus/rx-7900-xtx
- [clore-pricing]: https://docs.clore.ai/guides/getting-started/pricing (snapshot 2026-08-24)
- [tensordock]: https://www.tensordock.com/cloud-gpus.html (cennik z 2024-07-24, >12 mies.)
- [hostkey-radeon]: https://hostkey.com/gpu-dedicated-servers/radeon/
- [hostkey-gpu]: https://hostkey.com/gpu-dedicated-servers/
- [gigagpu]: https://gigagpu.com/dedicated-gpu-hosting/
- [gigagpu-b60]: https://gigagpu.com/intel-arc-pro-b60-hosting/
- [gigagpu-b70]: https://gigagpu.com/intel-arc-pro-b70-hosting/
- [gigagpu-395]: https://gigagpu.com/ryzen-ai-max-395-hosting/
- [gigagpu-5090]: https://gigagpu.com/nvidia-rtx-5090-hosting/
- [hetzner-gex]: https://www.hetzner.com/dedicated-rootserver/matrix-gpu/
- [gex45-news]: https://itbrief.news/story/hetzner-launches-gex45-gpu-server-for-ai-workloads
- [rtxpro4000]: https://videocardz.com/newz/nvidia-launches-rtx-pro-4000-sff-and-rtx-pro-2000-blackwell-workstation-gpus-with-70w-tdp (>12 mies.) ; https://www.leadtek.com/eng/products/workstation_graphics(2)/NVIDIA_RTX_PRO_4000_Blackwell_SFF_Edition(51043)/detail
- [scaleway-mac]: https://www.scaleway.com/en/pricing/apple-silicon/
- [macly-24h]: https://macly.io/alternatives/scaleway
- [aws-mac]: https://aws.amazon.com/ec2/instance-types/mac/faqs/
- [aws-mac-price]: https://macyou.co/blog/aws-ec2-mac-pricing-explained
- [aws-g4ad]: https://repost.aws/questions/QU-Y6iEgEMQce-s64i5vSbMg/has-aws-retired-the-g4ad-ec2-instance-family-which-uses-amd-radeon-pro-v520-gpus
- [azure-v620]: https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ngadsv620-series
- [azure-v620-price]: https://www.azurespeed.com/AzureVmPricing/Series/NGads-V620
- [amd-devcloud]: https://www.amd.com/en/developer/resources/cloud-access/amd-developer-cloud.html
- [amd-cloud-access]: https://www.amd.com/en/developer/resources/cloud-access.html
- [amd-openclaw]: https://www.amd.com/en/developer/resources/technical-articles/2026/openclaw-on-amd-developer-cloud-qwen-3-5-and-sglang.html
- [amd-devcloud-price]: https://isaacadjei.me/til/amd-developer-cloud (wtórne)
- [lambda-pricing]: https://lambda.ai/pricing
- [lambda-credits]: https://grantedai.com/grants/lambda-labs-research-grant-lambda-labs-7f35dc0d ; https://fin.ai/learn/ai-credits-for-startups (wtórne)
- [jarvis]: https://jarvislabs.ai/pricing
- [ovh]: https://www.ovhcloud.com/en/public-cloud/prices/
- [thunder-pricing]: https://www.thundercompute.com/pricing
- [thunder-how]: https://www.thundercompute.com/blog/how-thunder-compute-works-gpu-over-tcp
- [shadeform]: https://www.shadeform.ai/
- [gd-hyperbolic]: https://getdeploying.com/hyperbolic
- [gd-paperspace]: https://getdeploying.com/paperspace
- [gd-coreweave]: https://getdeploying.com/coreweave
- [gd-fluidstack]: https://getdeploying.com/fluidstack
- [gd-cudo]: https://getdeploying.com/cudo-compute
- [akash]: https://akash.network/pricing/gpus/
- [tiber]: https://www.intel.com/content/www/us/en/developer/articles/news/trusted-ai-in-developer-cloud.html (>12 mies.)
- [tiber-free]: https://community.intel.com/t5/Intel-Tiber-Developer-Cloud/What-happened-to-the-free-tier/td-p/1614678 (>12 mies.)
- [zedup-b60]: https://videocardz.com/newz/german-company-launches-intel-arc-pro-b60-rental-program (11 mies.)
- [gpuperhour-9070]: https://gpuperhour.com/rent/rx-9070-xt
- [gcp-startup]: https://cloud.google.com/startup
- [trc]: https://sites.research.google/trc/about/
- [aws-activate]: https://aws.amazon.com/startups/credits/
- [ms-startups]: https://www.microsoft.com/en-us/startups
- [ms-tiers]: https://klymentiev.com/blog/microsoft-for-startups (wtórne)
- [nv-inception]: https://www.nvidia.com/en-us/startups/
- [modal]: https://modal.com/pricing
- [modal-startup]: https://aicreditmart.com/ai-credits-providers/modal-startup-credits-how-to-get-up-to-25k-2026-guide/ (wtórne)
- [hf-zerogpu]: https://huggingface.co/docs/hub/spaces-zerogpu
- [hf-gpus]: https://huggingface.co/docs/hub/spaces-gpus
- [gh-pricing]: https://docs.github.com/en/billing/reference/actions-runner-pricing
- [gh-runners]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- [nv-ctrperm]: https://developer.nvidia.com/nvidia-development-tools-solutions-err-nvgpuctrperm-nsightcompute
- [spheron-prof]: https://www.spheron.network/blog/gpu-profiling-ai-workloads-nsight-compute-pytorch-profiler-guide/
- [yotta-ncu]: https://github.com/yottalabsai/Profiler/issues/2 (2026-09-27)
- [rocprof-cap]: https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html ; https://blog.alicegoldfuss.com/enabling-perf-in-kubernetes/ (>12 mies.)
- [lgc-ci]: https://github.com/graphty-org/graphty-monorepo/pull/1010
- [sinha-sc22]: https://arxiv.org/abs/2208.11035 (SC'22, >12 mies.)
- [hn-vast-pcie]: https://news.ycombinator.com/item?id=37141187 (>12 mies.)
- [trustpilot-vast]: https://www.trustpilot.com/review/vast.ai
- [nv-eula]: https://www.nvidia.com/content/DriverDownloads/licence.php?lang=us&type=GeForce ; https://www.techpowerup.com/239994/nvidia-forbids-geforce-driver-deployment-in-data-centers (>12 mies.)
- [gpu-shortage]: https://tech-insider.org/gpu-prices-2026/ ; https://shattered.io/desktop-gpu-shipments-12-5-million-nvidia-90-percent-2026/ ; https://evezone.evetech.co.za/quick-bytes/will-gpu-prices-drop-in-2026-or-2027 (wtórne)
- [macrumors-mini]: https://www.macrumors.com/2026/05/01/mac-mini-now-starts-at-799/
- [pp-3060]: https://www.pcprice.watch/gpu-buying-guide/rtx-3060-price-used-and-specs
- [pp-3090]: https://www.pcprice.watch/gpu-buying-guide/rtx-3090-price-used-and-specs
- [pp-4090]: https://www.pcprice.watch/gpu-buying-guide/rtx-4090-price-used-and-specs
- [pp-5090]: https://www.pcprice.watch/gpu-buying-guide/rtx-5090-price-used-and-specs
- [pp-7800xt]: https://www.pcprice.watch/gpu-buying-guide/rx-7800-xt-price-used-and-specs
- [pp-7900xtx]: https://www.pcprice.watch/gpu-buying-guide/rx-7900-xtx-price-used-and-specs
- [pp-9070xt]: https://www.pcprice.watch/gpu-buying-guide/rx-9070-xt-price-used-and-specs
- [pp-b580]: https://www.pcprice.watch/gpu-buying-guide/arc-b580-price-used-and-specs
- [pcprice-*]: zbiorczo pozycje pp-* powyżej (eBay sold, 90 dni, 7 rynków; 2026-10-15)
- [vcp-5090]: https://videocardprices.com/card/nvidia-rtx-5090/
- [vcp-7900xtx]: https://videocardprices.com/card/amd-radeon-rx-7900-xtx/
- [vcp-6700xt]: https://videocardprices.com/card/amd-rx-6700-xt/
- [ebay-4060ti]: https://www.ebay.com/sch/i.html?_nkw=rtx+4060+ti+16+gb&_sop=12
- [ebay-mini]: https://www.ebay.com/itm/298637413448 ; https://techcrunch.com/2026/04/24/mac-mini-price-expensive-ebay-shortage-ai-memory/
- [steam-hw]: https://store.steampowered.com/hwsurvey/videocard/ (wrzesień 2026)
- [localscore-gh]: https://github.com/cjpais/localscore
- [localscore-readme]: https://github.com/mozilla-ai/llamafile/blob/main/localscore/README.md
- [localscore-latest]: https://www.localscore.ai/latest
- [markaicode-ls]: https://markaicode.com/benchmarks/offline-ai-benchmark/ (wtórne)
- [llama-vk]: https://github.com/ggml-org/llama.cpp/discussions/10879
- [llama-rocm]: https://github.com/ggml-org/llama.cpp/discussions/15021
- [llama-sycl]: https://github.com/ggml-org/llama.cpp/discussions/23313
- [mle-101]: https://github.com/phonology024/make-localllm-easier/issues/101 (2026-10-10)
- [07-nasze-metody]: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md (materiał wewnętrzny)
