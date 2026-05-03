---
phase: quick-2-audit-roadmap
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/REVIEW-ROADMAP.md
autonomous: true
requirements:
  - QUICK-2-AUDIT
user_setup: []

must_haves:
  truths:
    - "REVIEW-ROADMAP.md is written (OVERWRITE) at /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md without the prior file contents being read"
    - "Review covers all 10 locked review dimensions from CONTEXT.md, including the distinct Arc/Phase/Slice/Step vs GSD Milestone/Phase conflation check"
    - "All findings carry an explicit severity tag from the set [BLOCKER / MAJOR / MINOR / NIT]"
    - "Output contains the 7 required top-level sections in the order specified in CONTEXT.md"
    - "Findings are surgical and terse: quote offending text with file + line numbers; do not rewrite the roadmap"
    - "Domain confusion scan covers BOTH: (a) HERE (build env: Claude Code + GSD + .planning/ + git on main) vs THERE (product: state engine + opencode plugin + .state/) and (b) Arc/Phase/Slice/Step (product runtime vocab) vs GSD Milestone/Phase (repo planning vocab)"
    - "Arc/Phase/Slice/Step conflation findings are visible — either their own dedicated subsection or clearly marked rows in the domain-confusion table (writer's call, but NOT buried)"
    - "Parallel-safe claim for v1..v5 is cross-checked against each milestone's verbatim `**Depends on:**` line using the evidence from 2-RESEARCH.md §3"
    - "P0 pitfall ownership audit flags P0-14 (debug-log plaintext tokens) against v27's missing `P0 pitfalls owned:` line per 2-RESEARCH.md §1"
    - "Phase-count discrepancy (STATE.md claims 267; ROADMAP.md has 256 `#### Phase` headings per 2-RESEARCH.md §2/§7) is named in findings"
    - "REQ-ID coverage spot-check inspects 3-5 phases and reports any REQ-ID vs phase-content mismatch"
    - "Toolchain dependencies (Python 3.12+, pytest, uv, pygit2) are NOT flagged as HERE/THERE confusion (explicit exclusion from CONTEXT.md §specifics)"
  artifacts:
    - path: ".planning/REVIEW-ROADMAP.md"
      provides: "Skeptical pre-execution audit of ROADMAP.md with severity-tagged findings"
      contains_sections_in_order:
        - "1. Executive summary (5 bullets; healthy/blocker count)"
        - "2. Domain confusion findings (table with file, line, quoted text, why, suggested rewrite — includes BOTH HERE/THERE and Arc/Phase/Slice/Step-vs-Milestone/Phase)"
        - "3. Per-milestone findings (severity-tagged subsections; only milestones with issues)"
        - "4. Coverage audit (REQ-IDs -> suspicious phases; 3-5 phases spot-checked)"
        - "5. DAG audit (missing + excessive edges; parallel-safe recheck for v1..v5)"
        - "6. Verifier audit (verifiers that don't cover stated milestone goal)"
        - "7. Recommendations (prioritized list of rewrites)"
      min_lines: 120
  key_links:
    - from: "REVIEW-ROADMAP.md §2 (Domain confusion)"
      to: ".planning/ROADMAP.md"
      via: "quoted offending text with line numbers"
      pattern: "ROADMAP.md.*line.*[0-9]+"
    - from: "REVIEW-ROADMAP.md §2 (Domain confusion)"
      to: "./CLAUDE.md"
      via: "secondary domain-confusion scan per CONTEXT.md §decisions"
      pattern: "CLAUDE\\.md"
    - from: "REVIEW-ROADMAP.md §3 (Per-milestone findings)"
      to: ".planning/PROJECT.md cardinal rules"
      via: "findings cite cardinal rules when a milestone violates them"
      pattern: "PROJECT\\.md|cardinal rule"
    - from: "REVIEW-ROADMAP.md §4 (Coverage audit)"
      to: ".planning/REQUIREMENTS.md"
      via: "REQ-ID references for the spot-checked phases"
      pattern: "REQ-|[A-Z]+-[0-9]+"
    - from: "REVIEW-ROADMAP.md §3 + §6"
      to: ".planning/research/PITFALLS.md"
      via: "P0 pitfall ownership cross-check (see 2-RESEARCH.md §1)"
      pattern: "P0-[0-9]+"
    - from: "REVIEW-ROADMAP.md §5 (DAG audit)"
      to: ".planning/STATE.md"
      via: "parallel-safe claim cross-check (STATE.md lines 34-42) vs ROADMAP.md `**Depends on:**` lines"
      pattern: "STATE\\.md|parallel-safe|Depends on"
