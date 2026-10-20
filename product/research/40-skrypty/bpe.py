"""Report 40: minimal byte-level BPE tokenizer for Qwen3.8 (GGUF vocab + merges, qwen35 pre-tokenizer) for rebuilding
the E0 prompt token ids on CPU. \\p{L} ~ [^\\W\\d_], \\p{N} ~ \\d (enough for PL/EN prose; checked against the
server's token ids by pa_extract_prep.py)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

CACHE = Path.home() / "qwen-opt/prose-accept/cache"
GGUF = Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"
L = r"[^\W\d_]"
NOT_LN = r"(?:[^\r\n\w]|_)"
NOT_SLN = r"(?:[^\s\w]|_)"
PAT = re.compile(r"(?i:'s|'t|'re|'ve|'m|'ll|'d)|" + NOT_LN + "?" + L + r"+|\d| ?" + NOT_SLN + r"+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+")
SPECIAL = ["<|im_start|>", "<|im_end|>", "<think>", "</think>", "<|endoftext|>"]


def _byte_encoder():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


class Tok:
    def __init__(self):
        f = CACHE / "bpe.json"
        if f.exists():
            d = json.loads(f.read_text())
        else:
            import gguf
            r = gguf.GGUFReader(str(GGUF))
            tf, mf = r.fields["tokenizer.ggml.tokens"], r.fields["tokenizer.ggml.merges"]
            d = {"tokens": [bytes(tf.parts[i]).decode("utf-8", "replace") for i in tf.data],
                 "merges": [bytes(mf.parts[i]).decode("utf-8", "replace") for i in mf.data]}
            CACHE.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(d, ensure_ascii=False))
        self.vocab = {t: i for i, t in enumerate(d["tokens"])}
        self.ranks = {tuple(m.split(" ", 1)): i for i, m in enumerate(d["merges"])}
        self.be = _byte_encoder()

    @lru_cache(maxsize=None)
    def _bpe(self, word: str) -> tuple[int, ...]:
        parts = list(word)
        while len(parts) > 1:
            best, bi = None, -1
            for i in range(len(parts) - 1):
                r = self.ranks.get((parts[i], parts[i + 1]))
                if r is not None and (best is None or r < best):
                    best, bi = r, i
            if best is None:
                break
            parts[bi:bi + 2] = [parts[bi] + parts[bi + 1]]
        return tuple(self.vocab[p] for p in parts)

    def encode(self, text: str) -> list[int]:
        out = []
        sp = "(" + "|".join(re.escape(s) for s in SPECIAL) + ")"
        for chunk in re.split(sp, text):
            if not chunk:
                continue
            if chunk in SPECIAL:
                out.append(self.vocab[chunk])
                continue
            for w in PAT.findall(chunk):
                out.extend(self._bpe("".join(self.be[b] for b in w.encode("utf-8"))))
        return out


def chat_prompt(user: str) -> str:
    """Qwen3.8 GGUF template, one user turn, add_generation_prompt, enable_thinking false."""
    return f"<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
