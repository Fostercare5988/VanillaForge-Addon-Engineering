# Installed-addon regressions

These tests preserve repaired behavior outside the game folder. They read the
selected installed addon; they do not contain a second addon checkout or install
anything. The core framework tests under `tests/` remain independent of a game
installation. Addon-specific replays require Python and `lupa` with `lupa.lua51`.

Run from VanillaForge, replacing the addon path with the maintained checkout:

```text
python -B tools/audit_addon.py "<AddOns>/FostercareAuras" --run-tests --test-start regressions/FostercareAuras --output .private/auras-current.json
```

The audit runner supplies `VANILLAFORGE_ADDON_ROOT` to the test process and records
the selected source path, exact command and nonzero test count. Tests fail when
run directly without that source selection. For direct unittest execution, set
that environment variable explicitly. A test suite must actually use the supplied
path; setting an environment variable alone cannot verify an unrelated harness.

Use `--compare <previous-audit.json>` to list changed, added, removed and identical
loaded modules and load-graph changes. Preserve the previous report. Matching
source supports selective reuse of earlier review; it does not transfer review
approval or establish matching DLLs, settings, test coverage or native behavior.

## Suite index

Every addon regression suite VanillaForge knows about. "Portable" suites read the
addon through `VANILLAFORGE_ADDON_ROOT` and run on any checkout with the audit
runner command in each section below. "Private" suites are adapted copies kept in
`.private/portfolio-review-2026-10-12/external-tests/` (not in git); they hard-code
the installed addon path and some archived development fixtures, so they run only
on the maintainer's PC. Source revisions and hashes for the private suites are in
that folder's `verified-repositories.json` and `validation.json`.

