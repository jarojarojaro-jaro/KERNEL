//! Analiza tekstu dla BM25: małe litery, zdjęcie ogonków, tokeny liczb i identyfikatorów,
//! lekki stemmer polski (obcinanie końcówek fleksyjnych), stop-słowa PL/EN, synonimy domenowe.

/// Zdejmuje polskie (i częste łacińskie) znaki diakrytyczne i zamienia na małe litery.
pub fn fold_char(c: char) -> char {
    match c {
        'ą' | 'Ą' | 'á' | 'à' | 'â' | 'ä' | 'Á' | 'Ä' => 'a',
        'ć' | 'Ć' | 'č' | 'ç' => 'c',
        'ę' | 'Ę' | 'é' | 'è' | 'ê' | 'ë' | 'É' => 'e',
        'ł' | 'Ł' => 'l',
        'ń' | 'Ń' | 'ñ' => 'n',
        'ó' | 'Ó' | 'ö' | 'ô' | 'Ö' => 'o',
        'ś' | 'Ś' | 'š' => 's',
        'ź' | 'Ź' | 'ż' | 'Ż' | 'ž' => 'z',
        'í' | 'ì' => 'i',
        'ú' | 'ü' | 'Ü' => 'u',
        _ => c.to_lowercase().next().unwrap_or(c),
    }
}

pub fn fold(s: &str) -> String {
    s.chars().map(fold_char).collect()
}

/// Stop-słowa po zdjęciu ogonków (pytania agentów: „gdzie”, „ile”, „dlaczego”, „what”, „how”).
const STOP: &[&str] = &[
    "a", "aby", "albo", "ale", "an", "and", "are", "as", "at", "be", "by", "byc", "byl", "byla",
    "bylo", "byly", "co", "czy", "dla", "do", "does", "for", "from", "gdzie", "how", "i", "ich",
    "ile", "in", "is", "it", "jak", "jaka", "jaki", "jakie", "jako", "jest", "juz", "ktora", "ktore",
    "ktory", "mamy", "ma", "na", "nad", "nam", "nas", "od", "of", "on", "or", "oraz", "po", "pod", "przez",
    "przy", "sa", "sie", "so", "tak", "tam", "te", "ten", "the", "to", "tu", "w", "was", "we", "what",
    "when", "where", "which", "why", "with", "z", "za", "ze", "zas", "dlaczego", "czemu", "kiedy",
    "jaka", "jakim", "jakiej", "mial", "miala", "mialo", "tego", "tej", "tym", "o", "u", "nie",
    "wiec", "bo", "lub", "czyli", "tez", "takze", "jesli", "gdy", "e", "np", "itd",
];

static STOP_SET: std::sync::LazyLock<std::collections::HashSet<&'static str>> =
    std::sync::LazyLock::new(|| STOP.iter().copied().collect());

pub fn is_stop(t: &str) -> bool {
    STOP_SET.contains(t)
}

/// Końcówki fleksyjne (po zdjęciu ogonków), najdłuższe najpierw. Rdzeń musi mieć ≥ 4 znaki.
const SUFFIXES: &[&str] = &[
    "owaniami", "owaniach", "owaniem", "owaniu", "owania", "owanie", "owanych", "owanym", "owanej",
    "owanego", "owana", "owane", "owany", "owali", "owala", "owalo", "owal", "owac", "ujacy", "ujaca",
    "ujace", "ujacych", "ujemy", "ujecie", "ujesz", "uje", "uja", "ujac", "aniami", "aniach", "aniem",
    "ania", "anie", "aniu", "enia", "enie", "eniu", "eniem", "eniach", "ami", "ach", "ami", "owie",
    "owi", "ow", "om", "ach", "ego", "emu", "ych", "ymi", "imi", "ich", "iej", "ej", "ym", "im", "em",
    "ie", "ia", "iu", "io", "ii", "a", "e", "i", "o", "u", "y", "s",
];

pub fn stem(w: &str) -> String {
    let n = w.chars().count();
    if n < 5 || !w.chars().all(|c| c.is_ascii_alphabetic()) {
        return w.to_string();
    }
    for suf in SUFFIXES {
        if w.len() >= suf.len() + 4 && w.ends_with(suf) {
            // angielska liczba mnoga (kernels, tests), ale nie proces/status/bias
            if *suf == "s" && !matches!(w.as_bytes()[w.len() - 2], b'l' | b'k' | b't' | b'g' | b'p' | b'd' | b'n' | b'm') {
                continue;
            }
            let mut s = w[..w.len() - suf.len()].to_string();
            if s.len() > 7 {
                s.truncate(7);
            }
            return s;
        }
    }
    let mut s = w.to_string();
    if s.len() > 7 {
        s.truncate(7);
    }
    s
}

