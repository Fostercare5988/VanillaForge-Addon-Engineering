# VanillaForge Engineering Workflow

This is the normal lifecycle for substantial addon engineering. Do not mechanically repeat every phase for every task.

## 1. Classify
Choose the smallest correct class: architecture discovery, modernization audit, bounded implementation, scoped bug fix, integration review, release/reconciliation, or framework maintenance.

## 2. Architecture Discovery
Use when the addon/subsystem is not yet understood. Establish TOC/load graph, module responsibilities, SavedVariables, event/timer ownership, state machines, UI ownership, actual dependencies, enhanced APIs, hot paths and cross-module contracts.

Deliver a concise architecture map plus uncertainties. Do not edit during an inspect-only phase.

## 3. Modernization Audit
Prioritize correctness and architectural simplification. Look for scraping where structured APIs exist, localized combat parsing where structured events exist, target swapping/fuzzy identity, unnecessary OnUpdate polling, obsolete compatibility layers, redundant caches, hot-path allocation churn, and ambiguous asynchronous ownership.

Record finding, location, evidence, impact and direction. Do not implement during audit-only work.

## 4. Plan Bounded Phases
Each phase needs one objective, explicit scope, invariants, validation and a stop condition.

## 5. Implement
Follow the authoritative API-selection guidance in `VANILLAFORGE_SYSTEM_PROMPT.md` §7.

There is no legacy fallback tier. For async workflows, make request ownership explicit so stale/duplicate events cannot advance or erase newer work.

## 6. Validate
Use targeted tests, structural/syntax checks, `tools/vanillaforge_linter.py`, repository tests, invariant review and runtime verification where static analysis cannot prove behavior.

Useful runtime tools: `/reload`, `/luaerrors 1`, `/etrace`, `/dump`, `/framestack`.

Static success is not runtime proof.

## 7. Integration Review
Use after complex multi-phase, state-machine, persistence, ownership or cross-module work. Review integrated behavior for stale events, supersession, premature state publication, lost deferred work, cleanup ownership, migration precedence, dependency mismatch and load-order regressions.

Use `agent/REVIEW_TEMPLATE.md`.

## 8. Repository Reconciliation
At completion check files added/deleted/renamed, TOC, root client-managed `Bindings.xml`, SavedVariables, dependencies, affected versions/docs, tests/linter, scratch artifacts, and git status/diff. Remove temporary diagnostic slash commands and debug instrumentation.

For a release/commit, follow `docs/RELEASE_WORKFLOW.md`.

## 9. Retrospective
Use `agent/RETROSPECTIVE_TEMPLATE.md`. Keep addon-specific lessons with the addon. Promote reusable lessons only through the framework lesson gate.
