# v49 Handoff: Teach Workflow Architecture & AOL Port Map

## Milestone Goal

Design the complete teach-mode workflow orchestration — how lesson→code→drills→verify works across the Kolb cycle, how teaching subagents are spawned and managed, how subjects are authored, how scaffolding-mentor and coding-partner workflows function, and how all AOL (Agent of Learning) capabilities map to state-native workflows. This is the teach-mode equivalent of v43.

## What This Milestone Must Produce

### 1. Full Teaching Cycle Per Concept

Design the complete lifecycle for a single Concept through the Kolb cycle:

```
CONCEPT INTRODUCED
  │
  ├─ PHASE 1: LESSON (Concrete Experience — CE)
  │   ├── Agent loads CONCEPT.md (lesson content)
  │   ├── Agent injects teaching mode prompt (per v47 mode selector)
  │   ├── Agent injects personality/style (per v47 style profile)
  │   ├── Agent presents concept: "Today we're learning about {concept}."
  │   ├── Agent demonstrates: shows code examples, walks through them
  │   ├── Learner observes, asks questions
  │   ├── Agent answers, clarifies
  │   ├── Event: state.concept.introduced
  │   └── Agent transitions: "Ready to reflect on what we just learned?"
  │
  ├─ PHASE 2: REFLECTION (Reflective Observation — RO)
  │   ├── Agent asks Socratic questions about the concept
  │   │   "What do you think happens when...?"
  │   │   "Why did the code behave that way?"
  │   │   "What's the key difference between X and Y?"
  │   ├── Learner reflects, answers (via opencode chat)
  │   ├── Agent probes deeper, checks understanding
  │   ├── Agent surface misconceptions (per v48)
  │   ├── If PRIMM mode: agent asks prediction questions
  │   │   "Before I run this, what do you think the output will be?"
  │   ├── Event: state.concept.observed
  │   └── Agent transitions: "Let's put this into practice."
  │
  ├─ PHASE 3: CODE (Abstract Conceptualization — AC)
  │   ├── Agent presents coding exercise from EXERCISES.md
  │   ├── Agent enters coding-partner mode (per v47)
  │   │   Watches silently, provides graduated hints
  │   │   Never writes code for learner
  │   │   Records observations to OBSERVATIONS.jsonl
  │   ├── Learner writes code
  │   ├── Agent reviews code (not adversarial — educational)
  │   │   "Your solution works! One thing to consider..."
  │   │   "This pattern you're using here is actually..."
  │   ├── If Constructivist mode: learner picks their own project
  │   ├── If Scaffolded mode: agent provides template, learner fills in
  │   ├── Event: state.concept.drilled (transitional)
  │   └── Agent transitions: "Let's see how well you've mastered this."
  │
  ├─ PHASE 4: DRILLS (Active Experimentation — AE)
  │   ├── Drill engine activates (per v48)
  │   │   Selects N drills from DRILLS.md
  │   │   Presents via opencode question tool
  │   │   Grades via Bayesian mastery formula
  │   │   Provides targeted feedback per drill
  │   ├── Events: state.drill.prepared → state.drill.submitted → state.drill.graded
  │   ├── If mastery >= threshold (0.80) → MASTERED
  │   ├── If mastery < threshold but improving → more drills
  │   ├── If mastery < threshold and NOT improving → back to PHASE 2 (RO)
  │   │   "Let's revisit the concept. I think there's something we missed."
  │   └── Event: state.concept.mastered
  │
  ├─ MASTERED
  │   ├── Mental model updated with mastery probability
  │   ├── Spaced repetition scheduler sets next_review (per v48)
  │   ├── Learning verifier produces VERIFY.md (per v48)
  │   └── Agent celebrates: "You've mastered {concept}! 🎉"
  │
  └─ REVIEW (triggered by scheduler)
      ├── Agent: "Time to review {concept}. Let's see what you remember."
      ├── Agent presents review drills (fewer, harder)
      ├── SM-2 algorithm updates interval and EF
      ├── If grade >= 3 (pass): interval extends
      ├── If grade < 3 (fail): re-enter Kolb cycle from CE
      └── Event: state.concept.reviewed
```

