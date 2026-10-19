"""Content-addressed evidence store (report 21j §7 P3).

Every file of a run is stored once, compressed, under `store/sha256/<aa>/<sha>/payload.<ext>`, where sha is the
sha256 of the ORIGINAL bytes. A canonical manifest lists the run's files and is stored as
`store/manifests/<evidence_id>.json`; evidence_id = sha256 of the canonical manifest without `created`, so identical
runs give identical ids. Writes are atomic (tmp + os.replace), stored files are 0444, nothing is ever deleted (no GC).

Codec: the `zstd` CLI (level 3, under `nice -n 19`) when installed, else stdlib lzma (`payload.xz`). The codec is
recorded per file; decompression follows the recorded codec.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import paths
from .hashing import canonical, sha256_bytes

SCHEMA = "evidence-v1"
CHUNK = 1 << 20
SUFFIX = {"zstd": "zst", "xz": "xz"}
ZSTD_LEVEL = 3
_ID_RE = re.compile(r"[0-9a-f]{64}")


class EvidenceError(RuntimeError):
    pass


def default_codec() -> str:
    return "zstd" if shutil.which("zstd") else "xz"


def evidence_id_of(manifest: dict) -> str:
    return sha256_bytes(canonical({k: v for k, v in manifest.items() if k != "created"}))


def payload_path(store: Path, sha: str, codec: str) -> Path:
    return store / "sha256" / sha[:2] / sha / f"payload.{SUFFIX[codec]}"


def manifest_path(store: Path, evidence_id: str) -> Path:
    if not _ID_RE.fullmatch(evidence_id):
        raise EvidenceError(f"bad evidence_id {evidence_id!r}")
    return store / "manifests" / f"{evidence_id}.json"


def _store(store: Path | None) -> Path:
    return Path(store) if store is not None else paths.EVIDENCE


def _tmp_for(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return target.parent / f".{target.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"


def _commit(tmp: Path, target: Path, mode: int = 0o444) -> None:
    os.chmod(tmp, mode)
    os.replace(tmp, target)


def _sha_file(p: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with open(p, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def _existing_payload(store: Path, sha: str) -> tuple[str, Path] | None:
    for codec in SUFFIX:
        p = payload_path(store, sha, codec)
        if p.is_file():
            return codec, p
    return None


def _compress(src: Path, dst: Path, codec: str) -> str:
    """Compress src into dst (dst is a fresh tmp file); returns sha256 of the bytes actually read."""
    h = hashlib.sha256()
    with open(src, "rb") as fin:
        if codec == "zstd":
            with open(dst, "wb") as fout, tempfile.TemporaryFile() as err:
                proc = subprocess.Popen(["nice", "-n", "19", "zstd", f"-{ZSTD_LEVEL}", "-q", "-c"],
                                        stdin=subprocess.PIPE, stdout=fout, stderr=err)
                try:
                    while chunk := fin.read(CHUNK):
                        h.update(chunk)
                        proc.stdin.write(chunk)
                finally:
                    proc.stdin.close()
                    rc = proc.wait()
                if rc != 0:
                    err.seek(0)
                    raise EvidenceError(f"zstd failed on {src} (rc={rc}): {err.read().decode(errors='replace')}")
        elif codec == "xz":
            with lzma.open(dst, "wb") as fout:
                while chunk := fin.read(CHUNK):
                    h.update(chunk)
                    fout.write(chunk)
        else:
            raise EvidenceError(f"unknown codec {codec!r}")
    return h.hexdigest()


def _decompress(payload: Path, codec: str, out=None) -> tuple[str, int]:
    """Stream-decompress payload, optionally writing into the binary file `out`; returns (sha256, bytes)."""
    h, n = hashlib.sha256(), 0

    def take(chunk: bytes) -> None:
        nonlocal n
        h.update(chunk)
        n += len(chunk)
        if out is not None:
            out.write(chunk)

    if codec == "zstd":
        if not shutil.which("zstd"):
            raise EvidenceError("zstd CLI not available to decompress a zstd payload")
        with open(payload, "rb") as fin, tempfile.TemporaryFile() as err:
            proc = subprocess.Popen(["nice", "-n", "19", "zstd", "-d", "-q", "-c"],
                                    stdin=fin, stdout=subprocess.PIPE, stderr=err)
            while chunk := proc.stdout.read(CHUNK):
                take(chunk)
            proc.stdout.close()
            rc = proc.wait()
            if rc != 0:
                err.seek(0)
                raise EvidenceError(f"zstd -d failed on {payload} (rc={rc}): {err.read().decode(errors='replace')}")
    elif codec == "xz":
        try:
            with lzma.open(payload, "rb") as fin:
                while chunk := fin.read(CHUNK):
                    take(chunk)
        except lzma.LZMAError as e:
            raise EvidenceError(f"xz decompress failed on {payload}: {e}") from e
    else:
        raise EvidenceError(f"unknown codec {codec!r}")
    return h.hexdigest(), n


def _run_files(rundir: Path) -> list[tuple[str, Path]]:
    out = []
    for dirpath, dirnames, filenames in os.walk(rundir):
        dirnames.sort()
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.is_file():
                out.append((p.relative_to(rundir).as_posix(), p))
    return out


def preserve(rundir: Path, store: Path | None = None, codec: str | None = None) -> dict:
    """Store every file under rundir; returns {evidence_id, manifest, files, bytes_in, bytes_out, new_payloads}.

    bytes_in = original bytes of all files; bytes_out = stored bytes of the distinct payloads this run references
    (after compression and dedup, whether newly written or already present); new_payloads = payloads written now.
    """
    rundir = Path(rundir)
    if not rundir.is_dir():
        raise EvidenceError(f"not a directory: {rundir}")
    store = _store(store)
    codec = codec or default_codec()
    if codec not in SUFFIX:
        raise EvidenceError(f"unknown codec {codec!r}")
    files: dict[str, dict] = {}
    seen: set[str] = set()
    bytes_in = bytes_out = new_payloads = 0
    for rel, p in _run_files(rundir):
        sha, size = _sha_file(p)
        hit = _existing_payload(store, sha)
        if hit is None:
            target = payload_path(store, sha, codec)
            tmp = _tmp_for(target)
            try:
                if _compress(p, tmp, codec) != sha:
                    raise EvidenceError(f"{p} changed while being preserved")
                _commit(tmp, target)
            finally:
                tmp.unlink(missing_ok=True)
            hit = (codec, target)
            new_payloads += 1
        used_codec, payload = hit
        stored = payload.stat().st_size
        files[rel] = {"sha256": sha, "bytes": size, "stored_bytes": stored, "codec": used_codec}
        bytes_in += size
        if sha not in seen:
            seen.add(sha)
            bytes_out += stored
    manifest = {"schema": SCHEMA, "root": str(rundir), "files": files,
                "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    evidence_id = evidence_id_of(manifest)
    mpath = manifest_path(store, evidence_id)
    if mpath.is_file():
        manifest = json.loads(mpath.read_bytes())  # same content already preserved: keep the first `created`
    else:
        tmp = _tmp_for(mpath)
        try:
            tmp.write_bytes(canonical(manifest))
            _commit(tmp, mpath)
        finally:
            tmp.unlink(missing_ok=True)
    return {"evidence_id": evidence_id, "manifest": manifest, "files": len(files),
            "bytes_in": bytes_in, "bytes_out": bytes_out, "new_payloads": new_payloads}


def load_manifest(evidence_id: str, store: Path | None = None) -> dict:
    return json.loads(manifest_path(_store(store), evidence_id).read_bytes())


def verify_evidence(evidence_id: str, store: Path | None = None) -> list[str]:
    """Problems found (empty = OK): missing manifest/payload, id mismatch, decompress failure, sha/size mismatch."""
    store = _store(store)
    try:
        mpath = manifest_path(store, evidence_id)
    except EvidenceError as e:
        return [str(e)]
    if not mpath.is_file():
        return [f"manifest missing: {mpath}"]
    try:
        manifest = json.loads(mpath.read_bytes())
    except (ValueError, OSError) as e:
        return [f"manifest unreadable: {e}"]
    problems = []
    if evidence_id_of(manifest) != evidence_id:
        problems.append(f"manifest id mismatch: file {evidence_id}, content {evidence_id_of(manifest)}")
    for rel, ent in sorted(manifest.get("files", {}).items()):
        sha, codec = ent.get("sha256", ""), ent.get("codec", "")
        if not _ID_RE.fullmatch(sha) or codec not in SUFFIX:
            problems.append(f"{rel}: bad manifest entry {ent}")
            continue
        payload = payload_path(store, sha, codec)
        if not payload.is_file():
            problems.append(f"{rel}: payload missing {payload}")
            continue
        try:
            got, n = _decompress(payload, codec)
        except EvidenceError as e:
            problems.append(f"{rel}: {e}")
            continue
        if got != sha:
            problems.append(f"{rel}: sha256 mismatch after decompress ({got} != {sha})")
        elif n != ent.get("bytes"):
            problems.append(f"{rel}: size mismatch ({n} != {ent.get('bytes')})")
    return problems


def restore(evidence_id: str, dest: Path, store: Path | None = None) -> list[Path]:
    """Write the run's files under dest (atomic per file, sha-checked); returns the written paths."""
    store = _store(store)
    manifest = load_manifest(evidence_id, store)
    if evidence_id_of(manifest) != evidence_id:
        raise EvidenceError(f"manifest id mismatch for {evidence_id}")
    dest = Path(dest)
    written = []
    for rel, ent in sorted(manifest["files"].items()):
        parts = PurePosixPath(rel).parts
        if PurePosixPath(rel).is_absolute() or ".." in parts or not parts:
            raise EvidenceError(f"unsafe path in manifest: {rel!r}")
        target = dest.joinpath(*parts)
        payload = payload_path(store, ent["sha256"], ent["codec"])
        if not payload.is_file():
            raise EvidenceError(f"{rel}: payload missing {payload}")
        tmp = _tmp_for(target)
        try:
            with open(tmp, "wb") as out:
                got, _ = _decompress(payload, ent["codec"], out)
            if got != ent["sha256"]:
                raise EvidenceError(f"{rel}: sha256 mismatch after decompress ({got} != {ent['sha256']})")
            _commit(tmp, target, 0o644)
        finally:
            tmp.unlink(missing_ok=True)
        written.append(target)
    return written
