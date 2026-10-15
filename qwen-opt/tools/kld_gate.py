#!/usr/bin/env python3
"""KLD gate: compare two llama-perplexity --kl-divergence logs (same --kl-divergence-base reference).

  kld_gate.py compare BASE.log CAND.log [--k 2] [--tail-ratio 1.25] [--json]
      exit 0 PASS/IDENTICAL, 1 FAIL, 2 ERROR
  kld_gate.py check LOG          exit 0 if LOG is a complete KLD log
  kld_gate.py table MANIFEST     canary table; MANIFEST lines: name<TAB>expected<TAB>base_log<TAB>cand_log<TAB>note
      expected: BASE (row shown, not gated), PASS (PASS or IDENTICAL ok), IDENTICAL, FAIL, PROBE (reported only)
      exit 0 all expectations met, 1 any UNEXPECTED, 2 missing/errored logs (and nothing UNEXPECTED)

Gate (candidate C vs baseline B, k = 2, tail ratio 1.25):
  IDENTICAL  every number of the chunk table and of the three statistics sections is equal
  PASS iff   KLD_C - KLD_B           <=  k * sqrt(se_B^2 + se_C^2)      (mean KLD)
         and top_C - top_B           >= -k * sqrt(se_B^2 + se_C^2)      (same top p, %)
         and KLD99.9_C               <= tail_ratio * KLD99.9_B          (99.9 % KLD quantile)
  ERROR      a log is incomplete, or PPL(base)/chunk count differ (different reference or text)
RMS dp and PPL(Q)/PPL(base) are reported, not gated.
"""
import argparse
import json
import math
import os
import re
import sys

NUM = r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)'
PM = r'\s*±\s*'
PATTERNS = {
    'kld':       re.compile(r'^Mean\s+KLD:\s*' + NUM + PM + NUM, re.M),
    'kld_max':   re.compile(r'^Maximum KLD:\s*' + NUM, re.M),
    'kld_999':   re.compile(r'^99\.9%\s+KLD:\s*' + NUM, re.M),
    'kld_99':    re.compile(r'^99\.0%\s+KLD:\s*' + NUM, re.M),
    'top':       re.compile(r'^Same top p:\s*' + NUM + PM + NUM + r'\s*%', re.M),
    'rms_dp':    re.compile(r'^RMS Δp\s*:\s*' + NUM + PM + NUM + r'\s*%', re.M),
    'ppl_ratio': re.compile(r'^Mean PPL\(Q\)/PPL\(base\)\s*:\s*' + NUM + PM + NUM, re.M),
    'ppl_q':     re.compile(r'^Mean PPL\(Q\)\s*:\s*' + NUM + PM + NUM, re.M),
    'ppl_base':  re.compile(r'^Mean PPL\(base\)\s*:\s*' + NUM + PM + NUM, re.M),
}
CHUNK_ROW = re.compile(r'^[ \t]*(\d+)[ \t]+' + NUM + PM + NUM + r'[ \t]', re.M)
REQUIRED = ('kld', 'kld_999', 'top', 'rms_dp', 'ppl_ratio', 'ppl_base')
SECTION = re.compile(r'^====== (.+?) ======$')


class LogError(Exception):
    pass


