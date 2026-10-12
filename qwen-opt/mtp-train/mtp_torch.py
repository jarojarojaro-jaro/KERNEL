"""PyTorch mirror of llama.cpp qwen35.cpp graph_mtp (Qwen3.5/3.8 dense MTP / nextn head, blk.<n_layer>).

Weights are dequantized from the GGUF (gguf-py of the fork), the frozen token embedding (Q4_K) and the
reduced-vocabulary LM head rows (Q6_K, draft vocab order) are cached as fp16 .npy next to this file.

Data flow per pass (qwen35.cpp:569-656):
  x = eh_proj([enorm(emb(tok)); hnorm(h)])            # embedding first
  a = attn_norm(x); q|gate = per-head interleaved [q(256) | gate(256)]; q/k RMS-normed per head
  IMRoPE with equal text positions == NeoX rope on the first n_rot=64 dims, base 1e7
  attn (GQA 24/4, scale 1/16, causal) * sigmoid(gate) -> wo -> + x
  -> post_attention_norm -> SwiGLU FFN -> + residual -> shared_head_norm (= h_nextn) -> head
GGUF norm weights already include the Qwen3.5 +1, so norms are plain x * w.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.expanduser("~/llama-master/gguf-py"))
import gguf  # noqa: E402
from gguf.quants import dequantize  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("MTP_CACHE", HERE / "cache"))


class Cfg:
    n_embd = 5120
    n_head = 24
    n_head_kv = 4
    head_dim = 256
    n_rot = 64
    rope_base = 1e7
    eps = 1e-6
    n_ff = 17408


MTP_TENSORS = ["nextn.eh_proj", "nextn.enorm", "nextn.hnorm", "nextn.shared_head_norm", "attn_norm",
               "attn_q", "attn_k", "attn_v", "attn_q_norm", "attn_k_norm", "attn_output",
               "post_attention_norm", "ffn_gate", "ffn_up", "ffn_down"]


def _deq(t) -> np.ndarray:
    a = dequantize(np.asarray(t.data), t.tensor_type)
    return a.reshape([int(x) for x in reversed(t.shape)]) if a.ndim == 1 and len(t.shape) > 1 else a


def _deq_rows(t, rows: np.ndarray | None, chunk: int = 8192) -> np.ndarray:
    """Dequantize (a subset of) rows of a 2D quantized tensor to fp16."""
    data = np.asarray(t.data)  # [n_rows, row_bytes] for quantized types
    rows = np.arange(data.shape[0]) if rows is None else rows
    out = np.empty((len(rows), int(t.shape[0])), dtype=np.float16)
    for i in range(0, len(rows), chunk):
        out[i:i + chunk] = dequantize(data[rows[i:i + chunk]], t.tensor_type).astype(np.float16)
    return out


def load_gguf_weights(gguf_path: str, dvocab: np.ndarray, layer: int = 64) -> dict[str, np.ndarray]:
    """fp32 MTP block weights + fp16 token_embd (all rows) + fp16 draft head rows (dvocab order)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    tag = Path(gguf_path).stem
    r = gguf.GGUFReader(gguf_path)
    tens = {t.name: t for t in r.tensors}
    w = {}
    for n in MTP_TENSORS:
        t = tens[f"blk.{layer}.{n}.weight"]
        w[n] = _deq(t).astype(np.float32)
    f_emb = CACHE / f"{tag}.token_embd.f16.npy"
    if not f_emb.exists():
        np.save(f_emb, _deq_rows(tens["token_embd.weight"], None))
    w["token_embd"] = np.load(f_emb, mmap_mode="r")
    f_head = CACHE / f"{tag}.head{len(dvocab)}.f16.npy"
    if not f_head.exists():
        np.save(f_head, _deq_rows(tens["output.weight"], dvocab))
    w["head"] = np.load(f_head, mmap_mode="r")
    return w


def rms(x: torch.Tensor, w: torch.Tensor, eps: float) -> torch.Tensor:
    xf = x.float()
    return (xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + eps)).to(x.dtype) * w


def q4_0_roundtrip(x: torch.Tensor) -> torch.Tensor:
    """Emulate a q4_0 KV cache store/load (blocks of 32 along the last dim)."""
    shp = x.shape
    b = x.float().reshape(-1, 32)
    idx = b.abs().argmax(-1, keepdim=True)
    mx = torch.gather(b, 1, idx)
    d = (mx / -8).half().float()
    inv = torch.where(d != 0, 1.0 / d, torch.zeros_like(d))
    q = torch.clamp(torch.floor(b * inv + 8.5), 0, 15)  # ggml: (int8)(x*id + 8.5), min(15, ...)
    return ((q - 8) * d).reshape(shp).to(x.dtype)


