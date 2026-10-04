from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.validate_task import (
    load_source_manifest,
    validate_review_result,
    validate_task_set,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/phase1-task-set.json"


class TaskValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        cls.tasks = document["tasks"]
        cls.sources, source_errors = load_source_manifest(ROOT / "SOURCE_MANIFEST.json")
        assert not source_errors, source_errors

    def assert_invalid(self, tasks: list[dict], expected: str) -> None:
        errors = validate_task_set(tasks, self.sources)
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_example_task_set_is_valid(self) -> None:
        self.assertEqual(validate_task_set(self.tasks, self.sources), [])

    def test_accepts_copilot_fallback_task(self) -> None:
        task = copy.deepcopy(self.tasks[2])
        task["dependencies"] = []
        errors = validate_task_set([task], self.sources)
        self.assertEqual(errors, [])

    def test_rejects_unknown_repository(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["repository"]["name"] = "other-repo"
        self.assert_invalid(tasks, "tasks[0].repository.name")

    def test_rejects_unreviewed_task(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["review"]["runtime"] = "p40"
        self.assert_invalid(tasks, "tasks[0].review.runtime")

    def test_rejects_p40_task_without_exclusive_resource(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["resources"]["required"] = []
        self.assert_invalid(tasks, "tasks[0].resources.required")

    def test_rejects_copilot_task_without_account_resource(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[2]["resources"]["required"] = ["p40"]
        self.assert_invalid(tasks, "tasks[2].resources.required")

    def test_rejects_source_hash_drift(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["inputs"]["source_images"][0]["sha256"] = "0" * 64
        self.assert_invalid(tasks, "path and hash do not match")

    def test_rejects_duplicate_idempotency_key(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[1]["idempotency_key"] = tasks[0]["idempotency_key"]
        self.assert_invalid(tasks, "duplicate key")

    def test_rejects_dependency_cycle(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["dependencies"] = [tasks[1]["task_id"]]
        self.assert_invalid(tasks, "dependency graph contains a cycle")

    def test_rejects_path_traversal(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["repository"]["allowed_paths"] = ["../outside"]
        self.assert_invalid(tasks, "repository-relative path without traversal")

    def test_rejects_secret_pattern(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["outputs"].append("token=" + "gho" + "_not-a-real-token")
        self.assert_invalid(tasks, "credential or private-key pattern")

    def test_rejects_more_than_two_fix_rounds(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks[0]["review"]["max_fix_rounds"] = 3
        self.assert_invalid(tasks, "tasks[0].review.max_fix_rounds")

    def test_accepts_codex_pass_review(self) -> None:
        review = json.loads((ROOT / "examples/phase1-review-pass.json").read_text())
        self.assertEqual(validate_review_result(review, self.tasks[0]), [])

    def test_accepts_codex_fix_required_review(self) -> None:
        review = json.loads((ROOT / "examples/phase1-review-fix.json").read_text())
        self.assertEqual(validate_review_result(review, self.tasks[1]), [])

    def test_accepts_codex_review_of_copilot_branch(self) -> None:
        task = copy.deepcopy(self.tasks[2])
        task["dependencies"] = []
        review = json.loads((ROOT / "examples/phase1-review-pass.json").read_text())
        review["task_id"] = task["task_id"]
        review["idempotency_key"] = task["idempotency_key"]
        review["branch"] = task["repository"]["work_branch"]
        self.assertEqual(validate_review_result(review, task), [])

    def test_rejects_pass_review_with_requested_fixes(self) -> None:
        review = json.loads((ROOT / "examples/phase1-review-pass.json").read_text())
        review["requested_fixes"] = ["Change something"]
        errors = validate_review_result(review, self.tasks[0])
        self.assertTrue(any("pass results cannot contain" in error for error in errors), errors)

    def test_rejects_review_for_wrong_branch(self) -> None:
        review = json.loads((ROOT / "examples/phase1-review-pass.json").read_text())
        review["branch"] = "p40/other-task"
        errors = validate_review_result(review, self.tasks[0])
        self.assertTrue(any("review.branch" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
