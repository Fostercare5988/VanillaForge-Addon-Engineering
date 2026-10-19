# OctoWoW Deployed Client Baseline

> **Historical deployed snapshot; verify the active installation before reuse.**
> Generated from static reverse-engineering and byte-level audits of the earlier OctoWoW runtime.

Use [target preflight](../docs/TARGET_ENVIRONMENT.md) and
[TARGET_ENVIRONMENT.json](../TARGET_ENVIRONMENT.json) for current task requirements.
This file preserves dated deployment evidence. Its personal paths, version labels
and logs do not establish the installation on another computer or a later session.

## Current installation correction — 19 October 2026

The active game remains `C:\Users\Fostercare\Desktop\client-2026-10-10`.
Its `ClassicAPI.dll` was replaced with the official v1.16.0 release asset:
1,512,448 bytes, SHA-256
`ae88fc0461b58eff37171e10015ddaf8c27b1f428794c4ff927429389fc2535b`.
The bytes match GitHub's published asset digest. The v1.15.16 recovery copy is
stored outside the game at
`C:\Users\Fostercare\Documents\VanillaForge\.private\ClassicAPI-v1.16.0-upgrade-2026-10-19\ClassicAPI-v1.15.16.dll`
and its prior SHA-256 was verified. `dlls.txt` and the other native binaries
were not changed. No game process was active at replacement time, so v1.16.0
runtime loading and addon startup guards remain unverified; a full client restart
is required.

All 16 maintained addon repositories now declare ClassicAPI v1.16.0+ as their
shared support minimum in TOC metadata and startup guards. See the [v1.16.0
upstream audit](../docs/CLASSICAPI_1.16.0_AUDIT.md) for provenance and validation.

The [current client manifest](octowow-client-manifest.json) and native inventory
are refreshed from this install. The [12 October manifest](octowow-client-manifest-2026-10-12.json)
and the earlier records below remain historical evidence.

## Earlier installation correction — 12 October 2026

The 12 October record selected `C:\Users\Fostercare\Desktop\client-2026-10-10`, launched
with its `VanillaFixes.exe`. Maintained addon repositories lived directly in
`C:\Users\Fostercare\Desktop\client-2026-10-10\Interface\AddOns\<addon>`.
For that installation, engineering used those installed folders rather than a
second source checkout. Select the actual source/client root for each new task;
keep developer tools, tests, audit evidence and recovery outside the game. Earlier checkouts and the
retired `FostercareClient` workspace are preserved under
`C:\Users\Fostercare\Documents\VanillaForge\.private\addon-consolidation-2026-10-11\recovery`.
The earlier `client` and `client-2026-10-06` games are historical/recovery only.
All 15 maintained GitHub addon repositories were moved from the latter with
their Git history, ignored/untracked files and uncommitted changes intact.
Full file hashes, directories, HEADs, branches, remotes and working-tree status
matched before/after. Migration evidence is under
`.private/client-migration-2026-10-12`; its `incoming-SuperAPI` directory preserves
the new client's original non-Git SuperAPI copy outside the game. Non-Git addons
and WTF were outside this migration's scope.
On 12 October, FostercareTweaks 1.3.0 moved its nameplate implementation into
the independent FostercareNameplates 1.0.0 repository in the same active AddOns
directory. There are now 16 maintained repositories. Nameplates starts disabled;
`/fnp` opens its settings when enabled. The target-frame castbar stays in Tweaks.
Source, migration, regression and deployment evidence is under
`.private/fostercare-nameplates-split-2026-10-12`; this separation does not establish
the cause of the reported stutters or native crash safety.
The active executable remains WoW 1.12.1.5875, Interface `11200`; SHA-256:
`cb599a39b7cbc6fc2d63cc1d2fb18fac62546b81b08c407512d1bdec4471614b`.