### 2. Teaching Subagent Architecture

Design what subagents are spawned during teaching and what they do:

**Background subagents (non-blocking — fire and forget):**

| Subagent | Trigger | Action | Output |
|----------|---------|--------|--------|
| `aol-observation-recorder` | After each Kolb stage interaction | Records observations, mistakes, confidence signals | OBSERVATIONS.jsonl |
| `aol-mental-modeler` | After each concept session | Updates mental model with mastery, style signals, misconceptions | MENTAL-MODEL.json |
| `aol-navigator` | During learner think-time | Pre-computes next concept, next teaching mode, next drill selection | next-steps.json |
| `aol-state-writer` | After concept completion | Batched write of all observation/mistake/confidence files | Multiple files |
| `aol-learning-verifier` | After concept mastery | Generates VERIFY.md with learning evidence | VERIFY.md |

**Interactive subagents (blocking — learner-facing):**

| Subagent | Trigger | Action |
|----------|---------|--------|
| `aol-concept-teacher` | Concept start | Runs full Kolb cycle (4 phases) |
| `aol-coding-partner` | Code exercises (AC phase) | Watches learner code, provides hints |
| `aol-scaffolding-mentor` | Project skeleton creation | Guides file-by-file project creation |
| `aol-drill-mentor` | Drill sessions (AE phase) | Runs muscle-memory drill sessions |
| `aol-code-reviewer` | After code exercises | Educational code review (not adversarial) |

**Key architectural boundary (from AOL design):**
- Skills = interactive work (multi-turn dialogue with learner)
- Subagents = batch/background work (state recording, planning, verification)
- The teaching agent is the skill. The recording/planning agents are subagents spawned in the background.

### 3. Subject Authoring Workflow

Design how subjects get created (4-gate workflow from v24):

```
GATE 1: INTERVIEW
  ├── Agent interviews subject-matter expert (or learner)
  │   "What do you want to learn? What do you already know?"
  │   "What's the end goal? What project would prove mastery?"
  ├── Agent captures: subject scope, prerequisites, learning goals
  └── → INTERVIEW.md (raw interview notes)

GATE 2: CONCEPT GRAPH
  ├── Agent analyzes INTERVIEW.md
  ├── Agent proposes concept graph: modules → concepts → prerequisite DAG
  ├── Learner reviews, adjusts: "Actually, I already know X. Add Y."
  └── → CONCEPT-GRAPH.md (module list, concept list, prerequisites)

GATE 3: DRAFT
  ├── Agent generates full content for each concept:
  │   CONCEPT.md (lesson, examples, exercises)
  │   DRILLS.md (drill bank)
  │   EXERCISES.md (coding exercises)
  ├── Agent generates MODULE.md and SUBJECT.md
  └── → Draft artifacts under .state/teach/subjects/{subject-id}/

GATE 4: PROMOTE
  ├── Agent runs validation: all concepts have drills, all drills have answers
  ├── Agent runs dry-run: teach a concept to verify flow works
  ├── Learner approves: "This looks right. Ship it."
  └── → Subject promoted from draft to published
```

### 4. Scaffolding Mentor Workflow

Design the scaffolding-mentor interaction (from v22):

**Project skeleton creation:**
```
1. Learner has PROJECT-PLAN.md (their project plan)
2. Agent reads PROJECT-PLAN.md → generates internal scaffold blueprint
3. Blueprint: ordered list of files to create, with dependencies
4. Agent guides learner through each file:
   ├── "Let's start with the project structure. Create src/ and tests/."
   ├── "Now create src/main.py. What should it contain?"
   ├── [Learner creates file]
   ├── Agent observes: "Good. Now let's add the database module."
   └── [Repeat for all files in blueprint]
5. Agent records observations for every file creation
6. Progress tracked in TUI sidebar (per v23)
7. Across context resets: blueprint state survives via event store

HARD CONSTRAINTS:
- Agent NEVER takes the keyboard (never writes files)
- Agent NEVER writes code for the learner
- Agent only provides guidance: what to create, what to consider, what to avoid
- Learner creates every file, writes every line
```

