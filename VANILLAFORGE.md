# VanillaForge

**Goal:** build and modernize World of Warcraft 1.12.1 addons that are lean,
clean and modern. They take their data and events from the client's extension
DLLs, do as little work per frame as possible, and are correct for the server
they are played on.

This file is the whole working contract. Everything else here is reference
material: search it for the question at hand, never read it whole.

## 1. Know the target before writing code

An addon runs on three layers. Each answers different questions and has its
own source of truth:

| Layer | Decides | Source of truth |
| --- | --- | --- |
| **Client engine:** WoW 1.12.1, build 5875, Interface 11200 | Lua syntax, widgets, FrameXML, handler conventions | [ENGINE_REFERENCE.md](ENGINE_REFERENCE.md); native FrameXML via `tools/extract_framexml.py` |
| **Extension DLLs:** ClassicAPI, SuperWoW, NamPower, UnitXP SP3 (minimums in [UPSTREAM_VERSIONS.json](UPSTREAM_VERSIONS.json)) | Which functions, events and arguments exist | The maintainers' docs in `.private/upstream/` (`python -B tools/fetch_upstream_docs.py`), then [CLASSICAPI_MASTER_REFERENCE.md](CLASSICAPI_MASTER_REFERENCE.md) and [ENGINE_REFERENCE.md](ENGINE_REFERENCE.md) |
| **Server:** the active profile in [servers/](servers/) | Game data: spell and item IDs, durations, cooldowns, talents, battleground rules, custom content | The sources listed in that server's profile, then in-game checks |

Rules, in order of importance:

1. **Know the server first.** The workspace `CLAUDE.md` names the active server
   profile. If none is named, ask. Never assume a server.
2. **Game data comes only from the active server's sources.** Never take IDs,
   durations, cooldowns, ranks, talent numbers or battleground rules from
   Blizzard Classic (Classic Era, Season of Discovery, Hardcore, Retail),
   Wowhead, other private servers (Turtle WoW and the like) or memory. Servers
   change spells, items and rules; a matching name or icon proves nothing. If
   the profile's sources do not have it, write `-- UNVERIFIED: test in game`
   and give a one-line check, such as `/run print(GetSpellInfo(12345))`.
3. **Prefer reading data at runtime over hardcoding it.** Ask the client and DLLs
   for names, IDs and durations where an API gives them (spell info, aura data,
   NamPower spell events with IDs). When a table is unavoidable, cite its source
   in a comment.
4. **APIs come only from the DLL docs and these references.** Blizzard's modern
   API documentation (warcraft.wiki.gg, the Classic API) describes a different
   client: the same function name can take other arguments or behave
   differently here. Never invent a function, event, argument or return value;
   grep the docs for the exact name first. If it is not documented, say so and
   mark it unverified.
5. **Treat the DLLs as installed.** Do not inspect, hash or verify them or the
   client installation; the user says when one changes. Extracting FrameXML is
   fine, and so is reading config and log files when the user asks for help
   with performance or graphics.

The client and the server are English only: no localization, locale tables or
`GetLocale()` branches. Modernizing an addon removes its locale layer.

Lua is 5.0 with ClassicAPI's 5.1 backports: `#t`, `...`, `select`, `%`,
`string.match`/`gmatch`, string methods. `#` is not `table.getn`; leave
`table.getn` where code relies on it. Handlers always get `this`, `event` and
`arg1`...; positional `(self, event, ...)` arguments usually work too. Follow
the addon's existing convention. Details: CLASSICAPI_MASTER_REFERENCE.md §4.

## 2. How the addons are written

- **Use the DLLs.** Structured events, GUIDs and the `C_` APIs beat tooltip
  scraping, combat-log text parsing, name matching, target swapping and polling.
  Pick the provider by verified behaviour and cost, not by habit.
- **Events and timers, not OnUpdate,** except for animation and dragging.
  Coalesce bursts into one refresh per frame. Skip UI writes that change nothing.
  Avoid allocations in hot paths (combat, auras, health, nameplates, bags).
- **Never block a frame.** Big scans and rebuilds are split across frames in
  small, time-limited batches.
- **No dead weight.** No stock-client fallbacks, compatibility libraries or
  locale layers. In the code you touch, remove displaced helpers, dead branches
  and options that do nothing.
- **Retire features completely:** code, option, default, slash command and docs
  together, and clear the old saved setting (set it to `nil` on load).
