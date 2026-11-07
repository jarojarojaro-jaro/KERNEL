#!/usr/bin/env python3
"""Cheapest reliable Vast offers per card, ranked by TOTAL estimated cost = dph_total (GPU + storage) x hours +
GB downloaded x inet_down_cost. Offers whose model pull costs more than MAX_PULL (default $0.02) are excluded.
   find67.py <card> [hours]     (card names as in cards/*.json; reads the download size from the card file)
Read-only: `vastai search offers` needs no key and spends nothing. Prints no addresses."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = {"3060ti": ["RTX 3060 Ti"], "3070": ["RTX 3070"], "2080ti": ["RTX 2080 Ti"], "3080": ["RTX 3080"],
       "3060": ["RTX 3060"], "4070": ["RTX 4070"], "4070ti": ["RTX 4070 Ti", "RTX 4070S"], "5070": ["RTX 5070"],
       "3080-12": ["RTX 3080"], "4060ti": ["RTX 4060 Ti"], "4070tis": ["RTX 4070S Ti"], "4080": ["RTX 4080", "RTX 4080S"],
       "5060ti": ["RTX 5060 Ti"], "5070ti": ["RTX 5070 Ti"], "5080": ["RTX 5080"], "3090": ["RTX 3090"],
       "4090": ["RTX 4090"], "5090": ["RTX 5090"]}
card = sys.argv[1]
VRAM_MIN = {"3080-12": 11.5, "3080": 9.5, "2080ti": 10.5, "3060ti": 7.5, "3070": 7.5, "3060": 11.5, "4070": 11.5,
            "4070ti": 11.5, "5070": 11.5, "4060ti": 15, "4070tis": 15, "4080": 15, "5060ti": 15, "5070ti": 15, "5080": 15,
            "3090": 23, "4090": 23, "5090": 31}
hours = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
c = json.load(open(f"{HERE}/cards/{card}.json"))
model_gb = c["model"]["size"] / 1e9
dl_gb = model_gb + (c.get("draft") or {}).get("size", 0) / 1e9 + (c.get("moe") or {}).get("size", 0) / 1e9 + 1.6
disk = 70 if not c.get("moe") else 90
max_pull = float(os.environ.get("MAX_PULL", "0.02"))
rows = []
for g in GPU[card]:
    q = (f"gpu_name={g.replace(' ', '_')} num_gpus=1 reliability>=0.97 rentable=true direct_port_count>=1 "
         f"disk_space>={disk} cuda_vers>=12.8 cpu_ram>=15 inet_down>=200 geolocation notin [CN]")
    env = dict(os.environ, PATH=f"{os.path.expanduser('~/qwen-opt/cloud/.venv/bin')}:{os.environ['PATH']}")
    out = subprocess.run(["vastai", "search", "offers", q, "--storage", str(disk), "-o", "dph_total", "--limit", "200", "--raw"],
                         capture_output=True, text=True, env=env).stdout
    for o in json.loads(out or "[]"):
        if o["gpu_ram"] / 1024 < VRAM_MIN.get(card, 0) or (card == "3080" and o["gpu_ram"] / 1024 > 11):
            continue
        dlc = o.get("inet_down_cost") or 0
        pull = model_gb * dlc
        if pull > max_pull:
            continue
        est = o["dph_total"] * hours + dl_gb * dlc
        rows.append((est, o))
rows.sort(key=lambda r: r[0])
print(f"{card}: download ~{dl_gb:.1f} GB, disk {disk} GB, {hours} h, max model pull ${max_pull}")
for est, o in rows[:6]:
    print(f"  id {o['id']} {o['gpu_name']} {o['gpu_ram'] / 1024:.0f}G est ${est:.3f} = {o['dph_total']:.3f}/h x {hours} + "
          f"{dl_gb:.1f} GB x ${(o.get('inet_down_cost') or 0) * 1000:.2f}/TB | storage ${o['storage_cost']:.2f}/GB/mo "
          f"rel {o['reliability']:.3f} drv {o['driver_version']} cuda {o['cuda_max_good']} pcie {o.get('pci_gen')}x{o.get('gpu_lanes')} "
          f"{o['inet_down']:.0f} Mbps ram {o['cpu_ram'] / 1024:.0f}G cpu {o['cpu_cores_effective']:.0f} {o['geolocation']}")
if not rows:
    print("  no offer under the pull-cost limit")
