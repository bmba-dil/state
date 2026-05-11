---
phase: 404
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
autonomous: false
requirements:
  - APG-01
  - APG-02
  - APG-03
  - APG-04
  - APG-05
  - APG-06

must_haves:
  truths:
    - "ANALYSIS-PARALYSIS-GUARD.md exists at .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md and fully specifies the read-only-loop discipline guard with pure-machine bash classifier (APG-01)."
    - "Read-only tool set is enumerated: Read, Grep, Glob, Explore, Bash (when matching read-only-pattern via bash_classifier)."
    - "Pre-compiled READ_ONLY_PATTERNS list is rendered verbatim from 404-CONTEXT.md with all 7+ regex entries (5 gsd-2-heritage + state-specific extensions for ls/wc/file/stat/du/df/pwd/tree/env/which/type/command + jq/yq guarded against -i + git read-only subcommands)."
    - "Compound-command handling rule is documented: COMPOUND_SEP tokenization on `;` `&&` `||` `|` `&` (at word boundaries; heredoc bodies opaque); worst-sub-command-wins classification."
    - "Output-redirection rules are documented: `> path` write, `> /dev/null` read, `>> path` write, `>> /dev/null` read, `2> path` write, `2>&1` read, `| tee` write, process substitution write."
    - "Inline-interpreter payload scanning is documented: WRITE_SYSCALL_PATTERNS regex list rendered verbatim from 404-CONTEXT.md (7 patterns covering open/print-file/os.shutil.pathlib/subprocess/bare-redirect/node-fs/ruby-File/IO); payload match -> write classification."
    - "Bash exit code is documented as NOT a strike/paralysis trigger; only the read/write classification matters; cites gsd-2 loop-control.md §4 preparation-vs-execution narrowing (agent-loop.ts:324-329, issue #3618)."
    - "Per-step-type threshold table is rendered: default 5 consecutive read-only for type=auto/auto+tdd/checkpoint:*; default 15 for type research/discuss/plan (Slice-level overrides via Slice frontmatter `paralysis: {execute_threshold: int, research_threshold: int}`)."
    - "6-advisory escalation ladder is rendered as a markdown table: advisory x3 -> clear+reinject (single shot, cites compaction.snapshot_taken cross-link) -> advisory x3 more -> force-stop+human gate via opencode question tool."
    - "Pydantic ParalysisEvent payload is rendered verbatim with the exact field set from 404-CONTEXT.md (task_id, step_id, slice_id, count int, threshold int, tier Literal advisory|reinject|human_gate, advisory_number int 1..6, agent_response_summary str <=2KB, triggering_command str, triggered_at datetime, session_id str)."
    - "Counter reset rule is documented: an intervening Write/Edit (allowed by tool.execute.before stack — i.e., NOT rejected by Layers 1-4) resets the per-task consecutive read-only counter to 0."
    - "Single-module Python pattern is documented: state_build/harness/paralysis/bash_classifier.py exports READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP; mirrors gsd-2 branch-patterns.ts single-module pattern (file-tracking.md §branch-patterns)."
    - "APG-vs-PRF counter independence is documented citing gsd-2 loop-control.md §0 Correction 1 (forward-reference to PROOF-GATE.md Section 6 same statement)."
    - "Read-only false-positive avoidance is documented: research-heavy step types (discuss/plan/research) get higher 15-threshold default; gsd-2-lineage advisory-not-security framing cited (bash-interceptor.ts is advisory; not a security boundary)."
    - "Advisory message authoring guidance is rendered with recommended template ('N+ read-only operations on this task. State your hypothesis and either write code or report what is blocking you. Last commands: <list>. Current count: N of <threshold>.') and Claude's Discretion note that v14 may refine."
    - "Documented limitation: obfuscated shell payloads (base64-encoded scripts, eval-piped strings) MAY pass the classifier and run as 'read'; classifier is advisory not security."
  artifacts:
    - path: ".planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md"
      provides: "Canonical analysis-paralysis guard spec covering APG-01..APG-06 with read-only bash classifier regex corpora + 6-advisory ladder + ParalysisEvent payload."
      min_lines: 500
  key_links:
    - from: ".planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md"
      to: ".planning/milestones/v41/phases/404/specs/PROOF-GATE.md"
      via: "APG-vs-PRF counter independence statement (sibling-spec cross-reference)"
      pattern: "PROOF-GATE\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md"
      to: ".planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md"
      via: "Reinject tier (advisory_number=3) cites compaction.snapshot_taken via snapshot_event_id cross-link analogous to GateStrike pattern"
      pattern: "CONTEXT-PROTOCOL\\.md"
    - from: ".planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md"
      to: ".planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md"
      via: "Per-step-type threshold table references type Literal from StepFrontmatter (auto / auto+tdd / checkpoint:* / research / discuss / plan)"
      pattern: "STEP-PLAN-FORMAT\\.md"
---

<objective>
Author the canonical `ANALYSIS-PARALYSIS-GUARD.md` spec document — the design contract that v14 Build Kernel implements for the read-only-loop discipline guard. This file fully specifies: (1) the read-only tool set classification (APG-01) including the bash classifier module shape adapted from gsd-2's `bash-interceptor.ts`; (2) the default 5-consecutive threshold (APG-02) with exact advisory message text guidance; (3) the per-step-type threshold table (APG-03) and Slice-level override mechanism; (4) the 3-advisory -> clear+reinject escalation (APG-04); (5) the 3-more-advisories -> force-stop+human-gate (APG-05); (6) the `ParalysisEvent` Pydantic payload (APG-06).

Purpose: APG-01..APG-06 fully covered. Downstream consumers — v14 (Build Kernel: implements `state_build/harness/paralysis/bash_classifier.py` + per-task counter cache + 6-advisory state machine), v15 (Build Core Commands: registers the per-Step-type threshold lookup), Phase 405 (DEV-04 human-gate path consumes ParalysisEvent tier=human_gate events), Phase 406 (harness rollup cites this spec for tier-1 advisory inject + tier-3 force clear+reinject + tier-4 force-stop+human-gate of the intervention ladder) — all read from this file.

Output: One markdown spec doc at `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md`, ≥500 lines, fully populated with the literal READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP regex corpora, the compound-command/redirection/inline-interpreter classification rules, the per-step-type threshold table, the 6-advisory escalation ladder, the Pydantic ParalysisEvent payload, and advisory-not-security framing.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/milestones/v41/STATE.md
@.planning/milestones/v41/ROADMAP.md
@.planning/milestones/v41/REQUIREMENTS.md
@.planning/milestones/v41/HANDOFF.md
@.planning/milestones/v41/phases/404/404-CONTEXT.md
@.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md
@.planning/milestones/v41/phases/403/403-CONTEXT.md
@.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md
@.planning/milestones/v41/phases/402/specs/SLICE-CYCLE.md
@.planning/milestones/v40/phases/400/specs/EVENT-TAXONOMY.md
@.planning/milestones/v40/phases/400/specs/FRONTMATTER-SCHEMAS.md
</context>

<interfaces>
<!-- Upstream interfaces this spec consumes. Executor must NOT re-derive (STP-07 zero-codebase-exploration). -->

Excerpt A — Step `type` Literal from Phase 403 STEP-PLAN-FORMAT.md frontmatter schema (per-step-type threshold table dispatches on this):
```python
type: Literal["auto", "auto+tdd",
              "checkpoint:human-verify",
              "checkpoint:decision",
              "checkpoint:human-action"]
# Plus the Slice-stage type axis: research | discuss | plan (research-heavy stages get 15-threshold default)
```

