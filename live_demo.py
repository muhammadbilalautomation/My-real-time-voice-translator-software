"""Simple continuous translation experiment, not yet connected to a meeting app."""
import queue
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

import sounddevice as sd
from audio_test import AudioTest
from live_audio import LiveSession


class LiveDemo(AudioTest):
    def __init__(self, root):
        super().__init__(root)
        self.session = None
        root.title("Live Urdu ↔ English / مسلسل ترجمہ ٹیسٹ")
        root.geometry("900x680")
        root.minsize(800, 640)
        panel = root.winfo_children()[0]
        panel.pack_configure(fill="x", expand=False)
        panel.configure(padding=(16, 4, 16, 0))
        labels = [w for w in panel.winfo_children() if isinstance(w, ttk.Label)]
        for widget in (labels[0], labels[1], labels[-1], self.meter, self.play_button):
            widget.pack_forget()
        for widget in panel.winfo_children():
            if isinstance(widget, ttk.Checkbutton) or any(isinstance(child, ttk.Scale) for child in widget.winfo_children()):
                widget.pack_forget()
        self.record_button.config(text="▶ Start Live / مسلسل شروع", command=self.start_live)
        self.stop_button.config(command=self.stop)
        self.refresh_button = ttk.Button(self.record_button.master, text="↻ ایئربڈز کی فہرست تازہ کریں", command=self.refresh_devices)
        self.refresh_button.pack(side="left", padx=8)
        lower = ttk.Frame(root, padding=(16, 0, 16, 10))
        lower.pack(fill="both", expand=True)
        self.direction = ttk.Combobox(lower, state="readonly", values=["Urdu → English", "English → Urdu"])
        self.direction.current(0)
        self.direction.pack(fill="x", pady=6)
        self.hear = tk.BooleanVar(value=False)
        ttk.Checkbutton(lower, text="ترجمے کی آواز سنیں — صرف Headphones/Headset منتخب کرکے", variable=self.hear,
                        command=self.change_audio).pack(anchor="w", pady=5)
        self.muted = tk.BooleanVar(value=False)
        ttk.Checkbutton(lower, text="اپنا مائیک خاموش کریں / Mute microphone", variable=self.muted,
                        command=self.change_mic).pack(anchor="w", pady=5)
        ttk.Label(lower, text="Start صرف ایک بار دبائیں۔ پھر عام انداز میں بولیں؛ ہر بار Record/Translate دبانے کی ضرورت نہیں۔", wraplength=850).pack(pady=5)
        self.original = tk.Text(lower, height=4, wrap="word", font=("Segoe UI", 12), state="disabled")
        ttk.Label(lower, text="Original / اصل بات").pack(anchor="w")
        self.original.pack(fill="both", expand=True)
        ttk.Label(lower, text="Live translation / مسلسل ترجمہ").pack(anchor="w", pady=(6, 0))
        self.translation = tk.Text(lower, height=4, wrap="word", font=("Segoe UI", 12), state="disabled")
        self.translation.pack(fill="both", expand=True)
        self.notice = tk.StringVar(value="یہ live experiment ہے؛ ابھی Zoom/Meet کی روٹنگ اور ہر غلطی روکنے کی تصدیق نہیں ہوئی۔")
        ttk.Label(lower, textvariable=self.notice, foreground="#a13c00", wraplength=850).pack(pady=5)
        ttk.Label(lower, text="Voice locked: Puck (male) — لائیو متن سے ایک ہی آواز بنتی ہے؛ کچھ اضافی تاخیر ممکن ہے۔", wraplength=850).pack()
        self.status.set("تیار ہے۔ پہلے headphones منتخب کریں، یا صرف متن کے لیے آواز کا خانہ بند رکھیں۔")
        self.poll_timer = root.after(100, self.poll)
        self.update_controls()

    def update_controls(self):
        super().update_controls()
        if hasattr(self, "direction"):
            self.direction.config(state="readonly" if self.mode == "idle" else "disabled")
            self.refresh_button.config(state="normal" if self.mode == "idle" else "disabled")

    def refresh_devices(self):
        if self.mode != "idle":
            return
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--hear"],
                         cwd=str(Path(__file__).resolve().parent))
        self.close()

    def headphones_selected(self):
        return any(word in self.speaker.get().lower() for word in ("headphones", "headset", "earbuds"))

    def change_audio(self):
        if self.hear.get() and not self.headphones_selected():
            self.hear.set(False)
            self.notice.set("اسپیکر منتخب ہیں۔ آواز دوبارہ مائیک میں جانے سے بچانے کے لیے صرف متن چلے گا۔ پہلے headphones منتخب کریں۔")
        if self.session:
            self.session.mute_audio(not self.hear.get())

    def change_mic(self):
        if self.session:
            self.session.mute_mic(self.muted.get())

    def start_live(self):
        if self.mode != "idle":
            return
        self.change_audio()
        try:
            self.session = LiveSession(self.inputs[self.mic.get()], self.outputs[self.speaker.get()],
                                       "en" if self.direction.current() == 0 else "ur", audio_enabled=self.hear.get())
            self.session.mute_mic(self.muted.get())
            self.mode = "live"
            self.update_controls()
            self.session.start()
        except Exception:
            self.mode = "idle"
            self.update_controls()
            self.status.set("ڈیوائس دستیاب نہیں۔ ایئربڈز connect کرکے ونڈو دوبارہ کھولیں۔")

    def stop(self):
        if hasattr(self, "session") and self.session is not None:
            self.session.stop()
            self.mode = "stopping"
            self.status.set("مائیک اور آواز بند ہو رہے ہیں…")
            self.update_controls()
        else:
            super().stop()

    def poll(self):
        if self.session:
            try:
                while True:
                    kind, message = self.session.events.get_nowait()
                    if kind in ("original", "translation") and self.mode == "live":
                        widget = self.original if kind == "original" else self.translation
                        widget.config(state="normal")
                        widget.insert("end", message)
                        # Bound transcript memory, too.
                        if int(widget.index("end-1c").split(".")[0]) > 100:
                            widget.delete("1.0", "20.0")
                        widget.see("end")
                        widget.config(state="disabled")
                    elif kind in ("error", "latency"):
                        self.notice.set(message)
                    elif kind == "status" and self.mode == "live":
                        self.status.set(message)
                    elif kind == "stopped":
                        self.mode = "idle"
                        self.status.set(message)
                        self.update_controls()
            except queue.Empty:
                pass
        self.poll_timer = self.root.after(100, self.poll)

    def close(self):
        self.root.after_cancel(self.poll_timer)
        if self.session:
            self.session.stop()
        self.root.after_cancel(self.timer)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LiveDemo(root)
    if "--hear" in sys.argv and app.headphones_selected():
        app.hear.set(True)
        app.change_audio()
    root.lift()
    root.attributes("-topmost", True)
    root.after(5000, lambda: root.attributes("-topmost", False))
    root.mainloop()


if __name__ == "__main__":
    main()
