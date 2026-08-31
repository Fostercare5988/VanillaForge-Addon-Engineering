# OctoWoW Addon Modernization & Reverse Engineering — System Prompt

[![World of Warcraft 1.12.1](https://img.shields.io/badge/WoW-1.12.1%20(Vanilla)-blue.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Engine Stack](https://img.shields.io/badge/Engine-ClassicAPI%20%7C%20SuperWoW%20%7C%20NamPower%20%7C%20UnitXP-green.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Lua Version](https://img.shields.io/badge/Lua-5.0%20Strict-orange.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)

A battle-tested, high-precision system prompt designed for AI coding assistants and reverse engineers to modernize, refactor, and optimize legacy **World of Warcraft 1.12.1 (Vanilla)** addons for the **OctoWoW** client ecosystem.

---

## 🎯 Modernization Paradigm

We **ONLY** build and modernize addons that strictly require and leverage the complete modern **OctoWoW Engine Stack** (including **ClassicAPI**). We never write backwards-compatible 2006 fallback code, tooltip scanners, or combat log string parsers.

### Why Legacy 1.12.1 Addons Lags vs. The Modern Stack:
- **No Combat Log Parsing:** ClassicAPI provides native millisecond-accurate castbars (`UnitCastingInfo` / `UnitChannelInfo`), eradicating combat log text regexes and GC stutter.
- **No Hidden Tooltip Scans:** Structured aura tables via `C_UnitAuras.GetAuraDataByIndex` replace slow hidden `GameTooltip` string reading.
- **No `OnUpdate` Polling Loops:** Hardware-level timers (`C_Timer.After` / `C_Timer.NewTicker`) eliminate Lua frame polling.
- **Native Nameplate System:** `C_NamePlate` replaces complex `WorldFrame` coordinate scraping.
- **Native Focus Target:** True `"focus"` unit token (`FocusUnit` / `ClearFocus`).

The [**`OCTOWOW_SYSTEM_PROMPT.md`**](OCTOWOW_SYSTEM_PROMPT.md) guarantees that refactored addons run with **zero runtime errors, zero layout glitches, and zero combat GC stutter**.

---

## ⚡ The Mandatory OctoWoW Engine Stack

All modernized addons **strictly require** the full 4-DLL client extension stack:

| Component | Minimum Version | Core Capability / Role |
| :--- | :--- | :--- |
| **ClassicAPI** | **Mandatory DLL** | Modern retail-style `C_` namespaces (`C_Timer.After` / `NewTicker`, `UnitCastingInfo` / `UnitChannelInfo`, `C_NamePlate`, `C_UnitAuras`, `FocusUnit` / `ClearFocus`, `C_Container`, `C_EncodingUtil`). |
| **SuperWoW** | `v2.2+` **Mandatory DLL** | GUID-based unit arguments on all unit functions, `RAW_COMBATLOG`, exact-name targeting `TargetByName(name, true)`, direct GUID targeting `TargetUnit(guid)`, `SetMouseoverUnit`, clickthrough modes. |
| **NamPower** | `v4.6.2+` **Mandatory DLL** | Client-side spell-cast queueing (eliminates input latency), cooldown/aura/spell info (`SpellInfo`, `GetSpellNameAndRankForId`), binary combat event dispatches. |
| **UnitXP SP3** | `SP3` **Mandatory DLL** | Real-time uncapped raw numerical health (`UnitXP("health", unit)` / `UnitXP("maxhealth", unit)`), line-of-sight, distance calculation (`UnitXP("distance", unit)` / `UnitXP("distanceBetween", u1, u2)`), OS taskbar flashing (`FlashClientIcon()`), window foregrounding (`SetClientWindowForeground()`). |
| **VanillaFixes + DXVK** | Latest + Vulkan | Direct3D 9 to Vulkan translation, high refresh rates (144Hz/240Hz+), frametime jitter reduction, animation smoothing. |

---

## 🛡️ Mandatory Addon Startup Guard

Every modernized addon must declare an engine dependency check at initialization:

```lua
-- Strict Engine Dependency Guard
if not (C_Timer and C_Timer.After and UnitCastingInfo) then
    DEFAULT_CHAT_FRAME:AddMessage("|cffff2020[Fatal Error]|r " .. (addonName or "Addon") .. " requires ClassicAPI.dll & SuperWoW! Please enable ClassicAPI in OctoLauncher.", 1, 0.2, 0.2)
    return
end
```

---

## 📚 Core Architecture & Directives Overview

The master prompt is structured into 7 core thematic sections:

### **Part A — Lua 5.0 Strict Compiler Guardrails**
- **No uncalled colon methods**: `(f.GetScript and f:GetScript("OnClick"))` is required — `(f:GetScript ...)` crashes the Lua 5.0 parser.
- **No `%` modulo operator**: `%` is illegal in Lua 5.0 syntax — strictly use `math.mod(a, b)`.
- **No `#` length operator**: Use `table.getn(t)` and `table.setn(t, n)`.
- **Lua 5.0 string compliance**: Strictly use `string.find`, `string.sub`, `string.len`, `string.lower`, `string.gsub`.

### **Part B — Modern Engine Stack API Reference**
- **Real-Time Castbars**: `UnitCastingInfo(unit)` / `UnitChannelInfo(unit)`.
- **Modern Nameplates**: `C_NamePlate.GetNamePlates()` and `NAME_PLATE_UNIT_ADDED` / `REMOVED` events.
- **Structured Auras**: `C_UnitAuras.GetAuraDataByIndex(unit, idx)`.
- **Native Focus Unit**: `FocusUnit("target")`, `ClearFocus()`, `UnitHealth("focus")`.
- **Native C++ Encodings**: `C_EncodingUtil` (Base64, MD5, SHA).
- **Protocol 1.12.1 Specifications**: Exact 5-tuple loot roll returns, NamPower combat enums (`SMSG_SPELLLOGMISS`), and UnitXP SP3 uncapped health/distance engine.
- **SuperWoW Hardware APIs**: `TargetByName(name, true)`, `TargetUnit(guid)`, and `FlashClientIcon()`.

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
- **Currency protection**: Guards rare server currencies (e.g. `Fashion Coin`) and isolates token idols from equipable class relics.
- **Zero-leak minimap tray discovery**: Whitelist-only addon button detection; strict exclusion of player WeakAuras, condition frames, and UI checkboxes; persistent registry retention; renderability visual inspection.
- **Server UI suppression**: Explicit global frame lists and multi-layer `ARTWORK` region texture/FontString inspection for Turtle/Octo radio buttons and LFG frames; reversible state preservation (`_alOrigState`).

### **Part F — Static Verification Before Commit**
- Pre-commit AST/closure verification, regex linting for bare colon methods, and automated eradication of 2006 dead code patterns (hidden tooltip scanning, combat log cast parsing, custom OnUpdate timers).

### **Part G — Conventions, Workflow & Conflict Resolution**
- OctoLauncher `.git` remote preservation (`https://github.com/Fostercare5988/<AddonName>.git`).
- Pure English standard and clean `.toc` metadata (`## Interface: 11200`).
- Mandatory Read-Before-Write protocol for non-destructive system prompt updates.

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
