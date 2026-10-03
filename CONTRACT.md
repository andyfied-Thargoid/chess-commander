# Common choose-move contract

This is the boundary between a Chess Commander backend and the future Punchess
player client. It is deliberately independent of the BBC emulator and of the
P40 transport.

Schema: `contracts/choose-move.v1.schema.json`

## Request

A backend receives:

- `request_id`: unique identifier for one decision attempt;
- `position.fen`: canonical current position;
- `position.moves_uci`: complete move history in UCI, oldest first;
- `legal_moves_uci`: the referee-derived legal move set for the current turn;
- `clock`: remaining clocks and increment in milliseconds;
- `backend`: exactly `acornsoft` or `thompson`;
- `strategy_revision`: extracted/native strategy revision;
- `model` and `prompt_revision`: nullable P40 attribution fields.

The backend must treat FEN and the legal move list as input data, not as an
invitation to mutate the referee state. It must return one move from the
provided legal set or a structured failure. A backend must not invent a move,
submit HTTP requests to Punchess, or retry a move submission.

## Response

A successful response has this shape:

```json
{
  "request_id": "...",
  "status": "ok",
  "move_uci": "e2e4",
  "evidence": {
    "backend": "acornsoft",
    "source_sha256": "...",
    "strategy_revision": "oracle-v0",
    "model": null,
    "prompt_revision": null,
    "candidates_uci": ["e2e4", "d2d4"],
    "selected_move_uci": "e2e4",
    "latency_ms": 123,
    "seed": null,
    "trace_ref": null,
    "failure_reason": null
  }
}
```

`status` is either `ok` or `error`. An error response has `move_uci: null`
and retains the same evidence fields, with `failure_reason` set to a stable
category such as `invalid_position`, `no_legal_move`, `timeout`,
`emulator_failure`, or `model_output_invalid`.

Required invariants:

1. `move_uci` is non-null only when `status` is `ok`.
2. A successful `move_uci` must be an exact member of `legal_moves_uci`.
3. `selected_move_uci` must equal `move_uci`.
4. `backend` and `source_sha256` identify the implementation that actually
   produced the answer.
5. `latency_ms` is measured by the caller around the decision, not guessed by
   the model.
6. `trace_ref` points to a local evidence artifact only; it must never contain
   credentials, raw prompts with secrets, or an unrestricted host path.
7. An ambiguous transport result is not a successful move response. The client
   must re-read Punchess state before deciding whether a new decision attempt
   is needed.

The BBC oracle adapters may leave `model`, `prompt_revision`, and `seed` null.
They must populate the source hash and strategy revision. Native backends and
P40 calls use the same response shape, so comparison tooling can distinguish
legal agreement from exact reference agreement.