/// Jednostki znormalizowane (wspólne z indeksem faktów).
pub fn norm_unit(u: &str) -> Option<&'static str> {
    let f = fold(u);
    Some(match f.as_str() {
        "t/s" | "tok/s" | "tokens/s" | "token/s" | "tps" | "tok/sek" => "t/s",
        "ms/krok" | "ms/step" => "ms/krok",
        "ms/token" | "ms/tok" => "ms/tok",
        "tok/krok" | "tok./krok" | "tokens/step" => "tok/krok",
        "ms" => "ms",
        "s" | "sek" => "s",
        "min" => "min",
        "h" => "h",
        "gb" | "gib" => "GB",
        "mb" | "mib" => "MB",
        "tb" => "TB",
        "%" => "%",
        "×" | "x" => "×",
        "°c" | "c" => "°C",
        "w" => "W",
        "rpm" => "RPM",
        "$" | "usd" | "$/h" | "usd/h" => "$",
        "kld" => "KLD",
        "tok" | "tok." | "tokenow" | "tokens" => "tok",
        _ => return None,
    })
}

#[derive(Debug, Clone, PartialEq)]
pub struct Tok {
    pub term: String,
    /// waga (części identyfikatorów i pochodne liczby ważą mniej niż pełny token)
    pub w: f32,
}

fn push(out: &mut Vec<Tok>, term: String, w: f32) {
    if term.is_empty() {
        return;
    }
    out.push(Tok { term, w });
}

/// Tokenizacja do BM25. Dzieli na „słowa” złożone z liter, cyfr i łączników `-_.`/` wewnątrz słowa.
pub fn analyze(text: &str) -> Vec<Tok> {
    let folded: Vec<char> = text.chars().map(fold_char).collect();
    let mut out = Vec::new();
    let n = folded.len();
    let mut i = 0;
    while i < n {
        let c = folded[i];
        // jednostki z ukośnikiem: t/s, tok/s
        if c.is_alphanumeric() {
            let start = i;
            let mut j = i;
            while j < n {
                let cj = folded[j];
                if cj.is_alphanumeric() {
                    j += 1;
                } else if (cj == '-' || cj == '_' || cj == '.' || cj == ',' || cj == '/')
                    && j + 1 < n
                    && folded[j + 1].is_alphanumeric()
                    && j > start
                {
                    // przecinek tylko między cyframi (130,2); ukośnik tylko w jednostkach t/s, tok/s
                    if cj == ',' && !(folded[j - 1].is_ascii_digit() && folded[j + 1].is_ascii_digit()) {
                        break;
                    }
                    if cj == '/' {
                        let rest: String = folded[j..n.min(j + 3)].iter().collect();
                        let pre: String = folded[start..j].iter().collect();
                        if !(rest.starts_with("/s") && matches!(pre.as_str(), "t" | "tok" | "tokens" | "token")) {
                            break;
                        }
                    }
                    j += 1;
                } else {
                    break;
                }
            }
            // grupy tysięcy: „27 327” → 27327
            let mut word: String = folded[start..j].iter().collect();
            if word.chars().all(|c| c.is_ascii_digit()) && word.len() <= 3 {
                let mut k = j;
                loop {
                    if k + 4 <= n
                        && matches!(folded[k], ' ' | '\u{a0}' | '\u{202f}' | '\u{2009}')
                        && folded[k + 1..k + 4].iter().all(|c| c.is_ascii_digit())
                        && (k + 4 == n || !folded[k + 4].is_alphanumeric())
                    {
                        word.extend(&folded[k + 1..k + 4]);
                        k += 4;
                    } else {
                        break;
                    }
                }
                j = k;
            }
            emit_word(&word, &mut out);
            i = j;
        } else {
            i += 1;
        }
    }
    out
}

fn emit_word(word: &str, out: &mut Vec<Tok>) {
    let word = word.trim_end_matches(['.', '-', '_']);
    if word.is_empty() {
        return;
    }
    if let Some(u) = norm_unit(word) {
        if word.contains('/') {
            push(out, u.to_string(), 1.0);
            return;
        }
    }
    let has_digit = word.chars().any(|c| c.is_ascii_digit());
    let has_sep = word.contains(['-', '_', '.', ',', '/']);
    if !has_digit && !has_sep {
        if is_stop(word) {
            return;
        }
        push(out, stem(word), 1.0);
        return;
    }
    if !has_sep {
        emit_alnum(word, out, 1.0);
        return;
    }
    // liczba dziesiętna (130.2, 130,2, 1.7k)
    let dec = word.replace(',', ".");
    if is_number_like(&dec) {
        emit_alnum(&dec, out, 1.0);
        return;
    }
    // identyfikator złożony: cały + części
    push(out, word.replace(',', "."), 1.0);
    for part in word.split(['-', '_', '/', ',']) {
        if part.is_empty() {
            continue;
        }
        if is_number_like(part) {
            emit_alnum(part, out, 0.5);
        } else {
            for p in part.split('.') {
                if p.is_empty() {
                    continue;
                }
                if p.chars().any(|c| c.is_ascii_digit()) {
                    emit_alnum(p, out, 0.5);
                } else if !is_stop(p) {
                    push(out, stem(p), 0.5);
                }
            }
        }
    }
}

