# list GGUF tensors (name type shape bytes) without numpy
import struct, sys, collections
T = {0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',30:'BF16',16:'IQ2_XXS',17:'IQ2_XS',18:'IQ3_XXS',20:'IQ4_NL',21:'IQ3_S',22:'IQ2_S',23:'IQ4_XS'}
BS = {'F32':(1,4),'F16':(1,2),'BF16':(1,2),'Q4_0':(32,18),'Q8_0':(32,34),'Q4_K':(256,144),'Q5_K':(256,176),'Q6_K':(256,210),'Q2_K':(256,84),'Q3_K':(256,110),'Q5_0':(32,22),'IQ4_XS':(256,136),'IQ4_NL':(32,18),'IQ3_XXS':(256,98),'IQ3_S':(256,110),'IQ2_XXS':(256,66),'IQ2_XS':(256,74),'IQ2_S':(256,82)}
f = open(sys.argv[1], 'rb')
def u32(): return struct.unpack('<I', f.read(4))[0]
def u64(): return struct.unpack('<Q', f.read(8))[0]
def s(): n = u64(); return f.read(n).decode()
def val(t):
    sz = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
    if t == 8: return s()
    if t == 9:
        et = u32(); n = u64()
        for _ in range(n): val(et)
        return None
    return f.read(sz[t])
assert f.read(4) == b'GGUF'; u32(); nt = u64(); nkv = u64()
for _ in range(nkv): s(); val(u32())
rows = []
for _ in range(nt):
    name = s(); nd = u32(); dims = [u64() for _ in range(nd)]; t = T.get(u32(), '?'); u64()
    n = 1
    for d in dims: n *= d
    b = n // BS[t][0] * BS[t][1] if t in BS else 0
    rows.append((name, t, dims, b))
for r in rows: print(f"{r[0]:40} {r[1]:5} {str(r[2]):28} {r[3]/1e6:9.2f} MB")
