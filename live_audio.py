"""Continuous Gemini translation; audio is bounded, memory-only and never auto-started."""
import asyncio
import base64
from collections import deque
import json
import queue
import re
import threading
import time

import numpy as np
import sounddevice as sd
from websockets.asyncio.client import connect

from gemini_client import ServiceError, load_key

LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"


def live_setup(target):
    if target not in ("en", "ur"):
        raise ValueError("Only Urdu and English supported")
    return {"setup": {
        "model": "models/gemini-3.5-live-translate-preview",
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}},
            "translationConfig": {"targetLanguageCode": target, "echoTargetLanguage": False},
        },
        "inputAudioTranscription": {}, "outputAudioTranscription": {},
    }}


class Resampler:
    """Stateful low-pass resampling: keeps filter history across microphone blocks."""
    def __init__(self, source_rate, target_rate=16000):
        self.source_rate, self.target_rate = source_rate, target_rate
        cutoff = 0.45 * min(1, target_rate / source_rate)
        positions = np.arange(101) - 50
        self.kernel = 2 * cutoff * np.sinc(2 * cutoff * positions) * np.hamming(101)
        self.kernel /= self.kernel.sum()
        self.history = np.zeros(100, dtype="float32")
        self.seen = 0
        self.next_position = 0.0

    def process(self, samples):
        data = np.asarray(samples, dtype="float32").reshape(-1)
        if not len(data):
            return data
        combined = np.concatenate((self.history, data))
        filtered = np.convolve(combined, self.kernel, mode="valid")
        self.history = combined[-100:]
        end = self.seen + len(data)
        positions = np.arange(self.next_position, end, self.source_rate / self.target_rate)
        result = np.interp(positions - self.seen, np.arange(len(filtered)), filtered)
        self.next_position += len(positions) * self.source_rate / self.target_rate
        self.seen = end
        return result.astype("float32")


class PlaybackBuffer:
    def __init__(self, rate):
        self.rate = rate
        self.parts = deque()
        self.offset = 0
        self.frames = 0
        self.lock = threading.Lock()

    def clear(self):
        with self.lock:
            self.parts.clear()
            self.frames = self.offset = 0

    def append(self, data):
        with self.lock:
            if self.frames + len(data) > self.rate * 5:
                raise ServiceError("ترجمے کی آواز 5 سیکنڈ سے زیادہ پیچھے رہ گئی؛ پرانا آڈیو چلانے کے بجائے سیشن روک دیا۔")
            self.parts.append(data)
            self.frames += len(data)

    def read(self, output, frames, timing, status):
        output.fill(0)
        with self.lock:
            written = 0
            while self.parts and written < frames:
                part = self.parts[0]
                count = min(frames - written, len(part) - self.offset)
                output[written:written + count, 0] = part[self.offset:self.offset + count]
                self.offset += count
                self.frames -= count
                written += count
                if self.offset == len(part):
                    self.parts.popleft()
                    self.offset = 0


