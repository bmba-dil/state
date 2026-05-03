#!/usr/bin/env node
'use strict';
/**
 * One-shot migration: M-A<N>.P<M> → v<N> + NNN (milestone-scoped layout).
 * Preserves all content; only restructures and renames.
 * Run from repo root: node .planning/_archived/migrate.js [--apply]
 */

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const PLAN = path.join(REPO, '.planning');
const ARCH = path.join(PLAN, '_archived');
const DRY = !process.argv.includes('--apply');

const log = (...a) => console.log(...a);
const write = (p, c) => {
  if (DRY) { log(`  [DRY] would write ${path.relative(REPO, p)} (${c.length} bytes)`); return; }
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, c, 'utf-8');
};
const mkdir = (p) => {
  if (DRY) { log(`  [DRY] would mkdir ${path.relative(REPO, p)}`); return; }
  fs.mkdirSync(p, { recursive: true });
};
const rename = (from, to) => {
  if (DRY) { log(`  [DRY] would rename ${path.relative(REPO, from)} → ${path.relative(REPO, to)}`); return; }
  fs.renameSync(from, to);
};
const rmrf = (p) => {
  if (DRY) { log(`  [DRY] would rm -rf ${path.relative(REPO, p)}`); return; }
  fs.rmSync(p, { recursive: true, force: true });
};

