# Analysis Paralysis Guard (Canonical, v41)

> **Phase:** 404
> **Status:** Canonical (v41)
> **Requirements covered:** APG-01..APG-06
> **Build-mode only.** `state.build.*` MUST NOT import the Teach-mode subtree (cardinal mode-isolation rule, PROJECT.md). The classifier module lives at `state_build/harness/paralysis/bash_classifier.py`.
> **Authoritative ordering:** Pydantic class definitions are authoritative; prose is supplementary.
> **Sibling specs:** PROOF-GATE.md (PRF strike counter — INDEPENDENT from APG paralysis counter; see Section 6 §APG-vs-PRF), SCOPE-PROHIBITION.md (files_modified allowlist + prohibited-language scan — neither participates in the paralysis counter).

The harness counts consecutive read-only tool uses per active task (APG-01). On threshold cross (APG-02 default 5; APG-03 per-step-type), the harness injects an advisory. The 6-advisory ladder (APG-04 reinject at advisory 3; APG-05 force-stop+human-gate at advisory 6) is independent from the PRF strike counter (see PROOF-GATE.md Section 6 §APG-vs-PRF). Each advisory and escalation emits a `ParalysisEvent` (APG-06). This spec is the design contract that v14 Build Kernel implements; v15 Build Core Commands registers the per-Slice-stage threshold lookup; Phase 405 DEV-04 consumes `tier=human_gate` events as input to the human-gate path; Phase 406 cites this spec for tier-1, tier-3, and tier-4 of the 4-tier intervention ladder.

**The classifier is ADVISORY, not a security boundary.** Mirrors gsd-2's `tool-system.md:851` — no command allowlist/denylist; the classifier is a heuristic for paralysis detection. The hard security boundary is the `files_modified` allowlist (SCOPE-PROHIBITION.md SRP-04). A determined agent can evade the classifier via obfuscated payloads — base64-decoded scripts, eval-piped strings, heredoc-bodied invocations (documented limitation, Section 5). The classifier's success metric is detecting genuine read-only loops in cooperative agents; it is not a defense against malicious behavior.

## Read-Only Tool Set (APG-01)

The harness classifies every tool invocation as read-only or write. Read-only invocations increment the per-task consecutive-read-only counter; write invocations reset it to 0. The tool set is fixed by opencode's tool taxonomy; only Bash needs sub-classification (the bash_classifier module, Section 3). All other tools have a fixed classification by name — no per-invocation analysis required.

### Inherently read-only tools

