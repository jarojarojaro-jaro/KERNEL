#!/usr/bin/env python3
"""EvalPlus codegen against an OpenAI-compatible llama-server (jakość-mini gate).

Uses evalplus's own codegen() loop (prompt = instruction prefix + ```python task```, system message
"You are a helpful assistant good at coding.", sanitize(), samples/raw jsonl) with the evalplus
OpenAIChatDecoder. Two deliberate deviations from `evalplus.codegen --backend openai`:
  * no 100 s SIGALRM retry loop (a thinking answer can run longer; evalplus would retry forever),
    instead a 1800 s HTTP timeout and max_tokens 32768 (reasoning tokens count against max_tokens);
  * per-answer usage/timings (llama-server `timings`) and reasoning length go to <out>.stats.jsonl.
Greedy: temperature 0, n=1 (evalplus also sends top_p 0.95, irrelevant at T=0). The thinking effort is
the server's (--reasoning-effort from run-llm.sh EFFORT), i.e. exactly what production clients get.
"""
import argparse, json, os, time

import openai
from evalplus.codegen import codegen
from evalplus.provider.openai import OpenAIChatDecoder

PREFIX = ("Please provide a self-contained Python script that solves the following problem "
          "in a markdown code block:")  # evalplus run_codegen default


class StatsDecoder(OpenAIChatDecoder):
    def __init__(self, stats_path, **kw):
        super().__init__(**kw)
        self.client = openai.OpenAI(api_key="none", base_url=kw["base_url"], timeout=1800, max_retries=2)
        self.stats_path = stats_path

    def codegen(self, prompt, do_sample=False, num_samples=1):
        message = self.instruction_prefix + f"\n```python\n{prompt.strip()}\n```"
        t0 = time.time()
        r = self.client.chat.completions.create(
            model=self.name, max_tokens=self.max_new_tokens, temperature=0, n=1, top_p=0.95,
            messages=[{"role": "system", "content": "You are a helpful assistant good at coding."},
                      {"role": "user", "content": message}])
        dt = time.time() - t0
        msg = r.choices[0].message
        extra = r.model_extra or {}
        rc = (msg.model_extra or {}).get("reasoning_content") or ""
        with open(self.stats_path, "a") as f:
            f.write(json.dumps({"prompt_head": prompt[:80], "wall_s": round(dt, 3),
                                "finish": r.choices[0].finish_reason,
                                "completion_tokens": r.usage.completion_tokens if r.usage else None,
                                "prompt_tokens": r.usage.prompt_tokens if r.usage else None,
                                "reasoning_chars": len(rc), "content_chars": len(msg.content or ""),
                                "timings": extra.get("timings")}) + "\n")
        return [msg.content or ""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["humaneval", "mbpp"])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", default="local")
    ap.add_argument("--out", required=True, help="samples .jsonl (resumable)")
    ap.add_argument("--max-tokens", type=int, default=32768)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    dec = StatsDecoder(a.out.replace(".jsonl", ".stats.jsonl"), name=a.model, base_url=a.base_url,
                       batch_size=1, temperature=0.0, max_new_tokens=a.max_tokens,
                       instruction_prefix=PREFIX, response_prefix="")
    codegen(a.out, dec, a.dataset, greedy=True, n_samples=1)


if __name__ == "__main__":
    main()
