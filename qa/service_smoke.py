"""Opt-in cloud smoke test using synthetic speech; no microphone or speakers.

Run from the project root with .venv Python and --target en or ur. This consumes
Gemini free-tier quota. No audio files, keys, headers or human speech are logged.
"""
import argparse
import asyncio
import base64
import io
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from gemini_client import ServiceError, numeric_values, speak_stream
from live_audio import LiveSession, Resampler, explain_live_error


class NoHardware:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def source_audio(target):
    if target == 'en':
        text = 'میرا نام بلال ہے۔ آپ کے پروجیکٹ پر سات دن لگیں گے۔'
        parts = [part for part, rate in speak_stream(text)]
        return text, np.concatenate(parts)[:, 0]
    text = 'Hello Bilal. Your project will take seven days.'
    # The installed Windows voice creates a synthetic source, in RAM only.
    script = ("Add-Type -AssemblyName System.Speech; "
              "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$m=New-Object IO.MemoryStream; $s.SetOutputToWaveStream($m); "
              "$s.Speak('Hello Bilal. Your project will take seven days.'); "
              "[Console]::Write([Convert]::ToBase64String($m.ToArray())); "
              "$s.Dispose(); $m.Dispose()")
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
                            capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise ServiceError('Installed Windows synthetic test voice unavailable.')
    with wave.open(io.BytesIO(base64.b64decode(result.stdout)), 'rb') as stream:
        rate = stream.getframerate()
        data = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').astype('float32') / 32768
    return text, Resampler(rate, 24000).process(data)


async def run_case(target, text, source):
    with patch('live_audio.sd.query_devices', return_value={'default_samplerate': 24000}), \
         patch('live_audio.sd.InputStream', NoHardware), patch('live_audio.sd.OutputStream', NoHardware):
        session = LiveSession(0, 1, target, audio_enabled=True)
        task = asyncio.create_task(session.connect_and_stream())
        started, position, frames, translated = time.monotonic(), 0, 0, ''
        failure = None
        try:
            while time.monotonic() - started < 25 and not task.done():
                if session.started:
                    block = source[position:position + 2400]
                    position += 2400
                    if not len(block):
                        block = np.zeros(2400, dtype='float32')
                    session.capture(block.reshape(-1, 1), len(block), None, None)
                    output = np.zeros((2400, 1), dtype='float32')
                    session.playback.read(output, 2400, None, None)
                    if output.any():
                        frames += len(output)
                while not session.events.empty():
                    kind, message = session.events.get_nowait()
                    if kind == 'translation':
                        translated += message
                    elif kind == 'latency':
                        print(message, flush=True)
                await asyncio.sleep(.1)
            if task.done():
                try:
                    task.result()
                except Exception as error:
                    failure = explain_live_error(error, session.phase)
        finally:
            session.stop()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if failure:
            print('FAILED:', str(failure), flush=True)
            return False
        print('Synthetic translation:', translated, flush=True)
        numbers_match = numeric_values(text) == numeric_values(translated)
        print('Voice output frames:', frames, 'Numbers preserved:', numbers_match, flush=True)
        print('Microphone/speaker opened: NO. Human voice quality still needs listening.', flush=True)
        return bool(frames and translated and numbers_match)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('en', 'ur'), required=True)
    args = parser.parse_args()
    try:
        text, source = source_audio(args.target)
        success = asyncio.run(run_case(args.target, text, source))
    except ServiceError as error:
        print('FAILED:', str(error))
        success = False
    except Exception:
        print('Synthetic test could not complete; no raw errors or credentials displayed.')
        success = False
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
