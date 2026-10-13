import json

import pyaudio
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)  # Hide Vosk's internal logs

RATE = 16000
CHUNK = 4000  # 0.25 seconds of audio per read

# Words and phrases Vosk listens for when Alfred asks a yes/no question
ANSWER_PHRASES = [
    "yes", "yeah", "yep", "sure", "okay", "confirm", "go ahead", "do it",
    "no", "nope", "cancel", "stop", "not sure", "don't", "never",
]


class WakeWordDetector:
    """Offline listening with a small Vosk model: the wake word and yes/no answers."""

    def __init__(self, wake_word="alfred"):
        self.wake_word = wake_word.lower()
        # Downloads the small English model (~40 MB) on first run, then caches it
        self.model = Model(lang="en-us")
        self.audio = pyaudio.PyAudio()

    def _open_stream(self):
        return self.audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, frames_per_buffer=CHUNK,
        )

    def wait(self):
        """Blocks until the wake word is heard."""
        recognizer = KaldiRecognizer(self.model, RATE, json.dumps([self.wake_word, "[unk]"]))
        stream = self._open_stream()
        try:
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    text = json.loads(recognizer.Result()).get("text", "")
                else:
                    text = json.loads(recognizer.PartialResult()).get("partial", "")
                if self.wake_word in text.split():
                    return
        finally:
            # Release the mic so speech_recognition can use it next
            stream.stop_stream()
            stream.close()

    def listen_for_answer(self, timeout=6.0):
        """Listens for a yes/no style answer. Returns the text, or '' if nothing was heard."""
        recognizer = KaldiRecognizer(self.model, RATE, json.dumps(ANSWER_PHRASES + ["[unk]"]))
        stream = self._open_stream()
        try:
            for _ in range(int(timeout * RATE / CHUNK)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    text = json.loads(recognizer.Result()).get("text", "").replace("[unk]", "").strip()
                    if text:
                        return text
            return json.loads(recognizer.FinalResult()).get("text", "").replace("[unk]", "").strip()
        finally:
            stream.stop_stream()
            stream.close()