| Addon | Location | Tests | Portable | Run |
| --- | --- | ---: | --- | --- |
| AutoBG | `regressions/AutoBG` | 48 | Yes | [AutoBG](#autobg) |
| FostercareAuras | `regressions/FostercareAuras` | 11 | Yes | [FostercareAuras](#fostercareauras) |
| FostercareTweaks | `regressions/FostercareTweaks` | 19 | Yes | [FostercareTweaks](#fostercaretweaks) |
| MikScrollingBattleText | `regressions/MikScrollingBattleText` | 10 | Yes | [MikScrollingBattleText](#mikscrollingbattletext) |
| AutoLazy | private `external-tests/AutoLazy` | 132 | No | private command below |
| aux-addon | private `external-tests/aux-addon` | 5 | No | private command below |
| BetterCharacterStats | private `external-tests/BetterCharacterStats` | 9 | No | private command below |
| BigWigs | private `external-tests/BigWigs` | 7 | No | private command below |
| FostercareAuras (older) | private `external-tests/FostercareAuras` | 33 | No | private command below |
| SuperAPI | private `external-tests/SuperAPI` | 12 | No | private command below |
| TWThreat | private `external-tests/TWThreat` | 4 | No | private command below |
| UnitXP_SP3_Addon | private `external-tests/UnitXP_SP3_Addon` | 4 | No | private command below |

Private suites, from VanillaForge (replace `<Addon>` with the folder name):

```text
python -B -m unittest discover -s .private/portfolio-review-2026-10-12/external-tests/<Addon> -p "test*.py"
```

Counts are test methods as of 20 October 2026; update this table when a suite
gains or loses tests. Moving a private suite here means switching it to
`VANILLAFORGE_ADDON_ROOT` and removing archived fixture paths.

## FostercareAuras

Eleven actual-source regressions cover bag changes with an intervening snapshot,
equipment/bag ordering, 200-event invalidation bursts, reentrant ability/aura/custom
evaluation, ongoing slides, removed frames and foreign global state. Six delivery
and three slide tests fail the preceding installed source for the intended defects.
The other two tests preserve existing slide and deferred-reflow behavior.

The harness executes complete selected Lua function/event bodies with explicit
state and widget mocks. It uses Lua 5.1 and does not prove WoW Lua 5.0/native widget
semantics, appearance, frame times or gameplay. Native acceptance stays with the
[current runtime checklist](../audit/OCTOWOW_RUNTIME_VERIFICATION.md#current-acceptance-pass-2026-10-12).

## MikScrollingBattleText

Ten regressions cover the six [MSBT audit](../audit/MSBT_2026-10-12_AUDIT.md)
findings repaired in MSBT 1.0.1: aura stack decreases (F1), Notification row font
owner (F2), disabled-state game-damage CVar (F3), color-picker profile ownership
(F4), external 0-255 message colors through the installed BigWigs caller (F5) and
the mana-gain baseline on enable (F6). Eight fail on the preceding installed
source; two picker controls pass on both. They reuse the audit replay harness, so
the client's MPQs must be readable and the adjacent BigWigs checkout present:

```text
python -B tools/audit_addon.py "<AddOns>/MikScrollingBattleText" --run-tests --test-start regressions/MikScrollingBattleText --output .private/msbt-current.json
```

The audit reproductions in `audit/replays/msbt-2026-10-12` now fail by design on
1.0.1; they remain historical demonstrations of the defects.
## FostercareTweaks

Eighteen regressions cover the 2026-10-19 private audit
repairs in FostercareTweaks 1.3.1.
- P2-1: the raid buff switches on a profile with no saved count.
- P2-2: suppressing and restoring Blizzard frames. Native event sets are taken from
  the deployed FrameXML OnLoad code.
- P3-1 to P3-4: operation counts for raid and modern-frame text, badge geometry and
  player aura rescans.
- P3-5 and P3-6: castbar and reagent fan-out.

Fourteen fail on the 1.3.0 source for the intended reason. The other four are
controls that pass on both. A nineteenth test checks the hard-coded native event
lists against the client's FrameXML. Run `tools/extract_framexml.py --client
<client-root>` first, which writes Blizzard's files to `.private/framexml`. The
test is skipped without them. They run complete selected functions or module files
with counting widget mocks, under Lua 5.1. They do not prove native widget
behavior, real event payloads or frame times.

```text
python -B tools/audit_addon.py "<AddOns>/FostercareTweaks" --run-tests --test-start regressions/FostercareTweaks --output .private/fct-current.json
```

## AutoBG

Six regressions cover the 2026-10-19 private audit repairs (AutoBG `f005e24`):
- P1-1: Cancel All leaves queues with a nil flag, like Blizzard's Leave Queue.
- P2-1: scoreboard class colors reach `WorldStateScoreButton<i>NameButtonName`.
- P2-2: taskbar flashing goes through `UnitXP("notify", "taskbarIcon")`.

Three fail on 1.0.0 (`e92b86f`). One is a setting control. Two check the
assumptions against the client's FrameXML and are skipped without
`tools/extract_framexml.py --file Interface\FrameXML\BattlefieldFrame.lua --file
Interface\FrameXML\WorldStateFrame.xml`. The complete AutoBG.lua file runs under Lua 5.1
with generic widget mocks. These tests do not prove how the game handles the native
flag, the taskbar flash or scoreboard drawing.

Eleven more cover the redesign in AutoBG `dfb923d`..`20e7936`:
- `test_spy_nearby.py`: visible enemies stay listed, unseen ones dim before removal,
  fixed window width (Spy-superwow's Nearby model).
- `test_timer_bars.py`: titles, faction fills, icons and group height of the bars.
- `test_carrier_health.py`: carrier health shows real values from NamPower
  `GetUnitField` or `UnitHealth`, and stays a percent otherwise.

Nine of these fail on `f005e24`. The rest are controls.

The DLL batch (AutoBG `5438b7e`, `0b528fa`) extends `test_spy_nearby.py`,
`test_carrier_health.py` and adds `test_targets_guid_events.py`:
- NamPower `UNIT_HEALTH_GUID`, `UNIT_DIED` and `BUFF_ADDED/REMOVED_OTHER` drive enemy-frame
  health, death, stealth and trinket timers for enemies off every unit token.
- Spy lists standing enemies through ClassicAPI `nameplate1..40`, and takes stealth and
  death from the same NamPower events.
- Carrier stacks follow `DEBUFF_ADDED/REMOVED_OTHER`; auras are read once per carrier.

Nine of these fail on `20e7936`. Native event delivery and timing remain in-game checks.

The second audit (`.private/audit-AutoBG-2026-10-19b.md`) adds batch B (`a322ee9`) and
batch C (`0c33a7c`) cases: `test_player_state.py` (ClassicAPI `UnitIsAFK`, one Deserter
lookup), `test_match_flow.py` (one auto-accept, `LeaveBattlefield()`),
`test_options_preview.py` (no automatic preview inside a battleground), GUID learning,
spell-classification caching, resurrection, carrier restore after test mode and
battleground-only zone detection. Ten fail on `0b528fa`. `test_queue_types.py` covers
the Blood Ring removal: every Auto-Queue choice reaches a native OctoWoW queue type,
and an old saved `AutoQueue_BR` is cleared on load. Both fail on `0c33a7c`.
The placeholder-name cases (Spy and enemy frames ignore the client's `UNKNOWNOBJECT`
name until the real one is cached) fail on `f90e342`.
`test_no_chat_parsing.py` keeps enemy detection on DLL events instead of English
combat-log text (P3-14); it fails on `c7138b9`.

```text
python -B tools/audit_addon.py "<AddOns>/AutoBG" --run-tests --test-start regressions/AutoBG --output .private/autobg-current.json
```
