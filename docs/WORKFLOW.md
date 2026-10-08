# VanillaForge Engineering Workflow

This is the normal lifecycle for substantial addon engineering. Do not mechanically repeat every phase for every task.

## 1. Classify
Choose the smallest correct class: architecture discovery, modernization audit, capability displacement review, bounded implementation, scoped bug fix, integration review, release/reconciliation, or framework maintenance.

## 2. Architecture Discovery
Use when the addon/subsystem is not yet understood. Establish TOC/load graph, module responsibilities, SavedVariables, event/timer ownership, state machines, UI ownership, actual dependencies, enhanced APIs, hot paths and cross-module contracts.

Deliver a concise architecture map plus uncertainties. Do not edit during an inspect-only phase.

## 3. Modernization Audit
Prioritize correctness and architectural simplification. Look for scraping where structured APIs exist, localized combat parsing where structured events exist, target swapping/fuzzy identity, unnecessary OnUpdate polling, obsolete compatibility layers, redundant caches, hot-path allocation churn, and ambiguous asynchronous ownership.

Record finding, location, evidence, impact and direction. Do not implement during audit-only work.

### Complete performance and polish pass

For an authorized full audit/refactor, carry discovery through bounded repairs
and validation in the same task. Audit-only mode still stops at findings.
Start with the actual maintained source and active deployment; a previous audit
is reusable only while its relevant file hashes, dependencies and settings apply.

Run `python tools/audit_addon.py <AddonPath> --output <PrivateReportPath>` to
collect the loaded module inventory, source hashes, registrations, candidate
query/UI sites and scoped lint results. Add `--run-tests` to run local Python
unittest discovery when that is the repository's test contract. Other test
frameworks need their documented command. The report is a review map, not proof
that every module was inspected or that a call is expensive. Keep it outside the
addon and active game. Dynamic loaders, indirect wrappers and engine event
semantics still need source review.

Use one compact coverage table with a row per loaded module or coherent
subsystem. Record its responsibility, state owner, triggers, repeated work,
relevant API choices, evidence and disposition: repaired, verified unchanged,
reused evidence, or unresolved. Include load-on-demand paths, client-managed
bindings and optional integrations. Do not call an inventory a completed audit;
resolve every row before reporting full coverage, and state remaining limits.

Trace triggers through their consumers before counting suspicious syntax:

1. **Fan-out and cardinality:** list events/hooks/timers, burst sizes, affected
   entities and work per callback. A per-slot hook that refreshes every slot can
   multiply a linear pass into quadratic work. Trace who already refreshed or
   invalidated the same data. Death, loot, aura, bag, equipment and inspect bursts
   deserve explicit scenarios where the addon handles them.
2. **Authority and lifecycle:** compare existing native and DLL providers using
   verified semantics, traversal cost, payload, identity, restrictions and cleanup.
   A newer API or native timer is not automatically cheaper. Roster changes do
   not cover live aggro changes; hidden views should not retain needless scans.
   Preserve frame-rate animation and native input/redraw owners.
3. **Bounded repair:** coalesce invalidations sharing one view/owner, query current
   state at delivery, and preserve reentrant work and independent slots. Diff
   stable addon-owned styling without suppressing required native updates. Do not
   introduce broad caches, new polling or speculative abstractions to lower a
   call counter. See [Known patterns](../KNOWN_PATTERNS.md) for lifecycle details.
4. **Evidence:** use the actual before/after source with the same controlled
   fixture. Count meaningful queries, traversed units, UI mutations, allocations
   or scheduled callbacks as applicable; include setup and any work moved into
   a timer/native provider. Exercise closed views, reused identities, bursts,
   cancellation, repeated requests, missing data and optional owners. New
   regressions should fail the old code for the intended reason where practical.
   Operation counts establish work reduction; frame delivery needs comparable
   native measurements. Profiler Count includes idle and throttle returns.
5. **Polish:** review control usefulness, defaults and descriptions before styling.
   Apply the shared settings theme consistently, preserve positions/bindings and
   test visibility, scaling, dragging, Escape and native widget semantics. A
   screenshot or permissive mock cannot prove native input behavior.

Stop after the agreed coverage, backed repairs, relevant checks, exact deployment
verification and concise unresolved runtime list. Do not expand into speculative
rewrites. Keep one private record of changed source, installed/pending files,
measurements, validation and recovery. Release cleanup follows the separate
[release workflow](RELEASE_WORKFLOW.md).

