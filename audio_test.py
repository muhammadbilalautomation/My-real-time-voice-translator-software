"""Local, memory-only microphone test. Recording starts only on a button press."""

import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import sounddevice as sd


def prepare_playback(audio, rate, clean=True):
    """Gentle DC removal/headroom; no denoising, pitch change or amplification."""
    result = np.array(audio, dtype="float32", copy=True)
    if clean and len(result):
        result -= np.mean(result, axis=0, keepdims=True)
        peak = float(np.max(np.abs(result)))
        if peak > 0.8:
            result *= 0.8 / peak
        # Short fades prevent clicks at playback boundaries only.
        fade = min(round(rate * 0.005), len(result) // 2)
        if fade:
            ramp = np.linspace(0, 1, fade, dtype="float32")[:, None]
            result[:fade] *= ramp
            result[-fade:] *= ramp[::-1]
    return result


class AudioTest:
    def __init__(self, root):
        self.root = root
        self.stream = None
        self.mode = "idle"
        self.chunks = []
        self.audio = None
        self.rate = 48000
        self.frames = 0
        self.peak = 0.0
        self.warning = ""
        self.started = 0.0
        root.title("Voice Translator — Microphone Test / آواز کا ٹیسٹ")
        root.geometry("780x500")
        root.minsize(680, 500)
        root.protocol("WM_DELETE_WINDOW", self.close)
        panel = ttk.Frame(root, padding=20)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Step 2: Record → Stop → Play", font=("Segoe UI", 17)).pack(pady=8)
        ttk.Label(panel, text="Record دبائیں، 10 سیکنڈ بولیں، پھر Play دبائیں۔", font=("Segoe UI", 13)).pack(pady=5)
        self.devices = sd.query_devices()
        apis = sd.query_hostapis()
        self.inputs = {}
        self.outputs = {}
        for i, device in enumerate(self.devices):
            api = apis[device["hostapi"]]["name"]
            if api not in ("MME", "Windows WASAPI"):
                continue
            label = f'{i}: {device["name"]} [{api}]'
            if device["max_input_channels"]:
                self.inputs[label] = i
            if device["max_output_channels"]:
                self.outputs[label] = i
        self.mic = self.selector(panel, "Microphone / بولنے کا مائیک", self.inputs)
        self.speaker = self.selector(panel, "Playback / سننے کی ڈیوائس", self.outputs)
        self.choose(self.mic, self.inputs, "realtek", sd.default.device[0])
        self.choose(self.speaker, self.outputs, "airpads", sd.default.device[1])
        buttons = ttk.Frame(panel)
        buttons.pack(pady=16)
        self.record_button = ttk.Button(buttons, text="● Record — بولیں", command=self.record)
        self.record_button.pack(side="left", padx=8)
        self.stop_button = ttk.Button(buttons, text="■ Stop — روکیں", command=self.stop)
        self.stop_button.pack(side="left", padx=8)
        self.play_button = ttk.Button(buttons, text="▶ Play — سنیں", command=self.play)
        self.play_button.pack(side="left", padx=8)
        self.clean = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Light cleanup / ہلکی صفائی (بند کرکے اصل سے موازنہ کریں)",
                        variable=self.clean).pack()
        volume_row = ttk.Frame(panel)
        volume_row.pack(fill="x", pady=5)
        ttk.Label(volume_row, text="Playback volume / آواز کی اونچائی").pack(side="left")
        self.volume = tk.DoubleVar(value=80)
        ttk.Scale(volume_row, from_=10, to=100, variable=self.volume).pack(side="left", fill="x", expand=True, padx=12)
        self.meter = ttk.Progressbar(panel, maximum=100)
        self.meter.pack(fill="x", pady=5)
        self.status = tk.StringVar(value="تیار ہے۔ ابھی مائیک ریکارڈ نہیں ہو رہا۔")
        ttk.Label(panel, textvariable=self.status, wraplength=710).pack(pady=8)
        ttk.Label(panel, text="Local only • No internet • No audio files saved", foreground="#555555").pack()
        self.update_controls()
        self.timer = root.after(100, self.tick)

    @staticmethod
    def selector(panel, title, values):
        ttk.Label(panel, text=title).pack(anchor="w", pady=(8, 2))
        combo = ttk.Combobox(panel, values=list(values), state="readonly", width=90)
        combo.pack(fill="x")
        return combo

    def choose(self, combo, options, preferred, fallback):
        matches = [key for key in options if preferred in key.lower()]
        wasapi = [key for key in matches if "WASAPI" in key]
        defaults = [key for key, index in options.items() if index == fallback]
        candidates = wasapi or matches or defaults or list(options)
        if candidates:
            combo.set(candidates[0])

    def update_controls(self):
        busy = self.mode != "idle"
        self.record_button.config(state="disabled" if busy or not self.inputs else "normal")
        self.play_button.config(state="disabled" if busy or self.audio is None or not self.outputs else "normal")
        self.stop_button.config(state="normal" if busy else "disabled")
        for combo in (self.mic, self.speaker):
            combo.config(state="disabled" if busy else "readonly")

    def capture(self, data, frames, timing, status):
        if status:
            self.warning = str(status)
        remaining = int(self.rate * 10) - self.frames
        if remaining > 0:
            chunk = data[:remaining].copy()
            self.chunks.append(chunk)
            self.frames += len(chunk)
            self.peak = float(np.max(np.abs(chunk)))

    def record(self):
        try:
            device = self.inputs[self.mic.get()]
            self.rate = int(self.devices[device]["default_samplerate"])
            sd.check_input_settings(device=device, channels=1, samplerate=self.rate, dtype="float32")
            self.chunks = []
            self.audio = None
            self.frames = 0
            self.peak = 0.0
            self.warning = ""
            self.stream = sd.InputStream(device=device, channels=1, samplerate=self.rate,
                                         dtype="float32", latency="high", callback=self.capture)
            self.stream.start()
            self.started = time.monotonic()
            self.mode = "recording"
            self.update_controls()
        except Exception as error:
            self.stop()
            self.status.set(f"مائیک شروع نہیں ہوا۔ Windows microphone permission یا منتخب ڈیوائس چیک کریں۔ {error}")

    def stop(self):
        old_mode = self.mode
        self.mode = "idle"
        try:
            if self.stream is not None:
                try:
                    self.stream.abort()
                finally:
                    self.stream.close()
                    self.stream = None
            sd.stop()
            if old_mode == "recording":
                self.audio = np.concatenate(self.chunks) if self.chunks else None
                self.chunks = []
                seconds = 0 if self.audio is None else len(self.audio) / self.rate
                note = ""
                if self.audio is not None:
                    peak = float(np.max(np.abs(self.audio)))
                    if peak < 0.005:
                        note = " آواز بہت دھیمی یا خاموش ہے؛ مائیک چیک کریں۔"
                    elif peak >= 0.99:
                        note = " مائیک کی آواز پھٹ سکتی ہے؛ کچھ دور بول کر دوبارہ Record کریں۔ صفائی کھوئی ہوئی آواز واپس نہیں لاتی۔"
                self.status.set(f"ریکارڈنگ رک گئی: {seconds:.1f} سیکنڈ۔ Play سے سنیں۔{note} {self.warning}")
            elif old_mode == "playing":
                self.status.set("پلے بیک رک گیا۔ آواز صاف تھی؟")
        except Exception as error:
            self.status.set(f"آڈیو ڈیوائس میں مسئلہ ہے۔ ایپ بند کرکے دوبارہ کھولیں۔ {error}")
        self.meter["value"] = 0
        self.update_controls()

    def play(self):
        if self.audio is None:
            return
        try:
            device = self.outputs[self.speaker.get()]
            rate = int(self.devices[device]["default_samplerate"])
            sd.check_output_settings(device=device, channels=1, samplerate=rate, dtype="float32")
            audio = prepare_playback(self.audio, self.rate, self.clean.get())
            audio *= float(self.volume.get()) / 100
            if rate != self.rate:
                count = max(1, round(len(audio) * rate / self.rate))
                positions = np.arange(count) * self.rate / rate
                audio = np.interp(positions, np.arange(len(audio)), audio[:, 0]).astype("float32")
            sd.play(audio, samplerate=rate, device=device, blocking=False, latency="high")
            self.mode = "playing"
            self.status.set("آپ کی ریکارڈ کی ہوئی آواز چل رہی ہے۔ مائیک بند ہے۔")
            self.update_controls()
        except Exception as error:
            self.stop()
            self.status.set(f"آواز نہیں چل سکی۔ ایئربڈز کا کنکشن اور Playback ڈیوائس چیک کریں۔ {error}")

    def tick(self):
        if self.mode == "recording":
            self.meter["value"] = min(100, self.peak * 100)
            self.status.set(f"اب بولیں — {self.frames / self.rate:.1f} / 10 سیکنڈ۔ {self.warning}")
            if self.frames >= self.rate * 10:
                self.stop()
            elif time.monotonic() - self.started > 12:
                self.warning = "مائیک سے مکمل آڈیو موصول نہیں ہوئی؛ دوبارہ ٹیسٹ کریں۔"
                self.stop()
        elif self.mode == "playing":
            try:
                if not sd.get_stream().active:
                    playback_status = sd.get_status()
                    self.stop()
                    if playback_status:
                        self.status.set(f"پلے بیک کے دوران آڈیو کٹی ہے؛ دوبارہ سنیں یا دوسری ڈیوائس آزمائیں۔ {playback_status}")
            except Exception as error:
                self.stop()
                self.status.set(f"پلے بیک ڈیوائس دستیاب نہیں۔ {error}")
        self.timer = self.root.after(100, self.tick)

    def close(self):
        self.root.after_cancel(self.timer)
        self.stop()
        self.audio = None
        self.chunks = []
        self.root.destroy()


def main():
    root = tk.Tk()
    AudioTest(root)
    # Bring this separate desktop window above the editor on startup.
    root.update_idletasks()
    x = max(0, (root.winfo_screenwidth() - 780) // 2)
    y = max(0, (root.winfo_screenheight() - 500) // 2)
    root.geometry(f"780x500+{x}+{y}")
    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)
    root.after(5000, lambda: root.attributes("-topmost", False))
    root.mainloop()


if __name__ == "__main__":
    main()