The 12 October client manifest recorded the then-current active
installation. The archived private workspace's `client-baseline.json` and
`docs/STUTTER_REVIEW.md` describe the previous installation. DXVK 3.1.1
D3D9/Vulkan presentation was established in that older installation after
restoring root `d3d9.dll`. Its SHA-256 is
`265888c31ca78dffa290c39cb7e50bfb02762590e41927906e46fb32f01497fa`.
The new root contains the matching `d3d9.dll`; this is file evidence, not runtime
verification. The earlier absence of `d3d9.dll` did not establish an alternate
working renderer. WeirdPerformance's exact release/loading/effect remains
unverified. Current settings and OctoWoW Data patches remain authoritative;
do not substitute older snapshots or assume matching DLL files prove runtime compatibility.

At migration, the new root's `ClassicAPI.dll` reports **1.15.12.0**, below the
framework's deliberate 1.15.16+ baseline and FostercareTweaks 1.2.2's declared
1.15.15+ minimum. That observation is historical: the 12 October portfolio
preflight now finds **1.15.16.0**, SHA-256
`e34886fb9725b9059375a5c37bff81ce220633c4e2c39719ef3223a6b8fc703d`, matching
the pinned upstream release. SuperWoW 2.2, NamPower 4.6.2, UnitXP SP3 build 90
and DXVK 3.1.1 d3d9.dll match the dated reference file hashes. All five are listed
in the current `dlls.txt`; no listed file is missing. These are current file and
loader-list observations, not proof of runtime loading or performance. The
manifest now distinguishes declared PE versions from reference hash identity.
Native updates require a full client restart.

The 15 October upstream recheck refines the labels without rewriting these
observations: the recorded NamPower hash matches the official `v4.6.3` asset,
whose version dispatcher still reports `4.6.2`. The recorded UnitXP hash differs
from the official brues-code `v90` asset, so its remembered build-90 label alone
does not prove release identity. Supported minimums remain NamPower 4.6.2 and
UnitXP SP3 v89. See [engine provenance](../ENGINE_REFERENCE.md) and the registry
for supported floors, source pins and released artifacts as separate evidence.

Sections below preserve the earlier audit's original source scope.

---

## 1. Earlier Snapshot Client Identity

| Dimension | Authoritative Value | Evidence / Provenance |
| :--- | :--- | :--- |
| **Earlier Client Root** | `C:\Users\Fostercare\Desktop\client` | `[DEPLOYED FACT]` Historical audit root |
| **Client Executable** | `WoW.exe` (4,927,488 bytes) | `[DEPLOYED FACT]` SHA256: `079921d4994102e51f1424f4f8221387bf3a98f907cabbb6475d63506263cebf` |
| **WoW Client Version** | `1.12.1.5875` | `[DEPLOYED FACT]` PE VersionResource: `FileVersion="1, 12, 1, 5875"`, `ProductVersion="Version 1.12"` |
| **Interface Version Number** | `11200` | `[DEPLOYED FACT]` `FrameXML.toc` line 2: `## Interface: 11200` |
| **Server / Content Realm** | `play.octowow.st` | `[DEPLOYED FACT]` `realmlist.wtf`: `set realmlist "play.octowow.st"` |
| **Server Content Database** | `https://octowow.st/db/` | `[UPSTREAM FACT]` Authoritative source for custom items, quests, NPCs, spells |

---

## 2. Directory Layout & Engineering Responsibility

