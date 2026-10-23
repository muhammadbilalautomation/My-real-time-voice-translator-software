"""Offline GUI safety checks; never record or play audio."""
import tkinter as tk
import unittest

from translator_demo import TranslatorDemo


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = TranslatorDemo(self.root)

    def tearDown(self):
        self.app.close()

    def test_stop_discards_late_network_result(self):
        self.app.mode = "processing"
        old_generation = self.app.generation
        self.app.stop()
        self.app.results.put((old_generation, "translation", {
            "status": "ok", "transcript": "old", "translation": "old", "issue": ""}, 1))
        self.app.poll()
        self.assertIsNone(self.app.translated)
        self.assertEqual(self.app.output.get("1.0", "end").strip(), "")

    def test_unclear_result_cannot_be_spoken(self):
        self.app.results.put((self.app.generation, "translation", {
            "status": "unclear", "transcript": "price...", "translation": "", "issue": "دوبارہ کہیں"}, 1))
        self.app.poll()
        self.assertEqual(str(self.app.speak_button["state"]), "disabled")
        self.assertIn("دوبارہ", self.app.issue.get())

    def test_ready_result_is_reviewed_before_speaking(self):
        self.app.results.put((self.app.generation, "translation", {
            "status": "ok", "transcript": "ہاں", "translation": "Yes.", "issue": ""}, 1))
        self.app.poll()
        self.assertEqual(self.app.mode, "idle")
        self.assertEqual(str(self.app.speak_button["state"]), "normal")
        self.assertIsNone(self.app.generated_audio)

    def test_all_controls_fit_small_laptop_window(self):
        self.root.deiconify()
        self.root.geometry("900x680")
        self.root.update()
        panel = self.root.winfo_children()[1]
        self.assertTrue(all(widget.winfo_ismapped() for widget in panel.winfo_children()))
        self.assertLessEqual(panel.winfo_y() + panel.winfo_height(), self.root.winfo_height())


if __name__ == "__main__":
    unittest.main()