class LiveSession:
    def __init__(self, mic, output, target, *, audio_enabled=False):
        self.mic, self.output, self.target = mic, output, target
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.fault = threading.Event()
        self.mic_muted = False
        self.audio_muted = not audio_enabled
        self.capture_queue = queue.Queue(maxsize=20)
        self.input_rate = int(sd.query_devices(mic)["default_samplerate"])
        self.output_rate = int(sd.query_devices(output)["default_samplerate"])
        self.playback = PlaybackBuffer(self.output_rate)
        self.thread = None
        self.first_output = None
        self.started = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.playback.clear()

    def mute_audio(self, muted):
        self.audio_muted = muted
        if muted:
            self.playback.clear()

    def mute_mic(self, muted):
        self.mic_muted = muted
        if muted:
            try:
                while True:
                    self.capture_queue.get_nowait()
            except queue.Empty:
                pass

    def capture(self, data, frames, timing, status):
        if self.stop_event.is_set():
            return
        if status:
            self.fault.set()  # Do not translate audio known to have missing frames.
            return
        try:
            self.capture_queue.put_nowait(np.zeros_like(data) if self.mic_muted else data.copy())
        except queue.Full:
            self.fault.set()

    def run(self):
        try:
            asyncio.run(self.connect_and_stream())
        except ServiceError as error:
            if not self.stop_event.is_set():
                self.events.put(("error", str(error)))
        except Exception as error:
            if not self.stop_event.is_set():
                code = getattr(getattr(error, "rcvd", None), "code", None)
                message = "لائیو کنکشن ٹوٹ گیا۔ انٹرنیٹ، API اجازت یا quota چیک کرکے Start دوبارہ دبائیں۔"
                if code == 1007:
                    message = "لائیو model configuration قبول نہیں ہوئی؛ technical setup چیک کرنا ہوگا۔"
                self.events.put(("error", message))
        finally:
            self.stop_event.set()
            self.playback.clear()
            self.events.put(("stopped", "سیشن بند ہے۔ پرانی آواز دوبارہ نہیں چلے گی۔"))

    async def connect_and_stream(self):
        self.events.put(("status", "Google سے مسلسل آڈیو کنکشن بن رہا ہے…"))
        async with connect(LIVE_URL, additional_headers={"x-goog-api-key": load_key()},
                           open_timeout=15, close_timeout=2, max_size=8 * 1024 * 1024) as ws:
            await ws.send(json.dumps(live_setup(self.target)))
            setup = json.loads(await asyncio.wait_for(ws.recv(), 15))
            if "setupComplete" not in setup:
                raise ServiceError("Live session تیار نہیں ہوا۔ کوئی recording شروع نہیں ہوئی۔")
            if self.stop_event.is_set():
                return
            # Raw microphone and translated playback are separate. UI allows audible
            # output only with a selected headset to prevent a speaker feedback loop.
            with sd.OutputStream(device=self.output, channels=1, samplerate=self.output_rate,
                                 dtype="float32", latency="high", callback=self.playback.read):
                with sd.InputStream(device=self.mic, channels=1, samplerate=self.input_rate,
                                    blocksize=round(self.input_rate * .1), dtype="float32",
                                    latency="high", callback=self.capture):
                    self.started = time.monotonic()
                    self.events.put(("status", "لائیو شروع ہے۔ بولیں؛ مختصر معنوی حصوں میں ترجمہ آتا رہے گا۔"))
                    tasks = [asyncio.create_task(self.send(ws)), asyncio.create_task(self.receive(ws))]
                    try:
                        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                        for task in done:
                            task.result()
                    finally:
                        for task in tasks:
                            task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)

    async def send(self, ws):
        resampler = Resampler(self.input_rate)
        while not self.stop_event.is_set():
            if self.fault.is_set():
                raise ServiceError("مائیک کا آڈیو کٹ گیا یا کنکشن پیچھے رہ گیا؛ یہ سیشن روک دیا۔ Start سے دوبارہ آزمائیں۔")
            try:
                block = self.capture_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(.01)
                continue
            samples = resampler.process(block)
            pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
            await ws.send(json.dumps({"realtimeInput": {"audio": {
                "mimeType": "audio/pcm;rate=16000", "data": base64.b64encode(pcm).decode("ascii")}}}))

    async def receive(self, ws):
        while not self.stop_event.is_set():
            message = json.loads(await ws.recv())
            if self.stop_event.is_set():
                return
            content = message.get("serverContent", {})
            if content.get("interrupted"):
                self.playback.clear()
            for key, event in (("inputTranscription", "original"), ("outputTranscription", "translation")):
                text = content.get(key, {}).get("text", "")
                if text:
                    if event == "translation":
                        language = content[key].get("languageCode", "").split("-")[0]
                        if (language and language != self.target) or (self.target == "en" and re.search(r"[\u0600-\u06ff]", text)):
                            self.playback.clear()
                            raise ServiceError("ترجمے کی زبان درست نہیں ملی؛ مزید آواز روک دی گئی۔")
                    self.events.put((event, text))
            for part in content.get("modelTurn", {}).get("parts", []):
                inline = part.get("inlineData", {})
                if not inline.get("data"):
                    continue
                if self.first_output is None:
                    self.first_output = time.monotonic() - self.started
                    self.events.put(("latency", f"پہلی ترجمہ آواز: سیشن شروع ہونے سے {self.first_output:.1f}s (بولنے سے الگ پیمائش)"))
                if self.audio_muted:
                    continue
                raw = base64.b64decode(inline["data"])
                audio = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768 * .8
                count = max(1, round(len(audio) * self.output_rate / 24000))
                data = np.interp(np.arange(count) * 24000 / self.output_rate, np.arange(len(audio)), audio).astype("float32")
                if not self.stop_event.is_set() and not self.audio_muted:
                    self.playback.append(data)
