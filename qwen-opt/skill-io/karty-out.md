| firma | karta | arch | VRAM | GB/s | FP16 / INT8 T | plain 2k | MTP a=3,2 2k | 128k | prefill 4k FP16 / INT8 | 32k | 256k śr. | mieści 262k? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AMD | RX 6800 | RDNA2 gfx1030 | 16 | 512 | 32.33 / 64.7 | 32 | 92 | 81 | 311 / 622 | 561 | 315 | nie (wagi > VRAM) |
| AMD | RX 6900 XT | RDNA2 gfx1030 | 16 | 512 | 46.08 / 92.2 | 32 | 92 | 81 | 443 / 886 | 800 | 449 | nie (wagi > VRAM) |
| AMD | RX 7900 GRE | RDNA3 gfx1100 | 16 | 576 | 92 / 92 | 36 | 104 | 92 | 885 / 885 | 798 | 448 | nie (wagi > VRAM) |
| AMD | RX 7900 XT | RDNA3 gfx1100 | 20 | 800 | 103 / 103 | 49 | 144 | 127 | 990 / 990 | 893 | 501 | ~196k |
| AMD | RX 7900 XTX | RDNA3 gfx1100 | 24 | 960 | 123 / 123 | 59 | 173 | 153 | 1183 / 1183 | 1067 | 599 | tak |
| AMD | RX 9070 XT | RDNA4 gfx1201 | 16 | 640 | 195 / 389 | 40 | 115 | 102 | 1875 / 3740 | 3374 | 1893 | nie (wagi > VRAM) |
| AMD | MI250 | CDNA2 gfx90a | 128 | 3277 | 362.1 / 362.1 | 203 | 590 | 521 | 3481 / 3481 | 3141 | 1762 | tak |
| AMD | MI300X | CDNA3 gfx942 | 192 | 5300 | 1307.4 / 2614.9 | 328 | 955 | 842 | 12570 / 25141 | 22682 | 12726 | tak |
| AMD | MI325X | CDNA3 gfx942 | 256 | 6000 | 1307.4 / 2614.9 | 371 | 1081 | 953 | 12570 / 25141 | 22682 | 12726 | tak |
| AMD | MI355X | CDNA4 gfx950 | 288 | 8000 | 2500 / 5000 | 495 | 1441 | 1271 | 24036 / 48072 | 43371 | 24333 | tak |
| NVIDIA | RTX 3090 | Ampere sm_86 | 24 | 936 | 71.2 / 284.7 | 58 | 169 | 149 | 685 / 2737 | 2470 | 1386 | tak |
| NVIDIA | RTX 4090 | Ada sm_89 | 24 | 1008 | 165.2 / 660.6 | 62 | 182 | 160 | 1588 / 6351 | 5730 | 3215 | tak |
| NVIDIA | RTX 5060 Ti 16GB | Blackwell sm_120 | 16 | 448 | 47.4 / 189.8 | 28 | 81 | 71 | 456 / 1825 | 1646 | 924 | nie (wagi > VRAM) |
| NVIDIA | RTX 5090 | Blackwell sm_120 | 32 | 1792 | 209.5 / 838 | 111 | 323 | 285 | 2014 / 8057 | 7269 | 4078 | tak |
| NVIDIA | A100 80GB SXM | Ampere sm_80 | 80 | 2039 | 312 / 624 | 126 | 367 | 324 | 3000 / 5999 | 5413 | 3037 | tak |
| NVIDIA | H100 SXM | Hopper sm_90 | 80 | 3350 | 989.5 / 1979 | 207 | 604 | 532 | 9513 / 19027 | 17166 | 9631 | tak |
| NVIDIA | H200 SXM | Hopper sm_90 | 141 | 4800 | 989.5 / 1979 | 297 | 865 | 763 | 9513 / 19027 | 17166 | 9631 | tak |
| NVIDIA | B200 | Blackwell sm_100 | 180 | 8000 | 2250 / 4500 | 495 | 1441 | 1271 | 21632 / 43265 | 39034 | 21900 | tak |

RX 7900 XTX  sufit a=3,2    173  zmierzone  119.3    69%  (Q4_K_M, spec_sweep T=1)
RTX 3090     sufit a=3,2    160  zmierzone   80.0    50%  (UD-Q4_K_XL, fork kvqleana, final-recipes)
RTX 4090     sufit a=3,2    172  zmierzone  101.3    59%  (UD-Q4_K_XL, fork kvqlean)
RTX 5090     sufit a=3,2    251  zmierzone  148.6    59%  (UD-Q6_K, fork kvqlean)
RTX 5060 Ti  sufit a=3,2    120  zmierzone   49.4    41%  (IQ3_XXS GSQ, fork kvqlean 196k)
