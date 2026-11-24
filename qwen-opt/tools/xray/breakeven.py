#!/usr/bin/env python3
"""Break-even per-position acceptance a* for a draft window of B rows (anchor + B-1 drafts).
Step cost model: c[B] = c1 * (1 + j + s*(B-1)) + d*(B-1); expected tokens (1-a^B)/(1-a) (SpecCtl, ik2_main.cu:3163-3167)."""
import sys
def E(a,B): return B if a>=1 else (1-a**B)/(1-a)
def astar(r,B):
    lo,hi=0.0,0.999999
    if E(hi,B)<r: return float('nan')
    for _ in range(60):
        m=(lo+hi)/2
        if E(m,B)<r: lo=m
        else: hi=m
    return hi
c1=8.9
print(f"plain c1={c1} ms (XTX Maya ik2, 112.3 t/s); d = drafter ms per drafted token")
print(f"{'j':>5} {'s':>5} {'d':>4} | " + " ".join(f"B={B}:r/a*".rjust(13) for B in (2,3,4,5,6)))
for j in (0.0,0.15,0.3,0.5):
  for s in (0.1,0.2,0.3):
    for d in (0.0,0.5):
      cells=[]
      for B in (2,3,4,5,6):
        r=(c1*(1+j+s*(B-1))+d*(B-1))/c1
        cells.append(f"{r:5.2f}/{astar(r,B):.2f}".rjust(13))
      print(f"{j:5.2f} {s:5.2f} {d:4.1f} | "+" ".join(cells))
