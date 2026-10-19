//! Ocena na zbiorze złotych pytań: recall@k, MRR, opóźnienie (w procesie, rozgrzane).
//! Oczekiwane miejsca są zapisane jako `needle` (dosłowny fragment linii), bo numery linii dryfują.

use crate::index::{Config, Index};
use crate::search::{facts_query, Mode, Searcher};
use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::Path;
use std::time::Instant;

#[derive(Deserialize, Clone)]
pub struct Expect {
    pub file: String,
    pub needle: String,
}

#[derive(Deserialize, Clone)]
pub struct Gold {
    pub id: String,
    pub q: String,
    pub kind: String,
    pub expect: Vec<Expect>,
    #[serde(default)]
    pub answer: String,
}

pub fn load_gold(path: &Path) -> Result<Vec<Gold>> {
    let text = std::fs::read_to_string(path).with_context(|| format!("czytanie {}", path.display()))?;
    text.lines().filter(|l| !l.trim().is_empty()).map(|l| serde_json::from_str(l).with_context(|| format!("zły wiersz: {l}"))).collect()
}

/// (plik, linie 1-based) dla każdego oczekiwanego miejsca.
pub fn resolve(root: &Path, g: &Gold) -> Vec<(String, Vec<u32>)> {
    g.expect
        .iter()
        .map(|e| {
            let text = std::fs::read_to_string(root.join(&e.file)).unwrap_or_default();
            let lines = text.lines().enumerate().filter(|(_, l)| l.contains(&e.needle)).map(|(i, _)| i as u32 + 1).collect();
            (e.file.clone(), lines)
        })
        .collect()
}

pub struct ModeResult {
    pub mode: String,
    pub ranks: Vec<Option<usize>>,
    /// trafienie na poziomie pliku (diagnostyka: dobry dokument, zła linia)
    pub file_ranks: Vec<Option<usize>>,
    pub top: Vec<Vec<(String, u32, u32)>>,
    pub lat_ms: Vec<f64>,
}

impl ModeResult {
    pub fn recall(&self, sel: &[usize], k: usize) -> f64 {
        if sel.is_empty() {
            return 0.0;
        }
        sel.iter().filter(|&&i| self.ranks[i].is_some_and(|r| r < k)).count() as f64 / sel.len() as f64
    }
    pub fn file_recall(&self, sel: &[usize], k: usize) -> f64 {
        sel.iter().filter(|&&i| self.file_ranks[i].is_some_and(|r| r < k)).count() as f64 / sel.len().max(1) as f64
    }
    pub fn mrr(&self, sel: &[usize], k: usize) -> f64 {
        sel.iter().map(|&i| self.ranks[i].filter(|&r| r < k).map_or(0.0, |r| 1.0 / (r as f64 + 1.0))).sum::<f64>() / sel.len().max(1) as f64
    }
    pub fn pct(&self, p: f64) -> f64 {
        let mut v = self.lat_ms.clone();
        v.sort_by(|a, b| a.total_cmp(b));
        if v.is_empty() {
            return 0.0;
        }
        v[((v.len() - 1) as f64 * p).round() as usize]
    }
}

/// Wyniki jako (plik, start, end) → pozycja pierwszego trafienia.
fn first_hit(results: &[(String, u32, u32)], exp: &[(String, Vec<u32>)]) -> Option<usize> {
    results.iter().position(|(f, s, e)| exp.iter().any(|(ef, lines)| ef == f && lines.iter().any(|l| l >= s && l <= e)))
}

