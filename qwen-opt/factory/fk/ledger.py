"""Append-only, hash-chained ledger.jsonl. Only the verifier (factory.py) appends.

Every row: seq, ts, kind, ..., prev_sha256 (sha256 of the previous row, GENESIS for the first), sha256 (of the row's
canonical JSON without the sha256 field). ledger.head keeps {seq, sha256} of the last row, so truncation of the tail
is detected too. The file is kept read-only (0444) between appends.
"""
from __future__ import annotations

import fcntl
import json
import os
import stat
import time
from pathlib import Path

from .hashing import sha256_json

GENESIS = "0" * 64
KINDS = ("register", "verdict", "harness-lock", "note")


class LedgerError(Exception):
    pass


def row_sha(row: dict) -> str:
    return sha256_json({k: v for k, v in row.items() if k != "sha256"})


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.head = self.path.with_name(self.path.name + ".head")
        self.lock = self.path.with_name(self.path.name + ".lock")

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        with open(self.path, encoding="utf-8") as f:
            for n, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError as e:
                    raise LedgerError(f"{self.path}:{n + 1}: not JSON ({e})")
        return out

    def verify(self) -> list[str]:
        """Problems with the chain (empty list = intact)."""
        try:
            rows = self.rows()
        except LedgerError as e:
            return [str(e)]
        problems = []
        prev = GENESIS
        for i, r in enumerate(rows):
            if r.get("seq") != i:
                problems.append(f"row {i}: seq {r.get('seq')} != {i}")
            if r.get("prev_sha256") != prev:
                problems.append(f"row {i}: prev_sha256 does not match row {i - 1}")
            if r.get("sha256") != row_sha(r):
                problems.append(f"row {i}: content changed (sha256 mismatch)")
            prev = r.get("sha256")
        if self.head.exists():
            h = json.loads(self.head.read_text())
            last = rows[-1] if rows else None
            if (last is None and h.get("seq", -1) != -1) or (last and (h.get("seq") != last["seq"]
                                                                       or h.get("sha256") != last["sha256"])):
                problems.append(f"head {h} does not match the last row (truncated or replaced ledger)")
        elif rows:
            problems.append("ledger.head missing")
        return problems

    def append(self, row: dict) -> dict:
        if row.get("kind") not in KINDS:
            raise LedgerError(f"unknown row kind {row.get('kind')!r}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock, "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            problems = self.verify()
            if problems:
                raise LedgerError("refusing to append to a broken chain: " + "; ".join(problems))
            rows = self.rows()
            r = dict(row)
            r.pop("sha256", None)
            r["seq"] = len(rows)
            r.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            r["prev_sha256"] = rows[-1]["sha256"] if rows else GENESIS
            r["sha256"] = row_sha(r)
            if self.path.exists():
                os.chmod(self.path, 0o644)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.chmod(self.path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            tmp = self.head.with_name(self.head.name + ".tmp")
            tmp.write_text(json.dumps({"seq": r["seq"], "sha256": r["sha256"]}))
            os.replace(tmp, self.head)
            return r

    # queries
    def find(self, **match) -> list[dict]:
        return [r for r in self.rows() if all(r.get(k) == v for k, v in match.items())]

    def registration(self, claim_id: str, claim_sha: str) -> dict | None:
        for r in self.rows():
            if r.get("kind") == "register" and r.get("claim_id") == claim_id and r.get("claim_sha256") == claim_sha:
                return r
        return None

    def last_harness_lock(self) -> dict | None:
        locks = [r for r in self.rows() if r.get("kind") == "harness-lock"]
        return locks[-1] if locks else None
