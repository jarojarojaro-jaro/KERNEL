//! Podział Markdown na fragmenty z zakresem linii: akapit, punkt listy, wiersz tabeli
//! (z nagłówkiem tabeli jako kontekstem), blok kodu. Kontekst = tytuł notatki + ścieżka nagłówków.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Chunk {
    pub file: u32,
    /// linie 1-based, włącznie
    pub start: u32,
    pub end: u32,
    /// ścieżka nagłówków „H1 > H2 > H3”
    pub heading: String,
    /// nagłówek tabeli dla wierszy tabel (pusty dla innych)
    pub table_header: String,
    pub text: String,
}

pub struct Doc {
    pub title: String,
    pub tags: String,
    pub chunks: Vec<Chunk>,
}

const MAX_CHARS: usize = 900;
const MERGE_UNDER: usize = 160;
const MERGE_MAX: usize = 520;

#[derive(PartialEq, Clone, Copy)]
enum Kind {
    Para,
    List,
    Table,
    Code,
}

struct Block {
    kind: Kind,
    start: u32,
    end: u32,
    lines: Vec<String>,
    heading: String,
    table_header: String,
}

fn heading_level(line: &str) -> Option<(usize, &str)> {
    let t = line.trim_start();
    if !t.starts_with('#') || line.len() - t.len() > 3 {
        return None;
    }
    let lvl = t.bytes().take_while(|&b| b == b'#').count();
    if lvl == 0 || lvl > 6 {
        return None;
    }
    let rest = &t[lvl..];
    if !rest.is_empty() && !rest.starts_with(' ') {
        return None;
    }
    Some((lvl, rest.trim()))
}

fn is_list_item(line: &str) -> bool {
    let t = line.trim_start();
    if t.starts_with("- ") || t.starts_with("* ") || t.starts_with("+ ") {
        return true;
    }
    let d = t.bytes().take_while(|b| b.is_ascii_digit()).count();
    d > 0 && d < 4 && (t[d..].starts_with(". ") || t[d..].starts_with(") "))
}

fn is_table_sep(line: &str) -> bool {
    let t = line.trim();
    t.starts_with('|') && t.chars().all(|c| matches!(c, '|' | '-' | ':' | ' '))
}

/// Parsuje frontmatter YAML (płaski klucz: wartość). Zwraca (meta, numer pierwszej linii treści 0-based).
fn frontmatter(lines: &[&str]) -> (Vec<(String, String)>, usize) {
    if lines.first().map(|l| l.trim_end()) != Some("---") {
        return (Vec::new(), 0);
    }
    for (i, l) in lines.iter().enumerate().skip(1) {
        if l.trim_end() == "---" {
            let meta = lines[1..i]
                .iter()
                .filter(|l| !l.starts_with([' ', '-']))
                .filter_map(|l| l.split_once(':'))
                .map(|(k, v)| (k.trim().to_string(), v.trim().to_string()))
                .collect();
            return (meta, i + 1);
        }
    }
    (Vec::new(), 0)
}

