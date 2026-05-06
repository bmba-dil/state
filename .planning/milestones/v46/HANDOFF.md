# v46 Handoff: Teach Mode Structure & Artifact Architecture

## Milestone Goal

Fully architect the teach-mode product hierarchy (Subject → Concept → Kolb Cycle → Drill), its on-disk file structure, its artifact catalog, its mental-model schema, its cross-referencing rules, and its state machine definitions. This is the teach-mode equivalent of v40 — the backbone of the entire Teach mode.

## Teach Mode vs Build Mode — Structural Differences

Build mode has a 4-tier project hierarchy (Arc → Phase → Slice → Step). Teach mode has a fundamentally different structure because **learning is not project delivery**:

| Build Tier | Teach Equivalent | Key Difference |
|------------|-----------------|----------------|
| Arc | **Subject** (e.g., "Python 3.12") | A Subject is a domain of knowledge, not a feature block |
| Phase | **Learning Module** (e.g., "Async/Await") | A Module is a coherent unit of concepts within a subject |
| Slice | (No Slice equivalent) | No worktrees in teaching — no code to ship |
| Step | **Concept** (e.g., "Task Groups") | A Concept is the unit of the Kolb learning cycle |

But there's also a cross-cutting dimension: **teaching modes** (PRIMM, Scaffolded, Socratic, Constructivist) that apply per-concept based on mastery level.

## What This Milestone Must Produce

### 1. Tier Definitions

**Subject:**
- Definition: A domain of knowledge the learner wants to master (e.g., "Python 3.12", "TypeScript", "System Design")
- Lifecycle: `created → authoring → published → archived`
- Artifacts: SUBJECT.md (subject definition, module list, prerequisites, learning path)
- Frontmatter: id, title, description, modules[], status, prerequisites[], author, version
- How subjects get created: `/state:teach:new-subject` or AOL subject authoring workflow

**Learning Module:**
- Definition: A coherent unit of concepts within a subject (e.g., "Async/Await", "Generics", "React Hooks")
- Lifecycle: `planned → in_progress → complete`
- Artifacts: MODULE.md (module definition, concept list, learning objectives, prerequisites)
- Frontmatter: id, subject_id, title, description, concepts[], status, prerequisites, learning_objectives
- How modules relate: modules can have prerequisites (must complete Module A before Module B)

**Concept:**
- Definition: The smallest unit of learning — one thing to understand and practice. Runs the full Kolb cycle.
- Lifecycle: `introduced → observing → abstracting → experimenting → mastered | reviewed`
- Artifacts: CONCEPT.md (concept definition, lesson content, code examples, drill templates)
- Frontmatter: id, module_id, title, description, teaching_mode, mastery_threshold, drill_count, depends_on[], kolb_stages[]
- The `depends_on[]` specifies prerequisite concepts within the same module
- `teaching_mode` is selected by the mode selector (v20): PRIMM, Scaffolded, Socratic, or Constructivist
- `mastery_threshold` is the mastery probability (0-100) at which the concept is considered "mastered"

**Drill:**
- Definition: A single practice exercise within a Concept's Active Experimentation phase
- Lifecycle: `prepared → presented → submitted → graded`
- Artifacts: DRILL.md (per-concept drill bank), individual drill entries within
- Frontmatter: concept_id, question, answer_pattern, difficulty, time_limit, hints[]

### 2. Kolb Cycle State Machine

Design the Kolb experiential learning cycle FSM for a Concept:

```
INTRODUCED (Concrete Experience — CE)
  │  Agent introduces the concept, shows examples, demonstrates
  │  Event: state.concept.introduced
  │
  ├─→ OBSERVING (Reflective Observation — RO)
  │     Learner reflects, asks questions via opencode question tool
  │     Agent guides reflection, clarifies misconceptions
  │     Event: state.concept.observed
  │
  ├─→ ABSTRACTING (Abstract Conceptualization — AC)
  │     Agent guides the learner through coding exercises
  │     Learner writes code, agent reviews (AOL coding-partner mode)
  │     Event: state.concept.drilled (transitional)
  │
  ├─→ EXPERIMENTING (Active Experimentation — AE)
  │     Drill engine generates practice exercises
  │     Learner completes drills, engine grades via Bayesian mastery
  │     Event: state.drill.prepared → state.drill.submitted → state.drill.graded
  │
  ├─→ MASTERED
  │     Mastery probability >= threshold
  │     Event: state.concept.mastered
  │
  └─→ REVIEW
        Scheduled review per spaced-repetition algorithm
        Mastery probability decays → re-enter Kolb cycle
        Event: state.concept.reviewed
```

