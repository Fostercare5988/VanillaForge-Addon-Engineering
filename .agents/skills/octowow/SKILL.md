---
name: octowow
description: >-
  Autonomous agent skill for World of Warcraft 1.12.1 Enhanced Engine Addon Modernization and Greenfield Development.
  Enforces ClassicAPI v1.13.3+, SuperWoW v2.2+, NamPower v4.6.2+, UnitXP SP3, DXVK frame pacing, zero-GC memory recycling,
  automated AST & static linting via tools/octowow_linter.py, and single-branch git standardization.
---

# OctoWoW Addon Modernization & Greenfield Development Skill

Use this skill whenever:
- Modernizing a legacy 2006 World of Warcraft 1.12.1 addon.
- Building a new 1.12.1 addon from scratch using modern engine capabilities.
- Auditing an existing addon for memory leaks, GC churn, or compatibility.
- Synchronizing an addon with the latest ClassicAPI / SuperWoW DLL updates.

Master System Prompt: [`OCTOWOW_SYSTEM_PROMPT.md`](../../OCTOWOW_SYSTEM_PROMPT.md)
Automated Static Auditor: `python tools/octowow_linter.py <target_path>`

---

## 1. Automated Static Linting (The Gatekeeper)
Before modifying or after touching any Lua file, run the automated OctoWoW linter:
```bash
python "c:\Users\Fostercare\Documents\System Prompts\tools\octowow_linter.py" "<addon_directory>"
```
The linter validates:
- Lua AST syntax & block nesting balance (`if/end`, `do/end`, `function/end`, `repeat/until`).
- Rule B1 Mandatory Startup Guard (`CLASSIC_API_VERSION and SUPERWOW_VERSION`).
- Rule A1 bare colon method prevention (`f:GetScript` crash protection).
- Rule B3 tooltip scraping elimination.
- Rule B10 unconditional native C++ `table.wipe` enforcement.
- Rule C8 mouse passthrough on child cooldown models and textures.
- Rule D1 zero-GC register tail recursion hierarchy scanning.
- Rule H5 README documentation compliance & raw WoW color escape code eradication.
- Rule H7 modular directory architecture (eradication of legacy Locales/ folders & separation of <Addon>Opt.lua).
- Clean DXVK standard notation without redundant "144Hz+" marketing buzzwords.

---

## 2. Mode Identification (Part J)
- **Mode A: Legacy Modernization:**
  1. Deep audit & kill 2006 bloat (tooltip scanning, chat regexes, OnUpdate polling).
  2. Wire modern C_Namespaces (`C_Timer`, `C_UnitAuras`, `C_GossipInfo`), native `table.wipe`, and `TargetUnit(guid)`.
  3. Run linter until 0 issues / 0 warnings remain.
  4. Generate Rule H5 README and commit to a single branch (`main` or `master`).
  5. **Phase 5 (Mandatory Gate)**: Compare all fixes against Part I. If novel anti-patterns were resolved, append them to `OCTOWOW_SYSTEM_PROMPT.md`, update `tools/octowow_linter.py`, and push to GitHub before concluding.
- **Mode B: Greenfield Scaffolding:**
  1. Scaffold canonical structure: `<Addon>.toc`, `Core.lua`, `UIElements.lua`, `README.md`.
  2. Pre-allocate all combat state tables and sort buffers at file load time.
  3. Use `C_Timer.After` / `C_Timer.NewTicker` for all delayed/recurring tasks.
  4. Build UI with `:EnableMouse(false)` on non-interactive children.
  5. Validate with linter and push to GitHub.
  6. **Phase 6 (Mandatory Gate)**: Register new reusable patterns or boilerplate in Part I.

---

## 3. Golden Anti-Patterns & Battle-Tested Diffs (Part I)
- Always refer to Part I in `OCTOWOW_SYSTEM_PROMPT.md` for verified code templates.
