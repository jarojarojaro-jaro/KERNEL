---
typ: lekcja
tags: [lekcje, agenci, prefill]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:121-150; ~/KERNEL/product/research/21f-agentx-stats-out.txt
status: aktualne
---
# Na sesji agentowej Qwena prefill waży więcej niż decode

**Na śladach AgentX z naszymi krzywymi XTX (Qwen, limit 128k, polityka cram jak w produkcji) prefill zajmuje 148 h z 256 h zegara (58%), decode 82 h (32%): ×2 decode skraca zegar sesji o ~16%, ×2 prefill o ~29%, a zmiana polityki cache lane → radix tnie prefill 148 → 68 h (−32% zegara) (raport 21f, `[SZACUNEK]`, 2026-10-19).**

Przy 200k: ×2 decode −10.5…−25.8%, ×2 prefill −18.1…−37.0% zależnie od polityki. Dla LFM odwrotnie – przy dobrym cache decode to 52–62% zegara (cram 128k 51.8%), więc kernele decode ważą tam ~2× więcej. Zysk ogona lookupu ×2.4 dotyczy tylko kopiującej części decode – na całą sesję agentową raczej −10…−20%.

Reguła: dla Qwena w pracy agentowej priorytet mają prefill i współdzielenie cache prefiksów między torami (kierunek `CACHE_SHARE_MIN`, cache na SSD), a nie kolejne kernele decode.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[ksztalt-ruchu-agentowego]]
- [[2026-10-18-cache-promptu-agenta]]
- [[cache-sesji-na-dysku]]