```text
C:\Users\Fostercare\Desktop\client\
├── WoW.exe                          # Native client binary (1.12.1 Build 5875)
├── dlls.txt                         # Loader configuration list (active native extensions)
├── dlls.txt.cache                   # Cached absolute paths resolved by loader
├── dxgi.dll                         # DXVK Direct3D-to-Vulkan translation layer (runtime infra)
├── dxvk.conf                        # DXVK configuration profile
├── realmlist.wtf                    # Server pointer: play.octowow.st
├── ClassicAPI.dll                   # Modernized WoW API backport (v1.15.16)
├── SuperWoWhook.dll                 # SuperWoW client extension (v2.2)
├── nampower.dll                     # Spell/combat/nameplate engine extension (v4.6.2)
├── UnitXP_SP3.dll                   # UnitXP SP3 native camera/targeting/cvar extension (Build 90)
├── AuctionQueryThrottle.dll         # AH scan pacing / query throttling
├── transmogfix.dll                  # Transmog visual rendering hook (WeirdUtils)
├── VanillaFixes.exe / Helpers / etc # Windows 10/11 compatibility and multimonitor shims
├── Data\                            # Base and custom patch MPQ archives
│   ├── base.MPQ ... wmo.MPQ         # Base 1.12.1 game assets
│   ├── patch.MPQ                    # Stock 1.12.1 patch data
│   ├── patch-1.mpq ... patch-3.mpq  # Intermediate content patches
│   ├── patch-4.mpq                  # OctoWoW modernized UI / FrameXML modifications
│   ├── patch-5.mpq                  # OctoWoW wide quest log, calendar, LFT, shop, locale data
│   ├── patch-O.mpq                  # OctoWoW custom spells, DBCs, models, sound assets
│   └── patch-Y.MPQ                  # OctoWoW autologin GlueXML layer
├── Interface\
│   └── AddOns\                      # Addon directory hosting active maintained repositories
├── Logs\                            # Runtime diagnostic logs
│   ├── classicapi_debug.log         # ClassicAPI registration traces (767 API registrations)
│   ├── nampower_debug.log           # NamPower startup and CVar initialization traces
│   └── FrameXML.log                 # Blizzard UI XML/TOC loading log
└── WDB\                             # Client runtime entity caches
    ├── questcache.wdb               # Cached quest descriptions & objectives
    └── itemcache.wdb                # Cached item names, links, and tooltips
```

---

## 3. Historical Comparison: `client` vs `Niko2`

`C:\Users\Fostercare\Desktop\Niko2` is an **older historical client snapshot**, several OctoWoW client iterations behind. It is strictly **comparison-only** and must never override findings from `C:\Users\Fostercare\Desktop\client`.

### Material Historical Deltas:
1. **ClassicAPI Upgrade**:
   - `Niko2`: Shipped ClassicAPI `v1.15.15.0` (1,448,960 bytes, SHA256: `fc0030...`).
   - `client`: Upgraded to ClassicAPI **`v1.15.16.0`** (1,449,984 bytes, SHA256: `e34886fb...`), matching the official upstream release.
2. **DirectX / Vulkan Infrastructure**:
   - `Niko2`: Contained `d3d9.dll` (7,856,142 bytes) in the root.
   - `client`: Root `d3d9.dll` absent at the snapshot; alternate rendering/loading was not verified.
3. **Data Patch Upgrades**:
   - `Niko2`: Missing `patch-O.mpq` (OctoWoW custom DBCs/spells) and `patch-Y.MPQ` (AutoLogin).
   - `client`: Deploys `patch-O.mpq` (9,315,256 bytes) and `patch-Y.MPQ` (12,822 bytes).
   - `patch-5.mpq`: Modified between clients (`PVP_MEDAL65` title normalized from `"Godslayer of Hakkar"` to `"Godslayer"`, and updated locale tables).
4. **Loader Order**:
   - `dlls.txt` reorganized to load `SuperWoWhook.dll` and `ClassicAPI.dll` ahead of `nampower.dll` and `UnitXP_SP3.dll`.

---

## 4. Authority Rules for Addon Engineering

When resolving conflicting specifications or APIs:

1. **Currently Active Deployed Client Files**:
   Verify the active root and revision first. Its relevant source/files establish
   deployed engine behavior, event names and FrameXML functions; file presence
   alone does not establish runtime DLL loading.
2. **OctoWoW Database (`https://octowow.st/db/`)**:
   Wins for server-content identities: item IDs, quest IDs, NPC IDs, spell IDs, and quest turn-in requirements.
3. **Exact Upstream Native Releases**:
   Authoritative for C_ namespace semantics (`ClassicAPI v1.15.16`, `SuperWoW v2.2`, `NamPower v4.6.2`, `UnitXP SP3 v90`).
4. **VanillaForge Canonical Knowledge**:
   Governs architectural safety, boundary isolation, linter rules, and repository hygiene.
5. **Generic Vanilla 1.12 Assumptions**:
   Invalidated wherever OctoWoW or ClassicAPI has introduced modernized constructs.
