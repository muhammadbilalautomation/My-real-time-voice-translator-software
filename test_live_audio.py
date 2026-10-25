"""Offline streaming safety tests; no real microphone, playback or API calls."""
import tkinter as tk
import asyncio
import base64
import json
import time
import unittest
from unittest.mock import patch

import numpy as np
from gemini_client import ServiceError
from live_audio import DEFAULT_VOICE, LiveSession, PlaybackBuffer, Resampler, TextChunker, live_setup
from live_demo import LiveDemo


class StreamingTests(unittest.TestCase):
    def make_session(self):
        with patch("live_audio.sd.query_devices", return_value={"default_samplerate": 48000}):
            session = LiveSession(0, 1, "en", audio_enabled=True)
        session.started = time.monotonic()
        return session

    def test_sentence_chunks_preserve_words_and_decimal_amounts(self):
        chunker = TextChunker()
        self.assertEqual(chunker.feed("Your proj"), [])
        self.assertEqual(chunker.feed("ect costs 500.50 dollars."), ["Your project costs 500.50 dollars."])
        self.assertEqual(chunker.feed(" Done", finished=True), ["Done"])

    def test_uncontrolled_native_audio_never_reaches_playback(self):
        session = self.make_session()
        class Socket:
            count = 0
            async def recv(inner):
                inner.count += 1
                if inner.count > 1:
                    session.stop_event.set()
                    return "{}"
                return json.dumps({"serverContent": {"modelTurn": {"parts": [{"inlineData": {
                    "data": base64.b64encode(bytes(4800)).decode(), "mimeType": "audio/pcm;rate=24000"}}]}}})
        asyncio.run(session.receive(Socket()))
        self.assertEqual(session.playback.frames, 0)

    def test_every_speech_job_uses_same_selected_male_voice(self):
        session = self.make_session()
        async def scenario():
            session.speech_jobs = asyncio.Queue()
            session.speech_ready = asyncio.Queue()
            session.queue_speech("Hello.")
            session.queue_speech("The price is 500 dollars.")
            worker = asyncio.create_task(session.synthesize())
            first = await asyncio.wait_for(session.speech_ready.get(), 2)
            second = await asyncio.wait_for(session.speech_ready.get(), 2)
            for item in (first, second):
                await asyncio.wait_for(asyncio.to_thread(item[2].get), 2)
            session.stop()
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
        with patch("live_audio.speak_stream", return_value=[(np.zeros((100, 1), dtype="float32"), 24000)]) as speaker:
            asyncio.run(scenario())
        self.assertEqual(speaker.call_count, 2)
        self.assertTrue(all(call.kwargs["voice"] == DEFAULT_VOICE for call in speaker.call_args_list))

    def test_urdu_text_cannot_be_queued_for_english_voice(self):
        session = self.make_session()
        with self.assertRaises(ServiceError):
            session.queue_speech("میرا نام بلال ہے۔")

    def test_resampling_keeps_continuity_across_blocks(self):
        rate = 48000
        audio = (0.1 * np.sin(2 * np.pi * 440 * np.arange(rate) / rate)).astype("float32")
        whole = Resampler(rate).process(audio)
        converter = Resampler(rate)
        blocks = np.concatenate([converter.process(block) for block in np.split(audio, 10)])
        self.assertEqual(len(blocks), 16000)
        np.testing.assert_allclose(whole, blocks, atol=1e-5)

    def test_tts_playback_preserves_waveform_across_network_chunks(self):
        session = self.make_session()
        source = (.15 * np.sin(2 * np.pi * 730 * np.arange(4800) / 24000)).astype('float32')
        rendered = []
        async def scenario():
            import queue
            chunks = queue.Queue()
            for part in np.array_split(source, 17):
                chunks.put(('audio', part.reshape(-1, 1), 24000))
            chunks.put(('end', None, None))
            session.speech_ready = asyncio.Queue()
            await session.speech_ready.put((0, 0, chunks, time.monotonic()))
            worker = asyncio.create_task(session.render())
            await asyncio.sleep(.05)
            session.stop()
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
        with patch.object(session.playback, 'append', side_effect=lambda data: rendered.append(data.copy())):
            asyncio.run(scenario())
        expected = Resampler(24000, 48000).process(source * .8)
        np.testing.assert_allclose(np.concatenate(rendered), expected, atol=1e-5)

    def test_stop_buffer_clears_all_old_audio(self):
        buffer = PlaybackBuffer(24000)
        buffer.append(np.ones(2400, dtype="float32"))
        buffer.clear()
        output = np.ones((100, 1), dtype="float32")
        buffer.read(output, 100, None, None)
        self.assertFalse(output.any())

    def test_disabled_buffer_rejects_late_audio_after_stop(self):
        buffer = PlaybackBuffer(24000)
        buffer.enable(False)
        buffer.append(np.ones(100, dtype="float32"))
        self.assertEqual(buffer.frames, 0)

    def test_backlog_fails_instead_of_silently_dropping_words(self):
        buffer = PlaybackBuffer(24000)
        with self.assertRaises(ServiceError):
            buffer.append(np.ones(24000 * 6, dtype="float32"))

    def test_partial_read_has_correct_order(self):
        buffer = PlaybackBuffer(24000)
        buffer.append(np.arange(10, dtype="float32"))
        output = np.zeros((4, 1), dtype="float32")
        buffer.read(output, 4, None, None)
        np.testing.assert_array_equal(output[:, 0], np.arange(4))
        buffer.read(output, 4, None, None)
        np.testing.assert_array_equal(output[:, 0], np.arange(4, 8))

    def test_setup_never_echoes_target_language(self):
        setup = live_setup("en")["setup"]
        self.assertFalse(setup["generationConfig"]["translationConfig"]["echoTargetLanguage"])
        self.assertIn("inputAudioTranscription", setup)

    def test_mic_mute_clears_unsent_audio(self):
        with patch("live_audio.sd.query_devices", return_value={"default_samplerate": 48000}):
            session = LiveSession(0, 1, "en")
        session.capture_queue.put(np.ones((4800, 1), dtype="float32"))
        session.mute_mic(True)
        self.assertTrue(session.capture_queue.empty())
        session.capture(np.ones((4800, 1), dtype="float32"), 4800, None, None)
        self.assertFalse(session.capture_queue.get().any())

    def test_ui_never_starts_recording_and_blocks_speaker_output(self):
        root = tk.Tk()
        root.withdraw()
        app = LiveDemo(root)
        try:
            self.assertIsNone(app.session)
            self.assertFalse(app.hear.get())
            speaker = next(label for label in app.outputs if "speakers" in label.lower())
            app.speaker.set(speaker)
            app.hear.set(True)
            app.change_audio()
            self.assertFalse(app.hear.get())
        finally:
            app.close()


if __name__ == "__main__":
    unittest.main()