---

<objective>
Produce a skeptical, surgical pre-execution audit of `.planning/ROADMAP.md` as
`.planning/REVIEW-ROADMAP.md` (OVERWRITE; do not read the prior file).

Purpose: Catch domain confusion, coverage gaps, dependency mistakes, complexity-honesty
problems, and verifier holes BEFORE the first milestone kicks off — when fixes are cheapest.
This review is input to the kickoff gate, not a post-mortem.

Output: A single file at `/Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md` with the
7 mandated top-level sections in order, severity-tagged findings, and quoted evidence with
file:line references. No roadmap rewrites — flags only.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
# LOCKED user decisions — do NOT revisit
@.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-CONTEXT.md

# Pre-extracted raw evidence — the reviewer's ammunition
@.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md

# Sources the audit must inspect (read from disk during execution)
@.planning/ROADMAP.md
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/research/SUMMARY.md
@.planning/research/PITFALLS.md
@.planning/STATE.md
@CLAUDE.md

# Project convention — do not re-read prior quick-task outputs
# DO NOT read: .planning/REVIEW-ROADMAP.md (prior-pass contents must not pollute this pass)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Load source evidence (explicit skip of prior review)</name>
  <files>
    .planning/ROADMAP.md,
    .planning/PROJECT.md,
    .planning/REQUIREMENTS.md,
    .planning/research/SUMMARY.md,
    .planning/research/PITFALLS.md,
    .planning/STATE.md,
    CLAUDE.md,
    .planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-CONTEXT.md,
    .planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md
  </files>
  <action>
    CRITICAL FIRST STEP — do NOT read `.planning/REVIEW-ROADMAP.md`. The user explicitly
    wants an independent pass; loading the prior review would pollute this context.

    Use the `Read` tool (or `Grep` where the file exceeds token limits — ROADMAP.md is
    ~2660 lines and will exceed a single Read) to load:
      1. `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-CONTEXT.md` — locked decisions
      2. `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md` — the
         pre-extracted evidence (P0 ownership map, milestone roster with verbatim
         Depends-on lines, Arc/Slice/Step vocabulary survey with line numbers, phase-count
         discrepancy, REQ-ID totals). Lean on this; do not re-extract what RESEARCH already extracted.
      3. `.planning/PROJECT.md` — cardinal rules (ground truth for HERE/THERE boundary)
      4. `CLAUDE.md` — secondary domain-confusion scan target
      5. `.planning/ROADMAP.md` — primary audit target. For sections beyond what RESEARCH
         already quoted, use `Grep` with line-number output (-n) instead of full Read.
      6. `.planning/REQUIREMENTS.md` — for the coverage spot-check (§4); use Grep for
         specific REQ-IDs rather than full read.
      7. `.planning/research/PITFALLS.md` — confirm P0 roster only if 2-RESEARCH §1 is
         insufficient for a specific finding; otherwise trust 2-RESEARCH.
      8. `.planning/research/SUMMARY.md` and `.planning/STATE.md` — already extracted in
         2-RESEARCH; re-read only targeted sections if a finding requires fresh quotation.

    Explicitly SKIP: `.planning/REVIEW-ROADMAP.md` — do not open, do not read, do not grep.

    Build a mental index of the 10 review dimensions from 2-CONTEXT.md §decisions
    (Domain hygiene including Arc/Phase/Slice/Step vs Milestone/Phase; Goal clarity;
    Requirement coverage; Depends-on realism; Complexity honesty; P0 pitfall ownership;
    Observable success criteria; Parallelization recheck; Verifier-vs-goal alignment;
    Under/over-planning). Every review dimension must surface at least once in the output
    (with severity tag) OR be explicitly noted as "no findings" in the executive summary.

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md` contains the P0 ownership map (§1), milestone roster with verbatim Depends-on (§2), Arc/Slice/Step line-indexed survey (§4), and phase-count discrepancy (§2, §7). REUSE directly — do not re-grep.
        - Grep pattern for cross-checks: `grep -nE "\*\*Depends on:\*\*|\*\*Verifier:\*\*|\*\*P0 pitfalls owned:\*\*" .planning/ROADMAP.md`
        - Grep pattern for REQ-ID spot-check: `grep -nE "REQ-|[A-Z]+-[0-9]+" .planning/ROADMAP.md | head -50`
      </code_to_reuse>
      <docs_to_consult>
        N/A — this is a documentation-audit task; no external libraries.
      </docs_to_consult>
      <tests_to_write>
        N/A — no exported logic; output is a markdown artifact, verified by structural checks in Task 2 and Task 3.
      </tests_to_write>
    </quality_scan>
  </action>
  <verify>
    Source files above are loaded into working context. `.planning/REVIEW-ROADMAP.md` has
    NOT been opened — confirm by listing tool-call history: no Read/Grep call targets
    `REVIEW-ROADMAP.md`. The reviewer can cite at least 10 distinct ROADMAP.md line numbers
    from memory (drawn from 2-RESEARCH.md tables).
  </verify>
  <done>
    All nine source files listed in `<files>` loaded; prior REVIEW-ROADMAP.md NOT read;
    10 review dimensions indexed in the reviewer's working memory with at least one
    candidate finding per dimension (or an explicit "clean" note).
  </done>
</task>

<task type="auto">
  <name>Task 2: Write REVIEW-ROADMAP.md (7 sections, severity-tagged, OVERWRITE)</name>
  <files>.planning/REVIEW-ROADMAP.md</files>
  <action>
    Use the `Write` tool (OVERWRITE mode — do not read the existing file first) to create
    `/Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md` with the EXACT following
    top-level section order (headings verbatim, H1 for title, H2 per section):

      # REVIEW: ROADMAP.md — Pre-Execution Audit
      (brief preamble: date, reviewer stance "skeptical senior engineer", input scope,
       explicit note "prior REVIEW-ROADMAP.md not read", severity legend
       [BLOCKER / MAJOR / MINOR / NIT])

      ## 1. Executive Summary
      Exactly 5 bullets. Include a count line: "Findings: N blocker, M major, X minor, Y nit."
      First bullet = headline health call (healthy / concerning / blocker-present).
      One bullet reserved for domain-hygiene headline (HERE/THERE + Arc/Phase/Slice/Step
      vs Milestone/Phase). One bullet for DAG/parallelization. One bullet for coverage/P0
      pitfall ownership. One bullet for verifier-vs-goal alignment.

      ## 2. Domain Confusion Findings
      Markdown table with columns: | Severity | File | Line(s) | Quoted Text | Why It's Confused | Suggested Rewrite (sketch) |
      MUST cover BOTH dimensions:
        (a) HERE (build env: Claude Code + GSD + .planning/ + git on main) vs
            THERE (product: Python state engine + opencode plugin + two MCP servers
            + .state/ tree + events.sqlite — does not exist yet).
        (b) Arc/Phase/Slice/Step (product RUNTIME vocabulary — what state organizes for
            its users) vs GSD Milestone/Phase (repo PLANNING vocabulary — how we organize
            THIS repo's work).
      The Arc/Phase/Slice/Step-vs-Milestone/Phase findings must be visible — either as a
      clearly-labeled group of rows ("### 2a. Arc/Phase/Slice/Step vs Milestone/Phase")
      or as its own H3 subsection — writer's call, but NOT buried inside generic rows.
      Do NOT flag legitimate toolchain dependencies (Python 3.12+, pytest, uv, pygit2)
      as HERE/THERE confusion — those are build-time tools for building the THERE product,
      and CONTEXT.md §specifics explicitly excludes them.
      Secondary scan: include at least one row sourced from `CLAUDE.md` if any confusion
      is present there (or explicitly note "CLAUDE.md scan: clean").
      Use the Arc/Slice/Step line index in 2-RESEARCH.md §4 as the starting point —
      every flagged conflation must cite the ROADMAP.md line number.

      ## 3. Per-Milestone Findings
      H3 per milestone with issues (skip milestones with no findings). Each H3 is
      "### M-AX — <Title> [severity]". Body: bullet list of findings, each tagged with
      severity and quoting offending text with line numbers. Review dimensions to apply
      per milestone:
        - Goal clarity (is the `**Goal:**` line one testable sentence, or a run-on?)
        - Complexity honesty (milestone-level S/M/L/XL vs phase count + verifier breadth)
        - Verifier-vs-goal coverage (does the `**Verifier:**` line actually verify
          the `**Goal:**` line, or a proxy?)
        - Success-criteria observability (process checkboxes vs user-observable behaviors)
        - Under/over-planning (fluff phases that should collapse; thin XLs that need split)
      Cross-reference P0 ownership with 2-RESEARCH §1: flag P0-14 against v27's
      missing `**P0 pitfalls owned:**` line (or confirm it's present elsewhere).

      ## 4. Coverage Audit (REQ-ID ↔ Phase Content)
      Spot-check between 3 and 5 phases (writer's choice; choose phases most likely to
      reveal REQ-ID vs content drift — start with high-complexity phases in v14, v16,
      v20 since these are XL). For each:
        - Phase ID + line number
        - REQ-IDs claimed by the phase (from `**Requirements:**` line or equivalent)
        - A 1-line judgment: do the phase's goal + acceptance criteria actually satisfy
          those REQ-IDs? Severity-tag any mismatches.
      Include the REQUIREMENTS.md coverage-discrepancy surfaced in 2-RESEARCH §6
      (229 REQ-IDs vs stated "221/221 100% coverage" — 229 includes v2-deferred IDs;
      220 v1 is one short of 221) as a separate tagged bullet.

      ## 5. DAG Audit (Missing + Excessive Edges)
      - Parallelization recheck for v1..v5: quote each milestone's verbatim
        `**Depends on:**` line (from 2-RESEARCH §3) and judge whether the STATE.md
        "parallel-safe" claim holds. v3 declares soft-dep on v2; v5 declares hard
        dep on v1. Judge: is STATE.md's unconditional "All five have zero predecessors"
        phrasing accurate, overstated, or requires a footnote?
      - Missing edges: identify cases where a `**Depends on:**` line omits an edge that
        phase content implies (e.g., does v9 need v6 in addition to v7 for SSE?).
      - Excessive edges: v27's "most of v1..v24 (soft)" — is this vacuous sequencing
        that under-constrains nothing and over-scares readers? Severity-tag.
      - Phase-count discrepancy: STATE.md claims 267 phases, ROADMAP.md has 256
        `#### Phase` headings (per 2-RESEARCH §2, §7). Flag as MAJOR or MINOR per writer's
        judgment.

      ## 6. Verifier Audit
      For each milestone with a gap between `**Goal:**` and `**Verifier:**`, quote both
      lines with line numbers and describe what the verifier fails to cover. Use
      2-RESEARCH §2 "Verifier (abridged)" column as starting candidates. Specifically
      check: v11 (mode isolation — does `**Verifier:**` cover ALL 6 layers claimed in
      the goal?); v14 (Step FSM — does the 10-golden-fixture verifier cover the
      cross-tier regression it claims?); v20 (Four Modes + Selector — XL milestone,
      11 phases — does one `**Verifier:**` line suffice?).

      ## 7. Recommendations (Prioritized)
      Ordered list, BLOCKER first, descending severity. Each item: one sentence stating
      what to change + pointer to the finding (§section + severity). Do NOT provide full
      rewrites — point the reader at the fix, do not write it for them. Target 5-15 items.

    Style rules (enforced):
      - Surgical, terse, senior-engineer voice.
      - Every finding carries exactly one severity tag from [BLOCKER / MAJOR / MINOR / NIT].
      - Every finding quotes ROADMAP.md (or CLAUDE.md, PROJECT.md) text with a line number.
      - No roadmap rewrites. Flags and sketches only.
      - No prose fluff ("Overall the roadmap is comprehensive and well-structured..."
        is banned).

    <quality_scan>
      <code_to_reuse>
        - Known: `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md` §1 (P0 map), §2 (milestone roster), §3 (Depends-on verbatim), §4 (Arc/Slice/Step line index), §6 (REQ-ID totals), §7 (discrepancies). Every section 2–6 of the output pulls from this.
        - Grep for any fresh quote needed: `grep -nE "^\*\*(Goal|Verifier|Depends on|P0 pitfalls owned|Requirements):\*\*" .planning/ROADMAP.md`
      </code_to_reuse>
      <docs_to_consult>
        N/A — markdown authoring only.
      </docs_to_consult>
      <tests_to_write>
        N/A — artifact is a markdown review file; structural validation performed in Task 3.
      </tests_to_write>
    </quality_scan>
  </action>
  <verify>
    <automated>test -f /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md &amp;&amp; grep -c "^## " /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md | awk '{exit ($1 &gt;= 7 ? 0 : 1)}'</automated>
  </verify>
  <done>
    `.planning/REVIEW-ROADMAP.md` exists, opens with an H1 title + preamble + severity
    legend, contains all 7 H2 sections in the required order, contains severity-tagged
    findings in §§2-6, and §7 is a prioritized recommendations list.
  </done>
