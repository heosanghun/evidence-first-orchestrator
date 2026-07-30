from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
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

    def test_transport_assertion_overlays_pending_without_changing_state(self) -> None:
        task = collector.task_to_view(
            {
                "id": "P1b-8",
                "title": "Freeze run identity",
                "owner": "claude",
                "state": "pending",
                "lease": None,
                "updated_at": "2026-07-30T01:00:00Z",
                "external_status": {
                    "phase": "working",
                    "reported_at": "2026-07-30T02:00:00Z",
                    "reference": "private-dispatch-reference",
                    "note": "private transport note",
                    "transport_identity": {"control_principal": "private-control"},
                },
            }
        )
        self.assertEqual(task["state"], "pending")
        self.assertEqual(task["canonical_state"], "pending")
        self.assertEqual(task["external_phase"], "working")
        self.assertEqual(task["status_source"], "transport_assertion")
        self.assertEqual(task["status_badge"], "운반자 보고")
        self.assertEqual(task["progress_percent"], 40)
        self.assertEqual(task["next"], "외부 구현 결과 대기")
        self.assertEqual(task["updated_at"], "2026-07-30T02:00:00Z")
        self.assertEqual(collector.agent_state(task), "working")
        self.assertEqual(collector.workflow_progress([task]), 40)
        serialized = json.dumps(task, ensure_ascii=False)
        self.assertNotIn("private-dispatch-reference", serialized)
        self.assertNotIn("private transport note", serialized)
        self.assertNotIn("private-control", serialized)

    def test_transport_reported_block_is_not_a_canonical_block(self) -> None:
        task = collector.task_to_view(
            {
                "id": "P1b-8",
                "title": "Freeze run identity",
                "owner": "claude",
                "state": "pending",
                "lease": None,
                "external_status": {
                    "phase": "blocked",
                    "reported_at": "2026-07-30T02:00:00Z",
                },
            }
        )
        self.assertEqual(task["state"], "pending")
        self.assertEqual(task["external_phase"], "blocked")
        self.assertEqual(task["progress_percent"], 10)
        self.assertEqual(collector.agent_state(task), "blocked")

    def test_running_task_without_lease_is_reported_as_blocked(self) -> None:
        task = collector.task_to_view(
            {
                "id": "DRYRUN",
                "title": "flow smoke test",
                "owner": "codex",
                "state": "running",
                "lease": None,
            }
        )
        self.assertFalse(task["lease_active"])
        self.assertEqual(task["next"], "임대 만료 상태 확인")
        self.assertEqual(collector.agent_state(task), "blocked")

    def test_expired_lease_is_not_active(self) -> None:
        now = datetime(2026, 7, 30, tzinfo=timezone.utc)
        self.assertFalse(
            collector.lease_is_active(
                {"expires_at": "2026-07-29T07:00:08Z"},
                now=now,
            )
        )
        self.assertTrue(
            collector.lease_is_active(
                {"expires_at": "2026-07-31T07:00:08Z"},
                now=now,
            )
        )

    @patch("monitor.collector.read_uptime", return_value=10)
    @patch("monitor.collector.read_meminfo", return_value={})
    @patch("monitor.collector.shutil.disk_usage")
    def test_disk_pressure_uses_user_available_capacity(
        self,
        disk_usage_mock,
        _meminfo_mock,
        _uptime_mock,
    ) -> None:
        gib = 1024**3
        disk_usage_mock.return_value = SimpleNamespace(
            total=100 * gib,
            used=90 * gib,
            free=5 * gib,
        )
        system = collector.collect_system({"disk_path": "/"})
        self.assertEqual(system["disk"]["percent"], 94.74)

    def test_history_is_bounded_and_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "history.json"
            history = [{"at": str(index), "gpus": []} for index in range(100)]
            collector.save_history(path, history)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(stored), collector.HISTORY_LIMIT)
            self.assertEqual(stored[0]["at"], "40")

    def test_activity_projection_excludes_ledger_payload_and_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "sequence": 1,
                        "timestamp": "2026-07-30T01:00:00Z",
                        "actor": "codex",
                        "action": "task.submitted",
                        "task_id": "T-1",
                        "payload": {
                            "task": {
                                "id": "T-1",
                                "title": "Evidence bundle",
                                "description": "must stay private",
                            },
                            "password": "must-not-leave-server",
                        },
                        "event_hash": "private-hash",
                        "signature": "private-signature",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            activity = collector.collect_activity(
                {
                    "efo_ledger_file": str(ledger),
                    "activity_actor_aliases": {"codex": "Codex"},
                },
                directory,
                [],
            )
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0]["actor_name"], "Codex")
        self.assertEqual(activity[0]["label"], "증거 제출")
        self.assertEqual(activity[0]["title"], "Evidence bundle")
        serialized = json.dumps(activity, ensure_ascii=False)
        self.assertNotIn("must-not-leave-server", serialized)
        self.assertNotIn("private-signature", serialized)
        self.assertNotIn("description", serialized)

    def test_proxy_status_event_is_visible_as_transport_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "sequence": 2,
                        "timestamp": "2026-07-30T02:00:00Z",
                        "actor": "antigravity",
                        "action": "task.proxy_status_reported",
                        "task_id": "P1b-8",
                        "payload": {
                            "task": {
                                "id": "P1b-8",
                                "title": "Freeze run identity",
                            },
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            activity = collector.collect_activity(
                {"efo_ledger_file": str(ledger)},
                directory,
                [],
            )
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0]["label"], "외부 진행상태 보고")
        self.assertEqual(activity[0]["category"], "work")
        self.assertEqual(activity[0]["task_id"], "P1b-8")

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
