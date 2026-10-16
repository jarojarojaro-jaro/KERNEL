# LFM2.5 XTX per-token budget from the measured PM4 tape (c2_tr_1.txt, ~/wt/lfm4-prof, 304-dispatch steady tape,
# per dispatch = end of previous -> end of this, boundary included). Bytes per call from the GGUF header / bw.cpp table.
import re,sys
rows=[]
for l in open(__import__('os').path.expanduser('~/wt/lfm4-prof/c2_tr_1.txt')):
    m=re.match(r'\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(.*)',l)
    if m: rows.append((float(m.group(1)),float(m.group(2)),float(m.group(3)),m.group(4)))
MB={ # (substring of kernel+grid) -> MB read per call (weights only)
 'mul_mat_vec_q<t13, 1, true, false, false, false, 2> grid 768x4':17.30,  # expert gate+up Q5_K (4 experts)
 'mul_mat_vec_q_conv':8.65,                                              # shortconv in_proj Q5_K 6144x2048
 'moe_down_reduce<t13':8.65, 'moe_down_reduce<t14':10.35,                 # expert down Q5_K / Q6_K
 'mul_mat_vec_q<t14, 1, false, false, false, false, 2> grid 64000':215.0, # tied head Q6_K
 'mul_mat_vec_q<t13, 1, true, false, false, false, 2> grid 1024x1':2.88,  # out_proj / attn q (2048x2048 Q5_K)
 'grid 5888':33.2,                                                        # dense gate+up (2 layers)
 'mul_mat_vec_q<t13, 1, false, false, false, false, 2> grid 1024x1':2.88, # attn o
 'mul_mat_vec_q<t14, 1, true, false, false, false, 2> grid 1024x1':19.8,  # dense down Q6_K
 'mul_mat_vec_q<t13, 1, false, false, false, false, 2> grid 256x1':0.72,  # attn k Q5_K
 'mul_mat_vec_q<t14, 1, false, false, false, false, 2> grid 256x1':0.86,  # attn v Q6_K
 'mul_mat_vec_q<t14, 1, false, false, false, false, 2> grid 1024x4':10.0, # unclear 1024x4 Q6_K (1.2 calls avg)
 'mul_mat_vec_q<t13, 1, false, false, false, false, 2> grid 1024x4':17.30,
 'mul_mat_vec_q<t13, 1, false, false, false, false, 2> grid 3072':8.65,
}
def mb(k):
    for s,v in MB.items():
        if s in k: return v
    return 0.0
tot=sum(r[0] for r in rows); calls=sum(r[1] for r in rows)
mv=[(r,mb(r[3])) for r in rows if mb(r[3])>0]; sm=[r for r in rows if mb(r[3])==0]
mv_t=sum(r[0] for r,_ in mv); mv_calls=sum(r[1] for r,_ in mv); mv_bytes=sum(r[1]*b for r,b in mv)
sm_t=sum(r[0] for r in sm); sm_calls=sum(r[1] for r in sm)
print(f'tape {tot:.0f} us, {calls:.0f} dispatches; matvec {mv_calls:.0f} calls {mv_t:.0f} us {mv_bytes/1e3:.3f} GB -> {mv_bytes/mv_t*1e3:.0f} GB/s incl. boundaries')
print(f'non-matvec {sm_calls:.0f} calls {sm_t:.0f} us')
WALL=3404.0; HOST=WALL-tot
for BW in (960,900,850):
    stream=mv_bytes/BW*1e3  # us
    print(f'BW {BW}: pure weight stream {stream:.0f} us; matvec overhead {mv_t-stream:.0f} us; DRAM-idle-ish pool = matvec overhead + non-matvec = {mv_t-stream+sm_t:.0f} us ({(mv_t-stream+sm_t)/WALL*100:.0f}% of {WALL:.0f} us wall); host {HOST:.0f} us')
# per-call overhead table
print('\nper-call overhead vs 900 GB/s stream (us): kernel, calls, us/call, ideal, overhead')
for r,b in sorted(mv,key=lambda x:-x[0][0]):
    ideal=b/900*1e3
    print(f'  {r[3][:70]:70} {r[1]:5.1f} {r[2]:7.2f} {ideal:7.2f} {r[2]-ideal:6.2f}')
# scenarios
B=0.6   # PM4 boundary (0.46-0.86 measured)
def scen(name, save):
    t=WALL-save; print(f'{name:58} save {save:5.0f} us -> {t:5.0f} us/token = {1e6/t:5.0f} t/s ({WALL/t*100-100:+.0f}%)')
print()
scen('S0 old estimate: MoE triple boundaries only (2x38x0.6)', 2*38*B)
# S1 PM4-PDL: every dispatch boundary 0.6->0.25 us, matvec ramp hidden: min(overhead, R) per matvec call
for R in (1.0,2.0):
    s=calls*(B-0.25)+sum(r[1]*min(max(r[2]-b/900*1e3-B,0),R) for r,b in mv)
    scen(f'S1 PM4-PDL (early start, weights before flag), ramp hidden<= {R} us', s)
# S2 ideal persistent: time = max(stream @BW, chain) + unhidden dependency bubbles; pool recovered fraction f
pool900=mv_t-mv_bytes/900*1e3+sm_t
for f in (0.3,0.45,0.6):
    scen(f'S2 layer/model-persistent, recovers {int(f*100)}% of the {pool900:.0f} us pool', f*pool900)
# lower bound physical: stream at 900 + router->expert dependency 38x(5+1.5) + 240 handoffs x 0.6
lb=mv_bytes/900*1e3+38*(5+1.5)+240*0.6+HOST
print(f'\nphysical-ish floor: stream@900 {mv_bytes/900*1e3:.0f} + routed-expert dependency {38*6.5:.0f} + handoffs {240*0.6:.0f} + host {HOST:.0f} = {lb:.0f} us -> {1e6/lb:.0f} t/s')
