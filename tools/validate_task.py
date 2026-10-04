#!/usr/bin/env python3
"""Validate Paperclip task envelopes before they enter the Chess Commander queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

TASK_SCHEMA = "chess-commander.paperclip-task.v1"
TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
IDEMPOTENCY_RE = re.compile(r"^[a-z0-9][a-z0-9:._-]{2,127}$")
BRANCH_RE = re.compile(r"^(codex|p40|copilot)/[a-z0-9][a-z0-9/-]{2,62}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_ROOT = "/mnt/scratch/project-data/chess-commander/"
SECRET_RE = re.compile(
    r"(?:gho_[A-Za-z0-9_-]+|github_pat_[A-Za-z0-9_-]+|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16})"
)

EXPECTED_TASK_KEYS = {
    "schema",
    "task_id",
    "parent_task_id",
    "idempotency_key",
    "title",
    "phase",
    "kind",
    "repository",
    "worker",
    "resources",
    "dependencies",
    "execution",
    "inputs",
    "outputs",
    "acceptance_criteria",
    "review",
}
EXPECTED_REPOSITORY_KEYS = {
    "owner",
    "name",
    "base_branch",
    "work_branch",
    "allowed_paths",
}
EXPECTED_WORKER_KEYS = {"runtime", "mode", "account", "fallback_for"}
EXPECTED_RESOURCE_KEYS = {"required", "max_concurrency"}
EXPECTED_EXECUTION_KEYS = {"timeout_seconds", "retry", "on_ambiguous"}
EXPECTED_RETRY_KEYS = {"max_attempts", "same_idempotency_key"}
EXPECTED_INPUT_KEYS = {"source_manifest", "source_images"}
EXPECTED_SOURCE_KEYS = {"backend", "path", "sha256"}
EXPECTED_REVIEW_KEYS = {
    "required",
    "runtime",
    "mode",
    "fix_runtime",
    "max_fix_rounds",
    "failure_action",
}
EXPECTED_REVIEW_RESULT_KEYS = {
    "schema",
    "task_id",
    "idempotency_key",
    "branch",
    "round",
    "decision",
    "checked",
    "findings",
    "requested_fixes",
    "evidence",
}
REQUIRED_REVIEW_CHECKS = {"diff_scope", "tests", "source_boundary", "evidence"}
FORBIDDEN_PATH_PARTS = {".git", ".env", "credentials", "secrets", "private"}


class ValidationFailure(Exception):
    """Internal signal for a single validation failure."""


def _fail(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        _fail(errors, path, "must be an object")
        return None
    return value


def _keys(value: dict[str, Any], expected: set[str], path: str, errors: list[str]) -> None:
    unknown = sorted(set(value) - expected)
    if unknown:
        _fail(errors, path, f"unknown fields: {', '.join(unknown)}")


def _required(value: dict[str, Any], names: set[str], path: str, errors: list[str]) -> None:
    missing = sorted(names - set(value))
    if missing:
        _fail(errors, path, f"missing fields: {', '.join(missing)}")


def _string(value: Any, path: str, errors: list[str], *, minimum: int = 1) -> bool:
    if not isinstance(value, str) or len(value) < minimum:
        _fail(errors, path, f"must be a string with at least {minimum} character(s)")
        return False
    return True


def _enum(value: Any, path: str, allowed: set[str], errors: list[str]) -> None:
    if value not in allowed:
        _fail(errors, path, f"must be one of: {', '.join(sorted(allowed))}")


def _integer(value: Any, path: str, errors: list[str], *, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        _fail(errors, path, f"must be an integer from {minimum} to {maximum}")


def _unique_strings(value: Any, path: str, errors: list[str], *, minimum: int = 0) -> list[str]:
    if not isinstance(value, list):
        _fail(errors, path, "must be an array")
        return []
    if len(value) < minimum:
        _fail(errors, path, f"must contain at least {minimum} item(s)")
    if len(set(value)) != len(value):
        _fail(errors, path, "must not contain duplicates")
    for index, item in enumerate(value):
        _string(item, f"{path}[{index}]", errors)
    return [item for item in value if isinstance(item, str)]


def _validate_relative_path(value: Any, path: str, errors: list[str]) -> None:
    if not _string(value, path, errors):
        return
    if value.startswith(("/", "\\")) or ".." in value.replace("\\", "/").split("/"):
        _fail(errors, path, "must be a repository-relative path without traversal")
    if any(part.casefold() in FORBIDDEN_PATH_PARTS for part in value.replace("\\", "/").split("/")):
        _fail(errors, path, "targets a forbidden repository path")


def _scan_secrets(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _scan_secrets(item, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_secrets(item, f"{path}[{index}]", errors)
    elif isinstance(value, str) and SECRET_RE.search(value):
        _fail(errors, path, "contains a credential or private-key pattern")


def load_source_manifest(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"source_manifest: cannot read {path}: {exc}"]
    if not isinstance(document, dict) or not isinstance(document.get("sources"), list):
        return {}, ["source_manifest: sources must be an array"]
    sources: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(document["sources"]):
        if not isinstance(source, dict):
            _fail(errors, f"source_manifest.sources[{index}]", "must be an object")
            continue
        backend = source.get("backend")
        if backend in sources:
            _fail(errors, f"source_manifest.sources[{index}].backend", "duplicate backend")
            continue
        if backend not in {"acornsoft", "thompson"}:
            _fail(errors, f"source_manifest.sources[{index}].backend", "unknown backend")
            continue
        for required in ("path", "size_bytes", "sha256"):
            if required not in source:
                _fail(errors, f"source_manifest.sources[{index}]", f"missing {required}")
        if not isinstance(source.get("path"), str) or not isinstance(source.get("sha256"), str):
            continue
        if not SHA256_RE.fullmatch(source["sha256"]):
            _fail(errors, f"source_manifest.sources[{index}].sha256", "must be lowercase SHA-256")
        sources[backend] = source
    return sources, errors


def _validate_source_files(sources: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for backend, source in sources.items():
        path = Path(source["path"])
        if not path.is_file():
            _fail(errors, f"source_files.{backend}", f"missing source file: {path}")
            continue
        size = path.stat().st_size
        if size != source.get("size_bytes"):
            _fail(errors, f"source_files.{backend}", f"size {size} does not match manifest")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source.get("sha256"):
            _fail(errors, f"source_files.{backend}", "SHA-256 does not match manifest")


def validate_task(
    task: Any,
    manifest_sources: dict[str, dict[str, Any]],
    *,
    verify_source_files: bool = False,
) -> list[str]:
    """Return all validation errors for one Paperclip task envelope."""
    errors: list[str] = []
    value = _mapping(task, "task", errors)
    if value is None:
        return errors
    _keys(value, EXPECTED_TASK_KEYS, "task", errors)
    _required(value, EXPECTED_TASK_KEYS, "task", errors)

    if value.get("schema") != TASK_SCHEMA:
        _fail(errors, "task.schema", f"must equal {TASK_SCHEMA}")
    if not isinstance(value.get("task_id"), str) or not TASK_ID_RE.fullmatch(value.get("task_id", "")):
        _fail(errors, "task.task_id", "must be a lowercase kebab-case identifier")
    if not _string(value.get("parent_task_id"), "task.parent_task_id", errors):
        pass
    if not isinstance(value.get("idempotency_key"), str) or not IDEMPOTENCY_RE.fullmatch(value.get("idempotency_key", "")):
        _fail(errors, "task.idempotency_key", "must be a lowercase idempotency key")
    if not _string(value.get("title"), "task.title", errors, minimum=8):
        pass
    elif len(value["title"]) > 160:
        _fail(errors, "task.title", "must be at most 160 characters")
    if value.get("phase") != "phase1":
        _fail(errors, "task.phase", "must equal phase1")
    _enum(value.get("kind"), "task.kind", {"install", "coding", "assessment", "evidence"}, errors)

    repository = _mapping(value.get("repository"), "task.repository", errors)
    if repository is not None:
        _keys(repository, EXPECTED_REPOSITORY_KEYS, "task.repository", errors)
        _required(repository, EXPECTED_REPOSITORY_KEYS, "task.repository", errors)
        if repository.get("owner") != "andyfied-Thargoid":
            _fail(errors, "task.repository.owner", "must equal andyfied-Thargoid")
        if repository.get("name") != "chess-commander":
            _fail(errors, "task.repository.name", "must equal chess-commander")
        if repository.get("base_branch") != "main":
            _fail(errors, "task.repository.base_branch", "must equal main")
        if not isinstance(repository.get("work_branch"), str) or not BRANCH_RE.fullmatch(repository.get("work_branch", "")):
            _fail(errors, "task.repository.work_branch", "must start with codex/, p40/, or copilot/ and not target main")
        allowed_paths = _unique_strings(repository.get("allowed_paths"), "task.repository.allowed_paths", errors, minimum=1)
        for index, path in enumerate(allowed_paths):
            _validate_relative_path(path, f"task.repository.allowed_paths[{index}]", errors)

    worker = _mapping(value.get("worker"), "task.worker", errors)
    if worker is not None:
        _keys(worker, EXPECTED_WORKER_KEYS, "task.worker", errors)
        _required(worker, {"runtime", "mode"}, "task.worker", errors)
        worker_runtime = worker.get("runtime")
        if worker_runtime not in {"p40", "copilot"}:
            _fail(errors, "task.worker.runtime", "must equal p40 or copilot")
        if worker.get("mode") != "coder":
            _fail(errors, "task.worker.mode", "must equal coder")
        if worker_runtime == "p40":
            if worker.get("account") is not None:
                _fail(errors, "task.worker.account", "must be null or omitted for p40 tasks")
            if worker.get("fallback_for") is not None:
                _fail(errors, "task.worker.fallback_for", "must be null or omitted for p40 tasks")
        elif worker_runtime == "copilot":
            if worker.get("account") not in {"andyfied-agent", "andyfied-Thargoid"}:
                _fail(errors, "task.worker.account", "must identify one of the isolated Copilot accounts")
            if worker.get("fallback_for") != "p40":
                _fail(errors, "task.worker.fallback_for", "must equal p40 for Copilot fallback tasks")

    required_resources: list[str] = []
    resources = _mapping(value.get("resources"), "task.resources", errors)
    if resources is not None:
        _keys(resources, EXPECTED_RESOURCE_KEYS, "task.resources", errors)
        _required(resources, EXPECTED_RESOURCE_KEYS, "task.resources", errors)
        required_resources = _unique_strings(resources.get("required"), "task.resources.required", errors)
        if resources.get("max_concurrency") != 1:
            _fail(errors, "task.resources.max_concurrency", "must equal 1 for exclusive scheduling")
        if "p40" in required_resources and resources.get("max_concurrency") != 1:
            _fail(errors, "task.resources", "p40 requires max_concurrency=1")
    if worker is not None:
        worker_runtime = worker.get("runtime")
        if worker_runtime == "p40" and "p40" not in required_resources:
            _fail(errors, "task.resources.required", "p40 coder tasks must request the p40 resource")
        if worker_runtime == "copilot":
            account_resource = f"copilot:{worker.get('account')}"
            if account_resource not in required_resources:
                _fail(errors, "task.resources.required", f"Copilot tasks must request {account_resource}")

    dependencies = _unique_strings(value.get("dependencies"), "task.dependencies", errors)
    for index, dependency in enumerate(dependencies):
        if not TASK_ID_RE.fullmatch(dependency):
            _fail(errors, f"task.dependencies[{index}]", "must be a task identifier")
        if dependency == value.get("task_id"):
            _fail(errors, "task.dependencies", "cannot depend on itself")

    execution = _mapping(value.get("execution"), "task.execution", errors)
    if execution is not None:
        _keys(execution, EXPECTED_EXECUTION_KEYS, "task.execution", errors)
        _required(execution, EXPECTED_EXECUTION_KEYS, "task.execution", errors)
        _integer(execution.get("timeout_seconds"), "task.execution.timeout_seconds", errors, minimum=60, maximum=86400)
        if execution.get("on_ambiguous") != "reconcile_before_retry":
            _fail(errors, "task.execution.on_ambiguous", "must equal reconcile_before_retry")
        retry = _mapping(execution.get("retry"), "task.execution.retry", errors)
        if retry is not None:
            _keys(retry, EXPECTED_RETRY_KEYS, "task.execution.retry", errors)
            _required(retry, EXPECTED_RETRY_KEYS, "task.execution.retry", errors)
            _integer(retry.get("max_attempts"), "task.execution.retry.max_attempts", errors, minimum=0, maximum=3)
            if retry.get("same_idempotency_key") is not True:
                _fail(errors, "task.execution.retry.same_idempotency_key", "must be true")

    inputs = _mapping(value.get("inputs"), "task.inputs", errors)
    task_sources: dict[str, dict[str, Any]] = {}
    if inputs is not None:
        _keys(inputs, EXPECTED_INPUT_KEYS, "task.inputs", errors)
        _required(inputs, EXPECTED_INPUT_KEYS, "task.inputs", errors)
        if inputs.get("source_manifest") != "SOURCE_MANIFEST.json":
            _fail(errors, "task.inputs.source_manifest", "must equal SOURCE_MANIFEST.json")
        source_images = inputs.get("source_images")
        if not isinstance(source_images, list) or not source_images:
            _fail(errors, "task.inputs.source_images", "must contain at least one source image")
            source_images = []
        for index, source in enumerate(source_images):
            item = _mapping(source, f"task.inputs.source_images[{index}]", errors)
            if item is None:
                continue
            _keys(item, EXPECTED_SOURCE_KEYS, f"task.inputs.source_images[{index}]", errors)
            _required(item, EXPECTED_SOURCE_KEYS, f"task.inputs.source_images[{index}]", errors)
            backend = item.get("backend")
            _enum(backend, f"task.inputs.source_images[{index}].backend", {"acornsoft", "thompson"}, errors)
            if backend in task_sources:
                _fail(errors, f"task.inputs.source_images[{index}].backend", "duplicate backend")
            elif isinstance(backend, str):
                task_sources[backend] = item
            path = item.get("path")
            if not isinstance(path, str) or not path.startswith(SOURCE_ROOT) or not path.endswith(".ssd"):
                _fail(errors, f"task.inputs.source_images[{index}].path", "must be an SSD under /mnt/scratch/project-data/chess-commander/")
            digest = item.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                _fail(errors, f"task.inputs.source_images[{index}].sha256", "must be lowercase SHA-256")
            manifest = manifest_sources.get(backend)
            if manifest is None:
                _fail(errors, f"task.inputs.source_images[{index}]", "backend is absent from SOURCE_MANIFEST.json")
            elif item.get("path") != manifest.get("path") or item.get("sha256") != manifest.get("sha256"):
                _fail(errors, f"task.inputs.source_images[{index}]", "path and hash do not match SOURCE_MANIFEST.json")
        if verify_source_files and task_sources:
            selected_sources = {
                backend: manifest_sources[backend]
                for backend in task_sources
                if backend in manifest_sources
            }
            _validate_source_files(selected_sources, errors)

    for field in ("outputs", "acceptance_criteria"):
        _unique_strings(value.get(field), f"task.{field}", errors, minimum=1)

    review = _mapping(value.get("review"), "task.review", errors)
    if review is not None:
        _keys(review, EXPECTED_REVIEW_KEYS, "task.review", errors)
        _required(review, EXPECTED_REVIEW_KEYS, "task.review", errors)
        if review.get("required") is not True:
            _fail(errors, "task.review.required", "must be true")
        if review.get("runtime") != "codex":
            _fail(errors, "task.review.runtime", "must equal codex")
        if review.get("mode") != "review":
            _fail(errors, "task.review.mode", "must equal review")
        expected_fix_runtime = worker.get("runtime") if isinstance(worker, dict) else None
        if review.get("fix_runtime") != expected_fix_runtime:
            _fail(errors, "task.review.fix_runtime", "must equal the worker runtime")
        _integer(review.get("max_fix_rounds"), "task.review.max_fix_rounds", errors, minimum=1, maximum=2)
        expected_failure_action = (
            f"return_to_{expected_fix_runtime}" if expected_fix_runtime in {"p40", "copilot"} else None
        )
        if review.get("failure_action") != expected_failure_action:
            _fail(errors, "task.review.failure_action", "must return to the worker runtime")

    _scan_secrets(value, "task", errors)
    return errors


def _has_cycle(tasks: dict[str, dict[str, Any]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> bool:
        if task_id in visiting:
            return True
        if task_id in visited:
            return False
        visiting.add(task_id)
        for dependency in tasks[task_id].get("dependencies", []):
            if dependency in tasks and visit(dependency):
                return True
        visiting.remove(task_id)
        visited.add(task_id)
        return False

    return any(visit(task_id) for task_id in tasks)


def validate_task_set(
    tasks: list[Any],
    manifest_sources: dict[str, dict[str, Any]],
    *,
    verify_source_files: bool = False,
) -> list[str]:
    """Validate task envelopes and their dependency graph."""
    errors: list[str] = []
    if not isinstance(tasks, list) or not tasks:
        return ["tasks: must be a non-empty array"]
    identifiers: dict[str, dict[str, Any]] = {}
    idempotency_keys: dict[str, str] = {}
    for index, task in enumerate(tasks):
        task_errors = validate_task(task, manifest_sources, verify_source_files=verify_source_files)
        errors.extend(f"tasks[{index}].{error.removeprefix('task.') if error.startswith('task.') else error}" for error in task_errors)
        if isinstance(task, dict):
            task_id = task.get("task_id")
            if isinstance(task_id, str):
                if task_id in identifiers:
                    errors.append(f"tasks[{index}].task_id: duplicate task id {task_id}")
                identifiers[task_id] = task
            key = task.get("idempotency_key")
            if isinstance(key, str):
                if key in idempotency_keys:
                    errors.append(f"tasks[{index}].idempotency_key: duplicate key also used by {idempotency_keys[key]}")
                idempotency_keys[key] = task_id if isinstance(task_id, str) else "unknown"
    for task_id, task in identifiers.items():
        for dependency in task.get("dependencies", []):
            if dependency not in identifiers:
                errors.append(f"tasks[{task_id}].dependencies: unknown task {dependency}")
    if identifiers and _has_cycle(identifiers):
        errors.append("tasks.dependencies: dependency graph contains a cycle")
    return errors


def validate_review_result(review: Any, task: dict[str, Any]) -> list[str]:
    """Validate one Codex review result against its reviewed task."""
    errors: list[str] = []
    value = _mapping(review, "review", errors)
    if value is None:
        return errors
    _keys(value, EXPECTED_REVIEW_RESULT_KEYS, "review", errors)
    _required(value, EXPECTED_REVIEW_RESULT_KEYS, "review", errors)
    if value.get("schema") != "chess-commander.paperclip-review.v1":
        _fail(errors, "review.schema", "must equal chess-commander.paperclip-review.v1")
    if value.get("task_id") != task.get("task_id"):
        _fail(errors, "review.task_id", "must match the reviewed task")
    if value.get("idempotency_key") != task.get("idempotency_key"):
        _fail(errors, "review.idempotency_key", "must match the reviewed task")
    repository = task.get("repository") if isinstance(task.get("repository"), dict) else {}
    if value.get("branch") != repository.get("work_branch"):
        _fail(errors, "review.branch", "must match the task work branch")
    review_policy = task.get("review") if isinstance(task.get("review"), dict) else {}
    maximum = review_policy.get("max_fix_rounds", 0)
    if not isinstance(value.get("round"), int) or isinstance(value.get("round"), bool) or not 1 <= value["round"] <= maximum:
        _fail(errors, "review.round", "must be within the task's allowed fix rounds")
    _enum(value.get("decision"), "review.decision", {"pass", "fix_required"}, errors)
    checked = _unique_strings(value.get("checked"), "review.checked", errors, minimum=4)
    if set(checked) != REQUIRED_REVIEW_CHECKS:
        _fail(errors, "review.checked", "must contain exactly diff_scope, tests, source_boundary, and evidence")
    findings = _unique_strings(value.get("findings"), "review.findings", errors)
    requested_fixes = _unique_strings(value.get("requested_fixes"), "review.requested_fixes", errors)
    _unique_strings(value.get("evidence"), "review.evidence", errors, minimum=1)
    if value.get("decision") == "pass" and (findings or requested_fixes):
        _fail(errors, "review", "pass results cannot contain findings or requested fixes")
    if value.get("decision") == "fix_required" and not requested_fixes:
        _fail(errors, "review.requested_fixes", "fix_required results must list requested fixes")
    _scan_secrets(value, "review", errors)
    return errors


def load_tasks(path: Path) -> list[Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(document, dict) and "tasks" in document:
        return document["tasks"]
    return [document]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path, help="one task object or {\"tasks\": [...]} JSON")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--verify-source-files", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    try:
        tasks = load_tasks(args.task_file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid task document: {exc}", file=sys.stderr)
        return 2
    manifest_sources, manifest_errors = load_source_manifest(args.repo_root / "SOURCE_MANIFEST.json")
    errors = manifest_errors + validate_task_set(
        tasks,
        manifest_sources,
        verify_source_files=args.verify_source_files,
    )
    result = {"valid": not errors, "task_count": len(tasks) if isinstance(tasks, list) else None, "errors": errors}
    if args.json_output:
        print(json.dumps(result, indent=2))
    elif errors:
        print("invalid")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"valid ({result['task_count']} task(s))")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
