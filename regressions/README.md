# Addon regressions

Behaviour tests for the maintained addons. They read the installed addon (they
hold no copy of it) and run its real files against a model of the game. The
framework's own tests are in `tests/` and need no game. Python and `lupa`.

Run one suite from VanillaForge; the runner reports the count and the result:

```text
python -B tools/audit_addon.py "<AddOns>/<Addon>" --run-tests --test-start regressions/<Addon> --output "%TEMP%\audit-<Addon>.json"
```

The runner sets `VANILLAFORGE_ADDON_ROOT` to the addon folder and runs the tests
from `regressions/`, so `wowlua` and `wowkit` import. `--compare <earlier.json>`
lists the modules that changed since an earlier report.

One file, some files, or the same tests on an older commit of the addon:

```text
python -B tools/run_suite.py <Addon> [test_file_pattern.py] [--old <commit>]
```

Every suite at once, one line each, after a change to the kit (`wowkit.py`,
`wowlua.py`) or to a tool the suites use:

```text
python -B tools/run_suite.py --all
```

`--old` unpacks the addon at that commit with `git archive` (never a stash,
which can turn LF files to CRLF) and prints each test's first error line. A new
test for a bug fails there for the bug, not for its own setup: an error such as
"substring not found" from a helper means the test slices the source at text
the old code lacks, which proves nothing.

## The game's Lua: wowlua.py

Every suite runs on the game's Lua: `from wowlua import LuaRuntime`, never lupa
directly (`tests/test_wowlua.py` fails on a direct import). It removes what the
client does not open (`os`, `io`, `debug`, `package`, `require`, `dofile`,
`loadfile`), applies ClassicAPI's `gsub` rule (a replacement function that
returns nothing removes the match) and the game's `table.setn`/`getn`, and gives
`date`, `time` and the short aliases FrameXML uses. Its docstring cites each
source.

## The game model: wowkit.py

Widgets, events (ClassicAPI's unit filters), time and timers, and the loader
(TOC order, `(addonName, namespace)`, saved variables restored when the client
does, Lua 5.0 table loops, XML frame names), written once from the docs and
pinned by `tests/test_wowkit.py`; and ClassicAPI's Settings window
(`tests/test_wowkit_settings.py`), which a test uses through `settingsWindow`
the way a player does: `use(variable, value)`, `defaults(category)`,
`enabled(row)`, `click(row)`, `opened`. A harness adds only its addon's API and data,
and redefines a `Widget` method only where it records something its own way.
The kit builds no garbage of its own, so a garbage test measures the addon.

- Ask the model, not its tables: `receives(frame, event, unit)` and
  `IsEventRegistered`, not `frame.events`.
- Flags are the engine's 1 or nil: `assertTrue`/`assertFalse`, not `== True`.
- Slice a source file at a function's definition (`local function Name`,
  `function FT.Name`), never at a comment: cleanups reword comments, and one
  renamed comment broke 111 FostercareTweaks tests on 2026-11-13.
- Test what a change does, not the text it leaves: a test that asserts a source
  line is there fails on a cleanup that keeps the behaviour. Keep text checks for
  what must not come back (a retired name, an old form).
- New tests build on the kit. A suite still marked inline moves to it when its
  tests are next touched.
- Name a test file after the behaviour it pins (`test_flag_watch.py`), not the
  date of the pass; say the date and the version it fails on in the docstring.

## Suites

One suite per installed addon, named after its folder (`regressions/ErrorLog`
runs `!ErrorLog`). A rebuild's suite is `regressions/<Addon>_rebuild` while the
new addon is built beside the old one; at the switch-over it takes the addon's
name and the old suite is deleted the same day. `run_suite.py --all` names a
suite with no installed addon, or whose every test fails: both test code that
is gone (five such suites stayed for days, 2026-11-25).

| Addon | Harness |
| --- | --- |
| ActionBars | fb_env.py |
| Auras | auras_env.py (loads UnitFrames' stock-frame mocks beside it) |
| AutoArena | aa_env.py |
| AutoBG | abg_env.py |
| AutoLazy | al_env.py |
| Bags | bags_env.py |
| BattleText | bt_env.py |
| Brainwasher | sp_env.py |
| !ErrorLog (`ErrorLog`) | inline (the old 1.9 addon; its rebuild comes last) |
| GearRack | gr_env.py |
| Mail | mail_env.py |
| Nameplates | np_env.py |
| RaidFrames | fr_env.py |
| Restock | rs_env.py |
| ThreatMeter | tm_env.py (the old addon; its rebuild is approved) |
| Tweaks | ftr_env.py |
| UnitFrames | ff_env.py |

`tools/find_holes.py` reads each suite too: a mock for a name that no longer
exists anywhere is listed as a hole.

Notes on earlier passes (what each file proved, on which commit it failed) are
in [archive/docs/REGRESSIONS_NOTES_2026.md](../archive/docs/REGRESSIONS_NOTES_2026.md).
