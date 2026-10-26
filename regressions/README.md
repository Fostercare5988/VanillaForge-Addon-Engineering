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
| ActionBarProfiles | `regressions/ActionBarProfiles` | 5 | Yes | [ActionBarProfiles](#actionbarprofiles) |
| AutoBG | `regressions/AutoBG` | 148 | Yes | [AutoBG](#autobg) |
| AutoLazy | `regressions/AutoLazy` | 7 | Yes | [AutoLazy](#autolazy) |
| BrainwasherPro | `regressions/BrainwasherPro` | 29 | Yes | [BrainwasherPro](#brainwasherpro) |
| EasyPoisons | `regressions/EasyPoisons` | 34 | Yes | [EasyPoisons](#easypoisons) |
| FostercareAuras | `regressions/FostercareAuras` | 31 | Yes | [FostercareAuras](#fostercareauras) |
| FostercareNameplates | `regressions/FostercareNameplates` | 30 | Yes | [FostercareNameplates](#fostercarenameplates) |
| FostercareTweaks | `regressions/FostercareTweaks` | 34 | Yes | [FostercareTweaks](#fostercaretweaks) |
| GearRack | `regressions/GearRack` | 27 | Yes | [GearRack](#gearrack) |
| MikScrollingBattleText | `regressions/MikScrollingBattleText` | 30 | Yes | [MikScrollingBattleText](#mikscrollingbattletext) |
| OctoMail | `regressions/OctoMail` | 17 | Yes | [OctoMail](#octomail) |
| TWThreat | `regressions/TWThreat` | 6 | Yes | [TWThreat](#twthreat) |
| AutoLazy (older) | private `external-tests/AutoLazy` | 130 | No | private command below |
| aux-addon | private `external-tests/aux-addon` | 5 | No | private command below |
| BetterCharacterStats | private `external-tests/BetterCharacterStats` | 9 | No | private command below |
| FostercareAuras (older) | private `external-tests/FostercareAuras` | 33 | No | private command below |
| TWThreat | private `external-tests/TWThreat` | 4 | No | private command below |
| UnitXP_SP3_Addon | private `external-tests/UnitXP_SP3_Addon` | 4 | No | private command below |

Private suites, from VanillaForge (replace `<Addon>` with the folder name):

```text
python -B -m unittest discover -s .private/portfolio-review-2026-10-12/external-tests/<Addon> -p "test*.py"
```

`tools/audit_addon.py --private-suites` runs the same suite during an audit and puts
its result in the summary line (`private tests failed (5 failures/errors, 33 run)`),
so a suite broken by a floor or API change is not missed. Use it in every Gate pass
for an addon listed here.

Counts are test methods as of 20 October 2026; update this table when a suite
gains or loses tests. Moving a private suite here means switching it to
`VANILLAFORGE_ADDON_ROOT` and removing archived fixture paths.

## FostercareAuras

Eleven actual-source regressions cover bag changes with an intervening snapshot,
equipment/bag ordering, 200-event invalidation bursts, reentrant ability/aura/custom
evaluation, ongoing slides, removed frames and foreign global state. Six delivery
and three slide tests fail the preceding installed source for the intended defects.
The other two tests preserve existing slide and deferred-reflow behavior.

`test_combat_log_procs.py` (1.1.0-local, ClassicAPI 1.17.3) feeds
`COMBAT_LOG_EVENT_UNFILTERED` payloads to the real proc block: Overpower stays on
the unit that dodged (by GUID, not name), Revenge opens on any attacker's dodge,
parry or block, and Riposte, Surprise Attack, Arcane Surge and Lacerate open on
their miss types, resists and crits. Seven fail on 1.0.1, which parsed chat text;
the eighth is a control.

`test_item_use.py` (1.1.0-local) runs the real `_GetInventorySlotState`: an
equipped item counts as on-use only when `C_Item.GetItemSpell` names an ON_USE
spell, the slot tooltip is never read, and an item-cache miss is retried while a
hit is cached. All three fail on the tooltip-parsing code.

`test_condition_checks.py` runs the real talent and form checks. The talent mode
is normalized once per mode string (fails on 1.1.0-local, which rebuilt its cache
on every check); the paladin and druid form results are pinned across the move of
the form name lists into tables built once.

`test_lookups.py`: pet stack counts come from `FostercarePetAuras.GetStacks` with no
aura rescan, and a spell NamPower reports missing from the spellbook costs no
spellbook walk. Both fail on 1.1.0-local.

`test_saved_settings.py` runs the real SavedVariables init block: the retired
`FostercareAurasDB.settings` table is cleared on load (fails on 1.1.0-local) and
kept settings survive.

The harness executes complete selected Lua function/event bodies with explicit
state and widget mocks. It uses Lua 5.1 and does not prove WoW Lua 5.0/native widget
semantics, appearance, frame times or gameplay. Native acceptance stays with the
[current runtime checklist](../archive/audit/OCTOWOW_RUNTIME_VERIFICATION.md#current-acceptance-pass-2026-10-12).

## MikScrollingBattleText

`test_msbt_fixes.py` (10) covers the [2026-10-12 audit](../archive/audit/MSBT_2026-10-12_AUDIT.md)
repairs F1-F6; `test_msbt_audit_2026_10_25.py` (20) covers the 2026-10-25 audit, the
combat-log source and the ForgeUI settings window. Both run on `_msbt_runtime.py`: every
TOC file in a lupa model with ClassicAPI-only globals, a stateful widget model and `CL(...)`
for combat log events. No client MPQs are needed; the BigWigs test uses the adjacent checkout.

```text
python -B tools/audit_addon.py "<AddOns>/MikScrollingBattleText" --run-tests --test-start regressions/MikScrollingBattleText
```
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

FostercareTweaks 1.4.0 (ClassicAPI 1.17.3) adds `CastbarInterruptibleTests` in
`test_event_fanout.py`: the target castbar listens for
`UNIT_SPELLCAST_NOT_INTERRUPTIBLE` / `_INTERRUPTIBLE` and turns silver when a cast
becomes uninterruptible mid-cast. It fails on 1.3.1, which never registered them.

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
`test_ab_projection.py` covers the Arathi Basin projection: an equal finish shows a
tie instead of a stale win, a winning side is told what to hold, final scores carry
their faction, and a completed capture adds only the capturer's base (assaulted and
neutral nodes). Five of its six fail on `e1eb810`; tick rates stay an in-game check.
`test_spy_stealth_alert.py` follows a stealthed hostile rogue through each open-world
detection path (nameplate, stealth cast, NamPower `BUFF_ADDED_OTHER`) to the alert
window and the `RaidWarning` sound, alerts for a seen stealther at any distance,
stays quiet for one you cannot see, targets or focuses on click,
the sound setting and auto-hide. The detection cases pass on `e1eb810`; the preview
sound case fails there. Real distances, screen position and audio stay in-game checks.
`test_options_layout.py` covers the ForgeUI options window: one **Preview frames**
toggle starts and ends every preview (and closing the window ends it), the removed
per-page test, reset and Close buttons stay gone, switches save their settings,
refreshes show saved slider values without writing them, and **Only within 10
yards** dims while stealth warnings are off. `addon_loader.py` runs `ForgeUI.lua`
first and passes `("AutoBG", ns)` to each file, as the client does. The same file
also covers the enemy-frame size presets, **Custom size** and the row-feature switches.
`test_targets_row_features.py` covers enemy cast bars (ClassicAPI cast, interrupt,
cleared cast, finished cast, the event-duration fallback, channel drain, switch off,
click to target or focus the caster, the side setting and placement outside the
trinket), range shown as a green stripe on in-range rows, colors untouched (far, never seen, switch off), raid icons on `RAID_TARGET_UPDATE`,
group target counts and the preview samples. `test_targets_guid_events.py` adds the
locked "Enemies alive/total" header and its preview-only drag hint.
`test_spell_tables.py` checks the spell tables against octowow.st/db: Spy names
a race only from race-only spells, by name (10793 and 10795 are mounts), and the
Vanish aura counts as stealth while 8342, 23133 and 23134 do not; Vanish, an Invisibility Potion and the
Gnomish Cloaking Device each show their own label and SpellInfo icon. Three of its four
fail on AutoBG `9b69782`.
The 2026-10-25 audit (`.private/audit-AutoBG-2026-10-25.md`) adds
`test_audit_2026_10_25.py` (the Spy list survives subzone and area changes; it
fails on `1ccba8d`), `test_flag_alert.py` (the flag warning has its own card
beside the stealth warning, Ctrl+click announces, the icon is the learned
Opening spell, preview and auto-hide) and, in `test_match_flow.py`, the chat
report for an invite that ends before a scheduled enter. `addon_loader.py`
also loads `AutoBG_AlertCard.lua` before each file. The stubs set ClassicAPI
`11707`.

```text
python -B tools/audit_addon.py "<AddOns>/AutoBG" --run-tests --test-start regressions/AutoBG --output .private/autobg-current.json
```

## OctoMail

Sixteen regressions cover the 2026-10-20 private audit
(`.private/audit-OctoMail-2026-10-20.md`), repaired in OctoMail 1.6.0
(`464e7a1`..`2252498`):
- `test_audit_2026_10_20.py`: ClassicAPI 1.16.0 guard, no locale layer or global `L`,
  `MAIL_FAILED` releases the send queue, sent gold and per-mail C.O.D. in the log,
  inbox senders reach autocomplete, auction markers follow the inbox page, the
  gold-send confirmation and C.O.D. cap, and the calendar tooltip on empty days.
- `test_performance_2026_10_20.py`: no OnUpdate while idle (inbox refresh on
  `C_Timer.NewTicker`), no allocation in the closed-mailbox `GetContainerItemInfo`
  path, one Send Mail refresh per bag burst, one log filter per view.

All sixteen fail on 1.5.0 (`0abd851`). `octomail_env.py` loads the Script files named
in the selected `OctoMail.xml` under Lua 5.1, rewriting Lua 5.0 `for k, v in t do`
loops to `pairs(t)`, with permissive widget mocks. They do not prove native widget
behavior, event order or how the server handles mail.

```text
python -B tools/audit_addon.py "<AddOns>/OctoMail" --run-tests --test-start regressions/OctoMail --output .private/octomail-current.json
```

## FostercareNameplates

Fourteen regressions cover the 2026-10-20 private audit
(`.private/audit-FostercareNameplates-2026-10-20.md`), repaired in FostercareNameplates
1.1.0 (`eed7478`..`a811010`):
- `AuditReproductions`: saved master switch and module choices are restored before
  file scope reads them, GUID plate lookups use `GetNamePlateForGUID`, the plate
  binding is rechecked on a 0.5 s cadence and not at all with every per-frame module
  off, own debuffs walk the aura array once, idle castbars re-query once a second,
  layout sliders do not re-query plates.
- `UnitFilters`: critter, totem, pet, grey-level and idle-neutral fading, the opacity
  setting, filters off by default, and the target never fading.
- `PlateLayout` (from play on 2026-10-21): logout skips a plate whose parts the client
  already freed. Fails on 1.1.0.
- `OwnLevel` (1.2.0): the level is drawn in the border's oval with difficulty color and ?? for
  skulls; the native level text and skull only change alpha, never anchors or font
  (moving them crashed the client in 1.1.1); the setting off and logout restore them.
- `SettingsWindow` (1.3.0, ForgeUI): every module option key has a control, all four
  tabs open, switches and choices save the same keys as before, and reset restores
  options while keeping feature switches.

Eleven fail on the code before their batch for the stated reason; the other three guard
behavior that must stay unchanged. `fnp_env.py` runs the TOC files under Lua 5.1 with
permissive widget mocks and models the SavedVariables load order from the TOC's
`LoadSavedVariablesFirst` line. They do not prove native plate rendering, input or
engine timing.

```text
python -B tools/audit_addon.py "<AddOns>/FostercareNameplates" --run-tests --test-start regressions/FostercareNameplates --output .private/fnp-current.json
```

## ActionBarProfiles

Three regressions cover the 2026-10-20 private audit
(`.private/audit-ActionBarProfiles-2026-10-20.md`), from the in-game report "Cannot
load slot 19 (Elixir of the Mongoose)":
- a slot that already holds its saved item stays, even with none in the bags;
- slots that cannot be filled are skipped and named in chat, and the rest still load;
- each skipped slot names its reason, such as "item is locked".

Two more (`test_public_api.py`, 2026-10-21) cover the API BrainwasherPro uses:
`ABP_GetProfileNames` returns a copy of the names and `ABP_LoadProfileByName`
loads or refuses by name. Both fail on 1.0.0 before the API (`fa0d19a`).

All three fail on 1.0.0 (`a62c656`). `abp_env.py` runs `ActionBarProfiles.lua` under
Lua 5.1 with action-bar, spellbook, bag and cursor mocks shaped like the ClassicAPI and
SuperWoW docs. They do not prove native placement or zero-count item buttons.

```text
python -B tools/audit_addon.py "<AddOns>/ActionBarProfiles" --run-tests --test-start regressions/ActionBarProfiles --output .private/abp-current.json
```

## AutoLazy

Seven regressions cover the 2026-10-20 private audit
(`.private/audit-AutoLazy-2026-10-20.md`), repaired in AutoLazy 1.2.0
(`86e171f`..`b9c90bf`): exact dungeon identity (AQ40 is not Ruins of Ahn'Qiraj; the
Blasted Lands "The Dark Portal" subzone is not The Black Morass), stuck stock Shift
after Alt-Tab does not turn in quests, and a gossip opener is selected once per NPC.
Four fail on 1.1.0 (`2337d29`) for those reasons; the instance-name control also fails
there because 1.1.0 did not read `GetInstanceInfo`. Two controls pass on both.
The test loads only `AutoLazy.lua` under Lua 5.1 with minimal mocks; OctoWoW zone and
instance names remain an in-game check.

The older private suite was updated the same day for the 1.16.0 guard,
`GetInstanceInfo`/L-R Shift mocks and theme widget methods; two name-matching tests
were removed with the helpers they covered.

```text
python -B tools/audit_addon.py "<AddOns>/AutoLazy" --run-tests --test-start regressions/AutoLazy --output .private/autolazy-current.json
```

## EasyPoisons

Commit IDs and version numbers below are from before the public release: the
commits are in the addon's local `backup/pre-2.0.0` and `backup/pre-1.0.0`
branches. On GitHub its history starts at a single 1.0.0 commit (2026-10-22).

Thirteen regressions cover the 2026-10-21 audit, repaired in EasyPoisons 1.4.0
(`5e958e6`): one-stack purchases, one order at a time with a stale timeout
ignored, orders blocked when the vendor lacks a reagent or stock, away from a
vendor or without general bag space (quivers excluded), item 8928 named Instant
Poison VI, purchase size read from the vendor, recipes learned from the Poisons
window, rogue-only window, and no bag walk while the window is closed. Eleven fail
on the original 1.3 (`5376485`) for those reasons; the open/reset control and the
hidden-window check pass on both. `ep_env.py` loads the files the TOC lists and
rewrites Lua 5.0 `for k, v in t do` loops so 1.3 runs under Lua 5.1. Three more
cover EasyPoisons 1.4.1, after 80 Instant Poison VI in game gave 60 of 80 vials:
purchases go out one at a time, a lost purchase is bought again, and a vendor
that never delivers ends the order. All three fail on 1.4.0. `settle()` in
`ep_env.py` delivers each purchase as it is made and `drop` loses chosen ones.
Two cover 1.4.2 (released as 2.0.0): the window opens by itself only at a vendor selling Crystal
Vials and another reagent, and `/ep` still opens it at any vendor; the first
fails on 1.4.1. Nine cover the second audit (classes `Audit2` and
`FlashPowder`): the poison list read in game (Deadly IV, Wound, Agitating, plain
Corrosive), a poison with no known recipe asks for the Poisons window, recipes
that match the table are saved too, bag events while a purchase is on its way
skip planning, and Flash Powder tops up to 20 at any vendor when switched on.
The rows moved in 2.0.0, so `POISON` in `ep_env.py` follows the new order and
older tests fail on 1.4.2 for that reason too; the mock's Deadly IV recipe is a
test value. Four (class `NewRanks`, all fail before it) cover automatic ranks: a
higher rank in the Poisons window takes over its row with its recipe, a
filtered window never moves a row down, ranks are per character, and roman
numerals up to IX parse; item IDs 90001+ there are made up. Two (class
`TradeGoods`) cover 2026-10-22 in play: a vendor selling Crystal and Leaded
Vials opened the window once Wound's learned recipe made Leaded Vial a reagent;
now a vendor must sell a whole recipe. The first fails on the 2.0.0 commit, as
does the Flash Powder test for a repair-bot-like vendor (powder and vials only),
which must top up without opening the window. Purchase sizes and
the unverified recipes stay in-game checks.

```text
python -B tools/audit_addon.py "<AddOns>/EasyPoisons" --run-tests --test-start regressions/EasyPoisons --output .private/easypoisons-current.json
```

## BrainwasherPro

Commit IDs and version numbers below are from before the public release: the
commits are in the addon's local `backup/pre-2.0.0` and `backup/pre-1.0.0`
branches. On GitHub its history starts at a single 1.0.0 commit (2026-10-22).

Seventeen regressions cover the 2026-10-21 modernization to BrainwasherPro 2.0.0:
the hidden native menu cannot take clicks, buying a slot asks first, server-confirmed
options are not asked twice, the device is found by its menu, only offered slots
show, the unused talent snapshot is cleared, the point split shows, icons are read
per page instead of at login, and the ActionBarProfiles link (loads after the
talents settle, waits for combat, gives up without a talent change, cycles in the
edit window). Thirteen fail on the original 1.5 (`fe1f3dd`); four controls (show
original, trainer reset option, save, unrelated spell events) pass on both.
`bwp_env.py` drives both the stock GossipTitleButton widgets and C_GossipInfo
from one option list; its device menu is the wording read in play on OctoWoW.
Three more cover the in-game fixes of `4ce362a` and fail before it: the reset price `(1g0s0c)` is read,
and the split the device gives in each Activate option is shown, including for
a slot the addon has no record of. Three cover `1a7928b`: long spec and bar
profile names are cut with "..." before the Edit button and shown in full on
hover (both fail before it), and the split stays visible after a cut (a control).
Five cover the second audit (class `Audit2`; four fail on the earlier 2.0.0):
the active spec is marked and not swapped to, Save names the spec it replaces,
a deleted profile shows as missing and is not loaded, and talent events are
heard only during a swap; activating another spec still works (a control).
One more replays a swap seen in play on 2026-10-22: only `SPELLS_CHANGED`, no
points event, with the split going from 41/10/0 to 32/0/19; the bars must load.
It fails on the 2.0.0 commit. The mock measures text at 6 pixels a character, so
real font widths and swap timing stay in-game checks.

```text
python -B tools/audit_addon.py "<AddOns>/BrainwasherPro" --run-tests --test-start regressions/BrainwasherPro --output .private/brainwasherpro-current.json
```

## GearRack

Commit IDs below are in the addon's local `backup/pre-1.0.0` and `backup/pre-1.0.0-b`
branches; on GitHub its history is a single v1.0.0 commit (2026-10-22).

Eleven regressions cover the 2026-10-22 review (`b3997ec`) and the Ember restyle.
Two cover DLL use and fail on 1.0.0 (`7e1af41`): the ammo slot is named by
NamPower `GetAmmo()` without a tooltip, and a one-hand weapon goes to the off
hand only when ClassicAPI `CanDualWield()` allows it. One checks that the event
script tip names `GearRack.EquipSet`/`LoadSet`, not the missing `SaveSet()`.
Six load `Skin.lua`: the set-list arrow is not covered by the name box, tabs become pills on a track with the selected tab filled,
queue checkboxes sit on their tabs, buttons are control pills, selected event
rows fill while trinket rows are outlined (item-quality names stay readable),
and the gear bars keep their backdrops while the windows lose the old art.
`gr_env.py` creates a mock widget for every name the XML defines, nested
templates included, and gives each file ClassicAPI's `("GearRack", ns)`
varargs. How the windows look stays an in-game check. `SetRetry`: a saved set
re-issues a weapon the client refused (the off hand in combat); fails before it.
`NoWaitForWeapons`: weapon swaps skip the cast and global-cooldown wait, armor
keeps it (casts do not stop weapon swaps, measured in play).

`test_dodged_trigger_2026_10_23.py` (1.1.0, ClassicAPI 1.17.3): the new
`GEARRACK_DODGED` trigger fires with the dodger's GUID for your own dodged swing,
spell or shot, and not for parries or other units' dodges. The combat log stays
registered while either it or a user's own combat-log event needs it, and the
stock Overpower presets move from chat text to the new trigger while an edited
preset is left alone. Four fail on 1.0.0; the edited-preset test is a control.

`test_audit_2026_10_25.py` (refactored 1.0.0): Reset Events asks first and keeps
every set's restore data, the Brainwashing Device's other options stay silent while
Activate still fires `GEARRACK_GBD`, a two-hander save keeps the draft's off hand,
and the version is 1.0.0. They fail on `03888af`. The dodged-trigger file now checks
the templates directly; the old migration code is gone.

```text
python -B tools/audit_addon.py "<AddOns>/GearRack" --run-tests --test-start regressions/GearRack --output .private/gearrack-current.json
```

### TWThreat

`test_audit_2026_10_26.py`: tank-mode bars are ClassicAPI unit buttons (the
creature's GUID as the unit, left click targets it; test rows have no unit),
the hand-made targeting and its wrong-unit name fallbacks are gone, and the print
helpers are local. Four fail on `333c45b`. Clicking a bar stays an in-game check.

```text
python -B tools/audit_addon.py "<AddOns>/TWThreat" --run-tests --test-start regressions/TWThreat --output .private/twthreat-current.json
```