</task>

<task type="auto">
  <name>Task 3: Structural self-verification of the review</name>
  <files>.planning/REVIEW-ROADMAP.md</files>
  <action>
    Self-audit the just-written file. Do NOT re-open any prior REVIEW-ROADMAP.md — only
    read the file just written in Task 2. Run the following checks and, for any failure,
    edit in place (using `Edit`) and re-check:

      (a) Section order. Grep for `^## ` and confirm the 7 H2 headings appear in the
          exact CONTEXT.md-specified order. If not, reorder.
      (b) Severity tags present. Grep for `\[BLOCKER\]|\[MAJOR\]|\[MINOR\]|\[NIT\]` —
          count MUST be ≥ 1 for BLOCKER OR MAJOR (at least one substantive finding;
          a roadmap with zero substantive issues is improbable for a 267-phase plan).
          If zero major findings were surfaced, re-scan for obvious issues from
          2-RESEARCH (e.g., phase-count 256 vs 267 discrepancy; v27 missing P0-14
          ownership) and add them.
      (c) Arc/Phase/Slice/Step conflation finding visibility. Grep for "Arc.*Slice.*Step"
          AND "Milestone" within §2. Must co-occur in a single block (table row group or
          H3 subsection) so the distinction is obvious. If absent, add.
      (d) HERE/THERE finding visibility. Grep §2 for explicit mention of at least one of:
          ".state/", "events.sqlite", "opencode plugin", "state-build MCP", "state-teach MCP"
          paired with build-env indicators (".planning/", "GSD", "Claude Code"). Must appear
          in at least one table row or subsection.
          (NOTE: legitimate product-surface discussion that is correctly scoped is NOT a
          confusion finding — flag only ambiguity or swap.)
      (e) Line-number citations. Grep for `line [0-9]` or `:[0-9]+` — must have ≥ 10 line
          citations total across the file.
      (f) Parallel-safe recheck is present. Grep §5 for "v1" AND "v5" AND
          ("parallel" OR "Depends on"). Must co-occur.
      (g) P0 ownership is addressed. Grep for "P0-14" OR "P0 ownership" in §3 or §6.
          Must appear at least once.
      (h) Toolchain exclusion honored. Grep §2 for rows where "Python 3.12", "pytest",
          "uv ", or "pygit2" are flagged AS confusion — this must NOT happen. If found,
          remove those rows.
      (i) No prior-file pollution. Confirm no tool call in this session has read
          `.planning/REVIEW-ROADMAP.md` BEFORE Task 2's write (it is legitimate to read
          it AFTER writing for self-audit in Task 3).

    For each failure, make a minimal targeted edit and re-run the relevant grep. Do not
    rewrite whole sections.

    <quality_scan>
      <code_to_reuse>
        - Grep checklist above.
        - Known: `.planning/quick/2-audit-roadmap-md-for-domain-confusion-an/2-RESEARCH.md` §1 and §7 for fallback substantive findings if (b) fails.
      </code_to_reuse>
      <docs_to_consult>
        N/A.
      </docs_to_consult>
      <tests_to_write>
        N/A — this task IS the structural test.
      </tests_to_write>
    </quality_scan>
  </action>
  <verify>
    <automated>bash -c 'F=/Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md; test -f "$F" &amp;&amp; [ "$(grep -c "^## " "$F")" -ge 7 ] &amp;&amp; grep -qE "\[(BLOCKER|MAJOR|MINOR|NIT)\]" "$F" &amp;&amp; grep -qE "Arc.*Slice.*Step|Arc/Phase/Slice/Step" "$F" &amp;&amp; grep -qE "v1.*v5|v1..v5" "$F" &amp;&amp; [ "$(grep -cE "line [0-9]+|:[0-9]+" "$F")" -ge 10 ]'</automated>
  </verify>
  <done>
    All nine self-audit checks (a) through (i) pass. The file is severity-tagged,
    well-structured, cross-references the locked review dimensions, visibly surfaces
    the Arc/Phase/Slice/Step-vs-Milestone/Phase conflation finding, and has not been
    polluted by the prior REVIEW-ROADMAP.md.
  </done>
