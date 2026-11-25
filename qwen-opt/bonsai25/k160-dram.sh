#!/usr/bin/env bash
# K-160: Bonsai 2.5 plain decode, bytes L2->memory per kernel (rocprofv3 --pmc GL2C_EA_RDREQ_*B; FETCH_SIZE reads 0 on gfx1100) + GL2C hit rate + kernel durations -> achieved GB/s per kernel group.
set -uo pipefail
O=$HOME/qwen-opt/bonsai25/k160-$(date +%H%M); mkdir -p $O; export GGML_HIP_PM4=0
source ~/qwen-opt/perf-tools/profiles/bonsai25.env
B=$HOME/wt/topka-rt/build-hip/bin; P=/opt/rocm/core-10.0/bin/rocprofv3
~/qwen-opt/l1tok/chat8080.sh stop
run() { cd $O/$1 && env GGML_HIP_K157_MMVF_THIN=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 400 $P $2 --output-format csv -d . -o p -- \
  $B/llama-bench -m $MODEL -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 0 -n 32 -r 1 > bench.txt 2>&1; grep -E "tg32" bench.txt | tail -1; }
mkdir -p $O/kt $O/pmc1 $O/pmc2
run kt "--kernel-trace"
run pmc1 "--kernel-trace --pmc GL2C_EA_RDREQ_32B_sum GL2C_EA_RDREQ_64B_sum GL2C_EA_RDREQ_96B_sum GL2C_EA_RDREQ_128B_sum"
run pmc2 "--kernel-trace --pmc GL2C_HIT_sum GL2C_MISS_sum"
python3 - $O <<'PY'
import csv,glob,sys,collections,re
O=sys.argv[1]
def grp(n):
    n=re.sub(r'\(.*','',n); n=re.sub(r'<.*','',n); return n[:60]
def load(d):
    kt=glob.glob(f'{O}/{d}/**/*kernel_trace.csv',recursive=True); cc=glob.glob(f'{O}/{d}/**/*counter_collection.csv',recursive=True)
    return kt,cc
dur=collections.Counter(); cnt=collections.Counter()
kt,_=load('kt')
for r in csv.DictReader(open(kt[0])):
    g=grp(r['Kernel_Name']); dur[g]+=int(r['End_Timestamp'])-int(r['Start_Timestamp']); cnt[g]+=1
fetch=collections.Counter(); hit=collections.Counter(); miss=collections.Counter()
for d,tgt in (('pmc1',None),('pmc2',None)):
    _,cc=load(d)
    if not cc: print('no counters in',d); continue
    for r in csv.DictReader(open(cc[0])):
        g=grp(r['Kernel_Name']); v=float(r['Counter_Value']); c=r['Counter_Name']
        m=re.match(r'GL2C_EA_RDREQ_(\d+)B',c)
        if m: fetch[g]+=v*int(m.group(1))/1024
        elif c.startswith('GL2C_HIT'): hit[g]+=v
        elif c.startswith('GL2C_MISS'): miss[g]+=v
tot=sum(dur.values())
print(f"{'kernel':60s} {'ms':>8s} {'%':>5s} {'n':>6s} {'GB':>7s} {'GB/s':>6s} {'L2hit%':>6s}")
for g,t in dur.most_common(18):
    gb=fetch[g]*1024/1e9; ms=t/1e6
    hr=100*hit[g]/(hit[g]+miss[g]) if hit[g]+miss[g] else float('nan')
    print(f"K160 {g:60s} {ms:8.1f} {100*t/tot:5.1f} {cnt[g]:6d} {gb:7.2f} {gb/(ms/1e3) if ms else 0:6.0f} {hr:6.1f}")
print(f"K160 total GPU ms {tot/1e6:.1f}; fetched GB {sum(fetch.values())*1024/1e9:.2f}")
PY
echo "gfxhub $(journalctl -k --since '-15min' --no-pager | grep -c gfxhub)"
