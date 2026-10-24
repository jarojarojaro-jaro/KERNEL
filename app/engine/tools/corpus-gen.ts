// Generates data/corpus.txt: the fixed benchmark text (Polish + English prose, written for this project, public domain).
// Deterministic: a seeded PRNG composes paragraphs from the sentence parts below, alternating languages.
//   bun tools/corpus-gen.ts
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rnd = mulberry32(20261024);
const pick = <T>(xs: readonly T[]): T => xs[Math.floor(rnd() * xs.length)] as T;

const EN = {
  subj: ['The old lighthouse keeper', 'A young engineer from the coast', 'The village baker', 'Our neighbour with the red bicycle', 'The river pilot', 'A quiet student of astronomy', 'The miller', 'The schoolteacher', 'A travelling clockmaker', 'The ferryman', 'The librarian of the northern town', 'A fisherman with weathered hands'],
  verb: ['carefully repaired', 'slowly measured', 'patiently explained', 'quietly described', 'cheerfully counted', 'precisely drew', 'thoughtfully compared', 'gently cleaned', 'proudly displayed', 'calmly recorded'],
  obj: ['the brass instruments of the harbour', 'a map of the forgotten islands', 'the gears of the tower clock', 'the tides of the coming week', 'a long letter from the capital', 'the seeds stored for the spring', 'the stars above the frozen lake', 'the ledger of the cooperative', 'a wooden model of the bridge', 'the recipes of the winter market'],
  adv: ['before the first light of dawn', 'while the rain drummed on the roof', 'after the evening bells had rung', 'during the long autumn evenings', 'as the wind turned to the east', 'when the market square was empty', 'in the warm kitchen by the stove', 'under the lamp of the reading room'],
  tail: ['and nobody in the town forgot it.', 'so that the children could learn from it.', 'because the season demanded patience.', 'and wrote every detail into a small notebook.', 'as if the whole world depended on that work.', 'and then walked home along the cliffs.', 'which surprised even the oldest sailors.', 'and the result was simple and beautiful.'],
} as const;

const PL = {
  subj: ['Stary latarnik', 'Młoda inżynierka z wybrzeża', 'Wiejski piekarz', 'Sąsiad z czerwonym rowerem', 'Rzeczny pilot', 'Cicha studentka astronomii', 'Młynarz', 'Nauczycielka z małej szkoły', 'Wędrowny zegarmistrz', 'Przewoźnik', 'Bibliotekarka z północnego miasteczka', 'Rybak o spracowanych dłoniach'],
  verb: ['starannie naprawił', 'powoli zmierzył', 'cierpliwie objaśnił', 'spokojnie opisał', 'radośnie policzył', 'dokładnie narysował', 'w zamyśleniu porównał', 'delikatnie oczyścił', 'z dumą pokazał', 'skrupulatnie zapisał'],
  obj: ['mosiężne przyrządy portu', 'mapę zapomnianych wysp', 'tryby zegara na wieży', 'przypływy nadchodzącego tygodnia', 'długi list ze stolicy', 'nasiona przechowane na wiosnę', 'gwiazdy nad zamarzniętym jeziorem', 'księgę spółdzielni', 'drewniany model mostu', 'przepisy z zimowego targu'],
  adv: ['przed pierwszym brzaskiem', 'kiedy deszcz bębnił o dach', 'gdy przebrzmiały wieczorne dzwony', 'podczas długich jesiennych wieczorów', 'gdy wiatr skręcił na wschód', 'kiedy rynek był już pusty', 'w ciepłej kuchni przy piecu', 'pod lampą w czytelni'],
  tail: ['i nikt w miasteczku o tym nie zapomniał.', 'aby dzieci mogły się z tego uczyć.', 'bo pora roku wymagała cierpliwości.', 'i każdy szczegół zanotował w małym zeszycie.', 'jakby od tej pracy zależał cały świat.', 'a potem wrócił do domu ścieżką nad klifem.', 'co zaskoczyło nawet najstarszych żeglarzy.', 'a wynik był prosty i piękny.'],
} as const;

const OPENING = `The Harbour Notebook / Zeszyt z portu

This text was written for the Enigma benchmark. It describes ordinary people in a small coastal town and the
patient work they do through the seasons. It is released into the public domain.

Ten tekst powstał na potrzeby benchmarku Enigmy. Opisuje zwykłych ludzi z małego nadmorskiego miasteczka i ich
cierpliwą pracę w kolejnych porach roku. Tekst jest własnością publiczną (domena publiczna).
`;

function sentence(lang: typeof EN | typeof PL): string {
  return `${pick(lang.subj)} ${pick(lang.verb)} ${pick(lang.obj)} ${pick(lang.adv)}, ${pick(lang.tail)}`;
}

const parts: string[] = [OPENING];
for (let chapter = 1; chapter <= 60; chapter++) {
  const en = chapter % 2 === 1;
  parts.push(en ? `\nChapter ${chapter}\n` : `\nRozdział ${chapter}\n`);
  for (let p = 0; p < 6; p++) {
    const n = 4 + Math.floor(rnd() * 4);
    const ss: string[] = [];
    for (let s = 0; s < n; s++) ss.push(sentence(en ? EN : PL));
    parts.push(ss.join(' '));
  }
}
const text = parts.join('\n') + '\n';
writeFileSync(join(import.meta.dir, '..', 'data', 'corpus.txt'), text);
console.log(`data/corpus.txt: ${text.length} chars`);
