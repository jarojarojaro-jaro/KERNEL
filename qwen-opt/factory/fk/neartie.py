"""Near-tie gate (after tqLLM tests/golden_check.py): a greedy divergence is a numeric tie, not a bug, when at the
first differing position the candidate chose the reference's runner-up and the reference's top-1 vs top-2 logit
margin is <= 0.1. Logprob differences equal logit differences (softmax is shift-invariant), so the margin comes from
llama-server `logprobs: true, top_logprobs: 2` of the reference run.

Token stream entry (from choices[0].logprobs.content of /v1/chat/completions):
  {"id": int, "token": str, "logprob": float, "top_logprobs": [{"id": int, "token": str, "logprob": float}, ...]}
"""
from __future__ import annotations

MARGIN = 0.1


def compare(ref: list[dict], cand: list[dict], margin: float = MARGIN) -> dict:
    n = min(len(ref), len(cand))
    for i in range(n):
        if ref[i]["id"] != cand[i]["id"]:
            top = ref[i].get("top_logprobs") or []
            if len(top) < 2:
                return {"status": "DIVERGE", "pos": i, "reason": "reference has no runner-up logprob at the divergence"}
            top = sorted(top, key=lambda t: -t["logprob"])
            m = top[0]["logprob"] - top[1]["logprob"]
            info = {"pos": i, "ref_token": ref[i].get("token"), "cand_token": cand[i].get("token"),
                    "runner_up": top[1].get("token"), "margin": m}
            if top[0]["id"] != ref[i]["id"]:
                return {"status": "DIVERGE", **info, "reason": "reference token is not its own top-1 (not greedy?)"}
            if cand[i]["id"] == top[1]["id"] and m <= margin:
                return {"status": "NEAR-TIE", **info}
            why = "candidate token is not the runner-up" if cand[i]["id"] != top[1]["id"] else \
                f"margin {m:.4f} > {margin}"
            return {"status": "DIVERGE", **info, "reason": why}
    if len(ref) != len(cand):
        return {"status": "DIVERGE", "pos": n, "reason": f"one stream ends early ({len(ref)} vs {len(cand)} tokens)"}
    return {"status": "IDENTICAL", "pos": None}


def gate(pairs: dict[str, tuple[list, list]], margin: float = MARGIN) -> dict:
    """pairs: prompt -> (ref tokens, cand tokens). PASS when every prompt is IDENTICAL or NEAR-TIE."""
    res = {k: compare(r, c, margin) for k, (r, c) in pairs.items()}
    ok = all(v["status"] in ("IDENTICAL", "NEAR-TIE") for v in res.values())
    return {"verdict": "PASS" if ok else "FAIL", "prompts": res}


def tokens_from_response(resp: dict) -> list[dict]:
    lp = (resp.get("choices") or [{}])[0].get("logprobs") or {}
    return [{"id": t.get("id"), "token": t.get("token"), "logprob": t.get("logprob"),
             "top_logprobs": [{"id": x.get("id"), "token": x.get("token"), "logprob": x.get("logprob")}
                              for x in t.get("top_logprobs") or []]}
            for t in lp.get("content") or []]
