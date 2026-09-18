# ClassicAPI v1.15.10 through v1.15.12 integration audit

Reviewed 2026-09-18. Task type: **framework maintenance**.

## Task boundary

Objective: update VanillaForge's current environment/reference baseline to v1.15.12
without discarding valid v1.15.10 knowledge or forcing every addon's minimum upward.
Starting checkpoint: `d122f1dba968a57493a58ef29f473e4456fcba16`.
`AGENTS.md` already had the unstaged v1.15.12 baseline change at entry; preserved.

References used: AGENTS, the authoritative system prompt, agent bootstrap/task/review/
retrospective templates, and relevant ClassicAPI, engine, macro-pattern, tooling,
test, and validation-workflow sections. No whole-framework rediscovery.

Invariants: framework remains v3.1, WoW 1.12.1 Build 5875 / Interface 11200,
enhanced-client only and server-agnostic. No addon edits, Agent Layer redesign,
stock-client fallback, DXVK Lua dependency, or performance claim.
Git authorization: **none** for branch creation, staging, commits, pushes, tags,
or releases. Stop after validation and the integration report.

## A. Independently verified upstream provenance

Official repository: [brues-code/ClassicAPI](https://github.com/brues-code/ClassicAPI).
Audited the full [v1.15.10...v1.15.12 range](https://github.com/brues-code/ClassicAPI/compare/v1.15.10...v1.15.12),
both release intervals, every commit's changed paths, and the complete source/docs
delta. Local Git objects show an ancestor range with seven added commits and no
commits exclusive to the base. No macro changes are hidden by endpoint cancellation.

Annotated tags were read from a fresh official bare clone, then independently
cross-checked through GitHub REST tag refs and tag objects. Release pages also
identify the same target commits. Tag-object IDs are **not** commit IDs.

| Release | Annotated tag object | Peeled source commit | Published (UTC) |
| --- | --- | --- | --- |
| v1.15.10 | `44666109705b3d0bf62f4c234177acd8117d2bbc` | `bbefdb847d5d48a06fabca250e8a205b05ebab18` | 2026-09-17 04:36:45 |
| [v1.15.11](https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.11) | `a9155fa1538808807cf2fab73d2be32e34ff37d6` | `452f3c14fc3270420355edecd82e27868fc19d63` | 2026-09-17 19:27:29 |
| [v1.15.12](https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.12) | `a7719ec901b8a232e9c52330fdb387fe800904c3` | `fde3beca9dba18e7327802eb094b5bff81f39d47` | 2026-09-18 04:44:15 |

v1.15.11 source commit time: 2026-09-17 19:04:59 UTC; tagger time:
19:05:16 UTC. v1.15.12 source commit time: 2026-09-18 04:39:43 UTC;
tagger time: 04:40:28 UTC. Publication is later than either. Both releases are
non-draft and non-prerelease; GitHub release IDs are 391000698 and 391221950.

Downloaded the [official v1.15.12 ClassicAPI.dll](https://github.com/brues-code/ClassicAPI/releases/download/v1.15.12/ClassicAPI.dll)
to a temporary audit directory without loading or executing it. Locally computed
SHA-256 matches both GitHub's asset digest and the supplied prior observation:

```text
a2034799f5c03bb5e2ec9a0721a31b2dd024e7cd90bd9c56248383a948495677
```

Asset ID: **571828024**; size: **1,437,184 bytes**; uploaded/updated
2026-09-18 04:44:14 UTC. Hash agreement verifies the downloaded published artifact;
it does not claim a local reproducible build or an in-client test.

Git tree blob IDs below were independently cross-checked through GitHub's contents
API pinned to the v1.15.12 source commit:

| File | v1.15.12 Git blob SHA |
| --- | --- |
| `docs/API.md` | `0ab67379ec55e5e9ebe92595b40611cc5d482164` |
| `README.md` | `7611ff488b103ed6cda3258343e85cc5ccdef8ba` |
| `src/macro/ShowTooltip.cpp` | `24a8aa1158c5c93754b10e4d263c3dd6a90047e0` |
| `src/table/Length.cpp` | `5c3f9dfdbedd34ae016caefd038e3003facf6b28` |
| `src/Offsets.h` | `8e094ab16ebe3aa811cdbdf54b9787db0e9863e2` |
| `src/Game.cpp` | `2ab8ea5303263eb28c41f3a05d8bc43491dc0a07` |
| `src/Game.h` | `3fa23477c7d77281813b2b636d2296814d2ab50f` |
| `src/luaenv/Fenv.cpp` | `087f8c154ba70995f06ddba49538c711d947e40e` |

At v1.15.11, API.md remains `ee441d9ce1c67fc86ea0c3bb02da80d4f3ba49de`
and Length.cpp remains `7e817ff26d583ffa498def8d71c2051419bae37a`;
ShowTooltip.cpp already has the final blob above. README is unchanged across the
entire range (last changed by `0296e0e5a4f0a4156bbdee2854abb6ee1556aa19`).
API.md's previous content commit was `bbefdb847d5d48a06fabca250e8a205b05ebab18`;
its only new content commit is `fde3beca9dba18e7327802eb094b5bff81f39d47`.

## B. Complete change map

Classes: **1** new addon-facing capability; **2** addon-facing semantic/runtime fix;
**3** documentation clarification; **4** internal implementation/plumbing;
**5** irrelevant to VanillaForge addon engineering.

| Commit | Release interval | Change and classification |
| --- | --- | --- |
| `2fff9564b26b7aaab5ae2166cfcf47ad21451d51` | .10 -> .11 | Direct release-tag push to Gitea mirror; **4**, no Lua/API consequence (**5** for addon engineering). |
| `8c941c757d1bcb7e605a331537f9ecee7dedf0fa` | .10 -> .11 | Mirror authentication header change; **4/5**. |
| `a5bb3823fb9f2bc5ea438ff3ef7c259e3d300742` | .10 -> .11 | Temporary mirror authentication diagnostic; **4/5**. |
| `7a08199ba57669bc5448946e04fc70676e76d84d` | .10 -> .11 | Replace diagnostic with end-to-end dry-run push probe; **4/5**. |
| `6bb12c3c12045ead59e6400be01973df46be3dce` | .10 -> .11 | Remove Gitea mirror workflow, diagnostic, and build mirror job; **4/5**, GitHub remains publication source. |
| [`452f3c14fc3270420355edecd82e27868fc19d63`](https://github.com/brues-code/ClassicAPI/commit/452f3c14fc3270420355edecd82e27868fc19d63) | .10 -> .11 | Managed macro protection during spell-unlearn cleanup; **2**. Hook/address definitions and reentrancy/cache mechanics: **4**, retained only as evidence of the semantic fix. |
| [`fde3beca9dba18e7327802eb094b5bff81f39d47`](https://github.com/brues-code/ClassicAPI/commit/fde3beca9dba18e7327802eb094b5bff81f39d47) | .11 -> .12 | Weak-value stored-length exception: **2**. API.md exception/count update: **3**. Shared native GetMetatable binding and Fenv reuse: **4**, no new Lua function. |

**Class 1: none.** No new public function, namespace, event, parameter, or return
signature is introduced. The nine endpoint-changed files are the two CI files,
API.md, and the six source files listed in the blob table. The temporary diagnostic
workflow appears only in intermediate history and was included in the audit.

### Complete macro scope and retained lineage

[SOURCE-VERIFIED] Exactly one macro implementation commit lies in the requested
range; v1.15.12 does not further modify macro code. Its consequences include all of:

1. Preventing persisted action-bar removal when a managed display resolution names
   an unlearned spell, even if the macro's actual cast remains usable.
2. Protecting both parsed non-foreign `#showtooltip` / `#show` directives and
   externally published `C_Macro.SetMacroDisplay` entries. An unmanaged macro keeps
   stock cleanup; no-directive macros qualify only through external management.
3. Protecting a bare managed `#showtooltip` even when its actual cast is unlearned.
4. Suppressing catch-up during reentrant `ACTIONBAR_SLOT_CHANGED` reads while the
   sweep runs; restoring cache fields without unnecessary repaint; allowing later
   directive evaluation to react to changed spell knowledge. External display
   publishers retain responsibility for publishing changed answers.

This concerns macro **action-bar placement**, not deletion of saved macro text.
The full surrounding source and earlier history were checked, rather than treating
the fix's subject line as the whole macro contract. The following commits are
already ancestors of v1.15.10, so are preserved context, not .11/.12 additions:

| Earlier commit | Existing macro behavior |
| --- | --- |
| `36c367a6d672b20b18a6c0bf5ef5a65da67c76df` | Native directives, conditional commands, addon display API. |
| `3191c4dcfce0493074dede5f1cbd1bcefa21c204` | Foreign conditions remain owned by the other macro addon. |
| `d9565fbe1fb22755692f0c4237a54143d34d5b80` | Display handling when the client owns macro tooltips. |
| `0ba73b84571f5bc83d86215dff2fc9631be208b2` | Preserve GetMacroInfo's stored icon; expose displayed icon separately. |
| `3d91ae0f91cd329acc35189811d3c33f43e6f760` | Explicit spell IDs display even if unlearned. |
| `4f99a1ed95071081ac79fc571a1befa285bebc57` | Castsequence/castrandom/userandom. |
| `bf79ee1d9300d6e0bfd4b3ec6a9e11daf6495f2e` | Stopmacro. |
| `dfbba225d21d75676088414a6ae7acbfccfc7598` | Correct loose/MPQ icon enumeration split. |

KP-53's resting left-button conditional semantics and KP-54's empty-string
out-of-range icon result are unchanged. Their parser/icon paths are unchanged in
this range. KP-53 is also supported by current MacroOptions.lua/API.md; KP-54 is
preserved previously verified engine knowledge, with no change in this range
that supersedes it. No new disassembly or local runtime verification is claimed.

### Weak-value semantics and evidence boundary

[SOURCE-VERIFIED] `HasWeakValues` reads the metatable's raw `__mode`, checks that
it is a string, and looks for `v`. `LuaLGetN_h` returns the stored count for such
tables before trailing-nil-mark/border healing. A nil at the stored final index
cannot establish stale writer state because the collector can clear weak values.
This is an exception for weak values, not weak keys alone or every sparse table.

The source describes Compost-2.0's `secondarycache`: when slots 1 and 3 are collected
and slot 2 remains live, the old border search could report zero and cause
`table.remove(cache, 2)` to return nothing. Retaining the count fixes that failure.
Explicit numeric `n`, deliberate two-argument nil appends, ordinary stale-table
healing, and supported `table.setn` behavior remain. The independent `#` path in
`src/luasyntax/Transpile.cpp` calls `Table::Border::Find`; it is not this stored-count
exception. Mechanical getn-to-# rewriting is therefore unsafe as a blanket rule.

The upstream commit reports an in-game three-slot reproduction now yielding getn 3
and the live removal result, and reports the Compost errors gone. Record this as
**upstream-reported empirical verification**. No [EMPIRICALLY VERIFIED] claim is
made for the user's client or for testing by VanillaForge/Niko.

## C-D. Canonical placement and affected files

- `CLASSICAPI_MASTER_REFERENCE.md`: canonical macro/runtime behavior, current
  snapshot, evidence attribution and prior knowledge preservation.
- `ENGINE_REFERENCE.md`: baseline and short cross-reference only; no duplicate
  ClassicAPI runtime catalog.
- `VANILLAFORGE_SYSTEM_PROMPT.md`, `README.md`: current baseline and explicit
  distinction from individual addon minimum dependencies. Framework stays v3.1.
- `UPSTREAM_VERSIONS.json`: current commit/docs snapshot and release artifact
  provenance. `minimum_version` describes the framework environment; the added
  scope note is metadata, not an addon requirement or checker rule.
- `tools/vanillaforge_linter.py`: remove the baseline-only minimum warning and
  blanket getn/setn obsolescence advice; those require semantic evidence that the
  scanner does not possess. Guard presence remains reported; no new speculative
  weak-table detector.
- `tests/test_linter.py`: regress intentional table-length use and older valid
  addon minima; retain meaningful suppression tests against active rule A4.
- This audit: provenance, full classification, focused runtime checks, review and
  retrospective. `AGENTS.md`'s pre-existing baseline edit remains untouched.

`tools/check_upstream.py` needs no code change: its existing version/commit/docs
comparisons consume the updated snapshot. It does not validate DLL hashes or the
extra release metadata; those were independently verified during this audit.

## E. Known Pattern decision

**No KP change required.** Both new semantics are general, source-verified, likely
to recur and material to addon decisions. However, they can be represented fully
in the canonical macro/runtime reference, so the final promotion gate fails.
KP-53/KP-54 remain valid; KP-55's v1.15.10 capability floor is intentionally retained.

## F. Validation and integration review

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -p "test_*.py" -v` | PASS: all 24 tests. |
| `python -m py_compile tools/vanillaforge_linter.py tools/check_upstream.py tests/test_linter.py` | PASS. |
| JSON parse, canonical-file presence, obsolete filename checks from validation workflow | PASS. Local Python: 3.14.4; hosted workflow uses 3.13 and was not run here. |
| Strict linter CLI on temporary Lua/TOC fixture with minimum 11510 and weak-value getn/setn use | PASS: zero errors/warnings. |
| `python tools/check_upstream.py --component classicapi --verbose` | CURRENT; exit 0. Version, default-branch commit and both tracked documentation blobs match. |
| `python tools/check_upstream.py --verbose` | REVIEW REQUIRED for unrelated NamPower 4.6.2 -> 4.6.3 drift; ClassicAPI CURRENT. SuperWoW reports CURRENT with no stored source snapshot; UnitXP skipped because no repository is configured. No other baseline changed. |
| `git diff --check` and complete cumulative diff review, including the new audit | PASS; no unrelated changes. |
| Repository-wide stale-baseline search | PASS: remaining .10 mentions are history, version-encoding examples, regression inputs or KP-55's actual capability floor. |

Integration review: correctness/evidence and dependency policy PASS; ownership,
performance and persistence review limited to the documented source semantics.
No measured performance claims. Repository scope PASS. Runtime remains unverified.
Status: **READY for the scoped maintenance checkpoint**, with the unrelated
NamPower drift disclosed rather than silently updating another component.

Final repository state: branch `main`, HEAD remains
`d122f1dba968a57493a58ef29f473e4456fcba16`, index empty. Seven tracked files edited
by this task, one new audit file, and the pre-existing AGENTS baseline edit:

```text
 M AGENTS.md
 M CLASSICAPI_MASTER_REFERENCE.md
 M ENGINE_REFERENCE.md
 M README.md
 M UPSTREAM_VERSIONS.json
 M VANILLAFORGE_SYSTEM_PROMPT.md
 M tests/test_linter.py
 M tools/vanillaforge_linter.py
?? docs/CLASSICAPI_1.15.12_AUDIT.md
```

TOC/load graph and SavedVariables: not applicable to this framework-only update.
No addon/runtime files or dependency declarations were changed. The reviewed
v1.15.10 event/aura/swing/icon knowledge remains unless explicitly extended above.

## G. Focused runtime requirements

[UNVERIFIED - TEST FIRST] No target WoW client was run for this maintenance task.
Use the verified v1.15.12 DLL in the enhanced Build 5875 client and enable Lua errors.

1. Before unlearning a test spell, place on the bar a conditional explicit-ID
   `#showtooltip` macro whose cast stays learned, a bare directive whose cast will
   be unlearned, a `#show` macro, and a no-directive control. Verify managed entries
   survive the unlearn/respec and reload/relog; check cast availability, greying,
   icons and tooltips independently of placement. Confirm unmanaged controls retain
   stock behavior; do not infer saved-macro deletion from an emptied bar slot.
2. If an addon publishes macro display, exercise value/false/nil ownership,
   foreign conditions, and spell unlearning with multiple affected bar slots.
   Check event-driven readers do not cause mid-sweep loss, and the publisher
   updates its answer. Recheck resting/click button conditions and stored/displayed
   icons as adjacent regressions when testing a macro addon.
3. Build a three-slot weak-value table using `table.insert`, retaining a strong
   reference only to slot 2. After GC demonstrably clears 1 and 3, verify
   `table.getn(t) == 3` and `table.remove(t, 2)` returns that live object. Repeat
   with raw modes `v` and `kv`; compare ordinary and weak-key-only tables. A
   `#t` result is not evidence for the stored-length behavior.
4. Exercise an actual Compost-2.0 recycling consumer through repeated GC/reuse,
   checking for `table index is nil`; also check explicit numeric `n`, intentional
   two-argument nil append, and cleared/reused ordinary-table behavior. Static
   Python tests validate linter policy, not this C++/WoW runtime fix.

## H. Recommended direct-main checkpoint

```text
chore: integrate ClassicAPI v1.15.12 framework baseline and semantics
```

Recommendation only. No staging, commit, push, tag, release or branch creation.

## Retrospective

Task/result: bounded ClassicAPI maintenance; canonical source/docs changes and
tooling policy reconciled without addon work or a framework version bump.
Useful strategy: full Git range plus independent REST metadata and local artifact
hashing exposed the exact two semantic fixes and kept earlier macro work correctly
attributed. Existing scanner policy needed correction once the runtime contract
was inspected. No broader framework audit was necessary.

Reusable lesson gate: source-first semantic review is general, verified, recurrent
and important, but already required by the framework. No additional framework
lesson or Known Pattern is proposed.
