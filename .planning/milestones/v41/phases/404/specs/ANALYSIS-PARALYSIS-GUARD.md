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
