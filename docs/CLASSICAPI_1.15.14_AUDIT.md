# ClassicAPI v1.15.14 integration audit

Reviewed 2026-09-26. Task: framework maintenance and integration review.
Objective: independently verify and integrate v1.15.14 against the reviewed
v1.15.13 baseline. Starting VanillaForge HEAD:
`972f84b6cfef0598ffa66b9acea132e9594329c3` (clean working tree).
Scope: framework knowledge, baseline metadata and existing policy tests.
No addon repository, installed DLL, framework identity or Agent Layer redesign.
Earlier audits remain authoritative for unchanged knowledge; no repeat full audit.

## Verified provenance

The complete [v1.15.13...v1.15.14 range](https://github.com/brues-code/ClassicAPI/compare/v1.15.13...v1.15.14)
contains one commit, changing three files. The previous source commit is
`fa7d71435feabde2c5a08e9175321ca614b6449a`. The full diff and surrounding icon
enumeration/display implementation were inspected. Fetched official Git objects
were independently checked against GitHub REST tag and contents metadata.
The official DLL was downloaded to temporary storage and hashed, not executed.

| Fact | Verified value |
| --- | --- |
| [Release](https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.14) | v1.15.14; not draft or prerelease |
| Annotated tag object | `407a4c616a2828a70c9b5b736aa753ec9a240029` |
| Peeled commit | `7707127d5f1293ed9f1c15bd1e13e4b37254bf3d` |
| Commit timestamp | 2026-09-26 05:31:19 UTC |
| Tagger timestamp | 2026-09-26 05:32:34 UTC |
| Published timestamp | 2026-09-26 05:36:24 UTC |
| Release / DLL asset IDs | 397106642 / 590018427 |
| DLL size | 1,442,816 bytes |
| DLL SHA-256 | `18e25f0d120ff0fb7c1af8eb268eed30177d2d5eccd3169160b219ea1d24dc8f` |

The local hash matches GitHub's asset digest and the submitted investigation.
This establishes binary identity, not a reproducible build or gameplay validation.

| File | Verified Git blob at v1.15.14 |
| --- | --- |
| `docs/API.md` | `aeeb8c23d3848caa8f29f8cada0963619f27dcad` |
| `README.md` (unchanged) | `db401f0578060c3aa52364d533bbced570235fea` |
| `src/macro/Icons.cpp` | `5ad755eaf93c13bc4fea5e353f6ea40fea23e964` |
| `src/Offsets.h` | `e625357c0c7fc08b386d7522e41ea8bfc83684a5` |
| `src/macro/IconPath.cpp` (unchanged) | `40cd511660c76ec48ec8e22c96fad58c5cf1e7c2` |

## Complete change classification

The sole [commit](https://github.com/brues-code/ClassicAPI/commit/7707127d5f1293ed9f1c15bd1e13e4b37254bf3d)
is `fix(macro): add the question-mark icon to the macro icon list`.

| Change | Classification |
| --- | --- |
| Seed question mark on empty-list loading and put it first after native sorting/deduplication | 2: addon-facing semantic/runtime fix |
| API documentation adds question-mark exception and first-entry contract | 3: documentation clarification |
| Loader hook, synthetic callback record, array rotation and explanatory offset comments | 4: supporting implementation/plumbing |

No new public API capability (class 1), removed API, changed signature, new event,
event payload change, loader dependency or independent class-5 change was found.
Bag sorting, temporary CVars, nameplate delivery, macro unlearn protection and
weak-valued-table stored-length semantics are unchanged.

## Canonical integration and review corrections

[SOURCE-VERIFIED] The macro-icon section of `CLASSICAPI_MASTER_REFERENCE.md` is
the canonical home. The framework baseline advances to v1.15.14, while addon
minimums still depend on the APIs/fixes each addon consumes. No blanket 11514 guard.

- The Lua first-entry contract follows the empty-list initialization hook. It is
  not empirical proof of compatibility with every patched client or hook order.
- The new seed does not enter the loose-icon capture bucket. The four independent
  append-to-table enumerators retain their source/category ordering contracts.
- The question mark enables the existing dynamic icon rule. Explicit non-question
  icons, stored `GetMacroInfo` and displayed `C_Macro.GetMacroIcon` stay distinct.
- Counts/indices can change; therefore the proposed "zero breaking changes"
  statement was rejected. Numeric indices are not stable cross-version identity.
- Corrected the old fixed-count/Ability-and-Spell-only reference description and
  its claim that only `GetNumMacroIcons()` initializes enumeration: the four
  ClassicAPI enumerators already call `EnsureLoaded()` before this release.
- `0x00565880` in the upstream comment describes the 3.3.5 comparison loader;
  the actual 1.12 hook target in `Offsets.h` is `0x004F0090`. These addresses are
  provenance context, not addon-facing API guidance.

Files: AGENTS, system prompt, engine-reference baseline, README, version JSON and
linter header are synchronized; the master reference records semantics and source
snapshot; the existing minimum-version policy regression now also covers 11514.
The upstream checker needs no implementation change. No new linter heuristic.

Known Pattern gate: the index hazard is general, source-supported and potentially
recurring, and matters to addon engineering, but the canonical macro reference
sufficiently represents it. No KP promotion or change is required. KP-53 and
KP-54 remain valid, including KP-54's empty-string bounds check.

## Validation and final integration review

- Full regression suite: all 40 tests passed, including older addon minimums.
- Both tools and both test modules compile; JSON and canonical-file checks pass.
- Strict linter CLI on a temporary addon fixture: zero errors/warnings.
- Full upstream checker completed: ClassicAPI, SuperWoW and UnitXP CURRENT.
  Exit 1 reports pre-existing NamPower version drift (4.6.2 to 4.6.3), with its
  stored commit and blobs unchanged. This separate component was not updated.
- Complete cumulative diff, whitespace, status and stale-baseline review pass.
  Remaining older version mentions are history, feature floors or test fixtures.
- Correctness/evidence, dependency policy and repository scope pass. No measured
  performance claim. TOC/load graph and SavedVariables are not affected. Earlier
  v1.15.10 through v1.15.13 knowledge is preserved except the icon-reference
  corrections explicitly described above. Local changes are ready for review.

## Runtime requirements

[UNVERIFIED - TEST FIRST] No local WoW testing was performed. Upstream source
comments describe intended deduplication and prior-client behavior; these are not
Niko-local empirical evidence. After replacing the native DLL, fully restart
WoW.exe; `/reload` does not load a new DLL.

1. On the supported enhanced client, initialize enumeration and confirm entry 1
   is the question mark and selectable in the macro picker.
2. Verify question-mark `#showtooltip` / `#show` spell/item display on the action
   bar and drag cursor, plus an explicit fixed-icon control. Confirm stored and
   displayed icon getters remain distinct.
3. With custom assets or an existing question-mark injection, check duplicate
   suppression and selector mapping. Confirm no synthetic loose-icon entry and
   no persisted numeric-index assumptions in consuming addon code.

## Retrospective

The complete one-commit diff and adjacent loader/display code were sufficient;
no broader framework or addon discovery was needed. The important correction was
to distinguish unchanged signatures from changed enumeration indices and to
verify loading behavior beyond the release note. Existing canonical placement
and evidence rules cover the lesson; no new framework pattern is warranted.
