#!/usr/bin/env python3
"""Range-read GGUF header from a URL; print KV (short) and tensor type histogram (bytes, elements, bpw).
Usage: ggufhead.py URL [outjson]"""
import json, struct, sys, subprocess, collections

TYPES = {0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',9:'Q8_1',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',15:'Q8_K',
16:'IQ2_XXS',17:'IQ2_XS',18:'IQ3_XXS',19:'IQ1_S',20:'IQ4_NL',21:'IQ3_S',22:'IQ2_S',23:'IQ4_XS',24:'I8',25:'I16',26:'I32',27:'I64',28:'F64',29:'IQ1_M',30:'BF16',
34:'TQ1_0',35:'TQ2_0',39:'MXFP4',40:'NVFP4',41:'Q1_0',42:'Q2_0',142:'PQ2_0',143:'PTQ1_0'}

def fetch(url, start, end):
    r = subprocess.run(['curl','-sL','-r',f'{start}-{end}',url], capture_output=True, check=True)
    return r.stdout

def size_of(url):
    r = subprocess.run(['curl','-sIL',url], capture_output=True, text=True).stdout
    sz = None
    for line in r.splitlines():
        l = line.lower()
        if l.startswith('x-linked-size:') or l.startswith('content-length:'):
            sz = int(line.split(':')[1])
            if l.startswith('x-linked-size'): return sz
    return sz

class Buf:
    def __init__(self, url):
        self.url=url; self.data=b''; self.pos=0
    def need(self, n):
        while self.pos+n > len(self.data):
            more = max(8<<20, n)
            chunk = fetch(self.url, len(self.data), len(self.data)+more-1)
            if not chunk: raise EOFError
            self.data += chunk
    def read(self, n):
        self.need(n); b=self.data[self.pos:self.pos+n]; self.pos+=n; return b
    def u32(self): return struct.unpack('<I', self.read(4))[0]
    def u64(self): return struct.unpack('<Q', self.read(8))[0]
    def s(self): n=self.u64(); return self.read(n).decode('utf-8','replace')

SC = {0:('<B',1),1:('<b',1),2:('<H',2),3:('<h',2),4:('<I',4),5:('<i',4),6:('<f',4),7:('<?',1),10:('<Q',8),11:('<q',8),12:('<d',8)}
def val(b, t):
    if t in SC: f,n=SC[t]; return struct.unpack(f,b.read(n))[0]
    if t==8: return b.s()
    if t==9:
        at=b.u32(); n=b.u64()
        if at in SC:
            f,sz=SC[at]; raw=b.read(sz*n)
            return {'array_type':at,'len':n,'head':[struct.unpack(f,raw[i*sz:(i+1)*sz])[0] for i in range(min(n,8))]}
        items=[val(b,at) for _ in range(n)]
        return {'array_type':at,'len':n,'head':items[:4]}
    raise ValueError(t)

def main(url, out=None):
    b=Buf(url)
    assert b.read(4)==b'GGUF'
    ver=b.u32(); nt=b.u64(); nkv=b.u64()
    kv={}
    for _ in range(nkv):
        k=b.s(); t=b.u32(); kv[k]=val(b,t)
    tens=[]
    for _ in range(nt):
        name=b.s(); nd=b.u32(); dims=[b.u64() for _ in range(nd)]; t=b.u32(); off=b.u64()
        tens.append((name,dims,t,off))
    align=kv.get('general.alignment',32)
    data_start=(b.pos+align-1)//align*align
    fsz=size_of(url)
    offs=sorted(o for _,_,_,o in tens)
    nxt={o:(offs[i+1] if i+1<len(offs) else fsz-data_start) for i,o in enumerate(offs)}
    hist=collections.defaultdict(lambda:[0,0,0])
    rows=[]
    for name,dims,t,off in tens:
        ne=1
        for d in dims: ne*=d
        nb=nxt[off]-off
        tn=TYPES.get(t,str(t))
        h=hist[tn]; h[0]+=1; h[1]+=ne; h[2]+=nb
        rows.append({'name':name,'dims':dims,'type':tn,'bytes':nb})
    tot_e=sum(h[1] for h in hist.values()); tot_b=sum(h[2] for h in hist.values())
    print(f'GGUF v{ver} tensors={nt} kv={nkv} file={fsz} data_start={data_start}')
    for k,v in kv.items():
        if k.startswith('tokenizer.ggml.') and isinstance(v,dict): continue
        if k=='tokenizer.chat_template': v=f'<{len(v)} chars>'
        print(f'  {k} = {v}')
    print(f'  total elements={tot_e/1e9:.3f}G bytes={tot_b/1e9:.3f}GB avg bpw={8*tot_b/tot_e:.3f}')
    for tn,(c,e,nb) in sorted(hist.items(), key=lambda x:-x[1][2]):
        print(f'  {tn:8s} n={c:4d} elem%={100*e/tot_e:5.1f} bytes={nb/1e9:6.3f}GB bpw={8*nb/e:.3f}')
    if out:
        json.dump({'kv':{k:(v if not isinstance(v,dict) else {'len':v['len']}) for k,v in kv.items() if k!='tokenizer.chat_template'},'tensors':rows,'file':fsz},open(out,'w'),indent=0)

if __name__=='__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else None)
