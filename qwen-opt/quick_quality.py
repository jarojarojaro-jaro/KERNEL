#!/usr/bin/env python3
"""Quick sanity/quality check: short questions with checkable answers, greedy, thinking off.

usage: quick_quality.py PORT LABEL
"""
import json
import re
import sys
import urllib.request

QUESTIONS = [
    ("Ile to 17*23? Podaj tylko wynik.", r"\b391\b"),
    ("What is the capital of Australia? Answer with one word.", r"canberra"),
    ("Is 221 a prime number? Answer yes or no, then give the factorization if not.", r"13.{0,12}17|17.{0,12}13"),
    ("Rozwiąż równanie 2x + 6 = 20. Podaj x.", r"x\s*=\s*7\b|\b7\b"),
    ("Popraw błąd w zdaniu: 'Wczoraj poszłem do sklepu.' Podaj poprawne zdanie.", r"poszedłem"),
    ("What is the sum of the squares of the integers from 1 to 10? Give just the number.", r"\b385\b"),
    ("Jaka jest stolica Słowacji? Jedno słowo.", r"bratysław"),
    ("A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much is the ball? Answer in cents.", r"\b5\b|0\.05|five"),
    ("Ile dni ma rok przestępny? Podaj liczbę.", r"\b366\b"),
    ("Translate to English: 'Dziękuję za pomoc, to było bardzo miłe.'", r"thank"),
]


def ask(port: int, q: str) -> str:
    body = {"messages": [{"role": "user", "content": q}], "max_tokens": 200, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def main() -> None:
    port, label = int(sys.argv[1]), sys.argv[2]
    ok = 0
    for q, pat in QUESTIONS:
        a = ask(port, q)
        hit = re.search(pat, a, re.IGNORECASE) is not None
        ok += hit
        print(f"[{'OK' if hit else '--'}] {q[:50]:50} -> {a.strip()[:90]!r}")
    print(f"{label}: {ok}/{len(QUESTIONS)}")


if __name__ == "__main__":
    main()
