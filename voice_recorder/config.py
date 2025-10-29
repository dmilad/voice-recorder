"""Configuration management for voice recorder."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # Whisper settings
    whisper_model: str = os.getenv("WHISPER_MODEL", "base.en")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")

    # Audio settings
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    channels: int = int(os.getenv("CHANNELS", "1"))

    # Recording settings
    max_recording_duration: int = int(os.getenv("MAX_RECORDING_DURATION", "3600"))  # 1 hour (increased from 5 minutes)
    min_recording_duration: float = float(os.getenv("MIN_RECORDING_DURATION", "0.5"))

    # Chunked transcription settings
    enable_chunked_transcription: bool = os.getenv("ENABLE_CHUNKED_TRANSCRIPTION", "true").lower() == "true"
    chunk_duration_seconds: int = int(os.getenv("CHUNK_DURATION_SECONDS", "5"))  # Process in 5-second chunks
    chunk_overlap_seconds: int = int(os.getenv("CHUNK_OVERLAP_SECONDS", "3"))  # 3-second overlap for context
    temp_audio_dir: Path = Path(os.getenv("TEMP_AUDIO_DIR", tempfile.gettempdir())) / "voice_recorder_chunks"

    # Silence detection
    enable_silence_detection: bool = os.getenv("ENABLE_SILENCE_DETECTION", "true").lower() == "true"
    energy_threshold: float = float(os.getenv("ENERGY_THRESHOLD", "0.01"))

    # Clipboard settings
    restore_clipboard: bool = os.getenv("RESTORE_CLIPBOARD", "true").lower() == "true"
    paste_delay_ms: int = int(os.getenv("PASTE_DELAY_MS", "100"))

    # Hotkey
    hotkey: str = os.getenv("HOTKEY", "<cmd>+<alt>+<space>")

    def __post_init__(self):
        """Validate configuration."""
        if self.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            raise ValueError(f"Invalid sample rate: {self.sample_rate}")

        if self.channels not in [1, 2]:
            raise ValueError(f"Invalid number of channels: {self.channels}")

        if self.max_recording_duration <= 0:
            raise ValueError("Max recording duration must be positive")

        if self.min_recording_duration <= 0:
            raise ValueError("Min recording duration must be positive")

        if self.chunk_duration_seconds <= 0:
            raise ValueError("Chunk duration must be positive")

        if self.chunk_overlap_seconds < 0:
            raise ValueError("Chunk overlap must be non-negative")

        if self.chunk_overlap_seconds >= self.chunk_duration_seconds:
            raise ValueError("Chunk overlap must be less than chunk duration")

        # Create temp directory if it doesn't exist
        self.temp_audio_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()
