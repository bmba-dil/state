# Pattern: Memoized-promise lazy module import

> Defer import of an expensive ESM module until first call site; share the resolved namespace across all subsequent call sites via a single memoized Promise. Type-only imports at top of file preserve type-checker visibility without runtime cost.

**Layer:** Application Layer (M4) — CLI dispatch layer
**Source:** `gsd-2/src/cli.ts:35-41` (the canonical instance — `loadPiCodingAgentModule()` defers the `@gsd/pi-coding-agent` barrel import); `gsd-2/src/cli.ts:163-206` (the sibling instance — `ensureRtkBootstrap()` / `rtkBootstrapPromise`); `gsd-2/src/cli.ts:172, 192, 214, 224, 396, 432, 444, 473, 517, 696, 728, 737, 863, 866` (13 distinct one-shot lazy-import sites — the Variation discussed in this pattern).
**Discovered in:** Phase 19 (APP-02). Composes with [`two-stage-loader-with-fast-path-exit.md`](two-stage-loader-with-fast-path-exit.md) (Phase 19 sibling — Stage 2's overall architecture; this pattern is one of Stage 2's primary optimizations).
**Related reference:** [`../app/cli-boot.md`](../app/cli-boot.md) §4.2 (optimization table — row 2: "Memoized lazy import of pi-coding-agent") + §8 Patterns Inventory. [`../walkthroughs/cli-loader.ts.md`](../walkthroughs/cli-loader.ts.md) §6 (cli.ts:37-41 annotation) + §7 (RTK bootstrap walkthrough).

---

## What it does

