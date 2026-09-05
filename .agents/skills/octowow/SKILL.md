---
name: octowow
description: >-
  Autonomous agent skill for World of Warcraft 1.12.1 Enhanced Engine Addon Modernization and Greenfield Development.
  Enforces OctoWoW v2.0 standards: Capability-First Architecture, 4-Tier Execution Performance Model, ClassicAPI v1.13.4+,
  SuperWoW v2.2+, NamPower v4.6.3+, UnitXP SP3, DXVK Vulkan runtime environment, heuristic static scanning via tools/octowow_linter.py,
  and dual static/runtime verification pipeline.
---

# OctoWoW Addon Modernization & Greenfield Development Skill (v2.0)

Use this skill whenever:
- Modernizing a legacy 2006 World of Warcraft 1.12.1 addon.
- Building a new 1.12.1 addon natively for the enhanced engine stack.
- Auditing an existing addon for memory leaks, GC churn, or compatibility.
- Diagnosing event timing, FrameXML draw layering, or targeting bugs.

Master System Prompt: [`OCTOWOW_SYSTEM_PROMPT_v2.md`](../../OCTOWOW_SYSTEM_PROMPT_v2.md)
Heuristic Static Scanner: `python tools/octowow_linter.py <target_path>`

---

## 1. Core Operating Philosophy (v2.0)
1. **Capability-First Model:** Addons assume the modern stack is present, but consume a DLL capability ONLY when it provides measurable improvements in correctness, performance, safety, or architecture. Never introduce a DLL dependency merely to use it.
2. **Execution Tiers (Hot Path vs Cold Path):**
   - **Tier 0 (Load-Time):** `PLAYER_LOGIN` & SavedVariables. Readability > micro-optimization.
   - **Tier 1 (Cold Event):** Zone changes & UI toggles. Lightweight allocations allowed.
   - **Tier 2 (Combat Hot Path):** `UNIT_HEALTH`, `UNIT_CASTEVENT`, combat log. Zero closure churn, minimal allocations.
   - **Tier 3 (Per-Frame Path):** `OnUpdate` running 60–144+ FPS. Strict zero allocation. Allowed ONLY for visual interpolation, drag, or animations.
3. **API Priority Ladder:** Native Events → Direct Unit Tokens (`target`, `focus`, `nameplateN`) → SuperWoW GUIDs → ClassicAPI C_ APIs → Stack DLL APIs → Cached State → C_Timer → Legacy 1.12 APIs.
4. **Anti-Hallucination Mandate:** Never invent API functions, event names, or version signatures.
5. **Zero "Octo" Branding on GitHub & End-Addons (Stealth Rule):** NEVER mention "Octo", "OctoWoW", "OctoWoW v2", or custom private server names in end-addons, git commits, PRs, or public repos. Commits must use clean, neutral technical phrasing.

---

## 2. 10-Step Execution Protocol
1. **Inventory:** Inspect TOC, Lua files, SavedVariables, and dependencies.
2. **Classify Subsystems:** Mark each component as `KEEP`, `PATCH`, `REFACTOR`, or `REWRITE`.
3. **Capability Map:** Map required features to the highest available API tier.
4. **Hot Path Map:** Identify Tiers 0–3 execution paths.
5. **Change Plan:** Formulate minimal-diff plan before editing.
6. **Implement:** Execute deterministic, self-contained edits.
7. **Static Scan:** Run `python tools/octowow_linter.py <path>`.
8. **Runtime Diagnostics:** Verify in-client using `/reload`, `/luaerrors 1`, `/etrace`, and `/framestack`.
9. **PvP Stress Test:** Test in 10/15/40-man battlegrounds, target spamming, and roster shrink.
10. **Final Audit:** Confirm zero global leaks, explicit draw layering, and no stale fixed-array bleed.

---

## 3. Static Heuristic Scanning
Run the automated OctoWoW scanner:
```bash
python "c:\Users\Fostercare\Documents\System Prompts\tools\octowow_linter.py" "<addon_directory>"
```
- **Exit code 0:** All critical errors passed.
- **Strict Mode (`--strict`):** Treats advisory warnings as errors.
- **Inline Suppression:** Add `-- octowow-ignore: <RULE_ID>` (e.g. `-- octowow-ignore: AP-24`) to suppress verified exceptions.
