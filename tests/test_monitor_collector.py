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

    def test_signed_alias_projects_transport_work_to_display_agent(self) -> None:
        status = {
            "tasks": [
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
                        "author": "claude",
                        "author_identity": {
                            "actor": "claude",
                            "control_principal": "claude-a-control",
                        },
                    },
                }
            ],
            "status": {"ledger": {"valid": True, "event_count": 20}},
        }
        registered = [
            {
                "id": "claude",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "claude-a-control",
                    "model_family": "anthropic-claude",
                    "alias_of": None,
                    "alias_chain": [],
                },
            },
            {
                "id": "claude-a",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "claude-a-control",
                    "model_family": "anthropic-claude",
                    "alias_of": "claude",
                    "alias_chain": ["claude"],
                },
            },
        ]
        config = {
            "agents": [
                {
                    "id": "claude-a",
                    "efo_id": "claude-a",
                    "name": "Claude A",
                    "role": "reviewer",
                }
            ]
        }
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            agents, tasks, ledger, alerts, _activity = collector.collect_efo(config)

        self.assertTrue(ledger["valid"])
        self.assertEqual(alerts, [])
        self.assertEqual(tasks[0]["owner"], "claude")
        self.assertEqual(tasks[0]["state"], "pending")
        self.assertEqual(tasks[0]["external_phase"], "working")
        self.assertEqual(agents[0]["current_task_id"], "P1b-8")
        self.assertEqual(agents[0]["current"], "Freeze run identity")
        self.assertEqual(agents[0]["state"], "working")
        self.assertEqual(agents[0]["progress_percent"], 40)
        self.assertEqual(agents[0]["status_source"], "transport_assertion")
        self.assertEqual(agents[0]["status_badge"], "운반자 보고")

    def test_unattested_or_malformed_alias_does_not_merge(self) -> None:
        malformed_agents = [
            {
                "id": "claude",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "claude-a-control",
                    "model_family": "anthropic-claude",
                    "alias_of": None,
                    "alias_chain": [],
                },
            },
            {
                "id": "claude-a",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "claude-a-control",
                    "model_family": "anthropic-claude",
                    "alias_of": "missing-agent",
                    "alias_chain": ["missing-agent"],
                },
            },
        ]
        groups = collector.resolve_signed_identity_groups(
            malformed_agents,
            ledger_valid=True,
        )
        self.assertEqual(groups["claude"], frozenset({"claude"}))
        self.assertNotIn("claude-a", groups)
        self.assertEqual(
            collector.resolve_signed_identity_groups(
                malformed_agents,
                ledger_valid=False,
            ),
            {},
        )
        cyclic = [
            {
                "id": "alias-a",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "shared-control",
                    "model_family": "family",
                    "alias_of": "alias-b",
                    "alias_chain": ["alias-b"],
                },
            },
            {
                "id": "alias-b",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "shared-control",
                    "model_family": "family",
                    "alias_of": "alias-a",
                    "alias_chain": ["alias-a"],
                },
            },
            {
                "id": "self-alias",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "self-control",
                    "model_family": "family",
                    "alias_of": "self-alias",
                    "alias_chain": ["self-alias"],
                },
            },
        ]
        self.assertEqual(
            collector.resolve_signed_identity_groups(
                cyclic,
                ledger_valid=True,
            ),
            {},
        )

    def test_invalid_ledger_cannot_assign_even_an_exact_owner(self) -> None:
        status = {
            "tasks": [
                {
                    "id": "UNTRUSTED",
                    "title": "Untrusted projection",
                    "owner": "codex",
                    "state": "running",
                    "updated_at": "2026-07-30T01:00:00Z",
                }
            ],
            "status": {"ledger": {"valid": False, "event_count": 20}},
        }
        registered = [{"id": "codex", "identity": None}]
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            agents, tasks, ledger, _alerts, activity = collector.collect_efo(
                {
                    "agents": [
                        {
                            "id": "codex",
                            "efo_id": "codex",
                            "name": "Codex",
                            "role": "worker",
                        }
                    ]
                }
            )
        self.assertFalse(ledger["valid"])
        self.assertEqual(tasks[0]["id"], "UNTRUSTED")
        self.assertIsNone(agents[0]["current_task_id"])
        self.assertEqual(agents[0]["status_source"], "none")
        self.assertEqual(agents[0]["progress_percent"], 0)
        self.assertEqual(activity, [])

    def test_unsigned_profile_state_cannot_invent_current_work(self) -> None:
        status = {
            "tasks": [],
            "status": {"ledger": {"valid": True, "event_count": 20}},
        }
        registered = [{"id": "codex", "identity": None}]
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            agents, _tasks, _ledger, _alerts, _activity = collector.collect_efo(
                {
                    "agents": [
                        {
                            "id": "codex",
                            "efo_id": "codex",
                            "name": "Codex",
                            "role": "worker",
                            "state": "working",
                        }
                    ]
                }
            )
        self.assertEqual(agents[0]["state"], "waiting")
        self.assertIsNone(agents[0]["current_task_id"])
        self.assertEqual(agents[0]["status_source"], "none")
        self.assertEqual(agents[0]["progress_percent"], 0)

    def test_newer_verified_activity_outranks_old_blocked_task(self) -> None:
        status = {
            "tasks": [
                {
                    "id": "DRYRUN",
                    "title": "Old blocked probe",
                    "owner": "codex",
                    "state": "blocked",
                    "updated_at": "2026-07-29T01:00:00Z",
                },
                {
                    "id": "EFO-3",
                    "title": "Monitor task projection",
                    "owner": "claude-b",
                    "state": "verified",
                    "updated_at": "2026-07-30T01:00:00Z",
                    "verification": {
                        "actor": "codex-verifier",
                        "identity": {
                            "actor": "codex-verifier",
                            "control_principal": "codex-meta-control",
                        },
                    },
                },
                {
                    "id": "P1b-4",
                    "title": "Old Claude B block",
                    "owner": "claude-b",
                    "state": "blocked",
                    "updated_at": "2026-07-28T01:00:00Z",
                },
                {
                    "id": "REVIEW-1",
                    "title": "New Claude B verification",
                    "owner": "claude",
                    "state": "verified",
                    "updated_at": "2026-07-30T02:00:00Z",
                    "verification": {
                        "actor": "claude-b",
                        "identity": {
                            "actor": "claude-b",
                            "control_principal": "claude-b-control",
                        },
                    },
                },
            ],
            "status": {"ledger": {"valid": True, "event_count": 30}},
        }
        registered = [
            {
                "id": "codex",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "codex-meta-control",
                    "model_family": "openai-codex",
                    "alias_of": None,
                    "alias_chain": [],
                },
            },
            {
                "id": "codex-verifier",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "codex-meta-control",
                    "model_family": "openai-codex",
                    "alias_of": "codex",
                    "alias_chain": ["codex"],
                },
            },
            {
                "id": "claude-b",
                "identity": {
                    "schema_version": 1,
                    "control_principal": "claude-b-control",
                    "model_family": "anthropic-claude",
                    "alias_of": None,
                    "alias_chain": [],
                },
            },
        ]
        config = {
            "agents": [
                {
                    "id": "codex",
                    "efo_id": "codex",
                    "name": "Codex",
                    "role": "worker",
                },
                {
                    "id": "claude-b",
                    "efo_id": "claude-b",
                    "name": "Claude B",
                    "role": "verifier",
                },
            ]
        }
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            agents, tasks, _ledger, _alerts, _activity = collector.collect_efo(
                config
            )

        self.assertEqual(agents[0]["current_task_id"], "EFO-3")
        self.assertEqual(agents[0]["state"], "waiting")
        self.assertEqual(agents[0]["progress_percent"], 100)
        self.assertEqual(agents[1]["current_task_id"], "REVIEW-1")
        self.assertEqual(agents[1]["state"], "waiting")
        self.assertEqual(
            {task["id"] for task in tasks},
            {"DRYRUN", "EFO-3", "P1b-4", "REVIEW-1"},
        )
        self.assertEqual(
            next(task for task in tasks if task["id"] == "DRYRUN")["state"],
            "blocked",
        )
        self.assertEqual(
            next(task for task in tasks if task["id"] == "P1b-4")["state"],
            "blocked",
        )

    def test_live_task_outranks_newer_terminal_and_ties_use_task_id(self) -> None:
        live = {
            "id": "LIVE",
            "state": "pending",
            "external_phase": None,
            "updated_at": "2026-07-29T01:00:00Z",
        }
        terminal = {
            "id": "DONE",
            "state": "verified",
            "external_phase": None,
            "updated_at": "2026-07-30T01:00:00Z",
        }
        self.assertEqual(
            collector.choose_agent_task([terminal, live])["id"],
            "LIVE",
        )
        same_time = "2026-07-30T02:00:00Z"
        choices = [
            {
                "id": "TASK-B",
                "state": "verified",
                "external_phase": None,
                "updated_at": same_time,
            },
            {
                "id": "TASK-A",
                "state": "verified",
                "external_phase": None,
                "updated_at": same_time,
            },
        ]
        self.assertEqual(
            collector.choose_agent_task(choices)["id"],
            "TASK-A",
        )
        self.assertEqual(
            collector.agent_state(
                {
                    "state": "rejected",
                    "external_phase": None,
                    "lease_active": False,
                }
            ),
            "blocked",
        )

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
