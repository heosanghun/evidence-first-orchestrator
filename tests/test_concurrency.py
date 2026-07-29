from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from evidence_orchestrator.errors import TransitionError
from evidence_orchestrator.workspace import Workspace

from .helpers import make_workspace


class ConcurrencyTests(unittest.TestCase):
    def test_only_one_worker_claims_the_same_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "workspace"
            workspace = make_workspace(root)
            workspace.create_task(
                actor="antigravity",
                task_id="RACE",
                title="Claim once",
                description="Concurrent claim test.",
                owner="codex",
            )
            barrier = threading.Barrier(8)
            successes: list[str] = []
            failures: list[str] = []
            result_lock = threading.Lock()

            def claimant() -> None:
                barrier.wait()
                try:
                    result = Workspace(root).claim(actor="codex", task_id="RACE")
                except TransitionError as exc:
                    with result_lock:
                        failures.append(str(exc))
                else:
                    with result_lock:
                        successes.append(result["lease_token"])

            threads = [threading.Thread(target=claimant) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(len(successes), 1)
            self.assertEqual(len(failures), 7)
            self.assertEqual(Workspace(root).get_task("RACE")["attempt"], 1)


if __name__ == "__main__":
    unittest.main()
