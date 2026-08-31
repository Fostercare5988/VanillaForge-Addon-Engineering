# OctoWoW Addon Modernization & Reverse Engineering System Prompt

[![World of Warcraft 1.12.1](https://img.shields.io/badge/WoW-1.12.1%20(Vanilla)-blue.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Engine Stack](https://img.shields.io/badge/Engine-OctoWoW%20%7C%20SuperWoW%20%7C%20UnitXP%20%7C%20DXVK-green.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Lua Version](https://img.shields.io/badge/Lua-5.0%20Strict-orange.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)

A battle-tested, high-precision system prompt designed for AI coding assistants and reverse engineers to modernize, refactor, and optimize legacy **World of Warcraft 1.12.1 (Vanilla)** addons for the **OctoWoW** client ecosystem.

---

## 🎯 Purpose

Legacy Vanilla WoW (1.12.1) addons often suffer from:
- Lua 5.0 parser incompatibilities when modern Lua syntax is applied.
- FrameXML relative layout collapse and missing coordinate anchors.
- Severe garbage collection (GC) stutter and heap churn during high-frequency combat events.
- Hardcoded 60 Hz frame-step logic causing jitter on high-refresh-rate monitors (144 Hz / 240 Hz+).
- Inaccurate client assumptions (e.g., assuming TBC/WotLK API returns or 0–100% enemy health limits).

The [**`OCTOWOW_SYSTEM_PROMPT.md`**](OCTOWOW_SYSTEM_PROMPT.md) establishes strict rules, architectural guardrails, and binary protocol specifications to guarantee that refactored addons run with **zero runtime errors, zero layout glitches, and zero combat GC stutter**.

---

## ⚡ The Modern OctoWoW Engine Stack

This system prompt targets the enhanced OctoWoW client stack:

| Component | Minimum Version | Core Capability / Role |
| :--- | :--- | :--- |
| **SuperWoW** | `v2.2+` | Extended C++ client engine APIs (`C_Timer`, GUID targeting, window flashing, audio channels). |
| **NamPower** | `v4.6.2+` | Precise combat log enums (`SMSG_SPELLLOGMISS`, `SMSG_ATTACKERSTATEUPDATE`), spell engine enhancements. |
| **UnitXP SP3** | `SP3` | Real-time uncapped raw numerical health/maxhealth, accurate yard distance engine. |
| **DXVK** | `v3.0.2+` | Direct3D 9 to Vulkan translation for high framerate and low frame-time jitter. |
| **VanillaFixes** | Latest | Core client stability, memory fixes, and modern OS compatibility. |

---

## 🛡️ Core Directives Summary

The prompt is structured around 10 strict architectural pillars:

1. **Lua 5.0 Strict Compiler Guardrails**:
   - Forbids uncalled colon syntax (e.g. `obj:Method` checks without arguments) which crashes Lua 5.0's parser.
   - Requires `table.getn(t)` instead of the Lua 5.1 `#t` length operator.
   - Enforces 5.0 string APIs (`string.find`, `string.gsub`, `string.sub`).
2. **FrameXML Deterministic Anchoring & Layout Engine**:
   - Forbids relative sibling anchoring during file load to prevent button collapse.
   - Requires deterministic parent container offsets and registration in `UISpecialFrames`.
   - Zero static third-party frame anchors in XML.
3. **Exact Vanilla 1.12.1 Protocol Compliance**:
   - Exact 5-tuple return for `GetLootRollItemInfo(rollID)` (no `canNeed`/`canGreed`).
   - Exact binary roll enums (`0=Pass`, `1=Need`, `2=Greed`).
   - NamPower miss enums & 4-stage color-graded UnitXP distance engine.
4. **Strict Token Matching & Currency Protection**:
   - Forbids loose keyword/substring matching.
   - High-value server currency blacklists (e.g. `Fashion Coin`) & relic vs. token isolation (e.g. AQ20 idols vs equipable relics).
5. **Memory & Zero Combat GC Churn**:
   - Zero heap allocations inside combat loops, `OnUpdate`, or addon messaging.
   - Pre-allocated unit ID arrays, in-memory LRU item caches, and object recycling pools.
6. **High-Refresh Rate & DXVK Smoothing (144Hz+)**:
   - Framerate-decoupled animations using delta time (`dt`) exponential smoothing and accumulator timers.
7. **SuperWoW C++ Engine & Hardware Integration**:
   - Native `C_Timer.After` hardware timers.
   - Exact whole-name targeting (`TargetByName(name, true)`) and direct creature GUID targeting (`TargetUnit(guid)`).
   - Taskbar icon flashing (`FlashClientIcon()`) and OS window foregrounding.
8. **OctoLauncher & Git Remote Preservation**:
   - Ensures personal Git remote preservation (`https://github.com/Fostercare5988/<AddonName>.git`) to prevent launcher auto-update overwrites.
9. **Pure English Standard & Branding**:
   - 100% English interface, comments, and clean `.toc` metadata.
10. **Automated Static Analysis & Syntax Verification**:
    - Pre-commit AST/closure validation, colon method regex linting, and legacy 2006 dead code eradication.

---

## 🚀 How to Use

1. Open [`OCTOWOW_SYSTEM_PROMPT.md`](OCTOWOW_SYSTEM_PROMPT.md).
2. Copy the contents into your AI coding assistant (Claude, Gemini, Antigravity, ChatGPT, Cursor, etc.) as a **System Prompt** or initial instruction context.
3. Provide the path to the legacy Vanilla addon directory you wish to modernize.
4. Let the agent execute the deep audit, refactor, and verification following the rules.

---

## 👤 Author & Maintainer

- **Maintained by**: [Fostercare5988](https://github.com/Fostercare5988)
- **Repository**: [OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
