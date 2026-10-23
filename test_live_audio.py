"""Offline streaming safety tests; no real microphone, playback or API calls."""
import tkinter as tk
import unittest
from unittest.mock import patch

import numpy as np
from gemini_client import ServiceError
from live_audio import LiveSession, PlaybackBuffer, Resampler, live_setup
from live_demo import LiveDemo


class StreamingTests(unittest.TestCase):
    def test_resampling_keeps_continuity_across_blocks(self):
        rate = 48000
        audio = (0.1 * np.sin(2 * np.pi * 440 * np.arange(rate) / rate)).astype("float32")
        whole = Resampler(rate).process(audio)
        converter = Resampler(rate)
        blocks = np.concatenate([converter.process(block) for block in np.split(audio, 10)])
        self.assertEqual(len(blocks), 16000)
        np.testing.assert_allclose(whole, blocks, atol=1e-5)

    def test_stop_buffer_clears_all_old_audio(self):
        buffer = PlaybackBuffer(24000)
        buffer.append(np.ones(2400, dtype="float32"))
        buffer.clear()
        output = np.ones((100, 1), dtype="float32")
        buffer.read(output, 100, None, None)
        self.assertFalse(output.any())

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
