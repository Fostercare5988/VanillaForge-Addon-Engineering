# World of Warcraft 1.12.1 Enhanced Engine — OctoWoW Framework (v2.1)

[![World of Warcraft 1.12.1](https://img.shields.io/badge/WoW-1.12.1%20(Vanilla)-blue.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Engine Stack](https://img.shields.io/badge/Engine-ClassicAPI%20%7C%20SuperWoW%20%7C%20NamPower%20%7C%20UnitXP%20%7C%20DXVK-green.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Framework Version](https://img.shields.io/badge/OctoWoW-v2.1%20Canonical-brightgreen.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Lua Version](https://img.shields.io/badge/Lua-5.0%20Strict-orange.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)

A battle-tested, high-precision architectural framework and system prompt designed for AI coding assistants and reverse engineers to modernize, refactor, and build addons natively for the **Enhanced World of Warcraft 1.12.1 Client Extension Stack**, as used on the **OctoWoW** private server.

> **1.12.1 vs. 1.18.1 — not the same number.** `1.12.1` (`Interface: 11200`) is the vanilla *client*/Lua API version every addon here targets. `1.18.1` is OctoWoW's own *server-side content* patch (quests, zones, items) and has zero effect on the Lua API — never gate addon logic on it.

---

## 🎯 Modernization Paradigm & Core Principles

We **ONLY** build and modernize addons that strictly require and leverage the complete modern **Enhanced 1.12.1 Engine Stack** (ClassicAPI, SuperWoW, NamPower, UnitXP SP3, DXVK, and VanillaFixes). We never write backwards-compatible 2006 fallback code, tooltip scanners, or combat log string parsers.

### Why Legacy 1.12.1 Addons Lag vs. The Modern Stack:
- **No Combat Log Parsing:** ClassicAPI provides native millisecond-accurate castbars (`UnitCastingInfo` / `UnitChannelInfo`), eradicating combat log text regexes and GC stutter.
- **No Hidden Tooltip Scans:** Structured aura tables via `C_UnitAuras.GetAuraSlots` and `GetAuraDataBySlot` replace slow hidden `GameTooltip` string reading.
- **No `OnUpdate` Polling Loops:** Hardware-level timers (`C_Timer.After` / `C_Timer.NewTicker`) eliminate CPU-heavy Lua frame polling.
- **Native Nameplate System:** `C_NamePlate` replaces complex `WorldFrame` coordinate scraping.
- **Native Focus Target:** True `"focus"` unit token (`FocusUnit` / `ClearFocus`) replaces camera-hitching faux focus swaps.

### Core Architectural Directives (v2.1):
1. **Capability-First Model (Zero Artificial Bloat):** Addons assume the modern stack is present, but consume a DLL capability ONLY when it provides measurable improvements in correctness, performance, safety, or architecture. Never introduce a DLL dependency merely to use it.
2. **Four-Tier Execution Performance Architecture:**
   - **Tier 0 (Load-Time):** `PLAYER_LOGIN` & SavedVariables setup. Readability > micro-optimization.
   - **Tier 1 (Cold Event):** Zone changes & UI toggles. Lightweight allocations allowed.
   - **Tier 2 (Combat Hot Path):** `UNIT_HEALTH`, `UNIT_CASTEVENT`, combat log. Zero closure churn, minimal allocations.
   - **Tier 3 (Per-Frame Path):** `OnUpdate` running 60–144+ FPS. Strict zero allocation. Allowed ONLY for visual interpolation, drag, or animations.
3. **API Priority Ladder:** Native Events → Direct Unit Tokens (`target`, `focus`, `nameplateN`) → SuperWoW GUIDs → ClassicAPI C_ APIs → Stack DLL APIs → Cached State → C_Timer → Legacy 1.12 APIs.
4. **Stealth Rule (Zero "Octo" Branding on GitHub & End-Addons):** NEVER mention "Octo", "OctoWoW", "OctoWoW v2", or custom private server names on GitHub or in end-addons (.toc, README, git commits, PRs). Commits must strictly use neutral technical terminology (`feat(v3.5.0): modernize engine startup guards and dependency validation`).

---

## ⚡ The Mandatory Enhanced 1.12.1 Engine Stack

All modernized addons **strictly require** the modern client extension stack:

| Component | Official Repository | Minimum Version | Core Capability / Role |
| :--- | :--- | :--- | :--- |
| **ClassicAPI** | [**brues-code/ClassicAPI**](https://github.com/brues-code/ClassicAPI) | `v1.15.3+` (`v1.14.0+` baseline) | 637+ functions across ~60 modern retail-style `C_` namespaces (`C_Timer.After`/`NewTicker`, `UnitCastingInfo`/`UnitChannelInfo`, `C_NamePlate`, `C_UnitAuras` slot-batching, `FocusUnit`/`ClearFocus`, `C_Container` native coroutine sorting/queries, `C_Item` bagged enchants, `C_Macro` dynamic icons, `C_Texture` atlas/spritesheets, `C_Map` 3-tier coordinates/waypoints, `C_EncodingUtil`, `C_GossipInfo`, `C_AddOns`), plus `_G.ClassicAPI` anti-tamper mirror, true UTC `GetServerTime` (`CMSG_QUERY_TIME`), `hooksecurefunc`, `InCombatLockdown`, `table.wipe`, and an AST rewriter that compiles `#`, `%`, `string.match` on the Lua 5.0 VM. |
| **SuperWoW** | [**balakethelock/SuperWoW**](https://github.com/balakethelock/SuperWoW) | `v2.2+` (Mandatory DLL) | GUID-based unit arguments on all unit functions, `RAW_COMBATLOG`, exact-name targeting `TargetByName(name, true)`, direct GUID targeting `TargetUnit(guid)`, `SetMouseoverUnit`, clickthrough modes. |
| **NamPower** | [**Emyrk/nampower**](https://github.com/Emyrk/nampower) | `v4.6.3+` (Opt-in DLL) | Client-side spell-cast queueing (eliminates input latency), cooldown/aura/spell info (`SpellInfo`, `GetSpellNameAndRankForId`), binary combat event dispatches. |
| **UnitXP SP3** | [**brues-code/UnitXP_SP3**](https://github.com/brues-code/UnitXP_SP3) | Unpacked (Opt-in DLL) | Real-time uncapped raw numerical health (`UnitXP("health", unit)` / `UnitXP("maxhealth", unit)`), line-of-sight, distance calculation (`UnitXP("distance", unit)` / `UnitXP("distanceBetween", u1, u2)`), OS window foregrounding (`SetClientWindowForeground()`), OS taskbar flashing (`FlashClientIcon()`). |
| **DXVK** | [**doitsujin/dxvk**](https://github.com/doitsujin/dxvk) | `v2.0+` Vulkan Layer | Direct3D 9 to Vulkan translation layer, frametime pacing smoothing, jitter eradication, GPU optimization. |
| **VanillaFixes** | [**hannesmann/vanillafixes**](https://github.com/hannesmann/vanillafixes) | Latest Client Patch | High refresh rate animation uncap, modern OS compatibility, raw mouse input fix. |

---

## 🛡️ Mandatory Addon Startup Guard

Every modernized addon must declare an engine dependency check at initialization:

```lua
-- Strict Engine Dependency Guard (Mandatory ClassicAPI v1.14.0+ & SuperWoW v2.2+)
local MIN_CLASSIC_API = 11400

if not (CLASSIC_API_VERSION and SUPERWOW_VERSION) or 
   (type(CLASSIC_API_VERSION) == "number" and CLASSIC_API_VERSION < MIN_CLASSIC_API) then
    DEFAULT_CHAT_FRAME:AddMessage(
        "|cffff2020[Fatal Error]|r " .. (addonName or "Addon") .. 
        " requires ClassicAPI (v1.14.0+) & SuperWoW (v2.2+)! Please ensure both DLLs are loaded.", 
        1, 0.2, 0.2
    )
    return
end
```

---

## 🛠️ Automated Static Scanner & Linter (`tools/octowow_linter.py`)

This repository bundles a high-speed static analysis auditor located at:
```bash
python tools/octowow_linter.py <path_to_addon_or_file>
```

### Key Capabilities:
- **Block-Nesting Syntax Verification:** Catches unclosed blocks (`if/end`, `do/end`, `function/end`, `repeat/until`) and bracket parity.
- **Leveled Long Brackets Support:** Fully parses Lua 5.1/ClassicAPI leveled long brackets (`[=[ ... ]=]`, `[==[ ... ]==]`) in comments and strings without false positives.
- **Rule B1 Startup Guard Audit:** Ensures the mandatory startup dependency guard is present and checking `CLASSIC_API_VERSION` & `SUPERWOW_VERSION`.
- **Rule A1 Syntax Crash Audit:** Detects illegal bare colon method lookups (`f:GetScript and ...`) before they crash the Lua parser.
- **Rule B10 & D4 Memory Audit:** Flags obsolete 2006 table wiping loops and recommends native C++ `table.wipe(t)`.
- **Rule D1 Hierarchy Churn Audit:** Flags `{ f:GetRegions() }` and `{ parent:GetChildren() }` allocations in iterations.
- **Rule C12 & AP-26 Event Parameter Shadowing Audit:** Catches dangerous `(self, event, arg1)` signatures on event handlers that shadow `_G.event` / `_G.arg1` under 0-arg and 1-arg calling conventions, preventing silent addon initialization failures.
- **Rule H2 & H5 Documentation & Branding Audit:** Enforces neutral branding (no "Octo" leaks on GitHub), validates README compliance, and flags raw in-game WoW color escape codes (`|cff...`).
- **Strict Mode & Rule Suppression:** Pass `--strict` to treat warnings as fatal errors; suppress verified exceptions with `-- octowow-ignore: <RULE_ID>`.

---

## ⚠️ Known Limitations & Quality Directives

- **Rule G5 — The linter is a floor, not a ceiling:** `tools/octowow_linter.py` is a fast lexical scanner designed to prevent common syntax and structural bugs without heavy dependencies. A clean `0 errors, 0 warnings` run is necessary evidence of quality, but not sufficient proof. **Always follow static verification with an in-client `/reload` smoke test.**
- **Rule I0 — Anti-Pattern Growth & Consolidation:** When encountering new failure modes, prefer generalizing existing anti-patterns or promoting them to architectural rules over unbounded prompt expansion. Keep active anti-patterns capped at $\le 25$.
- **Rule F7 — Emergency Fast-Path Exception:** In high-urgency scenarios (e.g. raid hotfixes, quick PTR testing), agents may apply surgical code patches immediately and defer documentation / prompt synchronization.

---

## 🚀 How to Use

1. Open [`OCTOWOW_SYSTEM_PROMPT.md`](OCTOWOW_SYSTEM_PROMPT.md).
2. Copy the contents into your AI coding assistant (Claude, Antigravity, ChatGPT, Cursor, Windsurf) as a **System Prompt** or initial instruction context.
3. **If your tool has terminal / file access** (Antigravity, Claude Code, Cursor): point it to `C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\<AddonName>`.
   **If your tool is chat-only** (browser ChatGPT/Claude): paste the addon's `.lua`/`.toc` contents into the conversation. The AI will output complete code blocks and copy-pasteable git commands without pretending to run them.
4. Run `python tools/octowow_linter.py <addon-path>` to verify compliance, then perform an in-client `/reload` smoke test.

---

## 👤 Author & Maintainer

- **Maintained by**: [Fostercare5988](https://github.com/Fostercare5988)
- **Repository**: [OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
