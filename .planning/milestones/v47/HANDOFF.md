# v47 Handoff: Teach Mode Harness & Teaching Control

## Milestone Goal

Design the teach-mode harness — how the daemon/MCP/plugin manages teaching sessions, selects teaching modes, injects personality/style, controls pacing, detects frustration, and manages the learner's context. This is the teach-mode equivalent of v41, adapted for the fundamentally different interaction pattern of teaching vs building.

## Critical Difference from Build Mode

Build mode harness: controls an agent that writes code. The agent is the actor.
Teach mode harness: controls an agent that teaches a human. The human is the actor (writing code, answering drills), and the agent guides. This fundamentally changes the control model:

- Context management: the learner's mental state matters as much as the agent's context budget
- Paralysis detection: the learner can get stuck, not just the agent
- Deviation handling: the learner can go off-track, and the agent must guide back gently
- Checkpoints: every interaction is potentially a checkpoint (learner asks a question, makes a mistake, needs a hint)

## What This Milestone Must Produce

### 1. Teaching Session Management

Design how a teaching session works:

**Session lifecycle:**
```
START → warm-up → concept_intro → guided_practice → independent_practice → reflection → END
```

**Session identity:**
- Session linked to learner ID (mental model)
- Session tracks: subject, module, current concept, Kolb stage, elapsed time
- Session records: observations, mistakes, accomplishments, confidence signals
- Session persists across context resets

