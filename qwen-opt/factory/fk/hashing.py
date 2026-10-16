"""sha256 of files, builds, the harness and canonical JSON. Large files (GGUF) are cached by (path, size, mtime)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from . import paths

BUILD_BINS = ("llama-server", "llama-bench", "test-backend-ops", "llama-perplexity")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_json(obj) -> str:
    return sha256_bytes(canonical(obj))


def _cache_path(cache_dir: Path | None) -> Path:
    return (cache_dir or paths.CACHE) / "sha256.json"


def sha256_file(path, cache_dir: Path | None = None, use_cache: bool = True) -> str:
    p = Path(path).resolve()
    st = p.stat()
    key = f"{p}|{st.st_size}|{st.st_mtime_ns}"
    cp = _cache_path(cache_dir)
    cache = {}
    if use_cache and cp.exists():
        try:
            cache = json.loads(cp.read_text())
        except ValueError:
            cache = {}
        if key in cache:
            return cache[key]
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    d = h.hexdigest()
    if use_cache:
        cache[key] = d
        cp.parent.mkdir(parents=True, exist_ok=True)
        tmp = cp.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, indent=0, sort_keys=True))
        os.replace(tmp, cp)
    return d


def build_files(build_dir) -> dict[str, Path]:
    """Files that define a build: the four binaries we run and every real shared library under lib/."""
    b = Path(build_dir)
    out = {}
    for name in BUILD_BINS:
        f = b / "bin" / name
        if f.exists():
            out[f"bin/{name}"] = f
    lib = b / "lib"
    if lib.is_dir():
        for f in sorted(lib.iterdir()):
            if ".so" in f.name and f.is_file() and not f.is_symlink():
                out[f"lib/{f.name}"] = f
    return out


def hash_build(build_dir, cache_dir: Path | None = None) -> dict[str, str]:
    return {k: sha256_file(v, cache_dir) for k, v in build_files(build_dir).items()}


def harness_files() -> dict[str, Path]:
    """Every file whose change could change a verdict: factory code, rules, sealed set, wrapped tools."""
    out = {}
    for sub in ("fk", "rules", "sealed"):
        for f in sorted((paths.FACTORY / sub).rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                out[str(f.relative_to(paths.FACTORY))] = f
    for name in ("factory.py", "factory"):
        f = paths.FACTORY / name
        if f.exists():
            out[name] = f
    for f in paths.EXTERNAL_HARNESS:
        if f.exists():
            out[f"ext/{f.relative_to(paths.QWEN_OPT)}"] = f
    return out


def hash_harness() -> dict[str, str]:
    return {k: sha256_file(v, use_cache=False) for k, v in harness_files().items()}


def tree_sha(files: dict[str, str]) -> str:
    return sha256_json(files)


def file_contains(path, needle: bytes) -> bool:
    """Streaming byte search (switch names and the commit hash are compiled into the .so files)."""
    keep = len(needle) - 1
    prev = b""
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            buf = prev + chunk
            if needle in buf:
                return True
            prev = buf[-keep:] if keep else b""
    return False


def build_contains(build_dir, needle: str, sub: str = "lib") -> list[str]:
    hits = []
    for k, f in build_files(build_dir).items():
        if k.startswith(sub + "/") and file_contains(f, needle.encode()):
            hits.append(k)
    return hits
