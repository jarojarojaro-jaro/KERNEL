#!/usr/bin/env python3
"""Parallel ranged download with sha256 check.  usage: pdl.py URL OUT SHA256 SIZE [CONNECTIONS]"""
import concurrent.futures as cf
import hashlib
import os
import sys
import time
import urllib.request

url, out, sha, size = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
conns = int(sys.argv[5]) if len(sys.argv) > 5 else 16
part = 64 << 20
done = [0]

with open(out, "ab") as f:
    f.truncate(size)


def fetch(start: int) -> None:
    end = min(start + part, size) - 1
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=60) as r, open(out, "r+b") as f:
                f.seek(start)
                pos = start
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    pos += len(chunk)
                if pos != end + 1:
                    raise IOError(f"short read {pos}/{end + 1}")
            done[0] += end + 1 - start
            return
        except Exception as e:  # retry transient network errors
            print(f"retry {start}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed range {start}")


t0 = time.time()
with cf.ThreadPoolExecutor(conns) as ex:
    futs = [ex.submit(fetch, s) for s in range(0, size, part)]
    for i, fu in enumerate(cf.as_completed(futs)):
        fu.result()
        if i % 16 == 0:
            el = time.time() - t0
            print(f"{done[0] / 1e9:6.2f}/{size / 1e9:.2f} GB  {done[0] / el / 1e6:6.1f} MB/s", flush=True)

h = hashlib.sha256()
with open(out, "rb") as f:
    while b := f.read(16 << 20):
        h.update(b)
ok = h.hexdigest() == sha
print("sha256", "OK" if ok else f"MISMATCH {h.hexdigest()}")
sys.exit(0 if ok else 1)