pub fn chunk_markdown(file: u32, text: &str, fallback_title: &str) -> Doc {
    let lines: Vec<&str> = text.lines().collect();
    let (meta, body_start) = frontmatter(&lines);
    let tags = meta
        .iter()
        .find(|(k, _)| k == "tags")
        .map(|(_, v)| v.trim_matches(['[', ']']).replace(',', " "))
        .unwrap_or_default();
    let mut title = String::new();
    let mut stack: Vec<(usize, String)> = Vec::new();
    let mut blocks: Vec<Block> = Vec::new();
    let mut cur: Option<Block> = None;
    let mut table_header = String::new();
    let mut in_code = false;

    let heading_path = |stack: &Vec<(usize, String)>| -> String {
        stack.iter().map(|(_, h)| h.as_str()).collect::<Vec<_>>().join(" > ")
    };

    for (idx, raw) in lines.iter().enumerate().skip(body_start) {
        let ln = (idx + 1) as u32;
        let line = raw.trim_end();
        if in_code {
            let b = cur.as_mut().expect("blok kodu");
            b.lines.push(line.to_string());
            b.end = ln;
            if line.trim_start().starts_with("```") || line.trim_start().starts_with("~~~") {
                in_code = false;
                blocks.push(cur.take().unwrap());
            }
            continue;
        }
        if line.trim_start().starts_with("```") || line.trim_start().starts_with("~~~") {
            if let Some(b) = cur.take() {
                blocks.push(b);
            }
            in_code = true;
            cur = Some(Block {
                kind: Kind::Code,
                start: ln,
                end: ln,
                lines: vec![line.to_string()],
                heading: heading_path(&stack),
                table_header: String::new(),
            });
            continue;
        }
        if let Some((lvl, h)) = heading_level(line) {
            if let Some(b) = cur.take() {
                blocks.push(b);
            }
            if lvl == 1 && title.is_empty() {
                title = h.to_string();
            }
            while stack.last().is_some_and(|(l, _)| *l >= lvl) {
                stack.pop();
            }
            stack.push((lvl, h.to_string()));
            continue;
        }
        if line.trim().is_empty() {
            if let Some(b) = cur.take() {
                blocks.push(b);
            }
            continue;
        }
        let t = line.trim_start();
        if t.starts_with('|') {
            if is_table_sep(line) {
                continue;
            }
            // pierwszy wiersz tabeli = nagłówek (gdy następna linia to separator)
            let next_sep = lines.get(idx + 1).is_some_and(|l| is_table_sep(l));
            if next_sep {
                if let Some(b) = cur.take() {
                    blocks.push(b);
                }
                table_header = line.to_string();
                continue;
            }
            if let Some(b) = cur.take() {
                blocks.push(b);
            }
            blocks.push(Block {
                kind: Kind::Table,
                start: ln,
                end: ln,
                lines: vec![line.to_string()],
                heading: heading_path(&stack),
                table_header: table_header.clone(),
            });
            continue;
        }
        let list = is_list_item(line);
        let indent = line.len() - t.len();
        match cur.as_mut() {
            // kontynuacja punktu listy (wcięcie bez nowego punktu) albo akapitu
            Some(b) if !list && (b.kind == Kind::Para || (b.kind == Kind::List && (indent > 0 || !list))) => {
                b.lines.push(line.to_string());
                b.end = ln;
            }
            _ => {
                if let Some(b) = cur.take() {
                    blocks.push(b);
                }
                cur = Some(Block {
                    kind: if list { Kind::List } else { Kind::Para },
                    start: ln,
                    end: ln,
                    lines: vec![line.to_string()],
                    heading: heading_path(&stack),
                    table_header: String::new(),
                });
            }
        }
    }
    if let Some(b) = cur.take() {
        blocks.push(b);
    }
    if title.is_empty() {
        title = fallback_title.to_string();
    }

    let mut chunks: Vec<Chunk> = Vec::new();
    let mut pending: Option<Block> = None;
    for b in blocks {
        // łączymy krótkie punkty/akapity z tej samej sekcji, żeby fragment miał kontekst
        if let Some(p) = pending.as_mut() {
            let plen: usize = p.lines.iter().map(|l| l.len()).sum();
            let blen: usize = b.lines.iter().map(|l| l.len()).sum();
            if p.heading == b.heading
                && p.kind != Kind::Table
                && b.kind != Kind::Table
                && p.kind != Kind::Code
                && b.kind != Kind::Code
                && plen < MERGE_UNDER.max(1)
                && plen + blen <= MERGE_MAX
            {
                // puste linie między blokami zostają, żeby numeracja linii w emit() się zgadzała
                for _ in p.end + 1..b.start {
                    p.lines.push(String::new());
                }
                p.lines.extend(b.lines);
                p.end = b.end;
                continue;
            }
        }
        if let Some(p) = pending.take() {
            emit(file, p, &mut chunks);
        }
        pending = Some(b);
    }
    if let Some(p) = pending.take() {
        emit(file, p, &mut chunks);
    }
    Doc { title, tags, chunks }
}

