// Pins the upstream llama.cpp baseline engines in data/engines.json from the GitHub API (JSON only, no binaries).
//   bun tools/engines-pin.ts [--release v0.7.0 | --tag b11669]
// A `v*` release carries `nightly-tag.txt` naming the `b*` build whose assets are the official binaries.
// Keeps the enigma entries as they are; records each asset's sha256 digest from the API.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import type { EngineEntry, EnginesFile } from '../src/server/engine.ts';

const REPO = 'ggml-org/llama.cpp';
const { values } = parseArgs({ options: { release: { type: 'string' }, tag: { type: 'string' } } });

interface GhAsset { name: string; size: number; digest?: string | null; browser_download_url: string }
interface GhRelease { tag_name: string; published_at: string; assets: GhAsset[] }

async function gh(path: string): Promise<GhRelease> {
  const res = await fetch(`https://api.github.com/repos/${REPO}/${path}`, { headers: { accept: 'application/vnd.github+json' } });
  if (!res.ok) throw new Error(`GitHub API ${res.status} for ${path}`);
  return (await res.json()) as GhRelease;
}

let release = values.release ?? '';
let tag = values.tag ?? '';
if (!tag) {
  const rel = release ? await gh(`releases/tags/${release}`) : await gh('releases/latest');
  release = rel.tag_name;
  const marker = rel.assets.find((a) => a.name === 'nightly-tag.txt');
  if (!marker) throw new Error(`${release} has no nightly-tag.txt`);
  tag = (await (await fetch(marker.browser_download_url)).text()).trim();
}
const build = await gh(`releases/tags/${tag}`);
// pinned by build tag: an official nightly build (the newest binaries; `v*` releases point at older builds)
if (!release) release = 'nightly';

type Spec = Pick<EngineEntry, 'id' | 'os' | 'arch' | 'backend' | 'envKey' | 'label'> & { assets: string[] };
const specs: Spec[] = [
  { id: 'upstream-linux-x64-cpu', os: 'linux', arch: 'x64', backend: 'cpu', envKey: 'UPSTREAM_CPU', label: 'llama.cpp CPU (Ubuntu x64)', assets: [`llama-${tag}-bin-ubuntu-x64.tar.gz`] },
  { id: 'upstream-linux-x64-vulkan', os: 'linux', arch: 'x64', backend: 'vulkan', envKey: 'UPSTREAM_VULKAN', label: 'llama.cpp Vulkan (Ubuntu x64)', assets: [`llama-${tag}-bin-ubuntu-vulkan-x64.tar.gz`] },
  { id: 'upstream-linux-x64-rocm', os: 'linux', arch: 'x64', backend: 'rocm', envKey: 'UPSTREAM_ROCM', label: 'llama.cpp ROCm 10.0 (Ubuntu x64)', assets: [`llama-${tag}-bin-ubuntu-rocm-10.0-x64.tar.gz`] },
  { id: 'upstream-linux-x64-cuda', os: 'linux', arch: 'x64', backend: 'cuda', envKey: 'UPSTREAM_CUDA', label: 'llama.cpp CUDA 12.8 (Ubuntu x64)', assets: [`llama-${tag}-bin-ubuntu-cuda-12.8-x64.tar.gz`, `cudart-llama-${tag}-bin-ubuntu-cuda-12.8-x64.tar.gz`] },
  { id: 'upstream-windows-x64-cpu', os: 'windows', arch: 'x64', backend: 'cpu', envKey: 'UPSTREAM_CPU', label: 'llama.cpp CPU (Windows x64)', assets: [`llama-${tag}-bin-win-cpu-x64.zip`] },
  { id: 'upstream-windows-x64-vulkan', os: 'windows', arch: 'x64', backend: 'vulkan', envKey: 'UPSTREAM_VULKAN', label: 'llama.cpp Vulkan (Windows x64)', assets: [`llama-${tag}-bin-win-vulkan-x64.zip`] },
  { id: 'upstream-windows-x64-cuda', os: 'windows', arch: 'x64', backend: 'cuda', envKey: 'UPSTREAM_CUDA', label: 'llama.cpp CUDA 12.4 (Windows x64)', assets: [`llama-${tag}-bin-win-cuda-12.4-x64.zip`, 'cudart-llama-bin-win-cuda-12.4-x64.zip'] },
  { id: 'upstream-windows-x64-rocm', os: 'windows', arch: 'x64', backend: 'rocm', envKey: 'UPSTREAM_ROCM', label: 'llama.cpp HIP/ROCm 10.0 (Windows x64)', assets: [`llama-${tag}-bin-win-rocm-10.0-x64.zip`] },
  { id: 'upstream-macos-arm64-metal', os: 'macos', arch: 'arm64', backend: 'metal', envKey: 'UPSTREAM_METAL', label: 'llama.cpp Metal (macOS arm64)', assets: [`llama-${tag}-bin-macos-arm64.tar.gz`] },
];

const upstream: EngineEntry[] = specs.map((s) => ({
  id: s.id, kind: 'upstream', label: s.label, version: tag, os: s.os, arch: s.arch, backend: s.backend, envKey: s.envKey,
  distribution: 'download', features: ['mtp', 'lookup'],
  assets: s.assets.map((name) => {
    const a = build.assets.find((x) => x.name === name);
    if (!a) throw new Error(`${tag}: asset ${name} not found`);
    const sha = a.digest?.startsWith('sha256:') ? a.digest.slice(7) : undefined;
    return { name, url: a.browser_download_url, sizeBytes: a.size, ...(sha ? { sha256: sha } : {}) };
  }),
}));

const file = join(import.meta.dir, '..', 'data', 'engines.json');
let current: EnginesFile | null = null;
try {
  current = JSON.parse(readFileSync(file, 'utf8')) as EnginesFile;
} catch {
  current = null;
}
const out: EnginesFile = {
  upstream: { repo: REPO, release, tag, publishedAt: build.published_at, pinnedAt: new Date().toISOString().slice(0, 10) },
  engines: [...upstream, ...(current?.engines.filter((e) => e.kind === 'enigma') ?? [])],
};
writeFileSync(file, JSON.stringify(out, null, 2) + '\n');
console.log(`pinned ${REPO} ${release} = ${tag} (${build.published_at}), ${upstream.length} upstream engines`);
