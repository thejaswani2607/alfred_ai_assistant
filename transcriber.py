import os
import warnings

# Hide harmless Hugging Face cache warnings (must be set before importing faster_whisper)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
warnings.filterwarnings("ignore", module="huggingface_hub")

from dataclasses import dataclass

import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
DEBUG = os.getenv("WHISPER_DEBUG", "0") == "1"

# Words Alfred expects to hear often; only used when real speech is detected
HOTWORDS = "Alfred, PC, lock, mute, volume, YouTube, screenshot, clipboard, news, note, remember"

# Phrases Whisper sometimes "hears" in silence or background noise
HALLUCINATIONS = {
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "you", "bye", "subscribe", "please subscribe", "all",
}


@dataclass
class Transcription:
    text: str
    status: str  # "clear", "unclear" or "silence"


SILENCE = Transcription("", "silence")


class Transcriber:
    """Converts recorded speech to text locally with faster-whisper."""

    def __init__(self, model_name=None):
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "small.en")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        compute_type = "int8" if device == "cpu" else "float16"
        options = dict(device=device, compute_type=compute_type)

        print(f"[System] Loading Whisper model '{self.model_name}'...")
        try:
            # Use the cached copy without contacting Hugging Face
            self.model = WhisperModel(self.model_name, local_files_only=True, **options)
        except Exception:
            print(f"[System] Downloading Whisper model '{self.model_name}' (one-time download)...")
            self.model = WhisperModel(self.model_name, **options)

    def _run(self, samples, use_vad):
        segments, _ = self.model.transcribe(
            samples,
            language="en",
            beam_size=5,
            vad_filter=use_vad,
            condition_on_previous_text=False,
            # Hotwords only when the noise filter has confirmed real speech
            hotwords=HOTWORDS if use_vad else None,
        )
        return list(segments)

    def transcribe(self, audio):
        """Takes a speech_recognition AudioData and returns a Transcription."""
        raw = audio.get_raw_data(convert_rate=SAMPLE_RATE, convert_width=2)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        segments = self._run(samples, use_vad=True)
        speech_detected = bool(segments)

        # The noise filter can cut very short words like "mute"; retry short clips without it
        if not speech_detected:
            if len(samples) >= SAMPLE_RATE * 2:
                return SILENCE
            segments = self._run(samples, use_vad=False)

        text = " ".join(s.text.strip() for s in segments).strip()
        if not segments or not any(c.isalpha() for c in text):
            return SILENCE

        avg_logprob = sum(s.avg_logprob for s in segments) / len(segments)
        no_speech = max(s.no_speech_prob for s in segments)
        compression = max(s.compression_ratio for s in segments)

        if DEBUG:
            print(
                f"[Whisper debug] text={text!r} speech_detected={speech_detected} "
                f"avg_logprob={avg_logprob:.2f} no_speech={no_speech:.2f} compression={compression:.2f}"
            )

        # No speech found by the filter: only trust a short, very confident result
        if not speech_detected:
            if len(text.split()) > 3 or avg_logprob < -0.5 or no_speech > 0.4:
                return SILENCE

        # Known phrases Whisper invents from noise
        if text.lower().strip(" .!?,") in HALLUCINATIONS:
            return SILENCE

        # Whisper's own rule for "this was not speech"
        if no_speech > 0.6 and avg_logprob < -1.0:
            return SILENCE

        # Low confidence: only ask to repeat if it was probably real speech
        if avg_logprob < -1.0 or compression > 2.4:
            return Transcription(text, "unclear") if no_speech < 0.5 else SILENCE

        return Transcription(text, "clear")