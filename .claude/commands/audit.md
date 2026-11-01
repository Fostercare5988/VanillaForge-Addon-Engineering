Full VanillaForge audit of the addon $ARGUMENTS, at
C:\Users\Fostercare\Desktop\client-2026-10-10\Interface\AddOns\$ARGUMENTS.
Follow VANILLAFORGE.md. The active server profile is servers/octowow.md.
DLLs are assumed installed; do not inspect or hash them.

PHASE 1 — AUDIT ONLY. Do not edit the addon.
1. git fetch/status. Stop if the repo is not clean and level with origin.
2. Map the load graph from the TOC and XML. Read EVERY loaded file completely.
   List each file's job, events, timers, OnUpdate handlers, hooks, SavedVariables
   and which UI it owns.
3. For each API, event or argument the addon uses, grep the maintainers' docs in
   .private/upstream/ first (run tools/fetch_upstream_docs.py if missing), then the
   references (CLASSICAPI_MASTER_REFERENCE.md, ENGINE_REFERENCE.md, KNOWN_PATTERNS.md),
   and read only the matching section. Flag anything documented in neither, anything
   the code gets wrong (arguments, return values, states), and places where a DLL
   offers better data or events than the stock 1.12 code uses. Check every
   hardcoded spell ID, item ID, duration and rule against the server profile's
   sources; flag any that came from Blizzard Classic, Wowhead or another server.
4. Find:
   a) bugs: wrong behavior, stale callbacks, state crossing profiles/characters,
      settings applied while disabled, missing cleanup;
   b) modernization: places where the latest ClassicAPI (UPSTREAM_VERSIONS.json), SuperWoW, NamPower or UnitXP
      provide a verified, simpler or cheaper primitive than current code (polling,
      text scraping, name matching, hand-rolled helpers, dead fallbacks), and any
      locale layer (English only; linter rule L1);
   c) performance: hot paths (combat events, OnUpdate, bag/unit bursts) with
      repeated work, allocations or unchanged UI writes;
   d) UI/settings: one owner per surface, options that don't do what they say,
      settings theme, player-facing text.
5. For each serious bug, write a small lupa reproduction under
   regressions/$ARGUMENTS/ that FAILS on the current code.
6. Write the findings to .private/audit-$ARGUMENTS-<date>.md. Rank them
   P1 (breaks play) / P2 (wrong behavior) / P3 (polish or perf). For each one give
   file:line, evidence, the proposed fix and its risk. List the in-game checks that
   are still needed. Keep it under 2 pages.

Then STOP and show me the ranked list. Wait for me to choose what to fix.

PHASE 2 (only after I choose): fix one batch at a time. After each batch the
regression must pass, the linter must pass and Lua 5.0 syntax must be kept.
Give me an in-game checklist. Commit per batch and push only when I say.