Excerpt B — READ_ONLY_PATTERNS regex corpus, verbatim from 404-CONTEXT.md `<decisions>` Read-only Bash classification subsection:
```python
# Adapted from gsd-2/packages/pi-coding-agent/src/core/tools/bash-interceptor.ts:15-54
# (the read-side rules) plus state-specific extensions.
import re
READ_ONLY_PATTERNS: list[re.Pattern] = [
    # gsd-2 heritage (3 read patterns from bash-interceptor)
    re.compile(r"^\s*(cat(?!\s*<<)|head|tail|less|more)\s+"),
    re.compile(r"^\s*(grep|rg|ripgrep|ag|ack|fgrep|egrep)\s+"),
    re.compile(r"^\s*(find|fd|locate)\s+"),
    # state-specific extensions (filesystem inspection, no mutation)
    re.compile(r"^\s*(ls|ll|la|wc|file|stat|du|df|pwd|tree|env|which|type|command)\b"),
    re.compile(r"^\s*(jq|yq)\s+(?!.*-[iI]\b).*"),       # jq/yq, but NOT -i in-place mode
    # git read-only subcommands (explicit allowlist)
    re.compile(r"^\s*git\s+(log|show|diff|status|blame|branch\s+-l|config\s+--get|describe|rev-parse|ls-files)\b"),
]
COMPOUND_SEP = re.compile(r"(?:;|\&\&|\|\||\||\&)(?![\w])")
```

Excerpt C — WRITE_SYSCALL_PATTERNS regex corpus for inline-interpreter payload scanning, verbatim from 404-CONTEXT.md:
```python
WRITE_SYSCALL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bopen\s*\([^)]*,\s*['\"][wax]"),         # open(..., 'w'|'a'|'x' modes)
    re.compile(r"\bprint\s*\([^)]*file\s*="),              # print(..., file=...)
    re.compile(r"\b(os|shutil|pathlib)\.(remove|rename|unlink|copy|move|copyfile|write_text|write_bytes)"),
    re.compile(r"\bsubprocess\."),                          # any subprocess call (conservative)
    re.compile(r"[^&<>|]>(?![&=])"),                        # bare `>` redirect in the payload
    re.compile(r"\b(fs|node:fs)\.(write|writeFile|appendFile|rename|unlink|mkdir|rmdir)"),  # node
    re.compile(r"\b(File|IO)\.(write|open\s*\([^)]*,\s*['\"]w)"),                           # ruby
]
```

Excerpt D — `EventEnvelope` from src/state_core/schema.py lines 239-265 (ParalysisEvent rides this envelope):
```python
class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = ""
    seq: int = 0
    aggregate_type: str = "arc"
    aggregate_id: str = ""               # step_id for paralysis events
    type: str = ""                       # "state.step.paralysis_event"
    data: dict[str, Any] = {}
```
</interfaces>

<threat_model>
Phase 404 is design-only. ANALYSIS-PARALYSIS-GUARD.md introduces no production attack surface — it is a markdown specification of an ADVISORY (not security) classifier. Threats considered (per `<security_constraint>`):

- **[med] Bash-classifier evasion via creative shell constructs**: Compound commands, eval-piped strings, base64-encoded scripts, here-docs with sneaky payloads — a determined agent can hide a write under a read-classified surface. **Mitigation in spec:** spec MUST state up-front "the classifier is ADVISORY, not a security boundary" (gsd-2 framing: `tool-system.md:851` — no command allowlist/denylist). For compound commands the spec stipulates "worst-sub-command wins" (any non-read sub-command -> whole command classified write); for redirection the spec lists explicit forms. Documented limitation: obfuscated payloads (base64, eval-pipes) MAY pass; spec acknowledges; the harness's actual security boundary is the `files_modified` allowlist (SCOPE-PROHIBITION.md SRP-04), not the paralysis classifier.

- **[med] Regex catastrophic backtracking**: A pathological regex with nested quantifiers can DoS the classifier when scanning a long Bash command string. **Mitigation in spec:** spec MUST require all READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS to be pre-compiled (`re.compile`) and use NO nested quantifiers (no `(.+)+` or similar). The patterns rendered in 404-CONTEXT.md already satisfy this; the spec stipulates the pattern review as a v14 implementation gate. Bash payload length cap (recommended 64KB; v14 sets) further bounds worst case.

- **[high] Strike-counter integer overflow**: `count: int` is unbounded in the payload model; v14 increment site needs the bound. **Mitigation in spec:** spec stipulates `advisory_number: int  # 1..6` is bounded by the ladder (advisory_number=6 fires human_gate and the chain closes); `count` (consecutive read-only) is informally bounded by the threshold (counter resets at each Write/Edit or at the ladder transition). v14 enforces via type guard at the increment site.

- **[med] Mode-isolation drift**: The classifier lives at `state_build/harness/paralysis/bash_classifier.py` — MUST NOT import `state.teach.*`. **Mitigation in spec:** explicit "Build-mode only" header note; explicit module-path pin (`state_build/harness/paralysis/`); spec stipulates the regex module imports stdlib `re` only.

- **[low] Spec-doc misinterpretation by v14 implementers**: If the spec leaves the redirection rules ambiguous (e.g., "tee" without distinguishing `| tee path` write from `tee --version` read), v14 implementers will diverge. **Mitigation in spec:** rules are rendered as a markdown table with positive AND negative examples for each redirection form; v14's unit tests use this table as the fixture corpus.

