import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import io
import re
import sys
import traceback

from dotenv import load_dotenv
load_dotenv()  # Must run before the brain and Transcriber read their settings

import pygame
import speech_recognition as sr
from gtts import gTTS

import system_controls
from ai_brain import create_brain
from transcriber import Transcriber
from wake_word import WakeWordDetector

WAKE_WORD = "alfred"
SLEEP_COMMANDS = {"sleep", "go to sleep", "stop listening"}
EXIT_COMMANDS = {"exit program", "shut down", "shutdown", "quit"}
YES_WORDS = {"yes", "yeah", "yep", "sure", "confirm", "ok", "okay"}
NO_WORDS = {"no", "nope", "not", "dont", "cancel", "stop", "never"}
YES_PHRASES = ("go ahead", "do it")
MAX_IDLE_TURNS = 3  # Go back to sleep after this many silent listens in a row

recognizer = sr.Recognizer()
recognizer.pause_threshold = 1.3         # Seconds of silence that end a command
recognizer.non_speaking_duration = 0.5   # Audio kept from just before speech starts
recognizer.phrase_threshold = 0.3        # Ignore clicks and bumps shorter than this
recognizer.dynamic_energy_threshold = True


def speak(text):
    """Speaks text aloud using gTTS, played from memory (no temp files)."""
    if not text:
        return
    print(f"[Alfred]: {text}")
    try:
        audio = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(audio)
        audio.seek(0)
        pygame.mixer.music.load(audio, "mp3")
        pygame.mixer.music.play()
        clock = pygame.time.Clock()
        while pygame.mixer.music.get_busy():
            clock.tick(10)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"[Audio error]: {e}")


def record(timeout=6, phrase_limit=15):
    """Records one phrase from the microphone. Raises sr.WaitTimeoutError on silence."""
    with sr.Microphone(sample_rate=16000) as source:
        return recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)


def normalize(text):
    """Lowercases, strips punctuation and removes the wake word."""
    text = re.sub(r"[^\w\s]", "", text.lower()).replace(WAKE_WORD, "")
    return " ".join(text.split())


def is_yes(answer):
    """True only for a clear yes. Any negative word ('not sure', 'don't') means no."""
    text = normalize(answer)
    words = set(text.split())
    if words & NO_WORDS:
        return False
    return bool(words & YES_WORDS) or any(phrase in text for phrase in YES_PHRASES)


def confirm(question, detector, transcriber):
    """Asks a yes/no question out loud. Tries offline Vosk first, then Whisper as a fallback."""
    speak(question)
    print("[Confirm] Say yes or no...")
    try:
        answer = detector.listen_for_answer()
    except Exception:
        print("[Confirm error] Offline listening failed:")
        traceback.print_exc()
        try:
            answer = transcriber.transcribe(record(timeout=5, phrase_limit=4)).text
        except Exception as e:
            print(f"[Confirm error] Fallback listening also failed: {type(e).__name__} {e}")
            answer = ""
    print(f"[You]: {answer or '(nothing heard)'}")
    return is_yes(answer)


def active_session(brain, transcriber):
    """Handles commands until the user says sleep or stays silent for a while."""
    idle_turns = 0
    while idle_turns < MAX_IDLE_TURNS:
        print("\n[Active] Listening for a command...")
        try:
            audio = record()
        except sr.WaitTimeoutError:
            idle_turns += 1
            continue

        print("[Active] Transcribing...")
        result = transcriber.transcribe(audio)

        if result.status == "silence":
            idle_turns += 1
            continue

        idle_turns = 0
        if result.status == "unclear":
            print(f"[You]: {result.text}  (unclear, ignored)")
            speak("Sorry, I didn't catch that. Could you say it again?")
            continue

        print(f"[You]: {result.text}")
        command = normalize(result.text)

        if not command:
            speak("Yes?")
            continue
        if command in SLEEP_COMMANDS:
            speak("Going to sleep.")
            return
        if command in EXIT_COMMANDS:
            speak("Shutting down. Goodbye.")
            pygame.mixer.quit()
            sys.exit(0)

        speak(brain.process_input(command))

    print("[Active] No speech for a while. Going back to sleep.")


def main():
    pygame.mixer.init()
    brain = create_brain()
    print(f"[System] AI brain: {brain.label}")
    transcriber = Transcriber()
    detector = WakeWordDetector(WAKE_WORD)
    system_controls.confirm_callback = lambda question: confirm(question, detector, transcriber)

    with sr.Microphone(sample_rate=16000) as source:
        print("[System] Calibrating microphone for room noise, please stay quiet...")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)

    speak("Alfred is online. Say Alfred when you need me.")

    while True:
        print("\n[Passive] Waiting for the wake word...")
        detector.wait()
        speak("Yes?")
        active_session(brain, transcriber)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[System] Stopped by user.")