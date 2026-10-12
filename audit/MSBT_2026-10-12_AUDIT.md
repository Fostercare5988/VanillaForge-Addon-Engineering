# MSBT audit — 12 October 2026

**Result: fixes required. Six independently reproduced correctness defects and two measured sources of unnecessary work.** The addon already has substantial modernization: structured combat events, GUID routing, cancellable merge timers, bounded recycling, and active-frame animation. Its remaining problems concentrate around provider state and settings ownership. A complete rewrite is not justified by this evidence.

Audited source: `C:/Users/Fostercare/Desktop/client-2026-10-10/Interface/AddOns/MikScrollingBattleText`, clean `main` at `92bb79b2bbdf33eacf3610fe5eac5f35821e3421`, version 1.0.0. This is the installed and maintained source. No addon, SavedVariables, DLL, client configuration, or Git history was changed. The report, evidence snapshots, and replay scripts are published in VanillaForge, outside the game. Native reference source is extracted temporarily from the selected client and is not vendored.

The previous 49 tests pass against this source. They did not cover the six failures below. The new diagnostic script reproduces existing defects; its successful execution does **not** mean the defects are fixed. No P0/P1 defect was established within the reviewed scope. Native gameplay and visual acceptance remain outstanding.

## Confirmed findings

### F1 — P2: aura stack reductions produce false expiration messages