</task>

</tasks>

<verification>
Overall phase checks (run after all tasks complete):

1. File exists: `test -f /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
2. Seven H2 sections in correct order:
   `grep -n "^## " /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
   expected (in order): Executive Summary, Domain Confusion, Per-Milestone, Coverage
   Audit, DAG Audit, Verifier Audit, Recommendations.
3. Severity tags are used:
   `grep -cE "\[(BLOCKER|MAJOR|MINOR|NIT)\]" /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
   expected: ≥ 1 BLOCKER or MAJOR, plus any number of MINOR/NIT.
4. Arc/Phase/Slice/Step conflation is visibly addressed:
   `grep -n "Arc.*Slice.*Step\|Arc/Phase/Slice/Step" /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
5. Parallel-safe recheck is present in §5:
   `grep -n "v1" /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md | grep -i "parallel\|depends"`
6. P0 ownership audit is present:
   `grep -n "P0-14\|P0 pitfalls owned\|P0 ownership" /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
7. Line-number citations are dense:
   `grep -cE "line [0-9]+|:[0-9]+" /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
   expected: ≥ 10.
8. Toolchain items are NOT flagged as HERE/THERE confusion:
   `grep -nE "Python 3\.12|pytest|pygit2|uv " /Users/tmac/Projects/state/.planning/REVIEW-ROADMAP.md`
   if any hits appear inside §2 Domain Confusion, that is a failure.
</verification>

<success_criteria>
- REVIEW-ROADMAP.md written (OVERWRITE) with the 7 mandated sections in order.
- Every finding carries a severity tag from [BLOCKER / MAJOR / MINOR / NIT].
- Domain confusion section visibly covers BOTH HERE/THERE AND Arc/Phase/Slice/Step vs Milestone/Phase.
- Parallel-safe claim for v1..v5 is cross-checked against verbatim Depends-on lines.
- P0-14 ownership gap (v27) is either flagged or explicitly dismissed with evidence.
- Phase-count discrepancy (256 ROADMAP vs 267 STATE) is named.
- Between 3 and 5 phases are spot-checked for REQ-ID coverage.
- Prior `.planning/REVIEW-ROADMAP.md` was not read before Task 2's write.
- Findings are surgical — quote offending text with line numbers; no roadmap rewrites.
</success_criteria>

<output>
After completion, no SUMMARY.md is required for this quick task (per
`.planning/config.json` commit_docs=false and quick-task convention). The single
deliverable is `.planning/REVIEW-ROADMAP.md`.
</output>
