#!/usr/bin/env python3
"""needle.py — long-context retrieval gate (SOP-DOBOR-I-POMIARY.md §4, gate J3) against a running llama-server.

Usage: needle.py --port 18765 --tokens 131072 --corpus corpus.txt [--corpus more.txt ...] [--label X] [--out needle.jsonl]
Builds a haystack of ~--tokens tokens (server /tokenize decides, trimmed to fit) from the corpus files (repeated if short),
hides 5 facts (random 6-digit codes tied to PL/EN keys) at depths 10/30/50/70/90 %, asks for all 5 in one question
(T=0, 200 tokens). PASS = 5/5 codes exact and no invented code; the gate requires PASS at the chosen -c (and 200k
when chosen). One request = one full prefill: on a 3090 128k takes ~3 min. Prints one JSON line, exit 0 PASS / 1 FAIL.
"""
import argparse, json, random, re, sys, time, urllib.request

KEYS = ['kod sejfu w Gdańsku', 'vault code in Lisbon', 'numer zamówienia Marty', 'build id of the Orion branch',
        'PIN do skrytki 17']


def post(port, path, body, timeout=3600):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def ntok(port, text):
    return len(post(port, '/tokenize', {'content': text})['tokens'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=18765); ap.add_argument('--tokens', type=int, required=True)
    ap.add_argument('--corpus', action='append', required=True); ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--label', default='needle'); ap.add_argument('--out')
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    codes = [f'{rnd.randrange(10**5, 10**6)}' for _ in KEYS]
    text = '\n\n'.join(open(p, encoding='utf-8', errors='replace').read() for p in a.corpus)
    budget = a.tokens - 600  # question + answer + template
    # chars per token from a 20k-char sample, then trim with the real tokenizer
    cpt = 20000 / max(1, ntok(a.port, text[:20000]))
    hay = (text * (int(budget * cpt / max(1, len(text))) + 2))[:int(budget * cpt)]
    while ntok(a.port, hay) > budget - 5 * 40:
        hay = hay[:int(len(hay) * 0.97)]
    paras = hay.split('\n\n')
    for i, (k, c) in enumerate(zip(KEYS, codes)):
        pos = int(len(paras) * (0.1 + 0.2 * i))
        paras.insert(pos, f'WAŻNE / IMPORTANT: {k} to/is {c}. Zapamiętaj / remember it.')
    hay = '\n\n'.join(paras)
    q = ('Powyżej jest długi dokument. Podaj dokładnie pięć wartości ukrytych w zdaniach "WAŻNE / IMPORTANT", '
         'w formacie "klucz: wartość", po jednej w linii, bez komentarza. Keys: ' + '; '.join(KEYS))
    t0 = time.time()
    r = post(a.port, '/v1/chat/completions', {'messages': [{'role': 'user', 'content': hay + '\n\n' + q}],
                                              'temperature': 0, 'max_tokens': 2048, 'seed': 1})  # room for thinking
    dt = time.time() - t0
    ans = r['choices'][0]['message'].get('content') or ''
    found = set(re.findall(r'\b\d{6}\b', ans))
    hit = sum(c in found for c in codes); invented = len(found - set(codes))
    res = dict(label=a.label, tokens_prompt=r.get('usage', {}).get('prompt_tokens'), target=a.tokens, hits=hit,
               invented=invented, passed=(hit == 5 and invented == 0), seconds=round(dt, 1), answer=ans[:400])
    line = json.dumps(res, ensure_ascii=False)
    print(line)
    if a.out:
        with open(a.out, 'a') as f: f.write(line + '\n')
    sys.exit(0 if res['passed'] else 1)


if __name__ == '__main__':
    main()
