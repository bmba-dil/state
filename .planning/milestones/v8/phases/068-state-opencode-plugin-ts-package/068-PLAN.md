---
phase: "068"
phase_name: "@state/opencode-plugin TS Package Scaffolding"
goal: "package.json peer deps per STACK.md; tsconfig extends @tsconfig/node22; build: tsc; bun install"
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [HOOK-11]
---

## Plan 1: Scaffold `@state/opencode-plugin` TS Package

**Goal:** Create the `@state/opencode-plugin` TypeScript package with correct peer deps, tsconfig matching opencode conventions, and verified `bun install`.

**Downstream consumers:** Phases 069-079 import hooks from this package. The executor reads this PLAN.md. If the package.json is missing or malformed, subsequent hook phases cannot build.

### Tasks

#### 1.1 Create Package Directory and `package.json`
**Acceptance:** `packages/opencode-plugin/package.json` exists with correct name, version, peerDeps, scripts
**Estimated effort:** Small
**Dependencies:** None
**Details:**
```xml
<read_first>
- .planning/research/STACK.md (Core Stack > Opencode plugin section)
</read_first>

<acceptance_criteria>
- grep '"name": "@state/opencode-plugin"' packages/opencode-plugin/package.json
- grep '"effect": "4.0.0-beta.48"' packages/opencode-plugin/package.json
- grep '"zod": "4.1.8"' packages/opencode-plugin/package.json
- grep '"solid-js": "1.9.10"' packages/opencode-plugin/package.json
- grep '"@opentui/core": "0.1.99"' packages/opencode-plugin/package.json
- grep '"@opentui/solid": "0.1.99"' packages/opencode-plugin/package.json
- grep '"@opencode-ai/plugin"' packages/opencode-plugin/package.json
- grep '"@opencode-ai/sdk"' packages/opencode-plugin/package.json
- grep '"bun"' packages/opencode-plugin/package.json
- grep '"typescript": "5.8.2"' packages/opencode-plugin/package.json
- grep '"build": "tsc"' packages/opencode-plugin/package.json
- grep '"type": "module"' packages/opencode-plugin/package.json
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/package.json`:

- name: `@state/opencode-plugin`
- version: `0.1.0`
- type: `module`
- module: `src/index.ts`
- main: `src/index.ts`
- scripts: `{ "build": "tsc", "typecheck": "tsc --noEmit", "dev": "tsc --watch" }`
- peerDependencies (match opencode catalog from STACK.md):
  - `"@opencode-ai/plugin": ">=1.14.20"`
  - `"@opencode-ai/sdk": ">=1.14.20"`
  - `"effect": "4.0.0-beta.48"`
  - `"zod": "4.1.8"`
  - `"@opentui/core": "0.1.99"`
  - `"@opentui/solid": "0.1.99"`
  - `"solid-js": "1.9.10"`
- devDependencies:
  - `"typescript": "5.8.2"`
  - `"@tsconfig/node22": "22.0.2"`
  - `"@types/node": "22.13.9"`
  - `"@types/bun": "1.3.12"`
  - `"bun": "1.3.13"`
</action>
```

#### 1.2 Create `tsconfig.json`
**Acceptance:** `packages/opencode-plugin/tsconfig.json` extends `@tsconfig/node22` with ESM + bundler module settings
**Estimated effort:** Small
**Dependencies:** 1.1
**Details:**
```xml
<read_first>
- .planning/research/STACK.md (Core Stack > Opencode plugin section for module/bundler settings)
</read_first>

<acceptance_criteria>
- grep '"extends": "@tsconfig/node22"' packages/opencode-plugin/tsconfig.json
- grep '"module": "preserve"' packages/opencode-plugin/tsconfig.json
- grep '"moduleResolution": "bundler"' packages/opencode-plugin/tsconfig.json
- grep '"outDir": "dist"' packages/opencode-plugin/tsconfig.json
- grep '"rootDir": "src"' packages/opencode-plugin/tsconfig.json
- grep '"include": \["src"\]' packages/opencode-plugin/tsconfig.json
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/tsconfig.json`:
- extends: `@tsconfig/node22/tsconfig.json`
- compilerOptions: `module: "preserve"`, `moduleResolution: "bundler"`, `target: "esnext"`, `outDir: "dist"`, `rootDir: "src"`, `declaration: true`, `sourceMap: true`, `strict: true`, `skipLibCheck: true`, `verbatimModuleSyntax: true`
- include: `["src"]`
- exclude: `["node_modules", "dist"]`
</action>
```

#### 1.3 Create Entry Point `src/index.ts`
**Acceptance:** `packages/opencode-plugin/src/index.ts` exists with PluginModule type export placeholder
**Estimated effort:** Small
**Dependencies:** 1.1
**Details:**
```xml
<read_first>
- packages/opencode-plugin/package.json (for module paths)
</read_first>

<acceptance_criteria>
- grep 'export' packages/opencode-plugin/src/index.ts
</acceptance_criteria>

<action>
Create `packages/opencode-plugin/src/index.ts`:
- Import `PluginModule` type from `@opencode-ai/plugin`
- Export a placeholder `statePlugin: PluginModule` with empty `hooks`, `tui` objects
- Add JSDoc header: `/** @state/opencode-plugin — hook shim + TUI extensions for opencode */`
</action>
```

#### 1.4 Run `bun install` and Verify TypeScript Build
**Acceptance:** `bun install` succeeds; `bun run build` compiles without errors
**Estimated effort:** Small
**Dependencies:** 1.1, 1.2, 1.3
**Details:**
```xml
<read_first>
- packages/opencode-plugin/package.json
- packages/opencode-plugin/tsconfig.json
- packages/opencode-plugin/src/index.ts
</read_first>

<acceptance_criteria>
- `bun install` exits 0 (working directory: packages/opencode-plugin)
- `bun run build` exits 0 and produces dist/index.js
- `bun run typecheck` exits 0
</acceptance_criteria>

<action>
Working directory: `packages/opencode-plugin/`
1. Run `bun install` — verify no errors, verify `bun.lockb` is created
2. Run `bun run build` — verify `dist/` contains compiled output
3. Run `bun run typecheck` — verify no TypeScript errors
</action>
```

### Integration Notes
- This package is the foundation for phases 069-078 (individual hook implementations)
- Phase 079 (final bundle) depends on this scaffolding being correct
- The peerDependencies are declared (not bundled) because the package is loaded into opencode's runtime which already has these dependencies
- File paths follow opencode's `packages/` convention (not a separate repo or npm package)

### Deviation Notes
- None — following STACK.md specifications exactly

### Verification Criteria (must_haves)
- [ ] `packages/opencode-plugin/package.json` exists with all peer deps matching STACK.md
- [ ] `packages/opencode-plugin/tsconfig.json` extends `@tsconfig/node22`
- [ ] `packages/opencode-plugin/src/index.ts` exports a valid plugin entry point
- [ ] `bun install` completes without errors
- [ ] `bun run build` compiles TypeScript successfully
