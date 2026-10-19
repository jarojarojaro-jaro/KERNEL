//! Indeks faktów: każda liczba z jednostką (t/s, ms, GB, %, ×, $, KLD, RPM, °C…) z etykietą
//! (tekst tuż przed liczbą, nagłówek kolumny i pierwsza komórka wiersza tabeli) i linią źródłową.

use crate::analyze::norm_unit;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Fact {
    pub chunk: u32,
    pub line: u32,
    pub value: f64,
    pub unit: String,
    /// liczba z jednostką tak jak w tekście
    pub raw: String,
    /// lokalna etykieta: tekst przed liczbą w komórce/zdaniu + kolumna + wiersz tabeli
    pub label: String,
}

static NUM_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
            r"(?P<pre>[×$]|\bx)?\s?",
            r"(?P<num>\d{1,3}(?:[\u{a0}\u{202f}\u{2009} ]\d{3})+|\d+(?:[.,]\d+)?)",
            r"(?:\s?(?P<unit>tokens/s|tok/s|t/s|ms/krok|ms/token|ms/tok|tok\./krok|tok/krok|ms|GiB|GB|MB|MiB|TB|%|×|x|°C|RPM|USD|\$/h|s|sek|h|min|tok\.|tok|W))?"
    ))
    .unwrap()
});

