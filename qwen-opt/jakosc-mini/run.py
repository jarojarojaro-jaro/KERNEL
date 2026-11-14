#!/usr/bin/env python3
"""jakość-mini: a 290-question quality benchmark for any model behind an OpenAI-compatible llama-server.

  run.py subsets [--seed S]            build subsets/s<S>/ from data/ (pinned HF revisions, see subsets/s<S>/manifest.json)
  run.py gen   (--base-url URL | --port P) --model-label L [--effort E] [--seed S] [--reuse-humaneval DIR]
  run.py code-eval RUN_DIR [--no-scope]   HumanEval+ execution on CPU in the sandbox (code_eval.py)
  run.py report RUN_DIR                   score + summary.{json,md}

Composition (seed 20261109): GSM8K 50, MMLU-Pro 10 x 14 domains = 140, Global-MMLU pl 50, HumanEval+ 30,
BFCL v3 simple 8 + multiple 6 + parallel 6 = 20. Every request: /v1/chat/completions, the server's own chat template,
temperature 0, seed S, max_tokens 32768 (reasoning tokens count against it), one request at a time.
--effort E sends "reasoning_effort": E per request (the same template kwarg as llama-server --reasoning-effort);
--effort server sends nothing and leaves the server default.

Answer extraction (only message.content, never the reasoning; markdown "*" removed first; no guessing):
  GSM8K     last `Answer: <number>` (case-insensitive, optional $ and thousands commas), else last \\boxed{<number>};
            compared as decimals with the number after "####" in the reference solution.
  MMLU-Pro  last `answer is (X)` / `answer is X` (X in A-J; the official MMLU-Pro regex), else last `Answer: X`,
            else last \\boxed{X}. The official random-letter fallback is NOT used: unparsed = wrong.
  PL        last `Odpowiedź: X` / `Odpowiedz: X` / `Answer: X` (X in A-D), else last `answer is X` / `odpowiedź to X`,
            else last \\boxed{X}.
  HumanEval+ evalplus sanitize() of the reply (as evalplus codegen), pass = base AND plus tests (code_eval.py).
  BFCL      message.tool_calls only (no text parsing), arguments must be valid JSON; checked by the vendored BFCL v3
            AST checker (bfcl_ast_checker.py) against possible_answer.
Accuracy per category with a 95% Wilson interval; tokens = usage.completion_tokens (thinking included).
"""
import argparse, datetime, decimal, hashlib, json, math, os, random, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = ["gsm8k", "mmlu_pro", "pl_mmlu", "humaneval_plus", "bfcl"]
CAT_NAMES = {"gsm8k": "GSM8K", "mmlu_pro": "MMLU-Pro", "pl_mmlu": "PL (Global-MMLU pl)",
             "humaneval_plus": "HumanEval+", "bfcl": "BFCL v3"}
DEFAULT_SEED = 20261109
MAX_TOKENS = 32768

SOURCES = {  # repo, pinned revision, file inside the repo -> local file under data/
    "gsm8k": ("openai/gsm8k", "740312add88f781978c0658806c59bc2815b9866",
              [("main/test-00000-of-00001.parquet", "gsm8k/test.parquet")]),
    "mmlu_pro": ("TIGER-Lab/MMLU-Pro", "b189ec765aa7ed75c8acfea42df31fdae71f97be",
                 [("data/test-00000-of-00001.parquet", "mmlu_pro/test.parquet")]),
    "pl_mmlu": ("CohereLabs/Global-MMLU", "0e619dbeb34206cd48705a1a0ea7fb21cae09993",
                [("pl/test-00000-of-00001.parquet", "global_mmlu_pl/test.parquet")]),
    "bfcl": ("gorilla-llm/Berkeley-Function-Calling-Leaderboard", "61fc0608cfd831fcfbbaa676ebdfef0ed963eeda",
             [(f"{p}BFCL_v3_{c}.json", f"bfcl/{p}BFCL_v3_{c}.json")
              for c in ("simple", "multiple", "parallel") for p in ("", "possible_answer/")]),
}
BFCL_COUNTS = {"simple": 8, "multiple": 6, "parallel": 6}

