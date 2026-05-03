# v4 — Worktree + Snapshot Service Requirements

**Source:** Extracted from monolithic `.planning/_archived/REQUIREMENTS.md`.

---

### Kernel: Worktree + Snapshot Service (A4)

- [ ] **WRK-01**: Per-Slice worktree — one worktree for all Steps within a Slice, sequential within, concurrent across Slices
- [ ] **WRK-02**: Opencode worktree service preferred when available; pygit2 fallback otherwise
- [ ] **WRK-03**: Transactional bootstrap: branch + worktree dir + `.state/` inheritance atomic; rollback on failure
- [ ] **WRK-04**: Orphan-worktree GC (nightly daemon task) — detects `.git/worktrees/*/locked`, stale branch names, full removal
- [ ] **WRK-05**: Branch naming: `slice/<arc>/<phase>/<slice-id>` deterministic
- [ ] **WRK-06**: Step snapshots via opencode `Snapshot.track` before execute, `Snapshot.revert` on verify failure
- [ ] **WRK-07**: Slice snapshots on boundary (all Steps complete or aborted) for rollup revert
- [ ] **WRK-08**: Prefix-only revert: reverting Step N within a Slice reverts N..last without touching earlier Steps
- [ ] **WRK-09**: `state snapshot list|diff|revert` CLI
