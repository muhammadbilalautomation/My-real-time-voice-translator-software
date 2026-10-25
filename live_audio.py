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

from gemini_client import DEFAULT_VOICE, ServiceError, load_key, speak_stream

LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
SPEECH_SLOTS = threading.BoundedSemaphore(2)


def explain_live_error(error, phase):
    """Only whitelisted diagnostics: never echo exception URLs or server secrets."""
    if isinstance(error, ServiceError):
        return error
    if isinstance(error, sd.PortAudioError):
        label = 'مائیک' if phase == 'audio_input' else 'ایئربڈز / آڈیو ڈیوائس'
        return ServiceError(label + ' دستیاب نہیں یا رابطہ ٹوٹ گیا۔ اسے کنیکٹ کرکے فہرست تازہ کریں۔', category='device')
    response = getattr(error, 'response', None)
    status = getattr(response, 'status_code', None)
    frame = getattr(error, 'rcvd', None)
    code = getattr(frame, 'code', None)
    reason = str(getattr(frame, 'reason', '')).lower()
    if status == 429 or any(word in reason for word in ('quota', 'resource_exhausted', 'rate limit', 'too many requests')):
        retry = 30
        try:
            retry = max(1, int(response.headers.get('Retry-After', '30'))) if response else 30
        except (ValueError, TypeError, AttributeError):
            pass
        return ServiceError('Google Live کی quota / رفتار کی حد آ گئی ہے۔ کچھ دیر انتظار کریں؛ بار بار Start نہ دبائیں۔', retry_after=retry, category='quota')
    if status in (401, 403) or any(word in reason for word in ('api key', 'permission_denied', 'unauthenticated', 'credentials')):
        return ServiceError('Google Live نے key یا اجازت قبول نہیں کی۔ ترتیبات میں key اور اس پروجیکٹ کی Live API رسائی چیک کریں۔', category='access')
    if status == 404 or code == 1007:
        return ServiceError('Google Live کا ماڈل یا آڈیو configuration قبول نہیں ہوا؛ تکنیکی ترتیب چیک کرنا ہوگی۔', category='configuration')
    if isinstance(error, (TimeoutError, OSError)):
        return ServiceError('Google Live سے رابطہ نہیں ہوا یا جواب میں دیر ہوئی۔ انٹرنیٹ چیک کرکے دوبارہ Start کریں۔', category='network')
    if code in (1000, 1001):
        return ServiceError('Google Live کا سیشن ختم ہوگیا۔ نیا سیشن Start کریں؛ پرانی آواز دوبارہ نہیں چلے گی۔', category='session')
    if code == 1011 or (isinstance(status, int) and status >= 500):
        return ServiceError('Google Live کی طرف سے عارضی سرور خرابی آئی ہے۔ کچھ دیر بعد نیا سیشن آزمائیں۔', category='server')
    return ServiceError('لائیو آڈیو پروسیسنگ رک گئی۔ ڈیوائسز کی فہرست تازہ کرکے نیا سیشن آزمائیں۔', category='processing')


