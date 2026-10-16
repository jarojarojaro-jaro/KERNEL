"""Build token streams from omp agent transcripts (Qwen3.8 tokenizer).

Per session: one int32 stream = rendered conversation in file order (user text, assistant text,
tool calls in Qwen XML tool-call format, tool results). Assistant thinking is excluded.
Segments (start, end, class) mark assistant outputs whose tokens we later simulate.
Compaction entries restart the stream (the model only sees the summary afterwards).
Only aggregate statistics leave this script; no text is written.
"""
import glob
import json
import os
import pickle
import sys

import numpy as np
from tokenizers import Tokenizer

TOK = Tokenizer.from_file(os.path.expanduser('~/qwen-opt/mtp-train/smoke/qwen35-0.8b-hf/tokenizer.json'))
ROOT = os.path.expanduser('~/.omp/agent/sessions')
OUT = '/tmp/specsim/agent_streams.pkl'


def render_call(name, args):
    if not isinstance(args, dict):
        args = {'input': args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)}
    parts = [f'<tool_call>\n<function={name}>\n']
    for k, v in args.items():
        if not isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False)
        parts.append(f'<parameter={k}>\n{v}\n</parameter>\n')
    parts.append('</function>\n</tool_call>')
    return ''.join(parts)


def call_class(name, args):
    if name == 'edit':
        if isinstance(args, dict) and 'old_string' in args:
            return 'edit-strrep'
        return 'edit-hashline'
    if name == 'write':
        return 'write'
    if name == 'bash':
        return 'bash'
    return 'call-other'


def session_pieces(path):
    """Yield lists of (text, cls or None) per compaction epoch."""
    epoch = []
    for line in open(path):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get('type') == 'compaction':
            if epoch:
                yield epoch
            epoch = [('<|im_start|>user\n' + d.get('summary', '') + '<|im_end|>\n', None)]
            continue
        m = d.get('message')
        if not isinstance(m, dict):
            continue
        role, c = m.get('role'), m.get('content')
        if isinstance(c, str):
            c = [{'type': 'text', 'text': c}]
        if not isinstance(c, list):
            continue
        if role in ('user', 'developer'):
            txt = ''.join(x.get('text', '') for x in c if x.get('type') == 'text')
            epoch.append(('<|im_start|>user\n' + txt + '<|im_end|>\n', None))
        elif role == 'assistant':
            epoch.append(('<|im_start|>assistant\n', None))
            for x in c:
                if x.get('type') == 'text' and x.get('text'):
                    epoch.append((x['text'] + '\n', 'assistant-text'))
                elif x.get('type') == 'toolCall':
                    a = x.get('arguments')
                    epoch.append((render_call(x.get('name'), a), call_class(x.get('name'), a)))
            epoch.append(('<|im_end|>\n', None))
        elif role == 'toolResult':
            txt = ''.join(x.get('text', '') for x in c if x.get('type') == 'text')
            epoch.append(('<|im_start|>user\n<tool_response>\n' + txt + '\n</tool_response><|im_end|>\n', None))
    if epoch:
        yield epoch


def main():
    files = sorted(glob.glob(os.path.join(ROOT, '**/*.jsonl'), recursive=True))
    out = []
    for fi, f in enumerate(files):
        for epoch in session_pieces(f):
            texts = [t for t, _ in epoch]
            enc = TOK.encode_batch(texts, add_special_tokens=False)
            ids, segs, pos = [], [], 0
            for (t, cls), e in zip(epoch, enc):
                n = len(e.ids)
                if cls and n:
                    segs.append((pos, pos + n, cls))
                ids.extend(e.ids)
                pos += n
            if segs:
                out.append((os.path.basename(os.path.dirname(f)) + '/' + str(fi), np.asarray(ids, dtype=np.int32), segs))
        if fi % 20 == 0:
            print(fi, len(files), sum(len(s[1]) for s in out), file=sys.stderr, flush=True)
    pickle.dump(out, open(OUT, 'wb'))
    tot = sum(len(s[1]) for s in out)
    by = {}
    for _, _, segs in out:
        for a, b, c in segs:
            by[c] = by.get(c, 0) + (b - a)
    print('epochs', len(out), 'stream tokens', tot, 'output tokens by class', by)


if __name__ == '__main__':
    main()