- **Learn the server's numbers instead of assuming them.** A duration or rule the
  server decides (capture times, respawns, invite windows, cooldowns) is either
  verified against the server profile, or measured from events in play and
  saved, like AutoBG's invite window. A value that is still a guess looks like
  one to the player (AutoBG's `~`), and it stops looking like a guess as soon
  as evidence arrives.
- **Fix the kind, not just the case.** After finding a problem, search the addon
  for others of the same kind and list them with the fix. Fix them all when the
  user asked for that kind of fix; otherwise ask once with the full list.
- **Keep what works.** Change only what the task needs; keep existing behaviour
  and SavedVariables unless asked. Old but correct code is not a reason to
  rewrite.
- **Own your state.** Asynchronous work tracks its current request and ignores
  stale callbacks. Each addon owns its own data; integrations with other addons
  check availability and use narrow public functions.
- **Settings:** use the ForgeUI kit in `templates/ForgeUI/` (see
  [KNOWN_PATTERNS.md](KNOWN_PATTERNS.md#preferred-settings-theme)). Every option
  needs a real player benefit. Player text is short and factual, with no
  developer jargon.
- Recurring hazards and their fixes are in [KNOWN_PATTERNS.md](KNOWN_PATTERNS.md).

## 3. Measure in game

Static checks cannot see frame time, so evidence from the game decides
performance questions. The `!ErrorLog` addon
([Fostercare5988/ErrorLog](https://github.com/Fostercare5988/ErrorLog)) is the
measuring tool:

- `/err` lists every Lua error with its stack, zone and count.
- `/lag on` starts the stutter profiler (it reloads the UI), `/lag` shows the
  report, `/lag clear` starts fresh, `/lag off` stops it.
- The report gives, for every frame over 100 ms, how much of it was addon code
  and which addon and line; garbage collections and whether they hit a stutter;
  Lua memory; and each addon's CPU per second.
- The data is saved in `WTF\Account\<account>\SavedVariables\!ErrorLog.lua` on
  `/reload` or logout, so it can be read directly.

A stutter with almost no addon time is the engine (model loading, shader
compiles, drawing), not addon code. Fix measured problems first.

## 4. Before calling it done

1. From the VanillaForge folder, lint and run the addon's regression tests:

   ```text
   python -B tools/audit_addon.py "<addon folder>" --run-tests --test-start regressions/<Addon> --output "%TEMP%\audit-<Addon>.json"
   ```

   Lint findings are hints, not orders. Without a suite, the linter alone:
   `python -B tools/vanillaforge_linter.py "<addon folder>"`.
2. When behaviour changes on purpose, update the test that encoded the old
   behaviour. For a bug fix, add a test that fails on the old code where
   practical. Suites and their commands: [regressions/README.md](regressions/README.md).
3. Keep each file's line endings (several addons use CRLF).
4. Report what changed, the test results and what to check in game. Tests are
   not in-game proof; say which behaviour still needs a game check.
5. Git: run `git status` before editing. Commit each coherent step after its
   checks pass. Push only when the user says so. Never force-push.

## 5. Where things are

| Need | Where |
| --- | --- |
| A ClassicAPI function, event or argument | [CLASSICAPI_MASTER_REFERENCE.md](CLASSICAPI_MASTER_REFERENCE.md) |
| SuperWoW, NamPower, UnitXP, native UI behaviour | [ENGINE_REFERENCE.md](ENGINE_REFERENCE.md) |
| A recurring bug or performance hazard | [KNOWN_PATTERNS.md](KNOWN_PATTERNS.md) |
| Server facts and data sources | [servers/](servers/) |
| An addon's regression tests | [regressions/README.md](regressions/README.md) |
| The settings style | `templates/ForgeUI/` |
| DLL versions and upstream tracking | [UPSTREAM_VERSIONS.json](UPSTREAM_VERSIONS.json), `python -B tools/check_upstream.py` |
| Earlier audits, workflows and decisions | [archive/](archive/README.md), for history only |

## 6. Keeping VanillaForge lean

- One fact lives in one place. Improve an existing entry before adding one.
- Add a known pattern only when a hazard recurs and is not covered already.
- Facts about one addon belong in that addon's `CLAUDE.md`, not here.
- Facts about one server belong in its profile. A new server starts from
  [servers/TEMPLATE.md](servers/TEMPLATE.md).
