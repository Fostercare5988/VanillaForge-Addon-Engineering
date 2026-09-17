# VanillaForge Agent Entry Point

VanillaForge is the engineering framework for enhanced World of Warcraft 1.12.1 addon work.

`VANILLAFORGE_SYSTEM_PROMPT.md` is the authoritative engineering contract. `AGENTS.md` and the Agent Layer operationalize and route that contract; they do not override or replace it.

## Target
- WoW 1.12.1, Build 5875, Interface 11200
- ClassicAPI v1.15.10+
- SuperWoW v2.2+
- NamPower v4.6.2+
- UnitXP SP3 v90+
- DXVK is runtime infrastructure, never a Lua API/addon dependency.

The complete enhanced stack is assumed installed in the environment. Individual addons use and declare only components they actually consume.

## Read First
A fresh engineering session must load `VANILLAFORGE_SYSTEM_PROMPT.md`. Do not reread it every phase within the same session unless relevant context was lost or changed. Then retrieve selectively:
- ClassicAPI capability -> `CLASSICAPI_MASTER_REFERENCE.md`
- SuperWoW/NamPower/UnitXP/DXVK -> `ENGINE_REFERENCE.md`
- recurring hazards/solutions -> `KNOWN_PATTERNS.md`
- broad addon work -> `docs/WORKFLOW.md`
- release/reconciliation -> `docs/RELEASE_WORKFLOW.md`
- fresh AI session -> `docs/AGENT_BOOTSTRAP.md`

Do not read every reference merely because it exists.

## Canonical Contract Reminders
1. WoW 1.12.1 Build 5875 defines client/API/FrameXML semantics. Server/content revisions do not imply a newer Lua/API runtime.
2. Enhanced-client APIs are intentional. Do not add stock-client fallbacks.
3. Prefer verified authoritative state, structured events, unit tokens and GUID identity over scraping, fuzzy targeting, polling and compatibility shims.
4. Correct native 1.12 APIs remain valid primitives.
5. Never invent enhanced APIs. Verify uncertain claims.
6. Keep scope bounded. Do not turn a bug fix into global modernization.
7. Reuse completed discovery/audits unless new evidence invalidates them.
8. Optimize combat/hot paths deliberately; do not make performance claims stronger than evidence.
9. Runtime transaction/scratch state is not SavedVariables state unless persistence is intentional.
10. Root `Bindings.xml` is client-managed and need not be added to TOC merely to silence an orphan advisory.
11. Never declare DXVK as an addon dependency.
12. Never bypass failed validation with `--no-verify`.

## Evidence
Priority: source/headers -> official upstream docs -> verified project knowledge -> empirical runtime testing -> inference.

Use when relevant:
`[SOURCE-VERIFIED]`, `[EMPIRICALLY VERIFIED]`, `[UNVERIFIED - TEST FIRST]`.

## Task Discipline
Classify work as discovery, audit, bounded implementation, bug fix, integration review, release/reconciliation, or framework maintenance. Use `agent/TASK_TEMPLATE.md` for substantial work.

A scoped bug fix gets scoped inspection, fix and validation. Do not automatically repeat architecture discovery or a full audit.

## Completion
Before declaring substantial work complete, reconcile implementation, tests, VanillaForge linter, TOC/load graph when affected, SavedVariables when affected, dependency metadata, behavior docs, and git diff/status.

Use `agent/REVIEW_TEMPLATE.md` for complex final integration review.

## Learning
After substantial work, use `agent/RETROSPECTIVE_TEMPLATE.md`.

Do not automatically modify VanillaForge from one task. A framework lesson should be general, verified, likely to recur, important, and not already represented. Agents may propose a `FRAMEWORK LESSON CANDIDATE`; promotion requires deliberate review.

Project-specific facts stay with the addon.
