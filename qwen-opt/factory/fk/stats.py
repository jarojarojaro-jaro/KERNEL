"""Statistics of the verifier: ABBA schedule, paired deltas, A/A control, Student t and bootstrap 95 % CI, verdict.

Sign convention: an *effect* is in percent and positive when the candidate is better (lower ms, higher t/s).
"""
from __future__ import annotations

import math
import random
import statistics

# two-sided 97.5 % Student t quantiles, df 1..30 (same table as tools/loo.py)
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
        2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]

LOWER_IS_BETTER = {"ms_step": True, "ms_token": True, "tok_step": False, "tps": False, "pp_tps": False,
                   "tg_tps": False}
E2E_METRICS = set(LOWER_IS_BETTER)
# minimum detectable effect floors (%), from A/A in spec_sweep.jsonl: ms/step 0.09 % median, t/s 0.16 % (15f E-B)
MDE_FLOOR = {"ms_step": 0.2, "ms_token": 0.2, "tok_step": 0.5, "tps": 0.5, "pp_tps": 0.3, "tg_tps": 0.3}
# A/A control fails above this |median| (%): the session is too noisy to judge anything
AA_MAX = {"ms_step": 0.5, "ms_token": 0.5, "tok_step": 1.0, "tps": 1.0, "pp_tps": 1.0, "tg_tps": 1.0}


def median(xs):
    return statistics.median(xs)


def tq(df: int) -> float:
    return T975[df - 1] if 1 <= df <= len(T975) else 1.96


def t_ci(xs):
    """(mean, lo, hi) Student t 95 %; lo = hi = nan for n < 2."""
    n = len(xs)
    m = sum(xs) / n
    if n < 2:
        return m, math.nan, math.nan
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    h = tq(n - 1) * sd / math.sqrt(n)
    return m, m - h, m + h


def bootstrap_ci(xs, stat=median, b: int = 10000, seed: int = 20261016):
    """Percentile bootstrap 95 % CI of stat (deterministic seed)."""
    n = len(xs)
    if n < 2:
        return stat(xs), math.nan, math.nan
    rnd = random.Random(seed)
    sims = sorted(stat([xs[rnd.randrange(n)] for _ in range(n)]) for _ in range(b))
    return stat(xs), sims[int(0.025 * b)], sims[min(b - 1, int(0.975 * b))]


def abba_schedule(rounds: int, arms=("A", "B")):
    """[(round, pos, arm)]: odd rounds A B B A, even rounds B A A B. Every arm gets 2 fresh processes per round."""
    a, b = arms
    out = []
    for r in range(1, rounds + 1):
        order = (a, b, b, a) if r % 2 else (b, a, a, b)
        out += [(r, p, arm) for p, arm in enumerate(order)]
    return out


def effect_pct(base: float, cand: float, metric: str) -> float:
    """Candidate vs base in %, positive = better."""
    d = 100.0 * (cand / base - 1.0)
    return -d if LOWER_IS_BETTER[metric] else d


def paired_effects(values: dict, metric: str, a="A", b="B"):
    """values: {(round, pos): (arm, value)}. Pairs are adjacent runs (pos 0-1 and 2-3) of a round.
    Returns (effects, aa, bb): candidate-vs-base effects per pair, A/A and B/B effects (second vs first process)."""
    rounds = sorted({r for r, _ in values})
    effects, aa, bb = [], [], []
    for r in rounds:
        seq = [values[(r, p)] for p in range(4) if (r, p) in values]
        if len(seq) != 4:
            continue
        for i in (0, 2):
            (arm1, v1), (arm2, v2) = seq[i], seq[i + 1]
            base, cand = (v1, v2) if arm1 == a else (v2, v1)
            effects.append(effect_pct(base, cand, metric))
        av = [v for arm, v in seq if arm == a]
        bv = [v for arm, v in seq if arm == b]
        aa.append(effect_pct(av[0], av[1], metric))
        bb.append(effect_pct(bv[0], bv[1], metric))
    return effects, aa, bb


def summarize(effects, method: str = "t"):
    if method == "bootstrap":
        est, lo, hi = bootstrap_ci(effects)
    else:
        _, lo, hi = t_ci(effects)
        est = median(effects)
    return {"n": len(effects), "median": median(effects), "estimate": est, "ci95": [lo, hi], "ci_method": method}


def mde(metric: str, aa_effects, card_mde=None) -> float:
    floor = MDE_FLOOR[metric]
    noise = 2.0 * median([abs(x) for x in aa_effects]) if aa_effects else 0.0
    return max(floor, noise, card_mde or 0.0)


def verdict(summary: dict, mde_pct: float, kill_pct=None) -> tuple[str, str]:
    """Decision rule on favorable effects (%):
      REGRESSION  CI entirely below 0
      REFUTED     CI entirely below the pre-registered kill threshold (effect real but too small, or absent)
      CONFIRMED   CI entirely above 0 and median >= MDE
      NULL        otherwise (CI contains 0 or the effect is below the MDE)
    """
    lo, hi = summary["ci95"]
    med = summary["median"]
    if math.isnan(lo):
        return "NULL", "fewer than 2 pairs"
    if hi < 0:
        return "REGRESSION", f"CI [{lo:+.3f}, {hi:+.3f}] % below 0"
    if kill_pct is not None and hi < kill_pct:
        return "REFUTED", f"CI [{lo:+.3f}, {hi:+.3f}] % below the kill threshold {kill_pct:+.3f} %"
    if lo > 0 and med >= mde_pct:
        return "CONFIRMED", f"CI [{lo:+.3f}, {hi:+.3f}] % above 0, median {med:+.3f} % >= MDE {mde_pct:.3f} %"
    return "NULL", f"CI [{lo:+.3f}, {hi:+.3f}] %, median {med:+.3f} %, MDE {mde_pct:.3f} %"
