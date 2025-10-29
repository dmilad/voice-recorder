# Voice Recorder

A local voice-to-text application for macOS with global hotkey support. Record your voice from any application and automatically paste the transcribed text.

## Features

- 🎤 **Global Hotkey**: Press `Cmd+Shift+Space` from any application to start/stop recording
- 🔒 **Fully Local**: All processing happens on your Mac (no cloud, no internet required)
- ⚡ **Fast**: Uses faster-whisper for optimized transcription
- 📋 **Auto-Paste**: Automatically pastes transcribed text to the active text field
- 🔇 **Smart Detection**: Filters out silent recordings automatically
- 🇬🇧 **English Only**: Optimized for English language transcription

## Requirements

- macOS 11+ (tested on macOS Sequoia 15.6.1)
- Python 3.11+
- Microphone
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd voice-recorder
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **(Optional) Configure settings**:
   ```bash
   cp .env.example .env
   # Edit .env to customize settings
   ```

## macOS Permissions

This app requires several permissions to function:

### 1. Microphone Access
- Automatically prompted on first run
- Or manually: **System Settings → Privacy & Security → Microphone**
- Add Terminal or your Python executable

### 2. Accessibility Access (Required!)
- **System Settings → Privacy & Security → Accessibility**
- Click the `+` button and add:
  - Terminal (if running from terminal)
  - Or your Python executable (`.venv/bin/python3`)

### 3. Input Monitoring
- May be automatically prompted
- Or manually: **System Settings → Privacy & Security → Input Monitoring**
- Add Terminal or your Python executable

**Note**: After granting permissions, you may need to restart Terminal or the app.

## Usage

1. **Start the application**:
   ```bash
   uv run python main.py
   ```

2. **Record and transcribe**:
   - Press `Cmd+Shift+Space` to **start** recording
   - Speak into your microphone
   - Press `Cmd+Shift+Space` again to **stop** recording
   - Wait for transcription to complete
   - Text will automatically paste to your active text field!

3. **Stop the application**:
   - Press `Ctrl+C` in the terminal

## Configuration

Edit `.env` to customize settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `WHISPER_MODEL` | `base.en` | Model size (tiny.en, base.en, small.en, medium.en, large) |
| `HOTKEY` | `<cmd>+<alt>+<space>` | Global hotkey combination |
| `MAX_RECORDING_DURATION` | `300` | Maximum recording length (seconds) |
| `MIN_RECORDING_DURATION` | `0.5` | Minimum recording length (seconds) |
| `ENABLE_SILENCE_DETECTION` | `true` | Filter out silent recordings |
| `RESTORE_CLIPBOARD` | `true` | Restore original clipboard after pasting |

### Model Sizes

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny.en` | 39M | ~10x realtime | Good |
| `base.en` | 74M | ~7x realtime | **Recommended** |
| `small.en` | 244M | ~4x realtime | Better |
| `medium.en` | 769M | ~2x realtime | Best |
| `large` | 1550M | ~1x realtime | Overkill for English |

## How It Works

1. **Global Hotkey**: `pynput` listens for `Cmd+Shift+Space` system-wide
2. **Audio Recording**: `sounddevice` captures audio from your microphone at 16kHz
3. **Speech-to-Text**: `faster-whisper` transcribes audio locally (no internet)
4. **Text Injection**: Text is copied to clipboard and pasted via `Cmd+V` simulation

## Troubleshooting

### Hotkey doesn't work
- Ensure you've granted **Accessibility** and **Input Monitoring** permissions
- Restart Terminal after granting permissions
- Check if another app is using the same hotkey

### Microphone not working
- Grant **Microphone** permission in System Settings
- Check if the correct input device is selected (run with `-v` for device list)
- Test microphone in another app (e.g., Voice Memos)

### Transcription is slow
- Try a smaller model: `WHISPER_MODEL=tiny.en`
- Ensure you're using the `.en` models for English-only

### Text doesn't paste
- Make sure the target application has focus
- Check **Accessibility** permissions
- Text is still copied to clipboard - you can paste manually with `Cmd+V`

### "PortAudio not found" error
- Install PortAudio: `brew install portaudio`
- Then reinstall sounddevice: `uv pip install --force-reinstall sounddevice`

## Development

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run black .
```

## Privacy

- **No cloud**: All processing happens locally on your Mac
- **No storage**: Audio is not saved to disk (in-memory only)
- **No network**: The app works completely offline
- **No telemetry**: No data is collected or sent anywhere

## Known Limitations

- **English only**: Optimized for English language (use multilingual models for other languages)
- **macOS only**: Uses macOS-specific features (pynput, keyboard simulation)
- **Single application**: Can only run one instance at a time
- **Console-based**: No GUI (runs in Terminal)

## Future Enhancements

- [ ] Menu bar app with status indicator
- [ ] Background service (launch agent)
- [ ] Multiple language support
- [ ] Custom vocabulary/prompts
- [ ] Voice commands ("new line", "period", etc.)
- [ ] Recording history

## License

MIT License - See LICENSE file for details

## Credits

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast Whisper transcription
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [pynput](https://github.com/moses-palmer/pynput) - Input control
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Audio recording