A module imports an expensive ESM dependency lazily — not via top-of-file static `import` (which forces evaluation at the importing module's eval time), but via a function that calls `await import('expensive-module')` and stores the resulting Promise in a module-scope cache. The first call to that function triggers the actual import; subsequent calls receive the same Promise (already resolved, or resolving). Every caller of the function awaits the same promise; every caller sees the same module namespace.

The TypeScript shape:

```typescript
import type { ModuleType } from 'expensive-module'  // type-only — erased at runtime

let modulePromise: Promise<typeof import('expensive-module')> | undefined

function loadModule(): Promise<typeof import('expensive-module')> {
  return (modulePromise ??= import('expensive-module'))
}
```

The `??=` operator — nullish-coalescing assignment — is the load-bearing element. It assigns ONLY if the left-hand side is `null` or `undefined`. On the first call, `modulePromise` is `undefined`; the right-hand side evaluates (kicking off the dynamic import); the result is assigned. On subsequent calls, `modulePromise` is the already-resolved (or pending) Promise; the right-hand side is not evaluated; the existing Promise is returned.

The pattern's "memoized" name comes from the cache; the "promise" name comes from the cached value's type; the "lazy module import" name comes from the import deferral. All three are necessary for the pattern: removing the cache makes it eager-on-first-use-but-redundant-on-second-use; removing the promise makes it sync-only and breaks for ESM; removing the lazy import collapses to a regular static import.

In `gsd-2/src/cli.ts`, the canonical instance is `loadPiCodingAgentModule()` at L37-41:

```typescript
type PiCodingAgentModule = typeof import('@gsd/pi-coding-agent')

let piCodingAgentModulePromise: Promise<PiCodingAgentModule> | undefined

function loadPiCodingAgentModule(): Promise<PiCodingAgentModule> {
  return (piCodingAgentModulePromise ??= import('@gsd/pi-coding-agent'))
}
```

The `@gsd/pi-coding-agent` barrel re-exports 80+ symbols; importing it costs roughly 750ms on cold start (RESEARCH §5; MEDIUM-confidence per PROJECT.md "out-of-scope: performance benchmarking"). The barrel is needed by multiple code paths within cli.ts: `gsd install/remove/list` subcommands, the shared-init at L502, the `--list-models` path at L592. Each path awaits `loadPiCodingAgentModule()`; the barrel is loaded once across all of them.

## Why it works that way

Six pressures shape the design:

1. **ESM dynamic `import()` returns a Promise.** Synchronous `require()` (CJS) is dead in modern Node ESM contexts. The pattern accommodates async semantics natively rather than papering over them with synchronous wrappers (which would require `top-level await` or callback chains).

2. **A barrel import has fixed cost; sharing it is pure win.** The cost of evaluating `@gsd/pi-coding-agent` once is ~750ms; the cost of evaluating it twice is ~1500ms. Memoization is monotonically beneficial — there is no scenario where re-importing yields different behavior (Node ESM caches modules by absolute path; even without the manual cache, the second `import` call would return the same namespace, but at the cost of a function call and a Promise creation. The manual cache eliminates even that overhead).

3. **The `??=` operator is precisely what we need.** Nullish-coalescing assignment (`??=`) is the right primitive: it assigns *only* if the left side is `null` or `undefined`. This is exactly the cache semantics ("if not yet cached, compute and store; otherwise return cache"). Older JavaScript would write `cache = cache || compute()`, which has subtly wrong semantics for falsy non-null values (0, '', false). For Promise caching specifically the issue doesn't arise (Promises are always truthy), but `??=` makes the *intent* explicit: it's the cache-miss test, not a fallback default.

4. **Type-only imports preserve type-check while erasing at runtime.** `import type { … } from '@gsd/pi-coding-agent'` is a TypeScript construct that compiles away to nothing in the emitted JavaScript. Top-of-file type imports allow the function signature `Promise<PiCodingAgentModule>` to type-check against the real namespace without paying any runtime cost. The dynamic `import('@gsd/pi-coding-agent')` returns the actual namespace at runtime, where the types are then validated (or ignored, since types are erased there too).

5. **Module-scope state is the right scope.** `piCodingAgentModulePromise` is declared at module scope, not function scope. If it were function-scoped, every call would create a new promise. If it were object-scoped (e.g., on `globalThis`), it would leak across processes (in test contexts that share a globalThis) or be visible to debug/introspection tools that shouldn't see internals. Module scope is exactly the right granularity: one cache per module evaluation, invisible from outside.

6. **The pattern compiles to ~5 lines.** The implementation cost is trivial. The cognitive cost is modest (one new function-and-cache idiom per heavy dep). The benefit is real (one barrel import shared across N call sites). The cost-benefit favors using the pattern *liberally* — any dep with multiple call sites and non-trivial import cost is a candidate.

## When to use it

- **Heavy module accessed from multiple call sites in the same process.** The "multiple" part is essential — a one-shot use site is better served by inline `await import()` (the [Variations](#variations) section describes this).
- **Module that runs init side effects on first import.** Even if the module's namespace is small, side effects (config reads, env reads, file watchers) make the import non-idempotent. The cache ensures the side effects fire once.
- **Module that reads env at import time.** If the env is mutated between would-be imports, the second import would observe a different state. The cache pins the observed state to the first import's moment.
- **Barrel re-exports.** A barrel that re-exports 50+ symbols typically incurs evaluation cost from each re-exported module. Memoizing the barrel evaluates each transitive module once.
- **Cold-start-sensitive code paths.** CLIs, serverless functions, anything where the first run's latency matters. Memoization shifts cost to first use; subsequent uses are free.
- **Test contexts where you want exactly-one initialization.** A test that asserts "the heavy module is initialized once" can rely on the memoized promise; without it, the test would have to track init invocations across the entire test process.

## When NOT to use it

- **Cheap modules.** If the module costs <10ms to import, memoization is ceremony. Just `await import()` directly at each call site.
- **One-shot use.** If the module is used in exactly one code path, the cache adds overhead with no benefit. Inline the `await import()` at the call site.
- **Modules with deliberately-rerun init side effects.** Some modules need to re-initialize per invocation (e.g., a fresh DB connection). Memoization would freeze the first connection's state. Either re-design (separate import-once setup from per-use init) or use a different pattern (factory function returning fresh instances).
- **Modules that need to be conditionally swapped.** If the module choice depends on runtime state (mock vs real, A vs B), the memoization makes swapping awkward — you'd have to invalidate the cache. Strategy patterns or DI work better.
- **CommonJS-only environments.** `import()` is dynamic-import syntax; in pure CJS, `require()` is synchronous and already module-cached. The pattern degenerates to `let cached; function load() { return cached ?? (cached = require('mod')) }` — still useful but less impactful since CJS doesn't have ESM's lazy-eval promise semantics.
- **Code that runs in browsers via static bundlers without dynamic-import support.** Older Webpack configs may not split dynamic imports into separate chunks; the pattern reduces to a regular static import. Modern bundlers (Vite, esbuild, Webpack 5+) handle dynamic imports correctly.

## Algorithm

The pattern in TypeScript:

```typescript
// Type-only imports at the top — type-check visibility, zero runtime cost.
import type { ModuleType } from 'expensive-module'

// Module-scope cache — single shared Promise.
let modulePromise: Promise<typeof import('expensive-module')> | undefined

// The lazy loader — call from any number of call sites.
function loadModule(): Promise<typeof import('expensive-module')> {
  return (modulePromise ??= import('expensive-module'))
}

// First caller triggers the import.
async function caller1() {
  const mod = await loadModule()
  mod.doThing()
}

// Subsequent callers receive the same resolved Promise.
async function caller2() {
  const mod = await loadModule()
  mod.doOtherThing()
}
```

The semantics:

- First call to `loadModule()`:
  - `modulePromise` is `undefined` — the `??=` operator evaluates the right-hand side.
  - `import('expensive-module')` is invoked, returning a Promise that resolves to the module's namespace.
  - The Promise is assigned to `modulePromise`.
  - The Promise is returned to the caller.
  - The caller awaits; when the import resolves, the caller receives the namespace.
- Subsequent calls to `loadModule()`:
  - `modulePromise` is the already-existing Promise (resolved or still pending).
  - The `??=` operator does NOT evaluate the right-hand side.
  - The existing Promise is returned.
  - The caller awaits; if already resolved, awaits returns immediately with the cached namespace; if still pending, awaits with the same first-call resolution.

The crucial property is that *the first call's import is the only import*. Even if many callers fire `loadModule()` simultaneously (before the first import has resolved), they all receive the same pending Promise; when it resolves, they all unblock with the same namespace. There is no race; there is no double-import.

### The `??=` precondition

`??=` is ECMAScript 2021 (ES12). For environments older than Node 15 / TS 4.0, the equivalent is:

```typescript
return modulePromise ?? (modulePromise = import('expensive-module'))
```

The pattern's behavior is identical; only the syntax differs. GSD-2 targets Node 22+ (per `engines.node` in package.json), so `??=` is available.

### The type-only-imports invariant

Top-of-file `import type { … }` is a TypeScript-specific construct that the compiler erases. It does *not* generate runtime imports. This lets the function signature `Promise<typeof import('expensive-module')>` type-check against the real namespace without any runtime cost.

A common mistake is to use `import { … } from 'expensive-module'` (no `type` keyword). This generates a runtime import — which is exactly what the pattern is trying to avoid. The lint rule `@typescript-eslint/consistent-type-imports` catches this.

The `typeof import('expensive-module')` syntax (used in the `Promise<>` parameter) is a TypeScript type-level construct: it computes the type of what `import('expensive-module')` would produce at runtime, *without* generating any runtime code. It is purely a type expression.

### The single-process-instance invariant

Memoization is per process. A subprocess (a child node spawn, a worker thread) has its own module scope and its own cache. This is intentional — cross-process sharing of a Promise is not meaningful (Promises don't serialize). If cross-process behavior is needed, a different mechanism (shared state file, RPC) is required.

For tests, a fresh process means a fresh cache — straightforward isolation. For long-running processes that persist across many requests, the cache lives for the process's lifetime — also straightforward.

## Why this is portable

The pattern's algorithmic shape — defer-then-share — translates to any language with first-class promises (or futures) and lazy module loading:

- **Python:** `functools.cache` over `importlib.import_module` is the direct equivalent. Python's import system is itself a memoized cache (modules import once and stay in `sys.modules`), but the explicit pattern adds the *deferral* that Python's static `import` lacks.
- **Rust:** `OnceCell` or `OnceLock` from `std::sync` plus a `tokio::task::spawn` for async-loaded crates. Rust crates are compile-time linked, so "lazy crate loading" is rare; the pattern more often manifests as "lazy expensive-init."
- **Go:** `sync.Once` plus a package-level pointer. Go's static linking makes "lazy module loading" meaningless at the package level; the pattern applies within a package for expensive globals.
- **Java:** Lazy initialization holder pattern (Bill Pugh singleton) or `CompletableFuture` field. The Java idiom is similar with double-checked locking semantics.

In each case, the language idioms differ but the *contract* is identical: first call triggers, subsequent calls share, all callers await the same future.

## Python equivalent

```python
from functools import cache
import importlib
from typing import TYPE_CHECKING

# Type-only-import equivalent in Python — runs only during type-checking, never at runtime.
if TYPE_CHECKING:
    import expensive_module  # noqa: F401  (only for type-checker)

@cache
def load_module():
    """Lazy-import expensive_module; cached after first call."""
    return importlib.import_module("expensive_module")


def caller_1():
    mod = load_module()
    mod.do_thing()


def caller_2():
    mod = load_module()
    mod.do_other_thing()
```

For async contexts:

```python
import asyncio
from functools import cache

@cache
def _module_future():
    """Cache the asyncio.Future once, share across awaiters."""
    return asyncio.ensure_future(_actually_load())


async def _actually_load():
    return importlib.import_module("expensive_module")


async def load_module_async():
    return await _module_future()


async def async_caller_1():
    mod = await load_module_async()
    await mod.do_async_thing()
```

Python pitfalls:

- **`functools.cache` works on hashable arguments.** Since `load_module` takes no arguments, this is trivial. For parameterized lazy imports (e.g., `load_provider("anthropic")` vs `load_provider("openai")`), use `@cache` with the parameter as the cache key.
- **`@cache` with `maxsize=None` (unbounded) is the default.** For very large parameterized caches, prefer `@lru_cache(maxsize=N)` with an explicit cap.
- **Python's `import` system already memoizes modules.** A second `importlib.import_module("expensive_module")` after the first will hit `sys.modules` and return the cached entry — fast. The explicit `@cache` wrapper is for the deferral, not the memoization. Without the `@cache`, calling `load_module()` repeatedly is still cheap; with it, it's *imperceptibly* cheaper. The win is the *deferral*: the import doesn't fire until first call.
- **`TYPE_CHECKING`-guarded imports are not erased — they are runtime-skipped.** The compiled bytecode includes the import statement guarded by an `if False:` (since `TYPE_CHECKING = False` at runtime). Same effect as TypeScript's erasure, slightly different mechanism.
- **`asyncio.ensure_future` returns a Task.** Tasks are awaitable from multiple sites. Sharing one Task across many awaiters is the async equivalent of sharing a Promise.
- **`@cache` on a *coroutine function* caches the coroutine, not the result.** Subtle pitfall: every call would await a *different* coroutine if you `@cache` an `async def`. Cache the Task instead, as shown above.

## Source: GSD-2 implementation

The canonical instance is `gsd-2/src/cli.ts:35-41`. The full code:

```typescript
type PiCodingAgentModule = typeof import('@gsd/pi-coding-agent')

let piCodingAgentModulePromise: Promise<PiCodingAgentModule> | undefined

function loadPiCodingAgentModule(): Promise<PiCodingAgentModule> {
  return (piCodingAgentModulePromise ??= import('@gsd/pi-coding-agent'))
}
```

Five lines (including the type alias and the blank line). The type alias `PiCodingAgentModule = typeof import('@gsd/pi-coding-agent')` is the TypeScript way to extract the namespace type from a dynamic import without actually importing — pure type computation, erased at runtime.

The function is called from multiple sites within cli.ts. The exact call sites (extracted by grep `loadPiCodingAgentModule\(`):

- L306: inside the `gsd install/remove/list` subcommand path (package management — needs the registry of available packages).
- L502: shared startup init (the path used by both interactive and print mode).
- L592: `--list-models` flag handler (needs the model registry).

Each call site does:

```typescript
const { someExport } = await loadPiCodingAgentModule()
```

The `await` resolves once (when the import completes) and then resolves immediately for every subsequent call. The startup-timing instrumentation at `cli.ts:503` records `markStartup('loadPiCodingAgent')` — only the FIRST resolution costs the import; subsequent calls are no-ops at the instrumentation level.

### The sibling instance: RTK bootstrap

`gsd-2/src/cli.ts:163-206` shows the same pattern applied to a different concern — RTK (Rust-token-killer) bootstrap. The shape:

```typescript
let rtkBootstrapPromise: Promise<void> | undefined

async function doRtkBootstrap(): Promise<void> {
  // ... actual bootstrap work — read prefs, optionally call bootstrapRtk(), apply env
}

function ensureRtkBootstrap(): Promise<void> {
  if (!rtkBootstrapPromise) {
    markStartup('preRtkBootstrap')
    rtkBootstrapPromise = doRtkBootstrap()
  }
  return rtkBootstrapPromise
}
```

The shape is *almost* identical to `loadPiCodingAgentModule`, with two notable differences:

1. **The cached value is `Promise<void>`, not `Promise<Module>`.** RTK bootstrap is called for its side effects (env mutations); there's no module to return. Awaiting `ensureRtkBootstrap()` waits for the side effects to complete.

2. **The cache assignment uses `if`-guard plus assignment, not `??=`.** The author chose to inline a `markStartup('preRtkBootstrap')` call between the cache miss check and the assignment. With `??=`, the call would be inside the right-hand side (which is a single expression), making it harder to read. The `if`-guard form is functionally equivalent but more readable when the cache-miss branch needs multiple statements.

The RTK instance also shows the *full power* of the pattern: it's not just module loading, it's "cache the result of an expensive async operation, share across all awaiters." Module loading is one common application; idempotent async init is the more general one.

### The 13 one-shot lazy imports

cli.ts has 13 distinct sites that use `await import('./xyz.js')` directly, *without* memoization:

| Line | Module | Subcommand path |
|------|--------|-----------------|
| L172 | `./resources/extensions/gsd/preferences.js` | RTK preference check |
| L192 | `./rtk.js` | RTK bootstrap actual call |
| L214 | `./update-cmd.js` | `gsd update` |
| L224 | `@gsd-build/mcp-server` | `gsd graph build/status/query/diff` |
| L396 | `node:readline` | TBD |
| L432 | `./headless.js` | `gsd headless` |
| L444 | `./headless.js` | `gsd auto` (redirect to headless) |
| L473 | `./worktree-cli.js` | `gsd worktree list/merge/clean/remove` |
| L517 | `./models-resolver.js` | `--list-models` (and elsewhere) |
| L696 | `./mcp-server.js` | `gsd --mode mcp` |
| L728 | `./worktree-cli.js` | `--worktree` flag handler |
| L737 | `./worktree-status-banner.js` | worktree status banner |
| L863 | `./welcome-screen.js` | first-run welcome screen |
| L866 | `./resources/extensions/remote-questions/config.js` | remote-questions config resolution |

These are the [Variations](#variations) — see below. Each is *one-shot* (the path that uses it fires at most once per process), so memoization would add overhead with no benefit. They fall under the *one-shot lazy import* sub-pattern, which is structurally similar but lacks the memoization layer.

Note: L172 and L192 (the RTK paths) are *inside* the `doRtkBootstrap` function, which is itself memoized at the outer level. So cli.ts has nested lazy-import patterns: the outer `ensureRtkBootstrap` memoizes the bootstrap; the inner imports inside `doRtkBootstrap` are one-shot (because `doRtkBootstrap` runs once).

## Phase 19 instances

- **Canonical instance:** `gsd-2/src/cli.ts:37-41` — `loadPiCodingAgentModule()` defers the ~750ms `@gsd/pi-coding-agent` barrel import.
- **Sibling instance:** `gsd-2/src/cli.ts:163-206` — `ensureRtkBootstrap()` / `rtkBootstrapPromise` — same pattern applied to async side-effect init.
- **13 one-shot lazy-import sites** (the simpler Variation, applied where memoization isn't beneficial): cli.ts:172, 192, 214, 224, 396, 432, 444, 473, 517, 696, 728, 737, 863, 866.
- **Spine doc reference:** [`kb/app/cli-boot.md`](../app/cli-boot.md) §4.2 (optimization table — row 2: "Memoized lazy import of pi-coding-agent") + §8 Patterns Inventory.
- **Walkthrough reference:** [`kb/walkthroughs/cli-loader.ts.md`](../walkthroughs/cli-loader.ts.md) §6 (cli.ts:37-41 annotation) + §7 (RTK bootstrap walkthrough).

## Tradeoffs

**Pros:**

- Zero re-import cost for repeated calls.
- Module-scope cache is invisible from outside — clean abstraction boundary.
- Type-only imports preserve type-checker visibility for free.
- Composes naturally with [`two-stage-loader-with-fast-path-exit.md`](two-stage-loader-with-fast-path-exit.md) — Stage 1 sets env, Stage 2 uses memoized lazy imports.
- Idempotent: safe to call from any code path, including error-handlers and finalizers.

**Cons:**

- Adds ~5 lines of boilerplate per heavy dep.
- Module-scope state is testable only by re-evaluating the module (re-importing it in test). Most test runners handle this; some (which import once) may need explicit reset hooks.
- Type-only imports are a TypeScript-only construct; pure JavaScript falls back to `import { lazyMod }` without types or to JSDoc type annotations.
- The cache lives for the process lifetime — useful for CLIs, harmful for long-running daemons that want to refresh state on signal.

## Variations

**One-shot lazy import (no memoization).** When a module is used at exactly one call site, drop the cache:

```typescript
async function handleSubcommand() {
  const { runIt } = await import('./subcommand-impl.js')
  await runIt()
}
```

Each invocation pays the import cost (Node ESM caches by absolute path, so subsequent calls within the same process are fast). The cost saving from memoization is negligible because the call site fires once per process.

GSD-2's 13 one-shot sites use this Variation (cli.ts:172, 192, 214, 224, 396, 432, 444, 473, 517, 696, 728, 737, 863, 866).

**Async-init memoization.** Memoize a function call, not just a Promise:

```typescript
let initPromise: Promise<InitResult> | undefined

function init(): Promise<InitResult> {
  return (initPromise ??= computeInit())
}

async function computeInit(): Promise<InitResult> {
  // ... expensive setup
  return result
}
```

This is `ensureRtkBootstrap`'s pattern. Useful when the expensive operation is not a module import per se (it's a function call that returns a value).

**Module + state pattern.** Memoize the import + initialize state on first resolution:

```typescript
type ModuleAndState = {
  module: typeof import('expensive-module')
  state: SomeState
}

let moduleAndStatePromise: Promise<ModuleAndState> | undefined

function loadAndInit(): Promise<ModuleAndState> {
  return (moduleAndStatePromise ??= (async () => {
    const module = await import('expensive-module')
    const state = await module.initialize(/* ... */)
    return { module, state }
  })())
}
```

Combines module load with one-time state setup. Useful when the module exposes initialization that should run once (e.g., a database driver that needs to open a connection).

**Refreshable cache.** Add an invalidation mechanism:

```typescript
let modulePromise: Promise<ModuleType> | undefined

function loadModule(): Promise<ModuleType> {
  return (modulePromise ??= import('module'))
}

function invalidateModuleCache(): void {
  modulePromise = undefined
}
```

Useful when the module's behavior depends on state that can change (e.g., a config file that gets edited). Pair with a file-watcher to call `invalidateModuleCache()` on changes. Not used in GSD-2's CLI because CLI invocations are short-lived.

**Conditional lazy load.** Choose between modules at runtime:

```typescript
let modulePromise: Promise<ModuleType> | undefined

function loadModule(useReal: boolean): Promise<ModuleType> {
  return (modulePromise ??= (useReal ? import('./real.js') : import('./mock.js')))
}
```

The first call's `useReal` argument decides which module loads; subsequent calls receive the same. Subtle: if callers pass different `useReal` values, only the first call's value matters. This is a footgun for tests; document clearly or use parameterized cache.

**Per-key memoization.** Cache by argument:

```typescript
const moduleCache = new Map<string, Promise<ModuleType>>()

function loadModule(provider: string): Promise<ModuleType> {
  let cached = moduleCache.get(provider)
  if (!cached) {
    cached = import(`./providers/${provider}.js`)
    moduleCache.set(provider, cached)
  }
  return cached
}
```

Useful when many different modules might be loaded but each at most once. The Phase 11 LLM provider abstraction uses this shape (per-provider lazy load + cache).

## See also

- [`two-stage-loader-with-fast-path-exit.md`](two-stage-loader-with-fast-path-exit.md) (Phase 19 sibling) — Stage 2's overall architecture; this pattern is one of Stage 2's primary optimizations.
- [`lazy-flush-jsonl-on-commit-point.md`](lazy-flush-jsonl-on-commit-point.md) (Phase 18) — orthogonal lazy-init pattern for file persistence (NOT module loading).
- [`pure-decision-kernel-with-discriminated-actions.md`](pure-decision-kernel-with-discriminated-actions.md) (Phase 12) — separate concern (pure decision logic) but compatible — kernel calls into lazy-imported orchestrators.
- [`../app/cli-boot.md`](../app/cli-boot.md) §4.2 — the optimization table that names this pattern as row 2.
- [`../walkthroughs/cli-loader.ts.md`](../walkthroughs/cli-loader.ts.md) §6 + §7 — line-by-line walkthroughs of `loadPiCodingAgentModule` and `ensureRtkBootstrap`.

---

## Detailed walkthrough — the four phases

### Phase 1: Top-of-file declaration

```typescript
import type { ModuleType } from 'expensive-module'

let modulePromise: Promise<typeof import('expensive-module')> | undefined
```

The `import type` is erased at compile time. The `let` declaration creates the cache slot at module-evaluation time. Initial value is `undefined` — the cache-miss state. The Promise type parameter `typeof import('expensive-module')` is a type expression (does not generate runtime code) that captures the shape of what the dynamic import would produce.

### Phase 2: First call

```typescript
function loadModule(): Promise<typeof import('expensive-module')> {
  return (modulePromise ??= import('expensive-module'))
}

// First caller:
const mod = await loadModule()
```

When `loadModule()` is called for the first time:
- `modulePromise` is `undefined`.
- `??=` evaluates the right-hand side: `import('expensive-module')`.
- Node's ESM loader begins evaluating `expensive-module` (and its transitive imports).
- The result of `import(...)` is a Promise — assigned to `modulePromise`.
- The Promise is returned to the caller.
- The caller awaits — when Node finishes evaluating the module, the Promise resolves with the namespace.

### Phase 3: Concurrent calls before resolution

```typescript
// While caller 1 is awaiting the import, caller 2 fires:
async function caller2() {
  const mod = await loadModule()  // returns the same Promise as caller 1
  mod.doOtherThing()
}
```

When `loadModule()` is called while the import is pending:
- `modulePromise` is the pending Promise (truthy, not `null`/`undefined`).
- `??=` does NOT evaluate the right-hand side.
- The pending Promise is returned.
- The caller awaits — when the import resolves (same moment caller 1 unblocks), this caller also unblocks with the same namespace.

This is the "shared promise" property: many concurrent callers, one import.

### Phase 4: Calls after resolution

```typescript
// Hours later, in some completely separate code path:
async function caller3() {
  const mod = await loadModule()  // resolves immediately
  mod.somethingElse()
}
```

When `loadModule()` is called after the import has resolved:
- `modulePromise` is the resolved Promise.
- `??=` does NOT evaluate the right-hand side.
- The resolved Promise is returned.
- The caller awaits — Promise.resolve semantics: `await` on a resolved Promise returns immediately on the next microtask, yielding the cached namespace.

The microtask queue tick is the only cost — sub-microsecond on modern Node. Effectively free.

## Comparison to alternative patterns

### vs. top-of-file static import

```typescript
// Anti-pattern for heavy deps:
import { someExport } from 'expensive-module'

function caller1() {
  someExport.doThing()
}
```

The static import fires *at the importing module's evaluation time* — which is whenever cli.ts is first imported. For GSD-2, that's right after `loader.ts:258`'s dynamic-import handoff. The cost is paid even if no code path actually uses `someExport`. Memoized-lazy defers the cost to first use.

### vs. global singleton

```typescript
// (in some shared module)
export const expensiveModule = await import('expensive-module')

// (in caller)
import { expensiveModule } from './shared'
expensiveModule.doThing()
```

The "shared module" solution gets a top-level await working but still imports eagerly when *the shared module* is imported. If `./shared` is imported by some non-heavy code path, the heavy import fires. Memoized-lazy avoids this — the import doesn't fire until `loadModule()` is actually called.

### vs. CommonJS lazy require

```typescript
// CJS equivalent:
let cached: ModuleType | undefined

function loadModule(): ModuleType {
  return (cached ??= require('expensive-module'))
}
```

Synchronous, no Promise. Same memoization semantics. Limitation: only works in CJS contexts; ESM `import()` returns a Promise mandatorily.

### vs. service locator

```typescript
class ServiceLocator {
  private modules = new Map<string, Promise<unknown>>()
  get<T>(key: string, loader: () => Promise<T>): Promise<T> {
    if (!this.modules.has(key)) this.modules.set(key, loader())
    return this.modules.get(key)! as Promise<T>
  }
}
const locator = new ServiceLocator()

async function caller() {
  const mod = await locator.get('expensive', () => import('expensive-module'))
  mod.doThing()
}
```

More general — a registry of lazy modules keyed by string. Useful if you have *many* lazy modules with similar shapes; overkill for one or two. GSD-2 chose the simpler per-module pattern because the overhead of a generic locator (the Map lookup, the cache key string) is real and the use cases are few.

## Cross-language considerations

| Language | Idiom | Notes |
|----------|-------|-------|
| TypeScript ESM | `(promise ??= import('...'))` | Native fit. Use `import type` for type-only. |
| TypeScript CJS | `(cached ??= require('...'))` | Synchronous, simpler. No Promise. |
| JavaScript ESM | `(promise ??= import('...'))` | Same as TS, no type annotations. JSDoc optional. |
| Python | `@cache` over `importlib.import_module` | Python's import already caches; the wrapper adds *deferral*. |
| Rust | `OnceCell<MyModule>` + `tokio::task::spawn_once` | Crates are compile-time linked; pattern applies to expensive globals. |
| Go | `sync.Once` + package var | Static linking; pattern applies to expensive package init. |
| Java | Lazy-init holder pattern | Class-level static field, double-checked locking. |
| Swift | `lazy var` | Per-instance, not per-module. Closer to the per-key variation. |
| Kotlin | `by lazy {}` | Similar to Swift's `lazy var`. |

The pattern is a *concept*, not an idiom — every language has its own way to express "compute on first access, share thereafter."

## Performance characteristics

For a heavy module (say, `@gsd/pi-coding-agent` at ~750ms barrel import cost):

- **First call:** ~750ms (the barrel evaluates + the function call + the Promise creation).
- **Subsequent calls (after resolution):** sub-microsecond. The `??=` test, the function call, and the `await` on a resolved Promise total to a few CPU instructions plus one microtask queue tick.
- **Concurrent calls (during pending resolution):** the slowest concurrent caller blocks until the first call's resolution, which takes the same ~750ms. After that, all concurrent callers unblock simultaneously.

The performance win is asymptotic: with N call sites, eager would cost N * 750ms (worst case, if each site triggered its own re-import); memoized-lazy costs 1 * 750ms total. The real eager cost is closer to 1 * 750ms because Node ESM caches modules by absolute path — but the cost is paid *eagerly*, not at first use. Memoized-lazy shifts the cost to where it's needed.

For cold-start-sensitive code paths (like CLI fast-paths), this shift is decisive. `gsd --version` should not pay for `@gsd/pi-coding-agent`; the memoized-lazy + two-stage-loader combination ensures it doesn't.

## Real-world deployment considerations

- **Tree-shaking and dead-code elimination.** Bundlers may struggle to eliminate unreachable code after a `??=` assignment because the right-hand side has side effects (the import). For server-side Node, tree-shaking is less critical; for browser bundles, manual configuration may be needed.
- **Test isolation.** Tests that re-import the cli.ts module to test fresh state need explicit module-cache reset. Vitest/Jest's `vi.resetModules()` / `jest.resetModules()` does this; node:test requires manual reset (or running each test in a subprocess).
- **Hot-reload / HMR.** Build tools that hot-reload modules invalidate the cache automatically (the new module gets a new module-scope `let`). The pattern's per-evaluation scope is exactly what HMR expects.
- **Service-worker / Web environments.** Service workers don't generally use ESM dynamic imports the same way; the pattern is server-side-Node-flavored. Browser equivalents use `import()` similarly but with bundler-specific chunk splitting.
- **Memory pressure.** The cached Promise lives for the process lifetime. For a CLI, that's seconds-to-minutes; negligible. For a long-running server, the cached module's memory is held forever — usually fine because the module would be loaded anyway, but worth considering for memory-constrained environments.

## Migration considerations

Migrating an existing eager-import codebase to memoized-lazy:

1. **Identify heavy deps with multiple call sites.** Run `time node ./cli.js --version` and a profile to find what's taking time. Look for deps with high load cost and many call sites.
2. **Convert top-of-file imports to type-only.** `import { X } from 'heavy'` → `import type { X } from 'heavy'`. The compiler will complain about value uses; that's expected.
3. **Add the memoized loader.** Above the function definitions, declare the cache and the loader.
4. **Wrap each call site.** `X.doThing()` → `(await loadHeavy()).X.doThing()`. The await percolates: the calling function must be `async` (or use `.then()`).
5. **Verify cold-start.** `time node ./cli.js [fast-path]` should be faster.
6. **Verify behavior.** Run the full test suite. The pattern should be behavior-preserving; only timings change.

The migration is *additive* — you can leave existing eager imports in place and migrate one heavy dep at a time.

## Testing strategy

The pattern's test surface:

1. **Memoization correctness:** Test that calling `loadModule()` multiple times returns the same Promise. Use `===` equality on the Promise references (in tests where module-scope state is reset between tests, this requires running them in separate test files or using `vi.resetModules()`).
2. **Idempotency:** Test that the import side effects fire exactly once per process. Use a spy on the imported module's init code.
3. **Concurrency:** Spawn N concurrent `loadModule()` calls; verify they all resolve with the same namespace.
4. **Error handling:** Test that if the import fails, the cached Promise rejects, and subsequent calls receive the same rejection (or, depending on policy, retry).
5. **Type-safety:** TypeScript's compiler is the test for type-only imports being erased — if the build succeeds, types are correct.

## Worked example: cold-start latency comparison

Suppose `@gsd/pi-coding-agent` costs 750ms to import. cli.ts has three call sites: L306, L502, L592.

**Without memoization (eager top-of-file import):**
- cli.ts evaluation: ~50ms (its own code) + 750ms (pi-coding-agent) = ~800ms.
- Each subcommand pays this cost regardless of which call sites it actually hits.
- `gsd --version` (handled in loader.ts before cli.ts loads): ~7ms (no cli.ts cost).
- `gsd install foo` (hits L306): ~800ms.
- `gsd interactive` (hits L502): ~800ms.

**With memoized-lazy (current pattern):**
- cli.ts evaluation: ~50ms (its own code, plus ~5 lines for the cache and loader).
- The barrel doesn't load until first `await loadPiCodingAgentModule()`.
- `gsd --version`: ~7ms (no cli.ts cost; loader.ts fast-path).
- `gsd install foo`: ~50ms (cli.ts eval) + ~750ms (first barrel load at L306) = ~800ms.
- `gsd interactive`: ~50ms (cli.ts eval) + ~750ms (first barrel load at L502) = ~800ms.
- `gsd install foo && gsd install bar` (subprocess each): two ~800ms costs (separate processes; no sharing).
- `gsd interactive` (single process, hits L502, then later hits L306 for an install command): ~50ms + ~750ms (first load at L502) + microseconds (L306 reuses). Saves ~750ms vs. naive multi-load.

The savings are intra-process: any code path that hits the loader more than once benefits.

## What this pattern is NOT

- **Not a replacement for proper architecture.** If the heavy dep is heavy because it does too much, the right fix is to refactor the dep, not to lazily import it. The pattern is a tactical optimization, not a strategic one.
- **Not a security boundary.** The cache is in-process, in-module-scope. It's not isolated by trust level or origin. If the module's exported functions have security implications, the security boundary is at the function level, not the cache level.
- **Not a coordination primitive.** The cache shares one Promise across many awaiters in one process. Cross-process coordination needs message passing, not Promises.
- **Not a hot-reload mechanism.** The cache holds the first-loaded version forever (within a process). For hot-reload, invalidate explicitly or rely on the build tool's HMR.

## FAQ

**Q: What if the import fails?**

A: The Promise rejects; the cache holds the rejected Promise; subsequent calls receive the same rejection. To retry, manually reset: `modulePromise = undefined`, then call `loadModule()` again.

**Q: Can I memoize across modules?**

A: Yes — declare the cache in a shared module and export the loader. But that adds the cost of importing the shared module everywhere. For a single heavy dep used in one main module, keep the cache local.

**Q: What about top-level await?**

A: Top-level `await` (TLA) at the top of an ESM module makes the module asynchronously evaluated. Combined with `await import()`, it lets you write:

```typescript
const mod = await import('expensive-module')
export function caller() { mod.doThing() }
```

This is *eager* lazy import — the import fires when *this* module is evaluated, blocking it. No caller benefits from deferral. TLA is appropriate when the module *requires* the heavy dep to function; memoized-lazy is appropriate when callers may or may not need it.

**Q: How does this interact with bundlers?**

A: Modern bundlers (Vite, Webpack 5+, esbuild) preserve dynamic `import()` as a code-split point — the bundler emits a separate chunk for the lazily-imported module, loaded on demand. The pattern composes correctly. Older bundlers may inline the dynamic import; check bundler version.

**Q: Is this the same as a singleton?**

A: Conceptually yes — one shared instance. Mechanically different — singletons usually use a class with a private constructor and static `getInstance()`; this pattern uses a function and module scope. Functionally equivalent for the "one shared resource" property.

**Q: Why not just use `process.nextTick` or `setImmediate`?**

A: Those defer to the next tick of the event loop but don't memoize. The pattern's value is the *combination* of deferral + memoization. `nextTick`/`setImmediate` give you deferral; you'd still need a cache.

**Q: Does this work with circular dependencies?**

A: ESM handles circular dependencies by binding live exports — cycle members see partial initialization. The memoized-lazy pattern doesn't change this; the cached Promise resolves with whatever the import system would return (including potentially-partially-initialized cycle members). Avoid cycles in lazy-loaded modules.

## Glossary

- **ESM dynamic import.** The `import('./mod.js')` expression form, distinct from the static `import { … } from './mod.js'` declaration. Returns a Promise.
- **Memoization.** Caching the result of a computation keyed by its inputs (here, the cache key is implicit: there's only one input — the import path).
- **Promise.** A thenable representing an eventually-resolved value. `await` unwraps it.
- **Type-only import.** TypeScript's `import type` syntax. Erased at compile time; no runtime cost.
- **Nullish-coalescing assignment.** `??=` — assigns only if left is `null` or `undefined`. ES2021.
- **Module-scope state.** Variables declared at the top level of a module, visible only within that module.

## Closing notes

Memoized-promise lazy module import is a five-line pattern with disproportionate impact. In GSD-2's CLI, it eliminates the 750ms barrel import from every code path that doesn't need it (notably the fast-paths in loader.ts, but also any cli.ts subcommand that doesn't hit the pi-coding-agent surface). The pattern composes naturally with [`two-stage-loader-with-fast-path-exit.md`](two-stage-loader-with-fast-path-exit.md) — Stage 1 sets the env, Stage 2 uses memoized-lazy for the heavy deps.

The pattern's name encodes its three distinguishing properties: *memoized* (cache), *promise* (Promise as cache value), *lazy module import* (defer until first use). All three are necessary; removing any breaks the pattern.

For Python reimplementations, `functools.cache` over `importlib.import_module` is the direct equivalent — Python's import is already cached, so the explicit wrapper adds only the deferral. The cross-language portability is via the *contract* (defer-then-share), not the syntax.

Read this pattern alongside [`two-stage-loader-with-fast-path-exit.md`](two-stage-loader-with-fast-path-exit.md) — they capture the structural spine of GSD-2's CLI cold-start optimizations together. The spine doc [`../app/cli-boot.md`](../app/cli-boot.md) §8 Patterns Inventory provides the integration point.
