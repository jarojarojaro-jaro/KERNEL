#!/usr/bin/env python3
"""Report 53: target top-2 logit gap at the first token where two greedy outputs (same prompt) differ.
Needs a running plain llama-server (target only). usage: nt_gap.py --port P A.txt B.txt [--prompt-index 0]"""
import argparse
import json
import math
import urllib.request

PROMPTS = ['Explain how a hash map works, then implement one in C with open addressing.',
           'Napisz krótkie opowiadanie o latarniku i sztormie.']


def post(port, path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--prompt-index", type=int, default=0)
    x = ap.parse_args()
    ta, tb = open(x.a).read(), open(x.b).read()
    ka = post(x.port, "/tokenize", {"content": ta})["tokens"]
    kb = post(x.port, "/tokenize", {"content": tb})["tokens"]
    i = next(j for j in range(min(len(ka), len(kb))) if ka[j] != kb[j])
    prefix = post(x.port, "/detokenize", {"tokens": ka[:i]})["content"]
    tpl = post(x.port, "/apply-template", {"messages": [{"role": "user", "content": PROMPTS[x.prompt_index]}],
                                            "chat_template_kwargs": {"enable_thinking": False}})["prompt"]
    r = post(x.port, "/completion", {"prompt": tpl + prefix, "n_predict": 1, "temperature": 0, "n_probs": 5,
                                     "cache_prompt": False, "post_sampling_probs": False})
    top = r["completion_probabilities"][0]["top_logprobs"]
    pa = post(x.port, "/detokenize", {"tokens": [ka[i]]})["content"]
    pb = post(x.port, "/detokenize", {"tokens": [kb[i]]})["content"]
    gap = top[0]["logprob"] - top[1]["logprob"]
    print(json.dumps({"first_diff_token": i, "a_tok": [ka[i], pa], "b_tok": [kb[i], pb],
                      "top": [[t["id"], t["token"], round(t["logprob"], 5)] for t in top],
                      "top2_logit_gap": round(gap, 5), "p1": round(math.exp(top[0]["logprob"]), 5),
                      "p2": round(math.exp(top[1]["logprob"]), 5)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
