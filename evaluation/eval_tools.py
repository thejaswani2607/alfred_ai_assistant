"""Measures how often the AI brain picks the right tool. No tool is actually run.

Run from the project folder:
    python evaluation/eval_tools.py
It tests whichever brain BRAIN in .env selects ('gemini' or 'local').
"""
import csv
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # So the brain reads the same memory.json as Alfred

from dotenv import load_dotenv
load_dotenv()

from ai_brain import create_brain

CASES_FILE = HERE / "tool_cases.csv"
RESULTS_DIR = HERE / "results"


def main():
    brain = create_brain()
    # Pause between requests so Gemini's per-minute free limit isn't hit
    default_delay = "4" if os.getenv("BRAIN", "gemini").lower() == "gemini" else "0"
    delay = float(os.getenv("EVAL_DELAY", default_delay))

    with open(CASES_FILE, encoding="utf-8") as f:
        cases = list(csv.DictReader(f))
    print(f"Testing {len(cases)} commands with {brain.label}\n")

    rows = []
    for number, case in enumerate(cases, 1):
        expected = {name.strip() for name in case["expected_tool"].split("|")}
        start = time.perf_counter()
        try:
            tool, args = brain.choose_tool(case["command"])
            chosen = tool or "none"
        except Exception as e:
            chosen, args = "ERROR", {}
            print(f"  Error: {e}")
        seconds = time.perf_counter() - start

        passed = chosen in expected
        mark = "PASS" if passed else "FAIL"
        args_text = f" {args}" if args else ""
        print(f"[{number:2}/{len(cases)}] {mark} {case['command']!r} -> {chosen}{args_text} (expected {case['expected_tool']}, {seconds:.2f}s)")
        rows.append(dict(case, chosen=chosen, args=args, passed=passed, seconds=round(seconds, 3)))

        if delay and number < len(cases):
            time.sleep(delay)

    RESULTS_DIR.mkdir(exist_ok=True)
    safe_label = "".join(c if c.isalnum() else "_" for c in brain.label).strip("_")
    out_file = RESULTS_DIR / f"tools_{safe_label}.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    by_category = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row["passed"])

    print("\nAccuracy by category:")
    for category, results in by_category.items():
        print(f"  {category:8} {sum(results)}/{len(results)}")

    answered = [r for r in rows if r["chosen"] != "ERROR"]
    errors = len(rows) - len(answered)
    correct = sum(r["passed"] for r in rows)
    avg_time = sum(r["seconds"] for r in answered) / len(answered) if answered else 0.0

    print(f"\nSaved detailed results to {out_file}")
    if errors:
        print(f"Warning: {errors} request(s) failed (for example a quota limit) and count as wrong.")
    print("\nResults row (paste into README):\n")
    print("| Brain | Correct tool | Avg time per decision |")
    print("|---|---|---|")
    print(f"| {brain.label} | {correct}/{len(rows)} ({100 * correct / len(rows):.0f}%) | {avg_time:.2f} s |")


if __name__ == "__main__":
    main()