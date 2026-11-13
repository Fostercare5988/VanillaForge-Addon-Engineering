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
pinned by `tests/test_wowkit.py`. A harness adds only its addon's API and data,
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

| Addon | Folder | Harness |
| --- | --- | --- |
| ActionBarProfiles | `regressions/ActionBarProfiles` | abp_env.py |
| AutoBG | `regressions/AutoBG` | inline per test file; addon_loader.py loads files; clock_mock.py is ClassicAPI's duration text bindings, rule formatters and timers that fire by time (`__frame()` is a drawn frame) |
| AutoLazy | `regressions/AutoLazy` | inline per test file |
| Bagnon | `regressions/Bagnon` | bgn_env.py |
| BrainwasherPro | `regressions/BrainwasherPro` | bwp_env.py |
| EasyPoisons | `regressions/EasyPoisons` | ep_env.py |
| !ErrorLog | `regressions/ErrorLog` | inline; test_game_checks on wowkit |
| FostercareBattleText | `regressions/FostercareBattleText` | _fbt_runtime.py |
| FostercareNameplates | `regressions/FostercareNameplates` | fnp_env.py |
| FostercareTweaks | `regressions/FostercareTweaks` | ft_env.py for new tests; older files inline (`BASE` in test_audit_2026_10_26.py) |
| GearRack | `regressions/GearRack` | gr_env.py |
| Mailroom | `regressions/Mailroom` | mailroom_env.py |
| ThreatMeter | `regressions/ThreatMeter` | tm_env.py |

`tools/find_holes.py` reads each suite too: a mock for a name that no longer
exists anywhere is listed as a hole.

Notes on earlier passes (what each file proved, on which commit it failed) are
in [archive/docs/REGRESSIONS_NOTES_2026.md](../archive/docs/REGRESSIONS_NOTES_2026.md).