## 4. Plan Bounded Phases
Each phase needs one objective, explicit scope, invariants, validation and a stop condition.

## 5. Implement
Follow the authoritative API-selection guidance in `VANILLAFORGE_SYSTEM_PROMPT.md`.

There is no legacy fallback tier. For async workflows, make request ownership explicit so stale/duplicate events cannot advance or erase newer work.

When retiring a feature, remove its implementation, controls, defaults, event
registrations, commands and affected documentation together. Check dynamic
callers and supported integrations before calling code dead. Preserve necessary
SavedVariables migration and unrelated user choices. Simplicity does not justify
removing supported behavior outside the requested scope.

## 6. Validate
Use targeted tests, structural/syntax checks, `tools/vanillaforge_linter.py`, repository tests, invariant review and runtime verification where static analysis cannot prove behavior.

Useful runtime tools: `/reload`, `/luaerrors 1`, `/etrace`, `/dump`, `/framestack`.

Static success is not runtime proof.

For UI changes, verify methods against the actual client/widget type before
adding them to a test double. Mocks must reject unsupported methods on the
changed widget rather than silently return no-op functions. Exercise normal
settings entry, saved-state refresh, toggle and reset paths. For drag changes,
also test live refresh during a first unsaved drag, modifier release, and saved
positions at different scales. See `ENGINE_REFERENCE.md` §12.9.

For client hooks, verify the global in the exact 1.12 source or a verified
extension, then inspect its event and render callers. Test the native redraw
that can overwrite addon presentation, not only the addon's event handler.
Preserve meaningful side effects in mocks, such as cooldown sequence restarts.
For a regression fix, where practical, run the new test against the faulty
revision and confirm it fails for the intended reason. Execute the relevant
pinned FrameXML function in a source integration test when simplified mocks
cannot represent the interaction. Report this separately from in-game testing.

## 7. Integration Review
Use after complex multi-phase, state-machine, persistence, ownership or cross-module work. Review integrated behavior for stale events, supersession, premature state publication, lost deferred work, cleanup ownership, migration precedence, dependency mismatch and load-order regressions.

Use `agent/REVIEW_TEMPLATE.md`.

## 8. Repository Reconciliation
At completion check files added/deleted/renamed, TOC, root client-managed `Bindings.xml`, SavedVariables, dependencies, affected versions/docs, tests/linter, scratch artifacts, and git status/diff. Remove temporary diagnostic slash commands and debug instrumentation.

For a release/commit, follow `docs/RELEASE_WORKFLOW.md`.

## 9. Retrospective
Use `agent/RETROSPECTIVE_TEMPLATE.md` after substantial work. Record only useful
lessons or costly rework; a routine success needs no new report file. Inspect
existing coverage before proposing a change. Refining or replacing its canonical
owner takes precedence over adding guidance. Framework promotion is a separately
authorized maintenance action; addon-specific facts stay with the addon.

## 10. Upstream Refresh & Capability Displacement

A framework baseline update and an addon modernization review are separate, bounded phases:
- **Framework baseline update:** answers *"What capabilities are now available?"* Records provenance, audits drift, updates documentation, and advances framework tracking without editing addon repositories.
- **Capability displacement review:** answers *"Which existing addon mechanisms can now be retired, simplified, or moved to a superior provider?"* Identifies and schedules concrete portfolio modernization candidates.

### Modernization Lifecycle:
1. **Upstream release:** new tag or release identified.
2. **Upstream audit:** verify release boundary, tag hashes, commit provenance, and drift using `agent/UPSTREAM_AUDIT_TEMPLATE.md`.
3. **Framework baseline update:** advance `UPSTREAM_VERSIONS.json`, reference documentation, and linter baseline.
4. **Capability displacement review:** populate candidate matrix evaluating existing addon mechanisms against new primitives.
5. **Portfolio candidate selection:** select verified replacement candidates for bounded implementation tasks. Updating the framework baseline does not automatically mean editing all addons.
6. **Bounded addon modernization:** modernize identified subsystems in dedicated tasks using verified primitives.
7. **Static & runtime validation:** run linter scans, unit tests, and live game testing (`/dump`, `/etrace`).
8. **Obsolete code & dependency removal:** remove displaced Lua helpers, delete dead fallback paths, and drop unused DLL declarations from addon TOC and README when all call sites are eliminated.
