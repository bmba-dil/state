# Deviation Rules & Tiered Autonomy (Canonical, v41)

> **Phase:** 405
> **Status:** Canonical (v41)
> **Requirements covered:** DEV-01..DEV-07
> **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md).
> **Sibling specs:** SUBAGENT-MANAGEMENT.md (subagent typed-spawn + spot-check + crash recovery — Phase 405 Plan 02-03).
> **Naming discipline:** All identifiers are `STATE-*` / `state-*`. Past-phase `STATE-*` trailer references (note: any `S-D-*` legacy mentions inherited from gsd-2 design heritage are deferred-rename items handled in `<deferred>`).
> **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.

The harness governs deviation from a Step's locked PLAN via a 4-rule framework. Each rule has a category (bug fix / missing critical functionality / blocking issue / architectural change), a `max-attempts` cap, a commit-prefix convention (`fix:` / `feat:` / `refactor:` / etc. per gsd-2 `COMMIT_TYPE_RULES` keyword inference), and an escalation path. The agent declares the rule via the `log_deviation` MCP tool; the daemon cross-validates against pure-machine signals (`issue_signature` recomputation, the arch-pattern allowlist, `scope_deviation_request` correlation from Phase 404 SRP-04, and per-tuple cap check). Rule 4 (architectural) is structurally always-human-gate — no autonomy mode can bypass. Tiered autonomy (`--tiered` default / `--full-yolo` / `--conservative`) gates the other rule outcomes; per-Slice autonomy override is allowed via Slice frontmatter (DEV-06). Three-counter independence (APG / PRF / DEV) is preserved per gsd-2 `loop-control.md` §0 Correction 1 — the deviation chain is the third independent counter alongside Phase 404's `paralysis_event` (APG) and `gate_strike` (PRF) chains.

---

## The Four Rules

The four rules partition all deviation classes the harness recognises. They are mutually exclusive at any given `(task_id, issue_signature)` tuple — an issue belongs to exactly one rule at the time of declaration, and the daemon's cross-validation flow (Section 4) decides the final `rule_id` after correcting agent mis-classification. Per-rule semantics follow.

## Rule 1: Auto-fix Bugs (DEV-01)

- **Category:** wrong queries, logic errors, type errors, null-pointer dereference, off-by-one boundary errors, off-by-one indexing errors, undefined-behavior dispatches, incorrect predicate inversion, sign-flip arithmetic errors, branch-coverage holes that produce wrong output.
- **max-attempts: 3** (cap enforced per `(task_id, rule_id=1, issue_signature)` tuple — different `issue_signature` values do not poison each other).
- **Commit-prefix convention:** `fix: <description>` per gsd-2 `COMMIT_TYPE_RULES` (`git-service.ts:616`); trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 1`, `STATE-DeviationAttempt: K` where K ∈ {1,2,3}.
- **Escalation path:** after 3 failed attempts on the same tuple, the daemon emits `state.step.deviation_cap_exceeded` and force-promotes the chain to Rule 4. Rationale (encoded as cross-validation step 5 verdict): persistent bug-fix failures on the same `issue_signature` indicate a structural / architectural problem requiring human resolution, not another isolated bug-fix attempt. The 4th attempt's Rule 4 promotion is a STRUCTURAL invariant — no autonomy mode bypasses.

## Rule 2: Auto-add Critical Functionality (DEV-02)

- **Category:** missing error handling, missing input validation, missing null checks, missing auth on protected routes, missing DB indexes for hot-path queries, missing rate-limit decorators, missing CSRF guards, missing schema-validation calls before persistence, missing audit-log emissions.
- **max-attempts: 3** (cap enforced per `(task_id, rule_id=2, issue_signature)` tuple).
- **Commit-prefix convention:** `feat: <description>` if adding a new capability (new route handler, new validator); `fix: <description>` if patching a missed safety check (gsd-2 keyword inference applies — `infer_commit_type` decides from the diff text and modified file paths); trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 2`, `STATE-DeviationAttempt: K`.
- **Escalation path:** documented in `stepNSUMMARY.md` `## Deviations` section (auto-rendered by the projector — Section 10). After 3 failed attempts: same `state.step.deviation_cap_exceeded` -> Rule 4 promotion as Rule 1. The escalation justification: a critical-functionality addition that fails 3 times is no longer a localized correctness fix; it is structural.

