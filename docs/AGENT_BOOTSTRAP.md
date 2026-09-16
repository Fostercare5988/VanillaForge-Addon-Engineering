# VanillaForge Agent Bootstrap

The repository is the durable source of truth; chat history is supporting context.

## Generic
```text
You are working under VanillaForge.
Read AGENTS.md, then VANILLAFORGE_SYSTEM_PROMPT.md.
Retrieve companion references only when relevant.
Do not invent APIs, expand scope automatically, or repeat verified discovery/audits without cause.
For substantial work use agent/TASK_TEMPLATE.md.
INSPECT ONLY / REVIEW ONLY means no edits.
Honor the task's stop condition.
Validate before completion and reconcile the repository when appropriate.
Do not commit/push unless explicitly authorized.
```

## Antigravity / Gemini / Astra
```text
Perform the specified task.
Read AGENTS.md first and VANILLAFORGE_SYSTEM_PROMPT.md as the contract.
Retrieve ClassicAPI/engine/pattern references only when a concrete question makes them relevant.
Do not reread and summarize the entire framework each phase.
Work in bounded phases and prefer code + verification over narration.
INSPECT ONLY / REVIEW ONLY means no edits.
Honor the task's stop condition.
Do not commit/push unless requested.
At completion report files changed, behavior, validation, unresolved runtime checks and exact git status.
```

## Codex
```text
Follow AGENTS.md as repository entry point and VANILLAFORGE_SYSTEM_PROMPT.md as engineering contract.
Retrieve companion references selectively and keep context bounded.
Reuse completed discovery/audits.
Workflow: understand -> plan -> bounded implementation -> validate -> reconcile.
INSPECT ONLY / REVIEW ONLY means no edits.
Honor the task's stop condition.
Do not commit, push, branch or alter unrelated infrastructure unless authorized.
```

## New Addon Modernization
```text
TASK TYPE: Architecture discovery + modernization audit
Read AGENTS.md, VANILLAFORGE_SYSTEM_PROMPT.md and docs/WORKFLOW.md.
Inspect before proposing changes.
Produce architecture/load graph, persistent-state model, event/timer/hot-path map, actual stack dependencies, modernization findings with evidence/impact, and bounded phases.
Consult deep references only for concrete capability questions.
Do not implement. Do not commit/push. Stop after audit and plan.
```

## Continuing Existing Work
```text
TASK TYPE: Bounded implementation
Architecture discovery/audit are already complete. Do not repeat them unless repository evidence conflicts.

KNOWN VERIFIED STATE:
<state>

CURRENT PHASE:
<objective>

SCOPE:
<files/subsystems>

INVARIANTS:
<must remain true>

VALIDATION:
<tests/linter/runtime>

STOP CONDITION:
<boundary>
```

## Release
```text
TASK TYPE: Release reconciliation
Read AGENTS.md, VANILLAFORGE_SYSTEM_PROMPT.md as the authoritative engineering contract, and docs/RELEASE_WORKFLOW.md.
Review actual final repository state/diff. Do not perform unrelated modernization.
Verify manifests, dependencies, SavedVariables, affected versions/docs, tests/linter, hooks if relevant and git status.
Do not commit/push unless authorized.
```
