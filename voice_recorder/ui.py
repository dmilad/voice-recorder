"""
Tkinter UI for Voice Recorder.
Provides a simple window for recording and displaying transcriptions.
"""

import queue
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable
import pyperclip


class VoiceRecorderUI:
    """Simple Tkinter UI for voice recording and transcription display."""

    def __init__(self, on_record_pressed: Callable[[], None]):
        """
        Initialize the UI.

        Args:
            on_record_pressed: Callback function when record button is pressed
        """
        self.on_record_pressed = on_record_pressed
        self.update_queue: queue.Queue = queue.Queue()

        # Create main window
        self.root = tk.Tk()
        self.root.title("Voice Recorder")
        self.root.geometry("500x400")
        self.root.resizable(True, True)

        # Create UI components
        self._create_widgets()

        # Start queue checking
        self._check_queue()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Status label at top
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 12),
            fg="gray"
        )
        self.status_label.pack(pady=(10, 5))

        # Progress label (hidden by default)
        self.progress_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 10),
            fg="blue"
        )
        self.progress_label.pack(pady=(0, 5))

        # Text display area (scrollable, read-only)
        text_frame = tk.Frame(self.root)
        text_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.text_display = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            state=tk.DISABLED,
            height=15
        )
        self.text_display.pack(fill=tk.BOTH, expand=True)

        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        # Record button
        self.record_button = tk.Button(
            button_frame,
            text="🎤 Record",
            font=("Arial", 14),
            width=15,
            height=2,
            command=self._on_record_clicked
        )
        self.record_button.pack(side=tk.LEFT, padx=5)

        # Copy button
        self.copy_button = tk.Button(
            button_frame,
            text="📋 Copy",
            font=("Arial", 14),
            width=15,
            height=2,
            command=self._on_copy_clicked,
            state=tk.DISABLED
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)

    def _on_record_clicked(self):
        """Handle record button click."""
        self.on_record_pressed()

    def _on_copy_clicked(self):
        """Copy displayed text to clipboard."""
        text = self.text_display.get("1.0", tk.END).strip()
        if text:
            pyperclip.copy(text)
            self._update_status("Copied to clipboard!", "green")
            # Reset status after 2 seconds
            self.root.after(2000, lambda: self._update_status("Ready", "gray"))

    def _check_queue(self):
        """Check queue for updates from other threads."""
        try:
            while True:
                event_type, data = self.update_queue.get_nowait()

                if event_type == "state":
                    self._update_state(data)
                elif event_type == "transcription":
                    self._update_transcription(data)
                elif event_type == "status":
                    self._update_status(data["message"], data.get("color", "gray"))
                elif event_type == "progress":
                    self._update_progress(data["processed"], data["total"])

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self._check_queue)

    def _update_state(self, state: str):
        """Update UI based on recording state."""
        if state == "IDLE":
            self.record_button.config(text="🎤 Record", state=tk.NORMAL)
            self.status_label.config(text="Ready", fg="gray")
            self.progress_label.config(text="")  # Hide progress
        elif state == "RECORDING":
            self.record_button.config(text="⏹️ Stop Recording", state=tk.NORMAL)
            self.status_label.config(text="Recording...", fg="red")
            self.progress_label.config(text="")  # Clear progress at start
        elif state == "PROCESSING":
            self.record_button.config(text="⏳ Processing...", state=tk.DISABLED)
            self.status_label.config(text="Transcribing...", fg="orange")

    def _update_transcription(self, text: str):
        """Update the text display with transcription."""
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete("1.0", tk.END)
        self.text_display.insert("1.0", text)
        self.text_display.config(state=tk.DISABLED)

        # Enable copy button if there's text
        if text.strip():
            self.copy_button.config(state=tk.NORMAL)
        else:
            self.copy_button.config(state=tk.DISABLED)

    def _update_status(self, message: str, color: str = "gray"):
        """Update status label."""
        self.status_label.config(text=message, fg=color)

    def _update_progress(self, processed_seconds: float, total_seconds: float):
        """Update progress display."""
        def format_time(seconds: float) -> str:
            """Format seconds as MM:SS."""
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"

        processed_str = format_time(processed_seconds)
        total_str = format_time(total_seconds)

        # Calculate percentage
        percentage = (processed_seconds / total_seconds * 100) if total_seconds > 0 else 0

        progress_text = f"Transcribed {processed_str} / {total_str} ({percentage:.0f}%)"
        self.progress_label.config(text=progress_text)

    def queue_state_update(self, state: str):
        """Queue a state update (thread-safe)."""
        self.update_queue.put(("state", state))

    def queue_transcription_update(self, text: str):
        """Queue a transcription update (thread-safe)."""
        self.update_queue.put(("transcription", text))

    def queue_status_update(self, message: str, color: str = "gray"):
        """Queue a status update (thread-safe)."""
        self.update_queue.put(("status", {"message": message, "color": color}))

    def queue_progress_update(self, processed_seconds: float, total_seconds: float):
        """Queue a progress update (thread-safe)."""
        self.update_queue.put(("progress", {"processed": processed_seconds, "total": total_seconds}))

    def show(self):
        """Start the UI main loop (blocking)."""
        self.root.mainloop()

    def destroy(self):
        """Destroy the UI window."""
        if self.root:
            self.root.quit()
            self.root.destroy()
