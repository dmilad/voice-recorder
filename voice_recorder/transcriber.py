"""Speech-to-text transcription using Whisper."""

import numpy as np
import os
import tempfile
import wave
from pathlib import Path
from typing import Optional, Callable
from faster_whisper import WhisperModel
from .config import config


class Transcriber:
    """Transcribes audio to text using Whisper."""

    def __init__(self):
        """Initialize transcriber (model loaded lazily)."""
        self.model: Optional[WhisperModel] = None
        self._model_loaded = False
        self._temp_files: list[Path] = []  # Track temp files for cleanup

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

    def transcribe_chunk_with_context(
        self,
        audio_data: np.ndarray,
        previous_text: str = "",
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Transcribe an audio chunk with context from previous transcriptions.

        Args:
            audio_data: Audio samples as numpy array (float32, mono, 16kHz)
            previous_text: Previous transcription text to use as context
            progress_callback: Optional callback for progress updates

        Returns:
            Transcribed text for this chunk
        """
        if not self._model_loaded:
            self._load_model()

        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        # Ensure audio is in the correct format
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        duration_seconds = len(audio_data) / config.sample_rate

        if progress_callback:
            progress_callback(f"Transcribing {duration_seconds:.1f}s chunk...")

        try:
            # Prepare transcription parameters
            transcribe_params = {
                "audio": audio_data,
                "language": "en",
                "beam_size": 5,
                "vad_filter": True,
                "vad_parameters": dict(
                    min_silence_duration_ms=500,  # Default for chunking
                ),
            }

            # Use previous text as initial prompt for context (last ~100 chars)
            if previous_text:
                # Take last sentence or last 100 chars as context
                context = previous_text[-100:].strip()
                if context:
                    transcribe_params["initial_prompt"] = context

            # Transcribe
            segments, info = self.model.transcribe(**transcribe_params)

            # Collect all text segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            transcribed_text = " ".join(text_parts).strip()

            if progress_callback:
                if transcribed_text:
                    progress_callback(f"Chunk transcribed: {len(transcribed_text)} chars")
                else:
                    progress_callback("No speech in chunk")

            return transcribed_text

        except Exception as e:
            error_msg = f"Error transcribing chunk: {e}"
            if progress_callback:
                progress_callback(error_msg)
            print(error_msg)
            raise

    def _write_chunk_to_temp_file(self, audio_data: np.ndarray, chunk_index: int) -> Path:
        """
        Write audio chunk to a temporary WAV file.

        Args:
            audio_data: Audio samples as numpy array (float32, mono, 16kHz)
            chunk_index: Index of the chunk for file naming

        Returns:
            Path to the temporary file
        """
        # Ensure temp directory exists
        config.temp_audio_dir.mkdir(parents=True, exist_ok=True)

        # Create temp file with unique name
        temp_file = config.temp_audio_dir / f"chunk_{chunk_index}_{os.getpid()}.wav"

        # Convert float32 to int16 for WAV format
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Write WAV file
        with wave.open(str(temp_file), "wb") as wav_file:
            wav_file.setnchannels(config.channels)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(config.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        # Track for cleanup
        self._temp_files.append(temp_file)

        return temp_file

    def cleanup_temp_files(self) -> None:
        """Remove all temporary audio files created during chunked transcription."""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete temp file {temp_file}: {e}")

        self._temp_files.clear()

        # Try to remove temp directory if empty
        try:
            if config.temp_audio_dir.exists() and not any(config.temp_audio_dir.iterdir()):
                config.temp_audio_dir.rmdir()
        except Exception:
            pass  # Directory not empty or other issue, ignore
