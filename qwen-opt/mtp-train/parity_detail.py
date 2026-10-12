"""Depth-1 parity detail: PyTorch mirror (fp32 and bf16) vs llama.cpp MTP logits on the parity sequences.
Reports top-1 agreement, logit rel-L2, and the llama.cpp top-1/top-2 margin where top-1 disagrees."""
import sys
from pathlib import Path

import numpy as np
import torch

from analyze import load, read_seqs_bin
from mtp_torch import MTPHead, load_gguf_weights

d, seqs_prefix = Path(sys.argv[1]), sys.argv[2]
hd, seqs = load(d, Path(seqs_prefix + ".idx.jsonl"))
toks = read_seqs_bin(seqs_prefix + ".bin")
n_vd = int(hd["n_vocab_dft"])
dvocab = np.loadtxt(Path.home() / "models/draft/draft_vocab_qwen38.txt", dtype=np.int64, max_rows=n_vd)
d1 = torch.from_numpy(np.fromfile(d / "d1.f32", dtype=np.float32).reshape(-1, n_vd))
w = load_gguf_weights(str(Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"), dvocab)
for dt in (torch.float32, torch.bfloat16):
    tm = MTPHead(w, dtype=dt)
    o, ref_all, mine_all = 0, [], []
    for si in range(int(hd["parity_seqs"])):
        s, tok = seqs[si], torch.from_numpy(toks[si]).cuda()
        h = torch.from_numpy(np.asarray(s["h"])).cuda().to(dt)
        h_prev = torch.cat([torch.zeros_like(h[:1]), h[:-1]], 0)
        with torch.no_grad():
            hn, _ = tm.forward_tf(tok, h_prev, torch.arange(len(tok), device="cuda"))
        n_p = min(int(hd["parity_max"]), s["n_tok"] - s["n_prompt"])
        mine_all.append(tm.logits(hn[s["n_prompt"] - 1:s["n_prompt"] - 1 + n_p]).float().cpu())
        ref_all.append(d1[o:o + n_p])
        o += n_p
    ref, mine = torch.cat(ref_all), torch.cat(mine_all)
    agree = ref.argmax(-1) == mine.argmax(-1)
    rel = (ref - mine).norm(dim=-1) / ref.norm(dim=-1)
    top2 = ref.topk(2, -1).values
    margin = top2[:, 0] - top2[:, 1]
    pr_r, pr_m = ref.softmax(-1), mine.softmax(-1)
    tv = 0.5 * (pr_r - pr_m).abs().sum(-1)
    print(f"{str(dt):15s} n={len(ref)} top1={agree.float().mean():.4f} relL2 mean={rel.mean():.4f} "
          f"p99={rel.quantile(0.99):.4f} TV(p_llama,p_torch) mean={tv.mean():.4f} | llama margin at disagreements: "
          f"median={margin[~agree].median() if (~agree).any() else float('nan'):.3f} "
          f"(all positions median {margin.median():.3f})")
    del tm
    torch.cuda.empty_cache()
