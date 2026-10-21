import json,struct,subprocess,sys
import numpy as np
def hdr(url):
    b=subprocess.run(['curl','-sL','-r','0-7',url],capture_output=True).stdout
    n=struct.unpack('<Q',b)[0]
    h=json.loads(subprocess.run(['curl','-sL','-r',f'8-{7+n}',url],capture_output=True).stdout)
    return h,8+n
def row(url,h,base,name,r):
    t=h[name]; s,e=t['data_offsets']; cols=t['shape'][1]; o=base+s+r*cols*2
    b=subprocess.run(['curl','-sL','-r',f'{o}-{o+cols*2-1}',url],capture_output=True).stdout
    u=np.frombuffer(b,dtype=np.uint16).astype(np.uint32)<<16
    return u.view(np.float32)
D='https://huggingface.co/EAGLE-Corp/Qwen3.8-27B-EAGLE4/resolve/main/model.safetensors'
Q='https://huggingface.co/Qwen/Qwen3.8-27B/resolve/main/'
dh,db=hdr(D)
qe,qeb=hdr(Q+'model-00003-of-00018.safetensors')
ql,qlb=hdr(Q+'model-00018-of-00018.safetensors')
for r in [13,1000,77777,200000]:
    a=row(D,dh,db,'embed_tokens.weight',r); b=row(Q+'model-00003-of-00018.safetensors',qe,qeb,'model.language_model.embed_tokens.weight',r)
    c=row(D,dh,db,'lm_head.weight',r); d=row(Q+'model-00018-of-00018.safetensors',ql,qlb,'lm_head.weight',r)
    cos=lambda x,y: float(x@y/np.linalg.norm(x)/np.linalg.norm(y))
    print(r,'embed equal',np.array_equal(a,b),'cos',round(cos(a,b),4),'| lm_head equal',np.array_equal(c,d),'cos',round(cos(c,d),4),'norms',round(float(np.linalg.norm(c)),3),round(float(np.linalg.norm(d)),3))
print('mtp fc', ql.get('mtp.fc.weight',{}).get('shape'))
mtp=[k for k in ql if k.startswith('mtp.')]
print(len(mtp), sorted(mtp)[:40])
