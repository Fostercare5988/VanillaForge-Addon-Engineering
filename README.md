# World of Warcraft 1.12.1 Enhanced Engine — Addon Modernization & Architecture System Prompt

[![World of Warcraft 1.12.1](https://img.shields.io/badge/WoW-1.12.1%20(Vanilla)-blue.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Engine Stack](https://img.shields.io/badge/Engine-ClassicAPI%20%7C%20SuperWoW%20%7C%20NamPower%20%7C%20UnitXP-green.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Lua Version](https://img.shields.io/badge/Lua-5.0%20Strict-orange.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)

A battle-tested, high-precision system prompt designed for AI coding assistants and reverse engineers to modernize, refactor, and optimize legacy **World of Warcraft 1.12.1 (Vanilla)** addons for the **Enhanced World of Warcraft 1.12.1 Client Extension Stack**.

---

## 🎯 Modernization Paradigm

We **ONLY** build and modernize addons that strictly require and leverage the complete modern **Enhanced 1.12.1 Engine Stack** (including **ClassicAPI**, **SuperWoW**, **NamPower**, **UnitXP SP3**, and **DXVK**). We never write backwards-compatible 2006 fallback code, tooltip scanners, or combat log string parsers.

### Why Legacy 1.12.1 Addons Lag vs. The Modern Stack:
- **No Combat Log Parsing:** ClassicAPI provides native millisecond-accurate castbars (`UnitCastingInfo` / `UnitChannelInfo`), eradicating combat log text regexes and GC stutter.
- **No Hidden Tooltip Scans:** Structured aura tables via `C_UnitAuras.GetAuraDataByIndex` replace slow hidden `GameTooltip` string reading.
- **No `OnUpdate` Polling Loops:** Hardware-level timers (`C_Timer.After` / `C_Timer.NewTicker`) eliminate Lua frame polling.
- **Native Nameplate System:** `C_NamePlate` replaces complex `WorldFrame` coordinate scraping.
- **Native Focus Target:** True `"focus"` unit token (`FocusUnit` / `ClearFocus`).

The [**`OCTOWOW_SYSTEM_PROMPT.md`**](OCTOWOW_SYSTEM_PROMPT.md) guarantees that refactored addons run with **zero runtime errors, zero layout glitches, and zero combat GC stutter**.

---

## ⚡ The Mandatory Enhanced 1.12.1 Engine Stack

All modernized addons **strictly require** the full 4-DLL client extension stack:

| Component | Minimum Version | Core Capability / Role |
| :--- | :--- | :--- |
| **ClassicAPI** | **Mandatory DLL** | 550+ functions across ~60 modern retail-style `C_` namespaces (`C_Timer.After` / `NewTicker`, `UnitCastingInfo` / `UnitChannelInfo`, `C_NamePlate`, `C_UnitAuras`, `FocusUnit` / `ClearFocus`, `C_Container`, `C_EncodingUtil`, `C_GossipInfo`, `C_EquipmentSet`, `C_AddOns`), plus `hooksecurefunc`, `InCombatLockdown`, `table.wipe`, and a source-rewriter that makes modern Lua 5.1 syntax (`#`, `%`, `string.match`) compile on the 5.0 VM. |
| **SuperWoW** | `v2.2+` **Mandatory DLL** | GUID-based unit arguments on all unit functions, `RAW_COMBATLOG`, exact-name targeting `TargetByName(name, true)`, direct GUID targeting `TargetUnit(guid)`, `SetMouseoverUnit`, clickthrough modes. |
| **NamPower** | `v4.6.2+` **Mandatory DLL** | Client-side spell-cast queueing (eliminates input latency), cooldown/aura/spell info (`SpellInfo`, `GetSpellNameAndRankForId`), binary combat event dispatches. |
| **UnitXP SP3** | `SP3` **Mandatory DLL** | Real-time uncapped raw numerical health (`UnitXP("health", unit)` / `UnitXP("maxhealth", unit)`), line-of-sight, distance calculation (`UnitXP("distance", unit)` / `UnitXP("distanceBetween", u1, u2)`), OS taskbar flashing (`FlashClientIcon()`), window foregrounding (`SetClientWindowForeground()`). |
| **VanillaFixes + DXVK** | Latest + Vulkan | Direct3D 9 to Vulkan translation, high refresh rates (144Hz/240Hz+), frametime jitter reduction, animation smoothing. |

---

## 🛡️ Mandatory Addon Startup Guard

Every modernized addon must declare an engine dependency check at initialization — checking the DLLs' own version globals, not inferring presence indirectly from a function existing:

```lua
-- Strict Engine Dependency Guard
if not (CLASSIC_API_VERSION and SUPERWOW_VERSION) then
    DEFAULT_CHAT_FRAME:AddMessage("|cffff2020[Fatal Error]|r " .. (addonName or "Addon") .. " requires ClassicAPI.dll & SuperWoW! Please ensure ClassicAPI.dll and SuperWoW are loaded.", 1, 0.2, 0.2)
    return
end
```

---

## 📚 Core Architecture & Directives Overview

The master prompt is structured into 8 core thematic sections:

### **Part A — Lua Syntax: What ClassicAPI Rewrites, and What It Doesn't**
- **No uncalled colon methods** — the one rule that never changes: `(f.GetScript and f:GetScript("OnClick"))` is required; `(f:GetScript ...)` alone crashes the Lua parser, in any Lua version. This is a parser rule, not a 5.0-vs-5.1 gap, so it's not something ClassicAPI's rewriter touches.
- **`#` and `%` are safe to use directly** — confirmed in-client (`/run print(#{1,2,3})` → `3`). ClassicAPI's source-rewriter compiles modern Lua 5.1 syntax on the 1.12 Lua 5.0 VM before it reaches the compiler, so `#t` and `a % b` work normally now. `table.getn(t)`/`math.mod(a, b)` still work but are the legacy forms you'll meet in old or ported code, not something to write going forward.
- **String metatables & `string.match` are safe to use directly** — `("str"):upper()`, `msg:match("^!(%w+)")` resolve through the rewriter the same way `string.find`/`string.sub`/`string.gsub` always have.

### **Part B — Modern Engine Stack API Reference**
- **Real-Time Castbars**: `UnitCastingInfo(unit)` / `UnitChannelInfo(unit)`.
- **Modern Nameplates**: `C_NamePlate.GetNamePlates()`, `GetNamePlateForGUID()`, and `NAME_PLATE_UNIT_ADDED` / `REMOVED` events.
- **Structured Auras**: `C_UnitAuras.GetAuraDataByIndex(unit, idx)`, plus the more direct `GetBuffDataByIndex` / `GetUnitAuraBySpellID` for single-aura lookups.
- **Native Focus Unit**: `FocusUnit("target")`, `ClearFocus()`, `UnitHealth("focus")`.
- **Native C++ Encodings**: `C_EncodingUtil` — Base64, Hex, and JSON/CBOR serialization (no MD5/SHA — corrected from an earlier draft that claimed hashing support that doesn't exist).
- **Native Gossip**: `C_GossipInfo` (`GetActiveQuests`, `GetOptions`, `SelectOption`, …) replaces the old flat-vararg stock functions.
- **Protocol 1.12.1 Specifications**: Exact 5-tuple loot roll returns, NamPower combat enums (`SMSG_SPELLLOGMISS`), and UnitXP SP3 uncapped health/distance engine.
- **SuperWoW Hardware APIs**: `TargetByName(name, true)`, `TargetUnit(guid)`, and `FlashClientIcon()`.
- **High-value primitives easy to miss**: `hooksecurefunc`, `InCombatLockdown`, `C_AddOns.IsAddOnLoaded()` (reliable addon detection — see Part E), `table.wipe`, plus a bundled Lua utility library (`Mixin`, `TableUtil`, `MathUtil`) and a bundled `DebugTools` addon (`/dump`, `/etrace`, `/framestack`, `/luaerrors`, real `print()`).

### **Part C — FrameXML Layout & Event Rules**
- **Deterministic anchoring**: Eliminates relative sibling load-time anchoring bugs.
- **ESC closing & templates**: Native `UISpecialFrames` registration.
- **Click & script safety**: Explicit right-click registration (`btn:RegisterForClicks("LeftButtonUp", "RightButtonUp")`) and `:GetScript("OnClick")` type-checking on `Button`/`CheckButton` frames.
- **Global scope pollution defense**: Strict `local` scoping on all loop iterators and temporaries.

### **Part D — Performance: Memory, Zero GC Churn & Frame Timing**
- **Zero combat heap allocations**: No closures, temporary tables, or string concats inside combat/OnUpdate loops.
- **Pre-allocated unit ID arrays & LRU item caches**: O(1) cached lookup efficiency.
- **High-refresh DXVK animation smoothing**: Delta-time (`dt`) exponential smoothing and accumulator timers for jitter-free 144Hz+ rendering.
- **Exclusive C++ Hardware Timers**: `C_Timer.After` and `C_Timer.NewTicker` (custom pure-Lua timer loops are strictly forbidden).

### **Part E — Safety-Critical Matching & UI Filtering Rules**
- **Check `C_AddOns.IsAddOnLoaded()` first**: reliable, direct addon-presence detection for anything with a normal TOC entry — no scanning needed.
- **Currency protection**: Guards rare server currencies (e.g. `Fashion Coin`) and isolates token idols from equipable class relics.
- **Zero-leak minimap tray discovery**: Whitelist-only addon button detection for what `C_AddOns` can't cover (loose minimap buttons, server-injected UI); strict exclusion of player WeakAuras, condition frames, and UI checkboxes; persistent registry retention; renderability validated with a hand-written helper (not a built-in function).
- **Server UI suppression**: Explicit global frame lists and multi-layer `ARTWORK` region texture/FontString inspection for custom server radio buttons and LFG frames; reversible state preservation (`_alOrigState`).

### **Part F — Zero-Bloat Aggressive Consolidation & DRY Architecture Mandate**
- No superficial 1:1 API swaps: replacing `OnUpdate` with `C_Timer` while leaving the surrounding 2006-era bloat untouched doesn't count as done. Every touched file gets a full architectural diet.
- Consolidate duplicate rendering pipelines and monolithic `if/elseif` chains into single parameterized, table-driven functions.
- Any bugfix request triggers a full-codebase audit by default, not just a surgical patch — ask explicitly for a fast, scoped patch when you want one instead (mid-raid hotfixes, live testing).
- Target: 30–60% net line reduction per modernization pass — treated as the *expected outcome* of removing genuine bloat, not a number to hit by stripping comments or safety guards. Legitimate new lines (a real feature, a safety guard) are fine; call them out rather than cutting something else to compensate.

### **Part G — Static Verification Before Any Commit**
- Pre-commit AST/closure verification, regex linting for bare colon methods, and automated eradication of 2006 dead code patterns (hidden tooltip scanning, combat log cast parsing, custom OnUpdate timers).
- If you run a Lua 5.1+ syntax checker as a backstop: since ClassicAPI's rewriter now handles `#` / `%` / `string.match`, a clean 5.1 parse is a genuinely closer approximation of what will actually run on the enhanced client — not the false "all clear" it used to be before ClassicAPI was mandatory.

### **Part H — Conventions, Workflow & Conflict Resolution**
- OctoLauncher `.git` remote preservation (`https://github.com/Fostercare5988/<AddonName>.git`).
- Pure English standard and clean `.toc` metadata (`## Interface: 11200` — the client API version, unrelated to and unaffected by content patches like 1.18.1).
- Mandatory Read-Before-Write protocol for non-destructive system prompt updates, and a standing rule that direct in-game observation overrides a stale written rule.

---

## 🚀 How to Use

1. Open [`OCTOWOW_SYSTEM_PROMPT.md`](OCTOWOW_SYSTEM_PROMPT.md).
2. Copy the contents into your AI coding assistant (Claude, Gemini, Antigravity, ChatGPT, Cursor, etc.) as a **System Prompt** or initial instruction context.
3. Provide the path to the legacy Vanilla addon directory you wish to modernize (`C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\<AddonName>`).
4. Let the agent execute the deep audit, refactor, and verification following the rules.

---

## 👤 Author & Maintainer

- **Maintained by**: [Fostercare5988](https://github.com/Fostercare5988)
- **Repository**: [OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