class MTPHead(torch.nn.Module):
    def __init__(self, w: dict[str, np.ndarray], device="cuda", dtype=torch.float32, cfg=Cfg):
        super().__init__()
        self.cfg = cfg
        P = lambda a: torch.nn.Parameter(torch.from_numpy(np.ascontiguousarray(a)).to(device, dtype))  # noqa: E731
        self.eh_proj = P(w["nextn.eh_proj"])
        self.enorm, self.hnorm, self.head_norm = P(w["nextn.enorm"]), P(w["nextn.hnorm"]), P(w["nextn.shared_head_norm"])
        self.attn_norm, self.post_norm = P(w["attn_norm"]), P(w["post_attention_norm"])
        self.wq, self.wk, self.wv, self.wo = P(w["attn_q"]), P(w["attn_k"]), P(w["attn_v"]), P(w["attn_output"])
        self.q_norm, self.k_norm = P(w["attn_q_norm"]), P(w["attn_k_norm"])
        self.w_gate, self.w_up, self.w_down = P(w["ffn_gate"]), P(w["ffn_up"]), P(w["ffn_down"])
        # frozen: token embedding stays on CPU (gathered per batch), draft head on the device
        self.embd = torch.from_numpy(np.asarray(w["token_embd"]))
        self.register_buffer("head", torch.from_numpy(np.ascontiguousarray(w["head"])).to(device, dtype))
        self.device, self.dtype = device, dtype
        inv = 1.0 / (cfg.rope_base ** (torch.arange(0, cfg.n_rot, 2, dtype=torch.float64) / cfg.n_rot))
        self.register_buffer("inv_freq", inv.float().to(device))

    def emb(self, tok: torch.Tensor) -> torch.Tensor:
        return self.embd[tok.cpu()].to(self.device, self.dtype)

    def rope(self, x: torch.Tensor, pos: torch.Tensor) -> torch.Tensor:
        # x [T, H, D]; NeoX pairs (i, i + n_rot/2) on the first n_rot dims
        c = self.cfg
        ang = pos.float()[:, None] * self.inv_freq[None, :]  # [T, n_rot/2]
        cos, sin = ang.cos()[:, None, :].to(x.dtype), ang.sin()[:, None, :].to(x.dtype)
        x1, x2, rest = x[..., : c.n_rot // 2], x[..., c.n_rot // 2: c.n_rot], x[..., c.n_rot:]
        return torch.cat([x1 * cos - x2 * sin, x2 * cos + x1 * sin, rest], -1)

    def pre_attn(self, e: torch.Tensor, h: torch.Tensor, pos: torch.Tensor, kv_q4: bool):
        """Everything up to attention. Returns residual x, rope'd q, gate, k, v."""
        c = self.cfg
        x = torch.cat([rms(e, self.enorm, c.eps), rms(h, self.hnorm, c.eps)], -1) @ self.eh_proj.T
        a = rms(x, self.attn_norm, c.eps)
        T = a.shape[0]
        qf = (a @ self.wq.T).view(T, c.n_head, 2 * c.head_dim)
        q, gate = qf[..., : c.head_dim], qf[..., c.head_dim:]
        q = self.rope(rms(q, self.q_norm, c.eps), pos)
        k = self.rope(rms((a @ self.wk.T).view(T, c.n_head_kv, c.head_dim), self.k_norm, c.eps), pos)
        v = (a @ self.wv.T).view(T, c.n_head_kv, c.head_dim)
        if kv_q4:
            k, v = q4_0_roundtrip(k), q4_0_roundtrip(v)
        return x, q, gate, k, v

    def post_attn(self, x, o, gate):
        c = self.cfg
        T = x.shape[0]
        o = (o * torch.sigmoid(gate)).reshape(T, c.n_head * c.head_dim) @ self.wo.T
        x = x + o
        f = rms(x, self.post_norm, c.eps)
        f = (F.silu(f @ self.w_gate.T) * (f @ self.w_up.T)) @ self.w_down.T
        hn = rms(x + f, self.head_norm, c.eps)
        return hn

    def logits(self, hn):
        return hn @ self.head.T

    def forward_tf(self, tok, h_prev, pos, kv_q4=False):
        """Teacher-forced pass over a whole sequence (causal). tok[T], h_prev[T, n_embd] = target h at p-1.
        Returns h_nextn [T, n_embd] and the (k, v) cache [T, Hkv, D]."""
        c = self.cfg
        x, q, gate, k, v = self.pre_attn(self.emb(tok), h_prev, pos, kv_q4)
        rep = c.n_head // c.n_head_kv
        o = F.scaled_dot_product_attention(q.transpose(0, 1)[None], k.repeat_interleave(rep, 1).transpose(0, 1)[None],
                                           v.repeat_interleave(rep, 1).transpose(0, 1)[None], is_causal=True,
                                           scale=1.0 / c.head_dim ** 0.5)[0].transpose(0, 1)
        return self.post_attn(x, o, gate), (k, v)

    def forward_chain_step(self, tok, h, pos, kv_prefix, kv_chain, kv_q4=False, chunk=512):
        """One recursive draft step for every start position t at once.
        tok/h/pos [N]: inputs of step k for start t (pos = t + k - 1).
        kv_prefix (k, v) [T, Hkv, D]: teacher-forced cache; start t sees prefix positions 0..t (row t = start).
        kv_chain: list of (k, v) [N, Hkv, D] from earlier chain steps of the same start (steps 2..k-1).
        Returns h_nextn [N, n_embd] and this step's (k, v)."""
        c = self.cfg
        x, q, gate, k, v = self.pre_attn(self.emb(tok), h, pos, kv_q4)
        rep = c.n_head // c.n_head_kv
        kp, vp = kv_prefix
        Tp = kp.shape[0]
        chain_k = torch.stack([kc for kc, _ in kv_chain] + [k], 1)  # [N, j, Hkv, D]
        chain_v = torch.stack([vc for _, vc in kv_chain] + [v], 1)
        scale = 1.0 / c.head_dim ** 0.5
        N = tok.shape[0]
        out = torch.empty(N, c.n_head, c.head_dim, device=q.device, dtype=q.dtype)
        start = pos - len(kv_chain) - 1  # t for every row (pos = t + k - 1, k-1 = len(kv_chain) + 1 ... )
        qg = q.view(N, c.n_head_kv, rep, c.head_dim)
        for i in range(0, N, chunk):
            sl = slice(i, i + chunk)
            sp = torch.einsum("ngrd,sgd->ngrs", qg[sl].float(), kp.float()) * scale       # [n, Hkv, rep, Tp]
            mask = torch.arange(Tp, device=q.device)[None, :] > start[sl][:, None]       # key s > t masked
            sp = sp.masked_fill(mask[:, None, None, :], float("-inf"))
            sc = torch.einsum("ngrd,njgd->ngrj", qg[sl].float(), chain_k[sl].float()) * scale  # [n, Hkv, rep, j]
            pr = torch.softmax(torch.cat([sp, sc], -1), -1)
            o = torch.einsum("ngrs,sgd->ngrd", pr[..., :Tp], vp.float()) + \
                torch.einsum("ngrj,njgd->ngrd", pr[..., Tp:], chain_v[sl].float())
            out[sl] = o.reshape(-1, c.n_head, c.head_dim).to(q.dtype)
        return self.post_attn(x, out, gate), (k, v)

    @torch.no_grad()
    def draft_chain(self, tok, h_tgt, n_prompt, n_draft, kv_q4=False):
        """Greedy draft chains (draft-vocab argmax) from every start t = n_prompt-1 .. T-2, like the server.
        tok[T] token ids, h_tgt[T, n_embd] target h at each position. Returns
        ids [N, n_draft] (draft-vocab indices) and logits list per depth [N, n_vocab_dft] (float32, on device)."""
        T = tok.shape[0]
        dev = self.device
        h_prev = torch.cat([torch.zeros_like(h_tgt[:1]), h_tgt[:-1]], 0)
        pos_all = torch.arange(T, device=dev)
        hn_tf, kv_tf = self.forward_tf(tok, h_prev, pos_all, kv_q4)
        starts = torch.arange(n_prompt - 1, T - 1, device=dev)
        lg = self.logits(hn_tf[starts]).float()
        ids = [lg.argmax(-1)]
        logits = [lg]
        h = hn_tf[starts]
        kv_chain = []
        for k in range(2, n_draft + 1):
            tok_k = self.dvocab_t[ids[-1]]
            h, kv = self.forward_chain_step(tok_k, h, starts + k - 1, kv_tf, kv_chain, kv_q4)
            kv_chain.append(kv)
            lg = self.logits(h).float()
            logits.append(lg)
            ids.append(lg.argmax(-1))
        return torch.stack(ids, 1), logits, hn_tf