def parse(path):
    """Gate numbers + the full numeric fingerprint (chunk table and statistics sections) of a KLD log."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
    except OSError as e:
        raise LogError(f'{path}: {e.strerror}')
    r = {'path': path}
    for key, pat in PATTERNS.items():
        m = pat.findall(text)
        if m:
            v = m[-1]
            r[key] = tuple(float(x) for x in v) if isinstance(v, tuple) else float(v)
    missing = [k for k in REQUIRED if k not in r]
    if missing:
        raise LogError(f'{path}: incomplete KLD log (missing {", ".join(missing)})')
    rows = CHUNK_ROW.findall(text)
    r['chunks'] = int(rows[-1][0]) if rows else 0
    # fingerprint: chunk rows + every "label: numbers" line of the statistics sections
    fp, section = [], None
    for line in text.splitlines():
        m = SECTION.match(line.strip())
        if m:
            section = m.group(1)
            continue
        if section and ':' in line:
            label, _, rest = line.partition(':')
            fp.append((section, label.strip(), tuple(float(x) for x in re.findall(NUM, rest))))
        elif not line.strip():
            section = None
    r['fingerprint'] = (tuple(CHUNK_ROW.findall(text)), tuple(fp))
    return r


def gate(b, c, k=2.0, tail_ratio=1.25):
    """Verdict dict for candidate c vs baseline b (parsed logs)."""
    out = {'base': b['path'], 'cand': c['path'], 'k': k, 'tail_ratio': tail_ratio}
    if b['ppl_base'] != c['ppl_base'] or b['chunks'] != c['chunks']:
        out.update(verdict='ERROR', reasons=[
            f'different reference: PPL(base) {b["ppl_base"][0]} vs {c["ppl_base"][0]}, '
            f'chunks {b["chunks"]} vs {c["chunks"]}'])
        return out
    sd_kld = math.hypot(b['kld'][1], c['kld'][1])
    sd_top = math.hypot(b['top'][1], c['top'][1])
    d_kld = c['kld'][0] - b['kld'][0]
    d_top = c['top'][0] - b['top'][0]
    tail = c['kld_999'] / b['kld_999'] if b['kld_999'] > 0 else math.inf
    out.update(d_kld=d_kld, sd_kld=sd_kld, z_kld=d_kld / sd_kld if sd_kld else math.inf,
               d_top=d_top, sd_top=sd_top, z_top=d_top / sd_top if sd_top else -math.inf,
               tail=tail, d_rms_dp=c['rms_dp'][0] - b['rms_dp'][0],
               d_ppl_ratio=c['ppl_ratio'][0] - b['ppl_ratio'][0])
    if b['fingerprint'] == c['fingerprint']:
        out.update(verdict='IDENTICAL', reasons=[])
        return out
    reasons = []
    if d_kld > k * sd_kld:
        reasons.append(f'mean KLD +{d_kld:.6f} > {k:g}*{sd_kld:.6f}')
    if d_top < -k * sd_top:
        reasons.append(f'same top p {d_top:+.3f} % < -{k:g}*{sd_top:.3f} %')
    if tail > tail_ratio:
        reasons.append(f'99.9% KLD x{tail:.3f} > x{tail_ratio:g}')
    out.update(verdict='FAIL' if reasons else 'PASS', reasons=reasons)
    return out


def fmt_log(r):
    return (f'mean KLD {r["kld"][0]:.6f} ± {r["kld"][1]:.6f}  99.9% KLD {r["kld_999"]:.4f}  '
            f'same top p {r["top"][0]:.3f} ± {r["top"][1]:.3f} %  RMS dp {r["rms_dp"][0]:.3f} %  '
            f'PPL ratio {r["ppl_ratio"][0]:.4f}')


def cmd_compare(a):
    try:
        b, c = parse(a.base), parse(a.cand)
    except LogError as e:
        print(f'ERROR: {e}')
        return 2
    g = gate(b, c, a.k, a.tail_ratio)
    if a.json:
        print(json.dumps(g, indent=1))
    else:
        print(f'base: {fmt_log(b)}\ncand: {fmt_log(c)}')
        if 'd_kld' in g:
            print(f'dKLD {g["d_kld"]:+.6f} ({g["z_kld"]:+.2f} sd)  dtop {g["d_top"]:+.3f} % ({g["z_top"]:+.2f} sd)  '
                  f'99.9% x{g["tail"]:.3f}  dRMSdp {g["d_rms_dp"]:+.3f} %  dPPLratio {g["d_ppl_ratio"]:+.4f}')
        print(g['verdict'] + (': ' + '; '.join(g['reasons']) if g['reasons'] else ''))
    return {'PASS': 0, 'IDENTICAL': 0, 'FAIL': 1}.get(g['verdict'], 2)


def cmd_check(a):
    try:
        parse(a.log)
    except LogError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def outcome(expected, verdict):
    if verdict in ('MISSING', 'ERROR'):
        return verdict
    if expected in ('BASE', 'PROBE'):
        return '-'
    ok = {'PASS': ('PASS', 'IDENTICAL'), 'IDENTICAL': ('IDENTICAL',), 'FAIL': ('FAIL',)}[expected]
    return 'OK' if verdict in ok else 'UNEXPECTED'


def cmd_table(a):
    rows, unexpected, incomplete = [], 0, 0
    with open(a.manifest, encoding='utf-8') as f:
        entries = [ln.rstrip('\n').split('\t') for ln in f if ln.strip() and not ln.startswith('#')]
    for e in entries:
        name, expected, base, cand = e[:4]
        note = e[4] if len(e) > 4 else ''
        if expected not in ('BASE', 'PASS', 'IDENTICAL', 'FAIL', 'PROBE'):
            raise SystemExit(f'{a.manifest}: bad expectation {expected!r} for {name}')
        row = dict(name=name, expected=expected, note=note, kld='', top='', tail='', z='', verdict='', why='')
        if not os.path.exists(cand):
            row['verdict'] = 'MISSING'
        else:
            try:
                c = parse(cand)
                row.update(kld=f'{c["kld"][0]:.6f} ± {c["kld"][1]:.6f}', top=f'{c["top"][0]:.3f} ± {c["top"][1]:.3f}',
                           tail=f'{c["kld_999"]:.3f}')
                if base == '-':
                    row['verdict'] = 'BASE'
                else:
                    g = gate(parse(base), c, a.k, a.tail_ratio)
                    row['verdict'] = g['verdict']
                    if 'z_kld' in g:
                        row['z'] = f'{g["z_kld"]:+.1f}'
                    row['why'] = '; '.join(g['reasons'])
            except LogError as err:
                row.update(verdict='ERROR', why=str(err))
        row['outcome'] = outcome(expected, row['verdict'])
        if row['outcome'] == 'UNEXPECTED' and not row['why']:
            row['why'] = f'expected {expected}, gate says {row["verdict"]}'
        unexpected += row['outcome'] == 'UNEXPECTED'
        incomplete += row['outcome'] in ('MISSING', 'ERROR')
        rows.append(row)
    cols = [('variant', 'name'), ('expected', 'expected'), ('mean KLD', 'kld'), ('dKLD/sd', 'z'),
            ('99.9% KLD', 'tail'), ('same top p %', 'top'), ('verdict', 'verdict'), ('OK/UNEXPECTED', 'outcome')]
    w = [max(len(h), *(len(r[k]) for r in rows)) for h, k in cols]
    print(' | '.join(h.ljust(n) for (h, _), n in zip(cols, w)))
    print('-|-'.join('-' * n for n in w))
    for r in rows:
        print(' | '.join(r[k].ljust(n) for (_, k), n in zip(cols, w)))
    for r in rows:
        if r['why'] and (r['outcome'] != 'OK' or a.verbose):
            print(f'  {r["name"]}: {r["why"]}')
    print(f'gate: k={a.k:g} sd, 99.9% KLD <= x{a.tail_ratio:g};  '
          f'{sum(r["outcome"] == "OK" for r in rows)} OK, {unexpected} UNEXPECTED, {incomplete} missing/error')
    return 1 if unexpected else 2 if incomplete else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('compare', 'table'):
        s = sub.add_parser(name)
        s.add_argument('--k', type=float, default=2.0, help='sigma multiplier (default 2)')
        s.add_argument('--tail-ratio', type=float, default=1.25, help='max 99.9%% KLD ratio (default 1.25)')
        if name == 'compare':
            s.add_argument('base')
            s.add_argument('cand')
            s.add_argument('--json', action='store_true')
        else:
            s.add_argument('manifest')
            s.add_argument('-v', '--verbose', action='store_true', help='print gate reasons of OK rows too')
    s = sub.add_parser('check')
    s.add_argument('log')
    a = p.parse_args()
    return {'compare': cmd_compare, 'check': cmd_check, 'table': cmd_table}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
