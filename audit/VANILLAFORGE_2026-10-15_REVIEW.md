# VanillaForge framework review — 15 October 2026

Scope: framework maintenance against repository `88a4592f57b37c83182f224b2d1c45a29ca79739`.
All 56 original tracked files were reviewed, with structured inspection of large
JSON evidence. This reviews the framework and its evidence boundaries; it does
not recertify every upstream API or run a game session. No client download,
installed addon changes, native binary changes or deployment were required.

## Coverage and disposition

| Original area | Files | Review and disposition |
| --- | ---: | --- |
| Root guidance, references, registry and Git ignore | 8 | Refined mandatory environment policy, supported floors, source/release identity, provider collisions and misleading assumptions. Ignore rules remain suitable. |
| Agent templates | 4 | Added selected-client evidence to task/integration review; upstream and retrospective procedures remain applicable. |
| Workflow/bootstrap/release/decision docs and five ClassicAPI audits | 9 | Routed a short target guide, bound addon work to the selected installation, preserved historical audits, appended current stable provenance corrections. |
| Dated client/portfolio/native/UI/MSBT/runtime audits, JSON evidence and replay tools | 18 | Corrected historical scope and loader/renderer certainty. Structured JSON consistency checks retained original hashes and results. Historical reproductions remain defect demonstrations. |
| Installed-addon regressions and guide | 3 | Retained actual-source routing and Lua-model/native limitations. No addon source available or changed in this framework task. |
| Python tools | 6 | Added client preflight and evidence binding, real PE resource/architecture checks, Interface validation and environment/document drift checks. Existing upstream commit pinning and index generation retained. |
| Python test suites | 6 | Added positive/negative environment, provenance, supported-floor, TOC, output-containment and evidence-invalidation regressions. |
| CI workflows | 2 | Validation requires target profile and client tooling/tests; existing scheduled upstream review remains suitable. |

## Findings resolved

- The manifest previously stamped target build/interface onto arbitrary folders.
  Expected target data and observed executable evidence are now separate.
- All four API DLLs are explicitly required. Supported minima remain ClassicAPI
  1.15.16, SuperWoW 2.2, NamPower 4.6.2 and UnitXP SP3 v89. The current reference
  releases do not silently raise addon requirements.
- File/configuration preflight fails for absent, old or unidentified requirements,
  wrong realm/engine or non-x86 images. It reads bounded PE version resources,
  uses known released hashes where available and preserves uncertainty.
- Addon audits can select a client, enforce installed-source containment, compare
  environment evidence separately and invalidate test evidence after changes.
  Reports stay outside the selected game. Source-only checks remain explicit.
- Interface metadata is validated without rejecting inactive foreign TOC flavors.
  Explicit TOC scans are supported; default root discovery is a closure inventory,
  not proof of which flavor the runtime selected.
- Partial FrameXML extraction now identifies its scope, unknown archives and
  loose-file candidates. Comparison detects candidate, TOC and working-tree status
  changes even when addon commits do not move.
- Older native audit text confused configured loading with runtime loading and
  inferred rendering from file absence. Those conclusions were corrected while
  keeping dated file identities and historical evidence.

## Upstream evidence

The official [OctoWoW site](https://octowow.st/) lists distribution `2026.10.10`.
It does not establish a particular installation's files, engine or current realm
behavior. Official UI descriptions identify integration surfaces, not signatures.

[ClassicAPI v1.15.16](https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.16)
remains the stable reference. Unreleased master APIs are not promoted. The
reference now records development-version sentinels, active script-argument mode,
TOC flavor selection and the shared UnitPosition return-shape collision.

[SuperWoW 2.2](https://github.com/balakethelock/SuperWoW/releases/tag/Release)
uses a rolling release asset. Archive provenance and dated extracted DLL identity
stay distinct; a shared global alone does not prove the provider loaded.

[NamPower v4.6.3](https://github.com/Emyrk/nampower/releases/tag/v4.6.3)
still reports runtime `4.6.2`. Both supported v4.6.2 and current released artifact
digests are recorded. The source reference includes a separate unreleased
null-caster fix. Aura stack decreases and complete removal require different handling.

[UnitXP v89-to-v90 source](https://github.com/brues-code/UnitXP_SP3/compare/v89...v90)
has the same Lua dispatcher. This supports documented commands at the retained
v89 floor without certifying every binary. Its version commands identify a PE
timestamp/variant, not an ordinal release. The official v90 DLL differs from the
dated local file previously labeled v90. No identity was invented for that file.

## Validation and remaining evidence

The complete framework unittest suite, documentation/profile checks, ClassicAPI
audit-index check, Python compilation, JSON parsing and whitespace checks are
the acceptance commands for this change. The new fixture scenarios cover required
providers, supported 4.6.2/v89 floors, wrong/unknown versions, x64 rejection,
loader and realm changes, release/version disagreement, selected source and
report boundaries, and source/environment invalidation after tests.

Local result: 140 tests ran successfully, with one Windows native-symlink skip.
Documentation/profile and audit-index checks, Python compilation, JSON parsing
and whitespace checks passed. Before/after controls confirmed the previous
implementation accepted fake version text and assigned build 5875 to an empty
folder; the revised implementation rejects both conclusions.

One Windows native-symlink scenario is skipped where the OS does not permit its
creation. Linux CI exercises the repository separately. Fixture success establishes
framework behavior, not runtime loading, server acknowledgements or native safety.

The v89 binary digest could not be verified through the accessible Codeberg
endpoints. This remains a provenance gap, not a requirement to upgrade to v90.
Source-only maintenance needs no game. Future target-dependent addon work follows
the [target guide](../docs/TARGET_ENVIRONMENT.md), keeping installed files, runtime
checks and exact server-content evidence separate.
