# v4 — Worktree + Snapshot Service

**Source:** Extracted from monolithic `.planning/_archived/ROADMAP.md` (2026-04-22 migration).
**Phase range:** 032–040 (9 phases)

---

## Phases

#### Phase 032 — Worktree abstraction interface (`state_core.worktree.WorktreeService`)
**Goal:** `create/list/remove/reset` methods, host-agnostic signature.
**Depends on:** 001
**Requirements:** (foundational)
**Parallelizable:** yes

#### Phase 033 — opencode-HTTP worktree adapter
**Goal:** `POST /worktree` via opencode HTTP client; subscribe to `worktree.ready`/`worktree.failed` bus events.
**Depends on:** 032
**Requirements:** WRK-02
**Parallelizable:** yes with 034

#### Phase 034 — pygit2 fallback adapter
**Goal:** `Repository.add_worktree()`, `list_worktrees()`, `Worktree.prune()`; out-of-tree `state-snapshots` ref namespace for snapshots.
**Depends on:** 032
**Requirements:** WRK-02
**Parallelizable:** yes with 033

#### Phase 035 — Deterministic branch + worktree naming (`slice/<arc-id>/<product-phase-id>/<slice-id>`)
**Goal:** Name generator with collision detection.
**Depends on:** 032
**Requirements:** WRK-05
**Parallelizable:** yes

#### Phase 036 — Transactional bootstrap (`.state/` inheritance + rollback)
**Goal:** Branch + worktree dir + `.state/` link atomic; rollback via compensation if any step fails.
**Depends on:** 033, 034
**Requirements:** WRK-03, WRK-01
**Parallelizable:** no

#### Phase 037 — Orphan worktree GC (P0-10 defence)
**Goal:** Nightly daemon task scans `.git/worktrees/*/locked`, stale branch names, removes; never swallows errors.
**Depends on:** 033, 034
**Requirements:** WRK-04
**Parallelizable:** yes with 038, P8
**P0 pitfall:** P0-10

#### Phase 038 — Step snapshot (pre-execute + pre-verify via opencode `Snapshot.track`)
**Goal:** `snapshot(tier="step", reason="pre_execute"|"pre_verify")` with content-addressed hash stored in events + STEP.md frontmatter.
**Depends on:** 036
**Requirements:** WRK-06
**Parallelizable:** yes with 037, P8

#### Phase 039 — Slice snapshot (boundary hash + ship-time reference)
**Goal:** On Slice shipped, store slice-tier hash in events + SLICE.md.
**Depends on:** 038
**Requirements:** WRK-07
**Parallelizable:** yes with 037

#### Phase 040 — Prefix-only revert + CLI `state snapshot list|diff|revert`
**Goal:** Revert Step N within a Slice reverts N..last chronologically; Typer CLI.
**Depends on:** 038, 039
**Requirements:** WRK-08, WRK-09
**Parallelizable:** no (integration)

---

