#!/usr/bin/env python3
"""PFlash CPU pilot: build PL and EN long documents + factual questions with known evidence."""
import json, os, re

W = os.path.expanduser('~/KERNEL/wiki')
R = os.path.expanduser('~/KERNEL/qwen-opt/research/v2')

PL_NOTES = """eksperymenty/2026-10-12-cache-promptu-i-a7.md kernele/fattn-kvq.md kernele/prefill-mmq-fa.md
lekcje/lekcja-oom-ub2048.md eksperymenty/lfm-runda-3.md kernele/mmq-epilog.md eksperymenty/2026-10-13-k3-host.md
kernele/gdn-replay.md eksperymenty/2026-10-09-pierwsze-pomiary.md eksperymenty/2026-10-12-fuzje-a3-a6.md
kernele/cache-q8-1.md lekcje/lekcja-mikrobench-klamie.md kernele/clamp-q8-1.md kernele/conv-lag.md
kernele/vulkan-mmvq.md kernele/argmax-dpp.md kernele/lfm-shortconv.md eksperymenty/lfm-baza.md
eksperymenty/2026-10-12-rocm-vs-vulkan.md lekcje/lekcja-slaby-cpu-3090.md eksperymenty/2026-10-13-s2-s4.md
kernele/fuzje-weryfikacji.md eksperymenty/runda-6.md lekcje/baco-runtime-suspend.md eksperymenty/lfm-runda-1.md
eksperymenty/2026-10-14-t1-t2-draft.md eksperymenty/2026-10-10-sweep-mtp-dflash.md
lekcje/lekcja-spekulacja-zmienia-numeryke.md eksperymenty/2026-10-16-mtp-pl-pilot.md
lekcje/lekcja-mtp-glowica-optimum.md lekcje/lekcja-fit-mtp-16gb.md lekcje/lekcja-ten-sam-serwer-pending-h.md
eksperymenty/2026-10-12-vulkan-krok-po-kroku.md""".split()

EN_FILES = ['rr-prefill-kv.md', 'rr-hip.md']

PL_Q = [
    ("Ile trwało pierwsze pytanie (zimno) do dokumentu o długości 27k tokenów w teście cache promptu?", "31.9 s"),
    ("Jak zmienił się czas llama-bench d98304 n5 po łatce kvq dla KV q4_0?", "68.2 → 36.7 ms"),
    ("Ile TFLOPS osiągnął kafel FA MMA D=256 po przeniesieniu Q do SRAM?", "40.2 → 49.0 TFLOPS"),
    ("Ile t/s dawał LFM w llama-bench przy 98k kontekstu przed i po kernelu kvq dla q8_0?", "152.4 → 191.4"),
    ("Jaki zysk w pp4096 Qwena dał epilog MMQ przepisany na pary VOPD?", "+2.2% pp4096"),
    ("Ile kosztowała za godzinę najtańsza oferta RTX 3090, którą wybrał agent?", "$0.201/h"),
    ("Do ilu mikrosekund skrócił się argmax po słowniku w drafcie MTP po użyciu DPP?", "16.8 → 4.3 µs"),
    ("Ile t/s dawał model, gdy amdgpu uśpił kartę (BACO) i model działał przez PCIe?", "4.4 zamiast 92 t/s"),
    ("Po ilu znakach tekst MTP rozjeżdża się z tekstem plain?", "po 129 znakach"),
    ("Ile t/s dawał upstreamowy serwer z -fit on i MTP na RTX 5060 Ti 16 GB?", "7.7 t/s"),
]
EN_Q = [
    ("What is the q4_0 KV cache size per token summed over all 16 attention layers?", "18,432 B"),
    ("How long did the server take to prefill the 94,181-token prompt?", "141.5 s"),
    ("Which upstream pull request removed GGML_HIP_ROCWMMA_FATTN?", "#26046"),
    ("What speedup did PR #29846 measure at ub2 for qwen35 27B at depth 32768 on the RTX 3090?", "ub2 ×1.21"),
    ("How large is one context checkpoint of the recurrent state, approximately?", "150 MB"),
    ("What is the measured GDN kernel cost per token per layer?", "0.5-0.75 µs per token per layer"),
    ("What is the fixed prompt cost for a 30-token prompt with and without MTP?", "| 30 | 150 ms | 230 ms |"),
    ("What share of the matmul FLOPs is Q6_K in the Uncensored Q4_K_M model?", "4.25 G params (17.5%)"),
    ("How much VRAM does the FA f16 scratch take at 204800 context?", "839 MB"),
    ("What effective FA throughput was derived for the 94k prefill?", "~47 TFLOPS effective FA"),
]


def strip_note(text):
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S)
    text = re.split(r'\n## Powiązane', text)[0]
    return text.strip() + '\n'


def main():
    out = '/tmp/pflash/pilot'
    cases = []
    en = '\n'.join(open(os.path.join(R, f)).read() for f in EN_FILES)
    notes = list(PL_NOTES)
    import glob
    for p in sorted(glob.glob(os.path.join(W, 'kernele/*.md')) + glob.glob(os.path.join(W, 'lekcje/*.md'))):
        rel = os.path.relpath(p, W)
        if rel not in notes and '_hub' not in rel:
            notes.append(rel)
    parts, total = [], 0
    for n in notes:
        t = strip_note(open(os.path.join(W, n)).read())
        if total > 50000 and n not in PL_NOTES:
            break
        parts.append(t)
        total += len(t)
    pl = '\n'.join(parts)
    for lang, doc, qs in (('pl', pl, PL_Q), ('en', en, EN_Q)):
        open(f'{out}/doc_{lang}.txt', 'w').write(doc)
        for i, (q, ev) in enumerate(qs):
            n = doc.count(ev)
            assert n >= 1, (lang, ev)
            cases.append({'id': f'{lang}{i}', 'lang': lang, 'question': q, 'evidence': ev, 'occurrences': n})
    json.dump(cases, open(f'{out}/cases.json', 'w'), ensure_ascii=False, indent=1)
    print(len(pl), len(en), [c['occurrences'] for c in cases])


if __name__ == '__main__':
    main()