// ── Slug generation ──────────────────────────────────────────────────────────
// Strips backticks/parens/brackets, drops stopwords, max 5 words, kebab-case.
const STOPWORDS = new Set(['a','an','the','of','for','with','and','or','to','in','on','at','by','from','per','via']);
function slugify(title) {
  let t = title.replace(/\([^)]*\)/g, ' ');   // drop parenthetical clarifications
  t = t.replace(/`([^`]*)`/g, ' $1 ');         // keep code-span content, drop the backticks
  t = t.replace(/[^A-Za-z0-9\s-]/g, ' ');      // strip punctuation (incl. . in state_core.schema)
  const words = t.toLowerCase().split(/[\s-]+/).filter(w => w && !STOPWORDS.has(w));
  let slug = words.slice(0, 5).join('-').replace(/^-+|-+$/g, '').replace(/--+/g, '-');
  if (!slug) {
    // Fallback: use first non-code words from raw title
    slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'phase';
  }
  return slug;
}

// ── Parse monolithic ROADMAP.md ──────────────────────────────────────────────
// Source preference: current .planning/ROADMAP.md → _archived/ROADMAP.md (re-run resilience).
function readSrc(name) {
  const live = path.join(PLAN, name);
  const arch = path.join(ARCH, name);
  if (fs.existsSync(live)) return { text: fs.readFileSync(live, 'utf-8'), from: 'live' };
  if (fs.existsSync(arch)) return { text: fs.readFileSync(arch, 'utf-8'), from: 'archived' };
  console.error(`FATAL: neither ${live} nor ${arch} exists`);
  process.exit(1);
}
const rmSrc = readSrc('ROADMAP.md');
const rqSrc = readSrc('REQUIREMENTS.md');
log(`Source: ROADMAP.md from ${rmSrc.from}, REQUIREMENTS.md from ${rqSrc.from}`);
const roadmap = rmSrc.text;
const requirements = rqSrc.text;

const milestoneRe = /^## M-A(\d+)\s+—\s+(.+)$/gm;
const phaseRe = /^#### Phase M-A(\d+)\.P(\d+)\s+—\s+(.+)$/gm;

const milestones = [];
let m;
while ((m = milestoneRe.exec(roadmap)) !== null) {
  milestones.push({ num: +m[1], name: m[2].trim(), headerIdx: m.index, headerLine: m[0] });
}

const phases = [];
while ((m = phaseRe.exec(roadmap)) !== null) {
  phases.push({ mNum: +m[1], pNum: +m[2], title: m[3].trim(), headerIdx: m.index, headerLine: m[0] });
}

log(`Parsed: ${milestones.length} milestones, ${phases.length} phases`);
if (milestones.length !== 27 || phases.length !== 256) {
  console.error(`FATAL: expected 27 milestones and 256 phases`);
  process.exit(1);
}

// Assign flat global IDs
const idMap = {};
phases.forEach((p, i) => {
  p.oldId = `M-A${p.mNum}.P${p.pNum}`;
  p.newId = String(i + 1).padStart(3, '0');
  p.slug = slugify(p.title);
  idMap[p.oldId] = p.newId;
});

// Extract phase bodies
for (let i = 0; i < phases.length; i++) {
  const p = phases[i];
  const next = phases[i + 1];
  const nextMilestone = milestones.find(ms => ms.headerIdx > p.headerIdx);
  let end;
  if (next) end = next.headerIdx;
  else if (nextMilestone) end = nextMilestone.headerIdx;
  else {
    // Last phase — terminate before "---\n# Requirements Traceability" or end of file
    const cut = roadmap.indexOf('\n---\n\n# Requirements Traceability', p.headerIdx);
    end = cut > 0 ? cut : roadmap.length;
  }
  // But clamp to next milestone header if it comes first
  const nextMs = milestones.find(ms => ms.headerIdx > p.headerIdx);
  if (nextMs && nextMs.headerIdx < end) end = nextMs.headerIdx;
  p.body = roadmap.slice(p.headerIdx, end).trim();
}

// Group phases by milestone
const byMs = {};
for (const p of phases) (byMs[p.mNum] ||= []).push(p);

// ── Rewrite helpers ──────────────────────────────────────────────────────────
function rewritePhaseRefs(text) {
  // Pass 1: specific phase refs (longest first — must precede bare M-A<N>)
  let out = text;
  const keys = Object.keys(idMap).sort((a, b) => b.length - a.length);
  for (const k of keys) out = out.split(k).join(idMap[k]);
  // Pass 2: bare milestone refs M-A<N> → v<N>. Protect ONLY phase-shaped refs
  // like M-A1.P1 — a bare "M-A1" followed by ".." (range) or " " (prose) still rewrites.
  // Lookahead (?!\.P\d) only blocks phase-ref shape.
  out = out.replace(/M-A(\d+)(?!\.P\d)/g, 'v$1');
  return out;
}

// ── Build per-milestone files ────────────────────────────────────────────────
log('\n─── Per-milestone artifact generation ───');
for (const ms of milestones) {
  const vId = `v${ms.num}`;
  const msPhases = byMs[ms.num];
  const msDir = path.join(PLAN, 'milestones', vId);
  const phasesDir = path.join(msDir, 'phases');

  // Create phase dirs (empty — ready for /gsd:plan-phase)
  mkdir(phasesDir);
  for (const p of msPhases) {
    const dir = path.join(phasesDir, `${p.newId}-${p.slug}`);
    mkdir(dir);
    write(path.join(dir, '.gitkeep'), '');
  }

  // ROADMAP.md (per-milestone)
  const first = msPhases[0], last = msPhases[msPhases.length - 1];
  let roadmapOut = `# ${vId} — ${ms.name}\n\n`;
  roadmapOut += `**Source:** Extracted from monolithic \`.planning/_archived/ROADMAP.md\` (2026-04-22 migration).\n`;
  roadmapOut += `**Phase range:** ${first.newId}–${last.newId} (${msPhases.length} phases)\n\n---\n\n## Phases\n\n`;
  for (const p of msPhases) {
    const newHeader = `#### Phase ${p.newId} — ${rewritePhaseRefs(p.title)}`;
    const bodyMinusHeader = p.body.split('\n').slice(1).join('\n').trim();
    roadmapOut += newHeader + '\n' + rewritePhaseRefs(bodyMinusHeader) + '\n\n';
  }
  write(path.join(msDir, 'ROADMAP.md'), roadmapOut);

  // REQUIREMENTS.md (per-milestone) — extract (A<N>) section from monolithic
  const secRe = new RegExp(`^### [^\\n]*\\(A${ms.num}\\)[^\\n]*$`, 'm');
  const secMatch = requirements.match(secRe);
  if (secMatch) {
    const startIdx = secMatch.index;
    // End at next ### or ## at column 0
    const afterStart = requirements.slice(startIdx + secMatch[0].length);
    const nextRe = /^(##|###) /m;
    const nm = afterStart.match(nextRe);
    const endIdx = nm ? startIdx + secMatch[0].length + nm.index : requirements.length;
    const section = requirements.slice(startIdx, endIdx).trim();
    let reqOut = `# ${vId} — ${ms.name} Requirements\n\n`;
    reqOut += `**Source:** Extracted from monolithic \`.planning/_archived/REQUIREMENTS.md\`.\n\n---\n\n`;
    reqOut += rewritePhaseRefs(section) + '\n';
    write(path.join(msDir, 'REQUIREMENTS.md'), reqOut);
  } else {
    log(`  [WARN] no REQUIREMENTS section matched for v${ms.num}`);
  }

  // STATE.md (per-milestone seed)
  let stateOut = `# STATE: ${vId} — ${ms.name}\n\n`;
  stateOut += `**Milestone:** ${vId}\n`;
  stateOut += `**Phase range:** ${first.newId}–${last.newId}\n`;
  stateOut += `**Status:** Not started\n`;
  stateOut += `**Phases complete:** 0 / ${msPhases.length}\n`;
  stateOut += `**Last activity:** 2026-04-22 — Migrated to milestone-scoped layout\n\n---\n\n## Phase Status\n\n`;
  stateOut += `| Phase | Slug | Status |\n|-------|------|--------|\n`;
  for (const p of msPhases) {
    stateOut += `| ${p.newId} | ${p.slug} | Not started |\n`;
  }
  write(path.join(msDir, 'STATE.md'), stateOut);

  log(`  v${ms.num.toString().padEnd(2)} — ${ms.name.padEnd(45)} ${first.newId}–${last.newId}  (${msPhases.length} phases)`);
}