fn is_number_like(s: &str) -> bool {
    // 130.2, 1.7k, 27b, 0.0123
    let b = s.as_bytes();
    if b.is_empty() || !b[0].is_ascii_digit() {
        return false;
    }
    let mut dots = 0;
    let mut i = 0;
    while i < b.len() && (b[i].is_ascii_digit() || b[i] == b'.') {
        if b[i] == b'.' {
            dots += 1;
        }
        i += 1;
    }
    dots <= 1 && b[i..].iter().all(|c| c.is_ascii_alphabetic()) && b.len() - i <= 2
}

/// Słowo z cyframi bez separatorów (lub liczba dziesiętna): pełny token + część liczbowa/literowa.
fn emit_alnum(word: &str, out: &mut Vec<Tok>, w: f32) {
    push(out, word.to_string(), w);
    let b = word.as_bytes();
    if b[0].is_ascii_digit() {
        // prefiks liczbowy: 130.2 → 130; 1.7k → 1.7, 1; 27b → 27
        let num_end = b.iter().position(|c| !(c.is_ascii_digit() || *c == b'.')).unwrap_or(b.len());
        let num = &word[..num_end];
        let int_end = num.find('.').unwrap_or(num.len());
        let int = &num[..int_end];
        if num_end < word.len() && !num.is_empty() {
            // 5060ti, 7900xtx: model karty pisany łącznie = „5060 ti”
            let suffix = &word[num_end..];
            if suffix.len() >= 2 && suffix.bytes().all(|c| c.is_ascii_alphabetic()) {
                push(out, num.to_string(), w);
                push(out, stem(suffix), w * 0.5);
            } else {
                push(out, num.to_string(), w * 0.5);
            }
        }
        if int_end < num.len() && int.len() >= 2 {
            push(out, int.to_string(), w * 0.5);
        }
        // 27327 → 27k (zapytania „27k”); tylko liczby całkowite ≥ 1000
        if num_end == word.len() && int_end == num.len() && int.len() >= 4 && int.len() <= 6 {
            let v: u64 = int.parse().unwrap_or(0);
            push(out, format!("{}k", v / 1000), w * 0.5);
        }
    } else {
        // prefiks literowy i liczba: qwen3 → qwen; gfx1100 → gfx, 1100; ub2048 → ub, 2048; tg128 → tg, 128
        let alpha_end = b.iter().position(|c| c.is_ascii_digit()).unwrap_or(b.len());
        if alpha_end >= 2 && alpha_end < b.len() {
            push(out, stem(&word[..alpha_end]), w * 0.5);
            let digits = &word[alpha_end..];
            if digits.len() >= 2 && digits.bytes().all(|c| c.is_ascii_digit()) {
                push(out, digits.to_string(), w * 0.5);
            }
        }
    }
}

