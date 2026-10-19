# OctoWoW Addon Impact & Capability Displacement Matrix

> **Cross-Addon Audit for the VanillaForge Maintained Addon Portfolio**
> The 12 October portfolio review evaluated ClassicAPI v1.15.16, SuperWoW 2.2, NamPower 4.6.2, UnitXP SP3 Build 90, and OctoWoW FrameXML.

---

## Current support policy — 19 October 2026

ClassicAPI v1.16.0+ is now the explicit minimum for all 16 maintained addon
repositories listed in the dated portfolio below. Each TOC declares the minimum
and synthetic `!!!ClassicAPI` dependency, every addon has a startup version guard,
and installation docs state the same requirement. This is a shared support
standard, not a claim that every addon uses a v1.16.0-only API; no addon feature
modernization or package version change was included. The active client DLL
matches the official v1.16.0 release asset by size and SHA-256; runtime loading
still needs a full client restart. See the [v1.16.0 audit](../docs/CLASSICAPI_1.16.0_AUDIT.md).

---

## Current portfolio — 12 October 2026

The active source and game root is `C:\Users\Fostercare\Desktop\client-2026-10-10`.
All 16 maintained checkouts live directly in `Interface\AddOns`. On 12 October,
eight pending repositories were committed and pushed; the other eight already
matched origin. All 16 local HEADs, origin/main refs and remotely read main heads
matched, and every working tree was clean. This is a dated reconciliation, not a
permanent claim about future working trees. Tags and release assets were unchanged.
The [GitHub overview](https://github.com/Fostercare5988/Fostercare-Addons) is a
navigation hub; source ownership stays with each standalone addon.

| Project | Responsibility | TOC version | Verified HEAD | Publication |
| --- | --- | --- | --- | --- |
| [ActionBarProfiles](https://github.com/Fostercare5988/ActionBarProfiles) | Save/restore action bars | 1.0.0 | `6c929735` | existing commit verified |
| [AtlasLoot](https://github.com/Fostercare5988/AtlasLoot) | Loot browser | 3.4.6 | `a05952ec` | existing commit verified |
| [AutoBG](https://github.com/Fostercare5988/AutoBG) | Battleground queues, carriers and enemy views | 1.0.0 | `6531cc85` | existing commit verified |
| [AutoLazy](https://github.com/Fostercare5988/AutoLazy) | Loot messages, quest turn-ins and minimap tray | 1.1.0 | `a17ae1e4` | new commit pushed |
| [aux-addon](https://github.com/Fostercare5988/aux-addon) | Auction search/posting and price history | not declared | `7fed3e5f` | new commit pushed |
| [Bagnon](https://github.com/Fostercare5988/Bagnon) | Bags, bank, sorting and cached inventory | 1.0.0 | `6757678f` | existing commit verified |
| [BetterCharacterStats](https://github.com/Fostercare5988/BetterCharacterStats) | Character statistics | 1.15.3 | `6ff1064f` | new commit pushed |
| [BigWigs](https://github.com/Fostercare5988/BigWigs) | Encounter warnings and timers | 2.0.0 | `bc62ae88` | new commit pushed |
| [FostercareAuras](https://github.com/Fostercare5988/FostercareAuras) | Configurable trackers, conditions and bars | 1.0.1-local | `73b7d5a` | subsequent repair pushed |
| [FostercareNameplates](https://github.com/Fostercare5988/FostercareNameplates) | Separate nameplate appearance and casts | 1.0.0 | `82c44e91` | existing commit verified |
| [FostercareTweaks](https://github.com/Fostercare5988/FostercareTweaks) | Interface, unit frames and target castbar | 1.3.0 | `342dbb09` | existing commit verified |
| [GearRack](https://github.com/Fostercare5988/GearRack) | Equipment sets and weapon/trinket requests | 1.0.0 | `e1ac7d36` | existing commit verified |
| [MikScrollingBattleText](https://github.com/Fostercare5988/MikScrollingBattleText) | Combat event routing and scrolling output | 1.0.0 | `92bb79b2` | existing commit verified |
| [SuperAPI](https://github.com/Fostercare5988/SuperAPI) | SuperWoW settings/native interface integration | not declared | `a516eed2` | new commit pushed |
| [TWThreat](https://github.com/Fostercare5988/TWThreat) | Threat protocol and displays | 1.4.0 | `6c891f23` | new commit pushed |
| [UnitXP_SP3_Addon](https://github.com/Fostercare5988/UnitXP_SP3_Addon) | UnitXP settings/interface integration | not declared | `66f89ca4` | new commit pushed |

### Source and runtime evidence

The current [client manifest](octowow-client-manifest.json) records the source
root, native file identity, loader entries and all Git/TOC states. Native capture
time and later addon reconciliation time are separate. Current DLL observations
belong to the [installation correction](OCTOWOW_CLIENT_BASELINE.md#current-installation-correction--19-october-2026).
Do not reuse a historical warning as an unresolved current defect without checking.

All 16 projects passed TOC/XML closure and scoped VanillaForge lint: 465 loaded
files, including 422 Lua files compiled with Lua 5.1. Compilation is a syntax
check in that runtime, not a complete proof of WoW Lua 5.0 or native widget/API
compatibility. This inventory does not mean every loaded module received a new
human modernization audit.

206 retained behavioral regressions were adapted to read the installed source:
AutoLazy 132, aux 5, BetterCharacterStats 9, BigWigs 7, FostercareAuras 33,
SuperAPI 12, TWThreat 4 and UnitXP_SP3_Addon 4. Historical development fixtures
remain external; tests did not execute archived addon source. Unchanged projects
received source checks, not a repeat of all historical behavioral suites.
These checks establish neither measured FPS gains nor native crash safety.

One private record holds staged diffs, exact source hashes, external test paths,
commands/results, initial/final Git states and the review runner:
`.private/portfolio-review-2026-10-12`. Developer artifacts and recovery stay
outside the active game. Existing sparse-checkout rules remain in place.

### Framework review and corrections

| Finding | Evidence and resolution |
| --- | --- |
| Current and historical state were easy to confuse | The old handoff described 13 repositories and retired paths; the hub listed 12. The current inventory has 16. This section is the current project map; historical sections below keep their dates. |
| Native inventory could manufacture confidence | The manifest assigned baseline versions to unrecognized binaries, omitted d3d9.dll and hid archive-read failures. It now separates observed PE versions, reference hash identity and loader listings, includes D3D9 and reports incomplete inspection. Regression tests cover those cases. |
| Project discovery could miss new work | A maintained-name list required manual edits. Git checkouts are now discovered directly; unmanaged addon folders are listed separately. Quick inventory avoids hashing the game's archives, and optional remote verification reads authoritative branch heads. |
| Pending README edits broke standalone repositories | Seven READMEs pointed at the retired FostercareClient workspace or missing sibling documentation. Their usable standalone guides were retained and reconciled before pushing. The aura source-location record was corrected; original notices and license terms remain. |
| Old test placement could validate the wrong checkout | Retained tests live outside the game after consolidation. This pass explicitly redirected runtime reads to the installed source and recorded fixture origins. The workflow/task template now captures exact external test commands and source roots. |

The compact engineering contract now states the actual OctoWoW objective and
requires verification of the supported baseline. Existing performance, native UI
and settings-theme guidance is already substantial; more general rules would not
replace current-state checks and measured acceptance.

### Personal addon improvement and learning pass — 12 October 2026

The subsequent pass covered ActionBarProfiles, AutoBG, AutoLazy, FostercareAuras,
FostercareNameplates, FostercareTweaks, GearRack and MikScrollingBattleText.
Their 112 loaded modules passed closure/lint checks, and 93 Lua chunks compiled
with Lua 5.1. Applicable earlier source/architecture reviews were reused and
current entry points rerun; this is not a new line-by-line audit of every module.

Nine external suite invocations passed 1,154 test executions, including shared
tests exercised by more than one integration suite. Counts are executions, not
1,154 unique tests. The exact source roots, commands, fixtures, suite results,
coverage limits and before/after evidence are retained in
`.private/own-addons-learning-2026-10-12`. The portable new replay corpus lives
under [regressions](../regressions/README.md), outside the game.

FostercareAuras 1.0.1-local fixes three demonstrated defects: closely spaced bag
changes discarded after a snapshot read, evaluation callbacks losing subsequent
invalidation, and grouped-slide tracking reading a foreign global frame. Eleven
new actual-source regressions preserve those paths; nine reject the preceding
source. In the same 200-notification fixture, clock reads fall from 200 to zero;
both revisions still perform one bag query and 19 equipped-item reads. A second
change after an intervening read is now retained. This establishes control-flow
correctness and removed Lua work, not native FPS or crash safety.

Framework learning now has executable support: `audit_addon.py --compare`
detects source/load-graph changes while leaving human review pending. Its external
test runner passes the selected installed source root. Six tool regressions cover
those evidence boundaries, and all 94 framework tests pass. KP-11 was refined for
closely spaced invalidation; no additional mandatory policy document was added.
The reviewed framework changes are included in this publication.

### Fresh MSBT audit — 12 October 2026

The later [complete MSBT audit](MSBT_2026-10-12_AUDIT.md) reviewed all ten loaded
files at unchanged source `92bb79b2`. It reproduced six defects: false aura fades
on stack reductions, color-picker writes crossing profile boundaries, options
refresh hiding native damage while disabled, external-message color unit
mismatch, Notification font inheritance using Outgoing, and stale mana-gain
activation baselines. The original 49 regressions still pass; their coverage did
not include these failures. No MSBT fix or addon release was made by the audit.

Stationary sticky display performs 600 widget writes across 100 hold-phase
frames; a stress batch of 200 distinct spell IDs performs 19,900 merge candidate
comparisons. These are controlled operation counts, not native frame-time or
normal-workload measurements. The [published reproductions](replays/msbt-2026-10-12/README.md)
read installed source and extract native UI references temporarily, outside the
game. Successful execution confirms the historical defects, not repaired behavior.

### Next acceptance and review boundaries

1. Complete the [current runtime acceptance pass](OCTOWOW_RUNTIME_VERIFICATION.md#current-acceptance-pass-2026-10-12)
   on a repeatable route with fixed settings and commit identities. Investigate
   actual frame-time spikes before attributing them to Lua, DLLs or graphics.
2. Continue FostercareAuras from the condition/group repairs above. Check native
   grouped animation and final item state, then review hidden-editor lifecycle and
   complex/custom configuration paths against concrete reproductions. Existing
   target confirmation/expiry regressions remain current; lexical OnUpdate counts
   do not establish a defect or justify replacing animation callbacks.
3. Review visible interface owners together: FostercareTweaks, the independent
   FostercareNameplates and native compact group UI. Verify one owner per surface,
   then check fonts, spacing, scaling, dragging and the preferred settings theme
   in game. Preserve useful controls and saved positions.
4. Reuse applicable GearRack/Bagnon/inspect operation-count evidence, redirect
   external tests to current source and measure any remaining fan-out before
   editing. Keep projects separate; a merge alone has no demonstrated FPS benefit.
5. Repair the six MSBT findings with desired-behavior regressions and the audit's
   native checks. Preserve player profiles, merge semantics and active animation;
   measure representative bursts before changing the merge algorithm or styling.

Each implementation should finish one selected subsystem with a before/after
source fixture, explicit native checks and clean repository reconciliation.
No broad addon rewrite was performed by these bounded reviews.

Current MSBT and AutoBG source have no direct UnitXP call sites; the protected
health probes mentioned in the historical October 8 note below are absent.
FostercareNameplates owns the separate nameplate implementation; Tweaks retains
its target-frame castbar.

---

## Historical portfolio review (2026-10-06)

**Narrow reconciliation, 2026-10-08:** the table retains the October 6 review
scope. Observed UnitXP calls in its rows are not verified capabilities. The
pinned build-90 dispatcher has no health/maxhealth commands; see
[the corrected engine reference](../ENGINE_REFERENCE.md#71-verified-distance-and-sight-commands).
Current MSBT and AutoBG source still contain protected health probes requiring
their own bounded review. Current FostercareTweaks has no UnitXP call sites.
This documentation correction does not modify or newly validate those addons.

This supersedes the initial portfolio rows, including the retired ItemRack and
TrinketMenu rows. The active equipment owner is GearRack. Scope: all 14 Git
checkouts in the active client, plus integration checks of AtlasLoot, OctoMail
and shootyepgp found enabled in saved addon profiles. Profile files are evidence
of configuration, not proof of which addons are loaded in the current session.
This is a source, regression and integration audit; native gameplay and frame-time
attribution remain unverified. It does not certify every file as newly refactored.

Target: ClassicAPI 1.15.16, SuperWoW 2.2, NamPower 4.6.2 and UnitXP SP3 build 90.
ClassicAPI.dll's current PE resource confirms 1.15.16.0. The other DLLs lack PE
version strings here; their target versions come from the dated deployment
baseline. No DLL, loader, client source or SavedVariables file was changed.

| Addon | Responsibility and relevant API use | Review result |
| --- | --- | --- |
| GearRack | Equipment requests, sets, trinkets; exact `C_Item` GUID locations, shared carried-bag discovery, native cast/GCD observations, shared cooldown queries | Retain the single swap owner. Prior inventory/enchant burst regressions pass; no runtime changes in this pass. |
| FostercareTweaks | Frames, energy animation, aura/marker presentation, prices/comparison; `C_UnitAuras`, `C_NamePlate`, `C_Item`, NamPower resource telemetry, optional UnitXP | Keep render updates for animation. Repair three integration tests to reflect permanent GearRack counter ownership. |
| Bagnon | Inventory/bank presentation, sort actions and saved inventory; `C_Container`, `C_Item`, `BAG_UPDATE_DELAYED`, `C_Timer` | Batch carried-bag saves, item-grid updates, bag-bar size/icons, locks and cooldowns. Save bank data while it is accessible. |
| AutoLazy | Quest/roll workflows, loot-message filtering, minimap launcher presentation; gossip/roll APIs, native hooks and a launcher registry | Retain registry/lifecycle discovery. Foreign launcher input and parenting remain with their owners. |
| AutoBG | Battleground carriers/targets/spy observations; native aura/scoreboard data, NamPower/SuperWoW cast observations, UnitXP distance/health | Retain battleground gates and existing duplicate suppression. Carrier health/range polling has an active, bounded purpose. |
| MikScrollingBattleText | Scrolling combat output; NamPower event routing, SuperWoW identity, native timers, optional UnitXP health | Retain its merged event output and active animation lifecycle; it does not replace a damage or threat meter. |
| TWThreat | Supported server threat protocol and its displays; SuperWoW GUID targeting, ClassicAPI timers | Replace per-frame query polling with one cancellable ticker; stop bar animation when widths settle. Validate the declared SuperWoW floor and timer capability. |
| BetterCharacterStats | Character stats and custom stat interpretation; native aura-name lookup and one deferred aura refresh | Remove duplicate equipment scan, preserve pending equipment changes on opening, and batch aura-related stats/Tree requests. Keep custom amount parsing. |
| DoiteAuras | User-configured aura/ability conditions and icon animation; NamPower aura IDs/names, dirty snapshots and event batches | Recompute fast enchant-expiry eligibility on every update so reapplication releases fast mode. Preserve conditions and animations. |
| SuperAPI | SuperWoW configuration, mouseover and native-interface compatibility | Observe ClassicAPI Shift-key transitions instead of calling `SetAutoloot` every frame. Remove the unused bag-cache and forwarding-only action-tooltip hook. |
| BigWigs | Encounter detection, timers and raid warnings | Retain encounter/module lifecycles and bundled library contracts. Review warnings separately; no blanket Ace removal. |
| ShaguDPS | Damage aggregation and history | Retain the meter. Scrolling combat text is a different consumer; no further merge justified. |
| UnitXP_SP3_Addon | Native extension settings, targeting/camera and configured desktop notifications | Retain its extension/settings ownership. Its optional floating combat text overlaps MSBT presentation only when enabled. |
| aux-addon | Auction UI, paced queries, inventory context and cooperative work | Retain its active-thread scheduler and protocol/library semantics. No equipment-swap ownership. |

Additional enabled integrations reviewed without edits:

- AtlasLoot: loot tables and visible item-cache refresh; no equipment-swap owner.
- OctoMail: mailbox-bound attachment/send/receive work; its update frame is parented
  to MailFrame and its handler checks visibility. Bagnon presents bags at mail;
  these addons own different actions. Mail processing needs native verification.
- shootyepgp: guild/raid roster, EP/GP, profession sync and bench workflows. Its
  separate main-name cache and 30-second guild request are background work to
  include in native profiling. They were not attributed to the reported freezes
  or removed from source evidence alone.

---

## 2. AutoLazy v1.0.0 reconciliation (2026-10-04)

Deployed commit: `23b0d361a46d0b2f44eaaa91d506c7fa7c8d70da`.
This supersedes the older AutoLazy-specific findings; the native/FrameXML audit
and unrelated portfolio rows are not newly certified.

- Load order: `AutoLazy.lua`, `AutoLazy_MinimapTray.lua`, `AutoLazy_GUI.lua`.
  SavedVariables: `AutoLazyDB`; the minimum was 1.15.15 at this 4 October audit
  and was raised to the shared 1.16.0+ policy on 19 October.
- Automatic rolls match 39 officially verified item IDs and the configured
  dungeon. `GetLootRollItemID` supplies active roll identity; content definitions
  were checked independently against official OctoWoW records. Third-party addon
  catalogs and guessed aliases are not accepted as proof.
- Loot chat filtering suppresses intermediate roll chatter while retaining native
  winner/ordinary loot messages. Pattern conversion handles numbered placeholders
  and literal percent signs. Both old and condensed native winner formats need
  runtime coverage.
- Quest turn-ins remain Shift-gated. Available quests require manual acceptance.
  Gossip and native greeting paths remain distinct; handoff state outlives the
  old panel's closure. The addon timeout is not a universal engine guarantee.
- Launcher discovery runs at lifecycle boundaries and observes later Lua creation.
  Clicks/settings consume a registry; private anonymous launchers can register
  explicitly. Foreign parents/input scripts remain intact, owner requests are
  retained for restoration, and exclusions release ownership.
- [Deployed radio/LFT source](OCTOWOW_FRAMEXML_CAPABILITIES.md#6-minimap-integration-evidence-2026-10-04)
  confirms custom handlers and animation; do not replace them with stock guesses.
- Prior validation: 102 Lua model tests (54 core, 48 tray); no native performance
  measurement or new crash reproduction. Public v1.0.0 ZIP contents matched tagged
  blobs and the downloaded asset byte for byte. `/al` and `/autolazy` remain;
  `/ar` was removed. Addon implementation was not changed during this review.

The [framework decision](../docs/DECISION_LOG.md#2026-10-04--reviewed-addon-polish-lessons-and-deployed-ui-ownership)
records lesson promotion; the [runtime checklist](OCTOWOW_RUNTIME_VERIFICATION.md)
tracks remaining client/server scenarios. Source/model evidence above does not
certify native safety, full discovery coverage or CPU/GPU cost.

## 3. Implemented findings and evidence (2026-10-06)

### Burst and lifecycle fixes

- **Bagnon:** delayed bag events scan each dirty carried bag once. Keyring updates
  have a next-tick fallback because ClassicAPI explicitly excludes them from
  `BAG_UPDATE_DELAYED`. Locks and cooldowns share one refresh handle; bag bars
  batch their own size/icon/lock work and recheck cached-character ownership at
  delivery. Bank saves remain synchronous while the banker is accessible;
  logout flushes pending carried-bag state. A redundant closed-bank save was
  removed. Bootstrap checks both the timer API and delayed event actually used.
  Lock/cooldown passes skip dirty items already refreshed in the batch; bag-icon
  refreshes likewise cover their own lock state.
- **TWThreat:** showing the query frame starts one native ticker at the selected
  interval; hiding cancels it, and callbacks from earlier sessions cannot query.
  Queries retain group, combat, target, feature and healer-master gates. Only
  pending bar interpolation keeps the animator visible. The first target survives
  OnShow; cleanup discards unfinished animation. Removed the unused animation
  flag and inaccurate performance claims from its README.
- **DoiteAuras:** the previous fast-expiry flag stayed true if a short enchant was
  replaced by a long one while any enchant remained. Recompute the desired state
  from both weapon end times. The regular cooldown heartbeat is preserved.
- **BetterCharacterStats:** remove the second identical gear scan in `RunScans`.
  Inventory debounce attaches its render callback only while pending; opening
  the panel consumes pending equipment work immediately. Aura events share one
  deferred native lookup, stats refresh and applicable Tree-of-Life request.
  Aura presence comes from current native data instead of stale tooltip cache.
  Existing numeric stat parsing, contribution logic and `BCSConfig` remain.
- **SuperAPI:** the saved/live autoloot setting uses the same controller. Shift
  modes subscribe to `MODIFIER_STATE_CHANGED`; constant modes release it. Read
  left/right states because the merged vanilla Shift query is not corrected on
  focus regain. Capability guards and metadata declare the newly consumed APIs;
  no arbitrary version floor was added. The dormant bag cache had no active
  consumer/registration, and the action-tooltip wrapper only forwarded, so both
  were removed after checking callers.
- **FostercareTweaks tests:** retired GearRack toggles must not hand cooldown
  ownership back to FT. The deployed public ownership function now drives load-
  order, old-SavedVariables, expiry and unrelated-button tests. No new runtime
  cooldown owner or user setting was added.

API evidence: pinned official
[ClassicAPI documentation](https://raw.githubusercontent.com/brues-code/ClassicAPI/7ccbbaaf68bcde6b29b71806981d0338e0577189/docs/API.md),
particularly `BAG_UPDATE_DELAYED` coverage, cancellable timers, modifier transitions
and focus reconciliation, and localized exact-name aura lookup. Positional aura
returns and custom server protocols were not replaced with retail assumptions.

### Validation

754 addon tests pass: GearRack 342, FT 184, AutoLazy 102, AutoBG 85, Bagnon 19,
BCS 6, SuperAPI 5, TWThreat 4, DoiteAuras 3 and MSBT 4. New behavioral regressions
were exercised against the faulty source where practical. Mocks explicitly model
visibility/OnShow, timer cancellation, final bag state and cached-frame ownership;
they do not establish native rendering, server packet timing or frame-time cost.

Operation-count evidence (fixtures, not FPS measurements):

- 100 same-bag notifications, two slots: saved inventory performs **2 reads after
  the batch**, versus the previous **200 reads during it**; final contents win.
- 100 two-bag/lock notifications: the bag bar performs **one size pass**, one
  icon update per affected bag and one lock pass, with no idle render callback.
- A real six-item grid with two dirty slots performs **6 lock/item reads and 6
  cooldown reads**, rather than 8 of each from a second pass over refreshed slots.
- 100 aura notifications: BCS performs **one native lookup, one stats refresh and
  one applicable group request** after the batch. Gear scans run once per refresh.
- An enchant refreshed from 40 seconds to 30 minutes releases DoiteAuras' fast
  mode; ordinary configured cooldown evaluation still runs.
- FT's existing profile fixture: 480 energy draws use 13 alpha and 89 position
  writes; disabled energy has no update work. One nameplate's 480 updates use
  20 cast queries and 8 class queries. These are model counts only.

All 14 Git-backed TOC/XML include graphs resolve and parse. All 12 changed Lua sources
compile in Lua 5.1. Changed repositories pass diff whitespace checks. UnitXP's
pre-existing XML/library whitespace diagnostics remain untouched; its file
fingerprints match the start of this pass. No runtime tests or helpers were added
to addon TOCs. Affected dependency metadata and README requirements are reconciled;
SavedVariables names, user positions and unrelated preferences are preserved.

Strict lint ran over all 17 reviewed addons: **zero detected errors**. Seven are
clean (GearRack, FT, Bagnon, AutoBG, MSBT, ShaguDPS, aux). AutoLazy also has one
cold-discovery advisory, so it is not a strict-clean result. Strict exits for
advisories are reported rather than treated as clean passes. Advisory counts:
AutoLazy 1, BCS 8, BigWigs 445, DoiteAuras 6, SuperAPI 148, TWThreat 1,
UnitXP 1, AtlasLoot 97, OctoMail 8 and shootyepgp 215.

Classification: TWThreat/BCS/UnitXP root-TOC orphan warnings are XML-loaded files,
not missing runtime modules. AutoLazy/editor hierarchy snapshots are cold or
interactive traversal, not demonstrated combat scans. Doite's tooltip branches
are retained fallbacks in its existing aura implementation. BCS still interprets
custom numeric stat text: native aura identity alone is not a proven replacement
for all those amounts. Bundled Ace libraries and encounter-specific parsers need
purpose-specific coverage before removal. These retained paths are not certified
as the newest possible implementation or as cost-free.

### Ownership and native follow-up

GearRack owns equipment swaps. Bagnon owns bag views/cache/sorting. AutoLazy owns
launcher presentation and quest/roll workflows, not foreign launcher input. FT
adds its frame and tooltip presentation while respecting GearRack counters.
MSBT, ShaguDPS, TWThreat and BigWigs provide distinct outputs. Avoid enabling
multiple floating-combat-text displays or overlapping optional warnings unless
those extra displays are wanted; no preferences were changed automatically.

After `/reload`:

1. Repeat comparable Black Morass pulls and looting. Note whether freezes remain;
   source counts do not establish which addon or native component caused them.
   If needed, compare one suspected addon disabled at a time under similar load.
2. Loot/sort with bags open, switch cached characters, use the keyring, and
   deposit/withdraw then close/reopen the bank; verify final visible/saved contents.
3. Enter/leave combat and change threat targets; check settled bars, alerts, tank
   mode and the modern/standard FT target anchor.
4. Open Character Info during equipment changes. With a Tree-of-Life healer,
   verify live stats and bonus removal. Refresh weapon enchants near expiry and
   check Doite icon timers/conditions.
5. Test all four SuperAPI autoloot modes, both Shift keys together, release while
   tabbed out, and return to WoW. Verify GearRack queued weapons, trinket binds,
   cooldowns and both AutoLazy-collected launchers still work.

### Reconciliation and retrospective

Local changes in this pass: Bagnon, BCS, DoiteAuras, SuperAPI, TWThreat, FT's
integration tests, and this framework evidence file. Existing dirty work in
GearRack, FT, AutoLazy, BigWigs, UnitXP and aux was preserved. GearRack remains
on `codex/standalone`; other addon branches were not changed. No commits, pushes,
tags, releases, settings resets or DLL updates were made.

Lesson candidates, not automatic canonical promotion: batching coverage must
include secondary views and excluded containers; fast-mode flags must be derived
again when inputs can replace earlier eligibility; integration fixtures must
follow current public ownership contracts. Existing workflow/API guidance already
covers lifecycle gating and meaningful regressions. Keep source/operation counts
separate from native performance attribution; no new framework policy is needed
merely to call these addons modern.
