"""Measures Whisper's accuracy and speed on your recorded clips.

Run from the project folder:
    python evaluation/eval_speech.py                 (compares base.en and small.en)
    python evaluation/eval_speech.py small.en        (tests one model)
"""
import csv
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import speech_recognition as sr

from transcriber import Transcriber

CASES_FILE = HERE / "speech_cases.csv"
AUDIO_DIR = HERE / "audio"
RESULTS_DIR = HERE / "results"


def words(text):
    """Lowercase words without punctuation, so 'Lock my PC.' matches 'lock my pc'."""
    text = re.sub(r"[^\w\s]", "", text.lower().replace("-", " "))
    return text.split()


def word_errors(reference, heard):
    """Word-level edit distance: substitutions + deletions + insertions."""
    previous = list(range(len(heard) + 1))
    for i, ref_word in enumerate(reference, 1):
        current = [i] + [0] * len(heard)
        for j, heard_word in enumerate(heard, 1):
            current[j] = min(
                previous[j] + 1,                               # word missing
                current[j - 1] + 1,                            # extra word
                previous[j - 1] + (ref_word != heard_word),    # wrong word
            )
        previous = current
    return previous[-1]


def load_audio(path):
    with sr.AudioFile(str(path)) as source:
        return sr.Recognizer().record(source)


def evaluate(model_name, cases):
    transcriber = Transcriber(model_name)
    transcriber.transcribe(load_audio(AUDIO_DIR / cases[0]["file"]))  # Warm-up, not timed

    print(f"\n=== Whisper {model_name} ===")
    rows = []
    for case in cases:
        audio = load_audio(AUDIO_DIR / case["file"])
        start = time.perf_counter()
        result = transcriber.transcribe(audio)
        seconds = time.perf_counter() - start

        reference = words(case["text"])
        heard = words(result.text)
        errors = word_errors(reference, heard)
        mark = "OK  " if errors == 0 else "MISS"
        print(f"{mark} {case['file']} [{case['condition']}] said: {case['text']!r} | heard: {result.text!r} ({seconds:.2f}s)")
        rows.append(dict(case, heard=result.text, status=result.status,
                         errors=errors, ref_words=len(reference), seconds=round(seconds, 3)))

    RESULTS_DIR.mkdir(exist_ok=True)
    out_file = RESULTS_DIR / f"speech_{model_name.replace('.', '_')}.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    def wer(subset):
        total = sum(r["ref_words"] for r in subset)
        return 100 * sum(r["errors"] for r in subset) / total if total else 0.0

    quiet = [r for r in rows if r["condition"] == "quiet"]
    noisy = [r for r in rows if r["condition"] == "noisy"]
    exact = sum(r["errors"] == 0 for r in rows)
    avg_time = sum(r["seconds"] for r in rows) / len(rows)
    print(f"Saved detailed results to {out_file}")
    return f"| {model_name} | {wer(rows):.1f}% | {wer(quiet):.1f}% | {wer(noisy):.1f}% | {exact}/{len(rows)} | {avg_time:.2f} s |"


def main():
    with open(CASES_FILE, encoding="utf-8") as f:
        all_cases = list(csv.DictReader(f))
    cases = [c for c in all_cases if (AUDIO_DIR / c["file"]).exists()]
    if not cases:
        print("No recordings found. Run first: python evaluation/record_clips.py")
        return
    if len(cases) < len(all_cases):
        print(f"Note: only {len(cases)} of {len(all_cases)} clips are recorded; testing those.")

    models = sys.argv[1:] or ["base.en", "small.en"]
    summary = [evaluate(model, cases) for model in models]

    print("\nResults table (paste into README):\n")
    print("| Whisper model | Word error rate | Quiet | Noisy | Exactly right | Avg time per clip |")
    print("|---|---|---|---|---|---|")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()