# ClassicAPI v1.15.16 integration audit
Date: 2026-10-01. Upstream integration review and framework baseline maintenance.

## Provenance
Official release: https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.16
Complete range: https://github.com/brues-code/ClassicAPI/compare/v1.15.15...v1.15.16
Previous commit: 71805db62f1e8a154477033dc1f50960c535af8b.
Annotated tag ec18cc1ebacf39d79aaa37d9411f10719ef29256 peels to 7ccbbaaf68bcde6b29b71806981d0338e0577189.
Published 2026-09-30T20:04:08Z. DLL asset 601705195: 1,449,984 bytes.
SHA-256 e34886fb9725b9059375a5c37bff81ce220633c4e2c39719ef3223a6b8fc703d.
Actual downloaded bytes hashed and matched GitHub asset digest; DLL not installed.

### Unreleased master excluded from stable baseline
Commit 917b15640e2bdc2c8f24e0e0d4d520514d76ff52 (`feat(quest): add C_QuestLog.GetInfo and C_QuestLog.GetQuestLogTitle`)
committed 2026-09-30T20:08:38Z is post-v1.15.16 on default branch `master`.
It is unreleased and explicitly excluded from this stable release baseline.

## Complete change map
- 7ccbbaaf68bcde6b29b71806981d0338e0577189: `fix(compat): stop Turtle's Toggle Movement button erroring`.
  In bundled synthetic addon `AddOns/!!!ClassicAPI/Util/AddOnCompat.lua`, when `Turtle_GroupUI`
  is loaded via `EventUtil.ContinueOnAddOnLoaded`, wraps the global function `GroupFrame_ToggleMovement(state)`.
  Turtle's Options frame sets `GroupFrame_ToggleMovement(state)` directly as the "Toggle Movement"
  button's `OnClick`. Under modern script dispatch, the button widget frame (`self`) is passed as
  the first argument. The handler expects `nil` (to toggle based on current mouse state) or a
  numeric state (0 or 1); passing a frame table caused `1 - state` arithmetic errors at
  `Turtle_GroupUI.lua:409`. The wrapper sanitizes non-numeric arguments to `nil` before calling
  the original function.
- Public Lua API changes: none.
- Event changes: none.
- Return signature changes: none.
- ABI / engine hook changes: none.
- Tracked reference documentation (`README.md`, `docs/API.md`): unchanged from v1.15.15.

## Portfolio decisions
- Framework baseline advances to ClassicAPI v1.15.16+.
- Addon minimum-version guards remain capability-specific and unchanged (no addon repository modified).
- No new Known Pattern promoted: 1.12 callback vs. modern script argument semantics are already covered by framework principles; this is an isolated upstream addon compatibility wrapper.
- No DLL installation performed.

## Source blobs
| File | Blob SHA at v1.15.16 | Status |
| --- | --- | --- |
| `AddOns/!!!ClassicAPI/Util/AddOnCompat.lua` | 4eaac6bf5175c59a57ee47dbcce9ee89f04090e5 | Modified (+19 lines) |
| `README.md` | cf885d857ce6fedbe1559a01cba1c3ea25e2a35c | Unchanged from v1.15.15 |
| `docs/API.md` | a162057257ebe44c13e512d940eedf994c351a35 | Unchanged from v1.15.15 |

## Runtime requirements and retrospective
[SOURCE-VERIFIED] Official source and commit diff verified against GitHub repository.
[UNVERIFIED - TEST FIRST] DLL not installed into game client. If deployed, verify CLASSIC_API_VERSION==11516 and Turtle_GroupUI Options frame "Toggle Movement" button click behavior without error.
Retrospective: Single compatibility fix in bundled Lua helper; no framework pattern promotion justified.

## Validation outcome
Framework regression suite passes. Upstream configuration and audit index validated. Stale reference classification completed.

## Stable-baseline recheck and stack contracts — 2026-10-15

The official latest-release metadata still identifies v1.15.16, with the same
annotated tag, peeled commit, DLL asset ID, size and SHA-256 digest recorded
above. The current `master` branch remains at
`917b15640e2bdc2c8f24e0e0d4d520514d76ff52`; its unreleased quest additions remain
excluded from the stable baseline. GitHub asset metadata was rechecked; no DLL
was downloaded, installed or executed during this recheck.

Reviewed existing stable-version contracts omitted from the master reference:

- `src/api/Version.cpp` (blob `33c3ea05a268203cc96c0056557a497a141843a1`)
  publishes the version global. `CMakeLists.txt` (blob
  `830adb8a01e930faa3016184faface04b67b8ff6`) gives unstamped developer builds the
  value `99999999`; passing a minimum gate does not prove stable artifact identity.
- `docs/API.md` retains the recorded stable blob and documents the global
  script-argument toggle. The active setting must be checked before depending
  on positional handlers; a DLL version alone does not prove it is enabled.
- `src/unit/TokenExtensions.cpp` (blob
  `1bb9fa98dc16defa0e8a8c75d8ef96225b87b61f`) deliberately defers raw GUID input
  to SuperWoW when `SuperWoWhook.dll` is loaded. Shared GUID-aware APIs cannot
  identify the loaded provider or establish that all required DLLs are active.
- `src/unit/Position.cpp` (blob
  `156568032d2a419a7d3fedc006b3d7651bc9d975`) and the stable API documentation
  establish ClassicAPI's position returns. The documentation explicitly warns
  that SuperWoW defines the same global with a different return shape and the
  last registrant wins. The master reference now records this collision and
  requires verification on the combined target stack before using coordinates.

These clarify pre-existing stable behavior; they are not new v1.15.16 APIs or
a reason to raise addon guards. Canonical details are in master-reference
sections 2, 4.4 and 69. [SOURCE-VERIFIED] means the pinned upstream contracts;
[UNVERIFIED - TEST FIRST] remains applicable to the active OctoWoW client,
registration order, script setting and addon runtime results.