// ── MILESTONES.md index ──────────────────────────────────────────────────────
const tiers = [
  { name: 'Tier 1 — Foundation (parallel after scaffolding)', nums: [1, 2, 3, 4, 5] },
  { name: 'Tier 2 — Kernel & Plumbing', nums: [6, 7, 8, 9, 10, 11, 12, 13] },
  { name: 'Tier 3a — Build Domain Kernel', nums: [14, 15, 16, 17] },
  { name: 'Tier 3b — Teach Domain Kernel', nums: [18, 19, 20, 21, 22, 23, 24] },
  { name: 'Tier 4 — Polish & Portability', nums: [25, 26, 27] },
];
let msIndex = `# MILESTONES: state\n\n`;
msIndex += `**Layout:** milestone-scoped\n`;
msIndex += `**Total milestones:** 27\n`;
msIndex += `**Total phases:** 256\n`;
msIndex += `**Created:** 2026-04-22 (migration from monolithic)\n\n---\n\n`;
for (const t of tiers) {
  msIndex += `## ${t.name}\n\n`;
  msIndex += `| Milestone | Name | Phases | Path |\n|---|---|---|---|\n`;
  for (const n of t.nums) {
    const ms = milestones.find(x => x.num === n);
    const ps = byMs[n];
    msIndex += `| v${n} | ${ms.name} | ${ps[0].newId}–${ps[ps.length-1].newId} (${ps.length}) | \`milestones/v${n}/\` |\n`;
  }
  msIndex += `\n`;
}
msIndex += `---\n\n`;
msIndex += `## Progress\n\n`;
msIndex += `| Milestone | Phases done | Status |\n|---|---|---|\n`;
for (const ms of milestones) {
  const count = byMs[ms.num].length;
  msIndex += `| v${ms.num} ${ms.name} | 0/${count} | Not started |\n`;
}
msIndex += `| **TOTAL** | **0/256** | — |\n\n`;
msIndex += `*See \`_archived/ROADMAP.md\` for the pre-migration monolithic roadmap including DAG, tier boundaries, and revision history.*\n`;
write(path.join(PLAN, 'MILESTONES.md'), msIndex);

// ── Rewrite cross-reference docs ─────────────────────────────────────────────
log('\n─── Cross-doc reference rewrites ───');
// Collect files: top-level cross-ref docs + quick/**/*.md artifacts
const crossRefFiles = ['REVIEW-ROADMAP.md', 'DEBT.md', 'PROJECT.md', 'STATE.md'].map(f => path.join(PLAN, f));
function walkMd(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkMd(full));
    else if (entry.isFile() && entry.name.endsWith('.md')) out.push(full);
  }
  return out;
}
crossRefFiles.push(...walkMd(path.join(PLAN, 'quick')));
crossRefFiles.push(...walkMd(path.join(PLAN, 'research')));

for (const p of crossRefFiles) {
  if (!fs.existsSync(p)) continue;
  // Skip anything inside _archived/ or already-migrated milestones/
  const rel = path.relative(PLAN, p);
  if (rel.startsWith('_archived/') || rel.startsWith('milestones/')) continue;
  const before = fs.readFileSync(p, 'utf-8');
  const after = rewritePhaseRefs(before);
  if (before === after) continue;
  const delta = (before.match(/M-A\d+(\.P\d+)?/g) || []).length;
  log(`  ${rel}: ${delta} references rewritten`);
  write(p, after);
}

// ── config.json: add concurrent: true ────────────────────────────────────────
log('\n─── config.json ───');
const configPath = path.join(PLAN, 'config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
if (!config.concurrent) {
  config.concurrent = true;
  write(configPath, JSON.stringify(config, null, 2) + '\n');
  log('  set concurrent: true');
} else {
  log('  already has concurrent: true');
}

// ── Archive originals + cleanup ──────────────────────────────────────────────
// NOTE: macOS APFS is case-insensitive by default; `Milestones/` and `milestones/`
// resolve to the same inode. We've already populated `milestones/` above, so DO NOT
// rmrf the capitalized name — it would delete our new tree. Simply move originals
// if they're still live.
log('\n─── Archive + cleanup ───');
const liveRoadmap = path.join(PLAN, 'ROADMAP.md');
const liveReqs = path.join(PLAN, 'REQUIREMENTS.md');
if (fs.existsSync(liveRoadmap)) {
  if (DRY) log(`  [DRY] would move .planning/ROADMAP.md → _archived/ROADMAP.md`);
  else { rename(liveRoadmap, path.join(ARCH, 'ROADMAP.md')); log('  archived ROADMAP.md'); }
}
if (fs.existsSync(liveReqs)) {
  if (DRY) log(`  [DRY] would move .planning/REQUIREMENTS.md → _archived/REQUIREMENTS.md`);
  else { rename(liveReqs, path.join(ARCH, 'REQUIREMENTS.md')); log('  archived REQUIREMENTS.md'); }
}
// Old uppercase Milestones/ dir is the same inode as new milestones/ on APFS — no op needed.

log(`\n${DRY ? '[DRY RUN COMPLETE — re-run with --apply]' : '[APPLIED]'}`);
