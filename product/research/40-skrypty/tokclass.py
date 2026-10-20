"""Report 40: token strings of Qwen3.8 (from the GGUF, cached) and a coarse token class per id.

Classes (byte-level BPE, 'Ġ' = leading space, 'Ċ' = newline):
  oov    outside the 64k draft vocab (rank >= 65536 in draft_vocab_qwen38.txt)
  nl     contains a newline / only whitespace
  punct  punctuation only (optionally with a leading space): , . ; : ! ? - – — " „ ” ( ) … ' * etc.
  digit  contains a digit
  wstart leading space + letters (start of a word)
  cont   letters without a leading space (continuation of a word: Polish inflection endings, subword pieces)
  other  everything else (special, mixed)
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import numpy as np

CACHE = Path.home() / "qwen-opt/prose-accept/cache"
GGUF = Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"
RANK = Path.home() / "models/draft/draft_vocab_qwen38.txt"
CLASSES = ["oov", "nl", "punct", "digit", "wstart", "cont", "other"]


def _bytes_decoder():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def token_strings() -> list[str]:
    f = CACHE / "tokens.json"
    if f.exists():
        return json.loads(f.read_text())
    import gguf
    r = gguf.GGUFReader(str(GGUF))
    fld = r.fields["tokenizer.ggml.tokens"]
    raw = [bytes(fld.parts[i]).decode("utf-8", "replace") for i in fld.data]
    dec = _bytes_decoder()
    out = []
    for t in raw:
        try:
            out.append(bytes(dec[c] for c in t).decode("utf-8", "replace"))
        except KeyError:  # special tokens are stored verbatim
            out.append(t)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


def draft_rank(n_vocab: int) -> np.ndarray:
    order = np.loadtxt(RANK, dtype=np.int64)
    rk = np.full(n_vocab, len(order), np.int64)
    rk[order] = np.arange(len(order))
    return rk


def _cls(s: str) -> str:
    if s.startswith("<|") or s.startswith("<") and s.endswith(">") and len(s) > 2:
        return "other"
    if "\n" in s or (s and s.strip() == ""):
        return "nl"
    t = s[1:] if s.startswith(" ") else s
    if t and all(unicodedata.category(c).startswith(("P", "S")) for c in t):
        return "punct"
    if any(c.isdigit() for c in t):
        return "digit"
    if t and all(c.isalpha() for c in t):
        return "wstart" if s.startswith(" ") else "cont"
    return "other"


def classes(n_vocab: int) -> tuple[np.ndarray, list[str]]:
    """class index per token id (oov overrides the string class), plus the token strings."""
    strs = token_strings()
    rk = draft_rank(n_vocab)
    c = np.array([CLASSES.index(_cls(s)) for s in strs[:n_vocab]] + [CLASSES.index("other")] * (n_vocab - len(strs)))
    c[rk >= 65536] = CLASSES.index("oov")
    return c, strs
