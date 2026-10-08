# VanillaForge Release and Repository Reconciliation

Release cleanup is not permission for unrelated refactoring.

The [contract](../VANILLAFORGE_SYSTEM_PROMPT.md#completion-and-release) controls
release authorization and completion; this workflow supplies the procedure.

## Reconcile
Inspect the complete diff and working tree. Where relevant verify:
- TOC runtime entries exist and declared files exist;
- unlisted runtime-looking files are understood;
- root `Bindings.xml` is client-managed;
- SavedVariables/schema match implementation and current users' settings survive;
- dependency metadata reflects actual consumption;
- DXVK is not an addon dependency;
- optional/recommended dependencies are accurate;
- versions and behavior docs are consistent;
- deleted/renamed files disappeared from manifests/docs;
- tests/tools/scratch artifacts are not accidentally shipped.

Persist only intentional player settings or data; keep caches, transient queues
and request owners in runtime state. New addons start with a small current schema. Do not add
speculative legacy imports, version ladders or reset paths to make a release look
fresh. For an existing addon, migrate only a demonstrated stored shape that the
changed implementation needs, preserve unrelated values, and test the old and
current shapes. Removing credits or history prose is not a schema change.

## Validate
Run repository tests and VanillaForge validation.

From the VanillaForge repository root:
`python tools/vanillaforge_linter.py <AddonPath>`

Investigate findings and repair failed checks before proceeding.

## Git Hook Hygiene
When hooks exist, inspect `.git/hooks/`, `core.hooksPath`, and wrappers. Old framework paths may survive migrations. When repairing hooks, preserve unrelated existing hook checks. Local `.git/hooks` repairs must not be included in addon source commits. After hook repair, rerun the repaired hook and rerun repository validation before proceeding.

## Commit Discipline
Before commit: inspect status and the working-tree diff before staging, stage only intended files, inspect the staged diff after staging, run final validation, then commit with a concise factual message.

## Post-Commit
When pushing, verify local HEAD, `origin/<primary>` HEAD, intended tag if tags are used, and final working-tree status.

Report static validation, repository reconciliation, commit/push and runtime verification separately.

## Downloadable Package

Keep the README and player guides focused on purpose, features, installation,
controls and actual requirements. Omit engineering chronology, recovery notes,
unrelated integration asides and decorative credits when the user requests a
clean presentation. Preserve required license terms, copyright and attribution
notices; a request to remove personal names does not establish permission to
remove those notices or establish disputed authorship claims.

Define an explicit release file allowlist: the complete runtime load graph,
client-managed files such as `Bindings.xml`, required media/notices and useful
player guides. Tests, Python tools, CI, audit reports, capture logs, source
backups and engineering migration/recovery records belong outside the runtime
package. Keep useful engineering evidence locally; remove temporary diagnostics.

The public Git tree and downloadable package are separate deliverables. When the
user requests an end-user-only repository, apply the allowlist to tracked public
files as well as the ZIP. Retain private tests and validation tools in the
maintained workspace or local ignored paths. Export-ignore rules alone do not
remove developer files from GitHub, and ignoring a tracked file does not untrack
it. Recheck validation against the exact code selected for publication.

Build from the intended tag/commit with the correct addon directory prefix.
Verify the tracked tree, ZIP inventory and installed runtime independently
against their declared allowlists; compare common file contents with the reviewed
source/committed blobs. Check archive integrity, TOC/XML load closure and required
media. A clean ZIP does not prove a clean public tree or correct installed build.
Git on Windows may apply `core.autocrlf` during `git archive`; for an archive that
must match committed blobs exactly, use `git -c core.autocrlf=false archive ...`.
After an authorized upload, download the public asset and compare its bytes or
digest with the verified local archive. A successful push does not verify the ZIP.

For an explicitly authorized history reset, retain a verified local recovery copy
outside the active game and use guarded ref updates. Verify branches, tags and
release assets separately, including the final commit count when a single fresh
commit was requested. Check the contract's authorization boundary before changing
published history, tags or assets; clean packaging alone does not authorize them.

Keep recovery and engineering artifacts outside the active game directory by
default. Maintain one concise local record of source, deployment, evidence and
recovery paths. An existing authorized external recovery copy can satisfy this
need; avoid accumulating duplicate backups in the game folder.

## Runtime Follow-Up
Keep a concrete checklist for behavior that needs in-game proof: event payloads, combat transitions, target/focus stability, persistence/migrations, real UI event ordering, and optional dependency presence/absence.