### 5. Coding Partner Workflow

Design the coding-partner interaction (from v22):

**Code exercise flow:**
```
1. Agent presents exercise: "Write a function that {spec}."
2. Agent enters observation mode:
   ├── Watches learner's code (via Read tool on learner's files)
   ├── Detects: syntax errors, logical errors, style issues
   ├── Detects: learner is stuck (inactivity, repeated errors)
   └── Records all observations
3. Agent provides graduated hints (per v47 hint escalation):
   ├── Level 0: "What approach are you thinking of?"
   ├── Level 1: "Think about how {concept} applies here."
   ├── Level 2: "You might want to use {technique}."
   ├── Level 3: "Here's the pattern: {template}."
   └── Level 4: "Here's the explanation: {solution}." → concept enters REVIEW
4. Agent reviews completed code:
   ├── "Your solution works! Here's what's great: {strengths}."
   ├── "One thing to consider: {improvement}."
   └── "Compare with this alternative approach: {alternative}."

HARD CONSTRAINTS:
- Agent NEVER writes code for the learner
- Agent NEVER fixes learner's code
- Agent NEVER takes the keyboard
- All fixes/changes are made by the learner
```

### 6. AOL Port Map

Catalog all AOL capabilities and map them to state-native equivalents:

**Teaching workflows:**
| AOL Capability | State Equivalent | Design Decision |
|---------------|-----------------|-----------------|
| concept-teacher (Kolb cycle) | `teach-concept` command → KolbMachine FSM | Port (adapt) — event-sourced state tracking replaces AOL's markdown tracking |
| coding-partner | `code-with-me` mode (AC phase) | Port (adapt) — hint protocol and observation recording are event-sourced |
| scaffolding-mentor | `scaffold-project` command | Port (adapt) — blueprint tracking via event store |
| drill-mentor | `drill` command (AE phase) | Redesign — Bayesian formula replaces heuristic grading |
| code-review (teaching) | `review-my-code` command | Port (adapt) — educational, not adversarial |
| subject-authoring | `new-subject` → 4-gate workflow | Port (adapt) |

**Background agents:**
| AOL Agent | State Equivalent | Design Decision |
|-----------|-----------------|-----------------|
| observation-recorder | `aol-observation-recorder` subagent | Port — batched writes to OBSERVATIONS.jsonl |
| mental-modeler | `aol-mental-modeler` subagent | Port — writes MENTAL-MODEL.json projection |
| navigator | `aol-navigator` subagent | Port — writes next-steps.json |
| state-writer | `aol-state-writer` subagent | Port — consolidates all file I/O |
| learning-verifier | `aol-learning-verifier` subagent | Port — produces VERIFY.md |
| curriculum-planner | `aol-curriculum-planner` subagent | Port — plans across modules |

**Teaching modes:**
| AOL Mode | State Equivalent | Design Decision |
|----------|-----------------|-----------------|
| PRIMM | `mode: primm` | Port — predict→run→investigate→modify→make |
| Scaffolded | `mode: scaffolded` | Port — graduated hint removal |
| Socratic | `mode: socratic` | Port — question-driven discovery |
| Constructivist | `mode: constructivist` | Port — learner-driven projects |

**Personalities:**
| AOL Personality | State Equivalent | Design Decision |
|----------------|-----------------|-----------------|
| 7 personality definitions | `personalities/*.json` registry | Port verbatim — but add style profile inference |

**Commands:**
| AOL Command | State Equivalent | Design Decision |
|-------------|-----------------|-----------------|
| `teach-concept` | `/state:teach:teach <concept>` | Port |
| `code-with-me` | `/state:teach:code <concept>` | Port |
| `scaffold-project` | `/state:teach:scaffold <subject>` | Port |
| `drill` | `/state:teach:drill <concept>` | Port |
| `review-my-code` | `/state:teach:review <path>` | Port |
| `new-subject` | `/state:teach:new-subject` | Port |
| `progress` | `/state:teach:progress` | Redesign — from projector, not AOL's manual tracking |
| `resume` | `/state:teach:resume <concept>` | Redesign — from event store |