- **Read** — always read-only. Filesystem load with no mutation; multiple-target reads (Read with offset/limit) all count as a single read tool call.
- **Grep** — always read-only. Pattern search over the workspace; no mutation.
- **Glob** — always read-only. Pathname enumeration; no mutation.
- **Explore** — always read-only (opencode's plan-tool / explore-tool taxonomy; if absent in a given opencode build, fall back to Read/Grep/Glob). Read-side reconnaissance with no side effects.
- **WebFetch** — read-only (no filesystem mutation). External resource load; payload returned to the agent context.
- **WebSearch** — read-only. Query returns search results; no mutation.

### Inherently write tools

- **Write** — always write. Filesystem mutation (file creation or overwrite).
- **Edit** — always write. Filesystem mutation (in-place patch).
- **NotebookEdit** — always write. Notebook cell mutation.

### Sub-classified tools

- **Bash** — sub-classified via `bash_classifier.py` (see Section 3). Read patterns -> read-only counter increment; write patterns -> counter reset to 0. The classifier is the only per-invocation analysis the harness performs.
- **MCP tools** — by default classified as **write** (conservative) UNLESS the specific MCP tool's name appears in an opt-in read-only list. v14 implementation finalizes the list; this spec stipulates the default is conservative. Rationale: MCP tools are arbitrary extension points; treating them as write by default avoids the classifier-evasion attack surface where an agent invokes an MCP tool that happens to write but is incorrectly listed as read.

### Counter reset rule

- "An intervening Write/Edit/Bash-write tool call resets the per-task consecutive read-only counter to 0."
- "**Counter reset requires the tool call to be ALLOWED by the tool.execute.before stack** (PROOF-GATE.md Section 5 Layer 1-4 enforcement). A REJECTED Write/Edit (e.g., scope_deviation, plan_edit_blocked, scope_check, gate_strike) does NOT reset the counter — it counts as a no-op for paralysis purposes (the agent didn't actually mutate anything)."

Rationale: a rejected write that resets the counter would create a paralysis-evasion gadget. An agent stuck in a read loop could emit one rejected Write per N reads, keeping the counter at 0 indefinitely. The reset-on-allowed-only rule closes that gadget; counter semantics track ACTUAL workspace mutation, not attempted mutation.

## Bash Classifier Module

The bash classifier is a single Python module exporting three pre-compiled regex corpora plus a classification function. Mirrors gsd-2's `branch-patterns.ts` single-module pattern (`file-tracking.md §branch-patterns`): updates flow from one place; every consumer imports from this module; no parallel definitions in other modules. The module lives at `state_build/harness/paralysis/bash_classifier.py` and imports stdlib `re` only (no third-party dependencies; no Teach-mode imports; mode-isolation cardinal rule preserved).

### READ_ONLY_PATTERNS corpus

From 404-CONTEXT.md `<decisions>` Read-only Bash classification (APG-01 expanded). Adapted from gsd-2's `bash-interceptor.ts:15-54` read-side rules (3 patterns: cat-family, grep-family, find-family) plus state-specific extensions (filesystem inspection, jq/yq guarded against -i in-place mode, git read-only subcommands).

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
```

Notes on the corpus:

- **`cat(?!\s*<<)`** — negative lookahead excludes `cat <<EOF` heredoc invocations (which can carry write payloads in the heredoc body).
- **`jq|yq` guarded against `-i`/`-I`** — `jq -i` is in-place mode; would mutate the input file. The lookahead `(?!.*-[iI]\b)` excludes in-place invocations from the read-only set.
- **`git ... branch -l`** — `git branch` without flags lists branches (read), `git branch -l` is the explicit list flag; `git branch <name>` (create) and `git branch -d/-D` (delete) are excluded.
- **`git config --get`** — read-only config inspection. `git config <key> <value>` (set), `git config --add`, `git config --unset` are write.

### COMPOUND_SEP tokenization

```python
COMPOUND_SEP = re.compile(r"(?:;|\&\&|\|\||\||\&)(?![\w])")
```

Tokenizes a Bash command on shell-boundary tokens (`;`, `&&`, `||`, `|`, `&` at word boundaries; heredoc bodies treated as opaque single tokens). Classify each sub-command independently. If **any** sub-command is non-read-allowlist (or matches a write-pattern below), the whole compound is `write`. Pure-machine; no real shell-AST parser required; conservative.

The `(?![\w])` negative lookahead prevents splitting inside identifiers — e.g., `grep "a||b" foo.txt` (a literal `||` inside a quoted regex) tokenizes as a single sub-command, not three. This is a conservative approximation: a determined evader could embed shell metacharacters inside a string literal that the regex doesn't recognize, but the resulting compound classification will still be `write` because the unrecognized sub-command falls into the conservative-on-unknown bucket.

### WRITE_SYSCALL_PATTERNS corpus (inline-interpreter payload scanning)

For inline-interpreter invocations — `python3 -c '...'`, `node -e '...'`, `ruby -e '...'`, `perl -e '...'`, `bash -c '...'`, `sh -c '...'` — the classifier extracts the payload (the quoted/escaped string following `-c` / `-e`) and greps it against WRITE_SYSCALL_PATTERNS. Payload match -> classify as `write`. Clean payload -> classify as `read`. Pure-machine; deterministic; matches PRF-04 spirit.

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

Notes on the corpus:

- **`open\s*\(..., '[wax]`** — Python `open()` write/append/exclusive-create modes. Bare `open('foo.txt')` defaults to `'r'` (read) and does NOT match.
- **`subprocess.*`** — conservative bucket. Any subprocess invocation can launch a write command; the classifier conservatively treats the whole inline-interpreter payload as write if it imports/calls subprocess.
- **`[^&<>|]>(?![&=])`** — bare `>` redirect in the payload. The negative-character-class `[^&<>|]` prevents matching `>=`/`>>`/`<>` and similar bigraph operators; the negative lookahead `(?![&=])` prevents matching `>&` / `>=`.
- **`fs.write`, `node:fs.write`** — Node.js fs module write methods. Covers both the legacy `fs` import and the modern `node:fs` ES module specifier.
- **`File.write`, `IO.write`** — Ruby File/IO write methods. `File.open(..., 'w')` also covered by the explicit `open\s*\([^)]*,\s*['\"]w` clause.

The WRITE_SYSCALL_PATTERNS list is conservative-on-purpose: false positives (an inline payload classified write when the actual effect is read-only) only delay paralysis detection; false negatives (a real write classified as read) let paralysis loops continue and undermine the guard. The corpus prefers the safer error mode.

### Classification function signature

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

**Conservative-on-unknown:** the classifier defaults to `write` on any sub-command that doesn't match a READ_ONLY_PATTERN. This means the paralysis counter resets on unknown invocations — preferring false negatives (counter resets when it "should" have incremented) over false positives (counter increments when it "should" have reset). False positives delay detection of legit work; false negatives only delay detection of paralysis loops. The trade-off favors letting work proceed; paralysis detection has a 6-advisory ladder to recover even when the first few signals are missed.

**Pre-compilation requirement:** all patterns in READ_ONLY_PATTERNS, WRITE_SYSCALL_PATTERNS, and COMPOUND_SEP are pre-compiled at module import time via `re.compile(...)`. Per-invocation compilation is forbidden (DoS surface; regex compilation is expensive relative to matching). v14 enforces via a unit test that imports the module and asserts each pattern is `re.Pattern` (not `str`).

**No nested quantifiers:** patterns must NOT use nested quantifiers like `(.+)+` or `(a|aa)*` that admit catastrophic backtracking on adversarial inputs. The corpus rendered above satisfies this; v14 unit test corpus includes adversarial inputs (long strings of repeated separators) to verify worst-case latency is bounded. Recommended bound: <1ms per classification on a 64KB payload. Bash command length cap (recommended 64KB; v14 sets) further bounds worst case.

## Compound Commands, Redirection, Inline-Interpreter Rules

### Compound-command handling

- **Split tokens on COMPOUND_SEP**: `;`, `&&`, `||`, `|`, `&` at word boundaries; heredoc bodies (`<<EOF ... EOF`) treated as opaque single tokens (no recursive parsing into heredoc payload).
- **Worst-sub-command wins**: classify each sub-command via READ_ONLY_PATTERNS + inline-interpreter scan + redirection check; if ANY sub-command classifies as `write`, the whole compound is `write`.
- **No real shell-AST parser**: regex tokenization is good enough; pure-machine; conservative.

**Positive example:** `cat foo.txt | grep bar` -> two sub-commands; both READ_ONLY_PATTERNS match; both `read`; whole compound: `read`. The pipe between two read tools is itself a read invocation.

**Positive example:** `ls -la && pwd && git status` -> three sub-commands; all match READ_ONLY_PATTERNS; whole compound: `read`. Chained read tools with `&&` count as a single increment of the consecutive-read-only counter.

**Negative example:** `grep bar foo.txt && rm foo.txt` -> two sub-commands; first `read`; second unrecognized (`rm` not in READ_ONLY_PATTERNS) -> `write`; whole compound: `write`. The `rm` triggers conservative-on-unknown and resets the counter.

**Negative example:** `cat foo.txt | tee bar.txt` -> two sub-commands; first `read`; second `tee` with path target -> `write` (see redirection table below); whole compound: `write`.

**Negative example:** `find . -name '*.py' -exec rm {} \;` -> single sub-command (no compound separator at top level); `find` matches READ_ONLY_PATTERNS — BUT the `-exec rm` flag is a known classifier evasion. v1 does NOT scan `-exec` flags; this is a documented limitation (Section 5 §Documented limitations). v14 may add a `find` flag scanner.

### Output redirection

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

**Pure-machine token detection at parse time.** No path-resolution magic (no symlink chasing, no cwd-relative gymnastics) — a redirect is judged by its right-hand token only. Edge cases:

- `> "/dev/null"` (quoted) — matches the `/dev/null` rule; treated as read. The classifier strips surrounding quotes from path tokens before the `/dev/null` literal compare.
- `> /dev/null 2>&1` — both redirects match the read rules (`/dev/null` and `2>&1`); whole compound: read.
- `> /dev/null; echo hi > foo.txt` — two sub-commands separated by `;`; first read, second write; whole compound: write.

### Inline-interpreter payload scanning

- For `python3 -c '...'`, `node -e '...'`, `ruby -e '...'`, `perl -e '...'`, `bash -c '...'`, `sh -c '...'`: extract the payload (the quoted/escaped string following `-c` / `-e`).
- Grep the payload against WRITE_SYSCALL_PATTERNS (Section 3 corpus).
- Match -> classify as `write`. Clean -> classify as `read`.

**Positive example:** `python3 -c 'import json; print(json.load(open("foo.json")))'` -> payload contains `open(...)` but mode arg is missing OR default `r`; check against the `open(..., 'w'|'a'|'x')` regex (`\bopen\s*\([^)]*,\s*['\"][wax]`) — NO match -> `read`. (Bare `open()` calls in read mode pass; only `open(..., 'w')` style trips the regex.)

**Positive example:** `python3 -c 'import sys; sys.stdout.write("hi")'` -> payload does NOT match any WRITE_SYSCALL_PATTERN (sys.stdout.write is stream-write, not filesystem write); classified `read`. v1 corpus does NOT cover stdout-write-as-filesystem-write because the redirect (`> path`) at the outer shell level is the canonical write signal; the inner payload is judged on filesystem-mutation API calls only.

**Negative example:** `python3 -c 'open("foo.txt", "w").write("hi")'` -> payload matches `\bopen\s*\([^)]*,\s*['\"][wax]` -> `write`.

**Negative example:** `bash -c 'echo hi > foo.txt'` -> payload matches `[^&<>|]>(?![&=])` (bare `>` redirect) -> `write`.

**Negative example:** `node -e 'require("fs").writeFileSync("foo.txt", "hi")'` -> payload matches `\b(fs|node:fs)\.(write|writeFile|appendFile|...)` -> `write`. Note: `writeFileSync` is captured by the `\bwriteFile` prefix in `(write|writeFile|appendFile|...)`.

**Negative example:** `ruby -e 'File.write("foo.txt", "hi")'` -> payload matches `\b(File|IO)\.(write|...)` -> `write`.

**Negative example:** `python3 -c 'subprocess.run(["rm", "foo.txt"])'` -> payload matches `\bsubprocess\.` -> `write` (conservative). Even though `subprocess.run` here invokes `rm` (a write at the OS level), the classifier's signal is the `subprocess.` prefix match; conservative classification is correct.

### Documented limitations

- Obfuscated payloads MAY pass as `read`. Examples:
  - `bash -c "$(echo 'echo hi > foo.txt' | base64 -d)"` — base64-encoded payload; the decoded write is hidden from the regex scan.
  - `bash -c 'eval "echo hi > foo.txt"'` — eval-piped payload; the eval'd string is constructed at runtime and not visible to the scan.
  - `cat <<EOFINNER | bash` then `rm foo.txt` then `EOFINNER` — heredoc body is opaque; the rm inside is not scanned.
  - `find . -name '*.py' -exec rm {} \;` — find's `-exec` flag runs an arbitrary command; the classifier matches `find` against READ_ONLY_PATTERNS and does not parse the `-exec` payload.
  - `python3 -c "exec(open('script.py').read())"` — exec'd payload loaded from disk; the loaded script is opaque to the scanner.
- The classifier is ADVISORY; the hard security boundary is `files_modified` allowlist (SCOPE-PROHIBITION.md SRP-04). v14 acknowledges these limitations; future work may add a second pass that grep-scans the OUTPUT of a dry-run (if/when opencode supports a `--dry-run` flag), but this spec does NOT mandate.

The framing: paralysis loops are a cooperative-agent problem, not an adversarial-agent problem. An agent stuck reading the same files repeatedly because it cannot decide what to write is exactly the failure mode the guard targets. An agent deliberately obfuscating its writes to evade the counter is acting in bad faith; the response is the harder layer at SCOPE-PROHIBITION.md SRP-04 (`files_modified` allowlist diff-the-proposed-write enforcement at `tool.execute.before`), not a more elaborate classifier.

## Exit Code Is Not a Strike/Paralysis Trigger

- **Bash exit code is NOT a strike trigger.** Mirrors gsd-2's preparation-vs-execution narrowing (`agent-loop.ts:324-329`, issue #3618): a `grep` that exits 1 ("no matches") is valid usage, not a paralysis trigger.
- The paralysis counter cares about **classification of the invocation** (read vs write), not about its exit status.
- A `grep -q nonexistent foo.txt` exiting 1 still classifies as `read` and increments the consecutive-read-only counter.
- A `python3 -c 'open("foo.txt", "w")...'` exiting non-zero still classifies as `write` and resets the counter — even though the write attempt failed (the agent's INTENT was to write; that's what the counter measures).

The principle: counter mechanics track agent INTENT (as visible in the tool call shape), not agent ACHIEVEMENT (as visible in the exit code). An agent grepping for a string that does not exist is exhibiting reading behavior; the counter increments. An agent attempting to write a file (regardless of whether the write succeeds) is exhibiting writing behavior; the counter resets.

**Why this matters:** counting exit-non-zero as a strike would conflate two distinct failure modes — (a) the agent is stuck reading and not writing (paralysis), and (b) the agent is writing but its writes are failing (execution error). These are different problems with different remediations. The paralysis advisory says "state your hypothesis and write code"; an execution-error advisory would say "your write failed because X; fix X". The advisory ladder targets paralysis only; execution errors flow through the PRF strike chain (PROOF-GATE.md) which measures completion-claim failures.

**Cross-reference:** PROOF-GATE.md Section 6 §Strike trigger uses the same preparation-vs-execution narrowing for PRF strikes — strikes accrue only at the completion-claim boundary, not on mid-task exit codes. Both counters (APG, PRF) inherit the same gsd-2 §0 Correction 1 principle: distinct counters at distinct scopes, never conflated. The mid-task `grep` exit-1 is invisible to both the APG advisory ladder (counter increments but does not trigger a strike) and the PRF strike chain (strikes accrue only at `complete_task` MCP boundary).

**Implementation note for v14:** the bash classifier returns a Literal of `"read" | "write"` — there is no third value for "failed". Exit-code observation is the harness's responsibility (and the harness logs exit codes to the event store for audit), but the classifier itself does not see exit codes. The classification function is pure with respect to the command string; v14 unit tests pass deterministically without invoking the actual shell.

### Cooperative-agent framing

The advisory-not-security framing recurs throughout this spec; it deserves explicit treatment because the implication shapes every design choice that follows. The paralysis guard is built for the **cooperative agent** failure mode: an LLM that genuinely tries to make progress but gets stuck in a read-decide-read-decide loop because its reasoning surface is starved of the next concrete write commitment. The remediation pattern (advisory injection -> reinjection of a focused PLAN -> human gate) targets that failure mode directly.

The spec intentionally does NOT defend against the **adversarial agent** failure mode (an LLM deliberately obfuscating its writes to evade detection). Defense against adversarial behavior lives at SCOPE-PROHIBITION.md SRP-04 (`files_modified` allowlist) — the diff-the-proposed-write enforcement at `tool.execute.before` is a hard reject; the paralysis classifier is a soft signal. Layering the two — soft signal for cooperative paralysis, hard reject for adversarial mutation — keeps each layer's cost commensurate with the threat it addresses.

A practical consequence: v14 unit tests for the bash classifier should NOT include adversarial-evasion fuzzing as a primary success metric. Adversarial-evasion tests have value as documentation (they verify the documented limitations are accurate), but they should not gate the implementation. The classifier's primary unit-test fixture is the redirection table above (Section 4) plus the positive/negative examples in `### Inline-interpreter payload scanning`. v14 implementers can refer to this spec for the canonical fixture corpus.

### Cross-reference to PROOF-GATE.md

PROOF-GATE.md Section 6 §APG-vs-PRF counter independence and Section 6 §Strike trigger together encode the same preparation-vs-execution narrowing that this section applies to APG advisories. Specifically: PRF strikes accrue only at the `complete_task` MCP boundary (PROOF-GATE.md Section 6 §Strike trigger); APG advisories accrue only on consecutive-read-only classification (this section). Both counters refuse to conflate mid-task exit-code observation with the deeper failure modes they target. This is gsd-2 §0 Correction 1 applied to two distinct counters at two distinct scopes.

When a single task experiences both APG paralysis AND PRF strikes simultaneously (e.g., the agent reads in a loop, eventually claims completion, the completion claim fails the pure-machine evaluator, AND the paralysis counter has hit threshold), each chain advances independently. The harness emits one `paralysis_event` AND one `gate_strike` per qualifying trigger; the `harness_intervention` umbrella event (Phase 406 HRN-05) aggregates both into a single human-gate surface when either chain reaches advisory 6 (or strike 6).

### Closing note on Sections 1-5

Sections 1-5 establish the read/write classification substrate: what tools are inherently read or write (Section 2), how Bash invocations are sub-classified via the single-module regex corpora (Section 3), how compound commands and redirections and inline-interpreter payloads are handled (Section 4), and why exit codes do NOT participate in the strike/paralysis trigger logic (Section 5). Sections 6-10 build on this substrate: the per-step-type threshold table (Section 6) dispatches on the Step `type` Literal from Phase 403's frontmatter schema; the 6-advisory ladder (Section 7) consumes classification events; the `ParalysisEvent` Pydantic payload (Section 8) records each advisory and escalation; advisory message guidance (Section 9) and cross-references (Section 10) round out the spec.

The structural ordering — substrate first (Sections 1-5), policy second (Sections 6-7), payload schema third (Section 8), and operator guidance last (Sections 9-10) — keeps the spec readable top-to-bottom. Implementers can read Sections 1-5 in isolation and have a complete picture of the classifier; readers concerned only with policy can skip to Section 6.

## Per-Step-Type Threshold Table (APG-02, APG-03)

The harness reads the active Step's `type` field from frontmatter (Phase 403 STEP-PLAN-FORMAT.md schema) and the active Slice's stage from `SLICE-CYCLE.md` (Phase 402); these two axes determine the consecutive-read-only threshold for the active task. Defaults are pinned below; Slice frontmatter MAY override.

### Default thresholds

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

**Per-step-type axis (5 default for execute):** matches the Step `type` Literal from STEP-PLAN-FORMAT.md frontmatter schema (STP-02). All five execute-slice task types share the 5-threshold default; the discriminator is the parent Slice stage, not the Step type. The Step `type` Literal is reproduced from STEP-PLAN-FORMAT.md `<frontmatter_schema>` as: `Literal["auto", "auto+tdd", "checkpoint:human-verify", "checkpoint:decision", "checkpoint:human-action"]`.

**Per-Slice-stage axis (15 default for research-heavy):** when the active Slice is in `discuss-slice` / `plan-slice` / its `research` sub-stage, the agent is explicitly invited to read deeply. The threshold raises to 15 to reflect this. The Slice-stage axis derives from the active stage in `SLICE-CYCLE.md` (Phase 402). The rationale: research/discuss/plan stages explicitly expect a high read-to-write ratio (the deliverable IS the synthesis of reads into a plan or discussion artifact); paralysis advisories at the 5-threshold would fire spuriously during legitimate research work.

**Read-only false-positive avoidance:** research-heavy step types get the 15-threshold default specifically to avoid false-positive advisories. Combined with the advisory-not-security framing (Section 1), the spec leans into the cooperative-agent assumption: research stages are EXPECTED to read deeply; the advisory only fires if reading exceeds 15 consecutive operations without a write commitment, at which point the LLM almost certainly IS stuck. gsd-2-lineage advisory-not-security framing is cited explicitly: `tool-system.md:851` documents that gsd-2 itself has no command allowlist/denylist; the classifier is a heuristic that surfaces patterns, not a wall that blocks behavior.

### Slice-level override

Slice frontmatter MAY override the defaults via:

```yaml
paralysis:
  execute_threshold: int    # overrides the 5-default for all execute-slice Steps in this Slice
  research_threshold: int   # overrides the 15-default for the discuss/plan/research stages
```

Mirrors Phase 402's `compaction:` frontmatter shape. **Step-level override is REJECTED** for v1 (mirrors Phase 403's rejection of Step-level autonomy: Slice is the autonomy unit per D-11). Rationale: a per-Step paralysis override would let a planner author a `paralysis: {execute_threshold: 1000}` for a Step whose work is hard, effectively disabling the advisory ladder for that Step. The override surface deliberately stops at the Slice level so that the unit of "we expect this slice to be hard" matches the unit of "we are willing to relax the paralysis bound for it."

### Counter scope

- "**Counter scope: per active task.** Each Step's tasks share the Step's threshold; each task has its own consecutive-read-only counter; counters reset to 0 on task boundary and on any allowed Write/Edit/Bash-write tool call."
- "Cross-task carry-over is forbidden: the counter for task N closes (resets) when task N completes (pass/flag/omitted) and task N+1 starts fresh."
- "Cross-Step carry-over is forbidden: Step boundary closes all task counters."
- "Cross-Slice carry-over is irrelevant (fresh session per Slice — CTX-02)."

The per-task scope mirrors the gsd-2 lineage at `agent-loop.ts:191` — gsd-2's `consecutiveAllToolErrorTurns` is scoped per `runAgentLoop` invocation, the finest unit of agent work that produces a single completion claim. State's analog is the task: each task's read-only chain is independent; task transitions are clean boundaries.

## Six-Advisory Escalation Ladder (APG-04, APG-05)

When the per-task counter exceeds the threshold, the harness injects an advisory and emits a `ParalysisEvent`. The 6-advisory ladder (advisories 1-3 advisory tier, advisory 3 ALSO fires reinject single-shot, advisories 4-6 post-reinject advisory tier, advisory 6 fires human gate) is INDEPENDENT from the PRF strike counter (cross-reference: PROOF-GATE.md Section 6 §APG-vs-PRF).

### Escalation table

| Advisory # | Tier | Trigger | Harness action | Event emitted |
|-----------|------|---------|----------------|---------------|
| 1 | advisory | Counter exceeds threshold for the 1st time on this task | Inject system advisory naming the count + threshold + recent commands + remediation prompt | `state.step.paralysis_event` (tier=advisory, advisory_number=1) |
| 2 | advisory | Counter exceeds threshold again on this task after another window of read-only operations | Same advisory; updated count + remediation prompt | `state.step.paralysis_event` (tier=advisory, advisory_number=2) |
| 3 | advisory + reinject | Counter exceeds threshold for the 3rd time on this task | Inject advisory; fire compaction snapshot (records `snapshot_event_id`); clear context; reinject PLAN with focused prompt naming the specific paralysis pattern + the failing reasoning surface | `state.step.paralysis_event` (tier=reinject, advisory_number=3, snapshot_event_id=<id>) |
| 4 | advisory (post-reinject) | Counter exceeds threshold on the reinjected agent for the 1st time | Inject advisory; counter visible as 4 of 6 | `state.step.paralysis_event` (tier=advisory, advisory_number=4) |
| 5 | advisory | Counter exceeds threshold for the 5th time on this task | Inject advisory; warning that next paralysis fires human gate | `state.step.paralysis_event` (tier=advisory, advisory_number=5) |
| 6 | human_gate (force-stop) | Counter exceeds threshold for the 6th time | Force-stop the session; surface a human gate via opencode `question` tool with the paralysis pattern + the per-advisory recent-commands log + the 6-advisory chain audit | `state.step.paralysis_event` (tier=human_gate, advisory_number=6) |

**On advisory 6 human resolution:** human picks `proceed` (agent continues with a fresh task context) or `abort` (Slice transitions to `pending_replan` — same path as SRP-05 `split_recommendation`). v14 implements both paths; spec stipulates the two named resolutions.

### Counter reset on task completion

- "When a task closes (pass/flag/omitted), the consecutive-read-only counter for that task closes too."
- "The advisory chain (1-6) closes alongside; subsequent failures on the SAME task_id are impossible (task is done) and subsequent failures on the NEXT task start fresh from advisory 1."
- "**Reset rule diverges from PRF strike counter:** PRF strikes accrue across the reinject tier (per PROOF-GATE.md Section 6 §Reset rule); APG advisories ALSO continue counting across the reinject tier (the same 'continue counting' semantic — D-8 reading: 'human gate at advisory/strike 6 total')."

### APG-vs-PRF counter independence (cross-reference)

Cross-reference: `PROOF-GATE.md` Section 6 §APG-vs-PRF counter independence — this spec mirrors the same statement. Both counters can independently reach force-stop. The `harness_intervention` event (Phase 406 HRN-05) is the umbrella; both `paralysis_event` and `gate_strike` cite it as `trigger_reason`. The principle inherits from gsd-2's `loop-control.md §0 Correction 1`: distinct counters at distinct scopes, never conflated. State's two counters — APG paralysis (per task, per-read-only-classification) and PRF strikes (per (task_id, check_id), per-completion-claim-evaluation) — operate at orthogonal scopes; neither resets the other; neither's escalation suppresses the other's.

A worked scenario: an agent reads 5 times (APG counter at 5, threshold crossed, advisory 1 fires), then attempts to complete the task (PRF check fires; first fail -> PRF strike 1), then reads 5 more times (APG counter at 5 again post-reset rules, advisory 2 fires), then attempts completion again (PRF strike 2). Both counters are advancing; both will independently reach force-stop if the agent never makes progress; the `harness_intervention` umbrella event aggregates both for the human-gate surface.

## ParalysisEvent Pydantic Payload (APG-06)

Every advisory and escalation emits a `state.step.paralysis_event`. The Pydantic payload carries the audit-trail evidence: count, threshold, tier, advisory number, agent response excerpt, the triggering bash command, session_id, and (on reinject tier) the compaction snapshot cross-link. Payload riding on the `EventEnvelope` from `src/state_core/schema.py` (lines 239-265); `aggregate_type="step"`, `aggregate_id=step_id`, `type="state.step.paralysis_event"`, `data=<ParalysisEvent.model_dump()>`.

### Pydantic class

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

The 13-field payload extends 404-CONTEXT.md `<decisions>` Read-only Bash classification subsection (original 11 fields) with two state-specific extensions: `snapshot_event_id` (matches the `GateStrike` pattern in PROOF-GATE.md for the reinject tier cross-link) and `recent_tool_calls` (provides the human-gate operator with the immediate-precedent tool-call window for diagnosis). The 2KB excerpt convention for `agent_response_summary` and `triggering_command` is shared with PROOF-GATE.md `GateStrike` via a single bounded-truncation utility.

### Bounded truncation

Same discipline as `GateStrike` (see PROOF-GATE.md Section 7 §Bounded truncation): **2KB per excerpt, 10KB total per ParalysisEvent**. Truncation marker: `[... truncated <N> bytes ...]`. The harness-owned truncation utility is shared between APG and PRF events. The total 10KB bound applies to the sum of `agent_response_summary` + `triggering_command` + `recent_tool_calls` (joined by newline); if the sum exceeds 10KB, the truncation utility trims `recent_tool_calls` from the front (oldest tool calls dropped first), then `triggering_command`, then `agent_response_summary` as a last resort. Order is deterministic; replay rebuilds the same truncated payload bit-identically.

### State transitions

- "ParalysisEvent is APPEND-ONLY (no UPDATE/DELETE; corrections are NEW events)."
- "The ParalysisEvent itself does not transition the Slice/Step FSM; the harness's in-memory paralysis-counter state transitions on EMISSION (advisory_number increments)."
- "Replay rebuilds counter state from the event store: scan `state.step.paralysis_event` events filtered by `aggregate_id == step_id`, sort by `triggered_at`, replay tier transitions in order."

Append-only semantics are inherited from the v40 event-sourced baseline (PROJECT.md cardinal rule: "every domain event is written to `.state/events.sqlite` FIRST"). Corrections to a ParalysisEvent (e.g., a v14 bug-fix that re-classifies a borderline command from advisory tier to reinject tier) are NEW events that supersede the prior; the prior remains in the audit log for traceability.

## Advisory Message Authoring Guidance

Per 404-CONTEXT.md Claude's Discretion, exact advisory wording is deferred to v14 + EXEMPLAR-driven sizing. This section pins the recommended template; v14 may refine after observing real Step-execution patterns.

### Recommended advisory template (tier=advisory)

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

The template surfaces three signals to the agent: (1) the quantitative fact that read-only operations exceeded the threshold (count, threshold, advisory_number); (2) the actionable demand ("state your hypothesis... write code or report blocker"); (3) the escape hatch (`request_step_split` for scope failure, `complete_task` for partial completion with explicit blocker). The escape hatches are deliberately named — the agent is told the canonical tool to call, not asked to discover it from a tool catalog.

### Recommended advisory template (tier=reinject, advisory 3)

Adds: "A compaction snapshot has been recorded (snapshot_event_id={id}). The active session will receive a fresh-context reinjection of the PLAN focused on the paralysis pattern. After reinjection, the counter continues at advisory 4 — your next paralysis triggers advisory 5 with a warning that the 6th triggers a human gate."

The reinject-tier message has two audiences: the current agent (about to be paused) and the post-reinject agent (about to start). For the current agent, the message confirms the snapshot was taken and the session will pause; for the post-reinject agent, the focused PLAN reinjection naming the specific paralysis pattern serves as the primary context recovery surface (the snapshot itself is reinjected via Phase 402's reinject payload XML shape; the advisory message complements the snapshot with the paralysis-specific framing).

### Recommended human-gate prompt (tier=human_gate, advisory 6)

Surfaces via opencode `question` tool with: the failing task_id, the 6-advisory chain (event ids), the recent commands (all 6 × 5 = 30 most recent), and two named resolutions: `proceed` (clear paralysis chain, agent continues on the same task with a fresh sub-counter) or `abort` (Slice transitions to `pending_replan`, mirrors SRP-05 split path).

The human-gate prompt is necessarily denser than the advisory prompts because it serves a human operator (not the agent). The operator reads the full chain, picks one of two named resolutions, and the harness resumes accordingly. The `proceed` path is a one-shot grace: the paralysis-chain state is cleared and the agent gets to retry with a fresh sub-counter on the same task. If the operator's `proceed` is followed by another full 6-advisory cycle, the next human-gate prompt presents the second chain alongside the first for context.

### Claude's Discretion

- "Exact wording deferred to v14 per 404-CONTEXT.md."
- "Recommended placeholders (above) include count, threshold, advisory_number, recent_tool_calls — all available in the ParalysisEvent payload."
- "v14 may add: time-since-last-write, byte counts of files read in the window, names of files read repeatedly (recommended: top-3 most-read files in the read-only window)."

The Claude's Discretion fields are deliberately framed as additive: v14 implementers can extend the advisory template with the suggested additions (time-since-last-write, etc.) without changing the ParalysisEvent payload schema (those signals are computable from the existing fields and the event store at advisory-emission time). Schema extensions to the ParalysisEvent payload itself require a Phase 404 spec amendment.

## Cross-references

- **Sibling spec — proof gate:** `PROOF-GATE.md` Section 6 §APG-vs-PRF defines the same counter-independence statement; this spec mirrors it. PRF strike counter increments at the completion-claim boundary; APG paralysis counter increments on consecutive-read-only tool calls. Independent chains.
- **Sibling spec — scope:** `SCOPE-PROHIBITION.md` defines the `request_step_split` MCP tool (SRP-05) — the recommended escape hatch for an agent that recognizes paralysis. Advisories instruct the agent to call `request_step_split` rather than continue spinning.
- **Phase 403 carry-forward — Step type:** `STEP-PLAN-FORMAT.md` §Frontmatter Schema (STP-02) provides the `type` Literal that the per-step-type threshold table dispatches on.
- **Phase 402 carry-forward — compaction:** `CONTEXT-PROTOCOL.md` §Compaction (CTX-05/06) is the source of the `compaction.snapshot_taken` event that ParalysisEvent.snapshot_event_id cross-links when tier='reinject'.
- **Phase 402 carry-forward — Slice cycle:** `SLICE-CYCLE.md` defines the discuss/plan/execute/verify stages that the per-Slice-stage threshold axis dispatches on (research/discuss/plan default 15; execute default 5).
- **v40 baseline — events:** `EVENT-TAXONOMY.md` naming convention `state.{tier}.{action}`; this spec adds `state.step.paralysis_event`. Plan 04 of this phase appends the `## v41 Amendment` block to v40 EVENT-TAXONOMY.md registering this event.
- **gsd-2 lineage:** `bash-interceptor.ts:15-54` (read-side rules 3 patterns); `tool-system.md:851` (no allowlist/denylist; advisory-not-security framing); `loop-control.md §0 Correction 1` (four-counter independence); `loop-control.md §4` (preparation-vs-execution narrowing — exit code is NOT a trigger); `file-tracking.md §branch-patterns` (single-module pattern).
- **Phase 406 forward:** `harness_intervention` (HRN-05) umbrella event aggregates `paralysis_event` + `gate_strike` + `scope_check` + `scope_deviation_request` + `split_recommendation`; the 4-tier intervention ladder (HRN-04) cites this spec for tier-1 (advisory inject) + tier-3 (force clear+reinject at advisory 3) + tier-4 (force-stop+human-gate at advisory 6).

v14 Build Kernel implements `state_build/harness/paralysis/bash_classifier.py` (single module with READ_ONLY_PATTERNS + WRITE_SYSCALL_PATTERNS + COMPOUND_SEP + classify()), the per-task consecutive-read-only counter cache, the 6-advisory state machine, the recent-tool-calls ring buffer, and the bounded-truncation utility (shared with PROOF-GATE.md). v15 Build Core Commands implements the per-Slice-stage threshold lookup (discuss/plan/research = 15; execute = 5) and the Slice-frontmatter override resolution. Phase 405 (Deviation Rules) consumes `ParalysisEvent.tier=human_gate` events as input to the DEV-04 human-gate path. Phase 406 (Harness Architecture Rollup) cites this spec for tier-1/3/4 of the intervention ladder; the `harness_intervention` umbrella event (HRN-05) aggregates ParalysisEvent.

The downstream consumer surface is large but well-bounded: v14 is the implementation; v15 is the orchestration; Phase 405 is the human-gate path; Phase 406 is the rollup. Each consumer reads this spec at its respective milestone-close gate; v14's bash_classifier.py unit tests use the redirection table (Section 4) and the positive/negative examples (Sections 4 inline-interpreter) as fixtures; v15's per-Slice-stage threshold lookup unit tests use the threshold table (Section 6); Phase 405's DEV-04 contract test asserts that `ParalysisEvent(tier="human_gate", advisory_number=6)` triggers exactly one `harness_intervention.tier_4` umbrella event.

### v14 implementation notes (non-normative)

The following implementation notes are guidance for v14 Build Kernel; the spec is normative, the notes are informative. Implementers MAY deviate when a deviation preserves the normative behavior.

**Counter cache shape.** The per-task counter is a small in-memory map keyed by `task_id`, valued by a `ParalysisCounterState` dataclass:

```python
from dataclasses import dataclass, field

@dataclass
class ParalysisCounterState:
    task_id: str
    step_id: str
    slice_id: str
    consecutive_read_only: int = 0        # current count
    threshold: int = 5                    # resolved at task-start from Step.type + Slice.frontmatter
    advisory_number: int = 0              # 0 = no advisory fired yet; 1..6 as the chain advances
    recent_tool_calls: list[str] = field(default_factory=list)  # ring buffer; max 10 entries
    last_increment_at: datetime | None = None
    snapshot_event_id: str | None = None  # set when advisory_number=3 fires the reinject
```

The cache is rebuildable from the event store on daemon restart (replay `state.step.paralysis_event` events filtered by `aggregate_id == step_id`, sort by `triggered_at`, replay tier transitions). Live cache is a soft state; the SQLite event store is authoritative (PROJECT.md cardinal rule).

**Threshold resolution at task start.** When the harness begins a task, it computes the threshold once and stores it in the `ParalysisCounterState`:

1. Read the Step frontmatter `type` field (from Phase 403 STEP-PLAN-FORMAT.md schema).
2. Read the Slice frontmatter `paralysis: {execute_threshold, research_threshold}` if present.
3. Determine the Slice's active stage from `SLICE-CYCLE.md` (execute/research/discuss/plan).
4. Apply the resolution rule:
   - If the Slice stage is research/discuss/plan AND `paralysis.research_threshold` is set, use it.
   - Else if the Slice stage is research/discuss/plan, use the 15 default.
   - Else if `paralysis.execute_threshold` is set, use it.
   - Else use the 5 default.

The resolved threshold is stable for the duration of the task; threshold changes mid-task are forbidden (Slice frontmatter is locked at Slice start; the threshold cannot drift while the task is in flight).

**Recent tool calls ring buffer.** The `recent_tool_calls` list is a fixed-size ring buffer (max 10 entries) of formatted strings. Each entry is the result of `format_tool_call(name, args)` — a one-line summary suitable for the advisory message. v14 ships a single `format_tool_call` function; advisory messages, human-gate prompts, and replay diagnostics all use the same formatter for output consistency.

**Bounded-truncation utility.** Shared between APG and PRF events (and any future event with a bounded text field). Signature:

```python
def truncate_with_marker(text: str, max_bytes: int = 2048) -> str:
    """Truncate to max_bytes; append marker `[... truncated <N> bytes ...]`.
    If the input is already shorter, return unchanged (no marker)."""
    ...
```

Per-field cap is 2KB by default; the total per-event cap (10KB) is enforced by the caller composing multiple truncated fields. Deterministic; replay produces bit-identical output.

**Snapshot cross-link wiring.** When advisory 3 fires, the harness emits a Phase 402 `compaction.snapshot_taken` event FIRST, captures the returned event id, THEN emits the `paralysis_event` with `snapshot_event_id=<id>`. The ordering is mandatory: the cross-link must be writable when the paralysis_event is persisted; emitting the paralysis_event first would leave a dangling reference. v14 wraps the two emissions in a single SQLite transaction.

**Force-stop semantics at advisory 6.** "Force-stop" means the harness ends the current agent loop, emits the `paralysis_event` with `tier=human_gate`, and surfaces the opencode `question` tool prompt. The agent does NOT receive a follow-up tool call until the human resolves; the session pauses cleanly. The harness MUST NOT auto-resolve `tier=human_gate` events under any tiered-autonomy setting (DEV-05 territory) — human resolution is mandatory at advisory 6.

**Replay correctness.** The deterministic-replay cardinal rule (PROJECT.md: "event payloads must be deterministic — no `datetime.now()` or randomness in handlers; replay must be bit-identical") applies to the paralysis counter state machine. The `triggered_at` field is supplied by the caller (the harness, with a wall-clock value at emission time) but is NOT used by the replay logic to compute counter state — the order of events in the SQLite event store (by `seq`) is the source of truth for state reconstruction. Replay correctness is verified by v14's `test_replay_paralysis_chain` fixture: persist a known sequence of `paralysis_event` records, drop the in-memory counter cache, replay the event store, assert the rebuilt cache state matches.

### Event taxonomy registration (forward reference)

This spec adds one new event type to the v40 baseline:

- `state.step.paralysis_event` — Pydantic payload `ParalysisEvent` (Section 8). Rides the `EventEnvelope` from `src/state_core/schema.py` with `aggregate_type="step"`, `aggregate_id=step_id`. Append-only.

Plan 04 of this phase (`04-event-amendments-PLAN.md`) appends a `## v41 Amendment` block to v40 EVENT-TAXONOMY.md registering this event alongside the events introduced by Plan 01 (`gate_strike`, `gate_resolved`) and Plan 03 (`scope_check`, `scope_deviation_request`, `scope_deviation_resolved`, `split_recommendation`, `step_verify_completed`, `slice_verify_completed`).

### Closing summary

This spec — ANALYSIS-PARALYSIS-GUARD.md — is the canonical design contract for the read-only-loop discipline guard in state's Build mode. APG-01 (read-only tool set + bash classifier) is covered in Sections 2-3. APG-02 (default 5-consecutive threshold) is covered in Section 6 §Default thresholds. APG-03 (per-step-type threshold table; 15 for research-heavy) is covered in Section 6 §Default thresholds and §Slice-level override. APG-04 (3-advisory clear+reinject) is covered in Section 7 §Escalation table row 3. APG-05 (3-more force-stop+human-gate) is covered in Section 7 §Escalation table rows 4-6 and the advisory-6 human resolution paragraph. APG-06 (paralysis_event schema task_id/count/threshold/agent_response) is covered in Section 8 with state-specific extensions (snapshot_event_id, recent_tool_calls).

The spec is design-only; no production code lands in Phase 404. v14 Build Kernel is the canonical implementation site; v15 Build Core Commands is the canonical orchestration site. Phase 405 (Deviation Rules) and Phase 406 (Harness Architecture Rollup) are the canonical downstream consumers.

### Spec stability

This spec is canonical for the v41 milestone. Amendments to APG-01..APG-06 require a Phase 404 spec amendment (a new commit to this file with a `## v41.N Amendment` section appended, mirroring the EVENT-TAXONOMY.md amendment pattern). Implementations (v14 Build Kernel, v15 Build Core Commands) that need behavior not specified here MUST either propose an amendment OR document the deviation in their SUMMARY.md with explicit rationale and a forward pointer to a future amendment plan.

The intent: the spec is a stable contract for downstream phases. Implementation flexibility lives within the spec's stated boundaries (Claude's Discretion in 404-CONTEXT.md is reproduced inline at each decision point); behavior outside those boundaries flows through the amendment pipeline.

### Verification cross-check

The plan that authored this spec (`02-analysis-paralysis-guard-spec-PLAN.md`) carries a `<verify><automated>` block with grep assertions for every section heading, every regex corpus name, every Pydantic class name, every cross-reference target, and the negative assertion that no Teach-mode-subtree reference appears. The grep assertions are reproducible from this file's content; v14's spec-conformance test can rerun the same assertions as a regression check.
