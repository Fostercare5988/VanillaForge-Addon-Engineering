# ClassicAPI v1.15.13 integration audit

Reviewed 2026-09-25. Task: framework maintenance and final integration review.
Objective: reconcile the proposed v1.15.13 update against upstream source and
correct misleading addon-engineering guidance before committing and pushing.
Local starting HEAD: `11da204b310b29448d3bb6e771375866a8d04815`.
The existing nine-file working diff contained the proposed integration.
The user authorized the review corrections and a GitHub push after review.

Scope: framework references, baseline metadata, existing linter/test version
references, and this audit. No addon repository or installed DLL was modified.
VanillaForge remains v3.1, enhanced-client only, server-agnostic, and targeted at
WoW 1.12.1 Build 5875 / Interface 11200. An individual addon's minimum still follows
its consumed capabilities/fixes, not an automatic requirement to declare 11513.

## Verified provenance

The previous reviewed source was v1.15.12 at
`fde3beca9dba18e7327802eb094b5bff81f39d47`. The complete
[v1.15.12...v1.15.13 range](https://github.com/brues-code/ClassicAPI/compare/v1.15.12...v1.15.13)
contains three commits, with no commits exclusive to the base. All eight changed
files and the relevant surrounding implementations were inspected. Earlier
[v1.15.12 audit results](CLASSICAPI_1.15.12_AUDIT.md) were reused.

Official Git objects were checked against GitHub REST tag/release/contents metadata.
The published DLL was downloaded to a temporary directory and hashed locally;
it was not executed or installed.

| Fact | Verified value |
| --- | --- |
| [Release](https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.13) | v1.15.13; not draft or prerelease |
| Annotated tag object | `74b49619eda03ea5adefcb4ef176c16d014a06f4` |
| Peeled source commit | `fa7d71435feabde2c5a08e9175321ca614b6449a` |
| Tagger timestamp | 2026-09-25 16:08:07 UTC |
| Published timestamp | 2026-09-25 16:11:17 UTC |
| Release ID | 396750983 |
| DLL asset ID | 588725535 |
| DLL size | 1,442,304 bytes |
| DLL SHA-256 | `5fc99279f590a3c670cab14afabe19b3d78272c95485ab1c1e5ff2961f6de68b` |

The downloaded hash matches GitHub's asset digest and the proposed snapshot.
This verifies artifact identity, not a reproducible build or runtime correctness.

| File at v1.15.13 | Git blob SHA, independently checked against the contents API |
| --- | --- |
| `docs/API.md` | `23794ac2e8335aae7957d80f5ccecd4228ea34f0` |
| `README.md` | `db401f0578060c3aa52364d533bbced570235fea` |
| `src/cvar/Temp.cpp` | `3810691c26dc7e91ca2af75ad615c7e32945d58f` |
| `src/container/SortBags.cpp` | `b6d77b3b7bc6e8a9b2361fa4bfbcf1d2117acf7a` |
| `src/nameplate/Events.cpp` | `cebb4ac06c43f85dd907f74cd19b908bbd540897` |

The unchanged bag-event dispatcher was also read from the pinned Git tree:
`src/bag/UpdateDelayed.cpp`, blob `7836a3bfd3632c59ff6b12514bbe2aa56fc4fb81`.

## Complete change classification

Classes: 1 new addon-facing capability; 2 addon-facing semantic/runtime change;
3 documentation clarification; 4 internal plumbing; 5 irrelevant to addon engineering.

| Commit | Change | Classification |
| --- | --- | --- |
| [`6000df8009857e8e137a1f73621412929218db14`](https://github.com/brues-code/ClassicAPI/commit/6000df8009857e8e137a1f73621412929218db14) | SetTempCVar/RemoveTempCVar, README/API docs, factory persistence argument and offsets | 1, 3, 4 |
| [`3467513df9dbbcc0bfd80464a4b3129019a2b406`](https://github.com/brues-code/ClassicAPI/commit/3467513df9dbbcc0bfd80464a4b3129019a2b406) | Existing bag/bank sort gains inventory-type grouping instead of quality-tier gear categories | 2, 3; comparator storage/ranking is supporting implementation |
| [`fa7d71435feabde2c5a08e9175321ca614b6449a`](https://github.com/brues-code/ClassicAPI/commit/fa7d71435feabde2c5a08e9175321ca614b6449a) | Retry unannounced nameplates when event prerequisites become available | 2; deferred snapshot bookkeeping is supporting implementation |

No removed APIs, new events, changed event payloads, or new loader requirements
were identified. The sort APIs keep their existing signatures. No independent
class-5 change appears in this range. Macro and weak-table semantics from the
previous baseline are unchanged.

## Review corrections and canonical placement

[SOURCE-VERIFIED] The detailed contracts belong in `CLASSICAPI_MASTER_REFERENCE.md`.

- Corrected gear ordering: class precedes inventory-type rank; armor shields and
  held-offhands precede head items, neck follows feet, and subclass precedes
  quality. Poor-quality gear remains junk. Recorded the exact rank table and the
  remaining count/item-ID tie breakers rather than inventing a simplified order.
- Removed the claim that native sorting eliminates every addon's custom ordering.
  Upstream explicitly supports alternative ordering through native movement APIs.
  Bagnon feature requirements and integration remain a separate addon task.
- Clarified asynchronous behavior, bank/data constraints and view updates.
  `BAG_UPDATE_DELAYED` is emitted before the C++ subscribers that may start
  placement, so it cannot certify completion of the sorting operation.
- Corrected temporary-CVar ownership: the snapshot is the live value before the
  first override, and replacement is detected through string comparison. An
  ordinary same-value SetCVar does not release the override; remove it before an
  explicit persistent SetCVar. Repeated sets, nil, errors, no return values,
  process-global storage and overlapping-owner limitations are documented.
- Qualified nameplate retries: an unclaimed event is not proof of slot exhaustion.
  Retry depends on continued plate visibility and available prerequisites, not
  an unconditional next-tick or subscriber-delivery guarantee. Upstream expressly
  says the dropped-slot scenario was not verified in game.
- Replaced nonexistent `src/cvar/CVar.cpp` and `src/container/Sort.cpp` references
  with the actual paths and independently verified blobs.

Known Pattern decision: remove the proposed KP-57 and KP-58. Their API details can
be represented fully in the canonical reference; KP-58 also duplicated KP-35 and
introduced unmeasured performance claims. Extend existing KP-35 only with the
requirement-dependent native-sort choice and the concrete completion-event caveat.
No new pattern promotion is justified. Other patterns remain unchanged.

The verified baseline/provenance changes in AGENTS, the system prompt, README,
engine reference, UPSTREAM_VERSIONS.json and the linter header are retained, as is
the 11513 test case proving that addon minima are not forced to the baseline.
README now links this audit while preserving the previous audit. The upstream
checker requires no implementation change; no new linter heuristic is warranted.

## Validation and integration review

| Check | Result |
| --- | --- |
| Full regression suite (`python -m unittest discover -s tests -p "test_*.py" -v`) | PASS: all 40 tests. |
| Python compilation of both tools and both test modules | PASS. |
| JSON validation and validation-workflow canonical/stale-file checks | PASS. |
| Strict linter CLI on a temporary addon fixture with an older valid minimum and a bag-update listener | PASS: zero errors/warnings. |
| ClassicAPI-only upstream checker during review, without suppressing drift failures | CURRENT, exit 0; pinned commit and both documentation blobs matched. The snapshot is unchanged by the corrections. |
| Full upstream checker rerun before commit | Incomplete, exit 1: GitHub HTTP 403 API rate limit. No all-component CURRENT claim is made. |
| Complete cumulative diff, whitespace and stale-baseline review | PASS. Remaining v1.15.12 references describe history, feature introduction or regression inputs. Removed-path/KP mentions survive only as historical corrections in this audit. |

Integration review: source/evidence, dependency policy, knowledge placement and
repository scope PASS. No new measured-performance claims or automatic addon
minimum bump. The previous macro/weak-table knowledge is retained. Tests exercise
framework tooling policy, not the ClassicAPI C++ implementation or gameplay.
TOC/load graph, addon SavedVariables and deployed DLL replacement are not affected.
Ready for the authorized maintenance commit/push with the upstream-checker rate
limit disclosed. Runtime checks below remain outstanding.

## Runtime requirements

[UNVERIFIED - TEST FIRST] No local WoW runtime verification was performed. If the
DLL is replaced in the client, fully exit and restart WoW.exe; `/reload` cannot
load the replacement native DLL.

1. Sorting: check mixed gear slots, subclasses and qualities, poor-quality gear,
   partial stacks, specialty/excluded bags and both fill directions. Check missing
   item data immediately after login and retry after data arrives. For bank sorting,
   test open/closed bank and partially cached stack limits. Observe intermediate
   bag updates without publishing completion or reentering sorting on each event.
2. Temporary CVars: use a suitable writable CVar with a known baseline; exercise
   repeated temporary sets, removal, a different-value SetCVar and same-value
   SetCVar. Check persistence after an unrelated config flush, reload and restart.
   Verify remove-then-SetCVar for an intentional persistent change and coordinate
   overlapping modes; callbacks may normalize requested values.
3. Nameplates: check normal CREATED/ADDED ordering, visibility churn and reload.
   If a test environment can induce the unclaimed-event case, verify later
   announcement without token/observer leakage or unmatched REMOVED. Both local
   and upstream failure-path runtime verification remain outstanding.

## Retrospective

The prior audit established correct binary/version provenance but found inaccurate
semantic guidance. Reading the comparator, event dispatcher and override ownership
code resolved those issues without reopening unrelated framework architecture.
Canonical references plus one existing pattern suffice; no extra API catalog or
new framework lesson is needed. Source verification and runtime testing remain
explicitly separated. Commit/push authorization applies to this maintenance
checkpoint, not to addon changes, a tag, or a release.