- **[low] Single-module drift**: If v14 splits READ_ONLY_PATTERNS into multiple modules, future updates require multi-place edits and drift. **Mitigation in spec:** explicit "single Python module" requirement at `state_build/harness/paralysis/bash_classifier.py` (mirrors gsd-2's `branch-patterns.ts` single-module pattern, per `file-tracking.md §branch-patterns`).

No production code lands. No secrets. No network calls. No untrusted input.

<discovered_threats>
  <!-- empty at authoring time; runtime executor APPENDS only per PAP-05 carve-out -->
</discovered_threats>
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Author ANALYSIS-PARALYSIS-GUARD.md sections 1-5 (overview, read-only tool set, bash classifier corpora, compound + redirection + inline-interpreter rules, exit-code-not-strike rule)</name>
  <files>
    .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/404-CONTEXT.md (full file — every locked decision; <decisions> subsection "Read-only Bash classification (APG-01 expanded)" provides verbatim source for Sections 2-5)
    - .planning/milestones/v41/REQUIREMENTS.md lines 71-78 (APG-01..APG-06 verbatim)
    - .planning/milestones/v41/HANDOFF.md lines 118-128 (§4 Analysis Paralysis Guard — original framing)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (search "type: Literal" — confirms the step-type Literal set the per-step-type threshold table dispatches on)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/file-tracking.md (search "§branch-patterns" — single-module pattern this spec mirrors for state_build/harness/paralysis/bash_classifier.py)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/loop-control.md (search "§0 Correction 1" — four-counter independence; "§4" — preparation-vs-execution narrowing informs "exit code is not a strike trigger" rule)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/quality-enforcement.md (search "§1" — five-pipeline taxonomy informs advisory-not-security framing)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-PLAN.md lines 1-100 (Phase 403 spec-doc plan reference for verbose format/density target)
  </read_first>

  <action>
    Create `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md`. Sections 1–5 below; Task 2 owns sections 6–10. **Concrete content from 404-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 1 — File header

    ```
    # Analysis Paralysis Guard (Canonical, v41)

    > **Phase:** 404
    > **Status:** Canonical (v41)
    > **Requirements covered:** APG-01..APG-06
    > **Build-mode only.** `state.build.*` MUST NOT import `state.teach.*` (cardinal rule, PROJECT.md). The classifier module lives at `state_build/harness/paralysis/bash_classifier.py`.
    > **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
    > **Sibling specs:** PROOF-GATE.md (PRF strike counter — INDEPENDENT from APG paralysis counter; see Section 6 §APG-vs-PRF), SCOPE-PROHIBITION.md (files_modified allowlist + prohibited-language scan — neither participates in the paralysis counter).
    ```

    1-paragraph overview: the harness counts consecutive read-only tool uses per active task (APG-01). On threshold cross (APG-02 default 5; APG-03 per-step-type), the harness injects an advisory. The 6-advisory ladder (APG-04 reinject at advisory 3; APG-05 force-stop+human-gate at advisory 6) is independent from the PRF strike counter (see PROOF-GATE.md Section 6 §APG-vs-PRF). Each advisory and escalation emits a `ParalysisEvent` (APG-06).

    Up-front framing line: **"The classifier is ADVISORY, not a security boundary."** Mirrors gsd-2's `tool-system.md:851` — no command allowlist/denylist; the classifier is a heuristic. The hard security boundary is the `files_modified` allowlist (SCOPE-PROHIBITION.md SRP-04). A determined agent can evade the classifier via obfuscated payloads (documented limitation, Section 5).

    ### Section 2 — Read-Only Tool Set (APG-01)

    Heading: `## Read-Only Tool Set (APG-01)`.

    1-paragraph intro: the harness classifies every tool invocation as read-only or write. Read-only invocations increment the per-task consecutive-read-only counter; write invocations reset it to 0. The tool set is fixed by opencode's tool taxonomy; only Bash needs sub-classification (the bash_classifier module, Section 3).

    Sub-section `### Inherently read-only tools`:
    Render as a markdown list:
    - **Read** — always read-only.
    - **Grep** — always read-only.
    - **Glob** — always read-only.
    - **Explore** — always read-only (opencode's plan-tool / explore-tool taxonomy; if absent in a given opencode build, fall back to Read/Grep/Glob).
    - **WebFetch** — read-only (no filesystem mutation).
    - **WebSearch** — read-only.

    Sub-section `### Inherently write tools`:
    Render as a markdown list:
    - **Write** — always write.
    - **Edit** — always write.
    - **NotebookEdit** — always write.

    Sub-section `### Sub-classified tools`:
    Render as a markdown list:
    - **Bash** — sub-classified via `bash_classifier.py` (see Section 3). Read patterns -> read-only counter increment; write patterns -> counter reset to 0.
    - **MCP tools** — by default classified as write (conservative) UNLESS the specific MCP tool's name appears in an opt-in read-only list. v14 implementation finalizes the list; this spec stipulates the default is conservative.

    Sub-section `### Counter reset rule`:
    Render verbatim:
    - "An intervening Write/Edit/Bash-write tool call resets the per-task consecutive read-only counter to 0."
    - "**Counter reset requires the tool call to be ALLOWED by the tool.execute.before stack** (PROOF-GATE.md Section 5 Layer 1-4 enforcement). A REJECTED Write/Edit (e.g., scope_deviation, plan_edit_blocked, scope_check, gate_strike) does NOT reset the counter — it counts as a no-op for paralysis purposes (the agent didn't actually mutate anything)."

    ### Section 3 — Bash Classifier Module (`state_build/harness/paralysis/bash_classifier.py`)

    Heading: `## Bash Classifier Module`.

    1-paragraph intro: the bash classifier is a single Python module exporting three pre-compiled regex corpora plus a classification function. Mirrors gsd-2's `branch-patterns.ts` single-module pattern (`file-tracking.md §branch-patterns`). Updates flow from one place; every consumer imports from this module.

    Sub-section `### READ_ONLY_PATTERNS corpus`:

    Render verbatim (quote `<interfaces>` Excerpt B as a fenced Python block). Cite the source: "From 404-CONTEXT.md `<decisions>` Read-only Bash classification (APG-01 expanded). Adapted from gsd-2's `bash-interceptor.ts:15-54` read-side rules (3 patterns: cat-family, grep-family, find-family) plus state-specific extensions (filesystem inspection, jq/yq guarded against -i in-place mode, git read-only subcommands)."

    Add a sub-section `### COMPOUND_SEP tokenization`:
    Render verbatim:

    ```python
    COMPOUND_SEP = re.compile(r"(?:;|\&\&|\|\||\||\&)(?![\w])")
    ```

    "Tokenizes a Bash command on shell-boundary tokens (`;`, `&&`, `||`, `|`, `&` at word boundaries; heredoc bodies treated as opaque single tokens). Classify each sub-command independently. If **any** sub-command is non-read-allowlist (or matches a write-pattern below), the whole compound is `write`. Pure-machine; no real shell-AST parser required; conservative."

    Sub-section `### WRITE_SYSCALL_PATTERNS corpus (inline-interpreter payload scanning)`:

    Render verbatim (quote `<interfaces>` Excerpt C as a fenced Python block). 1-paragraph framing:
    "For inline-interpreter invocations — `python3 -c '...'`, `node -e '...'`, `ruby -e '...'`, `perl -e '...'`, `bash -c '...'`, `sh -c '...'` — the classifier extracts the payload (the quoted/escaped string following `-c` / `-e`) and greps it against WRITE_SYSCALL_PATTERNS. Payload match -> classify as `write`. Clean payload -> classify as `read`. Pure-machine; deterministic; matches PRF-04 spirit."

    Sub-section `### Classification function signature`:
    Render:

    ```python
    def classify(bash_command: str) -> Literal["read", "write"]:
        """
        Classify a Bash invocation as read-only or write for paralysis-counter purposes.

        - Tokenize on COMPOUND_SEP; classify each sub-command independently; worst-sub-command-wins.
        - For each sub-command: match against READ_ONLY_PATTERNS; if matches AND not an inline-interpreter
          with payload matching WRITE_SYSCALL_PATTERNS, classify as 'read'.
        - For inline-interpreter sub-commands (python3 -c / node -e / ruby -e / perl -e / bash -c / sh -c):
          extract payload; grep against WRITE_SYSCALL_PATTERNS; match -> 'write'; clean -> 'read'.
        - Output redirection (see Section 4 §Output redirection): any path-target redirect -> 'write'.
        - Process substitution `>(...)` or `<(...)` -> 'write' (conservative).
        - Unrecognized sub-command (matches NO READ_ONLY_PATTERN) -> 'write' (conservative).

        ADVISORY heuristic. Not a security boundary. Documented limitations: obfuscated payloads
        (base64, eval-pipes, heredoc tricks) MAY pass as 'read'.
        """
        ...
    ```

    "**Conservative-on-unknown:** the classifier defaults to `write` on any sub-command that doesn't match a READ_ONLY_PATTERN. This means the paralysis counter resets on unknown invocations — preferring false negatives (counter resets when it 'should' have incremented) over false positives (counter increments when it 'should' have reset). False positives delay detection of legit work; false negatives only delay detection of paralysis loops."

    ### Section 4 — Compound Commands, Redirection, Inline-Interpreter Rules

    Heading: `## Compound Commands, Redirection, Inline-Interpreter Rules`.

    Sub-section `### Compound-command handling`:
    Render verbatim:
    - "**Split tokens on COMPOUND_SEP**: `;`, `&&`, `||`, `|`, `&` at word boundaries; heredoc bodies (`<<EOF ... EOF`) treated as opaque single tokens (no recursive parsing into heredoc payload)."
    - "**Worst-sub-command wins**: classify each sub-command via READ_ONLY_PATTERNS + inline-interpreter scan + redirection check; if ANY sub-command classifies as `write`, the whole compound is `write`."
    - "**No real shell-AST parser**: regex tokenization is good enough; pure-machine; conservative."

    Positive example: `cat foo.txt | grep bar` -> two sub-commands; both READ_ONLY_PATTERNS match; both `read`; whole compound: `read`.

    Negative example: `grep bar foo.txt && rm foo.txt` -> two sub-commands; first `read`; second unrecognized (`rm` not in READ_ONLY_PATTERNS) -> `write`; whole compound: `write`.

    Sub-section `### Output redirection`:
    Render as a markdown table (verbatim from 404-CONTEXT.md):

    | Form | Classification | Notes |
    |------|----------------|-------|
    | `> path` (any non-`/dev/null` path) | write | path-target redirect |
    | `> /dev/null` | read | no real write |
    | `>> path` (any non-`/dev/null` path) | write | append-target redirect |
    | `>> /dev/null` | read | no real append |
    | `2> path` | write | stderr-to-path redirect |
    | `2> /dev/null` | read | stderr discard |
    | `2>> path` | write | stderr-append-to-path redirect |
    | `2>&1` | read | stream merge, no path |
    | `&> path` | write | both streams to path |
    | `<<< "data"` (here-string) | read | input redirect |
    | `<file` | read | input redirect |
    | `| tee path` (or `| tee -a path`) | write | tee mutates the path |
    | `| tee --version` | read | informational invocation (no path target) |
    | `>(cmd)` process substitution | write | conservative |
    | `<(cmd)` process substitution | write | conservative (cmd may be write) |

    "**Pure-machine token detection at parse time.** No path-resolution magic (no symlink chasing, no cwd-relative gymnastics) — a redirect is judged by its right-hand token only."

    Sub-section `### Inline-interpreter payload scanning`:
    Render verbatim:
    - "For `python3 -c '...'`, `node -e '...'`, `ruby -e '...'`, `perl -e '...'`, `bash -c '...'`, `sh -c '...'`: extract the payload (the quoted/escaped string following `-c` / `-e`)."
    - "Grep the payload against WRITE_SYSCALL_PATTERNS (Section 3 corpus)."
    - "Match -> classify as `write`. Clean -> classify as `read`."

    Positive example: `python3 -c 'import json; print(json.load(open("foo.json")))'` -> payload contains `open(...)` but mode arg is missing OR default `r`; check against the `open(..., 'w'|'a'|'x')` regex (`\bopen\s*\([^)]*,\s*['\"][wax]`) — NO match -> `read`. (Bare `open()` calls in read mode pass; only `open(..., 'w')` style trips the regex.)

    Negative example: `python3 -c 'open("foo.txt", "w").write("hi")'` -> payload matches `\bopen\s*\([^)]*,\s*['\"][wax]` -> `write`.

    Negative example: `bash -c 'echo hi > foo.txt'` -> payload matches `[^&<>|]>(?![&=])` (bare `>` redirect) -> `write`.

    Sub-section `### Documented limitations`:
    Render verbatim:
    - "Obfuscated payloads MAY pass as `read`. Examples:"
    - "  - `bash -c \"$(echo 'echo hi > foo.txt' | base64 -d)\"` — base64-encoded payload; the decoded write is hidden from the regex scan."
    - "  - `bash -c 'eval \"echo hi > foo.txt\"'` — eval-piped payload."
    - "  - `cat <<'EOF' | bash\\nrm foo.txt\\nEOF` — heredoc body is opaque; the rm inside is not scanned."
    - "The classifier is ADVISORY; the hard security boundary is `files_modified` allowlist (SCOPE-PROHIBITION.md SRP-04). v14 acknowledges these limitations; future work may add a second pass that grep-scans the OUTPUT of a dry-run (if/when opencode supports a `--dry-run` flag), but this spec does NOT mandate."

    ### Section 5 — Exit Code Is Not a Strike/Paralysis Trigger

    Heading: `## Exit Code Is Not a Strike/Paralysis Trigger`.

    Render verbatim from 404-CONTEXT.md `<decisions>` Read-only Bash classification subsection:
    - "**Bash exit code is NOT a strike trigger.** Mirrors gsd-2's preparation-vs-execution narrowing (`agent-loop.ts:324-329`, issue #3618): a `grep` that exits 1 ('no matches') is valid usage, not a paralysis trigger."
    - "The paralysis counter cares about **classification of the invocation** (read vs write), not about its exit status."
    - "A `grep -q nonexistent foo.txt` exiting 1 still classifies as `read` and increments the consecutive-read-only counter."
    - "A `python3 -c 'open(\"foo.txt\", \"w\")...'` exiting non-zero still classifies as `write` and resets the counter — even though the write attempt failed (the agent's INTENT was to write; that's what the counter measures)."

    Add a 1-paragraph cross-reference: "Cross-reference: PROOF-GATE.md Section 6 §Strike trigger uses the same preparation-vs-execution narrowing for PRF strikes — strikes accrue only at the completion-claim boundary, not on mid-task exit codes. Both counters (APG, PRF) inherit the same gsd-2 §0 Correction 1 principle: distinct counters at distinct scopes, never conflated."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (Plan 01 output — if available by execution time) — Mermaid sequence diagram patterns; Pydantic class rendering style.
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md` Section 2 — `type: Literal[...]` enumeration; quote for the per-step-type threshold table dispatch axis.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §6 (reinject payload) — the snapshot_event_id cross-link pattern this spec mirrors for ParalysisEvent.tier=='reinject'.
        - Grep pattern: `grep -nE "^### |^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md | head -40` — confirms heading depth convention.
        - Grep pattern: `grep -n "READ_ONLY_PATTERNS\|WRITE_SYSCALL_PATTERNS\|COMPOUND_SEP" /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/404-CONTEXT.md` — locates the verbatim source for the regex corpora.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<decisions>` Read-only Bash classification subsection — verbatim source for Sections 2-5 (all regex corpora + compound rules + redirection table + inline-interpreter payload scan + exit-code-not-strike rule + documented limitations).
        - file-tracking.md §branch-patterns — informs single-module pattern (state_build/harness/paralysis/bash_classifier.py).
        - loop-control.md §4 — preparation-vs-execution narrowing informs Section 5.
        - quality-enforcement.md §1 — five-pipeline taxonomy informs advisory-not-security framing.
        - tool-system.md:851 (referenced by 404-CONTEXT.md `<canonical_refs>`) — no command allowlist/denylist; informs Section 1 framing line.
      </docs_to_consult>
      <tests_to_write>
        - N/A — design-only deliverable (markdown spec). v14's bash_classifier.py unit tests will assert against this spec's redirection table + positive/negative examples as fixtures.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 250)}' \
        && grep -qE "^# Analysis Paralysis Guard" "$F" \
        && grep -qE "^## Read-Only Tool Set" "$F" \
        && grep -qE "^## Bash Classifier Module" "$F" \
        && grep -qE "^## Compound Commands, Redirection" "$F" \
        && grep -qE "^## Exit Code Is Not" "$F" \
        && grep -q "READ_ONLY_PATTERNS" "$F" \
        && grep -q "WRITE_SYSCALL_PATTERNS" "$F" \
        && grep -q "COMPOUND_SEP" "$F" \
        && grep -q "bash_classifier.py" "$F" \
        && grep -q "state_build/harness/paralysis" "$F" \
        && grep -q "branch-patterns" "$F" \
        && grep -q "ADVISORY" "$F" \
        && grep -q "worst-sub-command" "$F" \
        && grep -q "/dev/null" "$F" \
        && grep -q "tee" "$F" \
        && grep -q "2>&1" "$F" \
        && grep -q "process substitution" "$F" \
        && grep -q "python3 -c" "$F" \
        && grep -q "node -e" "$F" \
        && grep -q "ruby -e" "$F" \
        && grep -q "preparation-vs-execution" "$F" \
        && grep -q "agent-loop.ts:324-329" "$F" \
        && grep -q "obfuscated" "$F" \
        && grep -q "base64" "$F" \
        && grep -q "eval" "$F" \
        && grep -q "heredoc" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "SCOPE-PROHIBITION.md" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] File exists at `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md` with >= 250 lines after Task 1 (Task 2 extends to >= 500).
    - [check: must_haves.truths[0]] H1 `# Analysis Paralysis Guard (Canonical, v41)` present.
    - [check: must_haves.truths[1]] Read-only tool set enumerated (Read, Grep, Glob, Explore, Bash).
    - [check: must_haves.truths[2]] READ_ONLY_PATTERNS regex corpus rendered verbatim with the 6 entries (cat/head/tail/less/more, grep-family, find-family, ls/wc/file/stat/du/df/pwd/tree/env/which/type/command, jq/yq guarded against -i, git read-only subcommands).
    - [check: must_haves.truths[3]] COMPOUND_SEP regex rendered verbatim with "worst-sub-command wins" rule documented.
    - [check: must_haves.truths[4]] Redirection table rendered with at least 10 forms (`> path`, `> /dev/null`, `>> path`, `>> /dev/null`, `2> path`, `2>&1`, `&> path`, `| tee`, process substitution `>(...)` `<(...)`, here-string).
    - [check: must_haves.truths[5]] WRITE_SYSCALL_PATTERNS regex corpus rendered verbatim with all 7 entries (open mode w/a/x, print file=, os/shutil/pathlib mutation, subprocess, bare >, node fs, ruby File/IO).
    - [check: must_haves.truths[6]] Exit-code-not-strike rule rendered citing agent-loop.ts:324-329 and issue #3618.
    - [check: must_haves.truths[15]] Documented limitations rendered (obfuscated payloads MAY pass: base64, eval-pipes, heredoc).
    - [check: must_haves.truths[11]] Single-module pattern documented (state_build/harness/paralysis/bash_classifier.py) citing file-tracking.md §branch-patterns.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: must_haves.key_links[0]] PROOF-GATE.md cross-referenced in Section 1 and Section 5.
    - [check: verify_automated] File contains no `state.teach.` references (Build-mode isolation).
  </acceptance_criteria>

  <done>
    Sections 1–5 of ANALYSIS-PARALYSIS-GUARD.md authored: file header + read-only tool set (APG-01) + bash classifier module shape (READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP corpora) + compound/redirection/inline-interpreter rules + exit-code-not-strike rule with preparation-vs-execution narrowing citation. Task 2 will add the per-step-type threshold table (APG-02, APG-03), the 6-advisory escalation ladder (APG-04, APG-05), the Pydantic ParalysisEvent payload (APG-06), and the cross-references closing section.
  </done>
</task>

<task type="auto">
  <name>Task 2: Append ANALYSIS-PARALYSIS-GUARD.md sections 6-10 (threshold table, advisory ladder, ParalysisEvent payload, advisory message template, cross-references)</name>
  <files>
    .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md (full file — Task 1 output; this task appends to it)
    - .planning/milestones/v41/phases/404/404-CONTEXT.md lines 162-180 (ParalysisEvent payload subsection — verbatim source for Section 8)
    - .planning/milestones/v41/REQUIREMENTS.md lines 74-78 (APG-02..APG-06 verbatim)
    - .planning/milestones/v41/phases/404/specs/PROOF-GATE.md (full file if available — Plan 01 output; quote the APG-vs-PRF counter independence statement and the compaction.snapshot_taken cross-link pattern)
    - .planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md (search "compaction.snapshot_taken" — ParalysisEvent.tier=='reinject' cross-link source, analogous to GateStrike pattern)
    - .planning/milestones/v41/phases/403/specs/STEP-PLAN-FORMAT.md (full file — confirms Slice-frontmatter override mechanism `paralysis: {execute_threshold, research_threshold}` mirrors Phase 402's `compaction:` shape)
    - .planning/milestones/v41/workflow-docs-from-gsd-2/loop-control.md (search "§0 Correction 1" + "MAX_CONSECUTIVE_VALIDATION_FAILURES=3" — informs ladder thresholds)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-PLAN.md lines 380-460 (Phase 403 spec-doc plan reference for Task 2 append pattern)
  </read_first>

  <action>
    Append sections 6–10 to the existing `ANALYSIS-PARALYSIS-GUARD.md`. Use Edit (insert at end of file). **Concrete content from 404-CONTEXT.md verbatim — do NOT re-derive.**

    ### Section 6 — Per-Step-Type Threshold Table (APG-02, APG-03)

    Heading: `## Per-Step-Type Threshold Table (APG-02, APG-03)`.

    Sub-section `### Default thresholds`:
    Render verbatim as a markdown table:

    | Step type (frontmatter `type`) | Consecutive-read-only threshold | Rationale |
    |--------------------------------|---------------------------------|-----------|
    | `auto` | 5 | execute-slice; agent should write quickly |
    | `auto+tdd` | 5 | execute-slice (TDD); agent should write tests then code |
    | `checkpoint:human-verify` | 5 | execute-slice; pre-checkpoint reads should be bounded |
    | `checkpoint:decision` | 5 | execute-slice; pre-checkpoint reads should be bounded |
    | `checkpoint:human-action` | 5 | execute-slice; pre-checkpoint reads should be bounded |
    | (Slice-stage: research) | 15 | discuss-slice / plan-slice/research; deep exploration expected |
    | (Slice-stage: discuss) | 15 | discuss-slice; deep exploration expected |
    | (Slice-stage: plan) | 15 | plan-slice (any sub-stage); deep exploration expected |

    "**Per-step-type axis (5 default for execute):** matches the Step `type` Literal from STEP-PLAN-FORMAT.md frontmatter schema (STP-02). All five execute-slice task types share the 5-threshold default; the discriminator is the parent Slice stage, not the Step type."

    "**Per-Slice-stage axis (15 default for research-heavy):** when the active Slice is in `discuss-slice` / `plan-slice` / its `research` sub-stage, the agent is explicitly invited to read deeply. The threshold raises to 15 to reflect this. The Slice-stage axis derives from the active stage in `SLICE-CYCLE.md` (Phase 402)."

    Sub-section `### Slice-level override`:
    Render verbatim:
    - "Slice frontmatter MAY override the defaults via:"

    ```yaml
    paralysis:
      execute_threshold: int    # overrides the 5-default for all execute-slice Steps in this Slice
      research_threshold: int   # overrides the 15-default for the discuss/plan/research stages
    ```

    "Mirrors Phase 402's `compaction:` frontmatter shape. **Step-level override is REJECTED** for v1 (mirrors Phase 403's rejection of Step-level autonomy: Slice is the autonomy unit per D-11)."

    Sub-section `### Counter scope`:
    Render verbatim:
    - "**Counter scope: per active task.** Each Step's tasks share the Step's threshold; each task has its own consecutive-read-only counter; counters reset to 0 on task boundary and on any allowed Write/Edit/Bash-write tool call."
    - "Cross-task carry-over is forbidden: the counter for task N closes (resets) when task N completes (pass/flag/omitted) and task N+1 starts fresh."
    - "Cross-Step carry-over is forbidden: Step boundary closes all task counters."
    - "Cross-Slice carry-over is irrelevant (fresh session per Slice — CTX-02)."

    ### Section 7 — Six-Advisory Escalation Ladder (APG-04, APG-05)

    Heading: `## Six-Advisory Escalation Ladder (APG-04, APG-05)`.

    1-paragraph intro: when the per-task counter exceeds the threshold, the harness injects an advisory and emits a `ParalysisEvent`. The 6-advisory ladder (advisories 1-3 advisory tier, advisory 3 ALSO fires reinject single-shot, advisories 4-6 post-reinject advisory tier, advisory 6 fires human gate) is INDEPENDENT from the PRF strike counter (cross-reference: PROOF-GATE.md Section 6 §APG-vs-PRF).

    Sub-section `### Escalation table`:
    Render as a markdown table:

    | Advisory # | Tier | Trigger | Harness action | Event emitted |
    |-----------|------|---------|----------------|---------------|
    | 1 | advisory | Counter exceeds threshold for the 1st time on this task | Inject system advisory naming the count + threshold + recent commands + remediation prompt | `state.step.paralysis_event` (tier=advisory, advisory_number=1) |
    | 2 | advisory | Counter exceeds threshold again on this task after another window of read-only operations | Same advisory; updated count + remediation prompt | `state.step.paralysis_event` (tier=advisory, advisory_number=2) |
    | 3 | advisory + reinject | Counter exceeds threshold for the 3rd time on this task | Inject advisory; fire compaction snapshot (records `snapshot_event_id`); clear context; reinject PLAN with focused prompt naming the specific paralysis pattern + the failing reasoning surface | `state.step.paralysis_event` (tier=reinject, advisory_number=3, snapshot_event_id=<id>) |
    | 4 | advisory (post-reinject) | Counter exceeds threshold on the reinjected agent for the 1st time | Inject advisory; counter visible as 4 of 6 | `state.step.paralysis_event` (tier=advisory, advisory_number=4) |
    | 5 | advisory | Counter exceeds threshold for the 5th time on this task | Inject advisory; warning that next paralysis fires human gate | `state.step.paralysis_event` (tier=advisory, advisory_number=5) |
    | 6 | human_gate (force-stop) | Counter exceeds threshold for the 6th time | Force-stop the session; surface a human gate via opencode `question` tool with the paralysis pattern + the per-advisory recent-commands log + the 6-advisory chain audit | `state.step.paralysis_event` (tier=human_gate, advisory_number=6) |

    "**On advisory 6 human resolution:** human picks `proceed` (agent continues with a fresh task context) or `abort` (Slice transitions to `pending_replan` — same path as SRP-05 `split_recommendation`). v14 implements both paths; spec stipulates the two named resolutions."

    Sub-section `### Counter reset on task completion`:
    Render verbatim:
    - "When a task closes (pass/flag/omitted), the consecutive-read-only counter for that task closes too."
    - "The advisory chain (1-6) closes alongside; subsequent failures on the SAME task_id are impossible (task is done) and subsequent failures on the NEXT task start fresh from advisory 1."
    - "**Reset rule diverges from PRF strike counter:** PRF strikes accrue across the reinject tier (per PROOF-GATE.md Section 6 §Reset rule); APG advisories ALSO continue counting across the reinject tier (the same 'continue counting' semantic — D-8 reading: 'human gate at advisory/strike 6 total')."

    Sub-section `### APG-vs-PRF counter independence (cross-reference)`:
    "Cross-reference: `PROOF-GATE.md` Section 6 §APG-vs-PRF counter independence — this spec mirrors the same statement. Both counters can independently reach force-stop. The `harness_intervention` event (Phase 406 HRN-05) is the umbrella; both `paralysis_event` and `gate_strike` cite it as `trigger_reason`."

    ### Section 8 — ParalysisEvent Pydantic Payload (APG-06)

    Heading: `## ParalysisEvent Pydantic Payload (APG-06)`.

    1-paragraph intro: every advisory and escalation emits a `state.step.paralysis_event`. The Pydantic payload carries the audit-trail evidence: count, threshold, tier, advisory number, agent response excerpt, the triggering bash command, session_id, and (on reinject tier) the compaction snapshot cross-link.

    Sub-section `### Pydantic class`:
    Render verbatim from 404-CONTEXT.md `<decisions>` Read-only Bash classification subsection (extended with the snapshot_event_id reinject cross-link to match the GateStrike pattern):

    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict
    from typing import Literal

    class ParalysisEvent(BaseModel):
        model_config = ConfigDict(extra="forbid")
        task_id: str
        step_id: str
        slice_id: str
        count: int                                      # current consecutive read-only count when advisory fired
        threshold: int                                  # the per-step-type threshold in effect (5 or 15 default; or Slice-frontmatter override)
        tier: Literal["advisory", "reinject", "human_gate"]
        advisory_number: int                            # 1..6 (the 3 + 3 ladder)
        agent_response_summary: str                     # <= 2KB excerpt (gsd-2 truncation convention)
        triggering_command: str                         # the bash command (or tool name) that incremented the counter past threshold
        triggered_at: datetime                          # UTC, ISO-8601
        session_id: str
        snapshot_event_id: str | None                   # set when tier == "reinject" (cross-link to compaction.snapshot_taken; analogous to GateStrike pattern from PROOF-GATE.md)
        recent_tool_calls: list[str]                    # last N tool call summaries before the trigger (N=5 by default; max 10); helps human gate audit
    ```

    Sub-section `### Bounded truncation`:
    "Same discipline as `GateStrike` (see PROOF-GATE.md Section 7 §Bounded truncation): **2KB per excerpt, 10KB total per ParalysisEvent**. Truncation marker: `[... truncated <N> bytes ...]`. The harness-owned truncation utility is shared between APG and PRF events."

    Sub-section `### State transitions`:
    Render verbatim:
    - "ParalysisEvent is APPEND-ONLY (no UPDATE/DELETE; corrections are NEW events)."
    - "The ParalysisEvent itself does not transition the Slice/Step FSM; the harness's in-memory paralysis-counter state transitions on EMISSION (advisory_number increments)."
    - "Replay rebuilds counter state from the event store: scan `state.step.paralysis_event` events filtered by `aggregate_id == step_id`, sort by `triggered_at`, replay tier transitions in order."

    ### Section 9 — Advisory Message Authoring Guidance

    Heading: `## Advisory Message Authoring Guidance`.

    1-paragraph intro: per 404-CONTEXT.md Claude's Discretion, exact advisory wording is deferred to v14 + EXEMPLAR-driven sizing. This section pins the recommended template; v14 may refine.

    Sub-section `### Recommended advisory template (tier=advisory)`:

    ```
    {threshold}+ consecutive read-only operations on task {task_id} (count={count}, threshold={threshold}, advisory {advisory_number} of 6).

    State your hypothesis: what are you trying to verify, and what's the next concrete action — write code OR report what is blocking you?

    Recent commands:
    1. {recent_tool_calls[0]}
    2. {recent_tool_calls[1]}
    3. {recent_tool_calls[2]}
    4. {recent_tool_calls[3]}
    5. {recent_tool_calls[4]}

    If you cannot make progress, call `request_step_split` (the canonical scope-deviation tool — see SCOPE-PROHIBITION.md) OR emit a `complete_task` MCP call with a partial-completion summary and explicit blocker description.
    ```

    Sub-section `### Recommended advisory template (tier=reinject, advisory 3)`:
    "Adds: 'A compaction snapshot has been recorded (snapshot_event_id={id}). The active session will receive a fresh-context reinjection of the PLAN focused on the paralysis pattern. After reinjection, the counter continues at advisory 4 — your next paralysis triggers advisory 5 with a warning that the 6th triggers a human gate.'"

    Sub-section `### Recommended human-gate prompt (tier=human_gate, advisory 6)`:
    "Surfaces via opencode `question` tool with: the failing task_id, the 6-advisory chain (event ids), the recent commands (all 6 × 5 = 30 most recent), and two named resolutions: `proceed` (clear paralysis chain, agent continues on the same task with a fresh sub-counter) or `abort` (Slice transitions to `pending_replan`, mirrors SRP-05 split path)."

    Sub-section `### Claude's Discretion`:
    Render verbatim:
    - "Exact wording deferred to v14 per 404-CONTEXT.md."
    - "Recommended placeholders (above) include count, threshold, advisory_number, recent_tool_calls — all available in the ParalysisEvent payload."
    - "v14 may add: time-since-last-write, byte counts of files read in the window, names of files read repeatedly (recommended: top-3 most-read files in the read-only window)."

    ### Section 10 — Cross-references

    Heading: `## Cross-references`.

    Bullet list:
    - **Sibling spec — proof gate:** `PROOF-GATE.md` Section 6 §APG-vs-PRF defines the same counter-independence statement; this spec mirrors it. PRF strike counter increments at the completion-claim boundary; APG paralysis counter increments on consecutive-read-only tool calls. Independent chains.
    - **Sibling spec — scope:** `SCOPE-PROHIBITION.md` defines the `request_step_split` MCP tool (SRP-05) — the recommended escape hatch for an agent that recognizes paralysis. Advisories instruct the agent to call `request_step_split` rather than continue spinning.
    - **Phase 403 carry-forward — Step type:** `STEP-PLAN-FORMAT.md` §Frontmatter Schema (STP-02) provides the `type` Literal that the per-step-type threshold table dispatches on.
    - **Phase 402 carry-forward — compaction:** `CONTEXT-PROTOCOL.md` §Compaction (CTX-05/06) is the source of the `compaction.snapshot_taken` event that ParalysisEvent.snapshot_event_id cross-links when tier='reinject'.
    - **Phase 402 carry-forward — Slice cycle:** `SLICE-CYCLE.md` defines the discuss/plan/execute/verify stages that the per-Slice-stage threshold axis dispatches on (research/discuss/plan default 15; execute default 5).
    - **v40 baseline — events:** `EVENT-TAXONOMY.md` naming convention `state.{tier}.{action}`; this spec adds `state.step.paralysis_event`. Plan 04 of this phase appends the `## v41 Amendment` block to v40 EVENT-TAXONOMY.md registering this event.
    - **gsd-2 lineage:** `bash-interceptor.ts:15-54` (read-side rules 3 patterns); `tool-system.md:851` (no allowlist/denylist; advisory-not-security framing); `loop-control.md §0 Correction 1` (four-counter independence); `loop-control.md §4` (preparation-vs-execution narrowing — exit code is NOT a trigger); `file-tracking.md §branch-patterns` (single-module pattern).
    - **Phase 406 forward:** `harness_intervention` (HRN-05) umbrella event aggregates `paralysis_event` + `gate_strike` + `scope_check` + `scope_deviation_request` + `split_recommendation`; the 4-tier intervention ladder (HRN-04) cites this spec for tier-1 (advisory inject) + tier-3 (force clear+reinject at advisory 3) + tier-4 (force-stop+human-gate at advisory 6).

    Add closing 1-paragraph note: "v14 Build Kernel implements `state_build/harness/paralysis/bash_classifier.py` (single module with READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP + classify()), the per-task consecutive-read-only counter cache, the 6-advisory state machine, the recent-tool-calls ring buffer, and the bounded-truncation utility (shared with PROOF-GATE.md). v15 Build Core Commands implements the per-Slice-stage threshold lookup (discuss/plan/research = 15; execute = 5) and the Slice-frontmatter override resolution. Phase 405 (Deviation Rules) consumes `ParalysisEvent.tier=human_gate` events as input to the DEV-04 human-gate path. Phase 406 (Harness Architecture Rollup) cites this spec for tier-1/3/4 of the intervention ladder; the `harness_intervention` umbrella event (HRN-05) aggregates ParalysisEvent."

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/404/specs/PROOF-GATE.md` (Plan 01 output) — APG-vs-PRF counter independence statement; quote the exact wording in Section 7's cross-reference subsection.
        - Known: `.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` §6 — compaction.snapshot_taken cross-link pattern; mirror for ParalysisEvent.snapshot_event_id when tier='reinject'.
        - Known: `.planning/milestones/v41/phases/403/specs/STEP-EVENTS.md` Section 3 (state.step.plan_authored Pydantic class rendering) — event payload rendering pattern; mirror for ParalysisEvent.
        - Grep pattern: `grep -nE "^## " /Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md` — confirms Task 1's Section headings before appending.
        - Grep pattern: `grep -n "compaction.snapshot_taken" /Users/tmac/Projects/state/.planning/milestones/v41/phases/402/specs/CONTEXT-PROTOCOL.md` — locates exact event-type string.
      </code_to_reuse>
      <docs_to_consult>
        - 404-CONTEXT.md `<decisions>` Read-only Bash classification subsection — ParalysisEvent verbatim payload (extended here with snapshot_event_id reinject cross-link + recent_tool_calls list).
        - REQUIREMENTS.md lines 74-78 — APG-02 (5 default threshold) + APG-03 (per-step-type; 15 for research-heavy) + APG-04 (3-advisory clear+reinject) + APG-05 (3-more force-stop+human-gate) + APG-06 (paralysis_event schema task_id/count/threshold/agent_response) verbatim.
        - loop-control.md §0 Correction 1 — informs Section 7 cross-reference to PROOF-GATE.md.
        - Phase 402 SLICE-CYCLE.md — confirms discuss/plan stages exist; informs the per-Slice-stage threshold axis.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown spec.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 500)}' \
        && grep -qE "^## Per-Step-Type Threshold Table" "$F" \
        && grep -qE "^## Six-Advisory Escalation Ladder" "$F" \
        && grep -qE "^## ParalysisEvent Pydantic Payload" "$F" \
        && grep -qE "^## Advisory Message Authoring Guidance" "$F" \
        && grep -qE "^## Cross-references" "$F" \
        && grep -q "class ParalysisEvent" "$F" \
        && grep -q "advisory_number" "$F" \
        && grep -q 'extra="forbid"' "$F" \
        && grep -q "snapshot_event_id" "$F" \
        && grep -q "recent_tool_calls" "$F" \
        && grep -q "execute_threshold" "$F" \
        && grep -q "research_threshold" "$F" \
        && grep -q "paralysis:" "$F" \
        && grep -q "compaction.snapshot_taken" "$F" \
        && grep -q "request_step_split" "$F" \
        && grep -q "human_gate" "$F" \
        && grep -q "advisory" "$F" \
        && grep -q "reinject" "$F" \
        && grep -q "APG-vs-PRF" "$F" \
        && grep -q "PROOF-GATE.md" "$F" \
        && grep -q "SCOPE-PROHIBITION.md" "$F" \
        && grep -q "CONTEXT-PROTOCOL.md" "$F" \
        && grep -q "SLICE-CYCLE.md" "$F" \
        && grep -q "STEP-PLAN-FORMAT.md" "$F" \
        && grep -q "harness_intervention" "$F" \
        && grep -q "EVENT-TAXONOMY.md" "$F" \
        && ! grep -q "state.teach" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.artifacts[0]] ANALYSIS-PARALYSIS-GUARD.md >= 500 lines after this task.
    - [check: must_haves.truths[7]] Per-step-type threshold table rendered with execute=5 / research-heavy=15 defaults + Slice-frontmatter override mechanism `paralysis: {execute_threshold, research_threshold}`.
    - [check: must_haves.truths[8]] 6-advisory escalation ladder table rendered (advisory 1, 2, 3+reinject, 4, 5, 6+human-gate) with `state.step.paralysis_event` event emission per row.
    - [check: must_haves.truths[9]] Pydantic ParalysisEvent class rendered verbatim with all 11 fields (task_id, step_id, slice_id, count, threshold, tier Literal, advisory_number int 1..6, agent_response_summary, triggering_command, triggered_at, session_id, snapshot_event_id optional, recent_tool_calls list).
    - [check: must_haves.truths[10]] Counter reset rule documented (intervening allowed Write/Edit/Bash-write resets counter; rejected writes do NOT reset).
    - [check: must_haves.truths[12]] APG-vs-PRF counter independence cross-reference to PROOF-GATE.md Section 6 documented in Section 7.
    - [check: must_haves.truths[13]] Read-only false-positive avoidance documented (research-heavy step types get 15-threshold) + advisory-not-security framing cited.
    - [check: must_haves.truths[14]] Advisory message authoring guidance rendered with recommended template in Section 9.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: must_haves.key_links[0]] PROOF-GATE.md cited in Section 7 and Section 10.
    - [check: must_haves.key_links[1]] CONTEXT-PROTOCOL.md cited in Section 8 (compaction.snapshot_taken cross-link).
    - [check: must_haves.key_links[2]] STEP-PLAN-FORMAT.md cited for the type Literal source in Section 6.
    - [check: verify_automated] File contains no `state.teach.` references (Build-mode isolation).
  </acceptance_criteria>

  <done>
    ANALYSIS-PARALYSIS-GUARD.md complete — all 10 sections present. APG-01..APG-06 fully covered with literal READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP regex corpora (Section 3), the compound/redirection/inline-interpreter rules (Section 4), exit-code-not-strike rule (Section 5), per-step-type threshold table with Slice-frontmatter override (Section 6), 6-advisory escalation ladder (Section 7), Pydantic ParalysisEvent payload (Section 8), advisory message authoring guidance (Section 9), and cross-references to sibling specs + Phase 402/403 carry-forwards (Section 10).
  </done>
</task>

<task type="auto">
  <name>Task 3: Write 02-analysis-paralysis-guard-spec-SUMMARY.md</name>
  <files>
    .planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md
  </files>

  <read_first>
    - .planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md (full file — Tasks 1+2 output)
    - .planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md (full file — sibling SUMMARY shape reference)
    - .planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md (if available — Plan 01 sibling for consistency)
    - CLAUDE.md (project) — per-plan SUMMARY.md mandatory gate
  </read_first>

  <action>
    Author the per-plan SUMMARY.md. Mirror `403-02-SUMMARY.md` structure (frontmatter + body sections).

    1. Frontmatter (mirror sibling shape):
       - `phase: 404-boolean-proof-gate-discipline-guards`
       - `plan: 02`
       - `subsystem: design-spec`
       - `tags: [analysis-paralysis, bash-classifier, advisory-ladder, harness, apg]`
       - `requires`: 404-01 (PROOF-GATE.md for APG-vs-PRF cross-reference), 403 (STEP-PLAN-FORMAT.md for type Literal), 402 (CONTEXT-PROTOCOL.md for compaction.snapshot_taken; SLICE-CYCLE.md for per-Slice-stage axis), 400 (EVENT-TAXONOMY.md naming + FRONTMATTER-SCHEMAS.md Pydantic convention)
       - `provides`: ANALYSIS-PARALYSIS-GUARD.md — canonical analysis paralysis guard spec covering APG-01..APG-06 (>=500 lines); READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP regex corpora; bash_classifier.py module shape pinned at state_build/harness/paralysis/; per-step-type threshold table (5 execute / 15 research); 6-advisory escalation ladder; Pydantic ParalysisEvent payload with snapshot_event_id reinject cross-link and recent_tool_calls list extension; advisory message authoring guidance
       - `affects`: 404-04 (event taxonomy amendment registers state.step.paralysis_event), v14 Build Kernel (implements bash_classifier.py + per-task counter cache + 6-advisory state machine), v15 Build Core Commands (per-Slice-stage threshold lookup + Slice-frontmatter override), Phase 405 (DEV-04 human-gate consumes ParalysisEvent tier=human_gate), Phase 406 (harness rollup cites this spec for tier-1/3/4 of intervention ladder)
       - `tech-stack.patterns`: ["Single-module Python regex pattern (state_build/harness/paralysis/bash_classifier.py) mirroring gsd-2 branch-patterns.ts", "Compound-command tokenization on COMPOUND_SEP with worst-sub-command-wins classification", "Inline-interpreter payload scanning against WRITE_SYSCALL_PATTERNS (python3/node/ruby/perl/bash/sh -c/-e)", "Per-Slice-stage threshold axis (execute=5 / research-heavy=15) with Slice-frontmatter override paralysis: {execute_threshold, research_threshold}", "ParalysisEvent reinject tier cites compaction.snapshot_taken via snapshot_event_id (analog to GateStrike pattern)", "Advisory-not-security framing — classifier evadable by obfuscated payloads; documented limitation"]
       - `key-files.created`: `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md` (>=500 lines)
       - `key-decisions`: render the 7-8 locked-in design choices (read-only set, classifier module location, compound rule, redirection table, payload-scan WRITE_SYSCALL_PATTERNS, exit-code-not-trigger, per-step-type thresholds, 6-advisory ladder, ParalysisEvent extensions snapshot_event_id + recent_tool_calls, Slice-only override + Step-level rejection, advisory-not-security framing)
       - `requirements-completed`: APG-01..APG-06
       - `duration`: ~25min (estimated)
       - `completed`: {date}

    2. Body sections (mirror 403-02-SUMMARY.md format):
       - `# Plan 404-02 Summary: ANALYSIS-PARALYSIS-GUARD.md`
       - Bold tagline (1-2 sentences)
       - `## What Was Built` — 1 paragraph: ANALYSIS-PARALYSIS-GUARD.md at canonical path; 10 sections; APG-01..APG-06 covered; Pydantic ParalysisEvent + READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP corpora; per-step-type threshold table; 6-advisory ladder; advisory-not-security framing.
       - `## Key Decisions` — bullets
       - `## Files Touched` — ANALYSIS-PARALYSIS-GUARD.md only
       - `## Open Items / Deferred` — bullets:
         - "Exact advisory wording deferred to v14 per 404-CONTEXT.md Claude's Discretion."
         - "Inline-interpreter `python3 -c` write-syscall pattern completeness — v1 covers common cases; v14 may extend."
         - "Bash command length cap (recommended 64KB) — pinned by v14."
         - "Per-Step-level paralysis override REJECTED for v1 (mirrors Phase 403 D-11 rejection); revisit if real Step-execution data shows the need."
         - "Plan 04 of this phase appends `## v41 Amendment` block to v40 EVENT-TAXONOMY.md registering state.step.paralysis_event."
       - `## Downstream Hooks` — bullets:
         - "v14 Build Kernel implements bash_classifier.py at state_build/harness/paralysis/."
         - "v15 Build Core Commands implements per-Slice-stage threshold lookup + Slice-frontmatter override resolution."
         - "Phase 405 DEV-04 consumes ParalysisEvent tier=human_gate."
         - "Phase 406 harness rollup cites this spec for tier-1/3/4 of the 4-tier intervention ladder; harness_intervention event aggregates ParalysisEvent."
       - `## Task Commits` — placeholder
       - `## Deviations from Plan` — placeholder
       - `## Self-Check: PASSED` — checklist of every must_haves.truth verified

    Length: 100-180 lines.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/milestones/v41/phases/403/02-step-plan-format-spec-SUMMARY.md` — sibling SUMMARY exemplar; mirror frontmatter + body sections.
        - Known: `.planning/milestones/v41/phases/404/01-proof-gate-spec-SUMMARY.md` (Plan 01 output, if available) — sibling SUMMARY exemplar for consistency within Phase 404.
      </code_to_reuse>
      <docs_to_consult>
        - CLAUDE.md per-plan-SUMMARY-mandatory subsection.
      </docs_to_consult>
      <tests_to_write>
        - N/A — markdown SUMMARY.
      </tests_to_write>
    </quality_scan>
  </action>

  <verify>
    <automated>
      F=/Users/tmac/Projects/state/.planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md
      test -f "$F" \
        && wc -l "$F" | awk '{exit ($1 < 80)}' \
        && grep -q "Plan 404-02" "$F" \
        && grep -qE "^## What Was Built" "$F" \
        && grep -qE "^## Key Decisions" "$F" \
        && grep -qE "^## Files Touched" "$F" \
        && grep -qE "^## Downstream Hooks" "$F" \
        && grep -q "ANALYSIS-PARALYSIS-GUARD.md" "$F" \
        && grep -q "APG-01" "$F" \
        && grep -q "APG-06" "$F"
    </automated>
  </verify>

  <acceptance_criteria>
    - [check: must_haves.truths[0]] SUMMARY exists with >= 80 lines.
    - [check: verify_automated] All grep assertions in `<verify><automated>` pass.
    - [check: verify_automated] SUMMARY references Plan 02, the ANALYSIS-PARALYSIS-GUARD.md spec, all 6 APG requirements covered, and forward-points to Plans 01/03/04.
    - [check: verify_automated] All four core sections present (What Was Built, Key Decisions, Files Touched, Downstream Hooks).
  </acceptance_criteria>

  <done>
    Per-plan SUMMARY.md gate closed for Plan 404-02.
  </done>
</task>

</tasks>

<verification>
- File `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md` exists with >= 500 lines.
- File `.planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md` exists with >= 80 lines.
- All 10 H2 sections present in the spec (Read-Only Tool Set, Bash Classifier Module, Compound Commands / Redirection, Exit Code Is Not a Strike, Per-Step-Type Threshold Table, Six-Advisory Escalation Ladder, ParalysisEvent Pydantic Payload, Advisory Message Authoring Guidance, Cross-references — plus the H1 file header).
- READ_ONLY_PATTERNS, WRITE_SYSCALL_PATTERNS, COMPOUND_SEP all rendered as fenced Python blocks.
- Pydantic ParalysisEvent class rendered with `extra="forbid"` + all required fields.
- 6-advisory escalation ladder table rendered (advisory 1..6 with tier transitions).
- Per-step-type threshold table rendered (execute=5 / research-heavy=15 + Slice override `paralysis: {execute_threshold, research_threshold}`).
- Cross-references to PROOF-GATE.md, SCOPE-PROHIBITION.md, STEP-PLAN-FORMAT.md, CONTEXT-PROTOCOL.md, SLICE-CYCLE.md, EVENT-TAXONOMY.md, harness_intervention forward-reference all present.
- No `state.teach.` references.
- Single-module pattern (state_build/harness/paralysis/bash_classifier.py) documented.
- Advisory-not-security framing rendered.
- Compound-command worst-sub-command-wins rule rendered.
- Output-redirection table rendered with at least 10 forms.
- Inline-interpreter payload scanning rule rendered.
- Exit-code-not-strike rule rendered citing agent-loop.ts:324-329 and issue #3618.
</verification>

<success_criteria>
- APG-01 (read-only tool set + bash classifier): Read/Grep/Glob/Explore/Bash-read-only enumerated; bash_classifier.py module shape pinned with READ_ONLY_PATTERNS + COMPOUND_SEP + WRITE_SYSCALL_PATTERNS + classify() signature.
- APG-02 (default 5-consecutive threshold + advisory message text guidance): rendered in threshold table + Section 9 recommended templates.
- APG-03 (per-step-type threshold table; 15 for research-heavy): rendered with discuss/plan/research = 15; execute (auto/auto+tdd/checkpoint:*) = 5; Slice-frontmatter override.
- APG-04 (3-advisory clear+reinject): rendered as advisory 3 in the 6-advisory ladder table with compaction.snapshot_taken cross-link.
- APG-05 (3-more force-stop+human-gate): rendered as advisories 4-6 in the ladder, advisory 6 = human_gate via opencode question tool.
- APG-06 (paralysis_event schema task_id/count/threshold/agent_response): Pydantic ParalysisEvent rendered with extra='forbid' and all required fields + state-specific extensions (snapshot_event_id + recent_tool_calls).
- Per-plan SUMMARY.md gate closed.
</success_criteria>

<output>
After completion, the artifacts are:
- `.planning/milestones/v41/phases/404/specs/ANALYSIS-PARALYSIS-GUARD.md` (>= 500 lines)
- `.planning/milestones/v41/phases/404/02-analysis-paralysis-guard-spec-SUMMARY.md` (>= 80 lines)

Plan 04 (v40 EVENT-TAXONOMY.md amendment) in Wave 2 can now reference this spec for `state.step.paralysis_event`.
</output>
