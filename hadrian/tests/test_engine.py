#!/usr/bin/env python3
"""Unit tests for Hadrian L3 Goal Loop Engine."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from engine import HadrianEngine, compute_md5, find_repo_root


class TestHadrianEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="hadrian_test_")
        self.repo_path = Path(self.test_dir)
        # Initialize test git repository
        subprocess.run(["git", "init"], cwd=self.repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=self.repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_path, check=True)
        # Create initial commit
        readme = self.repo_path / "README.md"
        readme.write_text("# Test Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.repo_path, check=True, capture_output=True)

        self.engine = HadrianEngine(self.repo_path)

    def tearDown(self):
        # Clean up worktrees and temp dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_repo_root_and_md5(self):
        self.assertEqual(find_repo_root(self.repo_path), self.repo_path)
        readme = self.repo_path / "README.md"
        expected_md5 = compute_md5(readme)
        self.assertTrue(len(expected_md5) == 32)

    def test_intake_creates_contract_and_worktree(self):
        res = self.engine.cmd_intake("Test feature US#999", budget=5)
        self.assertEqual(res["status"], "READY")
        self.assertEqual(res["budget"], 5)
        self.assertTrue(Path(res["worktree"]).exists())

        # Check contract and state
        self.assertTrue(self.engine.contract_file.exists())
        self.assertTrue(self.engine.state_file.exists())

        status = self.engine.cmd_status()
        self.assertTrue(status["active"])
        self.assertTrue(status["contract_valid"])
        self.assertEqual(status["budget_total"], 5)
        self.assertEqual(status["budget_used"], 0)

    def test_contract_tamper_detection(self):
        self.engine.cmd_intake("Test tamper US#101")
        # Tamper with contract
        with self.engine.contract_file.open("a", encoding="utf-8") as f:
            f.write("\nTampered line!\n")

        status = self.engine.cmd_status()
        self.assertFalse(status["contract_valid"])

    def test_pause_and_resume(self):
        self.engine.cmd_intake("Test pause resume US#102")
        pause_res = self.engine.cmd_pause(reason="need manual inspection")
        self.assertEqual(pause_res["status"], "PAUSED")
        self.assertIn("need manual inspection", pause_res["reason"])

        state_text = self.engine.state_file.read_text(encoding="utf-8")
        self.assertIn("PAUSE at=", state_text)

        resume_res = self.engine.cmd_resume()
        self.assertEqual(resume_res["status"], "RESUMED")
        self.assertTrue(resume_res["contract_valid"])
        self.assertEqual(len(resume_res["malformed_verdicts"]), 0)

    def test_malformed_verdict_detection_on_resume(self):
        self.engine.cmd_intake("Test malformed verdicts US#103")
        # Inject valid and malformed verdicts into state.md
        with self.engine.state_file.open("a", encoding="utf-8") as f:
            f.write('\nVERDICT kind=gate id=G1 status=PASS evidence="ok" source=kb:AGENTS.md\n')
            f.write('\nVERDICT kind=gate id=G2 status=INVALID status evidence="" source=kb:AGENTS.md\n')

        resume_res = self.engine.cmd_resume()
        self.assertEqual(len(resume_res["malformed_verdicts"]), 1)
        self.assertEqual(resume_res["malformed_verdicts"][0]["line_number"], 18)

    def test_amend_contract(self):
        self.engine.cmd_intake("Test amendment US#104", budget=5)
        # Modify contract
        with self.engine.contract_file.open("a", encoding="utf-8") as f:
            f.write("\n- Budget: 15 cycles\n")

        # Before amendment, contract is invalid
        self.assertFalse(self.engine.cmd_status()["contract_valid"])

        # Call amend
        amend_res = self.engine.cmd_amend("Increased budget from 5 to 15", user="human_reviewer")
        self.assertEqual(amend_res["status"], "AMENDED")

        # After amendment, contract is valid with new MD5
        self.assertTrue(self.engine.cmd_status()["contract_valid"])

    def test_commit_and_review_diff(self):
        intake_res = self.engine.cmd_intake("Test commit and diff US#105")
        wt = Path(intake_res["worktree"])

        # Add a new file in worktree
        new_file = wt / "feature.py"
        new_file.write_text("print('hello world')\n", encoding="utf-8")

        commit_res = self.engine.cmd_commit("feat", "add feature.py", worktree_dir=str(wt))
        self.assertEqual(commit_res["status"], "COMMITTED")
        self.assertTrue(len(commit_res["sha"]) >= 7)

        # Check review diff
        diff_res = self.engine.cmd_review_diff(worktree_dir=str(wt))
        self.assertIn("feature.py", diff_res["stat"])
        self.assertIn("print('hello world')", diff_res["diff"])

    def test_taiga_sync_mock(self):
        from unittest.mock import patch
        with patch.object(self.engine, "_taiga_request") as mock_req:
            mock_req.side_effect = [
                {"id": 1, "slug": "smartsparks"}, # project
                {"id": 98, "ref": 326, "subject": "Test Story", "version": 1, "status_extra_info": {"name": "In progress"}}, # story
                [{"id": 272, "ref": 337, "subject": "Task 1", "version": 1, "status_extra_info": {"name": "Closed", "is_closed": True}}] # tasks
            ]
            res = self.engine.cmd_taiga_sync(action="status", story_ref=326)
            self.assertEqual(res["status"], "OK")
            self.assertEqual(res["story"]["ref"], 326)
            self.assertEqual(len(res["tasks"]), 1)
            self.assertTrue(res["tasks"][0]["is_closed"])

    def test_resolve_story_from_objective(self):
        self.assertEqual(
            self.engine._resolve_story_from_objective("Complete http://localhost:9500/project/smartsparks/us/327"),
            (327, "smartsparks"),
        )
        self.assertEqual(
            self.engine._resolve_story_from_objective("smartsparks#326"),
            (326, "smartsparks"),
        )
        self.assertEqual(
            self.engine._resolve_story_from_objective("US#327: P2 Volume and Capacity"),
            (327, "smartsparks"),
        )
        self.assertEqual(
            self.engine._resolve_story_from_objective("us/328"),
            (328, "smartsparks"),
        )
        self.assertEqual(
            self.engine._resolve_story_from_objective("Refactor internal engine"),
            (None, "smartsparks"),
        )

    def test_intake_with_taiga_story(self):
        from unittest.mock import patch
        story_desc = """**As a** Primary 2 pupil **I want to** learn volume **So that** I pass exams.