## Rule 3: Auto-fix Blocking Issues (DEV-03)

- **Category:** missing dependency at runtime (`ImportError`), wrong types in an upstream contract (mypy / pyright failure that blocks the test step), broken imports after a refactor, build config errors (`pyproject.toml` malformed but not a NEW dep), missing environment variable, CI lint configuration drift, formatter (Ruff) parse errors.
- **max-attempts: 3** (cap enforced per `(task_id, rule_id=3, issue_signature)` tuple).
- **Commit-prefix convention:** `fix: <description>` (typically — most blocking issues are mechanical fixes); `chore: <description>` for tooling-only adjustments (gsd-2 `COMMIT_TYPE_RULES` decides per the keyword table). Trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 3`, `STATE-DeviationAttempt: K`.
- **Escalation path:** after 3 failed attempts -> `checkpoint:decision` (Phase 403 task-type) presenting the resolution options to the human via opencode `question` tool. **Diverges from Rules 1-2** (which promote to Rule 4): blocking issues are often choice-shaped (which dep to pin? roll back the import? branch on the upstream contract?) rather than architectural-shaped. `checkpoint:decision` lets the human pick from a curated option set without forcing Rule 4's pros/cons-table machinery.

## Rule 4: Architectural Changes (DEV-04)

- **Category:** new DB table (not a column addition), major schema change (e.g., renaming a primary key, splitting a table), switching frameworks (Pydantic v2 -> v3, FastAPI -> Starlette), new infrastructure (CDN, queue, cache, sidecar service), introducing a new external SaaS dependency, adding a new top-level package under `src/state_*/`, registering a new MCP tool, adding a new dep to `pyproject.toml`.
- **max-attempts: 1** (Rule 4 is single-shot: render `question` -> resolution arrives -> attempt complete; no retry loop).
- **Commit-prefix convention:** typically `feat: <description>` (architectural changes most commonly add capability); occasionally `refactor: <description>` for pure structural reshuffles. Trailers `STATE-Task: <step_id>`, `STATE-DeviationRule: 4`, `STATE-DeviationAttempt: 1`.
- **Escalation path:** ALWAYS human gate via opencode `question` tool with a pros/cons table assembled from the agent's `alternatives: list[Rule4Option]` payload. Never auto-approved, even under `--full-yolo`. The `log_deviation(rule_id=4, ...)` MCP handler synchronously renders the question; there is no autonomy short-circuit branch in the daemon's middleware. The `alternatives` payload is REQUIRED (Pydantic-validated; at least 2 options; exactly one `recommended=True`).

**Rule-4 always-stop is STRUCTURAL, not policy.** The implementation guarantee: there is no `if mode == 'full-yolo' bypass` code path. The `log_deviation(rule_id=4)` MCP handler unconditionally renders opencode `question`. This pattern mirrors gsd-2's MCP-tool-call-as-canonical-agent-intent-signal (`tool-system.md` §5); state extends with strict cross-validation. The absence of an autonomy bypass branch in `state_build/deviation/log_deviation.py` is the structural enforcement — code review and CI grep both target this absence as a non-negotiable invariant.

### Inter-rule promotion paths (escalation graph)

The escalation graph between the four rules is:

- Rule 1 -> Rule 4 (on cap exceeded; cross-validation step 5).
- Rule 1 -> Rule 4 (immediate; cross-validation step 3 arch-pattern match).
- Rule 2 -> Rule 4 (on cap exceeded; cross-validation step 5).
- Rule 2 -> Rule 4 (immediate; cross-validation step 3 arch-pattern match).
- Rule 3 -> `checkpoint:decision` (on cap exceeded; cross-validation step 5). Note: this is NOT a Rule 4 promotion — Rule 3's escalation path diverges intentionally because blocking issues are choice-shaped rather than architectural-shaped.
- Rule 4 -> terminal (never escalates to anything else; the human gate is the terminal resolution).

The escalation graph is encoded in the daemon's `escalate_chain(rule_id, count, signature) -> EscalationVerdict` helper in `state_build/deviation/escalation.py`. The helper returns one of: `EscalationVerdict.continue_chain` (within cap), `EscalationVerdict.promote_to_rule_4`, `EscalationVerdict.fire_checkpoint_decision`, `EscalationVerdict.terminal_human_gate`. The verdict drives the daemon's downstream event emissions (`deviation_cap_exceeded` -> checkpoint render OR Rule 4 question render).

### Rule-distinguishing examples

To anchor the rule definitions concretely, examples of correct classification:

- `KeyError: 'user_id'` in a request handler that should have validated input -> **Rule 2** (missing input validation).
- `TypeError: NoneType has no attribute 'serialize'` after a refactor that introduced a `None` return path -> **Rule 1** (logic error: missing None-guard).
- `ImportError: cannot import name 'orjson_loads' from 'state_core.serde'` after deleting a helper -> **Rule 3** (blocking; broken import).
- Adding `redis>=5.0` to `pyproject.toml` to introduce caching layer -> **Rule 4** (new dependency; arch-pattern allowlist match).
- Creating `src/state_telemetry/__init__.py` to add a new top-level package -> **Rule 4** (new top-level package init; arch-pattern allowlist match).
- Bumping `pydantic>=2.10` to `pydantic>=2.13` -> **Rule 3** (BUMP, not ADD; routine dep update).

---

## log_deviation MCP Tool

### Signature (Pydantic-typed)

Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Deviation classification (DEV-01..04 expanded)" subsection:

```python
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict

