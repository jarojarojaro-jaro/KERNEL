//! Formatowanie wyników (tekst dla ludzi, JSON dla agentów). Zwraca (stdout, stderr), żeby ten sam
//! kod działał w procesie i w demonie `kb serve`.

use crate::analyze::analyze_query;
use crate::index::{Config, Index};
use crate::search::{snippet, FactHit, Hit, Intent, Mode};
use serde_json::json;
use std::fmt::Write;

pub struct Out {
    pub stdout: String,
    pub stderr: String,
}

fn home_path(cfg: &Config, rel: &str) -> String {
    let full = cfg.root.join(rel);
    let s = full.to_string_lossy();
    match std::env::var("HOME") {
        Ok(h) if s.starts_with(&h) => format!("~{}", &s[h.len()..]),
        _ => s.to_string(),
    }
}

pub fn line_text(idx: &Index, ci: u32, line: u32) -> &str {
    let c = &idx.chunks[ci as usize];
    c.text.lines().nth(line.saturating_sub(c.start) as usize).unwrap_or("")
}

pub fn hits(cfg: &Config, idx: &Index, q: &str, hits: &[Hit], mode: Mode, json: bool, full: bool, ms: f64) -> Out {
    let qt = analyze_query(q);
    let mut o = String::new();
    if json {
        let arr: Vec<_> = hits
            .iter()
            .map(|h| {
                let c = &idx.chunks[h.chunk as usize];
                let f = idx.chunk_file(h.chunk);
                let fact = h.fact.map(|fi| {
                    let x = &idx.facts[fi];
                    json!({"value": x.value, "unit": x.unit, "raw": x.raw, "label": x.label})
                });
                json!({
                    "path": f.path, "abs": cfg.root.join(&f.path), "line": h.line, "start": c.start, "end": c.end,
                    "title": f.title, "heading": c.heading, "score": h.score,
                    "text": if full { c.text.clone() } else { line_text(idx, h.chunk, h.line).trim().to_string() },
                    "fact": fact,
                })
            })
            .collect();
        writeln!(o, "{}", json!({"query": q, "mode": mode.name(), "ms": ms, "root": cfg.root, "results": arr})).unwrap();
        return Out { stdout: o, stderr: String::new() };
    }
    if hits.is_empty() {
        o.push_str("(brak wyników)\n");
    }
    for (i, h) in hits.iter().enumerate() {
        let c = &idx.chunks[h.chunk as usize];
        let f = idx.chunk_file(h.chunk);
        let span = if c.start == c.end { String::new() } else { format!("  [{}-{}]", c.start, c.end) };
        let head = c.heading.rsplit(" > ").next().unwrap_or("");
        writeln!(o, "{:>2}. {}:{}{}  — {}", i + 1, home_path(cfg, &f.path), h.line, span, if head.is_empty() { &f.title } else { head }).unwrap();
        if full {
            for l in c.text.lines() {
                writeln!(o, "      {l}").unwrap();
            }
        } else {
            writeln!(o, "      {}", snippet(line_text(idx, h.chunk, h.line), &qt, 220)).unwrap();
        }
    }
    Out { stdout: o, stderr: format!("kb: {} ms, tryb {}\n", ms.round(), mode.name()) }
}

pub fn facts(cfg: &Config, idx: &Index, q: &str, it: &Intent, fh: &[FactHit], json: bool, ms: f64) -> Out {
    let src = |fi: usize| {
        let f = &idx.facts[fi];
        format!("{}:{}", home_path(cfg, &idx.chunk_file(f.chunk).path), f.line)
    };
    let mut o = String::new();
    if json {
        let arr: Vec<_> = fh
            .iter()
            .map(|h| {
                let f = &idx.facts[h.fact];
                let c = &idx.chunks[f.chunk as usize];
                json!({
                    "value": f.value, "unit": f.unit, "raw": f.raw, "label": f.label,
                    "path": idx.chunk_file(f.chunk).path, "line": f.line, "heading": c.heading,
                    "text": line_text(idx, f.chunk, f.line).trim(), "rel": h.rel,
                    "also": h.also.iter().map(|&a| { let x = &idx.facts[a]; json!({"path": idx.chunk_file(x.chunk).path, "line": x.line}) }).collect::<Vec<_>>(),
                })
            })
            .collect();
        writeln!(o, "{}", json!({"query": q, "agg": it.agg.map(|a| format!("{a:?}")), "units": it.unit_filter(), "ms": ms, "root": cfg.root, "results": arr})).unwrap();
        return Out { stdout: o, stderr: String::new() };
    }
    if fh.is_empty() {
        o.push_str("(brak faktów — spróbuj `kb search`)\n");
    }
    let qt = analyze_query(q);
    for (i, h) in fh.iter().enumerate() {
        let f = &idx.facts[h.fact];
        let c = &idx.chunks[f.chunk as usize];
        let head = c.heading.rsplit(" > ").next().unwrap_or("");
        let unit = if f.raw.contains(&f.unit) { String::new() } else { format!(" {}", f.unit) };
        writeln!(o, "{:>2}. {}{}  {}  — {}", i + 1, f.raw, unit, src(h.fact), head).unwrap();
        writeln!(o, "      {}", snippet(line_text(idx, f.chunk, f.line), &qt, 200)).unwrap();
        if !h.also.is_empty() {
            writeln!(o, "      też: {}", h.also.iter().map(|&a| src(a)).collect::<Vec<_>>().join(", ")).unwrap();
        }
    }
    let agg = it.agg.map(|a| format!(", {a:?}")).unwrap_or_default();
    Out { stdout: o, stderr: format!("kb: {} ms, jednostki {:?}{}\n", ms.round(), it.unit_filter().unwrap_or_default(), agg) }
}
