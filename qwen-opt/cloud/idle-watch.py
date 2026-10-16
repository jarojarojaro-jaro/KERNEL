#!/usr/bin/env python3
"""Watch our rented GPUs (Vast + RunPod) and exit with an alert when one sits idle.

Polls every INTERVAL s. An instance counts as idle when GPU util < THRESH %. After IDLE_SAMPLES
consecutive idle samples (default 5 x 180 s = 15 min) it prints the alert and exits 2, so the
caller (a background job of the main agent) gets woken up and can act. Exits 0 when no instances
remain. RunPod pods listed in IGNORE (the user's own) are never reported.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

INTERVAL = int(os.environ.get("INTERVAL", 180))
THRESH = float(os.environ.get("THRESH", 5))
IDLE_SAMPLES = int(os.environ.get("IDLE_SAMPLES", 5))
IGNORE = set(os.environ.get("IGNORE", "phoneuse-stage1").split(","))
HERE = os.path.dirname(os.path.abspath(__file__))


def vast():
    key = open(os.path.expanduser("~/.vast/key")).read().strip()
    out = subprocess.run([f"{HERE}/.venv/bin/vastai", "--api-key", key, "show", "instances", "--raw"],
                         capture_output=True, text=True, timeout=60).stdout
    return [(f"vast:{i['id']}", i.get("label") or i.get("gpu_name"), float(i.get("gpu_util") or 0),
             round(float(i.get("dph_total") or 0), 3)) for i in json.loads(out or "[]")]


def runpod():
    key = open(os.path.expanduser("~/.runpod/key")).read().strip()
    q = {"query": "query { myself { pods { id name costPerHr runtime { gpus { gpuUtilPercent } } } } }"}
    req = urllib.request.Request("https://api.runpod.io/graphql", json.dumps(q).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    pods = json.load(urllib.request.urlopen(req, timeout=60))["data"]["myself"]["pods"]
    res = []
    for p in pods:
        if p["name"] in IGNORE:
            continue
        gpus = (p.get("runtime") or {}).get("gpus") or []
        util = max([g.get("gpuUtilPercent") or 0 for g in gpus] or [0])
        res.append((f"runpod:{p['id']}", p["name"], float(util), p.get("costPerHr")))
    return res


def main():
    idle = {}
    while True:
        try:
            inst = vast() + runpod()
        except Exception as e:  # network hiccup: try again next round
            print(f"{time.strftime('%H:%M')} poll error: {e}", flush=True)
            time.sleep(INTERVAL)
            continue
        if not inst:
            print(f"{time.strftime('%H:%M')} no instances left", flush=True)
            return 0
        alerts = []
        for iid, name, util, cost in inst:
            idle[iid] = idle.get(iid, 0) + 1 if util < THRESH else 0
            if idle[iid] >= IDLE_SAMPLES:
                alerts.append(f"IDLE {iid} {name} util {util:.0f}% for {idle[iid] * INTERVAL // 60} min (${cost}/h)")
        if alerts:
            print("\n".join(alerts), flush=True)
            return 2
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
