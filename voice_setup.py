"""Explicit user-operated reference and consent recording for personal voice setup."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from audio_test import AudioTest
from gemini_client import ServiceError, replicate_voice

CONSENT = "I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model."
CONSENT_READING = "آئی ایم دی اونَر آف دِس وائس\nاینڈ آئی کَن سینٹ ٹُو گوگل\nیُوزِنگ دِس وائس ٹُو کریئیٹ\nاے سِن تھیٹِک وائس ماڈل۔"


class VoiceSetup(AudioTest):
    def __init__(self, root):
        super().__init__(root)
        self.record_limit = 30
        self.reference = None
        self.consent = None
        self.jobs = queue.Queue()
        self.recording_kind = "reference"
        self.closed = False
        root.title("اپنی آواز بنائیں — دو آسان recordings")
        root.geometry("900x680")
        root.minsize(800, 640)
        audio_panel = root.winfo_children()[0]
        audio_panel.pack_configure(fill="x", expand=False)
        audio_panel.configure(padding=(16, 0, 16, 0))
        labels = [w for w in audio_panel.winfo_children() if isinstance(w, ttk.Label)]
        for widget in (labels[0], labels[1], labels[-1]):
            widget.pack_forget()
        # Use the detected devices; keep technical settings out of this simple flow.
        for widget in (self.mic, self.speaker, labels[2], labels[3]):
            widget.pack_forget()
        self.record_button.config(text="1. میری عام آواز ریکارڈ کریں")
        self.consent_record_button = ttk.Button(self.record_button.master, text="2. رضامندی ریکارڈ کریں", command=self.record_consent)
        self.consent_record_button.pack(side="left", padx=5)
        panel = ttk.Frame(root, padding=16)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="پہلا بٹن دبائیں، عام اردو میں 15–20 سیکنڈ بات کریں، پھر Stop دبائیں۔ نمونہ خود منتخب ہو جائے گا۔", wraplength=850, font=("Segoe UI", 12)).pack(pady=5)
        self.reference_button = ttk.Button(panel, text="Use recording as reference / قدرتی آواز کا نمونہ", command=self.use_reference)
        ttk.Label(panel, text="پھر دوسرا بٹن دبائیں، نیچے اردو حروف والی چار لائنیں پڑھیں، پھر Stop دبائیں۔", wraplength=850, font=("Segoe UI", 12)).pack(pady=5)
        phrase = tk.Text(panel, height=4, wrap="word", font=("Segoe UI", 18))
        phrase.tag_configure("reading", justify="right")
        phrase.insert("1.0", CONSENT_READING, "reading")
        phrase.config(state="disabled")
        phrase.pack(fill="x", pady=3)
        ttk.Label(panel, text="مطلب: یہ میری آواز ہے اور میں Google کو اس سے مصنوعی آواز بنانے کی اجازت دیتا ہوں۔", wraplength=850).pack(pady=3)
        ttk.Label(panel, text=CONSENT, wraplength=850, font=("Segoe UI", 9), foreground="#555555").pack(pady=2)
        self.consent_button = ttk.Button(panel, text="Use recording as consent / رضامندی کا نمونہ", command=self.use_consent)
        self.owned = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="میں بالغ ہوں، دونوں نمونے میری آواز ہیں، اور انہیں Google کو آواز کی نقل بنانے کے لیے بھیجنے پر راضی ہوں۔",
                        variable=self.owned, command=self.update_controls).pack(pady=5)
        self.create_button = ttk.Button(panel, text="Create my voice / میری آواز تیار کریں", command=self.create_voice)
        self.create_button.pack(pady=4)
        self.progress = tk.StringVar(value="ابھی کوئی نمونہ منتخب نہیں۔")
        ttk.Label(panel, textvariable=self.progress, wraplength=850).pack(pady=4)
        ttk.Label(panel, text="نمونے upload صرف Create پر ہوں گے۔ مقامی آڈیو فائل نہیں بنتی۔ عارضی voice key تقریباً 7 دن رہتی ہے۔", wraplength=850).pack()
        self.poll_timer = root.after(100, self.poll)
        self.update_controls()

    def update_controls(self):
        super().update_controls()
        if not hasattr(self, "create_button"):
            return
        idle = self.mode == "idle"
        for button in (self.reference_button, self.consent_button):
            button.config(state="normal" if idle and self.audio is not None else "disabled")
        ready = idle and self.reference is not None and self.consent is not None and self.owned.get()
        self.create_button.config(state="normal" if ready else "disabled")
        self.consent_record_button.config(state="normal" if idle and self.reference is not None else "disabled")

    def record(self):
        self.recording_kind = "reference"
        self.reference = None
        self.consent = None
        super().record()

    def record_consent(self):
        if self.reference is None or self.mode != "idle":
            return
        self.recording_kind = "consent"
        self.consent = None
        super().record()

    def use_reference(self):
        if self.audio is None or self.mode != "idle":
            return
        seconds = len(self.audio) / self.rate
        if not 10 <= seconds <= 30.1 or self.warning:
            self.progress.set("قدرتی آواز 10–30 سیکنڈ صاف اور بغیر کٹے ریکارڈ کریں۔")
            return
        self.reference = self.audio.copy(), self.rate
        self.progress.set("✓ پہلی recording تیار ہے۔ اب اوپر «2. رضامندی ریکارڈ کریں» دبائیں۔")
        self.update_controls()

    def use_consent(self):
        if self.audio is None or self.mode != "idle":
            return
        if len(self.audio) / self.rate < 3 or self.warning:
            self.progress.set("رضامندی کا مکمل جملہ بغیر کٹے ریکارڈ کریں۔")
            return
        self.consent = self.audio.copy(), self.rate
        self.progress.set("✓ دونوں recordings تیار ہیں۔ رضامندی کا خانہ منتخب کریں، پھر «میری آواز تیار کریں» دبائیں۔")
        self.update_controls()

    def create_voice(self):
        if not self.owned.get() or self.reference is None or self.consent is None or self.mode != "idle":
            return
        self.mode = "processing"
        self.status.set("Google رضامندی اور آواز چیک کر رہا ہے…")
        self.update_controls()
        reference, reference_rate = self.reference
        consent, consent_rate = self.consent
        def worker():
            try:
                replicate_voice(reference, reference_rate, consent, consent_rate)
                self.jobs.put((True, "ذاتی آواز تیار ہے۔ یہ ونڈو بند کرکے ترجمہ ڈیمو میں My voice منتخب کریں۔"))
            except ServiceError as error:
                self.jobs.put((False, str(error)))
            except Exception:
                self.jobs.put((False, "آواز تیار نہیں ہوئی؛ key یا نجی آواز کی تفصیل ظاہر نہیں کی گئی۔"))
        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        if self.mode == "processing":
            self.status.set("آواز کی تصدیق چل رہی ہے؛ سرور درخواست واپس نہیں لی جا سکتی۔ ریکارڈنگ بند ہے۔")
            return
        was_recording = self.mode == "recording"
        super().stop()
        if was_recording and self.audio is not None:
            if self.recording_kind == "reference":
                self.use_reference()
            else:
                self.use_consent()

    def poll(self):
        try:
            success, message = self.jobs.get_nowait()
            self.mode = "idle"
            self.status.set(message)
            self.progress.set(message)
            if success:
                self.reference = self.consent = self.audio = None
            self.update_controls()
        except queue.Empty:
            pass
        self.poll_timer = self.root.after(100, self.poll)

    def close(self):
        if self.mode == "processing":
            self.status.set("جاری voice setup مکمل ہونے دیں؛ ریکارڈنگ بند ہے۔")
            return
        self.root.after_cancel(self.poll_timer)
        self.reference = self.consent = None
        super().close()


if __name__ == "__main__":
    window = tk.Tk()
    VoiceSetup(window)
    window.lift()
    window.attributes("-topmost", True)
    window.after(5000, lambda: window.attributes("-topmost", False))
    window.mainloop()
