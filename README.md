# World of Warcraft 1.12.1 Enhanced Engine — OctoWoW Framework (v2.0)

[![World of Warcraft 1.12.1](https://img.shields.io/badge/WoW-1.12.1%20(Vanilla)-blue.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Engine Stack](https://img.shields.io/badge/Engine-ClassicAPI%20%7C%20SuperWoW%20%7C%20NamPower%20%7C%20UnitXP%20%7C%20DXVK-green.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
[![Framework Version](https://img.shields.io/badge/OctoWoW-v2.0%20Canonical-brightgreen.svg)](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)

A battle-tested, high-precision architectural framework and system prompt designed for AI coding assistants and reverse engineers to modernize, harden, and build addons natively for the **Enhanced World of Warcraft 1.12.1 Client Extension Stack**.

---

## 🎯 OctoWoW v2.0 Architecture & Core Principles

OctoWoW v2.0 replaces dogmatic, over-prescriptive rules with a **Capability-First**, **Execution-Tiered** engineering model:

1. **Capability-First Development (Zero Artificial Bloat):**
   - The modern stack is guaranteed to be installed.
   - An addon MUST leverage a DLL capability when it delivers measurable improvement in **correctness**, **performance**, **safety**, or **architectural simplicity**.
   - Never force NamPower or UnitXP dependencies into simple or UI-only addons merely to "use the stack."
2. **Four-Tier Execution Performance Model:**
   - **Tier 0 (Load-Time):** `PLAYER_LOGIN` & SavedVariables setup. Clarity & maintainability > micro-optimization.
   - **Tier 1 (Cold Event):** Zone changes & UI toggles. Lightweight allocations permitted.
   - **Tier 2 (Combat Hot Path):** `UNIT_HEALTH`, `UNIT_CASTEVENT`, combat log. Zero closure churn, minimal allocations.
   - **Tier 3 (Per-Frame Path):** `OnUpdate` running 60–144+ FPS. Strict zero allocation. Allowed ONLY for visual interpolation, drag, or animations.
3. **API Priority Ladder & Anti-Hallucination Mandate:**
   - Native Events → Direct Unit Tokens (`target`, `focus`, `nameplateN`) → SuperWoW GUIDs → ClassicAPI C_ APIs → Stack DLL APIs → Cached State → C_Timer → Legacy 1.12 APIs.
   - Absolute prohibition against inventing non-existent API functions or return signatures.
4. **DXVK as Runtime Rendering Environment:**
   - DXVK translates Direct3D 9 to Vulkan for smooth frame pacing and jitter eradication.
   - Addons enforce frame-rate independent math (`elapsed`), explicit FrameXML draw layering (`BACKGROUND`, `BORDER`, `ARTWORK`, `OVERLAY`), and zero texture churn.

---

## ⚡ The Enhanced 1.12.1 Engine Stack

| Component | Minimum Version | Core Capability / Role |
| :--- | :--- | :--- |
| **ClassicAPI** | `v1.13.4+` Mandatory DLL | 550+ functions across ~60 modern retail-style `C_` namespaces (`C_Timer`, `C_NamePlate`, `C_UnitAuras`, `FocusUnit`, `C_Container`), plus `hooksecurefunc`, `table.wipe`, `InCombatLockdown`, and automatic AST rewrites for `#`, `%`, string metatables. |
| **SuperWoW** | `v2.2+` Mandatory DLL | GUID-based unit arguments on all unit functions, `TargetUnit(guid)`, exact-name targeting `TargetByName(name, true)`, `SetMouseoverUnit`, `RAW_COMBATLOG`. |
| **NamPower** | `v4.6.3+` Opt-in DLL | Client-side spell queueing, DBC spell metadata (`GetSpellNameAndRankForId`), binary combat event dispatches. |
| **UnitXP SP3** | `v90+` Opt-in DLL | Real-time uncapped raw numerical health (`UnitXP("health", unit)`), line-of-sight, distance calculation (`UnitXP("distance", unit)`), OS window foregrounding. |
| **DXVK** | `v2.0+` Vulkan Layer | Direct3D 9 to Vulkan translation layer, frametime pacing smoothing, jitter eradication. |
| **VanillaFixes** | Latest Client Patch | High refresh rate animation uncap, modern OS compatibility, raw mouse input fix. |

---

## 🛡️ Mandatory Addon Startup Guard

Every modernized addon must declare an engine dependency check at initialization:

```lua
-- Strict Engine Dependency Guard (Mandatory ClassicAPI v1.13.4+ & SuperWoW v2.2+)
local MIN_CLASSIC_API = 11304

if not (CLASSIC_API_VERSION and SUPERWOW_VERSION) or 
   (type(CLASSIC_API_VERSION) == "number" and CLASSIC_API_VERSION < MIN_CLASSIC_API) then
    DEFAULT_CHAT_FRAME:AddMessage(
        "|cffff2020[Fatal Error]|r " .. (addonName or "Addon") .. 
        " requires ClassicAPI (v1.13.4+) & SuperWoW (v2.2+)! Please ensure both DLLs are loaded.", 
        1, 0.2, 0.2
    )
    return
end
```

---

## 🛠️ Automated Static Scanner & Linter (`octowow_linter.py`)

The repository includes a fast Python heuristic structural and static analysis auditor:

```bash
python tools/octowow_linter.py <path_to_addon_or_file>
```

### Features:
- **Heuristic Structural Scan:** Catches unclosed blocks (`if/end`, `do/end`, `function/end`, `repeat/until`) and bracket mismatches before launching the client.
- **Severity Levels:** Classifies findings into `ERROR` (hard syntax traps / fatal bare colons), `WARNING` (suspect allocations, legacy APIs), and `INFO` (optimization hints).
- **Inline Rule Suppression:** Suppress specific false positives using `-- octowow-ignore: <RULE_ID>` (e.g. `-- octowow-ignore: AP-24` or `-- octowow-ignore: all`).
- **Strict Mode:** Pass `--strict` to treat warnings as errors.

---

## 🚀 How to Use the System Prompt

1. Open [`OCTOWOW_SYSTEM_PROMPT_v2.md`](OCTOWOW_SYSTEM_PROMPT_v2.md) (the canonical v2 prompt).
2. Copy its contents into your AI coding assistant (Claude, ChatGPT, Antigravity, Cursor, Windsurf) as a **System Prompt** or project rule.
3. Use the **10-Step Execution Protocol** to audit, refactor, or build your addon.
4. Run `python tools/octowow_linter.py <addon_path>` to ensure clean structural compliance.
5. In-game: Verify with `/reload`, `/luaerrors 1`, `/etrace`, and `/framestack`.

---

## 👤 Author & Maintainer

- **Maintained by**: [Fostercare5988](https://github.com/Fostercare5988)
- **Repository**: [OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt](https://github.com/Fostercare5988/OctoWoW-Addon-Modernization-Reverse-Engineering-System-Prompt)