### Context:
- Corpus evidence: P2 exam papers.

### Acceptance Criteria:
- New topic `p2_volume_capacity` in MoeSyllabus.kt.
- Dedicated generator P2VolumeCapacityGenerator registered in Generators.kt.
- Question families:
  1. Reading beaker scales.
  2. Comparing liquid volumes.
- Integer constraints: 1 to 50 litres whole numbers.
"""
        with patch.object(self.engine, "_taiga_request") as mock_req:
            mock_req.side_effect = [
                {"id": 1, "slug": "smartsparks"}, # project
                {
                    "id": 99,
                    "ref": 327,
                    "subject": "US-24.2: P2 Generator — Volume and Capacity (Litres)",
                    "description": story_desc,
                }, # story
            ]
            res = self.engine.cmd_intake("Complete http://localhost:9500/project/smartsparks/us/327", budget=7)
            self.assertEqual(res["status"], "READY")
            self.assertEqual(res["budget"], 7)
            self.assertTrue(res["branch"].startswith("hadrian/us327-"))

            contract_text = self.engine.contract_file.read_text(encoding="utf-8")
            self.assertIn("# Goal Contract — US#327 US-24.2: P2 Generator — Volume and Capacity (Litres)", contract_text)
            self.assertIn("- **C1** — New topic `p2_volume_capacity` in MoeSyllabus.kt.", contract_text)
            self.assertIn("- **C2** — Dedicated generator P2VolumeCapacityGenerator registered in Generators.kt.", contract_text)
            self.assertIn("- **C3** — Question families:", contract_text)
            self.assertIn("1. Reading beaker scales.", contract_text)
            self.assertIn("- **C4** — Integer constraints: 1 to 50 litres whole numbers.", contract_text)
            self.assertIn("Decomposition before work: child sub-tasks of US#327", contract_text)
            self.assertIn("Fail-closed story completion: US#327 moves to Done", contract_text)
            self.assertIn("| G1 | assembleDebug --rerun-tasks", contract_text)
            self.assertIn("| G2 | testDebugUnitTest --rerun", contract_text)
            self.assertIn("| T1 | Decomposition before work", contract_text)
            self.assertIn("| T2 | Fail-closed completion", contract_text)
            self.assertIn("## Rubric (scale 0–4 per criterion)", contract_text)
            self.assertIn("| R1 |", contract_text)
            self.assertIn("| R2 |", contract_text)
            self.assertIn("| R3 |", contract_text)
            self.assertIn("## Ticket Sync", contract_text)
            self.assertIn("http://localhost:9500/project/smartsparks/us/327", contract_text)

            state_text = self.engine.state_file.read_text(encoding="utf-8")
            self.assertIn("# Goal State — US#327 US-24.2: P2 Generator — Volume and Capacity (Litres)", state_text)
            self.assertIn("- Ticket: smartsparks#327", state_text)
            self.assertIn("Budget used: 0 / 7 cycles", state_text)

    def test_cmd_signoff(self):
        # 1. No active goal should error
        err_res = self.engine.cmd_signoff()
        self.assertEqual(err_res["status"], "ERROR")

        # 2. Intake a goal
        intake_res = self.engine.cmd_intake("Feature to signoff US#200")
        self.assertEqual(intake_res["status"], "READY")
        self.assertTrue(self.engine.contract_file.exists())
        self.assertTrue(self.engine.state_file.exists())

        # Also create a mock evidence file and langsmith thread
        ev_file = self.engine.evidence_dir / "1-G1.md"
        ev_file.write_text("# Evidence G1\n", encoding="utf-8")
        thread_file = self.engine.hadrian_dir / "langsmith_thread"
        thread_file.write_text("thread_12345\n", encoding="utf-8")

        # 3. Call signoff without network operations (push=False, create_pr=False)
        res = self.engine.cmd_signoff(approver="davide", push=False, create_pr=False)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["approver"], "davide")
        self.assertFalse(self.engine.contract_file.exists())
        self.assertFalse(self.engine.state_file.exists())
        self.assertFalse((self.engine.hadrian_dir / "signoff").exists())
        self.assertFalse(thread_file.exists())

        # Check archived artifacts
        archive_path = Path(res["archive_dir"])
        self.assertTrue(archive_path.exists())
        self.assertTrue((archive_path / "contract.md").exists())
        self.assertTrue((archive_path / "state.md").exists())
        self.assertTrue((archive_path / "signoff").exists())
        self.assertTrue((archive_path / "langsmith_thread").exists())
        self.assertTrue((archive_path / "1-G1.md").exists())

        signoff_content = (archive_path / "signoff").read_text(encoding="utf-8")
        self.assertIn("APPROVED by davide", signoff_content)
        self.assertIn("Feature to signoff US#200", signoff_content)


if __name__ == "__main__":
    unittest.main()
