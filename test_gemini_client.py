"""Offline checks: never use a real key, microphone, network, or speaker."""
import unittest
from unittest.mock import patch
import json
import io
from pathlib import Path
import tempfile
import urllib.error
import numpy as np
import gemini_client as client
from audio_test import prepare_playback


def response(**result):
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}]}


class SafetyTests(unittest.TestCase):
    def test_silence_is_not_sent(self):
        with patch.object(client, "request") as request:
            result = client.translate("Urdu", "English", audio=np.zeros((48000, 1)))
            self.assertEqual(result["status"], "unclear")
            self.assertEqual(result["translation"], "")
            request.assert_not_called()

    def test_clipped_audio_is_not_sent(self):
        with patch.object(client, "request") as request:
            result = client.translate("Urdu", "English", audio=np.ones((48000, 1)))
            self.assertEqual(result["status"], "unclear")
            request.assert_not_called()

    def test_wrong_language_withheld(self):
        with patch.object(client, "request", return_value=response(status="ok", transcript="ہاں", translation="جی ہاں", issue="")):
            result = client.translate("Urdu", "English", text="ہاں")
        self.assertEqual(result["translation"], "")
        self.assertEqual(result["status"], "unclear")

    def test_phonetic_english_is_not_accepted_as_urdu_translation(self):
        with patch.object(client, "request", return_value=response(status="ok",
                transcript="Hi, my name is Bilal. I am from Pakistan.",
                translation="ہائی، مائی نیم از بلال۔ آئی ایم فرام پاکستان۔", issue="")):
            result = client.translate("English", "Urdu", text="Hi, my name is Bilal. I am from Pakistan.")
        self.assertEqual(result["status"], "unclear")
        self.assertEqual(result["translation"], "")

    def test_changed_amount_needs_review(self):
        with patch.object(client, "request", return_value=response(status="ok", transcript="500 dollars", translation="قیمت 5000 ڈالر ہے", issue="")):
            result = client.translate("English", "Urdu", text="500 dollars")
        self.assertEqual(result["status"], "unclear")

    def test_spoken_urdu_days_and_numeric_price_are_equivalent(self):
        source = "السلام علیکم آپ کے پروجیکٹ پر سات دن لگیں گے اور اس کی قیمت ہوگی 500 ڈالر۔"
        with patch.object(client, "request", return_value=response(status="ok", transcript=source,
                translation="Peace be upon you. 7 days will be spent on your project and its price will be 500 dollars.", issue="")):
            result = client.translate("Urdu", "English", text=source)
        self.assertEqual(result["status"], "ok")

    def test_spoken_amounts_and_digit_scripts(self):
        self.assertEqual(client.numeric_values("پانچ سو ڈالر اور سات دن"), ["500", "7"])
        self.assertEqual(client.numeric_values("five hundred dollars and seven days"), ["500", "7"])
        self.assertEqual(client.numeric_values("۵۰۰ ڈالر"), ["500"])
        self.assertEqual(client.numeric_values("5,000 dollars"), ["5000"])
        self.assertEqual(client.numeric_values("a week"), ["1"])
        self.assertEqual(client.numeric_values("اسی پروجیکٹ کی قیمت 500 ڈالر ہے"), ["500"])

    def test_spoken_changed_amount_still_needs_review(self):
        with patch.object(client, "request", return_value=response(status="ok", transcript="قیمت پانچ سو ڈالر", translation="The price is 5000 dollars.", issue="")):
            result = client.translate("Urdu", "English", text="قیمت پانچ سو ڈالر")
        self.assertEqual(result["status"], "unclear")

    def test_incomplete_output_is_rejected(self):
        with patch.object(client, "request", return_value={"candidates": [{"finishReason": "MAX_TOKENS"}]}):
            with self.assertRaises(client.ServiceError):
                client.translate("Urdu", "English", text="ہاں")

    def test_cleanup_preserves_source_and_headroom(self):
        audio = np.linspace(-1, 1, 48000, dtype="float32")[:, None]
        original = audio.copy()
        clean = prepare_playback(audio, 48000)
        np.testing.assert_array_equal(audio, original)
        self.assertLessEqual(float(np.max(np.abs(clean))), 0.80001)

    def test_upload_is_smaller_without_changing_duration_or_source(self):
        rate = 48000
        audio = (0.2 * np.sin(2 * np.pi * 440 * np.arange(rate) / rate)).astype("float32")[:, None]
        original = audio.copy()
        upload, upload_rate = client.speech_upload(audio, rate)
        self.assertEqual(upload_rate, 16000)
        self.assertEqual(len(upload), 16000)
        self.assertAlmostEqual(float(np.max(np.abs(upload))), 0.2, places=2)
        np.testing.assert_array_equal(audio, original)
        self.assertLess(len(client.wav_bytes(upload, upload_rate)), len(client.wav_bytes(audio, rate)) / 2)

    def test_http_error_never_displays_key(self):
        secret = "not-a-real-key-for-offline-test"
        error = urllib.error.HTTPError("https://example.invalid/", 403, "Denied", {}, io.BytesIO(secret.encode()))
        with patch.object(client, "load_key", return_value=secret), patch.object(client.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(client.ServiceError) as caught:
                client.request("models")
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn("403", str(caught.exception))

    def test_voice_setup_uses_stateless_storage(self):
        sample = np.full((240000, 1), 0.01, dtype="float32")
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / "profile.json"
            with patch.object(client, "VOICE_PROFILE", profile), patch.object(client, "request", return_value={"key": "voicekey_offline_test_only"}) as request:
                client.replicate_voice(sample, 24000, sample, 24000)
                self.assertFalse(request.call_args.args[1]["store"])
                self.assertEqual(client.personal_voice(), "voicekey_offline_test_only")
                saved = json.loads(profile.read_text())
                self.assertNotIn("source_audio", saved)
                self.assertNotIn("consent_audio", saved)


if __name__ == "__main__":
    unittest.main()
