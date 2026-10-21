def tok(a,n):
    s,p=1.0,1.0
    for k in range(n): p*=a[k]; s+=p
    return s
def step(n,pass_ms=0.55,row=0.85,base=21.78,extra=0.0): return base+n*(pass_ms+row)+extra
sc={
 'PL MTP (E0)':[0.635,0.461,0.350,0.296,0.28],
 'PL E4 pesym':[0.60,0.45,0.35,0.30,0.28],
 'PL E4 optym':[0.69,0.56,0.49,0.45,0.43],
 'EN MTP (E0)':[0.677,0.546,0.457,0.440,0.42],
 'EN E4 optym':[0.72,0.62,0.56,0.53,0.51],
}
for k,a in sc.items():
    for n in (3,4):
        for pm,lab in ((0.55,'Q4K'),(0.80,'Q8')):
            if 'MTP' in k and lab=='Q8': continue
            pm2 = 0.55 if 'MTP' in k else pm
            ex = 0 if 'MTP' in k else 0.05
            t=tok(a,n); s=step(n,pm2,extra=ex)
            print(f'{k:14s} n={n} {lab if "E4" in k else "   "} tok/krok {t:.3f} ms {s:.2f} t/s {1000*t/s:.1f}')
# efficient head on our MTP draft
save_pass=(178-35)/900e3*1e3  # ms per pass
print('eff head saving per pass ms',round(save_pass,3),'n=4 ->',round(4*save_pass-4*0.03,3),'ms',round(100*(4*save_pass-4*0.03)/27.38,2),'%')
# B300 per-round
print('961.6/4.745 round ms',1000/(961.6/4.745),'vanilla ms',1000/240.5)
print('MI355X row cost',(14185-11982)/7/1000,(15340-11982)/15/1000,'rel',(14185-11982)/7/11982,(15340-11982)/15/11982,'XTX rel',0.85/27.38)
print('phone J',0.356*23.3*43,0.166*74.7*14,'W',0.356*23.3,0.166*74.7)
print('LMhead us',0.654*574,574-0.654*574,0.179*255,255-0.179*255,0.379*326)
