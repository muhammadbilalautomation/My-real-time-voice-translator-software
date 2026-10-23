"""Short-utterance demo: manual recording, reviewable translation and speech preview."""
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

from audio_test import AudioTest
from gemini_client import ServiceError, load_key, personal_voice, speak, translate


class TranslatorDemo(AudioTest):
    def __init__(self, root):
        super().__init__(root)
        # Compact the audio-test header so all review controls fit a laptop screen.
        audio_panel = root.winfo_children()[0]
        audio_panel.pack_configure(fill="x", expand=False)
        audio_panel.configure(padding=(16, 4, 16, 0))
        labels = [widget for widget in audio_panel.winfo_children() if isinstance(widget, ttk.Label)]
        for widget in (labels[0], labels[1], labels[-1]):
            widget.pack_forget()
        self.record_limit = 20
        root.title("Urdu ↔ English — Translation Demo / ترجمہ ڈیمو")
        root.geometry("900x850")
        root.minsize(800, 640)
        self.results = queue.Queue()
        self.generation = 0
        self.translated = None
        self.generated_audio = None
        self.record_button.config(text="● Record / بولیں (20s max)")
        self.play_button.config(text="Original / اپنی آواز سنیں")
        panel = ttk.Frame(root, padding=(20, 0, 20, 12))
        panel.pack(fill="both", expand=True)
        self.direction = ttk.Combobox(panel, state="readonly", values=["Urdu → English", "English → Urdu"])
        self.direction.current(0)
        self.direction.pack(fill="x", pady=4)
        self.direction.bind("<<ComboboxSelected>>", self.direction_changed)
        ttk.Label(panel, text="1. Record → Stop   2. Translate   3. Review → Listen", font=("Segoe UI", 12)).pack(pady=4)
        row = ttk.Frame(panel)
        row.pack(fill="x", pady=5)
        self.translate_button = ttk.Button(row, text="Translate recording / ریکارڈنگ کا ترجمہ", command=self.translate_recording)
        self.translate_button.pack(side="left", padx=4)
        self.text_button = ttk.Button(row, text="Translate typed text / متن کا ترجمہ", command=self.translate_text)
        self.text_button.pack(side="left", padx=4)
        self.speak_button = ttk.Button(row, text="Listen translation / ترجمہ سنیں", command=self.speak_translation)
        self.speak_button.pack(side="left", padx=4)
        voice_row = ttk.Frame(panel)
        voice_row.pack(fill="x", pady=3)
        ttk.Label(voice_row, text="English voice:").pack(side="left")
        self.voice_choice = ttk.Combobox(voice_row, state="readonly", width=20, values=["Preset AI voice", "My voice"])
        self.voice_choice.current(0)
        self.voice_choice.pack(side="left", padx=6)
        self.voice_choice.bind("<<ComboboxSelected>>", lambda event: setattr(self, "generated_audio", None))
        self.voice_button = ttk.Button(voice_row, text="Set up my voice / اپنی آواز", command=self.setup_voice)
        self.voice_button.pack(side="left", padx=6)
        ttk.Label(panel, text="Original / آپ کی بات — متن کا ٹیسٹ کرنے کے لیے یہاں لکھ بھی سکتے ہیں").pack(anchor="w")
        self.original = tk.Text(panel, height=3, wrap="word", font=("Segoe UI", 12), undo=False)
        self.original.pack(fill="both", expand=True, pady=3)
        ttk.Label(panel, text="Translation / ترجمہ — صرف جائزے کے لیے").pack(anchor="w")
        self.output = tk.Text(panel, height=3, wrap="word", font=("Segoe UI", 12), state="disabled")
        self.output.pack(fill="both", expand=True, pady=3)
        self.issue = tk.StringVar()
        ttk.Label(panel, textvariable=self.issue, foreground="#a13c00", wraplength=850).pack(pady=3)
        ttk.Label(panel, text="Translate sends audio/text to Google. Demo uses a preset AI voice, not your cloned voice.",
                  foreground="#555555", wraplength=850).pack()
        ttk.Label(panel, text="ترجمہ دبانے پر آواز/متن Google کو جاتا ہے۔ ابھی Zoom سے منسلک نہیں۔", wraplength=850).pack()
        try:
            load_key()
            self.status.set("تیار ہے۔ Record سے بولیں، Stop کے بعد Translate دبائیں۔")
        except ServiceError as error:
            self.status.set(str(error))
        self.update_controls()
        self.poll_timer = root.after(100, self.poll)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def direction_changed(self, event=None):
        self.translated = None
        self.generated_audio = None
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")
        self.issue.set("")
        self.update_controls()

    def update_controls(self):
        super().update_controls()
        if not hasattr(self, "translate_button"):
            return
        idle = self.mode == "idle"
        self.translate_button.config(state="normal" if idle and self.audio is not None else "disabled")
        self.text_button.config(state="normal" if idle else "disabled")
        self.speak_button.config(state="normal" if idle and self.translated and self.translated["status"] == "ok" else "disabled")
        self.direction.config(state="readonly" if idle else "disabled")
        self.voice_choice.config(state="readonly" if idle else "disabled")
        self.voice_button.config(state="normal" if idle else "disabled")
        self.original.config(state="normal" if idle else "disabled")

    def record(self):
        self.direction_changed()
        self.original.delete("1.0", "end")
        super().record()

    def stop(self):
        if self.mode == "processing":
            self.generation += 1
            self.mode = "idle"
            self.status.set("درخواست روک دی گئی؛ دیر سے آنے والا نتیجہ نہیں چلایا جائے گا۔")
            self.update_controls()
        else:
            super().stop()

    def languages(self):
        return ("Urdu", "English") if self.direction.current() == 0 else ("English", "Urdu")

    def run_job(self, kind, function):
        self.generation += 1
        generation = self.generation
        self.mode = "processing"
        self.status.set("ترجمہ ہو رہا ہے…" if kind == "translation" else "ترجمے کی آواز بن رہی ہے…")
        self.update_controls()
        def worker():
            started = time.monotonic()
            try:
                result = function()
                self.results.put((generation, kind, result, time.monotonic() - started))
            except ServiceError as error:
                self.results.put((generation, "error", str(error), 0))
            except Exception:
                self.results.put((generation, "error", "درخواست مکمل نہیں ہوئی۔ دوبارہ کوشش کریں؛ کوئی آواز خود سے نہیں بھیجی گئی۔", 0))
        threading.Thread(target=worker, daemon=True).start()

    def translate_recording(self):
        if self.mode != "idle" or self.audio is None:
            return
        if self.warning:
            self.issue.set("ریکارڈنگ کے دوران آواز کٹی تھی؛ دوبارہ Record کریں۔ " + self.warning)
            return
        source, target = self.languages()
        audio, rate = self.audio.copy(), self.rate
        self.translated = None
        self.generated_audio = None
        self.run_job("translation", lambda: translate(source, target, audio=audio, rate=rate))

    def translate_text(self):
        if self.mode != "idle":
            return
        text = self.original.get("1.0", "end").strip()
        if not text:
            self.issue.set("پہلے اوپر متن لکھیں یا Record سے بولیں۔")
            return
        if len(text) > 2000:
            self.issue.set("اس ڈیمو میں مختصر متن، زیادہ سے زیادہ 2000 حروف، استعمال کریں۔")
            return
        source, target = self.languages()
        self.translated = None
        self.generated_audio = None
        self.run_job("translation", lambda: translate(source, target, text=text))

    def speak_translation(self):
        if self.mode != "idle" or not self.translated or self.translated["status"] != "ok":
            return
        if self.generated_audio is not None:
            self.preview()
        else:
            text = self.translated["translation"]
            voice = "Kore"
            if self.languages()[1] == "English" and self.voice_choice.current() == 1:
                voice = personal_voice()
                if voice is None:
                    self.issue.set("آپ کی آواز ابھی تیار نہیں یا اس کی key ختم ہو گئی ہے؛ Set up my voice استعمال کریں۔")
                    return
            self.run_job("speech", lambda: speak(text, voice=voice))

    def setup_voice(self):
        if self.mode != "idle":
            return
        from voice_setup import VoiceSetup
        window = tk.Toplevel(self.root)
        VoiceSetup(window)
        window.transient(self.root)
        window.grab_set()

    def preview(self):
        # Use the tested playback path without replacing the microphone recording.
        original_audio, original_rate = self.audio, self.rate
        self.audio, self.rate = self.generated_audio
        try:
            super().play()
        finally:
            self.audio, self.rate = original_audio, original_rate

    def poll(self):
        try:
            while True:
                generation, kind, result, elapsed = self.results.get_nowait()
                if generation != self.generation:
                    continue
                self.mode = "idle"
                self.update_controls()
                if kind == "error":
                    self.issue.set(result)
                    self.status.set("آواز روک دی گئی۔ error اوپر دیکھیں۔")
                elif kind == "translation":
                    self.translated = result
                    self.original.delete("1.0", "end")
                    self.original.insert("1.0", result["transcript"])
                    self.output.config(state="normal")
                    self.output.delete("1.0", "end")
                    self.output.insert("1.0", result["translation"])
                    self.output.config(state="disabled")
                    self.issue.set(result["issue"])
                    if result["status"] == "unclear":
                        self.issue.set(result["issue"] or "بات واضح نہیں ہوئی؛ دوبارہ کہیں۔")
                        self.status.set(f"{elapsed:.1f}s — تصدیق ضروری ہے؛ اس نتیجے کی آواز بند ہے۔")
                    else:
                        self.status.set(f"ترجمہ تیار: {elapsed:.1f}s۔ متن دیکھ کر Listen translation دبائیں۔")
                elif kind == "speech":
                    self.generated_audio = result
                    self.preview()
                self.update_controls()
        except queue.Empty:
            pass
        self.poll_timer = self.root.after(100, self.poll)

    def close(self):
        self.root.after_cancel(self.poll_timer)
        self.generation += 1
        self.generated_audio = None
        self.translated = None
        super().close()


def main():
    root = tk.Tk()
    TranslatorDemo(root)
    root.update_idletasks()
    height = min(850, root.winfo_screenheight() - 80)
    root.minsize(800, min(760, height))
    root.geometry(f"900x{height}+30+20")
    root.lift()
    root.attributes("-topmost", True)
    root.after(5000, lambda: root.attributes("-topmost", False))
    root.mainloop()


if __name__ == "__main__":
    main()