For each stage, specify:
- What the agent does (its role, prompt, constraints)
- What the learner does (input expected, tools available)
- What events are emitted
- How the teaching mode (PRIMM/Scaffolded/Socratic/Constructivist) modifies the stage
- How the personality/style (v21) modifies the agent's behavior

### 3. On-Disk File Structure

Design the complete `.state/teach/` directory tree:

```
.state/teach/
├── subjects/
│   └── {subject-id}/
│       ├── SUBJECT.md         ← subject definition + module list
│       ├── STATE.md           ← subject-level state projection
│       └── modules/
│           └── {module-id}/
│               ├── MODULE.md  ← module definition + concept list
│               ├── STATE.md   ← module-level state projection
│               └── concepts/
│                   └── {concept-id}/
│                       ├── CONCEPT.md          ← concept definition
│                       ├── LESSON.md           ← lesson content (CE phase)
│                       ├── EXERCISES.md        ← coding exercises (AC phase)
│                       ├── DRILLS.md           ← drill bank (AE phase)
│                       ├── OBSERVATIONS.jsonl  ← teaching observations
│                       ├── MISTAKES.jsonl      ← mistake log
│                       ├── MASTERY.md          ← mastery projection
│                       └── VERIFY.md           ← learning verification
├── mental-models/
│   └── {learner-id}/
│       ├── MENTAL-MODEL.json   ← rebuildable projection from OBSERVATIONS
│       ├── STYLE-PROFILE.json  ← teaching style preferences
│       └── HISTORY.json        ← learning history timeline
├── personalities/
│   ├── {personality-id}.json   ← AOL personality definitions
│   └── registry.json           ← personality registry
├── templates/
│   ├── subject-template.md
│   ├── module-template.md
│   ├── concept-template.md
│   └── drill-template.md
├── skills/
│   └── (teach-mode opencode skills — auto-discovered)
└── config/
    └── teach-config.toml       ← teach-mode configuration
```

### 4. Artifact Catalog

Formalize teach-mode artifacts with schemas:

| Artifact | Tier | Creator | Schema | Key Fields |
|----------|------|---------|--------|------------|
| SUBJECT.md | Subject | new-subject command | TBD | id, title, description, modules[], prerequisites, author |
| MODULE.md | Module | new-module command | TBD | id, subject_id, title, concepts[], learning_objectives |
| CONCEPT.md | Concept | concept-next command | TBD | id, module_id, teaching_mode, mastery_threshold, depends_on[] |
| LESSON.md | Concept | concept-teach (CE phase) | TBD | Lesson content, examples, demonstrations |
| EXERCISES.md | Concept | concept-teach (AC phase) | TBD | Coding exercises with expected solutions |
| DRILLS.md | Concept | drill-prepare | TBD | Drill bank with questions, answers, hints |
| OBSERVATIONS.jsonl | Concept | observation-recorder agent | JSONL event schema | Timestamp, observation_type, concept_id, details |
| MISTAKES.jsonl | Concept | coding-partner skill | JSONL | Mistake pattern, concept_id, timestamp, correction |
| MASTERY.md | Concept | drill engine projection | Projection | Mastery probability, last_review, next_review, history |
| VERIFY.md | Concept | learning-verifier agent | TBD | Learning evidence, pass/fail, recommendations |
| MENTAL-MODEL.json | Learner | mental-modeler agent | Projection | Rebuildable from OBSERVATIONS.jsonl |
| STYLE-PROFILE.json | Learner | style inference engine | TBD | 7-dimension style vector |

### 5. Mental Model Schema

Design the mental model projection that represents the learner's state:

```json
{
  "learner_id": "...",
  "subjects": {
    "python-3.12": {
      "mastery_overall": 0.72,
      "modules": {
        "async-await": {
          "mastery": 0.85,
          "concepts": {
            "task-groups": {
              "mastery": 0.91,
              "stage": "mastered",
              "last_review": "2026-05-01T00:00:00Z",
              "next_review": "2026-05-15T00:00:00Z",
              "mistakes": [
                {"pattern": "forgot await", "count": 2, "last_seen": "..."},
                {"pattern": "wrong exception handler", "count": 1, "last_seen": "..."}
              ],
              "learning_style_signals": {
                "prefers_examples": 0.8,
                "needs_repetition": 0.3,
                "grasps_quickly": 0.7
              }
            }
          }
        }
      }
    }
  },
  "learning_style": {
    "primary": "visual_experiential",
    "signals": {...}
  },
  "frustration": {
    "current_level": "low",
    "recent_events": [...],
    "threshold_breached": false
  }
}
```

Design the full pydantic model for this. It must be:
- Rebuildable from OBSERVATIONS.jsonl (event-sourced, not agent-maintained)
- Queryable by the mode selector (what mode to use for the next concept?)
- Queryable by the drill engine (what mastery level? what mistakes to drill?)
- Queryable by the learning verifier (what evidence of learning exists?)

