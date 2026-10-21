# ClassicAPI v1.15.15 integration audit
Date: 2026-09-27. Upstream integration review and bounded addon compatibility changes.

## Provenance
Official release: https://github.com/brues-code/ClassicAPI/releases/tag/v1.15.15
Complete range: https://github.com/brues-code/ClassicAPI/compare/v1.15.14...v1.15.15
Previous commit: 7707127d5f1293ed9f1c15bd1e13e4b37254bf3d.
Annotated tag bda6c8288abb2347a69a84e07c4882c55992c6cf peels to 71805db62f1e8a154477033dc1f50960c535af8b.
Published 2026-09-27T05:13:13Z. DLL asset 592197823: 1,448,960 bytes.
SHA-256 ec1624eb6c9fcd4dd92570b911c0be293cc6215dc202266a5429156f81d079a2.
Actual downloaded bytes hashed and matched GitHub asset digest; DLL not installed.

## Complete change map
- 46dc198505319ee07c41f8ad43bbe0888dffbc9d: new GetUnit capability; runtime GetUnitGUID name-resolution extension; token plumbing in Attributes/SetEvents/Offsets/header.
- 85619155f8632cd7f7d33881118b97a480aaf397: new native equipment-set pickup/action capability and WEAR_EQUIPMENT_SET; changed action/cursor returns; action tooltip/name/icon/usable/persistence semantics. Locked-item check extracted unchanged into shared helper, retaining missing-item semantics.
- 71805db62f1e8a154477033dc1f50960c535af8b: README API/event documentation.
- API docs clarify tokens, same-GUID refresh caveat and built-in equip handler. TODO is planning, not an API.
- Offsets/new headers/hooks are internal plumbing; only resulting Lua/event/storage semantics are promoted.
No bag-sort, macro parser, stealth detector, BG payload or Lua table-length change.

## Portfolio decisions
All eight repos checked for tooltip/action/cursor/equipment-set consumption and Git state.
- AutoBG: no release-driven runtime change; pending smooth timer/appearance work preserved.
- AutoLazy: no relevant call sites; no forced change.
- Bagnon: no sorting delta; no forced change.
- FostercareTweaks: exclude equipmentset from reagent icon inference.
- ItemRack: exclude equipmentset from item-use bookkeeping. Native sets and addon outfits remain separate; conversion requires explicit mapping design.
- MikScrollingBattleText: global GetUnitGUID helpers differ from the tooltip method; no change.
- TrinketMenu: exclude equipmentset from item-use/icon fallback.
- TWThreat: no relevant release change.
Framework reference advances to v1.15.15; addon guards remain capability-specific and unchanged. NamPower stays 4.6.2+. No Known Pattern addition: contracts fit canonical reference. No DLL installation. The user subsequently authorized committing and pushing the reviewed changes.

## Source blobs
| File | Blob SHA |
| --- | --- |
| AddOns/!!!ClassicAPI/Util/EquipmentManager.lua | 477915b610c17baee733f5f93641e4686f4b7c9f |
| README.md | cf885d857ce6fedbe1559a01cba1c3ea25e2a35c |
| TODO.md | 5fce00c12ace1f23109b962c01bb8fc03cfe6f53 |
| docs/API.md | a162057257ebe44c13e512d940eedf994c351a35 |
| src/Offsets.h | 9e10fb5f691d18aa23c1e1e90756da84042a08e9 |
| src/action/Info.cpp | e856b780ad5cc4dbb6e4828d0c0c789474ff19cf |
| src/cursor/Info.cpp | 3405c102d75670109a122d74fd146186633fba91 |
| src/cursor/Info.h | 015d8ca33e5cd9fbe79f9af56e82f4b3cae8f5bd |
| src/equipmentset/Action.cpp | ec51feb49455c96eb0065a384e096caefa479541 |
| src/equipmentset/Action.h | d3abd1f0784454a6863a0036f2021546d47dac7f |
| src/equipmentset/Api.cpp | c41e7a46b1a332891daf6a381335592706f456c8 |
| src/equipmentset/Data.cpp | e66d8f508b9cfc2eb84f4ab5c168418f379189a2 |
| src/equipmentset/Data.h | 4ca65d0f2df10addc2df89379fe00638cd9c4197 |
| src/equipmentset/Locations.cpp | 129a6afadd33a45aaaf46a119c20d517cd09fecf |
| src/equipmentset/Locations.h | 72070cdd1396993062db3d5c83a3d04063c8844f |
| src/equipmentset/Set.h | 57a971c6b602acecdb449b4695dff86ccbc86d47 |
| src/equipmentset/Storage.cpp | e3585e8feb4d5176ab28b353203f286cfff4c3c4 |
| src/equipmentset/Tooltip.cpp | 91cdc09851df96e8dc03bc62e7f90ecbb79a4108 |
| src/equipmentset/Tooltip.h | a4de73fd49aa543fc70f033555df024b00809b35 |
| src/frame/Attributes.cpp | 24da4b7933bdd8ae5657f5969ea1ccbcc70194c0 |
| src/tooltip/SetAction.cpp | f991d8c0d3d16af18b92054247cba31d697d0b9b |
| src/tooltip/SetEvents.cpp | 54accd21bfc88af3108adcc44f9b2990add9010c |
| src/unit/Tooltip.cpp | 6d28c79d72e8c4c0b98da50c0e29d70858da0aef |
| src/unit/Tooltip.h | 0e9bd0a17c76f0aa1e30df5594274b0506b8cd73 |