def log_deviation(
    rule_id: Literal[1, 2, 3, 4],
    issue_signature: str,                                # caller computes; daemon recomputes for verification
    classification_source: Literal[
        "agent_declared",                                # agent self-classified
        "harness_promoted",                              # auto-promoted by file-path heuristic
        "arch_pattern_match",                            # forced Rule 4 by allowlist match
    ],
    justification: str,                                  # ≤1KB agent rationale
    error_excerpt: str,                                  # ≤2KB; gsd-2 formatFailureContext truncation discipline
    alternatives: list["Rule4Option"] | None = None,    # REQUIRED for rule_id=4; otherwise None
) -> "DeviationLogResult": ...

class Rule4Option(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str                                            # short identifier shown in opencode question
    pros: str                                            # ≤512 chars
    cons: str                                            # ≤512 chars
    recommended: bool                                    # exactly one option in the list should be True

class DeviationLogResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deviation_event_id: str
    attempt_number: int                                  # 1..3 for rules 1-3; always 1 for rule 4
    cap_exceeded: bool                                   # True when this attempt is the 4th — auto-escalation triggered
    classification_accepted: bool                        # False if cross-validation rejected the declared rule_id
    rejection_reason: str | None                         # set when classification_accepted is False
```

### MCP tool registration

The tool is registered under the `state-build` MCP server at module path `state_build/deviation/log_deviation.py`. The MCP tool name is the literal string `log_deviation`. The handler is invoked from the daemon's middleware (single source of truth — daemon decides). The handler returns `DeviationLogResult` synchronously. The MCP tool surface is exposed only when the active mode is `build` (or `both`); never registered under the `state-teach` MCP server. Mode-isolation is enforced at the MCP server registration step, not at the tool-call step — the tool is simply not visible to teach-mode sessions.

### Caller responsibilities (agent side)

- **Compute `issue_signature`** via the SHA-256 16-char hex function defined in Section 7; pass the value as input to `log_deviation`. The daemon recomputes for verification (cross-validation step 1) and rejects on disagreement.
- **Set `classification_source = "agent_declared"`** for self-classified deviations. The daemon MAY override to `"harness_promoted"` (cross-validation step 3) or `"arch_pattern_match"` (step 4) before event emit. The final value on the persisted `Deviation` event is server-recomputed.
- **For `rule_id == 4`:** supply at least 2 `Rule4Option` entries with exactly one `recommended=True`. The Pydantic root validator on the inbound payload enforces this; the daemon also re-validates server-side (defense-in-depth). Pros/cons strings ≤512 chars each (Pydantic-validated).
- **Truncation discipline:** `justification` ≤ 1KB, `error_excerpt` ≤ 2KB (gsd-2 `formatFailureContext` truncation pattern; mirrors Phase 404's bounded-truncation 2KB/10KB discipline). Larger inputs are rejected at Pydantic parse time; the agent must truncate caller-side before invocation.

### Return shape

`DeviationLogResult` has 5 fields with the following semantics:

- `deviation_event_id`: ULID; the primary key of the just-emitted `state.step.deviation_logged` event. The agent SHOULD record this ID in the subsequent `commit_sha`-resolution event (Section 9) so the projector (Section 10) can join the resolution to the original deviation row.
- `attempt_number`: 1..3 for Rules 1-3 (computed by the daemon from the per-tuple counter +1); always 1 for Rule 4 (single-shot). Server-recomputed; agent-emitted value is ignored.
- `cap_exceeded`: `True` when this attempt is the 4th on the same `(task_id, rule_id, issue_signature)` tuple — auto-escalation already triggered server-side (a `state.step.deviation_cap_exceeded` event has been emitted before `log_deviation` returns).
- `classification_accepted`: `False` if cross-validation rejected the declared `rule_id` (the rejection event has already been emitted; the agent must re-call `log_deviation` with corrected `rule_id` + payload).
- `rejection_reason`: set when `classification_accepted` is `False`. One of: `"issue_signature_mismatch"`, `"rule_4_alternatives_missing"`, `"rule_4_recommended_invalid"`, `"arch_pattern_promotion_required"`, `"scope_deviation_correlation_promoted"`. The agent SHOULD use this value to construct the corrected re-call payload — for example, `"arch_pattern_promotion_required"` indicates that the agent must escalate to `rule_id=4` and supply an `alternatives` list before re-calling.

### Idempotency and re-call semantics

`log_deviation` is NOT idempotent at the (task_id, issue_signature) tuple — every accepted call increments `attempt_number` for Rules 1-3. The agent SHOULD NOT re-call `log_deviation` to "report progress" on an in-flight attempt; instead, the agent calls `log_deviation` once per discrete attempt at fixing the issue, and the resolution event (Section 9) marks the attempt's outcome.

For rejected calls (`classification_accepted=False`), the agent's corrective re-call is treated as a fresh attempt for cap-counting purposes only if the previous rejected call's `rule_id` was within {1, 2, 3}. Rejection on `rule_id=4` cross-validation (steps 2) does not increment the cap counter because the call never reached the success path; the agent's corrective re-call replaces the rejected one for audit purposes (via `agent_response_summary` cross-link).

### Worked example: agent / daemon round-trip

A worked example of the agent-daemon interaction for Rule 1 / attempt 2:

1. Agent runs failing test, captures `pytest_failure` with file/line/token.
2. Agent computes `issue_signature` via `compute_issue_signature(ErrorKind.pytest_failure, "tests/state_core/test_eventstore.py", 87, "assert_event_emitted")`.
3. Agent calls `log_deviation(rule_id=1, issue_signature=..., classification_source="agent_declared", justification="...", error_excerpt="..."[:2048])`.
4. Daemon runs cross-validation steps 1-5 (all pass).
5. Daemon emits `state.step.deviation_logged` with `attempt_number=2`, `resolution="pending"`.
6. Daemon returns `DeviationLogResult(deviation_event_id="...", attempt_number=2, cap_exceeded=False, classification_accepted=True, rejection_reason=None)`.
7. Agent attempts the fix, commits with trailers including `STATE-DeviationRule: 1`, `STATE-DeviationAttempt: 2`.
8. Agent (or daemon's post-commit hook) emits `state.step.deviation_resolution_recorded` to mark `resolution="auto_fix_succeeded"` and link `commit_sha`.

---

## Harness Cross-Validation Flow

Post-call (before event emit), the daemon runs a 5-step pure-machine validation against the proposed deviation. Mismatch -> rejection event + `classification_accepted=False` return. Mirrors Phase 404's diff-the-proposed-write pattern (cross-validation against deterministic signals before the side-effecting event lands). The 5 steps run in deterministic order; earlier steps short-circuit (return early on rejection). Step 5 (cap check) runs LAST because the cap-exceeded path still emits the `deviation_logged` event for audit-trail completeness.

### Numbered protocol

1. **Re-compute `issue_signature`** from the current `(task_id, rule_id, error_kind, file:line, matched_token)` tuple via the SHA-256 function defined in Section 7. Compare with the agent-supplied value. Disagreement -> emit `state.step.deviation_classification_rejected` with `reason: "issue_signature_mismatch"`, return early with `classification_accepted=False` and `rejection_reason="issue_signature_mismatch"`.

2. **Rule-4 alternatives check:** if `rule_id == 4`, require `alternatives is not None and len(alternatives) >= 2 and sum(o.recommended for o in alternatives) == 1`. Mismatch -> emit `state.step.deviation_classification_rejected` with `reason: "rule_4_alternatives_missing"` (when `alternatives` is None or shorter than 2) or `"rule_4_recommended_invalid"` (when zero or multiple `recommended=True` entries exist). Return early with `classification_accepted=False`.

3. **Rule-4 auto-promotion (arch-pattern allowlist):** scan the agent's recent `Write/Edit` targets (sourced from `tool.execute.before` event audit, last 60s window scoped to the current `session_id`) against `ARCH_PATTERN_ALLOWLIST` (Section 5). If `rule_id ∈ {1, 2, 3}` but a recent write target hits the allowlist -> emit `state.step.deviation_classification_rejected` with `reason: "arch_pattern_promotion_required"`; the agent must re-call with `rule_id=4` and an `alternatives` payload. Return early with `classification_accepted=False`. The cross-validation flow sets `classification_source="arch_pattern_match"` on the final accepted re-call (server-recomputed).

4. **`scope_deviation_request` correlation:** if there is an open `state.step.scope_deviation_request` (Phase 404 SRP-04 territory) for this `(task_id, requested_path)` AND the path matches the arch-pattern allowlist, force `rule_id=4`. Emit `state.step.deviation_classification_rejected` with `reason: "scope_deviation_correlation_promoted"` if the agent supplied a lower `rule_id`. Return early with `classification_accepted=False`. The daemon's `classification_source` projection sets the final value to `"harness_promoted"` on the accepted re-call. This step links the deviation chain to the scope-prohibition machinery from Phase 404 — see `.planning/milestones/v41/phases/404/specs/SCOPE-PROHIBITION.md` SRP-04 for the upstream event shape.

5. **Cap check:** query event store for `count(state.step.deviation_logged WHERE (task_id, rule_id, issue_signature) = ?)`. If `count >= 3` (this would be the 4th attempt) -> set `cap_exceeded=True` on the return; emit `state.step.deviation_cap_exceeded`; auto-escalate per the rule's escalation path (Rule 3 -> `checkpoint:decision`; Rules 1-2 -> force Rule-4 promotion). The event emit for the original `deviation_logged` STILL happens (audit-trail completeness) but with `resolution: "aborted_chain"` set at emission time.

Steps 1-5 run in deterministic order. Step 5 (cap check) runs LAST because the cap-exceeded path still emits the `deviation_logged` event for audit. Earlier steps short-circuit (return early on rejection). v14 implements as a synchronous chain inside `state_build/deviation/log_deviation.py`. Mirrors Phase 404 PROOF-GATE.md Section 6 strike-counter-evaluated-at-completion-claim ordering discipline.

### Server-side recomputation discipline

The daemon recomputes `issue_signature`, `attempt_number`, `cap_exceeded`, and `classification_source` from authoritative server-side state; agent-emitted values for these fields are recomputed at the cross-validation boundary (mirrors Phase 404's PRF `overall_passed` server-recomputation pattern + gsd-2's `server-recomputation-of-llm-emitted-fields.md`). Mismatch between agent input and server recomputation triggers the rejection events listed above. The `classification_source` field's final value is server-set: `agent_declared` (default) -> `harness_promoted` (cross-validation step 3 override) -> `arch_pattern_match` (step 4 override). The agent's emitted `classification_source` value is treated as a hint, not as authoritative.

---

## Arch-Pattern Allowlist (Rule-4 Detection)

The canonical pure-machine signal for an architectural change is a `Write/Edit` target matching the arch-pattern allowlist. Mirrors Phase 404's `READ_ONLY_PATTERNS` + `WRITE_SYSCALL_PATTERNS` single-module shape; lives at `state_build/deviation/arch_patterns.py`. The allowlist is a flat list of `re.Pattern` objects; match is first-match-wins against the normalised path.

### Regex allowlist

Verbatim from `.planning/milestones/v41/phases/405/405-CONTEXT.md` `<decisions>` "Rule-4 detection (DEV-04, arch-pattern allowlist)" subsection:

```python
import re

ARCH_PATTERN_ALLOWLIST: list[re.Pattern] = [
    re.compile(r"^alembic/(?!README)"),                          # any non-README path under alembic/
    re.compile(r"(?:^|/)migrations/[^/]+\.(py|sql)$"),
    re.compile(r"(?:^|/)schema\.(sql|prisma|graphql)$"),
    re.compile(r"^pyproject\.toml$|^uv\.lock$"),                # dep-list mutations (planner validates ADD vs BUMP)
    re.compile(r"^src/state_[a-z_]+/__init__\.py$"),            # new top-level package init creation
    re.compile(r"(?:^|/)mcp/tools/[^/]+\.py$"),                  # new MCP tool registrations
]
```

### Match semantics

- Match is against the **proposed write target path** (the file path the agent attempts to Write/Edit), intercepted via `tool.execute.before`. Not against existing on-disk content. The intercept point is the same as Phase 404's read-only-write prohibition gate; the two gates share the same audit window.
- Paths are normalised to repo-root-relative POSIX form (forward slashes always) before matching. Symlinks resolved; `.`/`..` segments normalised via `pathlib.PurePosixPath`. Absolute paths that fall outside the worktree root are rejected at a separate gate (Phase 404 SRP-01 territory) before reaching this check.
- First-match-wins; the order in the list is not semantically significant beyond determinism (mirrors gsd-2 `dispatch-rules-table.md` first-match-wins pattern). The list is a `list[re.Pattern]`, not a `set[...]`, to preserve insertion-order determinism for audit-log replay.

### ADD vs BUMP discrimination (pyproject.toml / uv.lock)

- **Pure-machine diff parse.** Lines beginning `+` matching regex `^\+\s*"[a-zA-Z0-9_\-]+>=` match the **ADD** pattern (adding a new dependency declaration).
- Lines matching `-\s*"X>=A.B"\s*\n\+\s*"X>=C.D"` (same package name X on both lines, only version delta) match the **BUMP** pattern.
- **ADD -> arch-pattern match (force Rule 4).** A new dependency is an architectural decision — it expands the project's supply chain and threat model, requires license review, and is irreversible without further cleanup.
- **BUMP -> no auto-promotion.** Version pin updates are routine (Rule 3 or below); the existing CI matrix and lockfile-update flows handle them without architectural review.
- **Multi-line YAML/TOML edge cases** (e.g., `pyproject.toml` `dependencies = [...]` array spanning many lines with one declaration per line): the planner pins the exact tokenizer in v14; for now the discriminator regex above is the starter set. v14 may upgrade to a TOML-aware parser if false-positive ADD/BUMP discrimination becomes a problem.

### Module ownership

Single-source-of-truth module: `state_build/deviation/arch_patterns.py`. Exports:

- `ARCH_PATTERN_ALLOWLIST: list[re.Pattern]` — the allowlist constant as rendered above.
- `match_arch_pattern(path: str) -> bool` — boolean predicate; returns `True` on first match.
- `classify_diff_kind(file_path: str, diff_text: str) -> Literal['ADD', 'BUMP', 'NEITHER']` — diff-text analyser for `pyproject.toml` / `uv.lock` to discriminate ADD vs BUMP.

v14 implements the module; v15 wires the daemon middleware to call `match_arch_pattern` during cross-validation step 3 and `classify_diff_kind` for the ADD/BUMP discriminator in cross-validation step 4 (when a `pyproject.toml` or `uv.lock` change is the trigger). The module ships with unit tests asserting the regex behaviour against a fixture path corpus rendered in `tests/state_build/deviation/test_arch_patterns.py`.

### Allowlist evolution policy

The allowlist starts at 6 patterns intentionally. Adding a new pattern is itself a Rule 4 architectural decision — the act of expanding the Rule 4 surface is, by construction, an architectural choice that requires human approval. New pattern additions follow the same `log_deviation(rule_id=4)` flow as any other architectural change. The single-source-of-truth module path `state_build/deviation/arch_patterns.py` is the only location where the allowlist may be edited; CI lint rejects allowlist modifications landed via any other path. This bootstrap discipline mirrors gsd-2's approach to `READ_ONLY_PATTERNS` curation at `branch-patterns.ts` — the pattern list is treated as project-level policy, not as a per-Slice configuration knob.

### Negative-space documentation (what is NOT a Rule 4 path)

The allowlist is intentionally narrow. Examples of paths that DO NOT trigger Rule 4 promotion:

- `src/state_*/**/*.py` (any file under an existing top-level package — these are routine edits within established architecture).
- `tests/**/*.py` (test changes — even adding new test files — are Rule 1 or Rule 2 territory, not architectural).
- `docs/**/*.md` (documentation changes — Rule 1 if fixing typos, Rule 2 if adding missing docs).
- `.planning/**/*.md` (planning artefacts — handled by the GSD workflow, not the deviation chain).
- `pyproject.toml` lines that BUMP an existing dependency (the BUMP regex catches these and skips auto-promotion).

The negative-space documentation is critical because false-positive Rule 4 promotions block routine work; the allowlist is calibrated to catch only the truly architectural cases. v14 ships with a regression corpus that exercises both positive and negative cases.

### Commit Trailer Convention (STATE-* Naming Discipline)

State keeps gsd-2's 7-rule keyword-based type-inference table (`COMMIT_TYPE_RULES`, sourced from `git-service.ts:616`) unchanged for the conventional-commit prefix selection. State adds new trailers on top of the inferred prefix:

```
fix: resolve null-pointer in CompactionSnapshot.serialize

Restore the missing None-guard before orjson.dumps.

STATE-Task: 405-deviation-rules/step-2
STATE-DeviationRule: 1
STATE-DeviationAttempt: 1
```

- `STATE-Task: <step_id>` — mandatory on every commit produced inside a Step. Identifies the originating step for audit and for the SUMMARY projector's join key.
- `STATE-DeviationRule: N` (N ∈ {1, 2, 3, 4}) — mandatory on every commit produced as the resolution of an open deviation. Auditor grep target enumerates every architectural change ever made.
- `STATE-DeviationAttempt: K` (K ∈ {1, 2, 3}) — mandatory alongside `STATE-DeviationRule`. For Rule 4 commits, K is always 1.
- `STATE-Subagent-Invocation: <invocation_id>` — mandatory on every commit produced inside a subagent session (Plan 02 owns this trailer; cited here for completeness of the trailer family).

**Auditor grep target:** `git log --grep="STATE-DeviationRule: 4"` enumerates every architectural change ever made. The CI naming-discipline grep target scans `.planning/milestones/v41/phases/405/` for any uppercase legacy trailer prefix matching `\bG[S]D-` and MUST return zero (project naming discipline — `STATE-*` only; the legacy lowercase project-name reference `gsd-2` is allowed as a design-heritage citation, but uppercase trailer prefixes from that lineage are a deferred-rename item handled in the `<deferred>` section of 405-CONTEXT.md).

**Single-source-of-truth module:** `state_build/commit/trailers.py` exports the trailer constants + the `infer_commit_type(message: str, files: list[str]) -> Literal['fix','feat','refactor','docs','test','chore','perf']` function (adapted from gsd-2's `git-service.ts` keyword table; the table content is unchanged, only the trailer-emission helper is novel to state). v14 implements; v15 wires the trailer emission at commit-time from the deviation-resolution code path.

### Trailer rendering order

The trailer block at the foot of a commit message follows a deterministic order to support `git interpret-trailers` parsing and pure-machine audit:

1. `STATE-Task: <step_id>` (always first; identifies the originating step).
2. `STATE-DeviationRule: N` (when a deviation is being resolved).
3. `STATE-DeviationAttempt: K` (always immediately after `STATE-DeviationRule`).
4. `STATE-Subagent-Invocation: <invocation_id>` (when authored inside a subagent session; Plan 02 territory).
5. Any additional `STATE-*` trailers added by future phases follow alphabetical order.

The renderer module `state_build/commit/trailers.py` exports a single helper `render_trailers(state_task: str, deviation: tuple[int, int] | None = None, subagent_invocation: str | None = None, extra: dict[str, str] | None = None) -> str` that produces the trailer block as a string, ready for concatenation to the commit message body. The helper enforces ordering and rejects unknown trailer keys (Pydantic-validated against a Literal whitelist).

### Mode-isolation note (commit machinery)

The trailer module lives under `state_build/commit/`; MUST NOT import from `state_teach/`. CI import-graph lint enforces. Teach-mode has its own (smaller) trailer family registered under `state_teach/commit/trailers.py` covering `STATE-Lesson:` and `STATE-Checkpoint:` (Plan 02 of a future teach-mode phase will pin the exact list). The two trailer modules share no code; the helper signatures are similar but not unified, by design.

---
