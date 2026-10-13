"""Records your voice for every clip listed in speech_cases.csv.

Run from the project folder:
    python evaluation/record_clips.py          (records clips that don't exist yet)
    python evaluation/record_clips.py --redo   (records every clip again)
"""
import csv
import sys
from pathlib import Path

import speech_recognition as sr

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "speech_cases.csv"
AUDIO_DIR = HERE / "audio"


def main():
    redo = "--redo" in sys.argv
    AUDIO_DIR.mkdir(exist_ok=True)
    with open(CASES_FILE, encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.3
    with sr.Microphone(sample_rate=16000) as source:
        print("Calibrating microphone, please stay quiet...")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)

    for number, case in enumerate(cases, 1):
        path = AUDIO_DIR / case["file"]
        if path.exists() and not redo:
            print(f"[{number}/{len(cases)}] {case['file']} already recorded, skipping")
            continue

        print(f"\n[{number}/{len(cases)}] Say: \"{case['text']}\"")
        if case["condition"] == "noisy":
            print("  NOISY clip: play music or turn on a fan before speaking")

        while True:
            input("  Press Enter, then speak...")
            try:
                with sr.Microphone(sample_rate=16000) as source:
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
                break
            except sr.WaitTimeoutError:
                print("  Nothing heard, let's try again.")

        path.write_bytes(audio.get_wav_data())
        print(f"  Saved {path.name}")

    print("\nAll clips recorded. Now run: python evaluation/eval_speech.py")


if __name__ == "__main__":
    main()