**Session initialization:**
- On session start: harness loads learner's mental model (MENTAL-MODEL.json projection)
- Harness selects next concept (from module plan or navigator's next-steps.json)
- Harness selects teaching mode based on mastery level:
  - 0–30% mastery → PRIMM (highly structured, step-by-step)
  - 30–50% mastery → Scaffolded (gradual removal of supports)
  - 50–70% mastery → Socratic (question-driven, discovery-based)
  - 70%+ mastery → Constructivist (learner-driven projects)

**Session pacing:**
- Harness tracks time per Kolb stage
- If learner is spending too long on a stage → agent nudges ("Ready to move on?")
- If learner is breezing through → agent probes deeper ("Can you explain why that works?")
- Harness detects session fatigue (long session, declining performance) → suggests break

### 2. Teaching Mode Selection & Injection

Design how the harness selects and injects teaching modes:

**Mode selector algorithm:**
1. Read concept's mastery level from mental model
2. Read concept's declared `teaching_mode` (can be overridden by selector)
3. Read learner's style profile (7-dimension vector)
4. Read frustration level
5. Select mode:
   - If mastery < 30%: PRIMM (even if concept declares Scaffolded — safety override)
   - If mastery 30–50%: Concept's declared mode (or Scaffolded if undeclared)
   - If mastery 50–70%: Socratic (regardless of declaration — ready for discovery)
   - If mastery 70%+: Constructivist (regardless of declaration — ready to build)
   - If frustration > threshold: Step down one mode (Constructivist → Socratic → Scaffolded → PRIMM)

**Mode injection:**
- Harness writes the selected mode to the agent's system prompt via `chat.system.transform` hook
- Mode-specific prompt templates contain:
  - PRIMM: "You are a structured teacher. Follow the PRIMM model: Predict, Run, Investigate, Modify, Make. Do not skip steps. Do not give answers directly."
  - Scaffolded: "You are a supportive teacher. Provide graduated hints. Hint 1: general direction. Hint 2: specific technique. Hint 3: near-solution. Never write code for the learner."
  - Socratic: "You are a Socratic teacher. Ask questions that lead to discovery. Never state facts directly. Every answer should be a question that guides thinking."
  - Constructivist: "You are a project mentor. The learner drives. You provide resources, feedback, and guardrails. Only intervene when the learner is stuck or going off-track."

**Mode transition:**
- Harness detects when mode should change (mastery crossed threshold, frustration spike)
- Transition is soft: agent finishes current interaction, then switches mode for next interaction
- Learner is NOT notified of mode change (transparent) unless mode stepped down due to frustration

### 3. Personality & Style Injection

Design how the 7-dimension style profile controls agent behavior:

**Style dimensions (from v21):**
| Dimension | Range | Effect |
|-----------|-------|--------|
| Warmth | 0.0 (cold) – 1.0 (warm) | Agent tone: clinical ↔ encouraging |
| Directness | 0.0 (indirect) – 1.0 (direct) | Hint style: subtle ↔ explicit |
| Humor | 0.0 (serious) – 1.0 (playful) | Agent personality: formal ↔ casual |
| Formality | 0.0 (casual) – 1.0 (formal) | Language: slang ↔ academic |
| Patience | 0.0 (fast) – 1.0 (patient) | Pacing: pushy ↔ relaxed |
| Challenge | 0.0 (easy) – 1.0 (hard) | Difficulty: gentle ↔ rigorous |
| Explicitness | 0.0 (vague) – 1.0 (explicit) | Explanations: terse ↔ verbose |

**Style inference:**
- Harness observes learner interactions and adjusts style profile
- Signals: learner's response time, question frequency, frustration events, explicit feedback
- Profile updated in STYLE-PROFILE.json by the mental-modeler agent

**Style injection:**
- Harness converts style profile to system prompt modifiers
- Warmth=0.8: "Be encouraging and supportive. Celebrate progress." vs Warmth=0.2: "Be concise and professional."
- Patience=0.9: "Allow the learner time to think. Don't rush." vs Patience=0.3: "Keep the pace brisk. Move on when the concept is understood."
- The style profile is additive to the teaching mode prompt — they compose

### 4. Frustration Detection & Response

Design how the harness detects and responds to learner frustration:

**Frustration signals:**
- 3+ errors on the same concept within 5 minutes
- Learner types short/terse responses (length dropping)
- Learner uses frustration words ("stuck", "confused", "don't get it", "whatever")
- Learner stops responding (inactivity > N seconds)
- Learner asks to skip or change concept
- Drill grading shows declining performance

**Frustration levels:**
| Level | Signals | Response |
|-------|---------|----------|
| None | No signals | Normal teaching |
| Low | 1-2 signals | Agent adds encouragement, offers hint |
| Medium | 3+ signals, declining performance | Agent steps down teaching mode, reviews fundamentals |
| High | 5+ signals, inactivity, explicit frustration | Agent pauses teaching, suggests break, reflects on what's hard |
| Critical | Persistent high frustration | Agent recommends switching concepts, notifies user |

**Frustration event:** `state.concept.frustration_detected` with level, signals, and context.

### 5. Hint Escalation Protocol

Design the graduated hint system (used in Scaffolded mode but available to all modes):

**Hint levels:**
| Level | Name | Content | When to Use |
|-------|------|---------|-------------|
| 0 | No hint | "What do you think you should try?" | First attempt |
| 1 | Direction | "Think about how {concept} relates to {context}." | After one failed attempt |
| 2 | Technique | "You might want to use {specific_technique} here." | After two failed attempts |
| 3 | Template | "Here's the pattern: {code_template_with_blanks}. Fill in the blanks." | After three failed attempts |
| 4 | Solution | "Here's how it works: {explanation}." | After four failed attempts — concept needs reteaching |

**Escalation triggers:**
- Learner gives up ("I don't know", "show me")
- Learner makes the same mistake N times
- Learner's code produces the same error N times
- Timeout (learner hasn't attempted for > N seconds)

**Escalation guardrails:**
- Never jump directly from Level 0 to Level 4
- After Level 4: concept enters REVIEW state (re-enter Kolb cycle, not mastered)
- Hint levels are per-attempt, not per-concept — each new coding exercise resets to Level 0

### 6. Context Management for Teaching

Design how the harness manages context during teaching (different from build mode):

**Context components (injected at session start):**
- Current CONCEPT.md (lesson content, examples, exercises)
- Learner's mental model for this concept (prior mastery, mistake patterns)
- Teaching mode prompt (selected by mode selector)
- Style profile prompt (from STYLE-PROFILE.json)
- Current Kolb stage instructions
- Recent observations (last 3-5, for continuity)

**Context budget management:**
- Teaching sessions are usually shorter than build sessions → less context pressure
- But the learner's code exercises accumulate in context → manage this
- After each Kolb stage: compact the stage's conversation, keep summary and key observations
- On concept transition: clear full context, reinject new concept + mental model

**Compaction for teaching:**
- What survives: concept mastery state, recent observations, mistake patterns, current hint level
- What's discarded: full conversation history, code examples (re-injected from CONCEPT.md)
- What's summarized: learner's questions, agent's explanations, key teaching moments

### 7. Coding Partner Mode

Design how the harness manages the coding-partner interaction (learner writes code, agent watches):

**Interaction model:**
- Learner shares code (via opencode workspace or explicit paste)
- Agent observes silently until: learner is stuck, learner makes an error, learner asks, or code is complete
- Agent provides graduated hints (Level 0→1→2→3→4)
- Agent NEVER writes code for the learner (hard constraint)

**Observation recording:**
- Every learner action is an observation: started writing, completed function, made error, asked question
- Observations written to OBSERVATIONS.jsonl by observation-recorder agent (background, non-blocking)
- Patterns detected across observations: recurring mistakes, learning speed, preferred learning style

**Accomplishment logging:**
- When learner successfully implements a concept → accomplishment logged
- Accomplishments surface in mental model, TUI, and session-end growth notes

### 8. Scaffolding Mentor Mode

Design how the harness manages the scaffolding-mentor interaction (learner creates project skeleton):

**Interaction model:**
- Agent reads PROJECT-PLAN.md (learner's project plan)
- Agent generates an internal scaffold blueprint (file list, structure, order of creation)
- Agent guides learner through creating each file, one at a time
- Agent NEVER takes the keyboard (hard constraint)
- Agent records observations for every file creation

**Progress tracking:**
- Scaffold blueprint: list of files with status (pending → in_progress → created)
- Progress visible in TUI sidebar
- Across context resets: blueprint state survives via event store

## Success Criteria

1. Teaching session management is specified with lifecycle, identity, initialization, and pacing.
2. Teaching mode selection algorithm selects the right mode based on mastery, frustration, and style.
3. Personality/style injection converts a 7-dimension vector to system prompt modifiers.
4. Frustration detection identifies 4 levels with appropriate responses.
5. Hint escalation protocol has 5 levels with clear triggers and guardrails.
6. Context management for teaching handles compaction and concept transitions.
7. Coding partner mode and scaffolding mentor mode are specified with hard constraints.

## Research Inputs

**Primary reference — AOL teaching interactions:**
- `~/.claude/agent-of-learning/` — all teaching workflows
- `~/.claude/skills/aol-concept-teacher/SKILL.md` — concept teaching phases, Kolb stages, teaching modes
- `~/.claude/skills/aol-coding-partner/SKILL.md` — coding partner interaction model, hint escalation, never-write-code constraint
- `~/.claude/skills/aol-scaffolding-mentor/SKILL.md` — scaffolding mentor interaction model, blueprint tracking
- `~/.claude/skills/aol-drill-mentor/SKILL.md` — drill interaction model

**AOL subagents (background observation):**
- aol-mental-modeler agent — style signals, misconception tracking, confidence calibration
- aol-navigator agent — next-steps planning
- aol-observation-recorder agent — observation I/O
- aol-state-writer agent — batched state recording
- aol-learning-verifier agent — learning verification

**State shipped code:**
- `packages/opencode-plugin/src/hooks/` — existing hooks (reuse for teach mode)
- `packages/opencode-plugin/src/tui/teach-concept.ts` — existing teach sidebar
- `src/state_teach/kernel.py` — KolbMachine skeleton
- `src/state_daemon/middleware.py` — mode enforcement for teach mode

**Build mode reference (patterns to adapt):**
- v41-handoff.md — harness patterns (context management, paralysis guard, deviation rules)

## Key Questions for Discuss-Phase

1. **Agent as teacher vs agent as executor**: In build mode, the agent writes code. In teach mode, the agent teaches but the learner writes code. How does the harness enforce the "never write code for learner" constraint? Is it a system prompt instruction (soft) or a tool-level block (hard)?

2. **Mode transition transparency**: Should the learner know when the teaching mode changes? (e.g., from Scaffolded to Socratic?) Or should it be transparent? Transparent might disrupt the learning flow. Transparent gives the learner agency.

3. **Multiple learners**: The current mental model schema assumes one learner. If multi-learner is in scope, the harness needs learner identification, session isolation, and per-learner mental models.

4. **Coding partner vs build mode**: When a learner is writing code in the AC phase, they're effectively in a build session. Should the harness spawn a build-mode subagent to verify the learner's code? Or should the teaching agent handle verification?

5. **Frustration false positives**: A learner being quiet (inactivity) might be thinking, not frustrated. A learner making many errors on a drill might be experimenting, not frustrated. How does the harness distinguish?

## Dependencies

- **v46 (Teach Structure & Artifacts)** — MUST be complete. The harness needs to know the hierarchy and artifact structure.
- **v41 (Build Harness)** — useful for patterns (context management, paralysis guard).

## Scope Boundaries

**In scope:**
- Teaching session management
- Teaching mode selection and injection
- Personality/style injection
- Frustration detection and response
- Hint escalation protocol
- Context management for teaching
- Coding partner mode specification
- Scaffolding mentor mode specification

**Out of scope:**
- Learning verification (v48)
- AOL workflow porting (v49)
- Any implementation