## Success Criteria

1. The full lesson→code→drills→verify cycle is specified for a Concept through all 4 Kolb stages.
2. Teaching subagent architecture is specified with background vs interactive agents.
3. Subject authoring workflow is specified across all 4 gates.
4. Scaffolding mentor workflow is specified with hard constraints and blueprint tracking.
5. Coding partner workflow is specified with graduated hints and hard constraints.
6. All AOL capabilities are mapped to state-native equivalents with design rationale.

## Research Inputs

**Primary reference — AOL workflows:**
- `~/.claude/agent-of-learning/` — entire AOL directory
- `~/.claude/skills/aol-concept-teacher/SKILL.md` — full teaching workflow, Kolb stages
- `~/.claude/skills/aol-coding-partner/SKILL.md` — coding partner interaction model
- `~/.claude/skills/aol-scaffolding-mentor/SKILL.md` — scaffolding mentor workflow
- `~/.claude/skills/aol-drill-mentor/SKILL.md` — drill session workflow
- `~/.claude/skills/aol-code-review/SKILL.md` — teaching-mode code review
- `~/.claude/skills/aol-curriculum-planner/SKILL.md` — curriculum planning
- `~/.claude/skills/aol-learning-verifier/SKILL.md` — learning verification

**AOL subagent definitions:**
- `~/.claude/agents/aol-observation-recorder.md`
- `~/.claude/agents/aol-mental-modeler.md`
- `~/.claude/agents/aol-navigator.md`
- `~/.claude/agents/aol-state-writer.md`
- `~/.claude/agents/aol-learning-verifier.md`
- `~/.claude/agents/aol-curriculum-planner.md`

**State shipped code:**
- `src/state_teach/kernel.py` — KolbMachine skeleton
- `src/state_teach/concepts.py` — empty placeholder
- `src/state_teach/drill.py` — empty placeholder
- `src/state_teach/mental_model.py` — empty placeholder
- `src/state_teach/personalities/` — empty placeholder
- `packages/opencode-plugin/src/tui/teach-concept.ts` — existing teach sidebar

**Build mode reference:**
- v43-handoff.md — workflow orchestration patterns (session management, subagent spawning, error recovery)

## Key Questions for Discuss-Phase

1. **AOL port fidelity**: Should AOL workflows be ported verbatim (preserving the exact interaction patterns) or redesigned (improving them with state's event-sourced infrastructure)? The trade-off: familiarity vs improvement.

2. **Background subagent timing**: Should background subagents (observation-recorder, mental-modeler) run during teaching or after? During = real-time state updates but potential latency. After = clean but state may be stale.

3. **Coding partner code isolation**: When the learner writes code in the AC phase, where does that code live? In the learner's project? In a sandbox? The learner's project is real code — teaching exercises shouldn't pollute it.

4. **Subject authoring vs subject importing**: Should state support importing pre-authored subjects (from a community registry)? Or is all subject authoring done locally by the learner?

5. **Scaffolding and coding partner overlap**: Both involve the learner writing code. When does scaffolding-mentor end and coding-partner begin? Is scaffolding just the project skeleton, and coding partner covers everything after?

## Dependencies

- **v46 (Teach Structure)** — MUST be complete. Workflows operate on the hierarchy.
- **v47 (Teach Harness)** — MUST be complete. Workflows use mode selection, style injection, frustration detection.
- **v48 (Teach Quality)** — MUST be complete. Workflows use drill engine, learning verifier, misconception detection.
- **v43 (Build Workflow)** — useful for patterns (workflow design, subagent management).

## Scope Boundaries

**In scope:**
- Full teaching cycle per concept (4 Kolb stages)
- Teaching subagent architecture
- Subject authoring workflow (4 gates)
- Scaffolding mentor workflow
- Coding partner workflow
- Complete AOL port map

**Out of scope:**
- Implementation of any workflow
- Build mode workflows
- Rust DB integration
