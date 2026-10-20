# VanillaForge Agent Bootstrap

Use this starter with any coding assistant. Replace the fields and choose one
mode; the repository holds durable state, while chat history supplies context.

- **Audit:** inspect and produce findings with evidence and a bounded plan; no edits.
- **Implementation:** complete the requested changes and validation in bounded phases.
- **Release:** reconcile the final state and prepare or publish only as authorized.
- **Framework maintenance:** review reusable evidence and refine its canonical owner.

## Start

```text
FRAMEWORK: <VanillaForge folder>
PROJECT: <addon/repository and active folder>
TARGET: <server, OctoWoW distribution revision, engine/interface, selected client root>
ENVIRONMENT EVIDENCE: <DLLs assumed installed per CORE; native acceptance or explicitly source-only>
MODE: <audit / implementation / release / framework maintenance>
OBJECTIVE: <requested result and current frustrations>
SCOPE: <subsystems; behavior and settings that must remain>
STOP CONDITION: <concrete completion boundary>
GIT AUTHORIZATION: <none, or the specific requested Git/release actions>

Read AGENTS.md, then CORE.md as the contract. For a Gate or Framework pass,
also read VANILLAFORGE_SYSTEM_PROMPT.md. Use the relevant workflow and references only for concrete questions. For the
selected OctoWoW client, follow docs/TARGET_ENVIRONMENT.md. Historical paths and
DLL observations in audit/OCTOWOW_CLIENT_BASELINE.md need current applicability.
Reuse completed discovery unless repository evidence invalidates it.

Follow the selected mode. Scale inspection and validation to the scope;
do not turn a small fix into a full modernization. For broad addon polish,
inspect load order, persistent state, events/timers, UI ownership and actual
dependencies, then simplify in bounded phases while preserving useful behavior.
Use docs/WORKFLOW.md's complete performance/polish pass: account for loaded
modules, trace burst fan-out, compare provider semantics/cost and measure actual
before/after work. Complete supported repairs when implementation is authorized.
Release preparation uses docs/RELEASE_WORKFLOW.md. Framework maintenance uses
agent/RETROSPECTIVE_TEMPLATE.md to merge, refine or replace existing knowledge.

Complete the authorized work and reconcile affected repository surfaces.
Report meaningful changes/removals, validation, remaining runtime checks and
git status. Distinguish static/model evidence from in-game verification.
```

## Resume

```text
Continue under AGENTS.md and CORE.md (plus VANILLAFORGE_SYSTEM_PROMPT.md for
a Gate or Framework pass). Reload the contract if its context was lost or changed; retrieve references selectively.
VERIFIED STATE: <completed work and source/test evidence>
CURRENT OBJECTIVE: <next bounded phase>
SCOPE / INVARIANTS: <what may change; what must remain>
VALIDATION: <relevant checks and outstanding runtime tests>
STOP CONDITION: <completion boundary>
GIT AUTHORIZATION: <none, or the specific requested actions>
Reuse completed discovery unless new evidence conflicts. Complete this phase
and report the result, validation and repository status.
```
