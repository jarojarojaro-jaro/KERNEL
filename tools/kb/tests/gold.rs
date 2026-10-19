//! Test integracyjny: złoty zbiór pytań na prawdziwej bazie ~/KERNEL.
//! Wymaga modelu e5 (setup.sh); bez korpusu albo modelu test jest pomijany z komunikatem.
//! Pierwsze uruchomienie po dużych zmianach w wiki dolicza embeddingi (do kilku minut na CPU).

use std::path::PathBuf;
use std::process::Command;

fn home() -> PathBuf {
    PathBuf::from(std::env::var("HOME").expect("HOME"))
}

#[test]
fn gold_recall_at_5() {
    let root = std::env::var("KB_ROOT").map(PathBuf::from).unwrap_or_else(|_| home().join("KERNEL"));
    let model = std::env::var("KB_MODEL").map(PathBuf::from).unwrap_or_else(|_| home().join("models/kb/multilingual-e5-small"));
    let gold = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("gold/gold.jsonl");
    if !root.join("wiki").is_dir() || !model.join("tokenizer.json").exists() {
        eprintln!("pominięte: brak korpusu {} albo modelu {}", root.display(), model.display());
        return;
    }
    let out = Command::new(env!("CARGO_BIN_EXE_kb"))
        .args(["eval", "--modes", "hybrid-facts", "--min-recall", "0.9", "--misses", "--gold"])
        .arg(&gold)
        .env("KB_NO_DAEMON", "1")
        .output()
        .expect("uruchomienie kb eval");
    let stdout = String::from_utf8_lossy(&out.stdout);
    let stderr = String::from_utf8_lossy(&out.stderr);
    println!("{stdout}\n{stderr}");
    assert!(out.status.success(), "recall@5 hybrid-facts < 0.9:\n{stdout}\n{stderr}");
    let row = stdout.lines().find(|l| l.starts_with("| hybrid-facts")).expect("wiersz wyniku");
    let p95: f64 = row.trim_end_matches('|').rsplit('|').next().unwrap().trim().parse().unwrap();
    assert!(p95 < 200.0, "p95 zapytania {p95} ms ≥ 200 ms");
}

#[test]
fn search_json_has_sources() {
    let root = home().join("KERNEL");
    if !root.join("wiki").is_dir() {
        return;
    }
    let out = Command::new(env!("CARGO_BIN_EXE_kb"))
        .args(["search", "--mode", "bm25-facts", "--json", "-k", "3", "gdzie", "bylo", "130", "t/s"])
        .env("KB_NO_DAEMON", "1")
        .output()
        .unwrap();
    assert!(out.status.success());
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    let res = v["results"].as_array().unwrap();
    assert!(!res.is_empty());
    for r in res {
        assert!(r["path"].as_str().unwrap().ends_with(".md"));
        assert!(r["line"].as_u64().unwrap() >= 1);
    }
    assert!(res.iter().any(|r| r["text"].as_str().unwrap().contains("130")), "{v}");
}

/// Regresja (2026-10-19): rekord z wiersza tabeli, którego podmiot („Qwen … XTX”) jest tylko w nagłówku
/// sekcji, był odcinany filtrem trafności i `kb facts` pokazywał 396.9 zamiast 400.9 t/s.
#[test]
fn facts_record_from_table_section() {
    let root = home().join("KERNEL");
    if !root.join("wiki/REKORDY.md").exists() {
        return;
    }
    let out = Command::new(env!("CARGO_BIN_EXE_kb"))
        .args(["facts", "--json", "--max", "-k", "5", "najlepszy", "wynik", "qwen", "xtx"])
        .env("KB_NO_DAEMON", "1")
        .output()
        .unwrap();
    assert!(out.status.success());
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    let res = v["results"].as_array().unwrap();
    assert!(
        res.iter().any(|r| r["value"].as_f64() == Some(400.9) && r["path"] == "wiki/REKORDY.md"),
        "brak 400.9 t/s z REKORDY.md w top 5: {v}"
    );
}