### 6. Cross-Referencing Rules

- SUBJECT.md references modules[] by ID
- MODULE.md references concepts[] by ID, subject_id, prerequisite modules
- CONCEPT.md references depends_on[] (prerequisite concepts within same module), module_id
- DRILLS.md references concept_id
- OBSERVATIONS.jsonl entries reference concept_id, module_id, subject_id
- MENTAL-MODEL.json is a projection — it references but is not referenced

## Success Criteria

1. All teach-mode tiers (Subject, Module, Concept, Drill) are fully defined with lifecycles, artifacts, and schemas.
2. The Kolb cycle FSM is specified with all stages, events, transitions, and guard conditions.
3. The `.state/teach/` directory tree is fully specified.
4. The artifact catalog lists every teach-mode artifact with schema requirements.
5. The mental model schema supports rebuild from events, query by mode selector, drill engine, and learning verifier.
6. Cross-referencing rules connect all teach-mode artifacts.

## Research Inputs

**Primary reference — AOL (Agent of Learning):**
- `~/.claude/agent-of-learning/` — all AOL workflows, personalities, learner schemas
  - Especially: concept-teacher workflow, coding-partner workflow, scaffolding-mentor workflow
  - Especially: personality definitions, Kolb cycle implementation, drill engine
  - Especially: MENTAL-MODEL.json schema, OBSERVATIONS.jsonl format
- `~/.claude/skills/aol-concept-teacher/` — concept teaching skill
- `~/.claude/skills/aol-coding-partner/` — coding partner skill
- `~/.claude/skills/aol-scaffolding-mentor/` — scaffolding mentor skill
- `~/.claude/skills/aol-drill-mentor/` — drill mentor skill
- `~/.claude/skills/aol-code-review/` — teaching-mode code review

**State shipped code (teach mode stubs):**
- `src/state_teach/kernel.py` — KolbMachine skeleton (15 lines)
- `src/state_teach/concepts.py` — empty placeholder
- `src/state_teach/drill.py` — empty placeholder
- `src/state_teach/mental_model.py` — empty placeholder
- `src/state_teach/personalities/` — empty placeholder
- `src/state_core/schema.py` — concept event types (`state.concept.*`, `state.drill.*`)

**State planning:**
- `.planning/milestones/v18/REQUIREMENTS.md` — TCH-01..08
- `.planning/milestones/v19/REQUIREMENTS.md` — DRL-01..06
- `.planning/milestones/v20/REQUIREMENTS.md` — MODE-P-01, MODE-S-01, etc.
- `.planning/research/ARCHITECTURE.md` — §9 (teach mode kernel)

**Build mode reference (patterns to reuse):**
- v40-handoff.md — hierarchy patterns, artifact catalog patterns
- `src/state_core/projector.py` — projection engine pattern (teach mode needs its own projection for mental model)

## Key Questions for Discuss-Phase

1. **Module vs Phase naming**: Should the teach-mode hierarchy use "Module" or keep "Phase" for consistency with build mode? Using the same name for different concepts may cause confusion, but different names may cause fragmentation.

2. **Worktree concept in teach mode**: Teach mode doesn't need git worktrees (no code to ship). But coding exercises in the AC phase DO involve code. Should those have isolated workspaces?

3. **Multiple learners**: Does the mental model support multiple learners? (A teacher using state to teach multiple students) Or is it single-learner only?

4. **Subject authoring**: Who creates subjects? The learner? A subject author? If the learner creates their own subject, the authoring workflow is a prerequisite to learning. If subjects are pre-authored, the authoring workflow is separate.

5. **Kolb cycle vs teaching modes**: How do the four teaching modes (PRIMM, Scaffolded, Socratic, Constructivist) compose with the Kolb cycle? Does each mode express all four Kolb stages differently? Or do some modes skip stages?

6. **Spaced repetition algorithm**: What algorithm governs review scheduling? SM-2 (proven, simple)? Leitner (flashcard model)? Custom Bayesian model?

## Dependencies

- **v40 (Build Hierarchy)** — useful for patterns, not blocking
- **v11 (Mode Enforcement)** — shipped. Teach mode structure is isolated from build mode.

## Scope Boundaries

**In scope:**
- Subject/Module/Concept/Drill tier definitions
- Kolb cycle FSM
- `.state/teach/` directory tree
- Teach-mode artifact catalog
- Mental model schema
- Cross-referencing rules

**Out of scope:**
- Teaching harness design (v47)
- Learning verification pipeline (v48)
- AOL workflow porting (v49)
- Any implementation