## Runtime requirements and retrospective
[SOURCE-VERIFIED] means official source/docs, not Niko-local gameplay evidence.
[UNVERIFIED - TEST FIRST] Fully restart WoW after replacing DLL. Verify CLASSIC_API_VERSION==11515, GetUnit in OnTooltipSetUnit and offline party hover; native set pickup/place/swap/use/delete/relogin, cast/lock rejection and persistence. Normal reagent counts, ItemRack autoqueue and TrinketMenu item-use detection must remain correct. Set buttons sharing spell/trinket icons must not trigger those trackers.
Retrospective: classify native action types explicitly; do not conflate native sets with addon outfit ownership. No performance claims or automatic outfit migration.


## Validation outcome
Framework: 40 tests pass. All eight addon linter scans report zero errors; Bagnon has 11 structure advisories and TWThreat one. Changed addon Lua compiles (FostercareTweaks 50 files, ItemRack 5, TrinketMenu 3). Direct mocked checks confirm all three equipment-set exclusions.
ItemRack: 30/31 regression tests pass; test_swap_abort_drains_queue_and_stops_retry fails identically when SOURCE is replaced with unchanged HEAD, so this is an independently reproduced baseline issue. Four poison-swap tests pass. No failed test is bypassed and no runtime verification is claimed.
Upstream checker confirms ClassicAPI commit and both blobs CURRENT; overall exit 1 is from NamPower 4.6.3 versus intentionally retained 4.6.2 baseline. SuperWoW and UnitXP are CURRENT. Diff checks pass. AutoBG's five pending smoothing/appearance files were preserved, not bundled into this audit.

Release reconciliation: README files for all eight addons recommend ClassicAPI v1.15.15+ and distinguish it from unchanged enforced minimums. The user authorized publishing the framework integration, three action-type fixes and pending validated AutoBG timer appearance work.

## Independent recheck and subsequent support policy — 2026-09-27

The annotated tag, peeled commit, all three commits in the complete .14-to-.15
range, publication timestamp, DLL asset ID/size, GitHub digest and all recorded
source/document blob SHAs were independently checked again against official
upstream. The downloaded DLL hashes to the recorded SHA-256. No source contract
correction or additional Known Pattern was required.

The maintainer subsequently chose v1.15.15+ as the published support floor for
the eight personal addon projects. This is an explicit support policy, not
evidence that their older APIs first appeared in .15, and does not impose the
same guard on other VanillaForge projects. The framework retains capability
history and does not automatically raise addon guards on future releases.
Project commits, deployment hash and runtime gaps belong in the local addon
maintenance register; source verification remains separate from gameplay proof.

Recheck validation: 40 framework tests and 99 addon regressions pass; 114
boundary scenarios cover the 19 addon startup guards (missing/invalid version,
.14 rejection, .15 and later acceptance). All eight Lua/load graphs and diff
checks pass. Static scans have zero errors; the 11 Bagnon and one TWThreat
XML-loading advisories are understood. The ClassicAPI-only upstream check is
CURRENT with exit 0. The full checker still reports the known NamPower .3 versus
intentionally supported .2 release difference; that separate policy is retained.
