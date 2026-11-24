"""Minimal GGUF v3 reader/writer for repacking (no ggml type knowledge beyond block sizes we need)."""
import struct
VT = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
# ggml type -> (block elems, block bytes)
BLK = {0:(1,4),1:(1,2),30:(1,2),8:(32,34),2:(32,18),12:(256,144),13:(256,176),14:(256,210),10:(256,84),11:(256,110),
       42:(64,18),142:(128,34),143:(128,28)}
class R:
    def __init__(s,b,o=0): s.b=b; s.o=o
    def u(s,f): v=struct.unpack_from('<'+f,s.b,s.o); s.o+=struct.calcsize('<'+f); return v[0]
    def str(s): n=s.u('Q'); v=s.b[s.o:s.o+n].decode('utf-8','replace'); s.o+=n; return v
    def val(s,t):
        if t==8: return s.str()
        if t==9:
            et=s.u('I'); n=s.u('Q'); return [s.val(et) for _ in range(n)]
        return s.u(VT[t])
def parse(buf):
    r=R(buf); assert buf[:4]==b'GGUF'; r.o=4; ver=r.u('I'); nt=r.u('Q'); nkv=r.u('Q')
    kv_start=r.o; kv={}
    for _ in range(nkv):
        k=r.str(); t=r.u('I'); kv[k]=(t,r.val(t))
    kv_end=r.o; tensors=[]
    for _ in range(nt):
        name=r.str(); nd=r.u('I'); dims=[r.u('Q') for _ in range(nd)]; ty=r.u('I'); off=r.u('Q')
        tensors.append(dict(name=name,dims=dims,type=ty,off=off))
    align=kv.get('general.alignment',(4,32))[1]
    data_start=(r.o+align-1)//align*align
    for t in tensors:
        n=1
        for d in t['dims']: n*=d
        be,bb=BLK[t['type']]; t['nbytes']=n//be*bb
    return dict(ver=ver,kv=kv,kv_raw=buf[kv_start:kv_end],nkv=nkv,tensors=tensors,align=align,data_start=data_start)
def w_str(s): b=s.encode(); return struct.pack('<Q',len(b))+b
def header(nkv,kv_raw,tensors,align):
    out=b'GGUF'+struct.pack('<IQQ',3,len(tensors),nkv)+kv_raw
    off=0
    for t in tensors:
        t['off']=off
        out+=w_str(t['name'])+struct.pack('<I',len(t['dims']))+b''.join(struct.pack('<Q',d) for d in t['dims'])+struct.pack('<IQ',t['type'],off)
        off=(off+t['nbytes']+align-1)//align*align
    pad=(-len(out))%align
    return out+b'\0'*pad
