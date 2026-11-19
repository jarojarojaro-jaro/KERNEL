#!/usr/bin/env python3
"""--long argument for bench.py so that the needle document has ~TARGET real tokens: bench.py sizes it as
TARGET/1.6 words; measure tokens per word of the same generator with the server's /tokenize and rescale."""
import json, sys, urllib.request
sys.argv, target = sys.argv[:1], int(sys.argv[1])
import bench
doc, _ = bench.document(16000, seed=7)
req = urllib.request.Request("http://127.0.0.1:18794/tokenize", json.dumps({"content": doc}).encode(), {"Content-Type": "application/json"})
n = len(json.load(urllib.request.urlopen(req))["tokens"])
print(int(target * 16000 / n))   # bench.document(L) gives ~n/16000 * L tokens
print(f"calib: document(16000) = {n} tokens", file=sys.stderr)
