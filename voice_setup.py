"""Explicit user-operated reference and consent recording for personal voice setup."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from audio_test import AudioTest
from gemini_client import ServiceError, replicate_voice

CONSENT = "I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model."


class VoiceSetup(AudioTest):
    def __init__(self, root):
        super().__init__(root)
        self.record_limit = 30
        self.reference = None
        self.consent = None
        self.jobs = queue.Queue()
        self.closed = False
        root.title("My voice setup / اپنی آواز کی تیاری")
        root.geometry("900x760")
        root.minsize(800, 680)
        audio_panel = root.winfo_children()[0]
        audio_panel.pack_configure(fill="x", expand=False)
        audio_panel.configure(padding=(16, 0, 16, 0))
        labels = [w for w in audio_panel.winfo_children() if isinstance(w, ttk.Label)]
        for widget in (labels[0], labels[1], labels[-1]):
            widget.pack_forget()
        self.record_button.config(text="Record (max 30s)")
        panel = ttk.Frame(root, padding=16)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="1. Record: اپنی عام اردو آواز میں 10–30 سیکنڈ بات کریں۔ Stop پھر Use reference دبائیں۔", wraplength=850).pack(pady=5)
        self.reference_button = ttk.Button(panel, text="Use recording as reference / قدرتی آواز کا نمونہ", command=self.use_reference)
        self.reference_button.pack(pady=3)
        ttk.Label(panel, text="2. دوبارہ Record دبائیں، یہ مکمل جملہ خود بولیں، Stop پھر Use consent دبائیں:", wraplength=850).pack(pady=5)
        phrase = tk.Text(panel, height=3, wrap="word", font=("Segoe UI", 12))
        phrase.insert("1.0", CONSENT)
        phrase.config(state="disabled")
        phrase.pack(fill="x", pady=3)
        self.consent_button = ttk.Button(panel, text="Use recording as consent / رضامندی کا نمونہ", command=self.use_consent)
        self.consent_button.pack(pady=3)
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

    def use_reference(self):
        if self.audio is None or self.mode != "idle":
            return
        seconds = len(self.audio) / self.rate
        if not 10 <= seconds <= 30.1 or self.warning:
            self.progress.set("قدرتی آواز 10–30 سیکنڈ صاف اور بغیر کٹے ریکارڈ کریں۔")
            return
        self.reference = self.audio.copy(), self.rate
        self.progress.set("قدرتی آواز منتخب ہے۔ اب رضامندی کا مکمل جملہ Record کریں۔")
        self.update_controls()

    def use_consent(self):
        if self.audio is None or self.mode != "idle":
            return
        if len(self.audio) / self.rate < 3 or self.warning:
            self.progress.set("رضامندی کا مکمل جملہ بغیر کٹے ریکارڈ کریں۔")
            return
        self.consent = self.audio.copy(), self.rate
        self.progress.set("رضامندی منتخب ہے۔ دونوں اصل recordings چیک کرکے checkbox منتخب کریں۔")
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
        super().stop()

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
