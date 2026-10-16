"""R36: no sealed prompt text in the implementer's diff (selection set != report set)."""
from fk import sealed
from rules import RulePolicy
from rules._util import diff_files

POLICY = RulePolicy(
    "R36", "sealed-leak", ("static",), "block", "REFUSE",
    source="15f E-E: build_draft_vocab.py prompts disjoint from spec_sweep verbatim (max similarity 0.47) but on one "
           "topic ('lighthouse keeper' vs 'latarnik'); arXiv 2610.09239 winner's curse 13-20 pts at 16 items",
    lesson="lekcja-jeden-prompt", failure_mode="lekcja")

N = 8


def check(ctx):
    f = diff_files(ctx)
    if f is None:
        return []
    if "sealed_texts" in ctx:
        grams = set()
        for t in ctx["sealed_texts"]:
            grams |= sealed.ngrams(t, N)
    else:
        grams = sealed.sealed_ngrams(sealed.load_sealed(), N)
    added = sealed.ngrams("\n".join(l for x in f for l in x.added), N)
    hit = added & grams
    return [f"diff contains {len(hit)} {N}-grams of the sealed prompt set, e.g. {' '.join(sorted(hit)[0])!r}"] if hit \
        else []
