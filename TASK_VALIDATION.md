# Paperclip task validation and review loop

`tools/validate_task.py` is the pre-queue gate for Phase 1 Chess Commander
work. It validates a task envelope before Paperclip creates or queues the
corresponding issue.

## What the validator checks

- schema version, required fields, unknown fields, and field types;
- Phase 1 task kind: `install`, `coding`, `assessment`, or `evidence`;
- repository owner/name, `main` base branch, dedicated work branch, and
  repository-relative path allowlist;
- P40 coder-mode worker selection or one of the two isolated Copilot fallback
  accounts;
- account-specific exclusive resource policy with `max_concurrency: 1`;
- bounded timeout, retry count, and reconcile-before-retry behavior;
- unique task IDs, unique idempotency keys, known dependencies, and an
  acyclic dependency graph when validating a task set;
- source image paths and SHA-256 values against `SOURCE_MANIFEST.json`;
- optional live source-file size and hash verification;
- non-empty outputs and executable acceptance criteria;
- mandatory Codex review, return-to-worker fix routing, and a maximum of two
  fix rounds; and
- credential/private-key patterns in the complete payload.

The validator does not execute a task, install software, mutate Paperclip, or
trust a successful worker exit as proof of acceptance.

## Usage

From the repository root:

    python3 tools/validate_task.py examples/phase1-task-set.json
    python3 tools/validate_task.py examples/phase1-task-set.json --json
    python3 tools/validate_task.py examples/phase1-task-set.json --verify-source-files
    python3 tools/validate_review.py examples/phase1-task-set.json examples/phase1-review-pass.json --task-id phase1-toolchain

The first two commands validate the task envelope and manifest. The final
command also checks the two SSD files currently recorded in the manifest. A
non-zero exit code means the task set must not be queued.

The machine-readable contract is:

    contracts/paperclip-task.v1.schema.json

    contracts/paperclip-review.v1.schema.json

The example task set demonstrates a toolchain task followed by an Acornsoft
smoke-load task. Thompson and later assessment tasks use the same envelope.
The review examples demonstrate both an accepted Codex review and a
`fix_required` result that can be returned to P40.

## Paperclip/Codex/P40 review loop

Paperclip can represent the lifecycle using a parent issue, child issues,
assignees, comments, heartbeat runs, and explicit status transitions. The safe
loop is:

1. P40 proposes a task set.
2. The coordinator validates the complete task set locally.
3. Paperclip creates the parent and child issues only after validation.
4. Paperclip assigns the child task to the P40 coder runtime.
5. P40 completes the bounded task and records structured evidence.
6. The coordinator creates or wakes a Codex review task associated with the
   same parent/task ID and branch.
7. Codex checks the diff, acceptance criteria, source boundary, tests, and
   evidence. It returns a structured `pass` or `fix_required` result.
8. On `pass`, Paperclip marks the task ready for the next dependency.
9. On `fix_required`, Paperclip returns the same task to its worker with the
   review findings, increments the fix-round count, and preserves the same
   idempotency key.
10. If P40 reaches a terminal failure, the coordinator validates a Copilot
    fallback envelope, selects one isolated account, and queues the fallback
    task with a `copilot:<account>` resource lock.
11. Copilot results go through the same Codex review and bounded-fix loop.
12. After two failed fix rounds, the task becomes blocked and requires human
    review; it is not silently retried again.

Paperclip's current CLI exposes the primitives needed for this coordination:
child issue creation, issue assignment/update, comments, heartbeat-run
readback, agent wakeups, and run cancellation. The conditional step that
interprets Codex's result and returns a failed task to P40 requires an explicit
coordinator or bridge; it should not be hidden inside a prompt.

Paperclip therefore can manage this workflow, but it does not automatically
provide an arbitrary P40/Copilot fallback loop merely because the agents exist.
The bridge must enforce the state machine, select the account-specific worker,
and call the validator before creating every retry or fix task.

The two Copilot mappings are represented by account-specific Paperclip agents:

- `Copilot Agent Fallback` -> `andyfied-agent` ->
  `/home/andyfied/.local/bin/hermes-copilot-agent`;
- `Copilot Thargoid Fallback` -> `andyfied-Thargoid` ->
  `/home/andyfied/.local/bin/hermes-copilot-thargoid`.

Each launcher selects a separate `COPILOT_HOME` and `GH_CONFIG_DIR`. Tokens are
not injected into Paperclip payloads or repository files. Both agents have
heartbeat disabled, maximum concurrency one, low-trust review permissions, and
are only woken by the routing bridge after a terminal P40 failure.

The compute01 routing bridge is:

    /home/andyfied/src/workstation/hosts/compute01/paperclip_task_router.py

It performs a dry-run decision by default. Its `--apply` path first reconciles
the existing Paperclip issue and active run, then reassigns that same issue to
one active Copilot account, wakes that account with the unchanged idempotency
key, and verifies the assignment. It never creates a replacement task. Every
successful or fallback result routes to Review Worker, whose primary reviewer
is the isolated Codex peer and whose only reviewer failover is Air Review.

## Required state machine

    proposed
      -> validated
      -> queued
      -> running
      -> review_pending
      -> accepted

    review_pending --fix_required--> fixing
    fixing -> running
    fixing --max rounds reached--> blocked

Any ambiguous worker response goes to `reconcile_pending`, where Paperclip
reads the existing run, issue, branch, and work products before deciding
whether a retry is safe. It must never create a new task solely because a
response was lost.

## Security boundary

Task payloads may contain repository-relative paths and the two explicitly
manifested external SSD paths. They must not contain credentials, provider
keys, unrestricted host paths, copied SSD data, emulator state, or raw model
secrets. Review evidence should reference bounded artifacts rather than embed
sensitive logs in Paperclip comments.
