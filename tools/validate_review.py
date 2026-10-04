#!/usr/bin/env python3
"""Validate a Codex review result before Paperclip changes task state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_task import load_tasks, load_source_manifest, validate_review_result, validate_task_set


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path)
    parser.add_argument("review_file", type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)

    try:
        tasks = load_tasks(args.task_file)
        review = json.loads(args.review_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid review input: {exc}", file=sys.stderr)
        return 2

    sources, manifest_errors = load_source_manifest(args.repo_root / "SOURCE_MANIFEST.json")
    errors = manifest_errors + validate_task_set(tasks, sources)
    matching = [task for task in tasks if isinstance(task, dict) and task.get("task_id") == args.task_id]
    if len(matching) != 1:
        errors.append(f"task-id: expected exactly one matching task, found {len(matching)}")
    else:
        errors.extend(validate_review_result(review, matching[0]))

    if errors:
        print("invalid")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"valid review for {args.task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