# ---------------------------------------------------------------- prompts (frozen into the subset files)
EVALPLUS_SYSTEM = "You are a helpful assistant good at coding."
EVALPLUS_PREFIX = ("Please provide a self-contained Python script that solves the following problem "
                   "in a markdown code block:")  # evalplus run_codegen default, identical to ../evalplus/gen.py


def gsm8k_messages(q):
    return [{"role": "user", "content":
             "Solve the following math problem. Reason step by step, then give the final answer on the last line "
             "in the form \"Answer: <number>\" (just the number, no units).\n\nProblem: " + q}]


def mmlu_pro_messages(q, options, category):
    opts = "\n".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(options))
    return [{"role": "user", "content":
             f"The following is a multiple choice question about {category}. Think step by step and then finish "
             f"your answer with \"the answer is (X)\" where X is the correct letter choice.\n\n"
             f"Question: {q}\nOptions:\n{opts}"}]


def pl_messages(q, options):
    opts = "\n".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(options))
    return [{"role": "user", "content":
             "Odpowiedz na poniższe pytanie jednokrotnego wyboru. Pomyśl krok po kroku, a na końcu podaj odpowiedź "
             "w ostatniej linii w formacie \"Odpowiedź: X\", gdzie X to litera poprawnej odpowiedzi (A, B, C lub D)."
             f"\n\nPytanie: {q}\n{opts}"}]


def humaneval_messages(prompt):
    prompt = prompt.strip() + "\n"  # evalplus codegen: task["prompt"].strip() + "\n"
    return [{"role": "system", "content": EVALPLUS_SYSTEM},
            {"role": "user", "content": EVALPLUS_PREFIX + f"\n```python\n{prompt.strip()}\n```"}]


# BFCL v3 function docs -> OpenAI tools, ported from bfcl_eval (gorilla @ 6ea57973c7a6): utils.py
# _func_doc_language_specific_pre_processing (Python hint) and model_handler/utils.py convert_to_tool /
# _cast_to_openai_type with GORILLA_TO_OPENAPI and ModelStyle.OSSMODEL ("." in names -> "_").
GORILLA_TO_OPENAPI = {"integer": "integer", "number": "number", "float": "number", "string": "string",
                      "boolean": "boolean", "bool": "boolean", "array": "array", "list": "array", "dict": "object",
                      "object": "object", "tuple": "array", "any": "string", "byte": "integer", "short": "integer",
                      "long": "integer", "double": "number", "char": "string", "ArrayList": "array",
                      "Array": "array", "HashMap": "object", "Hashtable": "object", "Queue": "array",
                      "Stack": "array", "Any": "string", "String": "string", "Bigint": "integer"}


def _cast_to_openai_type(properties, mapping):
    for key, value in properties.items():
        if "type" not in value:
            properties[key]["type"] = "string"
        else:
            var_type = value["type"]
            if var_type == "float":
                properties[key]["format"] = "float"
                properties[key]["description"] += " This is a float type value."
            properties[key]["type"] = mapping.get(var_type, "string")
        if properties[key]["type"] in ("array", "object"):
            if "properties" in properties[key]:
                properties[key]["properties"] = _cast_to_openai_type(properties[key]["properties"], mapping)
            elif "items" in properties[key]:
                items = properties[key]["items"]
                items["type"] = mapping[items["type"]]
                if items["type"] == "array" and "items" in items:
                    items["items"]["type"] = mapping[items["items"]["type"]]
                elif items["type"] == "object" and "properties" in items:
                    items["properties"] = _cast_to_openai_type(items["properties"], mapping)
    return properties


def bfcl_tools(functions):
    tools = []
    for f in json.loads(json.dumps(functions)):
        f["description"] = f["description"] + " Note that the provided function is in Python 3 syntax."
        f["name"] = re.sub(r"\.", "_", f["name"])
        f["parameters"]["type"] = "object"
        f["parameters"]["properties"] = _cast_to_openai_type(f["parameters"]["properties"], GORILLA_TO_OPENAPI)
        tools.append({"type": "function", "function": f})
    return tools