static KLD_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\b(kld|ppl)\b[^0-9|.`/_-]{0,24}$").unwrap());

struct Raw {
    s: usize,
    e: usize,
    value: f64,
    unit: Option<&'static str>,
    label: String,
}

fn parse_value(num: &str) -> Option<f64> {
    let clean: String = num.chars().filter(|c| c.is_ascii_digit() || *c == '.' || *c == ',').collect();
    let clean = if clean.matches(',').count() == 1 && !clean.contains('.') { clean.replace(',', ".") } else { clean.replace(',', "") };
    clean.parse().ok()
}

/// Granice „zdań” dla etykiet i dziedziczenia jednostek: `;`, `|`, nawiasy, kropka kończąca zdanie.
fn segment_bounds(text: &str) -> Vec<usize> {
    let b = text.as_bytes();
    let mut v = Vec::new();
    for (i, &c) in b.iter().enumerate() {
        let end_sentence = c == b'.' && i > 0 && !b[i - 1].is_ascii_digit() && b.get(i + 1).is_none_or(|n| *n == b' ');
        if matches!(c, b';' | b'|' | b'(' | b')' | b'\n') || end_sentence {
            v.push(i);
        }
    }
    v
}

/// Liczby z jednostkami w fragmencie tekstu (komórce tabeli albo linii), z etykietą lokalną.
fn scan(text: &str, default_unit: Option<&'static str>) -> Vec<Raw> {
    let mut out: Vec<Raw> = Vec::new();
    let mut at = 0;
    while let Some(m) = NUM_RE.captures_at(text, at) {
        let whole = m.get(0).unwrap();
        let num = m.name("num").unwrap();
        // odrzucone dopasowanie nie może „zjeść” prefiksu następnej liczby (×2.41 po „W16 ”)
        at = num.end();
        // „5 105.4” to dwie liczby, nie grupa tysięcy: zaczynamy od nowa za pierwszą cyfrą
        if let Some(sp) = num.as_str().find(|c: char| !c.is_ascii_digit()) {
            let rest = &text[num.end()..];
            if rest.starts_with(['.', ',']) && rest[1..].starts_with(|c: char| c.is_ascii_digit()) {
                at = num.start() + sp;
                continue;
            }
        }
        // nie wewnątrz identyfikatora/daty/wersji: qwen3.8, q4_0, 2026-10-14, v1.2.3
        let before = text[..num.start()].chars().next_back();
        if before.is_some_and(|c| c.is_alphanumeric() || c == '.' || c == '_' || c == '-' && m.name("pre").is_none() && text[..num.start()].chars().rev().nth(1).is_some_and(|d| d.is_alphanumeric())) {
            continue;
        }
        let after = text[whole.end()..].chars().next();
        let unit_m = m.name("unit");
        if after.is_some_and(|c| c.is_alphanumeric() || c == '_' || (c == '.' || c == '-') && text[whole.end() + 1..].chars().next().is_some_and(|d| d.is_ascii_digit())) {
            // „27B”, „1.7k”, „4_0”, „10-14” – to nie wartość z jednostką
            if unit_m.is_none() || unit_m.is_some_and(|u| u.as_str().chars().all(|c| c.is_alphabetic())) {
                continue;
            }
        }
        let Some(value) = parse_value(num.as_str()) else { continue };
        let mut unit = unit_m.and_then(|u| norm_unit(u.as_str()));
        if let Some(p) = m.name("pre") {
            unit = match p.as_str() {
                "×" | "x" => Some("×"),
                "$" => Some("$"),
                _ => unit,
            };
        }
        // „x”/„×” po spacji to nie mnożnik („4 x 3090”); „2.41x”, „2.41×” tak
        let mut end = whole.end();
        if unit_m.is_some_and(|u| matches!(u.as_str(), "x" | "×") && u.start() > num.end()) && m.name("pre").is_none() {
            unit = None;
            end = num.end();
        }
        if unit.is_none() && KLD_RE.is_match(&text[..num.start()]) {
            unit = Some(if text[..num.start()].to_lowercase().contains("ppl") { "PPL" } else { "KLD" });
        }
        let s = m.name("pre").map_or(num.start(), |p| p.start());
        let e = if unit.is_some() { end } else { num.end() };
        at = at.max(e);
        out.push(Raw { s, e, value, unit, label: String::new() });
    }
    let bounds = segment_bounds(text);
    let seg = |pos: usize| bounds.iter().filter(|&&b| b < pos).count();
    // „pl-proza 99.8, pl-tech 118.6, pl-kod 125.3 t/s”, „818 / 985 / 766 t/s”: jednostka następnej
    // liczby z tego samego zdania, jeśli rząd wielkości podobny (×0.05–20)
    for i in (0..out.len()).rev() {
        if out[i].unit.is_some() {
            continue;
        }
        let si = seg(out[i].s);
        // tylko element listy: następna liczba blisko i oddzielona przecinkiem/ukośnikiem/strzałką
        // („7900 XTX 128K prefill measured 926 tok/s” – 7900 nie dziedziczy)
        let j = i + 1;
        if j < out.len() && out[j].unit.is_some() {
            let gap = &text[out[i].e..out[j].s];
            let listy = gap.len() <= 40 && (gap.contains([',', '/', '→']) || gap.contains("->") || gap.contains(" vs "));
            let r = out[i].value / out[j].value;
            if listy && seg(out[j].s) == si && (0.05..=20.0).contains(&r) {
                out[i].unit = out[j].unit;
            }
        }
    }
    // etykieta: tekst od poprzedniej liczby albo początku zdania; sama interpunkcja = etykieta poprzedniej
    let mut prev: Option<(usize, usize, String)> = None;
    for r in out.iter_mut() {
        let si = seg(r.s);
        let from = match &prev {
            Some((pe, ps, _)) if *ps == si => *pe,
            _ => bounds.iter().rev().find(|&&b| b < r.s).map_or(0, |b| b + 1),
        };
        let mut l = clip_tail(text[from..r.s].trim_matches(|c: char| c.is_whitespace() || ",/→:*".contains(c)), 80);
        if !l.chars().any(|c| c.is_alphabetic()) {
            if let Some((_, ps, pl)) = &prev {
                if *ps == si {
                    l = pl.clone();
                }
            }
        }
        r.label = l.clone();
        prev = Some((r.e, si, l));
    }
    for r in out.iter_mut() {
        if r.unit.is_none() {
            r.unit = default_unit;
        }
    }
    out.retain(|r| r.unit.is_some());
    out
}

fn clip_tail(s: &str, max: usize) -> String {
    let mut start = s.len().saturating_sub(max);
    while !s.is_char_boundary(start) {
        start += 1;
    }
    s[start..].trim().to_string()
}

fn unit_in_header(h: &str) -> Option<&'static str> {
    let l = h.to_lowercase();
    for (pat, u) in [
        ("t/s", "t/s"),
        ("tok/s", "t/s"),
        ("ms/krok", "ms/krok"),
        ("tok/krok", "tok/krok"),
        ("(ms)", "ms"),
        (" ms", "ms"),
        ("(s)", "s"),
        ("kld", "KLD"),
        ("(%)", "%"),
        ("mib", "MB"),
        ("(mb)", "MB"),
        ("gib", "GB"),
        ("gb", "GB"),
        ("$", "$"),
        ("usd", "$"),
        ("rpm", "RPM"),
        ("°c", "°C"),
    ] {
        if l.contains(pat) {
            return Some(u);
        }
    }
    None
}

fn split_cells(row: &str) -> Vec<&str> {
    let t = row.trim();
    let t = t.strip_prefix('|').unwrap_or(t);
    let t = t.strip_suffix('|').unwrap_or(t);
    t.split('|').collect()
}

/// Fakty z linii fragmentu. `table_header` niepusty = linia jest wierszem tabeli.
pub fn extract(chunk: u32, line_no: u32, line: &str, table_header: &str, out: &mut Vec<Fact>) {
    if line.trim_start().starts_with('|') && !table_header.is_empty() {
        let cells = split_cells(line);
        let heads = split_cells(table_header);
        let row_label = cells.first().map(|c| c.trim()).unwrap_or("");
        for (ci, cell) in cells.iter().enumerate() {
            let head = heads.get(ci).map(|h| h.trim()).unwrap_or("");
            // jednostka z nazwy wiersza („VRAM (MiB)”) ma pierwszeństwo przed nagłówkiem kolumny
            let unit = if ci == 0 { None } else { unit_in_header(row_label).or_else(|| unit_in_header(head)) };
            for r in scan(cell, unit) {
                out.push(Fact {
                    chunk,
                    line: line_no,
                    value: r.value,
                    unit: r.unit.unwrap().to_string(),
                    raw: cell[r.s..r.e].trim().to_string(),
                    label: format!("{} | {} | {}", row_label, head, r.label),
                });
            }
        }
        return;
    }
    for r in scan(line, None) {
        out.push(Fact {
            chunk,
            line: line_no,
            value: r.value,
            unit: r.unit.unwrap().to_string(),
            raw: line[r.s..r.e].trim().to_string(),
            label: r.label,
        });
    }
}

/// Kierunek „lepszy” dla jednostki: przepustowość i przyspieszenie w górę, czas/koszt/KLD w dół.
pub fn higher_is_better(unit: &str) -> bool {
    matches!(unit, "t/s" | "×" | "tok/krok" | "%")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn facts(line: &str, hdr: &str) -> Vec<(f64, String, String)> {
        let mut v = Vec::new();
        extract(0, 1, line, hdr, &mut v);
        v.into_iter().map(|f| (f.value, f.unit, f.label)).collect()
    }

    #[test]
    fn prose_numbers() {
        let f = facts("- Długi kontekst (T=0, decode / prefill): 1.7k 130.2 / 818, 6.6k 118.5 / 985, 94k 100.6 / 766 t/s.", "");
        let vals: Vec<f64> = f.iter().map(|x| x.0).collect();
        assert!(vals.contains(&130.2) && vals.contains(&818.0) && vals.contains(&100.6), "{f:?}");
        assert!(f.iter().all(|x| x.1 == "t/s"), "{f:?}");
        assert!(!vals.contains(&1.7) && !vals.contains(&94.0));
    }

    #[test]
    fn table_row() {
        let f = facts(
            "| spec_sweep per prompt | pl-proza 99.8, pl-tech 118.6, **pl-kod 125.3**, en-chat 87.8 t/s | 2026-10-15 |",
            "| obciążenie / metryka | rekord | data |",
        );
        let pk = f.iter().find(|x| x.0 == 125.3).expect("125.3");
        assert!(pk.2.contains("pl-kod"), "{pk:?}");
        assert!(pk.2.contains("spec_sweep per prompt"));
        assert!(!f.iter().any(|x| x.0 == 2026.0));
    }

    #[test]
    fn units_and_prefixes() {
        let f = facts("W16 ×2.41, koszt $12.50, KLD 0.0123, 8019 → 1612 ms, wentylator 3300 RPM, Qwen3.8-27B q4_0 gfx1100", "");
        let has = |v: f64, u: &str| f.iter().any(|x| x.0 == v && x.1 == u);
        assert!(has(2.41, "×"), "{f:?}");
        assert!(has(12.5, "$"));
        assert!(has(0.0123, "KLD"));
        assert!(has(8019.0, "ms") && has(1612.0, "ms"));
        assert!(has(3300.0, "RPM"));
        assert!(!f.iter().any(|x| x.0 == 27.0 || x.0 == 3.8 || x.0 == 1100.0));
        assert!(facts("`16e-kwanty-kld.md:247`", "").is_empty());
        assert!(facts("LFM: pp 2k 7907 vs 5890 t/s", "").iter().any(|x| x.0 == 7907.0));
        let n = facts("7900 XTX 128K prefill measured 926 tok/s; tokenów 5 105.4 t/s", "");
        assert!(!n.iter().any(|x| x.0 == 7900.0 || x.0 == 5105.4), "{n:?}");
        assert!(n.iter().any(|x| x.0 == 105.4 && x.1 == "t/s"), "{n:?}");
        let g = facts("prompt 27 327 tok. kosztuje 1.3%", "");
        assert!(g.iter().any(|x| x.0 == 27327.0 && x.1 == "tok"), "{g:?}");
        assert!(g.iter().any(|x| x.0 == 1.3 && x.1 == "%"));
    }
}
