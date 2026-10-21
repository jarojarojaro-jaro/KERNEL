import json, re, collections, sys
BS = {'F32':(1,4),'F16':(1,2),'BF16':(1,2),'Q4_0':(32,18),'Q8_0':(32,34),'Q4_K':(256,144),'Q5_K':(256,176),'Q6_K':(256,210),'Q2_K':(256,84),'Q3_K':(256,110),'IQ4_XS':(256,136),'IQ4_NL':(32,18),'IQ3_XXS':(256,98),'IQ3_S':(256,110),'IQ2_XS':(256,74),'IQ2_XXS':(256,66),'IQ2_S':(256,82),'Q5_0':(32,22),'Q4_1':(32,20),'Q5_1':(32,24),'IQ1_M':(256,56),'IQ1_S':(256,50)}
def load_txt(p):
    d = {}
    for l in open(p):
        f = l.split()
        d[f[0]] = f[1]
    return d
xl = {t['name']: t for t in json.load(open('ud-map.json'))}
maps = {'XL': {k: v['type'] for k, v in xl.items()}}
for q in ['UD-Q4_K_M', 'UD-Q4_K_S', 'UD-IQ4_XS']:
    maps[q] = load_txt(f'map-{q}.txt')
def nbytes(name, ty):
    n = xl[name]['n']; b = BS[ty]; return n // b[0] * b[1]
def streamed(name):  # bytes read per decode token (no embd get_rows, no MTP block 64)
    return not (name.startswith('token_embd') or name.startswith('blk.64.'))
for q, m in maps.items():
    tot = sum(nbytes(n, m[n]) for n in xl); st = sum(nbytes(n, m[n]) for n in xl if streamed(n))
    print(f"{q:10s} file-tensors {tot/1e9:6.3f} GB  streamed/token {st/1e9:6.3f} GB")
# transitions XL -> M
for q in ['UD-Q4_K_M', 'UD-Q4_K_S']:
    tr = collections.Counter(); sav = collections.Counter()
    for n in xl:
        a, b = maps['XL'][n], maps[q][n]
        if a != b:
            role = re.sub(r'^blk\.\d+\.', '', n); tr[(role, a, b)] += 1; sav[(role, a, b)] += nbytes(n, a) - nbytes(n, b)
    print('==', q)
    for k, c in sorted(tr.items(), key=lambda x: -sav[x[0]]):
        print(f"  {k[0]:22s} {k[1]:7s}->{k[2]:7s} x{c:3d}  {sav[k]/1e9:+.3f} GB")
