# VanillaForge Release and Repository Reconciliation

Release cleanup is not permission for unrelated refactoring.

`VANILLAFORGE_SYSTEM_PROMPT.md` §16 is the controlling canonical release checklist; this workflow operationalizes it.

## Reconcile
Inspect the complete diff and working tree. Where relevant verify:
- TOC runtime entries exist and declared files exist;
- unlisted runtime-looking files are understood;
- root `Bindings.xml` is client-managed;
- SavedVariables/schema match implementation;
- dependency metadata reflects actual consumption;
- DXVK is not an addon dependency;
- optional/recommended dependencies are accurate;
- versions and behavior docs are consistent;
- deleted/renamed files disappeared from manifests/docs;
- tests/tools/scratch artifacts are not accidentally shipped.

## Validate
Run repository tests and VanillaForge validation.

From the VanillaForge repository root:
`python tools/vanillaforge_linter.py <AddonPath>`

Canonical local linter path (developer convenience):
`C:\Users\Fostercare\Documents\VanillaForge\tools\vanillaforge_linter.py`

The linter is heuristic static analysis, not runtime proof. Investigate failures. Never bypass validation using `--no-verify`.

## Git Hook Hygiene
When hooks exist, inspect `.git/hooks/`, `core.hooksPath`, and wrappers. Old framework paths may survive migrations. When repairing hooks, preserve unrelated existing hook checks. Local `.git/hooks` repairs must not be included in addon source commits. After hook repair, rerun the repaired hook and rerun repository validation before proceeding.

## Commit Discipline
Before commit: inspect status and the working-tree diff before staging, stage only intended files, inspect the staged diff after staging, run final validation, then commit with a concise factual message.

Do not branch, commit or push unless the current task authorizes it.

## Post-Commit
When pushing, verify local HEAD, `origin/<primary>` HEAD, intended tag if tags are used, and final working-tree status.

Report static validation, repository reconciliation, commit/push and runtime verification separately.

## Runtime Follow-Up
Keep a concrete checklist for behavior that needs in-game proof: event payloads, combat transitions, target/focus stability, persistence/migrations, real UI event ordering, and optional dependency presence/absence.
