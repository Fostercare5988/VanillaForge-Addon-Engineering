---
name: octowow
description: >-
  Autonomous agent skill for World of Warcraft 1.12.1 Enhanced Engine Addon Modernization and Greenfield Development.
  Enforces OctoWoW v2.1 standards: Capability-First Architecture, 4-Tier Execution Performance Model, ClassicAPI v1.15.0+ (v1.14.0+ baseline),
  SuperWoW v2.2+, NamPower v4.6.3+, UnitXP SP3, DXVK Vulkan runtime environment, heuristic static scanning via tools/octowow_linter.py,
  and dual static/runtime verification pipeline.
---

# OctoWoW Addon Modernization & Greenfield Development Skill (v2.1)

Use this skill whenever:
- Modernizing a legacy 2006 World of Warcraft 1.12.1 addon.
- Building a new 1.12.1 addon natively for the enhanced engine stack.
- Auditing an existing addon for memory leaks, GC churn, or compatibility.
- Diagnosing event timing, FrameXML draw layering, or targeting bugs.

Master System Prompt: [`OCTOWOW_SYSTEM_PROMPT.md`](../../OCTOWOW_SYSTEM_PROMPT.md)
Heuristic Static Scanner: `python tools/octowow_linter.py <target_path>`

---

## 1. Core Operating Philosophy (v2.1)
1. **Capability-First Model:** Addons assume the modern stack is present, but consume a DLL capability ONLY when it provides measurable improvements in correctness, performance, safety, or architecture. Never introduce a DLL dependency merely to use it.
2. **Execution Tiers (Hot Path vs Cold Path):**
   - **Tier 0 (Load-Time):** `PLAYER_LOGIN` & SavedVariables. Readability > micro-optimization.
   - **Tier 1 (Cold Event):** Zone changes & UI toggles. Lightweight allocations allowed.
   - **Tier 2 (Combat Hot Path):** `UNIT_HEALTH`, `UNIT_CASTEVENT`, combat log. Zero closure churn, minimal allocations.
   - **Tier 3 (Per-Frame Path):** `OnUpdate` running 60–144+ FPS. Strict zero allocation. Allowed ONLY for visual interpolation, drag, or animations.
3. **API Priority Ladder:** Native Events → Direct Unit Tokens (`target`, `focus`, `nameplateN`) → SuperWoW GUIDs → ClassicAPI C_ APIs (including `C_Container` sorting in v1.15.0+) → Stack DLL APIs → Cached State → C_Timer → Legacy 1.12 APIs.
4. **Anti-Hallucination Mandate:** Never invent API functions, event names, or version signatures.
5. **Zero "Octo" Branding on GitHub & End-Addons (Stealth Rule):** NEVER mention "Octo", "OctoWoW", "OctoWoW v2", or custom private server names in end-addons, git commits, PRs, or public repos. Commits must use clean, neutral technical phrasing.
6. **1.12.1 Client vs. 1.18.1 Content Patch:** The client and Lua API is ALWAYS strictly 1.12.1. 1.18.1 is only server-side content; never gate addon logic on 1.18.1.
7. **Event Parameter Shadowing Trap (Rule C12 / AP-26):** NEVER declare `(self, event, arg1)` on event handlers. In WoW 1.12.1 XML (`<OnEvent>Func(event);</OnEvent>`) and `:SetScript("OnEvent")` (0-arg), unpassed parameters evaluate to `nil` and shadow globals `_G.event` and `_G.arg1`, silently bricking `ADDON_LOADED` initialization. Always use neutral parameter names (`arg1_param, arg2_param, arg3_param`) with dual-convention fallback.
8. **Title-Bar Button Geometry & Texture Scaling (Rule C13 / AP-28):** Header action buttons (e.g. Sort, Settings) must anchor relative to sibling controls via `point="CENTER" relativeTo="<SiblingButton>" relativePoint="CENTER"` with `y="0"` and an explicit horizontal gap ($\ge 4\text{px}$)—never eyeballed static `TOPRIGHT` offsets. Buttons must enforce `setAllPoints="true"` on `<NormalTexture>` and `<PushedTexture>` to prevent unscaled 1.12.1 corner clipping, use circular highlights (`UI-Panel-MinimizeButton-Highlight`), and provide distinct tactile metallic bezels.
9. **In-Game Notification Tone & Zero Meta-Jargon (Rule C14 / AP-29):** Modern DLL actions execute in milliseconds. Never use progressive ellipsis (`"Sorting..."`) which implies slow 2006 Lua loops; use direct past-tense confirmation (`"Bagnon: Bags sorted."`). Never leak technical implementation or developer terms (`"C++"`, `"ClassicAPI"`, `"coroutine"`, `"DLL"`) into player-facing chat or tooltips.

---

## 2. Dual-Mode Execution Protocol
- **Mode A: 10-Step Legacy Modernization:**
  1. Inventory TOC, Lua, SavedVariables.
  2. Classify components: `KEEP`, `PATCH`, `REFACTOR`, `REWRITE`.
  3. Capability Map to native stack primitives.
  4. Hot Path Map (Tiers 0–3).
  5. Formulate minimal-diff Change Plan.
  6. Implement deterministic edits.
  7. Run Static Scan (`octowow_linter.py`).
  8. In-client Runtime Diagnostics (`/reload`, `/luaerrors 1`, `/etrace`, `/framestack`).
  9. PvP Stress Test (10/15/40-man battlegrounds, target spamming, roster shrink).
  10. Final Audit & Knowledge Sync Gate.
  - *Emergency Fast-Path Exception (Rule F7):* For urgent live hotfixes, apply scoped fix only, defer docs/sync, and report `Knowledge Evolution: [DEFERRED — fast scoped patch per Rule F7]`.
- **Mode B: Greenfield Scaffolding:** Canonical layout (`<Addon>.toc`, `Core.lua`, `Options.lua`, `README.md`), pre-allocated state tables, hardware timers (`C_Timer`), card mouse isolation, and linter pass.

---

## 3. Static Heuristic Scanning & Verification
Run the automated OctoWoW scanner:
```bash
python "c:\Users\Fostercare\Documents\System Prompts\tools\octowow_linter.py" "<addon_directory>"
```
- **Rule G5 (Linter Floor):** The linter is a regex/structural scanner, not a full Lua compiler. 0 errors / 0 warnings is necessary, but MUST be paired with an in-client `/reload` smoke test.
- **Exit code 0:** All critical errors passed.
- **Strict Mode (`--strict`):** Treats advisory warnings as errors.
- **Inline Suppression:** Add `-- octowow-ignore: <RULE_ID>` (e.g. `-- octowow-ignore: AP-24`) to suppress verified exceptions.
