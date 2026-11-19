from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

import watcher


class ParserTests(unittest.TestCase):
    def test_real_page(self):
        page = Path(__file__).with_name("fixtures").joinpath("kpj.html").read_text()
        self.assertEqual(watcher.parse_count(page), 0)

    def test_entities_tags_and_whitespace(self):
        self.assertEqual(watcher.parse_count("<h3>Aktuelle&nbsp;Restpl&auml;tze: <b>12</b></h3>"), 12)

    def test_missing_or_invalid(self):
        for page in ("", "Restplätze: 1", "Aktuelle Restplätze: unbekannt", "Aktuelle Restplätze: -1", "Aktuelle Restplätze: 1.5", "Aktuelle Restplätze: 1 Aktuelle Restplätze: 2"):
            with self.subTest(page=page), self.assertRaises(ValueError):
                watcher.parse_count(page)

    def test_ignore_scripts(self):
        self.assertEqual(watcher.parse_count('<script>Aktuelle Restplätze: 99</script><p>Aktuelle Restplätze: 0</p>'), 0)


class StateTests(unittest.TestCase):
    def test_zero_and_positive_changes_and_reminder(self):
        zero, alert = watcher.next_state({}, 0, None, 100)
        self.assertFalse(alert)
        positive, alert = watcher.next_state(zero, 2, None, 200)
        self.assertTrue(alert)
        self.assertFalse(watcher.next_state(positive, 2, None, 300)[1])
        self.assertTrue(watcher.next_state(positive, 3, None, 300)[1])
        self.assertTrue(watcher.next_state(positive, 2, None, 200 + watcher.REMINDER_SECONDS)[1])

    def test_failure_dedupe_and_recovery(self):
        failure, alert = watcher.next_state({}, None, "fetch failed", 100)
        self.assertTrue(alert)
        self.assertFalse(watcher.next_state(failure, None, "fetch failed", 200)[1])
        switched, alert = watcher.next_state(failure, None, "parse failed", 220)
        self.assertFalse(alert)
        self.assertFalse(watcher.next_state(switched, None, "fetch failed", 240)[1])
        recovered, alert = watcher.next_state(failure, 0, None, 300)
        self.assertFalse(alert)
        self.assertTrue(watcher.next_state(recovered, None, "fetch failed", 400)[1])
        self.assertTrue(watcher.next_state(failure, 1, None, 300)[1])

    def test_dry_run_never_notifies_or_saves(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            with patch("sys.argv", ["watcher", "--dry-run", "--state", str(state)]), patch("watcher.fetch_page", return_value="Aktuelle Restplätze: 3"), patch("watcher.notify") as notify:
                watcher.main()
            notify.assert_not_called()
            self.assertFalse(state.exists())

    def test_failure_notification_and_dedupe(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            with patch("sys.argv", ["watcher", "--state", str(state)]), patch("watcher.fetch_page", side_effect=OSError("offline")), patch("watcher.notify") as notify:
                watcher.main()
                watcher.main()
            notify.assert_called_once_with("Page fetch failed", urgent=False)


if __name__ == "__main__":
    unittest.main()
