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
                            "schema_version": 1,
                            "control_principal": "claude-a-control",
                            "model_family": "anthropic-claude",
                            "alias_of": None,
                            "alias_chain": [],
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

    def test_unlinked_roots_with_shared_control_do_not_merge(self) -> None:
        registered = [
            {
                "id": agent_id,
                "identity": {
                    "schema_version": 1,
                    "control_principal": "shared-control",
                    "model_family": "shared-family",
                    "alias_of": None,
                    "alias_chain": [],
                },
            }
            for agent_id in ("claude-a", "claude-b")
        ]
        groups = collector.resolve_signed_identity_groups(
            registered,
            ledger_valid=True,
        )
        self.assertEqual(groups["claude-a"], frozenset({"claude-a"}))
        self.assertEqual(groups["claude-b"], frozenset({"claude-b"}))

        status = {
            "tasks": [
                {
                    "id": "CLAUDE-B-WORK",
                    "title": "Claude B work",
                    "owner": "claude-b",
                    "state": "running",
                    "lease": {
                        "expires_at": "2099-01-01T00:00:00Z",
                    },
                    "updated_at": "2026-07-30T01:00:00Z",
                }
            ],
            "status": {"ledger": {"valid": True, "event_count": 20}},
        }
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            agents, _tasks, _ledger, _alerts, _activity = collector.collect_efo(
                {
                    "agents": [
                        {
                            "id": "claude-a",
                            "efo_id": "claude-a",
                            "name": "Claude A",
                            "role": "verifier",
                        },
                        {
                            "id": "claude-b",
                            "efo_id": "claude-b",
                            "name": "Claude B",
                            "role": "worker",
                        },
                    ]
                }
            )
        self.assertIsNone(agents[0]["current_task_id"])
        self.assertEqual(agents[1]["current_task_id"], "CLAUDE-B-WORK")

    def test_incomplete_task_identity_cannot_assign_secondary_actor(self) -> None:
        status = {
            "tasks": [
                {
                    "id": "OTHER-WORK",
                    "title": "Other work",
                    "owner": "other",
                    "state": "verified",
                    "updated_at": "2026-07-30T01:00:00Z",
                    "verification": {
                        "actor": "claude-a",
                        "identity": {},
                    },
                }
            ],
            "status": {"ledger": {"valid": True, "event_count": 20}},
        }
        registered = [
            {
                "id": agent_id,
                "identity": {
                    "schema_version": 1,
                    "control_principal": f"{agent_id}-control",
                    "model_family": "test-family",
                    "alias_of": None,
                    "alias_chain": [],
                },
            }
            for agent_id in ("other", "claude-a")
        ]
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            agents, _tasks, _ledger, _alerts, _activity = collector.collect_efo(
                {
                    "agents": [
                        {
                            "id": "claude-a",
                            "efo_id": "claude-a",
                            "name": "Claude A",
                            "role": "verifier",
                        }
                    ]
                }
            )
        self.assertIsNone(agents[0]["current_task_id"])
        self.assertEqual(agents[0]["status_source"], "none")

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
                            "schema_version": 1,
                            "control_principal": "codex-meta-control",
                            "model_family": "openai-codex",
                            "alias_of": "codex",
                            "alias_chain": ["codex"],
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
                            "schema_version": 1,
                            "control_principal": "claude-b-control",
                            "model_family": "anthropic-claude",
                            "alias_of": None,
                            "alias_chain": [],
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

    def test_card_selection_is_recency_first_across_state_classes(self) -> None:
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
            "DONE",
        )
        self.assertEqual(
            collector.choose_agent_task(
                [terminal, {**live, "updated_at": "2026-07-31T01:00:00Z"}]
            )["id"],
            "LIVE",
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

    def test_card_state_class_follows_rendered_card_urgency(self) -> None:
        self.assertEqual(
            collector.card_state_class(
                {"state": "blocked", "external_phase": None}
            ),
            "attention",
        )
        self.assertEqual(
            collector.card_state_class(
                {"state": "pending", "external_phase": "blocked"}
            ),
            "attention",
        )
        self.assertEqual(
            collector.card_state_class(
                {
                    "state": "running",
                    "external_phase": None,
                    "lease_active": False,
                }
            ),
            "attention",
        )
        self.assertEqual(
            collector.card_state_class(
                {
                    "state": "running",
                    "external_phase": None,
                    "lease_active": True,
                }
            ),
            "live",
        )
        self.assertEqual(
            collector.card_state_class(
                {"state": "pending", "external_phase": "working"}
            ),
            "live",
        )
        self.assertEqual(
            collector.card_state_class(
                {"state": "verified", "external_phase": None}
            ),
            "terminal",
        )
        self.assertEqual(
            collector.CARD_CLASS_PRIORITY,
            {"attention": 0, "live": 1, "terminal": 2},
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


class FrozenKnownAnswerTests(unittest.TestCase):
    """Synthetic regressions for the seven EFO-5 frozen known answers."""

    @staticmethod
    def _registered(
        agent_id: str,
        *,
        principal: str | None = None,
        alias_of: str | None = None,
        alias_chain: tuple[str, ...] = (),
    ) -> dict[str, object]:
        return {
            "id": agent_id,
            "identity": {
                "schema_version": 1,
                "control_principal": principal or f"{agent_id}-control",
                "model_family": "test-family",
                "alias_of": alias_of,
                "alias_chain": list(alias_chain),
            },
        }

    @classmethod
    def _identity_snapshot(
        cls,
        agent_id: str,
        *,
        principal: str | None = None,
        alias_of: str | None = None,
        alias_chain: tuple[str, ...] = (),
    ) -> dict[str, object]:
        record = cls._registered(
            agent_id,
            principal=principal,
            alias_of=alias_of,
            alias_chain=alias_chain,
        )
        return {"actor": agent_id, **record["identity"]}

    @staticmethod
    def _profile(profile_id: str, efo_id: str | None = None) -> dict[str, str]:
        return {
            "id": profile_id,
            "efo_id": efo_id or profile_id,
            "name": profile_id.title(),
            "role": "worker",
        }

    @staticmethod
    def _collect(
        raw_tasks: list[dict[str, object]],
        registered: list[dict[str, object]],
        profiles: list[dict[str, str]],
    ):
        status = {
            "tasks": raw_tasks,
            "status": {"ledger": {"valid": True, "event_count": 30}},
        }
        with patch(
            "monitor.collector.parse_json_command",
            side_effect=[status, registered],
        ):
            return collector.collect_efo({"agents": profiles})

    def _assert_idle(self, card: dict[str, object]) -> None:
        self.assertIsNone(card["current_task_id"])
        self.assertEqual(card["state"], "waiting")
        self.assertEqual(card["status_source"], "none")
        self.assertIsNone(card["status_badge"])
        self.assertIsNone(card["updated_at"])
        self.assertEqual(card["progress_percent"], 0)
        self.assertEqual(card["current"], "배정 대기")
        self.assertEqual(card["next"], "오케스트레이터 지시 대기")

    def test_known_answer_1_unregistered_verifier_without_identity(self) -> None:
        raw_task = {
            "id": "OTHER-WORK",
            "title": "Other work",
            "owner": "owner-agent",
            "state": "verified",
            "updated_at": "2026-07-30T01:00:00Z",
            "verification": {"actor": "ghost-verifier"},
        }
        agents, tasks, _ledger, _alerts, _activity = self._collect(
            [raw_task],
            [self._registered("owner-agent")],
            [self._profile("ghost-verifier")],
        )
        self._assert_idle(agents[0])
        self.assertEqual([task["id"] for task in tasks], ["OTHER-WORK"])
        self.assertEqual(
            collector.task_actor_ids(raw_task, {}, {"owner-agent"}),
            frozenset({"owner-agent"}),
        )

    def test_known_answer_1_partial_and_arbitrary_identity_never_attest(self) -> None:
        registry = {"claude-a": self._identity_snapshot("claude-a")}
        exact = registry["claude-a"]
        for claimed in (
            None,
            {},
            {"actor": "claude-a"},
            {key: value for key, value in exact.items() if key != "alias_chain"},
            {**exact, "extra": "field"},
            {**exact, "control_principal": "other-control"},
            [*exact],
            "claude-a",
        ):
            with self.subTest(claimed=claimed):
                record = {"actor": "claude-a"}
                if claimed is not None:
                    record["identity"] = claimed
                self.assertIsNone(
                    collector.attested_actor(
                        record,
                        "actor",
                        "identity",
                        registry,
                    )
                )
        self.assertEqual(
            collector.attested_actor(
                {"actor": "claude-a", "identity": dict(exact)},
                "actor",
                "identity",
                registry,
            ),
            "claude-a",
        )
        self.assertIsNone(
            collector.attested_actor(
                {"actor": "unregistered", "identity": dict(exact)},
                "actor",
                "identity",
                registry,
            )
        )

    def test_known_answer_2_external_author_without_author_identity(self) -> None:
        raw_task = {
            "id": "TRANSPORTED",
            "title": "Externally dispatched work",
            "owner": "owner-agent",
            "state": "pending",
            "lease": None,
            "updated_at": "2026-07-29T01:00:00Z",
            "external_status": {
                "phase": "working",
                "reported_at": "2026-07-30T02:00:00Z",
                "author": "ghost-transport",
            },
        }
        agents, tasks, _ledger, _alerts, _activity = self._collect(
            [raw_task],
            [self._registered("owner-agent")],
            [self._profile("ghost-transport")],
        )
        self._assert_idle(agents[0])
        self.assertEqual(tasks[0]["external_phase"], "working")
        self.assertEqual(tasks[0]["status_source"], "transport_assertion")
        self.assertEqual(
            collector.task_actor_ids(raw_task, {}, {"owner-agent"}),
            frozenset({"owner-agent"}),
        )

    def test_known_answer_2_registered_author_needs_exact_identity(self) -> None:
        def transported(author_identity: dict[str, object]) -> dict[str, object]:
            return {
                "id": "TRANSPORTED",
                "title": "Externally dispatched work",
                "owner": "owner-agent",
                "state": "pending",
                "lease": None,
                "updated_at": "2026-07-29T01:00:00Z",
                "external_status": {
                    "phase": "working",
                    "reported_at": "2026-07-30T02:00:00Z",
                    "author": "antigravity",
                    "author_identity": author_identity,
                },
            }

        registered = [
            self._registered("owner-agent"),
            self._registered("antigravity"),
        ]
        exact = self._identity_snapshot("antigravity")
        partial = {key: value for key, value in exact.items() if key != "alias_of"}
        agents, _tasks, _ledger, _alerts, _activity = self._collect(
            [transported(partial)],
            registered,
            [self._profile("antigravity")],
        )
        self._assert_idle(agents[0])

        agents, _tasks, _ledger, _alerts, _activity = self._collect(
            [transported(dict(exact))],
            registered,
            [self._profile("antigravity")],
        )
        self.assertEqual(agents[0]["current_task_id"], "TRANSPORTED")
        self.assertEqual(agents[0]["state"], "working")
        self.assertEqual(agents[0]["status_source"], "transport_assertion")

    def test_known_answer_3_display_id_collision_does_not_widen(self) -> None:
        raw_tasks = [
            {
                "id": "VICTIM-WORK",
                "title": "Victim work",
                "owner": "victim",
                "state": "running",
                "lease": {"expires_at": "2099-01-01T00:00:00Z"},
                "updated_at": "2026-07-30T01:00:00Z",
            }
        ]
        registered = [
            self._registered("victim"),
            self._registered("real"),
        ]
        agents, tasks, _ledger, _alerts, _activity = self._collect(
            raw_tasks,
            registered,
            [self._profile("victim", "real")],
        )
        self.assertEqual(agents[0]["id"], "victim")
        self.assertEqual(agents[0]["name"], "Victim")
        self._assert_idle(agents[0])
        self.assertEqual([task["id"] for task in tasks], ["VICTIM-WORK"])

        agents, _tasks, _ledger, _alerts, _activity = self._collect(
            raw_tasks,
            registered,
            [self._profile("victim")],
        )
        self.assertEqual(agents[0]["current_task_id"], "VICTIM-WORK")

    def test_known_answer_4_newer_block_outranks_older_live_task(self) -> None:
        agents, tasks, _ledger, _alerts, _activity = self._collect(
            [
                {
                    "id": "OLD-PENDING",
                    "title": "Older pending work",
                    "owner": "claude-b",
                    "state": "pending",
                    "lease": None,
                    "updated_at": "2026-07-01T00:00:00Z",
                },
                {
                    "id": "NEW-BLOCK",
                    "title": "Newer blocked work",
                    "owner": "claude-b",
                    "state": "blocked",
                    "updated_at": "2026-07-30T00:00:00Z",
                },
            ],
            [self._registered("claude-b")],
            [self._profile("claude-b")],
        )
        self.assertEqual(agents[0]["current_task_id"], "NEW-BLOCK")
        self.assertEqual(agents[0]["state"], "blocked")
        self.assertEqual(agents[0]["updated_at"], "2026-07-30T00:00:00Z")
        self.assertEqual(
            {task["id"]: task["state"] for task in tasks},
            {"OLD-PENDING": "pending", "NEW-BLOCK": "blocked"},
        )

    def test_known_answer_5_newer_live_or_verified_outranks_older_block(self) -> None:
        old_block = {
            "id": "OLD-BLOCK",
            "title": "Older blocked work",
            "owner": "claude-b",
            "state": "blocked",
            "updated_at": "2026-07-01T00:00:00Z",
        }
        newer_pending = {
            "id": "NEW-PENDING",
            "title": "Newer pending work",
            "owner": "claude-b",
            "state": "pending",
            "lease": None,
            "updated_at": "2026-07-30T00:00:00Z",
        }
        newer_verified = {
            "id": "NEW-VERIFIED",
            "title": "Newer verified work",
            "owner": "claude-b",
            "state": "verified",
            "updated_at": "2026-07-30T00:00:00Z",
        }
        for newer, expected_state in (
            (newer_pending, "waiting"),
            (newer_verified, "waiting"),
        ):
            with self.subTest(task=newer["id"]):
                agents, tasks, _ledger, _alerts, _activity = self._collect(
                    [old_block, newer],
                    [self._registered("claude-b")],
                    [self._profile("claude-b")],
                )
                self.assertEqual(agents[0]["current_task_id"], newer["id"])
                self.assertEqual(agents[0]["state"], expected_state)
                self.assertEqual(agents[0]["updated_at"], "2026-07-30T00:00:00Z")
                self.assertEqual(
                    next(
                        task for task in tasks if task["id"] == "OLD-BLOCK"
                    )["state"],
                    "blocked",
                )

    def test_known_answer_6_equal_timestamps_use_class_then_task_id(self) -> None:
        same_time = "2026-07-30T02:00:00Z"

        def candidate(task_id: str, state: str, **extra: object) -> dict[str, object]:
            return {
                "id": task_id,
                "state": state,
                "external_phase": None,
                "updated_at": same_time,
                **extra,
            }

        # Class priority decides before the task ID: the attention record wins
        # even though its ID sorts after the live and terminal records.
        self.assertEqual(
            collector.choose_agent_task(
                [
                    candidate("A-LIVE", "pending"),
                    candidate("Z-BLOCK", "blocked"),
                ]
            )["id"],
            "Z-BLOCK",
        )
        self.assertEqual(
            collector.choose_agent_task(
                [
                    candidate("A-DONE", "verified"),
                    candidate("Z-LIVE", "pending"),
                ]
            )["id"],
            "Z-LIVE",
        )
        # Within one class the lexicographically lower task ID wins.
        for state in ("blocked", "pending", "verified"):
            with self.subTest(state=state):
                self.assertEqual(
                    collector.choose_agent_task(
                        [
                            candidate("TASK-B", state),
                            candidate("TASK-A", state),
                        ]
                    )["id"],
                    "TASK-A",
                )

        agents, _tasks, _ledger, _alerts, _activity = self._collect(
            [
                {
                    "id": "TIE-A-PENDING",
                    "title": "Tied pending work",
                    "owner": "claude-b",
                    "state": "pending",
                    "lease": None,
                    "updated_at": same_time,
                },
                {
                    "id": "TIE-Z-BLOCK",
                    "title": "Tied blocked work",
                    "owner": "claude-b",
                    "state": "blocked",
                    "updated_at": same_time,
                },
            ],
            [self._registered("claude-b")],
            [self._profile("claude-b")],
        )
        self.assertEqual(agents[0]["current_task_id"], "TIE-Z-BLOCK")
        self.assertEqual(agents[0]["state"], "blocked")

    def test_known_answer_7_every_non_idle_card_names_a_retained_task(self) -> None:
        registered = [
            self._registered("codex"),
            self._registered(
                "codex-verifier",
                principal="codex-control",
                alias_of="codex",
                alias_chain=("codex",),
            ),
            self._registered("claude-b"),
            self._registered("victim"),
        ]
        raw_tasks = [
            {
                "id": "AAA-OLD-BLOCK",
                "title": "Old Claude B block",
                "owner": "claude-b",
                "state": "blocked",
                "updated_at": "2026-07-01T00:00:00Z",
            },
            {
                "id": "MMM-LIVE",
                "title": "Current Claude B work",
                "owner": "claude-b",
                "state": "running",
                "lease": {"expires_at": "2099-01-01T00:00:00Z"},
                "updated_at": "2026-07-30T00:00:00Z",
            },
            {
                "id": "ZZZ-VERIFIED",
                "title": "Codex verified work",
                "owner": "claude-b",
                "state": "verified",
                "updated_at": "2026-07-31T00:00:00Z",
                "verification": {
                    "actor": "codex-verifier",
                    "identity": self._identity_snapshot(
                        "codex-verifier",
                        principal="codex-control",
                        alias_of="codex",
                        alias_chain=("codex",),
                    ),
                },
            },
            {
                "id": "GHOST-WORK",
                "title": "Unattested transport report",
                "owner": "victim",
                "state": "pending",
                "lease": None,
                "updated_at": "2026-07-31T06:00:00Z",
                "external_status": {
                    "phase": "working",
                    "reported_at": "2026-07-31T07:00:00Z",
                    "author": "ghost-transport",
                },
            },
        ]
        profiles = [
            self._profile("codex"),
            self._profile("claude-b"),
            self._profile("ghost-transport"),
            self._profile("display-victim", "real"),
        ]
        agents, tasks, _ledger, _alerts, _activity = self._collect(
            raw_tasks,
            registered,
            profiles,
        )
        retained = {task["id"] for task in tasks}
        self.assertEqual(
            retained,
            {"AAA-OLD-BLOCK", "MMM-LIVE", "ZZZ-VERIFIED", "GHOST-WORK"},
        )
        non_idle = 0
        for card in agents:
            self.assertEqual(len(card), 11)
            if card["status_source"] == "none":
                self._assert_idle(card)
                continue
            non_idle += 1
            self.assertIn(card["current_task_id"], retained)
            task = next(
                item for item in tasks if item["id"] == card["current_task_id"]
            )
            self.assertEqual(card["current"], task["title"])
            self.assertEqual(card["next"], task["next"])
            self.assertEqual(card["progress_percent"], task["progress_percent"])
            self.assertEqual(card["status_source"], task["status_source"])
            self.assertEqual(card["status_badge"], task["status_badge"])
            self.assertEqual(card["updated_at"], task["updated_at"])
            self.assertEqual(card["state"], collector.agent_state(task))
        self.assertEqual(non_idle, 2)
        self.assertEqual(agents[0]["current_task_id"], "ZZZ-VERIFIED")
        self.assertEqual(agents[1]["current_task_id"], "ZZZ-VERIFIED")
        self._assert_idle(agents[2])
        self._assert_idle(agents[3])

    def test_agent_card_keeps_exact_eleven_field_projection(self) -> None:
        agents, _tasks, _ledger, _alerts, _activity = self._collect(
            [
                {
                    "id": "CARD-SHAPE",
                    "title": "Card shape",
                    "owner": "claude-b",
                    "state": "running",
                    "lease": {"expires_at": "2099-01-01T00:00:00Z"},
                    "updated_at": "2026-07-30T00:00:00Z",
                }
            ],
            [self._registered("claude-b")],
            [self._profile("claude-b")],
        )
        self.assertEqual(
            list(agents[0]),
            [
                "id",
                "name",
                "role",
                "state",
                "current",
                "current_task_id",
                "next",
                "progress_percent",
                "status_source",
                "status_badge",
                "updated_at",
            ],
        )


if __name__ == "__main__":
    unittest.main()
