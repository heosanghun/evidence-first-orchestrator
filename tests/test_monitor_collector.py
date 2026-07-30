from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monitor import collector


class MonitorCollectorTests(unittest.TestCase):
    def test_parse_tqdm_progress_uses_last_complete_counter(self) -> None:
        parsed = collector.parse_progress(
            " 41%|████ | 410/1000 [00:20<00:30, 19.2it/s]\n"
            " 42%|████ | 420/1000 [00:21<00:29, 19.3it/s]"
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["current"], 420)
        self.assertEqual(parsed["total"], 1000)
        self.assertEqual(parsed["percent"], 42)
        self.assertEqual(parsed["eta"], "00:29")

    def test_parse_generic_counter_does_not_invent_eta(self) -> None:
        parsed = collector.parse_progress("Stage 2 step 5,537/75,012 loss=0.14")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["current"], 5537)
        self.assertEqual(parsed["total"], 75012)
        self.assertAlmostEqual(parsed["percent"], 7.3814, places=3)
        self.assertIsNone(parsed["eta"])

    @patch("monitor.collector.run_command")
    def test_query_gpus_parses_all_rows_and_keeps_uuid_internal(
        self, run_command_mock
    ) -> None:
        run_command_mock.return_value = collector.CommandResult(
            0,
            "0, GPU-one, NVIDIA RTX A6000, 91, 39000, 49140, 72, 281\n"
            "1, GPU-two, NVIDIA RTX A6000, 0, 22, 49140, 35, 49\n",
            "",
        )
        gpus, alerts = collector.query_gpus()
        self.assertEqual(alerts, [])
        self.assertEqual([gpu["index"] for gpu in gpus], [0, 1])
        self.assertEqual(gpus[0]["_uuid"], "GPU-one")
        self.assertEqual(gpus[0]["utilization_percent"], 91)
        self.assertNotIn("_uuid", collector.strip_internal_fields(gpus)[0])

    def test_task_projection_reports_workflow_phase_not_metric(self) -> None:
        task = collector.task_to_view(
            {
                "id": "P1b-3",
                "title": "Preregister statistics",
                "owner": "codex",
                "state": "submitted",
                "updated_at": "2026-07-30T01:00:00Z",
            }
        )
        self.assertEqual(task["progress_percent"], 80)
        self.assertEqual(task["next"], "독립 검증")
        self.assertEqual(collector.workflow_progress([task]), 80)

    def test_history_is_bounded_and_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "history.json"
            history = [{"at": str(index), "gpus": []} for index in range(100)]
            collector.save_history(path, history)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(stored), collector.HISTORY_LIMIT)
            self.assertEqual(stored[0]["at"], "40")

    @patch("monitor.collector.urllib.request.urlopen")
    @patch("monitor.collector.time.time", return_value=1000)
    def test_submit_hmac_covers_timestamp_and_exact_body(
        self, _time_mock, urlopen_mock
    ) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return b'{"ok":true}'

        urlopen_mock.return_value = Response()
        snapshot = {"schema_version": "1.0", "generated_at": "now"}
        result = collector.submit_snapshot(
            "https://example.test/api/snapshot",
            "secret",
            snapshot,
        )
        self.assertTrue(result["ok"])
        request = urlopen_mock.call_args.args[0]
        expected = hmac.new(
            b"secret",
            b"1000." + request.data,
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(request.headers["X-efo-signature"], f"sha256={expected}")
        self.assertNotIn(b"secret", request.data)


if __name__ == "__main__":
    unittest.main()