/// Zamienia blok na fragmenty; długie bloki dzieli po liniach, a pojedyncze długie linie po zdaniach.
fn emit(file: u32, b: Block, out: &mut Vec<Chunk>) {
    let mut acc = String::new();
    let mut acc_start = b.start;
    let mut ln = b.start;
    let flush = |acc: &mut String, s: u32, e: u32, out: &mut Vec<Chunk>| {
        if !acc.trim().is_empty() {
            out.push(Chunk {
                file,
                start: s,
                end: e,
                heading: b.heading.clone(),
                table_header: b.table_header.clone(),
                text: std::mem::take(acc),
            });
        }
        acc.clear();
    };
    for line in &b.lines {
        if line.len() > MAX_CHARS {
            flush(&mut acc, acc_start, ln.saturating_sub(1).max(acc_start), out);
            for piece in split_sentences(line, MAX_CHARS * 2 / 3) {
                let mut p = piece;
                flush(&mut p, ln, ln, out);
            }
            ln += 1;
            acc_start = ln;
            continue;
        }
        if !acc.is_empty() && acc.len() + line.len() > MAX_CHARS {
            flush(&mut acc, acc_start, ln - 1, out);
            acc_start = ln;
        }
        if !acc.is_empty() {
            acc.push('\n');
        }
        acc.push_str(line);
        ln += 1;
    }
    flush(&mut acc, acc_start, ln - 1, out);
}

fn split_sentences(line: &str, target: usize) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut rest = line;
    while !rest.is_empty() {
        // koniec zdania: ". ", "; ", " — " po przekroczeniu celu
        let cut = rest
            .match_indices(['.', ';', '!', '?'])
            .map(|(i, _)| i + 1)
            .find(|&i| rest[i..].starts_with(' ') && cur.len() + i >= target / 2)
            .unwrap_or(rest.len());
        cur.push_str(&rest[..cut]);
        rest = &rest[cut..];
        if cur.len() >= target || rest.is_empty() {
            out.push(std::mem::take(&mut cur));
        }
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const MD: &str = "---\ntyp: meta\ntags: [a, b]\n---\n# Tytuł\n\n**Streszczenie.**\n\n## Sekcja XTX\n\n| metryka | rekord |\n|---|---|\n| decode | **130.2 t/s** |\n| prefill | 818 t/s |\n\n- punkt pierwszy\n  ciąg dalszy\n- punkt drugi\n\n```\nkod\n```\n";

    #[test]
    fn spans_and_context() {
        let d = chunk_markdown(0, MD, "x");
        assert_eq!(d.title, "Tytuł");
        assert_eq!(d.tags.trim(), "a  b");
        let row = d.chunks.iter().find(|c| c.text.contains("130.2")).unwrap();
        assert_eq!((row.start, row.end), (13, 13));
        assert_eq!(row.heading, "Tytuł > Sekcja XTX");
        assert!(row.table_header.contains("rekord"));
        // krótki akapit po streszczeniu jest dołączany, ale numer linii musi się zgadzać
        let merged = chunk_markdown(0, "# T\n\n**Krótko.**\n\nDruga 3426 RPM.\n", "x");
        assert_eq!((merged.chunks[0].start, merged.chunks[0].end), (3, 5));
        assert_eq!(merged.chunks[0].text.lines().nth(2), Some("Druga 3426 RPM."));
        let li = d.chunks.iter().find(|c| c.text.contains("punkt pierwszy")).unwrap();
        assert_eq!(li.start, 16);
        assert!(li.end >= 17);
        let code = d.chunks.iter().find(|c| c.text.contains("kod")).unwrap();
        assert_eq!((code.start, code.end), (20, 22));
    }

    #[test]
    fn long_line_split_keeps_line() {
        let long = format!("# T\n\n{}\n", "Zdanie numer jeden jest tu. ".repeat(80));
        let d = chunk_markdown(0, &long, "x");
        assert!(d.chunks.len() >= 2);
        assert!(d.chunks.iter().all(|c| c.start == 3 && c.end == 3));
    }
}
