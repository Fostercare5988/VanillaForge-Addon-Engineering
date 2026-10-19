# VanillaForge Core

This is the default working contract for addon work. Read it whole; it is short on purpose.
Read the full VANILLAFORGE_SYSTEM_PROMPT.md only when asked to run a **Gate** or
**Framework** pass.

## Target

WoW 1.12.1 (build 5875, Interface 11200) on OctoWoW, with ClassicAPI 1.16.0+,
SuperWoW 2.2+, NamPower 4.6.2+ and UnitXP SP3 v89+. Treat these as installed and
loaded. **Do not inspect, hash or verify DLLs or client files.** The user says when
a DLL changes.

Lua is 5.0: no `#` (use `table.getn`), varargs use `arg`, `string.gfind` not
`gmatch`. Handlers use the globals `this`, `event`, `arg1`... unless an extension
documents otherwise.

## Rules

1. **Never invent an API.** Before using a function, event, argument or return value
   you have not seen in this addon, search the references. Use grep for the name and
   read only the matching section. Never read a reference file whole.
   - ClassicAPI: `CLASSICAPI_MASTER_REFERENCE.md`
   - SuperWoW, NamPower, UnitXP, FrameXML behavior: `ENGINE_REFERENCE.md`
   - Recurring hazards: `KNOWN_PATTERNS.md`

   If the answer is not there, say so and mark the code `-- UNVERIFIED: test in game`.
2. Change only what the task needs. Keep existing behavior, settings and
   SavedVariables unless asked to change them.
3. Prefer events and timers over OnUpdate polling, except for animation and dragging.
4. English for code, comments and player text. Settings use the dark plum and
   lavender theme unless told otherwise.

## Session habits

- Start: `git fetch` and `git status` in each repo you touch. Report if anything is
  ahead, behind or uncommitted before editing.
- One task per session. No reports, audits or evidence files unless asked.
- Before committing: `python -B tools/vanillaforge_linter.py "<addon folder>"`.
  Treat findings as hints, not orders.
- End: summarize what changed and what to check in game. Commit and push only when
  the user says so. Never force-push.

## Levels

- **Tinker** (default): this file only.
- **Gate** ("this version is good"): full contract, `tools/audit_addon.py`, the addon's
  regression tests, version bump, in-game checklist, commit, tag, push.
- **Framework**: change VanillaForge itself, only when the user asks.