Location: [MikCombatEventHelper.lua:611](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MikCombatEventHelper.lua#L611), also the debuff handler at line 624.

Both removed handlers emit `NOTIFICATIONTYPE_BUFF_FADE` without reading the seventh argument. In [NamPower 4.6.2's event contract](https://github.com/Emyrk/nampower/blob/v4.6.2/EVENTS.md#buffdebuff-events), state 2 denotes modification; a removed event with that state represents a stack decrease while the aura remains. State 1 denotes removal.

Reproduction: emit either removed event with two remaining stacks and state 2. Each produces one fade notification; expected zero. The full helper → combat handler → animation dispatch path also produces the false fade. State 1 still correctly produces one notification as a positive control. The user can be told a buff or debuff expired while it still affects the character.

Bounded correction: distinguish actual removal from stack changes in both handlers. If stack notifications are wanted, give them explicit semantics instead of reusing expiration. Preserve actual-removal behavior and verify both helpful and harmful auras on the deployed provider.

### F4 — P2: an open color picker can overwrite a different profile

Location: [MSBTOptions.lua:1734](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MSBTOptions.lua#L1734), cancellation at line 1757; profile-load transition at line 1236.

The picker stores a variable path and swatch but not its owning profile. Selection and cancellation resolve that path against whichever profile is current when the callback runs. Loading a profile, changing tabs, and closing the main settings window do not retire the owned picker.

Reproduction uses the actual deployed `UIDropDownMenuButton_OpenColorPicker` function, native color-select/OK/Cancel XML scripts, and MSBT's actual button template and profile-load handler. Profile A starts at `(0.1, 0.2, 0.3)` and profile B at `(0.7, 0.8, 0.9)`. Open A's picker, select `(0.4, 0.5, 0.6)`, then load B. The picker remains open. OK overwrites B with A's selected color; Cancel overwrites B with A's original color and leaves A's preview applied. Same-profile selection is a passing control.

This is a persistent settings mutation across profiles, not merely an inaccurate preview. The deployed picker is a separate UIParent child; the applicable native panel path shows it without closing MSBT's custom settings frame. The replay models that branch, not the full game window manager.

Bounded correction: retire MSBT's owned picker before profile replacement/load/reset and main-window closure. Bind callbacks to the original profile/settings identity and reject stale callbacks. Establish ownership before hiding or cancelling the shared native picker so another addon's picker is not affected. Cancelling after switching the current profile would repeat the defect.

### F3 — P2: opening options can hide native damage while MSBT is disabled

Location: [MSBTOptions.lua:3822](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MSBTOptions.lua#L3822); competing lifecycle owner at [MikScrollingBattleText.lua:1399](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MikScrollingBattleText.lua#L1399).

Disabling MSBT restores `CombatDamage=1`. The options refresh unconditionally applies the profile's Show Game Damage setting. Its default is false, so opening options changes `CombatDamage` back to 0 while MSBT remains disabled. Both MSBT output and native damage above heads are then absent. Options initialization uses this same refresh path.

Reproduction: default Show Game Damage false → disable MSBT → observe CVar 1 → actual options OnShow → observe CVar 0 with UserDisabled still true. Enabled-state controls correctly apply false/true choices.

Bounded correction: centralize the effective CVar decision with disabled-state precedence. Make passive settings population read state without independently applying it. Keep the saved preference distinct from the effective value, and preserve the independently owned Blizzard/UnitXP floating-text settings.

### F5 — P2: external messages forward byte colors to the normalized text-color API

Location: [MikScrollingBattleText.lua:2636](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MikScrollingBattleText.lua#L2636), consumed at line 1736. Installed caller: [BigWigs/Plugins/Messages.lua:404](https://github.com/Fostercare5988/BigWigs/blob/bc62ae88eaa48c83a9d57e77a3c564585c94ef1d/Plugins/Messages.lua#L404).

`DisplayMessage` accepts and defaults to 0–255 channels. The installed BigWigs integration intentionally multiplies its normalized channels by 255. MSBT forwards those channels unchanged to `FontString:SetTextColor`, whereas its internal event path uses normalized 0–1 channels. Intermediate shades therefore cannot be represented correctly through the external interface.

Reproduction executes the installed BigWigs message handler and the complete MSBT display path. Input color `(0.2, 0.5, 0.8)` reaches `SetTextColor` as `(51, 127.5, 204)` rather than `(0.2, 0.5, 0.8)`. The exact argument mismatch is verified; native clamping and rendered appearance were not measured. Pure endpoint colors can conceal this error.

Bounded correction: normalize once at the legacy external interface boundary, preserving the public 0–255 contract and the existing normalized internal event path. Test intermediate colors, defaults, hidden/disabled areas, and the installed BigWigs caller. This does not require changing BigWigs.

### F2 — P2: Notification event font editors inherit from Outgoing

Location: [MSBTOptions.lua:2082](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MSBTOptions.lua#L2082); button dispatch at line 1354 and inheritance resolution at line 2663.

Notification rows are assigned `EventArea="Outgoing"`. Their Edit Fonts button therefore resolves inherited font, outline, and size from the Outgoing area, while editing the Notification event. The incorrect preview can become a saved override when inheritance is disabled.

Reproduction sets Incoming to 22, Outgoing to 20, and Notification to 34. Actual row button callbacks show correct Incoming/Outgoing sizes. The Notification editor reports 20 instead of 34. Unchecking Inherit saves 20 into the Notification event. Equal default settings masked the mistake in previous tests.

Bounded correction: give Notification rows their actual area. Cover real row-button dispatch with deliberately different area fonts and both inherited and explicit overrides, rather than calling the generic font editor directly.

### F6 — P3: enabling mana-gain display uses a stale observation baseline

Location: [MikCombatEventHelper.lua:1271](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MikCombatEventHelper.lua#L1271), with the generic checkbox setter in [MSBTOptions.lua:906](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MSBTOptions.lua#L906).

When no self-mana threshold trigger is enabled and Show All Mana Gains is off, the early return stops updating the mana baseline. Enabling the checkbox does not establish a new baseline. The first later gain is compared with an old amount, potentially omitting it or including mana gained while display was off.

Reproductions disable all self-mana thresholds, change mana while display is off, and enable it through the actual checkbox callback. An old baseline of 100 followed by enable at 20 misses the subsequent +5. An old baseline of 20 followed by enable at 70 reports +55 for a subsequent +5. The following +2 is correctly observed in both controls. This is conditional on inactive self-mana triggers; the default enabled low-mana trigger can conceal it.

Bounded correction: establish the current mana baseline on the false → true display transition. Avoid resetting unrelated health thresholds or introducing a throttle that loses small gains. Retain structured spell-gain de-duplication.

## Performance evidence and modernization order

These are operation counts from the current implementation under controlled fixtures. There is no patched comparison or native FPS/time claim.

1. **Remove redundant sticky hold-phase widget writes.** [DoAnimation:2109](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MikScrollingBattleText.lua#L2109) writes position, text alpha/height, and icon alpha/width/height on every update, even for a stationary noncritical sticky inside its two-second hold phase. One such sticky with an icon performs **600 widget writes over 100 hold-phase frames**: 100 of each operation. Write phase constants on transition and positions only when changed; preserve entry animation, fades, critical jitter, and repositioning when other stickies appear. Active OnUpdate animation remains appropriate.

2. **Replace repeated merge-prefix scans with an index if representative bursts justify it.** [MergeEvents:775](https://github.com/Fostercare5988/MikScrollingBattleText/blob/92bb79b2bbdf33eacf3610fe5eac5f35821e3421/MikScrollingBattleText.lua#L775) linearly scans accumulated groups for each event. Actual-source iterator instrumentation counts candidate visits below; final trailer iteration is excluded. Amounts remain conserved in all cases.

| Inputs in one merge batch | One shared spell ID | All distinct spell IDs |
| ---: | ---: | ---: |
| 1 | 0 | 0 |
| 10 | 9 | 45 |
| 50 | 49 | 1,225 |
| 200 | 199 | 19,900 |

The distinct-key growth is quadratic. The 200-event batch is a stress fixture, not a claim about normal play. Any index must preserve first-seen display order, spell-ID separation, melee GUID identity, multi-target labeling, critical totals, recycled-table ownership, and events arriving during a flush. Keep the 0.3-second merge semantics unless a separately measured UX change warrants changing them.

3. **Consolidate settings ownership after the correctness fixes.** Shared row descriptors should supply area, profile identity, and callback lifecycle together. A small owner-aware layer would address the repeated failure pattern without replacing all six settings pages at once. Preserve existing SavedVariables and player choices.

4. **Use a native acceptance pass to direct aesthetic changes.** Fix the font inheritance and external color defects first. Then inspect font rendering, icon alignment, critical/readability balance, small-screen scaling, mouse input, scroll-to-last-row behavior, and reopen/escape transitions at the user's actual resolution/UI scale. Existing dark-panel theme traversal runs once; its three allocation warnings are cold-path candidates and do not warrant a performance rewrite. Media presence does not establish visual quality.

NamPower and SuperWoW already supply the useful structured combat and identity primitives here. ClassicAPI timers/table helpers already reduce idle work. No missing UnitXP/DXVK integration was established as the cause of these defects. Adding another DLL call is not itself modernization; each replacement needs a verified semantic and cost advantage. Retain custom search triggers where native text matching is the selected user feature. A later conversion of individual built-in readiness triggers needs verified OctoWoW spell/state evidence, not assumed Retail behavior.

## Loaded-module coverage

All ten files in the actual TOC/XML closure were reviewed. The table records ownership, activation, cardinality, and disposition; source equality alone was not used as a review result.

| Loaded file | Owner and activation | Repeated work / cardinality | Reviewed disposition |
| --- | --- | --- | --- |
| MikScrollingBattleText.toc | Dependency metadata and ordered load closure | One TOC; six Lua and three XML dependencies | Complete graph, no missing loaded source. Requirements remain consistent with the installed stack; no dependency/version change proposed. |
| localization.lua | Default profile, messages, fonts, builtin triggers, suppression patterns | Load-time tables; 40 selectable fonts, 102 default event entries, 12 triggers, nine suppressions | Defaults and substitutions traced to consumers. Legacy stock spell IDs were not independently certified against OctoWoW custom DBCs in this audit. Four legacy event defaults have no options row; no current-provider loss was established from that alone. |
| localization_options.lua | Six-page UI labels, controls, event descriptions and tooltips | Static metadata; 43 Incoming, 38 Outgoing, 17 Notification rows | Every row resolves to an existing default event; no duplicate row event types. Unsupported exact overheal is disclosed in help. Metadata alone did not catch the F2 row-owner error. |
| MikTableRecyclerObject.lua | Temporary event-table acquire/release | Primary pool 40; weak overflow and duplicate-release tracking | Bounded/collectible behavior and nested-reference clearing covered by existing tests. No rewrite indicated. Estimated saved bytes are not native memory/FPS measurements. |
| MikCombatEventHelper.lua | Provider event routing, health/mana thresholds, search triggers, lifecycle | 17 NamPower events; 12 core event subscriptions; search subscriptions follow active triggers; bounded spell/format caches and selected-name history | Direction/GUID filtering, heal de-duplication, critical flags, shields, thresholds, invalid patterns and cancellation reviewed. F1/F6 require fixes. Health owner separation and final trailing checks retained. |
| MikScrollingBattleText.lua | Current profile, suppression/formatting, merge queues, display slots, animation, public interface | Two merge queues; one pending timer per queued area; three areas × 20 slots; active-frame updates | Generation guards and batch swapping protect cancellation/re-entrancy. F3 shared ownership and F5 color boundary require fixes. Sticky writes and merge cardinality are measured optimization candidates. |
| MSBTOptions.lua | Configuration controls, profile actions, shared dialogs, mover preview, theme | Initialization once, refresh on show; bounded visible rows; one shared font editor, picker, mover/config dialog | All six pages and control families inspected. F2/F3/F4/F6 exercise actual callbacks/transitions. Theme traversal is cold; no idle settings ticker introduced. |
| MikCombatEventHelper.xml | Helper event-frame scripts | One frame, two script bodies | Source callbacks resolve; lifecycle registration/unregistration traced. |
| MikScrollingBattleText.xml | Runtime event frame and three animation frames | 60 text objects; five script bodies | Animation callbacks belong to area frames; empty hidden frames stop displaying. No unsolicited global polling conversion proposed. |
| MSBTOptions.xml | Native-inherited templates, layout, callback wiring | 201 named declarations including templates; 79 script bodies | All script bodies syntax-checked; referenced addon methods resolve. Actual button/checkbox templates included in new reproductions. Rendering and full native widget behavior remain acceptance work. |

Additional coverage: README and user guide, 43 unique addon media references (all present), external BigWigs caller, deployed color-picker/menu/panel sources. There are 53 runtime files plus two player documents and two Git housekeeping files in the 57-file source hash snapshot. Native assets referenced by the client were not exhaustively decoded or visually certified. Fonts/sounds were checked for file presence, not perceived appearance or audio quality.

## Validation and integration review

| Review dimension | Result | Evidence / limit |
| --- | --- | --- |
| Correctness | FIXES REQUIRED | Six reproducible defects with locations, observed/expected values, and relevant controls. |
| Ownership / supersession | FIXES REQUIRED | Profile picker ownership, passive CVar mutation, notification row owner, mana activation baseline. Merge timer generation/cancellation remains covered. |
| API semantics | FIXES REQUIRED | NamPower aura modification field is ignored. External message color units mismatch their consumer. Structured heal/shield/crit behavior retains existing coverage. |
| Performance | REVIEWED, CANDIDATES MEASURED | Full loaded closure mapped; two actual-source operation-count probes. No native frame-time or provider CPU measurement. |
| Persistence | FIXES REQUIRED | Picker and inherited-size mistakes can save unintended profile values. Existing profile migration/deletion guards pass. No real player data used. |
| UI and load graph | REVIEWED, NATIVE ACCEPTANCE PENDING | All three XMLs parsed; 86 script bodies compiled; 26 distinct addon callback references resolve; 43 addon media references exist. |
| Static / executable validation | COMPLETED WITH STATED LIMITS | 49 existing regressions pass. Six new diagnostic reproductions confirm faulty behavior. Six original Lua files and XML scripts compile with Lua 5.1; no native Lua 5.0 compiler was available. Replay adaptation covers Lua 5.0 generic table iteration only. |
| Repository / deployment | UNCHANGED | Clean addon and framework main branches; 57 source file hashes unchanged during replays. No addon source edit or release performed. This report and replay evidence were subsequently published in VanillaForge. |

The graph/linter report contains zero lint errors and three hierarchy-allocation warnings in ApplyTheme, reviewed as cold initialization work. Its automatic `human_review_pending` marker describes the tool's own limits; the manual coverage/dispositions above complete this audit's source review, not native acceptance.

## Published reproduction tools

Run from the VanillaForge repository root with Python and `lupa.lua51` installed:

```powershell
$env:VANILLAFORGE_ADDON_ROOT = '<client>\Interface\AddOns\MikScrollingBattleText'
python -B audit\replays\msbt-2026-10-12\audit_replays.py
python -B audit\replays\msbt-2026-10-12\inventory.py
python -B audit\replays\msbt-2026-10-12\extract_native.py
```

Select the installed MSBT source explicitly. The adjacent installed BigWigs source is required for its integration replay. Native UI references are read from that client's Data archives into temporary storage; no recovered private fixture directory is needed. Outputs default to `.private/msbt-audit-current`, outside the game. `MSBT_AUDIT_OUTPUT` can select another external output folder. The [replay guide](replays/msbt-2026-10-12/README.md) explains assumptions and limitations.

These are historical defect demonstrations: successful execution confirms the six faulty behaviors at the audited revision. They are not desired-behavior regression tests or evidence of fixes. Once behavior is corrected, the corresponding assertion should fail until the reproduction is converted to a regression. The portable edition was rerun against the same source; all six findings and operation counts match the original audit. Its native-reference provenance includes the effective deployed templates, and the NamPower version stub returns the documented three integers.

The original 49-test baseline used retained local test fixtures outside the game. Its exact invocation and results remain recorded separately; publishing these six reproductions does not make that historical suite portable. Local absolute paths in JSON evidence are replaced with `<CLIENT>`, `<VANILLAFORGE>`, `<LOCAL_EVIDENCE>` and `<PYTHON>` placeholders; hashes, measured values and test outcomes are retained.

Evidence: [baseline](evidence/msbt-2026-10-12/baseline.json), [reproduction results](evidence/msbt-2026-10-12/replay-results.json), [inventory](evidence/msbt-2026-10-12/inventory.json), [native provenance](evidence/msbt-2026-10-12/native-provenance.json), and [reproduction source](replays/msbt-2026-10-12/audit_replays.py).

## Native acceptance after correction

1. Observe actual stack decreases and full aura removal with the deployed NamPower build; check that fade text agrees with the buff/debuff display.
2. Use distinct area fonts. Open Notification event editors through their row buttons; toggle inheritance, close/reopen, reload, and verify saved values and rendered output.
3. Open a color picker, switch profiles, reset/close settings, then invoke OK/Cancel where still applicable. Confirm only the intended owner changes and another addon's picker is unaffected.
4. Disable MSBT with Show Game Damage false, open/close settings, reload, and check native above-head damage. Re-enable and verify the saved preference becomes effective. Keep independently owned floating text intact.
5. Select MSBT as BigWigs' message output and send intermediate-shade alerts. Check color, font, icon, area suppression, and disabled-state behavior.
6. Disable self-mana thresholds, enable mana-gain display at different current mana amounts, and observe the first small gain and subsequent gains. Verify spell-gain de-duplication and regeneration/drinking behavior.
7. Capture representative single-target and AoE bursts before/after optimization using the same client, settings, display workload, and instrumentation. Validate totals/order, critical jitter, overlapping stickies, fade timing, low FPS, and UI repositioning before attributing frame-time improvements to a patch.

## Retrospective: how future work gets better

The central lesson is **test state transitions with distinguishable owners**. Equal default font sizes concealed the wrong area. A no-op CVar mock concealed a passive UI refresh changing game behavior. Calling an editor directly bypassed the actual faulty row button. A default enabled mana trigger concealed an inactive-observer transition. A picker needs both a setting path and its lifetime owner. Endpoint colors concealed a unit mismatch in a real integration.

For the next implementation pass, convert each diagnostic to a desired-behavior regression that fails this revision, implement one bounded correction, and keep the relevant positive controls. Record the provider contract, exact source revision, and callback route alongside the test. Require a named native acceptance result for visual/game behavior, and reserve performance claims for comparable operation counts or native measurements. Passing historical tests means those scenarios passed; it is not a reason to call an untouched addon modern or complete.

Framework lesson candidate: refine the existing ownership/lifecycle and UI integration guidance to explicitly require different profile/area values, observable configuration side effects, and activation after observation was suspended. Existing canonical owners are KNOWN_PATTERNS and the workflow/review validation guidance. This audit proposes a refinement; it does not automatically promote new framework rules or duplicate policy. Native rendering and OctoWoW custom spell-content assumptions remain investigations until verified.
