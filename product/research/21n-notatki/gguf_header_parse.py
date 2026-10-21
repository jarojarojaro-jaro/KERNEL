import struct, sys, json, collections, re
GT = {0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',9:'Q8_1',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',15:'Q8_K',
      16:'IQ2_XXS',17:'IQ2_XS',18:'IQ3_XXS',19:'IQ1_S',20:'IQ4_NL',21:'IQ3_S',22:'IQ2_S',23:'IQ4_XS',24:'I8',25:'I16',26:'I32',27:'I64',28:'F64',29:'IQ1_M',30:'BF16',34:'TQ1_0',35:'TQ2_0',39:'MXFP4',40:'NVFP4'}
def parse(path, filesize):
    b = open(path,'rb').read(); o = [0]
    def rd(fmt):
        v = struct.unpack_from('<'+fmt, b, o[0]); o[0] += struct.calcsize('<'+fmt); return v[0]
    def rs():
        n = rd('Q'); s = b[o[0]:o[0]+n].decode('utf-8','replace'); o[0] += n; return s
    def rv(t):
        if t==8: return rs()
        if t==9:
            at = rd('I'); n = rd('Q'); arr = [rv(at) for _ in range(n)]
            return arr if n<=16 else f'<arr type{at} n={n} first={arr[:6]}>'
        f = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t]; return rd(f)
    assert b[:4]==b'GGUF'; o[0] = 4; ver = rd('I'); nt = rd('Q'); nkv = rd('Q')
    kv = {}
    for _ in range(nkv):
        k = rs(); t = rd('I'); kv[k] = rv(t)
    ts = []
    for _ in range(nt):
        name = rs(); nd = rd('I'); dims = [rd('Q') for _ in range(nd)]; ty = rd('I'); off = rd('Q')
        ts.append([name, dims, ty, off])
    align = kv.get('general.alignment', 32)
    data0 = (o[0] + align - 1)//align*align
    ts.sort(key=lambda x: x[3])
    for i,t in enumerate(ts):
        end = ts[i+1][3] if i+1 < len(ts) else filesize - data0
        t.append(end - t[3])
    return ver, kv, ts, data0
if __name__ == '__main__':
    path, fs = sys.argv[1], int(sys.argv[2])
    ver, kv, ts, d0 = parse(path, fs)
    print('version', ver, 'tensors', len(ts), 'kv', len(kv), 'data_offset', d0)
    for k,v in kv.items():
        if 'tokenizer.ggml' in k and isinstance(v,str) and v.startswith('<arr'): v = v[:80]
        print(' KV', k, '=', str(v)[:200])
    # group
    def grp(n):
        n = re.sub(r'blk\.\d+\.', 'blk.N.', n); return n
    g = collections.OrderedDict()
    for name, dims, ty, off, sz in ts:
        k = (grp(name), GT.get(ty, f'type{ty}'))
        e = g.setdefault(k, [0,0,0,dims]); e[0]+=1; e[1]+=sz
        ne = 1
        for d in dims: ne*=d
        e[2]+=ne
    tot = 0
    for (n,ty),(c,sz,ne,dims) in sorted(g.items(), key=lambda x:-x[1][1]):
        tot += sz
        print(f'{n:55s} {ty:8s} x{c:3d} dims={dims} {sz/2**30:8.3f} GiB  bpw={sz*8/ne:6.3f}  params={ne/1e9:7.3f}B')
    print('TOTAL', tot/2**30, 'GiB', tot/1e9, 'GB')