class TextChunker:
    """Keep partial words; send completed translated sentences to one fixed voice."""
    def __init__(self):
        self.pending = ""

    def feed(self, text, finished=False):
        self.pending += text
        chunks = []
        while True:
            boundary = re.search(r"[!?۔؟]|(?<!\d)\.(?!\d)", self.pending)
            if boundary is None:
                # Long translated sentences can be spoken in clauses without
                # changing their words. Never split grouping commas in numbers.
                if len(self.pending.split()) >= 25:
                    boundary = re.search(r"(?<!\d)[,،;:](?!\d)", self.pending)
                if boundary is None:
                    break
            chunk = self.pending[:boundary.end()].strip()
            self.pending = self.pending[boundary.end():]
            if chunk:
                chunks.append(chunk)
        if finished and self.pending.strip():
            chunks.append(self.pending.strip())
            self.pending = ""
        if len(self.pending) > 2000:
            raise ServiceError("ترجمے میں مکمل جملے کی حد نہیں ملی؛ مزید آڈیو بنانے کے بجائے سیشن روک دیا۔")
        return chunks


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
        self.previous_filtered = 0.0

    def process(self, samples):
        data = np.asarray(samples, dtype="float32").reshape(-1)
        if not len(data):
            return data
        combined = np.concatenate((self.history, data))
        filtered = np.convolve(combined, self.kernel, mode="valid")
        self.history = combined[-100:]
        end = self.seen + len(data)
        positions = np.arange(self.next_position, end, self.source_rate / self.target_rate)
        # One source-sample delay makes interpolation causal: the last fractional
        # sample of a network chunk must not repeat its endpoint while waiting
        # for the next chunk. Preserve that endpoint across calls.
        result = np.interp(positions - self.seen - 1, np.arange(-1, len(filtered)),
                           np.concatenate(([self.previous_filtered], filtered)))
        self.previous_filtered = float(filtered[-1])
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
        self.enabled = True

    def enable(self, enabled):
        with self.lock:
            self.enabled = enabled
            if not enabled:
                self.parts.clear()
                self.frames = self.offset = 0

    def clear(self):
        with self.lock:
            self.parts.clear()
            self.frames = self.offset = 0

    def append(self, data):
        with self.lock:
            if not self.enabled:
                return
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
        self.playback.enable(audio_enabled)
        self.thread = None
        self.first_output = None
        self.started = None
        self.voice_epoch = 0
        self.speech_sequence = 0
        self.chunker = TextChunker()
        self.chunker_epoch = 0
        self.speech_jobs = None
        self.speech_ready = None
        self.phase = 'connecting'

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.playback.enable(False)

    def mute_audio(self, muted):
        if muted != self.audio_muted:
            self.voice_epoch += 1
            self.speech_sequence = 0
        self.audio_muted = muted
        self.playback.enable(not muted and not self.stop_event.is_set())

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
                if error.retry_after:
                    self.events.put(('cooldown', error.retry_after))
        except Exception as error:
            if not self.stop_event.is_set():
                safe = explain_live_error(error, self.phase)
                self.events.put(('error', str(safe)))
                if safe.retry_after:
                    self.events.put(('cooldown', safe.retry_after))
        finally:
            self.stop_event.set()
            self.playback.enable(False)
            self.events.put(("stopped", "سیشن بند ہے۔ پرانی آواز دوبارہ نہیں چلے گی۔"))

    async def connect_and_stream(self):
        self.phase = 'connecting'
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
            self.phase = 'audio_output'
            with sd.OutputStream(device=self.output, channels=1, samplerate=self.output_rate,
                                 dtype="float32", latency="high", callback=self.playback.read):
                self.phase = 'audio_input'
                with sd.InputStream(device=self.mic, channels=1, samplerate=self.input_rate,
                                    blocksize=round(self.input_rate * .1), dtype="float32",
                                    latency="high", callback=self.capture):
                    self.started = time.monotonic()
                    self.phase = 'streaming'
                    self.speech_jobs = asyncio.Queue(maxsize=4)
                    self.speech_ready = asyncio.Queue(maxsize=6)
                    self.events.put(("status", "لائیو شروع ہے۔ بولیں؛ مختصر معنوی حصوں میں ترجمہ آتا رہے گا۔"))
                    tasks = [asyncio.create_task(self.send(ws)), asyncio.create_task(self.receive(ws)),
                             asyncio.create_task(self.synthesize()), asyncio.create_task(self.synthesize()),
                             asyncio.create_task(self.render())]
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
            if self.chunker_epoch != self.voice_epoch or self.audio_muted:
                self.chunker = TextChunker()
                self.chunker_epoch = self.voice_epoch
            for key, event in (("inputTranscription", "original"), ("outputTranscription", "translation")):
                text = content.get(key, {}).get("text", "")
                if text:
                    if event == "translation":
                        language = content[key].get("languageCode", "").split("-")[0]
                        if (language and language != self.target) or (self.target == "en" and re.search(r"[\u0600-\u06ff]", text)):
                            self.playback.clear()
                            raise ServiceError("ترجمے کی زبان درست نہیں ملی؛ مزید آواز روک دی گئی۔")
                    self.events.put((event, text))
                    if event == "translation" and not self.audio_muted:
                        for chunk in self.chunker.feed(text):
                            self.queue_speech(chunk)
            if content.get("turnComplete") and not self.audio_muted:
                for chunk in self.chunker.feed("", finished=True):
                    self.queue_speech(chunk)
            # IMPORTANT: modelTurn.inlineData is never played. Its speaker identity
            # may vary. Only the translated text is synthesized with DEFAULT_VOICE.

    def queue_speech(self, text):
        if self.stop_event.is_set() or self.audio_muted:
            return
        if self.target == "en" and re.search(r"[\u0600-\u06ff]", text):
            raise ServiceError("انگریزی آواز کے لیے اردو متن ملا؛ آواز روک دی گئی۔")
        job = (self.voice_epoch, self.speech_sequence, text, time.monotonic())
        try:
            self.speech_jobs.put_nowait(job)
        except asyncio.QueueFull:
            raise ServiceError("مستقل مردانہ آواز بنانے کا کام پیچھے رہ گیا؛ سیشن روک دیا۔ مختصر جملوں سے دوبارہ آزمائیں۔") from None
        self.speech_sequence += 1

    async def synthesize(self):
        while not self.stop_event.is_set():
            epoch, sequence, text, created = await self.speech_jobs.get()
            if epoch != self.voice_epoch or self.audio_muted:
                continue
            chunks = queue.Queue(maxsize=30)
            await self.speech_ready.put((epoch, sequence, chunks, created))
            def produce():
                def put(item):
                    while not self.stop_event.is_set() and epoch == self.voice_epoch and not self.audio_muted:
                        try:
                            chunks.put(item, timeout=.1)
                            return True
                        except queue.Full:
                            pass
                    return False
                try:
                    for audio, rate in speak_stream(text, voice=DEFAULT_VOICE):
                        if not put(("audio", audio, rate)):
                            return
                    put(("end", None, None))
                except ServiceError as error:
                    put(("error", error, None))
                except Exception:
                    put(("error", "مستقل مردانہ آواز کا stream مکمل نہیں ہوا؛ سیشن روک دیا۔", None))
            finished = threading.Event()
            def run_producer():
                acquired = False
                try:
                    while not self.stop_event.is_set() and epoch == self.voice_epoch:
                        if SPEECH_SLOTS.acquire(timeout=.1):
                            acquired = True
                            produce()
                            return
                finally:
                    if acquired:
                        SPEECH_SLOTS.release()
                    finished.set()
            # A stopped session must not wait for an in-flight HTTPS response to
            # finish. Late audio is discarded; at most two synthesis calls run.
            threading.Thread(target=run_producer, daemon=True).start()
            while not finished.is_set() and not self.stop_event.is_set():
                await asyncio.sleep(.01)

    async def render(self):
        pending = {}
        epoch = self.voice_epoch
        expected = 0
        while not self.stop_event.is_set():
            item = await self.speech_ready.get()
            if epoch != self.voice_epoch:
                epoch, expected = self.voice_epoch, 0
                pending.clear()
            if item[0] != epoch or self.audio_muted:
                continue
            pending[item[1]] = item
            if len(pending) > 4:
                raise ServiceError("آواز کی ترتیب پیچھے رہ گئی؛ سیشن روک دیا۔")
            while expected in pending:
                _, _, chunks, created = pending.pop(expected)
                expected += 1
                converter = None
                while not self.stop_event.is_set() and epoch == self.voice_epoch and not self.audio_muted:
                    if time.monotonic() - created > 20:
                        raise ServiceError("ترجمے کی آواز بہت پرانی ہو گئی؛ پرانی بات سنانے کے بجائے سیشن روک دیا۔")
                    try:
                        kind, audio, rate = chunks.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(.01)
                        continue
                    if kind == "end":
                        break
                    if kind == "error":
                        raise audio if isinstance(audio, ServiceError) else ServiceError(audio)
                    if converter is None:
                        converter = Resampler(rate, self.output_rate)
                    samples = converter.process(audio[:, 0] * .8)
                    block = round(self.output_rate * .1)
                    for position in range(0, len(samples), block):
                        while self.playback.frames > self.output_rate:
                            if self.stop_event.is_set() or epoch != self.voice_epoch or self.audio_muted:
                                break
                            await asyncio.sleep(.02)
                        if self.stop_event.is_set() or epoch != self.voice_epoch or self.audio_muted:
                            break
                        if self.first_output is None:
                            self.first_output = time.monotonic() - self.started
                            self.events.put(("latency", f"پہلی مستقل مردانہ آواز: سیشن کے آغاز سے {self.first_output:.1f}s"))
                        self.playback.append(samples[position:position + block])
