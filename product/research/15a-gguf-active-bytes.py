import subprocess,sys,collections,re
def run(path,nused,nexp,tied):
    out=subprocess.run(['python3',__import__('os').path.join(__import__('os').path.dirname(__file__),'15a-ggufls.py'),path],capture_output=True,text=True).stdout.splitlines()
    cats=collections.Counter();cnt=collections.Counter();unk=0
    for l in out:
        m=re.match(r'(\S+)\s+(\S+)\s+(\[.*?\])\s+([\d.]+) MB',l)
        if not m: continue
        n,t,dims,mb=m.group(1),m.group(2),m.group(3),float(m.group(4))
        if t=='?': unk+=1
        if '_exps' in n: f=nused/nexp; c='experts'
        elif n=='token_embd.weight': f=1 if tied else 0; c='head(tied embd)'
        elif n=='output.weight': f=1; c='head'
        elif 'conv' in n or 'shortconv' in n: f=1; c='shortconv'
        elif 'ssm' in n: f=1; c='ssm/gdn'
        elif n.startswith('blk') and 'attn' in n and 'norm' not in n: f=1; c='attn'
        elif 'gate_inp' in n or 'exp_probs' in n: f=1; c='router'
        elif 'ffn' in n and 'norm' not in n: f=1; c='dense ffn'
        elif 'mtp' in n or 'nextn' in n: f=0; c='mtp(not in plain)'
        else: f=1; c='other'
        cats[c]+=mb*f; cnt[c]+=1
    act=sum(cats.values())
    print('==',path.split('/')[-1],'unknown-type tensors:',unk)
    for c,v in cats.most_common(): print('  %-20s %9.1f MB (%d)'%(c,v,cnt[c]))
    print('  ACTIVE %.3f GB/token -> floor 960GB/s %.3f ms | 936 %.3f ms | 448 %.3f ms'%(act/1e3,act/960,act/936,act/448))
run(sys.argv[1],4,64,True)
