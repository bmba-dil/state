# Quick Task 2: Roadmap audit — Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Task Boundary

Re-audit `.planning/ROADMAP.md` (and CLAUDE.md for domain-confusion risk) from a skeptical
senior-engineer perspective. Produce a fresh `.planning/REVIEW-ROADMAP.md` that OVERWRITES
the existing file (existing file must not be read — user wants an independent pass).

The review must flag domain-confusion risk between:
- **Domain A (HERE):** the build environment — Claude Code + GSD + `.planning/` + git
  committing to `main` on this repo.
- **Domain B (THERE):** the `state` product — Python engine, opencode plugin, two MCP
  servers, `.state/` tree, `events.sqlite`. Does not exist yet.

Additional (new in this pass): flag any conflation where the product's planning vocabulary
(Arc/Phase/Slice/Step) is used as a synonym for or substitute for GSD's own planning
vocabulary (Milestone/Phase). Arc/Phase/Slice/Step describes ONLY what `state` builds for
its users at runtime — never how we organize this repo's work.

</domain>

<decisions>
## Implementation Decisions

### Output file
- Write to `.planning/REVIEW-ROADMAP.md` (OVERWRITE; do not read current contents).

### Scope of sources to read
- `.planning/PROJECT.md` (cardinal rules)
- `.planning/ROADMAP.md` (primary target)
- `.planning/REQUIREMENTS.md` (coverage spot-checks — 3–5 phases)
- `.planning/research/SUMMARY.md`
- `.planning/research/PITFALLS.md` (P0 ownership cross-check)
- `.planning/STATE.md` (parallelization + tier claims)
- `./CLAUDE.md` (secondary domain-confusion scan)
- DO NOT read the existing `.planning/REVIEW-ROADMAP.md`.

### Review dimensions (must all appear in output)
1. Domain hygiene (HERE/THERE + Arc/Phase/Slice/Step vs Milestone/Phase)
2. Goal clarity (one testable sentence)
3. Requirement coverage (REQ-IDs actually match phase content)
4. Depends-on realism (over- and under-serialization)
5. Complexity honesty (S/M/L/XL vs actual scope)
6. P0 pitfall ownership (each P0 named in owning phase text)
7. Success criteria are observable, not process checkboxes
8. Parallelization claim recheck (v1..v5 parallel-safe per STATE.md)
9. Verifier definition covers stated milestone goal
10. Under/over-planning (fluff phases or thin XLs)

### Output structure (sections, in order)
1. Executive summary (5 bullets; healthy/blocker count)
2. Domain confusion findings (table: file, line, quoted text, why, suggested rewrite)
3. Per-milestone findings (severity-tagged subsections; only for milestones with issues)
4. Coverage audit (REQ-IDs → suspicious phases)
5. DAG audit (missing + excessive edges)
6. Verifier audit (verifiers that don't cover stated goal)
7. Recommendations (prioritized list of rewrites)

### Style
- Surgical and terse. Quote offending text with line numbers where possible.
- Do NOT rewrite the roadmap. Flag only.
- Use severity tags [BLOCKER / MAJOR / MINOR / NIT].

### Claude's Discretion
- Exact number of phases spot-checked for coverage (minimum 3, up to 5 if signal warrants).
- Whether to include CLAUDE.md findings in section 2 (domain confusion) or as a separate
  short subsection — writer's call.
- Whether to treat Arc/Phase/Slice/Step conflation as its own dedicated section or
  integrate into section 2 — writer's call, but it MUST be visible and not buried.

</decisions>

<specifics>
## Specific Ideas

- Existing REVIEW-ROADMAP.md exists at `.planning/REVIEW-ROADMAP.md` — do not read; overwrite.
- Roadmap has 267 phases across 27 milestones per STATE.md.
- STATE.md claims v1..v5 are parallel-safe — verify against actual Depends-on edges.
- One genuine tool dependency category exists (Python 3.12+, pytest, uv, pygit2 for
  toolchain) — do not flag those as "HERE/THERE" confusion.

</specifics>

<canonical_refs>
## Canonical References

- `CLAUDE.md` — cardinal rule: mode isolation is physical; Arc→Phase→Slice→Step is the
  PRODUCT hierarchy; GSD milestones/phases is the BUILD hierarchy; one GSD milestone =
  one product Arc.
- `.planning/PROJECT.md` — ground truth for cardinal rules and mode boundaries.

</canonical_refs>
