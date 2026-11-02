Full VanillaForge audit of the addon $ARGUMENTS, at
C:\Users\Fostercare\Desktop\client-2026-10-10\Interface\AddOns\$ARGUMENTS,
and then the fixes. Follow VANILLAFORGE.md. The active server profile is
servers/octowow.md. DLLs are assumed installed; do not inspect or hash them.

Most of this code is from 2006. Working code is not a reason to keep it: look for
the better solution everywhere, and make it. The result should be as lean, clean
and cheap as it can be while working as well as it can, and nicer to use.

AUDIT
1. git fetch/status. Stop if the repo is not clean and level with origin.
2. Map the load graph from the TOC and XML. Read EVERY loaded file completely.
   Note each file's job, events, timers, OnUpdate handlers, hooks, SavedVariables
   and which UI it owns.
3. Run tools/find_holes.py on the addon (fetch_upstream_docs.py and
   extract_framexml.py first if missing). Its findings are leads.
4. Read the players' side: every character's saved settings for this addon
   (WTF\Account\*\*\*\SavedVariables), !ErrorLog.lua, any /lag data. An option all
   characters leave the same, or that has no reason to be off, is a candidate to
   become permanent and be retired.
5. For each API, event or argument the addon uses, grep the maintainers' docs in
   .private/upstream/ first, then the references, and read only the matching
   section. Flag anything documented in neither, anything used wrongly (arguments,
   return values, states, which containers or units a call supports), and every
   place where a DLL offers better data or events than the stock 1.12 code. Check
   every hardcoded spell ID, item ID, duration and rule against the server
   profile; flag any that came from Blizzard Classic, Wowhead or another server.
6. Find, in every file: bugs (wrong behaviour, stale callbacks, state crossing
   characters, settings applied while disabled, string escapes Lua 5.0 drops);
   modernization (DLL primitives for polling, text scraping, wrapped Set*
   methods, hand-rolled helpers); performance (repeated work per slot or event,
   allocations, unchanged UI writes, layouts redone for nothing); old code
   (`getglobal` and name concatenation per call, `this`/`arg1` decoding by type,
   fallbacks for things that always exist, two files doing one job, copies of one
   routine, hidden globals shared across files, a locale layer); and UI (options
   that do not do what they say, player text, the settings window in the old style).
7. For each kind of finding, search the addon for the rest of that kind.

FIX, in the same session
8. Write one failing lupa reproduction per real bug under regressions/$ARGUMENTS/
   (it must fail on the current code), and a test for each moved path that has
   none. The Bagnon harness in regressions/Bagnon/bgn_env.py is the pattern.
9. Fix everything found, in coherent batches: bugs first, then the old code and
   performance, then options and the settings window (ForgeUI, a short English
   label per option, tooltips for detail, no jargon). Retire options completely:
   code, setting (cleared on load), slash command, docs. Delete dead code, files
   and assets. Keep behaviour and SavedVariables players rely on; say what they
   will notice. Keep each file's line endings; edit files in place with a
   byte-safe patcher, never with tools that rewrite endings or permissions.
10. After each batch: the addon's tests, the linter (tools/audit_addon.py ...
    --run-tests), and a load-order check that every function the XML calls exists.
    Then update README and docs, commit, and push (standing order).
11. Write .private/audit-$ARGUMENTS-<date>.md (under 2 pages): findings ranked
    P1/P2/P3 with file:line, evidence and what was done, what could not be done
    and why, and the in-game checks still needed.

Stop to ask only when a fix needs something the DLLs cannot do (say so, and offer
the options and your recommendation) or would take away something players rely
on. Finish with the in-game checklist.