# ---------------------------------------------------------------- subsets
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cmd_subsets(a):
    import pandas as pd
    out = os.path.join(HERE, "subsets", f"s{a.seed}")
    if os.path.exists(os.path.join(out, "manifest.json")) and not a.force:
        sys.exit(f"{out} exists; subsets are frozen (every model must get the same questions). --force to rebuild")
    os.makedirs(out, exist_ok=True)
    D = os.path.join(HERE, "data")
    for cat, (_, _, files) in SOURCES.items():
        for _, local in files:
            if not os.path.exists(os.path.join(D, local)):
                sys.exit(f"missing data/{local}; run ./fetch-data.sh")
    rng = lambda tag: random.Random(f"{a.seed}:{tag}")
    items = {c: [] for c in CATS}

    d = pd.read_parquet(os.path.join(D, "gsm8k/test.parquet"))
    for i in sorted(rng("gsm8k").sample(range(len(d)), 50)):
        r = d.iloc[i]
        items["gsm8k"].append({"id": f"gsm8k/test/{i}", "cat": "gsm8k", "sub": "", "messages": gsm8k_messages(r.question),
                               "gold": r.answer.split("####")[-1].strip().replace(",", "")})

    d = pd.read_parquet(os.path.join(D, "mmlu_pro/test.parquet"))
    for cat in sorted(d.category.unique()):
        rows = d[d.category == cat]
        for i in sorted(rng(f"mmlu_pro:{cat}").sample(range(len(rows)), 10)):
            r = rows.iloc[i]
            items["mmlu_pro"].append({"id": f"mmlu_pro/{int(r.question_id)}", "cat": "mmlu_pro", "sub": cat,
                                      "messages": mmlu_pro_messages(r.question, list(r.options), cat),
                                      "gold": r.answer, "n_options": len(r.options)})

    d = pd.read_parquet(os.path.join(D, "global_mmlu_pl/test.parquet"))
    for i in sorted(rng("pl_mmlu").sample(range(len(d)), 50)):
        r = d.iloc[i]
        items["pl_mmlu"].append({"id": f"global_mmlu_pl/{r.sample_id}", "cat": "pl_mmlu", "sub": r.subject_category,
                                 "messages": pl_messages(r.question, [r.option_a, r.option_b, r.option_c, r.option_d]),
                                 "gold": r.answer, "subject": r.subject,
                                 "cultural_sensitivity": r.cultural_sensitivity_label})

    from evalplus.data import get_human_eval_plus
    import evalplus
    he = get_human_eval_plus()
    ids = sorted(he, key=lambda t: int(t.split("/")[1]))
    for t in sorted(rng("humaneval_plus").sample(ids, 30), key=lambda t: int(t.split("/")[1])):
        items["humaneval_plus"].append({"id": t, "cat": "humaneval_plus", "sub": "",
                                        "messages": humaneval_messages(he[t]["prompt"]),
                                        "prompt": he[t]["prompt"], "entry_point": he[t]["entry_point"]})

    for c, k in BFCL_COUNTS.items():
        q = [json.loads(l) for l in open(os.path.join(D, f"bfcl/BFCL_v3_{c}.json"))]
        ans = {r["id"]: r["ground_truth"] for r in map(json.loads, open(os.path.join(D, f"bfcl/possible_answer/BFCL_v3_{c}.json")))}
        for i in sorted(rng(f"bfcl:{c}").sample(range(len(q)), k)):
            r = q[i]
            assert len(r["question"]) == 1, "single-turn categories only"
            items["bfcl"].append({"id": f"bfcl/{r['id']}", "cat": "bfcl", "sub": c, "messages": r["question"][0],
                                  "tools": bfcl_tools(r["function"]), "functions": r["function"],
                                  "gold": ans[r["id"]]})

    man = {"seed": a.seed, "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "selection": "random.Random(f'{seed}:{tag}').sample per category (MMLU-Pro: per domain, tag mmlu_pro:<domain>;"
                        " BFCL: per sub-category, tag bfcl:<cat>), indices sorted, file row order",
           "counts": {c: len(v) for c, v in items.items()}, "sources": {}}
    for cat, (repo, rev, files) in SOURCES.items():
        man["sources"][cat] = {"repo": f"huggingface.co/datasets/{repo}", "revision": rev,
                               "files": {f: sha256(os.path.join(D, l)) for f, l in files}}
    man["sources"]["humaneval_plus"] = {"package": f"evalplus {evalplus.__version__}",
                                        "dataset": "HumanEvalPlus-v0.1.10 (evalplus default)"}
    for c, v in items.items():
        with open(os.path.join(out, f"{c}.jsonl"), "w") as f:
            for it in v:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        man["sources"][c]["subset_sha256"] = sha256(os.path.join(out, f"{c}.jsonl"))
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(json.dumps(man["counts"]), "->", out)


def load_subsets(seed, only=None):
    d = os.path.join(HERE, "subsets", f"s{seed}")
    if not os.path.exists(os.path.join(d, "manifest.json")):
        sys.exit(f"no subsets for seed {seed} ({d}); run: run.py subsets --seed {seed}")
    man = json.load(open(os.path.join(d, "manifest.json")))
    items = []
    for c in CATS:
        if only and c not in only:
            continue
        p = os.path.join(d, f"{c}.jsonl")
        if sha256(p) != man["sources"][c]["subset_sha256"]:
            sys.exit(f"{p}: sha256 differs from manifest.json - the subset was modified")
        items += [json.loads(l) for l in open(p)]
    return items, man


# ---------------------------------------------------------------- generation
def http_json(url, body=None, timeout=3600, api_key=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {api_key}"} if api_key else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def reuse_humaneval(src, items, props, done, out_f):
    """Take HumanEval+ answers from an EvalPlus run of the same server config (../evalplus/gen.py, same prompt,
    system message, T=0, max_tokens 32768). Rows of <ds>.raw.jsonl / .jsonl / .stats.jsonl are in the same order."""
    try:
        sp = json.load(open(os.path.join(src, "props.json")))
        raw = [json.loads(l) for l in open(os.path.join(src, "humaneval.raw.jsonl"))]
        san = [json.loads(l) for l in open(os.path.join(src, "humaneval.jsonl"))]
        st = [json.loads(l) for l in open(os.path.join(src, "humaneval.stats.jsonl"))]
    except (OSError, ValueError) as e:
        print(f"reuse: {src} unusable ({e}); generating HumanEval+ here")
        return 0
    keys = ("model_path", "chat_template")
    diff = [k for k in keys if sp.get(k) != props.get(k)]
    if sp.get("default_generation_settings", {}).get("n_ctx") != props.get("default_generation_settings", {}).get("n_ctx"):
        diff.append("n_ctx")
    if diff:
        print(f"reuse: {src} server differs in {diff}; generating HumanEval+ here")
        return 0
    if not (len(raw) == len(san) == len(st)):
        print(f"reuse: row counts differ raw {len(raw)} san {len(san)} stats {len(st)}; generating here")
        return 0
    by_id = {}
    for r, s, t in zip(raw, san, st):
        by_id[r["task_id"]] = (r, s, t)
    n = 0
    for it in items:
        if it["cat"] != "humaneval_plus" or it["id"] in done or it["id"] not in by_id:
            continue
        r, s, t = by_id[it["id"]]
        if t["prompt_head"] != (it["prompt"].strip() + "\n")[:80] or r["task_id"] != s["task_id"]:
            print(f"reuse: {it['id']} stats row does not match its prompt; generating it here")
            continue
        rec = {"id": it["id"], "cat": it["cat"], "sub": it["sub"], "source": f"reused:{os.path.abspath(src)}",
               "content": r["solution"], "reasoning_chars": t["reasoning_chars"], "tool_calls": None,
               "finish": t["finish"], "prompt_tokens": t["prompt_tokens"], "completion_tokens": t["completion_tokens"],
               "wall_s": t["wall_s"], "timings": t["timings"], "solution": s["solution"]}
        out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out_f.flush()
        with open(os.path.join(os.path.dirname(out_f.name), "humaneval_plus.stats.jsonl"), "a") as sf:
            sf.write(json.dumps({"id": it["id"], "sub": "", "source": "reused", **{k: rec[k] for k in (
                "wall_s", "finish", "completion_tokens", "prompt_tokens", "reasoning_chars", "timings")}}) + "\n")
        done.add(it["id"])
        n += 1
    print(f"reuse: {n} HumanEval+ answers from {src}")
    return n


def cmd_gen(a):
    base = a.base_url or f"http://127.0.0.1:{a.port}"
    base = base.rstrip("/")
    root = base[:-3] if base.endswith("/v1") else base
    api = root + "/v1"
    only = set(a.only.split(",")) if a.only else None
    items, man = load_subsets(a.seed, only)
    run = a.out or os.path.join(HERE, "runs", f"{a.model_label}-{a.effort}-s{a.seed}")
    os.makedirs(run, exist_ok=True)
    try:
        props = http_json(root + "/props", timeout=30, api_key=a.api_key)
    except Exception as e:  # not every OpenAI-compatible server has /props
        props = {"error": repr(e)}
    json.dump(props, open(os.path.join(run, "props.json"), "w"), indent=1)
    meta = {"model_label": a.model_label, "effort": a.effort, "seed": a.seed, "base_url": base,
            "max_tokens": a.max_tokens, "subsets": f"subsets/s{a.seed}", "subset_counts": man["counts"],
            "model_path": props.get("model_path"), "n_ctx": props.get("default_generation_settings", {}).get("n_ctx"),
            "build_info": props.get("build_info"), "started": datetime.datetime.now().isoformat(timespec="seconds")}
    json.dump(meta, open(os.path.join(run, "meta.json"), "w"), indent=1)
    ap = os.path.join(run, "answers.jsonl")
    done = set()
    if os.path.exists(ap):
        done = {json.loads(l)["id"] for l in open(ap) if l.strip()}
    from evalplus.sanitize import sanitize
    n_err = 0
    t_start = time.time()
    with open(ap, "a") as out_f:
        if a.reuse_humaneval:
            reuse_humaneval(a.reuse_humaneval, items, props, done, out_f)
        todo = [it for it in items if it["id"] not in done]
        print(f"{len(items)} items, {len(done)} done, {len(todo)} to generate -> {run}", flush=True)
        for k, it in enumerate(todo):
            body = {"model": a.model_label, "messages": it["messages"], "temperature": 0, "seed": a.seed,
                    "max_tokens": a.max_tokens}
            if it["cat"] == "humaneval_plus":
                body["top_p"] = 0.95  # what evalplus' OpenAI decoder sends (irrelevant at T=0)
            if it["cat"] == "bfcl":
                body["tools"] = it["tools"]
            if a.effort != "server":
                body["reasoning_effort"] = a.effort
            t0 = time.time()
            try:
                r = http_json(api + "/chat/completions", body, timeout=a.timeout, api_key=a.api_key)
            except Exception as e:
                n_err += 1
                with open(os.path.join(run, "errors.jsonl"), "a") as ef:
                    ef.write(json.dumps({"id": it["id"], "error": repr(e), "t": time.time()}) + "\n")
                print(f"[{k + 1}/{len(todo)}] {it['id']} ERROR {e!r}", flush=True)
                continue
            dt = time.time() - t0
            ch = r["choices"][0]
            msg = ch["message"]
            u = r.get("usage") or {}
            rec = {"id": it["id"], "cat": it["cat"], "sub": it["sub"], "source": "generated",
                   "content": msg.get("content") or "", "reasoning_content": msg.get("reasoning_content") or "",
                   "reasoning_chars": len(msg.get("reasoning_content") or ""), "tool_calls": msg.get("tool_calls"),
                   "finish": ch.get("finish_reason"), "prompt_tokens": u.get("prompt_tokens"),
                   "completion_tokens": u.get("completion_tokens"), "wall_s": round(dt, 3), "timings": r.get("timings")}
            if it["cat"] == "humaneval_plus":
                rec["solution"] = sanitize(rec["content"], entrypoint=it["entry_point"])
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_f.flush()
            with open(os.path.join(run, f"{it['cat']}.stats.jsonl"), "a") as sf:  # for ~/qwen-opt/speed_real.py
                sf.write(json.dumps({"id": it["id"], "sub": it["sub"], **{k: rec[k] for k in (
                    "wall_s", "finish", "completion_tokens", "prompt_tokens", "reasoning_chars", "timings")}}) + "\n")
            print(f"[{k + 1}/{len(todo)}] {it['id']} {rec['finish']} {rec['completion_tokens']} tok {dt:.1f} s",
                  flush=True)
    meta["gen_wall_s"] = round(time.time() - t_start)
    meta["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    json.dump(meta, open(os.path.join(run, "meta.json"), "w"), indent=1)
    if n_err:
        sys.exit(f"{n_err} requests failed (errors.jsonl); rerun the same command to retry only those")


# ---------------------------------------------------------------- scoring
NUM = r"(-?[0-9][0-9,]*(?:\.[0-9]+)?|-?\.[0-9]+)"
GSM_ANSWER = re.compile(r"(?i:answer)\s*[:：]\s*\\?\$?\s*" + NUM)
GSM_BOXED = re.compile(r"\\boxed\{\s*\\?\$?\s*" + NUM)


def last(rx, text):
    m = None
    for m in rx.finditer(text):
        pass
    return m.group(1) if m else None


def parse_gsm8k(text):
    t = text.replace("*", "")
    v = last(GSM_ANSWER, t) or last(GSM_BOXED, t)
    if v is None:
        return None
    try:
        return decimal.Decimal(v.replace(",", ""))
    except decimal.InvalidOperation:
        return None


def mcq_rx(letters):
    L = f"[{letters}]"
    return [re.compile(r"(?i:answer is)\s*:?\s*\(?(" + L + r")\)?(?!\w)"),
            re.compile(r"(?i:answer)\s*:\s*\(?(" + L + r")\)?(?!\w)"),
            re.compile(r"\\boxed\{\s*(?:\\text\{\s*)?\(?(" + L + r")\)?")]


MMLU_PRO_RX = mcq_rx("A-J")
PL_RX = [re.compile(r"(?i:odpowied[źz]|answer)\s*:\s*\(?([A-D])\)?(?!\w)"),
         re.compile(r"(?i:answer is|odpowied[źz] to)\s*:?\s*\(?([A-D])\)?(?!\w)"),
         re.compile(r"\\boxed\{\s*(?:\\text\{\s*)?\(?([A-D])\)?")]


def parse_mcq(text, rxs):
    t = text.replace("*", "")
    for rx in rxs:
        v = last(rx, t)
        if v:
            return v
    return None


def score_bfcl(it, rec):
    from bfcl_ast_checker import Language, ast_checker
    calls = rec.get("tool_calls") or []
    if not calls:
        return False, None, "no tool_calls"
    decoded = []
    for c in calls:
        f = c.get("function") or {}
        try:
            args = json.loads(f.get("arguments") or "{}")
        except ValueError:
            return False, None, "arguments are not JSON"
        if not isinstance(args, dict):
            return False, None, "arguments are not an object"
        decoded.append({f.get("name"): args})
    res = ast_checker(it["functions"], decoded, it["gold"], Language.PYTHON, it["sub"], "jakosc-mini")
    return bool(res["valid"]), decoded, None if res["valid"] else res.get("error_type")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cmd_report(a):
    R = a.run
    meta = json.load(open(os.path.join(R, "meta.json")))
    items, man = load_subsets(meta["seed"])
    recs = {}
    for l in open(os.path.join(R, "answers.jsonl")):
        if l.strip():
            r = json.loads(l)
            recs[r["id"]] = r
    he_eval = {}
    hp = os.path.join(R, "humaneval_plus_eval.json")
    if os.path.exists(hp):
        he_eval = json.load(open(hp))
    sys.path.insert(0, HERE)
    scored = []
    for it in items:
        r = recs.get(it["id"])
        s = {"id": it["id"], "cat": it["cat"], "sub": it["sub"], "answered": r is not None, "parsed": False,
             "correct": False, "pred": None}
        if r is not None:
            s.update({k: r.get(k) for k in ("finish", "completion_tokens", "prompt_tokens", "wall_s", "reasoning_chars",
                                            "source")})
            c = r.get("content") or ""
            if it["cat"] == "gsm8k":
                v = parse_gsm8k(c)
                s["parsed"], s["pred"] = v is not None, None if v is None else str(v)
                s["correct"] = v is not None and v == decimal.Decimal(it["gold"])
            elif it["cat"] in ("mmlu_pro", "pl_mmlu"):
                v = parse_mcq(c, MMLU_PRO_RX if it["cat"] == "mmlu_pro" else PL_RX)
                s["parsed"], s["pred"], s["correct"] = v is not None, v, v == it["gold"]
            elif it["cat"] == "humaneval_plus":
                e = he_eval.get(it["id"])
                s["parsed"] = bool((r.get("solution") or "").strip())
                if e is None:
                    s["correct"] = None
                else:
                    s["pred"] = f"base {e['base']} plus {e['plus']}"
                    s["correct"] = e["base"] == "pass" and e["plus"] == "pass"
            elif it["cat"] == "bfcl":
                ok, dec, err = score_bfcl(it, r)
                s["parsed"], s["pred"], s["correct"], s["error"] = bool(r.get("tool_calls")), dec, ok, err
        s["gold"] = it.get("gold") if it["cat"] != "bfcl" else None
        scored.append(s)
    with open(os.path.join(R, "scored.jsonl"), "w") as f:
        for s in scored:
            f.write(json.dumps(s, ensure_ascii=False, default=str) + "\n")

    def agg(rows):
        n = len(rows)
        k = sum(bool(s["correct"]) for s in rows)
        ans = [s for s in rows if s["answered"]]
        toks = [s["completion_tokens"] for s in ans if s.get("completion_tokens") is not None]
        lo, hi = wilson(k, n)
        return {"n": n, "correct": k, "acc": round(100 * k / n, 1) if n else None,
                "ci95": [round(100 * lo, 1), round(100 * hi, 1)], "answered": len(ans),
                "parsed": sum(s["parsed"] for s in rows), "truncated": sum(s.get("finish") == "length" for s in ans),
                "tokens_per_answer": round(sum(toks) / len(toks)) if toks else None,
                "wall_s": round(sum(s.get("wall_s") or 0 for s in ans)),
                "pending_eval": sum(s["correct"] is None for s in rows)}

    out = {"meta": meta, "manifest_counts": man["counts"], "categories": {}, "subcategories": {}}
    for c in CATS:
        rows = [s for s in scored if s["cat"] == c]
        out["categories"][c] = agg(rows)
        if c in ("mmlu_pro", "bfcl", "pl_mmlu"):
            out["subcategories"][c] = {sub: agg([s for s in rows if s["sub"] == sub])
                                       for sub in sorted({s["sub"] for s in rows})}
    out["overall_micro"] = agg(scored)
    accs = [out["categories"][c]["acc"] for c in CATS if out["categories"][c]["acc"] is not None]
    out["macro_acc"] = round(sum(accs) / len(accs), 1) if accs else None
    reused = sum(1 for s in scored if (s.get("source") or "").startswith("reused"))
    out["reused_answers"] = reused
    json.dump(out, open(os.path.join(R, "summary.json"), "w"), indent=1)

    def row(name, d):
        return (f"| {name} | {d['n']} | {d['correct']} | {d['acc']} | {d['ci95'][0]}–{d['ci95'][1]} | "
                f"{d['parsed']}/{d['answered']} | {d['truncated']} | {d['tokens_per_answer']} | {d['wall_s']} |")
    hdr = ["| kategoria | n | poprawne | acc % | 95% CI (Wilson) | sparsowane/odp. | ucięte | tok/odp. | wall s |",
           "|---|---|---|---|---|---|---|---|---|"]
    md = [f"# jakość-mini: {meta['model_label']} (effort {meta['effort']}, seed {meta['seed']})", "",
          f"model: `{os.path.basename(meta.get('model_path') or '?')}`, n_ctx {meta.get('n_ctx')}, "
          f"max_tokens {meta['max_tokens']}, T=0, subsets `{meta['subsets']}`"
          + (f", HumanEval+ reused from an EvalPlus run: {reused}" if reused else ""), ""] + hdr
    md += [row(CAT_NAMES[c], out["categories"][c]) for c in CATS]
    md += [row("**razem (mikro)**", out["overall_micro"]), "", f"Średnia makro 5 kategorii: {out['macro_acc']}%", ""]
    for c, title in (("mmlu_pro", "MMLU-Pro wg dziedzin (n=10, orientacyjnie)"), ("bfcl", "BFCL wg kategorii"),
                     ("pl_mmlu", "PL wg grup przedmiotów")):
        md += [f"## {title}", ""] + hdr + [row(sub, d) for sub, d in out["subcategories"][c].items()] + [""]
    if any(s["correct"] is None for s in scored):
        md.append("HumanEval+: wykonanie kodu jeszcze nie uruchomione (run.py code-eval).")
    open(os.path.join(R, "summary.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


def cmd_code_eval(a):
    py = sys.executable
    cmd = [py, os.path.join(HERE, "code_eval.py"), os.path.abspath(a.run), "--parallel", str(a.parallel)]
    if not a.no_scope:
        cmd = ["nice", "-n", "19", "systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=4G",
               "-p", "CPUQuota=200%", "--"] + cmd
    else:
        cmd = ["nice", "-n", "19"] + cmd
    sys.exit(subprocess.call(cmd))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("subsets")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--force", action="store_true")
    p = sp.add_parser("gen")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--base-url", help="server root or .../v1, e.g. http://127.0.0.1:8098")
    g.add_argument("--port", type=int, help="shorthand for --base-url http://127.0.0.1:PORT")
    p.add_argument("--model-label", required=True, help="run name / request model field, e.g. qwen-unc")
    p.add_argument("--effort", default="server", help="reasoning_effort sent per request (low|medium|xhigh|none) "
                                                      "or 'server' = send nothing (server default)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="subset seed (subsets/s<seed>) and request seed")
    p.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    p.add_argument("--timeout", type=int, default=3600, help="HTTP timeout per request, s")
    p.add_argument("--only", help="comma list of categories (" + ",".join(CATS) + ")")
    p.add_argument("--out", help="run dir (default runs/<label>-<effort>-s<seed>)")
    p.add_argument("--reuse-humaneval", help="EvalPlus run dir of the SAME server config to take HumanEval+ from")
    p.add_argument("--api-key", default=os.environ.get("JAKOSC_API_KEY"))
    p = sp.add_parser("code-eval")
    p.add_argument("run")
    p.add_argument("--parallel", type=int, default=2)
    p.add_argument("--no-scope", action="store_true", help="no systemd --user scope (hosts without systemd); "
                                                           "Landlock + guards still apply")
    p = sp.add_parser("report")
    p.add_argument("run")
    a = ap.parse_args()
    {"subsets": cmd_subsets, "gen": cmd_gen, "report": cmd_report, "code-eval": cmd_code_eval}[a.cmd](a)


if __name__ == "__main__":
    main()