pub fn run_mode(cfg: &Config, idx: &Index, s: &mut Searcher, gold: &[Gold], exp: &[Vec<(String, Vec<u32>)>], mode: &str, k: usize) -> Result<ModeResult> {
    let mut ranks = Vec::new();
    let mut lat = Vec::new();
    let mut top = Vec::new();
    let mut file_ranks = Vec::new();
    for (g, e) in gold.iter().zip(exp) {
        let (res, ms) = match mode {
            "wiki.py" => wikipy(cfg, &g.q)?,
            "facts" => {
                let t = Instant::now();
                let (_, fh) = facts_query(idx, &g.q, None, None, k);
                let ms = t.elapsed().as_secs_f64() * 1e3;
                let r = fh
                    .iter()
                    .map(|h| {
                        let f = &idx.facts[h.fact];
                        (idx.chunk_file(f.chunk).path.clone(), f.line, f.line)
                    })
                    .collect();
                (r, ms)
            }
            m => {
                let m: Mode = clap::ValueEnum::from_str(m, true).map_err(|e| anyhow::anyhow!(e))?;
                // pierwsze wywołanie rozgrzewa (pamięć podręczna, alokator), mierzymy drugie
                s.search(&g.q, m, k)?;
                let t = Instant::now();
                let hits = s.search(&g.q, m, k)?;
                let ms = t.elapsed().as_secs_f64() * 1e3;
                let r = hits
                    .iter()
                    .map(|h| {
                        let c = &idx.chunks[h.chunk as usize];
                        (idx.files[c.file as usize].path.clone(), c.start, c.end)
                    })
                    .collect();
                (r, ms)
            }
        };
        ranks.push(first_hit(&res, e));
        file_ranks.push(res.iter().position(|(f, _, _)| e.iter().any(|(ef, _)| ef == f)));
        top.push(res);
        lat.push(ms);
    }
    Ok(ModeResult { mode: mode.to_string(), ranks, file_ranks, top, lat_ms: lat })
}

/// Dotychczasowe `wiki.py search`: wynik na poziomie notatki, więc trafienie = zgodny plik (łagodniej).
fn wikipy(cfg: &Config, q: &str) -> Result<(Vec<(String, u32, u32)>, f64)> {
    let script = cfg.root.join("wiki/tools/wiki.py");
    let t = Instant::now();
    let out = std::process::Command::new("python3").arg(&script).arg("search").args(q.split_whitespace()).env("KB_NO_DELEGATE", "1").output()?;
    let ms = t.elapsed().as_secs_f64() * 1e3;
    let text = String::from_utf8_lossy(&out.stdout);
    let res = text
        .lines()
        .filter_map(|l| l.split_whitespace().nth(1))
        .filter(|p| p.ends_with(".md"))
        .map(|p| (format!("wiki/{p}"), 0, u32::MAX))
        .collect();
    Ok((res, ms))
}

pub fn report(results: &[ModeResult], gold: &[Gold], k: usize) -> String {
    let all: Vec<usize> = (0..gold.len()).collect();
    let dev: Vec<usize> = all.iter().copied().filter(|&i| id_num(&gold[i].id) <= 40).collect();
    let held: Vec<usize> = all.iter().copied().filter(|&i| id_num(&gold[i].id) > 40).collect();
    let facts: Vec<usize> = all.iter().copied().filter(|&i| gold[i].kind == "fact").collect();
    let mut s = format!(
        "| tryb | recall@{k} wszystkie ({}) | dev g01–g40 | held-out g41+ | fakty ({}) | MRR@{k} | plik@{k} | p50 ms | p95 ms |\n|---|---|---|---|---|---|---|---|---|\n",
        all.len(),
        facts.len()
    );
    for r in results {
        s += &format!(
            "| {} | **{:.3}** | {:.3} | {:.3} | {:.3} | {:.3} | {:.3} | {:.1} | {:.1} |\n",
            r.mode,
            r.recall(&all, k),
            r.recall(&dev, k),
            r.recall(&held, k),
            r.recall(&facts, k),
            r.mrr(&all, k),
            r.file_recall(&all, k),
            r.pct(0.5),
            r.pct(0.95),
        );
    }
    s
}

pub fn id_num(id: &str) -> u32 {
    id.trim_start_matches(|c: char| !c.is_ascii_digit()).parse().unwrap_or(0)
}