/// Synonimy domenowe (strona zapytania). Klucze i wartości po `fold`, przed stemmingiem.
const SYNONYMS: &[(&str, &[&str])] = &[
    ("fan", &["wentylator", "rpm"]),
    ("fans", &["wentylator", "rpm"]),
    ("wentylator", &["fan", "rpm"]),
    ("wentylatory", &["fan", "rpm"]),
    ("xtx", &["7900"]),
    ("7900", &["xtx"]),
    ("koszt", &["cena", "$", "cost"]),
    ("kosztuje", &["koszt", "cena", "cost"]),
    ("cost", &["koszt", "cena"]),
    ("cena", &["koszt", "cost"]),
    ("price", &["cena", "koszt"]),
    ("decision", &["decyzja"]),
    ("decyzja", &["decision", "zasada"]),
    ("lesson", &["lekcja"]),
    ("record", &["rekord", "najlepszy"]),
    ("rekord", &["najlepszy", "record"]),
    ("best", &["najlepszy", "rekord"]),
    ("najlepszy", &["rekord"]),
    ("speed", &["t/s", "szybkosc"]),
    ("szybkosc", &["t/s", "speed"]),
    ("predkosc", &["t/s", "szybkosc"]),
    ("throughput", &["t/s"]),
    ("decode", &["dekodowanie", "tg"]),
    ("dekodowanie", &["decode", "tg"]),
    ("context", &["kontekst", "ctx"]),
    ("kontekst", &["context", "ctx"]),
    ("ctx", &["kontekst", "context"]),
    ("speculative", &["spekulacja", "spec"]),
    ("spekulacja", &["speculative", "spec", "mtp"]),
    ("quant", &["kwant", "kwantyzacja"]),
    ("kwant", &["quant", "kwantyzacja"]),
    ("crash", &["awaria", "reset", "hang"]),
    ("awaria", &["crash", "reset", "hang"]),
    ("hang", &["zawieszenie", "reset", "timeout"]),
    ("zawieszenie", &["hang", "reset", "timeout"]),
    ("temperatura", &["hotspot", "°c", "temp"]),
    ("temperature", &["temperatura", "hotspot"]),
    ("karta", &["gpu"]),
    ("card", &["karta", "gpu"]),
    ("why", &["przyczyna", "bo"]),
    ("dlaczego", &["przyczyna"]),
    ("przyczyna", &["root", "cause"]),
    ("memory", &["pamiec", "vram"]),
    ("pamiec", &["memory", "vram"]),
    ("slow", &["wolny", "regresja"]),
    ("wolno", &["regresja", "wolny"]),
    ("chmura", &["cloud", "vast", "runpod"]),
    ("wydalismy", &["koszt", "$", "budzet", "wydatki"]),
    ("wydatki", &["koszt", "$", "budzet"]),
    ("spent", &["koszt", "$", "budzet"]),
    ("ttft", &["prefill"]),
    ("trwa", &["ttft", "czas"]),
    ("cloud", &["chmura"]),
];

/// Termy zapytania: (term, waga). Synonimy dostają wagę 0.4.
pub fn analyze_query(q: &str) -> Vec<Tok> {
    let mut out = analyze(q);
    let mut extra = Vec::new();
    for raw in q.split_whitespace() {
        let f = fold(raw.trim_matches(|c: char| !c.is_alphanumeric()));
        if let Some((_, syns)) = SYNONYMS.iter().find(|(k, _)| *k == f) {
            for s in syns.iter() {
                for t in analyze(s) {
                    extra.push(Tok { term: t.term, w: 0.4 * t.w });
                }
            }
        }
    }
    // „dlaczego” to stop-słowo, ale pytanie o przyczynę: dodaj „przyczyna”
    out.extend(extra);
    // deduplikacja: najwyższa waga
    let mut dedup: Vec<Tok> = Vec::new();
    for t in out {
        if let Some(d) = dedup.iter_mut().find(|d| d.term == t.term) {
            d.w = d.w.max(t.w);
        } else {
            dedup.push(t);
        }
    }
    dedup
}

#[cfg(test)]
mod tests {
    use super::*;

    fn terms(s: &str) -> Vec<String> {
        analyze(s).into_iter().map(|t| t.term).collect()
    }

    #[test]
    fn diacritics_and_stems() {
        assert_eq!(terms("wentylatorów"), terms("wentylatory"));
        assert_eq!(terms("Wentylator"), terms("wentylatorach"));
        assert_eq!(terms("resetuje"), terms("resetów"));
        assert_eq!(terms("kosztuje"), terms("koszty"));
        assert_eq!(terms("decyzja"), terms("decyzje"));
        assert_eq!(terms("prędkość"), terms("predkosc"));
    }

    #[test]
    fn numbers() {
        let t = terms("1.7k 130.2 / 818 t/s");
        assert!(t.contains(&"130.2".to_string()));
        assert!(t.contains(&"130".to_string()));
        assert!(t.contains(&"1.7k".to_string()));
        assert!(t.contains(&"t/s".to_string()));
        assert!(t.contains(&"818".to_string()));
        let t = terms("prompt 27 327 tok.");
        assert!(t.contains(&"27327".to_string()));
        assert!(t.contains(&"27k".to_string()));
        assert!(terms("130,2 tok/s").contains(&"130.2".to_string()));
        assert!(terms("130,2 tok/s").contains(&"t/s".to_string()));
    }

    #[test]
    fn identifiers() {
        let t = terms("Qwen3.8-27B UD-Q4_K_XL pl-kod GGML_HIP_PM4");
        for want in ["qwen3.8-27b", "qwen", "27b", "pl-kod", "kod", "ggml_hip_pm4", "pm4", "q4"] {
            assert!(t.contains(&want.to_string()), "{want} w {t:?}");
        }
    }
}
