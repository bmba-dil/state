# v48 Handoff: Teach Quality & Learning Verification Pipeline

## Milestone Goal

Design the teach-mode quality pipeline — how we prove that learning actually occurred, the Bayesian mastery formula for drill grading, the learning verifier, the spaced-repetition review scheduler, and the misconception detection and correction system. This is the teach-mode equivalent of v42.

## Critical Difference from Build Mode

Build mode verifies: "does the code achieve the stated goal?" (objective, mechanical, git-diff-based)
Teach mode verifies: "did the learner actually learn?" (subjective, behavioral, observation-based)

This is fundamentally harder. You can't grep a human's brain.

## What This Milestone Must Produce

### 1. Learning Verification Framework

Design how we measure whether learning occurred:

**Verification dimensions:**
| Dimension | What It Measures | How It's Measured |
|-----------|-----------------|-------------------|
| Knowledge | Can the learner recall and explain the concept? | Drill accuracy, Socratic responses |
| Application | Can the learner apply the concept to new problems? | Coding exercises, prediction drills |
| Transfer | Can the learner use the concept in novel contexts? | Constructivist projects, cross-concept exercises |
| Retention | Does the learner retain the concept over time? | Spaced review performance |
| Confidence | Does the learner BELIEVE they understand? | Self-assessment, confidence calibration |

**Learning evidence types:**
| Evidence | Weight | Source | Reliability |
|----------|--------|--------|-------------|
| Drill pass (first attempt) | High | Drill engine | Objective |
| Drill pass (with hints) | Medium | Drill engine | Partial — hints reduced difficulty |
| Drill pass (after retry) | Low | Drill engine | May be memorization, not understanding |
| Code exercise correctness | High | Coding partner | Objective |
| Code exercise quality | Medium | Coding partner | Subjective — agent judge |
| Socratic response quality | Medium | Teaching agent | Subjective — agent judge |
| Prediction accuracy (PRIMM mode) | High | Concept teacher | Objective |
| Self-assessment | Low | Learner | Subjective |
| Transfer project success | High | Learning verifier | Subjective |
| Spaced review retention | High | Review scheduler | Objective |

**Verification report (VERIFY.md per concept):**
```yaml
concept_id: "..."
verified_at: "..."

dimensions:
  knowledge:
    score: 0.85
    evidence: "4/5 drills passed first attempt, 1/1 prediction correct"
  application:
    score: 0.80
    evidence: "Coding exercise passed, 1 minor hint used"
  transfer:
    score: null  # Not yet assessed
    evidence: null
  retention:
    score: null  # First learning — retention assessed at review
    evidence: null
  confidence:
    score: 0.75
    evidence: "Self-assessed 4/5, matches performance"

verdict: LEARNED
# LEARNED (all dimensions >= threshold)
# PARTIAL (some dimensions insufficient)
# NOT_LEARNED (major gaps — reteach needed)

recommendations:
  - "Revisit error handling pattern — 2 drills showed confusion about except vs except Exception"
  - "Good candidate for constructivist project to test transfer"
```

### 2. Bayesian Mastery Formula

Design the mathematical model for drill grading and mastery estimation. This is the core of the drill engine.

**Current state (from v19 research gap):**
Phase 178 is flagged: "AOL drill-verify internals deep-dive research — the Bayesian mastery formula is NOT yet documented." This phase must resolve that gap.

**Required outputs:**

**Prior mastery probability:** P(mastery) before the drill session, from the mental model.

**Likelihood function:** P(answer_correct | mastery) — probability of correct answer given mastery state:
- P(correct | mastered) = 1.0 - slip_probability (the learner knows it but made a slip)
- P(correct | not_mastered) = guess_probability (the learner guessed correctly)
- `slip_probability` estimated from learner's history (some learners are sloppy)
- `guess_probability` depends on question type (multiple choice has higher guess rate)

**Posterior update:** Bayes' theorem:
```
P(mastery | answer_correct) = P(answer_correct | mastery) * P(mastery) / P(answer_correct)
```

**Multi-drill aggregation:** After N drills on a concept:
```
P(mastery | answers[1..N]) = product of likelihoods * prior / normalizing_constant
```

**Drill difficulty calibration:** Each drill has a difficulty rating (0.0–1.0). Difficulty affects the likelihood function:
- Easy drill (0.2): correct answer is weak evidence for mastery (learner could know a tiny bit and pass)
- Hard drill (0.8): correct answer is strong evidence for mastery (must deeply understand to pass)

**Hint penalty:** Using a hint reduces the evidence weight of the drill:
- No hint: weight = 1.0
- Hint level 1: weight = 0.8
- Hint level 2: weight = 0.5
- Hint level 3: weight = 0.3
- Hint level 4 (solution shown): weight = 0.0 (no evidence — learner was shown the answer)

**Time penalty:** Answering very quickly or very slowly reduces evidence weight:
- Optimal time range: T_optimal ± 50%
- Outside range: weight *= 0.8

