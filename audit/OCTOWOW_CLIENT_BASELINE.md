# OctoWoW Deployed Client Baseline

> **Authoritative Target Environment Baseline for VanillaForge Addon Engineering**
> Generated from static reverse-engineering and byte-level audits of the deployed OctoWoW runtime.

---

## 1. Authoritative Client Identity

| Dimension | Authoritative Value | Evidence / Provenance |
| :--- | :--- | :--- |
| **Primary Deployed Client Root** | `C:\Users\Fostercare\Desktop\client` | `[DEPLOYED FACT]` Active development/runtime root |
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
   - `client`: Removed root `d3d9.dll`; loads through `dxgi.dll` and runtime driver hooks.
3. **Data Patch Upgrades**:
   - `Niko2`: Missing `patch-O.mpq` (OctoWoW custom DBCs/spells) and `patch-Y.MPQ` (AutoLogin).
   - `client`: Deploys `patch-O.mpq` (9,315,256 bytes) and `patch-Y.MPQ` (12,822 bytes).
   - `patch-5.mpq`: Modified between clients (`PVP_MEDAL65` title normalized from `"Godslayer of Hakkar"` to `"Godslayer"`, and updated locale tables).
4. **Loader Order**:
   - `dlls.txt` reorganized to load `SuperWoWhook.dll` and `ClassicAPI.dll` ahead of `nampower.dll` and `UnitXP_SP3.dll`.

---

## 4. Authority Rules for Addon Engineering

When resolving conflicting specifications or APIs:

1. **Deployed Client Files (`C:\Users\Fostercare\Desktop\client`)**:
   Wins unconditionally for client engine behavior, event names, FrameXML functions, and native DLL availability.
2. **OctoWoW Database (`https://octowow.st/db/`)**:
   Wins for server-content identities: item IDs, quest IDs, NPC IDs, spell IDs, and quest turn-in requirements.
3. **Exact Upstream Native Releases**:
   Authoritative for C_ namespace semantics (`ClassicAPI v1.15.16`, `SuperWoW v2.2`, `NamPower v4.6.2`, `UnitXP SP3 v90`).
4. **VanillaForge Canonical Knowledge**:
   Governs architectural safety, boundary isolation, linter rules, and repository hygiene.
5. **Generic Vanilla 1.12 Assumptions**:
   Invalidated wherever OctoWoW or ClassicAPI has introduced modernized constructs.
