# ClassicAPI reference history

Moved out of CLASSICAPI_MASTER_REFERENCE.md on 2026-11-07: the reference describes
the release pinned in UPSTREAM_VERSIONS.json; this file keeps what it used to say
about earlier releases, for reading old commits. Nothing here is current guidance.

## Version stamps of earlier releases (from section 2)

Older stamps, for reading old code:

```text
v1.15.8 -> 11508
v1.15.9 -> 11509
v1.15.10 -> 11510
v1.15.11 -> 11511
v1.15.12 -> 11512
v1.15.13 -> 11513
v1.15.14 -> 11514
v1.15.15 -> 11515
v1.15.16 -> 11516
v1.16.0 -> 11600
v1.17.0 -> 11700
v1.17.3 -> 11703
v1.17.4 -> 11704
v1.17.5 -> 11705
v1.17.6 -> 11706
v1.17.7 -> 11707
v1.17.8 -> 11708
v1.17.9 -> 11709
v1.17.10 -> 11710
v1.17.11 -> 11711
v1.17.12 -> 11712
v1.17.13 -> 11713
v1.18.0 -> 11800
v1.18.5 -> 11805
v1.19.2 -> 11902
v1.20.4 -> 12004
```

## Source snapshot and refresh protocol (sections 103 and 104 until 2026-11-07)

## 103. Source Snapshot

This document was built from the official repository:

```text
brues-code/ClassicAPI
release: v1.17.11 (tag commit 317539dbd8aa9e9cd7a23441c0e355bb85c7e2ab)
commit:  317539dbd8aa9e9cd7a23441c0e355bb85c7e2ab
branch:  master
```

Official source files used as primary reference (v1.17.11):

```text
README.md (blob: 0e9caaa69eab05385d058b8404768b9bb33c33a8)
docs/API.md (blob: fb0bfad60bb898eca5e862df8f85b104f2dbcd84)
commit messages v1.17.8...v1.17.11 (behaviour API.md leaves out)
src/frame/Alpha.cpp (at abd5367, the nameplate alpha rules)
```

Source files read for earlier snapshots (v1.15.16, commit 7ccbbaaf):

```text
src/macro/Icons.cpp (blob: 5ad755eaf93c13bc4fea5e353f6ea40fea23e964)
src/macro/IconPath.cpp (blob: 40cd511660c76ec48ec8e22c96fad58c5cf1e7c2)
src/Offsets.h (blob: 9e10fb5f691d18aa23c1e1e90756da84042a08e9)
src/macro/ShowTooltip.cpp (blob: 24a8aa1158c5c93754b10e4d263c3dd6a90047e0)
src/table/Length.cpp (blob: 5c3f9dfdbedd34ae016caefd038e3003facf6b28)
src/cvar/Temp.cpp (blob: 3810691c26dc7e91ca2af75ad615c7e32945d58f)
src/container/SortBags.cpp (blob: b6d77b3b7bc6e8a9b2361fa4bfbcf1d2117acf7a)
src/nameplate/Events.cpp (blob: cebb4ac06c43f85dd907f74cd19b908bbd540897)
src/api/Version.cpp (blob: 33c3ea05a268203cc96c0056557a497a141843a1)
CMakeLists.txt (blob: 830adb8a01e930faa3016184faface04b67b8ff6)
src/unit/TokenExtensions.cpp (blob: 1bb9fa98dc16defa0e8a8c75d8ef96225b87b61f)
src/unit/Position.cpp (blob: 156568032d2a419a7d3fedc006b3d7651bc9d975)
Earlier verified source knowledge retained (Swing.cpp, SwingRange.cpp, Equipment.cpp, Data.cpp, Custom.cpp, Offsets.h)
```

The v1.15.12 API reference blob was:

```text
0ab67379ec55e5e9ebe92595b40611cc5d482164
```

The v1.15.14 release makes the question-mark icon the first engine macro icon
and selectable without a separate icon-injection workaround. No API signatures,
event payloads, bag sorting or Lua table semantics change in this release. See
[the v1.15.14 audit](archive/docs/CLASSICAPI_1.15.14_AUDIT.md) for the full one-commit range,
independently verified provenance and runtime requirements.

The v1.15.13 release added:

- `C_CVar.SetTempCVar` and `C_CVar.RemoveTempCVar` (session-only CVar overrides without `Config.wtf` persistence)
- Baganator-style equipment slot grouping in `C_Container.SortBags()` and `C_Container.SortBankBags()`
- Nameplate announcement retries while prerequisites remain unmet (no new event payloads)

The complete three-commit `v1.15.12...v1.15.13` range, release/DLL provenance,
review corrections and runtime requirements are recorded in
[the v1.15.13 audit](archive/docs/CLASSICAPI_1.15.13_AUDIT.md).
The [earlier audit](archive/docs/CLASSICAPI_1.15.12_AUDIT.md) retains v1.15.10 through
v1.15.12 provenance; its macro and weak-table knowledge remains valid.

---

## 104. Refresh Protocol

When updating this master reference:

1. Fetch current `README.md`.
2. Fetch current `docs/API.md`.
3. Compare the API.md blob SHA with the snapshot above.
4. Review changed API sections.
5. Update:
   - namespace inventory
   - events
   - Lua compatibility behavior
   - macro behavior
   - modern client features
   - caveats
6. Do not copy unfinished TODO items into the active API catalog.
7. Increment the local document revision/date if your repository tracks revisions.

---

## Release notes moved from the contract sections (1.15.16, 1.16.0)

## v1.15.16 source-verified addon contracts
[SOURCE-VERIFIED] Compatibility-only release; no new public Lua API symbols, events, or return signature changes. Bundled `!!!ClassicAPI` compatibility module `AddOns/!!!ClassicAPI/Util/AddOnCompat.lua` intercepts `Turtle_GroupUI` via `EventUtil.ContinueOnAddOnLoaded` and wraps the global `GroupFrame_ToggleMovement(state)` function. Under modern script dispatch, frame buttons pass the widget (`self`) as the first argument to `OnClick`; this wrapper sanitizes any non-numeric `state` argument to `nil` before calling the original function, preventing an arithmetic error (`1 - state` at `Turtle_GroupUI.lua:409`). See [v1.15.16 audit](archive/docs/CLASSICAPI_1.15.16_AUDIT.md).

[SUPERSEDED in 1.17] In 1.16.0, `CreateFrame("Cooldown", ...)` was a Model, `SetReverse` / `SetDrawEdge` changed nothing and XML could not create it. 1.17.0 and 1.17.1 changed all three; see [v1.17 Cooldown](#native-cooldown-frame-1171).

This release adds 4.3.4-era API coverage plus behavior fixes across frames, tooltips, hooks, XML, nameplate/unit events, quest-log behavior and Lua compatibility. See the [v1.16.0 audit](archive/docs/CLASSICAPI_1.16.0_AUDIT.md) for upstream provenance, deployment evidence and portfolio displacement candidates. In-game behavior remains unverified locally.