**Mastery threshold:**
- P(mastery) >= 0.80 → MASTERED
- 0.50 <= P(mastery) < 0.80 → IN_PROGRESS
- P(mastery) < 0.50 → NOT_YET

### 3. Drill Engine Design

Design the drill engine that generates, presents, and grades practice exercises:

**Drill types:**
| Type | Description | Kolb Stage | Assessment |
|------|-------------|------------|------------|
| Recall | "What is {concept}?" — free text or multiple choice | RO | Knowledge |
| Predict | "What will this code output?" (PRIMM) | RO | Knowledge |
| Fill-in | "Complete this code: {template}" | AC | Application |
| Debug | "Find the bug: {code_with_bug}" | AC | Application |
| Write | "Write a function that {spec}" | AC | Application |
| Explain | "Explain why {code} works this way" | RO | Knowledge |
| Compare | "What's the difference between {A} and {B}?" | RO | Knowledge |
| Transfer | "Build {project} using {concept}" | AE | Transfer |

**Drill generation:**
- Drills are pre-authored in DRILLS.md (per concept) — not generated live by the agent
- Each drill has: question, answer_pattern (for grading), difficulty, hints[], drill_type
- The drill engine selects drills from the bank based on:
  - Current mastery level (easy drills for low mastery, hard for high)
  - Mistake history (prioritize drills targeting past mistakes)
  - Drill type variety (don't give 5 recall drills in a row)

**Drill presentation:**
- Via opencode's `question` tool (interactive prompt)
- Drill appears as a question the learner must answer
- Timer visible (for time-based evidence weight)
- Hint button available ("Need a hint?" — increments hint level)

**Drill grading:**
- Compare learner's answer to `answer_pattern` (fuzzy match, not exact)
- For code drills: run against test cases
- For explanation drills: LLM judges semantic equivalence
- Grade: CORRECT, PARTIAL, INCORRECT
- Update mental model via Bayesian formula

**Drill session flow:**
```
PREPARE → engine selects N drills from bank
  → PRESENT → engine presents drill via question tool
    → SUBMIT → learner submits answer
    → GRADE → engine grades, updates Bayesian mastery
    → FEEDBACK → agent provides targeted feedback
  → REPEAT for N drills or until mastery >= threshold
→ COMPLETE → engine writes mastery update to mental model
```

**Drill budget:**
- Max drills per session: configurable, default 10
- Max time per drill: configurable, default 3 minutes
- Max token budget for drill prompt: ≤ 3000 tokens (v19 requirement)
- Early termination: if mastery >= threshold after M drills (M < N), stop early

### 4. Spaced Repetition Review Scheduler

Design how review scheduling works after a concept is mastered:

**Algorithm options:**
- SM-2 (SuperMemo 2): proven, battle-tested, simple
- Leitner system: physical flashcard model adapted to digital
- Custom Bayesian: decay model based on learner's forgetting curve

**Recommended: SM-2 with learner-specific calibration.**

**SM-2 parameters:**
- `n`: repetition number (how many times reviewed)
- `EF`: easiness factor (how easy the learner finds this concept)
- `interval`: days until next review

**SM-2 algorithm:**
```
After each review:
  If grade >= 3 (pass):
    If n == 0: interval = 1 day
    If n == 1: interval = 6 days
    If n >= 2: interval = previous_interval * EF
    n += 1
  Else (fail):
    n = 0
    interval = 1 day
  EF = EF + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
  EF = max(EF, 1.3)  # floor
```

**Review events:**
- `state.concept.reviewed` — review session completed, SM-2 parameters updated
- `state.concept.mastery_decayed` — mastery fell below threshold (scheduled but not yet reviewed)

**Review scheduling in mental model:**
```json
{
  "next_review": "2026-05-15T00:00:00Z",
  "review_history": [
    {"date": "2026-05-01", "grade": 4, "interval": 1, "ef": 2.5},
    {"date": "2026-05-02", "grade": 5, "interval": 6, "ef": 2.6},
    {"date": "2026-05-08", "grade": 4, "interval": 15, "ef": 2.5}
  ],
  "mastery_decay_rate": 0.02  # per day without review
}
```

### 5. Misconception Detection & Correction

Design how the system detects and corrects misconceptions:

**Misconception taxonomy:**
| Type | Example | Detection |
|------|---------|-----------|
| Syntax confusion | Using `async` without `await` | Pattern matching on code errors |
| Semantic misunderstanding | Thinking `await` blocks all execution | Socratic probing reveals wrong explanation |
| Over-generalization | Applying pattern everywhere without discrimination | Transfer exercises show inappropriate use |
| Under-generalization | Not recognizing when to apply pattern | Missing opportunities in code exercises |
| Terminology confusion | Mixing up "coroutine" and "task" | Free-text response analysis |

**Detection methods:**
- Recurring drill mistakes on the same concept → likely misconception
- Coding exercises with the same error pattern → likely misconception
- Socratic responses that are consistent but wrong → likely misconception
- Explicit learner confusion ("I thought X meant Y") → likely misconception

**Correction protocol:**
1. Detect: identify the misconception from mistake patterns
2. Surface: agent gently points out the misconception ("I notice you've been doing X. Actually...")
3. Re-teach: agent re-enters CE (Concrete Experience) with a counter-example specifically targeting the misconception
4. Verify: targeted drill specifically on the misconception
5. Confirm: learner can explain the correct concept in their own words

**Misconception recording:**
```json
{
  "concept_id": "async-await",
  "misconception": "await blocks the event loop",
  "detected_at": "...",
  "evidence": ["3 drills answered with blocking assumption", "exercise used time.sleep instead of asyncio.sleep"],
  "resolved": false,
  "resolution_attempts": 1
}
```

### 6. Growth Verification (Cross-Concept)

Design how we verify growth across multiple concepts:

**Module-level verification:**
- All concepts in module at MASTERED level → module is COMPLETE
- Some concepts NOT_YET → module is IN_PROGRESS
- Transfer exercise spans multiple concepts in module → module growth verified

**Subject-level verification:**
- All modules COMPLETE → subject is COMPLETE
- Capstone project spans multiple modules → subject growth verified
- This is the teach-mode equivalent of the build-mode cross-tier verifier

**Learning trajectory:**
- Trace mastery over time for each concept
- Detect plateaus (mastery flatlines despite drills) → flag for intervention
- Detect regression (mastery declines) → flag for review

## Success Criteria

1. The learning verification framework defines 5 dimensions with evidence types, weights, and reliability ratings.
2. The Bayesian mastery formula is fully specified with prior, likelihood, posterior, aggregation, difficulty calibration, hint penalty, and time penalty.
3. The drill engine supports 8 drill types with generation, presentation, grading, and session flow.
4. The spaced repetition scheduler (SM-2 variant) is specified with parameters and decay model.
5. Misconception detection covers 5 types with detection methods and correction protocol.
6. Growth verification spans from concept to module to subject level.

## Research Inputs

**Primary reference — AOL drill engine (the gap to fill):**
- `~/.claude/agent-of-learning/` — any drill grading formulas, Bayesian math, mastery thresholds
- `~/.claude/skills/aol-drill-mentor/SKILL.md` — drill interaction flow, grading criteria
- Look specifically for: mastery probability formulas, drill grading rules, spaced repetition implementation
- If AOL doesn't have a formal Bayesian formula (it may be heuristic), the design needs to CREATE one

**Learning science reference:**
- SM-2 algorithm specification (SuperMemo 2) — proven spaced repetition algorithm
- Bayesian Knowledge Tracing (BKT) — academic model for estimating student knowledge
- Item Response Theory (IRT) — academic model for calibrating question difficulty

**State shipped code:**
- `src/state_core/schema.py` — drill events (`state.drill.prepared`, `state.drill.submitted`, `state.drill.graded`)
- `src/state_teach/drill.py` — empty placeholder

**State planning:**
- `.planning/milestones/v19/REQUIREMENTS.md` — DRL-01..06
- `.planning/milestones/v19/ROADMAP.md` — Phase 178 research gap

**Build mode reference:**
- v42-handoff.md — learning verification is analogous to code verification (both use evidence weighting, multi-level checking, adversarial stance)

## Key Questions for Discuss-Phase

1. **Bayesian vs heuristic**: Should the mastery formula be a formal Bayesian model (rigorous, explainable, but complex) or a heuristic scoring system (simple, tunable, but less principled)? The AOL drill engine may already use one or the other.

2. **LLM-as-judge for grading**: For explanation/prediction drills, the only way to grade is via LLM. How reliable is LLM grading? Should it be calibrated against human grading? Should the learner be able to appeal a grade?

3. **Mastery threshold**: Is 0.80 the right threshold? Too low → learner moves on without understanding. Too high → learner gets stuck drilling forever. Should it be configurable per concept?

4. **Review obligation**: After a concept is mastered, how obligated is the learner to review? Can they ignore review prompts? If they skip reviews, does mastery decay to zero? Or does the system just remind?

5. **Transfer verification**: How do we verify transfer (applying a concept in a novel context)? This is the hardest dimension. Is it feasible to automate, or does it always require human evaluation?

## Dependencies

- **v46 (Teach Structure)** — MUST be complete. The quality pipeline operates on the hierarchy.
- **v47 (Teach Harness)** — useful. The harness manages drill sessions and misconception detection.
- **v42 (Build Quality)** — useful for patterns (4-level model, adversarial stance).

## Scope Boundaries

**In scope:**
- Learning verification framework (5 dimensions)
- Bayesian mastery formula
- Drill engine design (8 types)
- Spaced repetition review scheduler
- Misconception detection and correction
- Growth verification (concept → module → subject)

**Out of scope:**
- Implementation of any formula
- AOL workflow porting (v49)
- Drill UI (v23 TUI extensions)
