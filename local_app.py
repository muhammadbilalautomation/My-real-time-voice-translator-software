"""Loopback-only desktop web UI. No browser API keys, recordings or remote hosting."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import queue
import re
import secrets
import socket
import subprocess
import threading
import time
import urllib.request
import unicodedata
import webbrowser

import numpy as np
import sounddevice as sd

from gemini_client import ServiceError, load_key, speak_stream
from live_audio import LiveSession, Resampler

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / '.env'
PORT = 8765


class LocalServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR allows two servers to accept on the SAME port,
    # mixing app tokens and session state. Reserve it exclusively instead.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class AppState:
    def __init__(self):
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.session = None
        self.active = self.testing = False
        self.original = self.translation = self.error = self.latency = ''
        self.status = 'تیار ہے — Start دبانے تک مائیک بند ہے۔'
        self.last_seen = time.monotonic()
        self.hear = True
        self.muted = False
        self.test_cancel = threading.Event()
        self.next_start_at = 0.0

    def devices(self):
        devices, apis = sd.query_devices(), sd.query_hostapis()
        result = {'inputs': [], 'outputs': []}
        for index, item in enumerate(devices):
            api = apis[item['hostapi']]['name']
            if api not in ('MME', 'Windows WASAPI'):
                continue
            name = item['name']
            entry = {'id': index, 'name': name, 'api': api,
                     'headphones': any(w in name.lower() for w in ('headphones', 'headset', 'earbuds', 'airpod', 'airpad'))}
            if item['max_input_channels']:
                result['inputs'].append(entry)
            if item['max_output_channels']:
                result['outputs'].append(entry)
        return result

    def snapshot(self):
        with self.lock:
            self.last_seen = time.monotonic()
            if self.session:
                while True:
                    try:
                        kind, text = self.session.events.get_nowait()
                    except queue.Empty:
                        break
                    if kind in ('original', 'translation'):
                        setattr(self, kind, (getattr(self, kind) + text)[-12000:])
                    elif kind == 'error':
                        self.error = text
                    elif kind == 'latency':
                        self.latency = text
                    elif kind == 'status':
                        self.status = text
                    elif kind == 'cooldown':
                        self.next_start_at = max(self.next_start_at, time.monotonic() + float(text))
                    elif kind == 'stopped':
                        self.active = False
                        self.status = text
            try:
                load_key()
                key_ready = True
            except ServiceError:
                key_ready = False
            return {key: getattr(self, key) for key in
                    ('active', 'testing', 'original', 'translation', 'error', 'latency', 'status', 'hear', 'muted')} | {'key_ready': key_ready, 'retry_after': max(0, math.ceil(self.next_start_at - time.monotonic()))}

    def refresh_devices(self):
        with self.lock:
            self.require_idle()
            if self.session and getattr(self.session, 'thread', None) and self.session.thread.is_alive():
                raise ValueError('پچھلا سیشن بند ہو رہا ہے؛ چند سیکنڈ بعد فہرست تازہ کریں۔')
            sd._terminate()
            sd._initialize()
            return self.devices()

    def require_available(self):
        if time.monotonic() < self.next_start_at:
            raise ValueError('Google کی حد کے بعد انتظار جاری ہے؛ countdown ختم ہونے دیں۔')

    @staticmethod
    def resolve_device(devices, body, kind):
        name, api = body.get(kind + '_name'), body.get(kind + '_api')
        if not isinstance(name, str) or not isinstance(api, str) or not name or not api:
            raise ValueError('ونڈو کو Ctrl+Shift+R سے تازہ کریں، پھر مائیک اور ایئربڈز منتخب کریں۔')
        matches = [d['id'] for d in devices if d['name'] == name and d['api'] == api]
        if len(matches) != 1:
            label = 'مائیک' if kind == 'mic' else 'ایئربڈز / منتخب سننے کی ڈیوائس'
            raise ValueError(label + ' اب دستیاب نہیں۔ اسے کنیکٹ کرکے فہرست تازہ کریں؛ کوئی API درخواست نہیں بھیجی گئی۔')
        return matches[0]

    def validate_devices(self, body):
        devices = self.devices()
        mic, output = body.get('mic'), body.get('output')
        if type(mic) is not int or not any(d['id'] == mic for d in devices['inputs']):
            raise ValueError('مائیک منتخب کریں؛ ضرورت ہو تو Devices refresh دبائیں۔')
        selected = next((d for d in devices['outputs'] if d['id'] == output and type(output) is int), None)
        if not selected:
            raise ValueError('سننے کی ڈیوائس منتخب کریں۔')
        if type(body.get('hear', True)) is not bool:
            raise ValueError('آواز کی ترتیب درست نہیں۔')
        if body.get('hear', True) and not selected['headphones']:
            raise ValueError('آواز سننے کے لیے پہلے ایئربڈز منتخب کریں؛ اسپیکر سے آواز مائیک میں واپس جا سکتی ہے۔')
        return mic, output

    def start(self, body):
        with self.lock:
            self.snapshot()
            self.require_idle()
            self.require_available()
            if body.get('target') not in ('en', 'ur'):
                raise ValueError('صرف Urdu یا English منتخب کریں۔')
            # Bluetooth reconnect can renumber endpoints. Refresh before any API
            # connection and resolve the user's exact name/API, never a stale ID.
            fresh = self.refresh_devices()
            mic = self.resolve_device(fresh['inputs'], body, 'mic')
            output = self.resolve_device(fresh['outputs'], body, 'output')
            self.validate_devices(body | {'mic': mic, 'output': output})
            load_key()
            # Do not overlap device handles while a previous session closes.
            if self.session and self.session.thread and self.session.thread.is_alive():
                raise ValueError('پچھلا سیشن بند ہو رہا ہے؛ چند سیکنڈ انتظار کریں۔')
            self.session = LiveSession(mic, output, body['target'], audio_enabled=body.get('hear', True))
            self.hear, self.muted = body.get('hear', True), False
            self.original = self.translation = self.error = self.latency = ''
            self.status = 'Google سے رابطہ ہو رہا ہے…'
            self.active = True
            self.session.start()

    def require_idle(self):
        if self.active or self.testing:
            raise ValueError('پہلے موجودہ ٹیسٹ یا سیشن روکیں۔')

    def save_key(self, value):
        with self.lock:
            self.require_idle()
            if not isinstance(value, str) or len(value) > 500:
                raise ValueError('مکمل API key پیسٹ کریں۔')
            key = ''.join(c for c in value if unicodedata.category(c) != 'Cf').strip()
            if key.startswith('GEMINI_API_KEY='):
                key = key.partition('=')[2].strip()
            key = key.strip('\"\'`').strip()
            if not re.fullmatch(r'[A-Za-z0-9_.-]{20,300}', key):
                raise ValueError('اصل API key پیسٹ کریں؛ اضافی الفاظ یا خالی جگہ شامل نہ کریں۔')
            if os.environ.get('GEMINI_API_KEY'):
                raise ValueError('Key ماحول کی ترتیب سے آ رہی ہے؛ اسے بدلنے کے لیے backend کی environment ترتیب اپ ڈیٹ کریں۔')
            lines = ENV_PATH.read_text(encoding='utf-8-sig').splitlines() if ENV_PATH.exists() else []
            lines = [line for line in lines if line.partition('=')[0].strip() != 'GEMINI_API_KEY']
            temporary = ENV_PATH.with_name('.env.new')
            try:
                temporary.write_text('\n'.join(lines + ['GEMINI_API_KEY=' + key]) + '\n', encoding='utf-8')
                os.replace(temporary, ENV_PATH)
            finally:
                temporary.unlink(missing_ok=True)

    def stop(self):
        with self.lock:
            self.test_cancel.set()
            if self.session:
                self.session.stop()
            self.active = False
            self.status = 'مائیک بند ہے۔'

    def test_voice(self, body):
        with self.lock:
            self.require_idle()
            self.require_available()
            fresh = self.refresh_devices()
            mic = self.resolve_device(fresh['inputs'], body, 'mic')
            output = self.resolve_device(fresh['outputs'], body, 'output')
            self.validate_devices(body | {'mic': mic, 'output': output, 'hear': True})
            load_key()
            self.testing = True
            self.test_cancel.clear()
            self.error = ''
            self.status = 'مردانہ آواز کا مختصر نمونہ بن رہا ہے…'
        def work():
            try:
                parts, frames = [], 0
                for audio, _ in speak_stream('Hello Bilal. Your project will take seven days.'):
                    if self.test_cancel.is_set():
                        return
                    parts.append(audio)
                    frames += len(audio)
                    if frames > 24000 * 15:
                        raise ServiceError('نمونہ غیر متوقع طور پر لمبا ہے؛ آواز روک دی۔')
                if self.test_cancel.is_set():
                    return
                audio = np.concatenate(parts) * .8
                rate = int(sd.query_devices(output)['default_samplerate'])
                converted = Resampler(24000, rate).process(audio)
                # Entire short sample is buffered, so network jitter cannot cut it.
                with sd.OutputStream(device=output, samplerate=rate, channels=1, dtype='float32', latency='high') as stream:
                    for position in range(0, len(converted), rate // 10):
                        if self.test_cancel.is_set():
                            return
                        stream.write(converted[position:position + rate // 10].reshape(-1, 1))
                with self.lock:
                    self.status = 'نمونہ ایئربڈز پر چلایا گیا — سن کر معیار بتائیں۔'
            except ServiceError as error:
                with self.lock:
                    self.error = str(error)
                    if error.retry_after:
                        self.next_start_at = time.monotonic() + error.retry_after
            except Exception:
                with self.lock:
                    self.error = 'ایئربڈز پر آواز نہیں چل سکی؛ کنکشن اور ڈیوائس منتخب کرکے دوبارہ آزمائیں۔'
            finally:
                with self.lock:
                    self.testing = False
        threading.Thread(target=work, daemon=True).start()


def make_server(state, port=PORT):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never persist speech, headers or secrets in HTTP logs.

        def reply(self, code, data, content_type='application/json; charset=utf-8'):
            if isinstance(data, (dict, list)):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            if isinstance(data, str):
                data = data.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(data)

        def trusted(self, authenticated=False):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != origin.removeprefix('http://'):
                return False
            if self.headers.get('Origin') not in (None, origin):
                return False
            if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
                return False
            return not authenticated or secrets.compare_digest(self.headers.get('X-App-Token', ''), state.token)

        def do_GET(self):
            if not self.trusted():
                return self.reply(403, {'error': 'Local access only'})
            if self.path == '/health':
                return self.reply(200, {'app': 'bilal-voice-translator', 'version': '0.7.0'})
            if self.path.startswith('/api/'):
                if not self.trusted(True):
                    return self.reply(403, {'error': 'Open the app from its shortcut'})
                if self.path == '/api/state':
                    return self.reply(200, state.snapshot())
                if self.path == '/api/devices':
                    try:
                        return self.reply(200, state.devices())
                    except Exception:
                        return self.reply(503, {'error': 'آڈیو ڈیوائسز دستیاب نہیں؛ ونڈو بند کرکے دوبارہ کھولیں۔'})
                return self.reply(404, {})
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8'), '/icon.svg': ('icon.svg', 'image/svg+xml')}
            if self.path not in files:
                return self.reply(404, {})
            name, mime = files[self.path]
            content = (ROOT / 'web' / name).read_text(encoding='utf-8')
            if name == 'index.html':
                content = content.replace('__APP_TOKEN__', state.token)
            self.reply(200, content, mime)

        def do_POST(self):
            if not self.trusted(True):
                return self.reply(403, {'error': 'Request refused'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 <= size <= 2048 or self.headers.get('Content-Type') != 'application/json':
                    return self.reply(400, {'error': 'Invalid request'})
                body = json.loads(self.rfile.read(size) or b'{}')
                if not isinstance(body, dict):
                    raise ValueError('درخواست درست نہیں۔')
                if self.path == '/api/start':
                    state.start(body)
                elif self.path == '/api/key':
                    state.save_key(body.get('key'))
                elif self.path == '/api/stop':
                    state.stop()
                elif self.path == '/api/mute':
                    with state.lock:
                        for key in ('hear', 'muted'):
                            if key in body and type(body[key]) is not bool:
                                raise ValueError('ترتیب درست نہیں۔')
                        if 'hear' in body:
                            if body['hear'] and state.session:
                                state.validate_devices({'mic': state.session.mic, 'output': state.session.output, 'hear': True})
                            state.hear = body['hear']
                            if state.session:
                                state.session.mute_audio(not state.hear)
                        if 'muted' in body:
                            state.muted = body['muted']
                            if state.session:
                                state.session.mute_mic(state.muted)
                elif self.path == '/api/test':
                    state.test_voice(body)
                elif self.path == '/api/clear':
                    with state.lock:
                        state.require_idle()
                        state.original = state.translation = state.error = state.latency = ''
                elif self.path == '/api/refresh':
                    state.refresh_devices()
                    with state.lock:
                        if time.monotonic() >= state.next_start_at:
                            state.error = ''
                        state.status = 'فہرست تازہ ہے۔ ڈیوائس منتخب کرکے Start کریں۔'
                elif self.path == '/api/shutdown':
                    state.stop()
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                else:
                    return self.reply(404, {})
                self.reply(200, {'ok': True})
            except (ValueError, ServiceError) as error:
                self.reply(400, {'error': str(error)})
            except Exception:
                self.reply(503, {'error': 'آڈیو ڈیوائس یا رابطہ دستیاب نہیں؛ کنکشن چیک کرکے دوبارہ آزمائیں۔'})
    server = LocalServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def open_window(url):
    for base in (os.environ.get('PROGRAMFILES(X86)', ''), os.environ.get('PROGRAMFILES', ''), os.environ.get('LOCALAPPDATA', '')):
        edge = Path(base) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe'
        if edge.is_file():
            subprocess.Popen([str(edge), '--app=' + url, '--window-size=1180,820'])
            return
    webbrowser.open(url)


def main():
    url = f'http://127.0.0.1:{PORT}'
    state = AppState()
    try:
        server = make_server(state)
    except OSError:
        try:
            with urllib.request.urlopen(url + '/health', timeout=2) as response:
                if json.load(response).get('app') == 'bilal-voice-translator':
                    open_window(url)
        except Exception:
            import tkinter.messagebox
            tkinter.messagebox.showerror('Voice Translator', 'Port 8765 مصروف ہے؛ دوسری local app بند کرکے دوبارہ کھولیں۔')
        return
    def watchdog():
        while True:
            time.sleep(3)
            if (state.active or state.testing) and time.monotonic() - state.last_seen > 30:
                state.stop()
    threading.Thread(target=watchdog, daemon=True).start()
    open_window(url)
    try:
        server.serve_forever()
    finally:
        state.stop()
        server.server_close()


if __name__ == '__main__':
    main()
