# VanillaForge

**Goal:** build and modernize World of Warcraft 1.12.1 addons that are lean,
clean and modern: at least as good as the best modern addon that does the same
job. They take their data and events from the client's extension DLLs, do as
little work per frame as possible, and are correct for the server they are
played on.

This file is the whole working contract. Everything else here is reference
material: search it for the question at hand, never read it whole.

## How we think

We audit, clean, refactor, improve, develop and maintain. The work is not done
when the code runs; it is done when nothing in it can be done better. An audit
does not end with a list: it ends with the fixes made, tested and pushed.

- **Every line earns its place.** Deleting is the best fix. Code nobody uses,
  code for things that do not exist, and options nobody turns on are holes.
- **The DLLs first.** When a DLL does it, ours goes. Ask the docs before
  writing a line, and again when reading old code: they grow every release.
- **Low coupling, high cohesion.** Each addon owns its data; each module does
  one job. Every connection between addons is visible, narrow and deliberate.
  A hidden connection is a hole.
- **Old is a question, not a verdict.** Most of this code is from 2006. Working
  code still gets asked: why is this here, is there a better way now (a DLL, an
  event, a smaller design)? When there is, replace it. "It works" is not a reason
  to keep it; "players rely on it" is, and that means behaviour and settings,
  not the lines that produce them.
- **Today's best is the yardstick, not 2006.** Asking "what is wrong with these
  lines?" finds only what the old design allows; modern calls in an old shape
  pass it. Ask "how would this be built today?" and compare with a modern addon
  doing the same job (Classic Era or later: GearRack's are ItemRack Classic and
  TrinketMenu). That finds the design holes: what it stores, what it waits for,
  how its files split the work.
- **Wonder.** Read the players' settings, the error log and the stutter report.
  The best findings come from asking what is really used and what really costs.
- **Evidence beats memory.** Docs, measurements and tests decide; a guess is
  marked as one until the game confirms it.

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
`string.match`/`gmatch`, string methods, `table.wipe`. Write them, never the 5.0
forms they replace: `%` not `mod`, `gmatch` not `gfind`, `#s` not `string.len`,
`...` not `unpack(arg)` (linter rule A4). `#` is not `table.getn`; leave
`table.getn` where code relies on it. Handlers always get `this`, `event` and
`arg1`...; positional `(self, event, ...)` arguments usually work too. Follow
the addon's existing convention. Details: CLASSICAPI_MASTER_REFERENCE.md §4.

## 2. How the addons are written

- **Use the DLLs.** Structured events, GUIDs and the `C_` APIs beat tooltip
  scraping, combat-log text parsing, name matching, target swapping and polling.
  Pick the provider by verified behaviour and cost, not by habit.
- **Start from a modern addon, not the 2006 one.** ClassicAPI aims to run
  Classic Era addons "with little or no change" (its README), so a modern addon
  that does the job is the design to build towards, and its code may be ported
  when its license allows (credit its authors, as EasyPoisons credits Horyoshi).
  A new addon starts by looking for one. It was still written for another client:
  every function, event, argument and widget method it calls must be in the DLL
  docs (§1 rule 4), its Lua must run on 5.0 with the backports, its game data
  (spell and item IDs, durations, talent tables) is Classic Era's and is never
  taken over (§1 rule 2), and its locale layer, libraries and settings panel go
  (ForgeUI, below).
