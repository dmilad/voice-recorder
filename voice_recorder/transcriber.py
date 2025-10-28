"""Speech-to-text transcription using Whisper."""

import numpy as np
from typing import Optional
from faster_whisper import WhisperModel
from .config import config


class Transcriber:
    """Transcribes audio to text using Whisper."""

    def __init__(self):
        """Initialize transcriber (model loaded lazily)."""
        self.model: Optional[WhisperModel] = None
        self._model_loaded = False

    def _load_model(self) -> None:
        """Load the Whisper model."""
        if self._model_loaded:
            return

        print(f"Loading Whisper model: {config.whisper_model}...")
        try:
            self.model = WhisperModel(
                config.whisper_model,
                device=config.whisper_device,
                compute_type="int8" if config.whisper_device == "cpu" else "float16",
            )
            self._model_loaded = True
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            raise

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Audio samples as numpy array (float32, mono, 16kHz)

        Returns:
            Transcribed text
        """
        if not self._model_loaded:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        # Ensure audio is in the correct format
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        print(f"Transcribing {len(audio_data) / config.sample_rate:.2f}s of audio...")

        try:
            # Transcribe
            segments, info = self.model.transcribe(
                audio_data,
                language="en",
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                ),
            )

            # Collect all text segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            transcribed_text = " ".join(text_parts).strip()

            if transcribed_text:
                print(f"Transcription complete: {len(transcribed_text)} characters")
            else:
                print("No speech detected in audio")

            return transcribed_text

        except Exception as e:
            print(f"Error during transcription: {e}")
            raise

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model_loaded