- **Events and timers, not OnUpdate,** except for animation and dragging.
  Work that runs while nothing changes is a hole even when it measures cheap:
  wake on the event, or at the moment something will next change (a label's
  next text, a cooldown's end), and sleep otherwise.
  Coalesce bursts into one refresh per frame. Skip UI writes that change nothing.
  Avoid allocations in hot paths (combat, auras, health, nameplates, bags).
- **Never block a frame.** Big scans and rebuilds are split across frames in
  small, time-limited batches.
- **No dead weight.** No stock-client fallbacks, compatibility libraries or
  locale layers. In the code you touch, remove displaced helpers, dead branches
  and options that do nothing.
- **Retire features completely:** code, option, default, slash command and docs
  together, and clear the old saved setting: one sweep at load clears every saved
  key nothing owns, so the retired key needs no line of its own (KNOWN_PATTERNS
  KP-64).
- **Learn the server's numbers instead of assuming them.** A duration or rule the
  server decides (capture times, respawns, invite windows, cooldowns) is either
  verified against the server profile, or measured from events in play and
  saved, like AutoBG's flag spots. A value that is still a guess looks like
  one to the player (AutoBG's `~`), and it stops looking like a guess as soon
  as evidence arrives.
- **Fix the kind, not just the case.** After finding a problem, search the whole
  addon by pattern for others of the same kind, not only the path where it
  showed or was measured, and fix them all.
- **Keep what players rely on.** Keep behaviour players notice and their
  SavedVariables, or migrate or clear them on purpose. The code itself is not
  protected: rewrite old working code when the result is leaner, clearer or
  cheaper, and say in the report what players will notice.
- **Own your state.** Asynchronous work tracks its current request and ignores
  stale callbacks. Each addon owns its own data; integrations with other addons
  check availability and use narrow public functions.
- **Settings:** use the ForgeUI kit in `templates/ForgeUI/` (see
  [KNOWN_PATTERNS.md](KNOWN_PATTERNS.md#preferred-settings-theme)). Pages are
  built as sections (`ForgeLayout.lua`) and every page is also in AddOn Options,
  one column at full size (`/options <Addon>`). Every option
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
  and which addon and line; garbage collections, whether they hit a stutter and
  inside which addon they started; Lua memory; and each addon's CPU and new Lua
  memory per second (the addons that make the most memory bring collections on).
- The data is saved in `WTF\Account\<account>\SavedVariables\!ErrorLog.lua` on
  `/reload` or logout, so it can be read directly.

A stutter with almost no addon time is the engine (model loading, shader
compiles, drawing), not addon code. Fix measured problems first.

**Game checks close the loop.** Every question only the game can answer is a
check: an `-- UNVERIFIED:` note in the code or an item under an audit's "In-game
checks". `python -B tools/game_checks.py` lists the open ones; `push` (game
closed) hands them to `!ErrorLog`, where `/check` asks them one by one, runs a
check's `/run` line and records the answer; `pull` reads the answers back.
`find_holes.py` starts each audit with the addon's open and failed checks. A
check answered bad is a bug to fix; one answered ok lets its note go; `drop`
gives up the open ones nobody will answer. The tool reads the comment lines after
an `UNVERIFIED:` note as part of it: put the note last in its comment block.

## 4. Audit: find the holes, then close them

Start every audit with the hole finder; it reads the addon next to all the
others, the game's own code, the DLL docs and every character's saved settings:

```text
python -B tools/find_holes.py "<addon folder>"
```

It needs `python -B tools/fetch_upstream_docs.py` and
`python -B tools/extract_framexml.py --client "<client>" --all` once. Its
findings are leads; read the code before acting. So are earlier audits: what
they kept, and why, is asked again, not inherited (FostercareTweaks' Vendor Values
was kept for a reason the docs contradict). Each reason an audit keeps something
cites its evidence (a doc section, a FrameXML file:line, a measurement), so the
next audit checks it instead of trusting it. Then answer every question
below, in this order, and write the answers in `.private/audit-<Addon>-<date>.md`:

1. **How would it be built today?** Compare with the addon's reference addons
   (named in its `CLAUDE.md`; when none is, find the most used modern addon for
   the job on CurseForge or GitHub, write it there and name it in the report;
   ask the user only when nothing fits): what each saves
   per item, set and character, which events it listens to, when it wakes, how
   its files split the work, what players can do with it. Every gap is a
   finding, and so is anything ours does that it does not need. Of each saved
   record: does it tell apart what the player can (two copies of one item, two
   ranks of one spell)?
2. **What is unused?** Files, functions, images, options no character turns on,
   saved settings no code reads.
3. **What does a DLL do now?** Search the docs for the job, not just the name.
   Add each new find to [tools/replacements.json](tools/replacements.json).
4. **What reaches into another addon?** Globals read across addons, aliases,
   shared tables. Make each connection visible and narrow, or remove it.
5. **What is old or stale?** Code for other clients or missing libraries,
   "unverified" notes the docs now cover, old migrations, version drift.
6. **What runs while nothing changes?** Every repeating timer and OnUpdate (the
   hole finder lists them): what does it wait for, and does it stop when nothing
   will change? Cheap is not a reason to keep one: fix the shape, then the cost
   (§2). The game's own code counts too where the addon takes its frames over:
   the hole finder lists the FrameXML OnUpdates on frames the addon touches
   (FostercareTweaks' 72 action buttons, 2026-11-13). Also garbage built on hot
   paths (Lua 5.0 collects in one full pass).
7. **What do players see and use?** Their settings, errors and stutters; what is
   confusing in the settings window. An option every character leaves alone, or
   that has no reason to be off, becomes permanent: retire it (§2).
8. **What is just old?** The 2006 habits: `getglobal` and name concatenation per
   call, handlers that decode `this` or `arg1` by type, wrapped `Set*` methods
   where a script event exists, fallbacks for things that always exist, two files
   doing one job or one file doing several, two routines doing one job, the same
   work repeated per slot or per event, tables built per call, settings windows
   in the old style (move them to ForgeUI).
9. **Of each finding: is it a kind?** Search the whole addon by pattern for the
   rest of that kind (§2).

Then fix everything the audit found, in one pass of coherent batches: the
bugs, the old code, the options that should not exist, the settings window. Each
batch ends with the checks in §5; commit and push it. Stop to ask only when a
fix needs something the DLLs cannot do (say so and offer the options), or would
take away something players rely on.

## 5. Before calling it done

1. From the VanillaForge folder, lint and run the addon's regression tests:

   ```text
   python -B tools/audit_addon.py "<addon folder>" --run-tests --test-start regressions/<Addon> --output "%TEMP%\audit-<Addon>.json"
   ```

   Lint findings are hints, not orders, but read the warning count as well as the
   error count (rule A5 catches string escapes Lua 5.0 drops, as a warning). Without
   a suite, the linter alone: `python -B tools/vanillaforge_linter.py "<addon folder>"`.
2. When behaviour changes on purpose, update the test that encoded the old
   behaviour. For a bug fix, add a test that fails on the old code where
   practical, and prove it: `python -B tools/run_suite.py <Addon> <test file>
   --old <commit>` runs it against the addon at that commit (unpacked, never
   stashed) and gives each failure's first error line, so a test that only
   fails in its own setup shows. Without `--old` it runs one file or the suite.
   Suites and their commands: [regressions/README.md](regressions/README.md).
3. Keep each file's line endings (several addons use CRLF). Patch addon files with
   [tools/addon_edit.py](tools/addon_edit.py): it keeps the endings and the
   backslashes of Lua paths (the `@@` placeholder writes two, KNOWN_PATTERNS KP-60;
   `@/` writes one, for a TOC line or an XML file path).
4. Report what changed, the test results and what to check in game. Tests are
   not in-game proof; say which behaviour still needs a game check.
5. Git: run `git status` before editing. Commit each coherent step after its
   checks pass. Push every commit after its checks pass (user's standing order, 2026-11-01).
   Force-push only to take something out of a repo's history when the user asks
   for that: bundle the repo first (`git bundle create ... --all`), push with
   `--force-with-lease`, and say what was rewritten. Never to get past a
   rejected push (user's order, 2026-11-09).

## 6. Where things are

| Need | Where |
| --- | --- |
| A ClassicAPI function, event or argument | [CLASSICAPI_MASTER_REFERENCE.md](CLASSICAPI_MASTER_REFERENCE.md) |
| SuperWoW, NamPower, UnitXP, native UI behaviour | [ENGINE_REFERENCE.md](ENGINE_REFERENCE.md) |
| A recurring bug or performance hazard | [KNOWN_PATTERNS.md](KNOWN_PATTERNS.md) |
| Old ways a DLL now does better | [tools/replacements.json](tools/replacements.json), read by `tools/find_holes.py` |
| Server facts and data sources | [servers/](servers/) |
| An addon's regression tests | [regressions/README.md](regressions/README.md); one file, or on an old commit: `tools/run_suite.py` |
| The game's Lua and engine model for tests | `regressions/wowlua.py`, `regressions/wowkit.py` |
| What only the game can answer, and the answers | `python -B tools/game_checks.py`; `/check` in `!ErrorLog` |
| The settings style | `templates/ForgeUI/` |
| DLL versions and upstream tracking | [UPSTREAM_VERSIONS.json](UPSTREAM_VERSIONS.json), `python -B tools/check_upstream.py` |
| Patch addon files safely | [tools/addon_edit.py](tools/addon_edit.py) |
| Take a new DLL release | `python -B tools/upgrade_dll.py [component] [--pin]`: what changed, the pin, leads in every addon |
| Earlier audits, workflows and decisions | [archive/](archive/README.md), for history only |

## 7. Keeping VanillaForge lean

- One fact lives in one place. Improve an existing entry before adding one.
- DLL versions live only in UPSTREAM_VERSIONS.json, always the latest release.
  Addons check that a DLL is loaded in code (a guard file), never its version,
  and their TOC (no `## Dependencies: !!!ClassicAPI`: the tooltip shows it), README
  and headers name no version, so a release changes no addon file by itself.
- Add a known pattern only when a hazard recurs and is not covered already.
- Facts about one addon belong in that addon's `CLAUDE.md`, not here. That file
  stays local: every repo, this one too, ignores `CLAUDE.md`, `AGENTS.md` and
  `.claude/`.
- "Maintained" means one thing in every tool: an installed addon with a suite
  in `regressions/`.
- Facts about one server belong in its profile. A new server starts from
  [servers/TEMPLATE.md](servers/TEMPLATE.md).
