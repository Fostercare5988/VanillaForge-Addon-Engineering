# VanillaForge --- Known Patterns & Pitfalls for Enhanced WoW 1.12.1

> Companion knowledge base to `VANILLAFORGE_SYSTEM_PROMPT.md`.
>
> These are extracted and consolidated from the old v2 system prompt.
> They are reference patterns, not mandatory ceremonies. Apply a pattern
> only when the current addon/task actually matches its conditions.
>
> Promote new entries only when they are verified, reusable, and
> materially useful across future work.

------------------------------------------------------------------------

## 1. Legacy Modernization Patterns

### KP-01 --- Tooltip Aura Scraping

**Problem:** Hidden `GameTooltip` scanning is used to discover aura
information.

**Risk:** unnecessary UI work, localization fragility, latency, brittle
parsing.

**Preferred direction:** use verified structured aura APIs such as
`C_UnitAuras` when they expose the required information.

------------------------------------------------------------------------

### KP-02 --- Repeated / Quadratic Aura Scanning

**Problem:** repeated index-based rescans traverse the aura list
inefficiently.

**Risk:** unnecessary C/Lua boundary work in combat hot paths.

**Preferred direction:** use slot batching or a verified iterator such
as `AuraUtil.ForEachAura` when available.

Inspect the provider's lookup cost. Repeated by-index access can restart a
descriptor walk even when the Lua loop is linear. Compare descriptor visits,
table construction and required fields, not API-call count alone. Batch into
reusable caller-owned storage only where the verified API supports it; preserve
filtering, ordering, tooltip indices and identity.

------------------------------------------------------------------------

### KP-03 --- Faux Focus Through Target Swapping

**Problem:** addon temporarily changes the player's target to simulate
focus.

**Risk:** dropped commands, visual target changes, state corruption.

**Preferred direction:** use verified enhanced focus/unit capabilities.

------------------------------------------------------------------------

### KP-04 --- Localized Combat-Log Parsing for Cast Tracking

**Problem:** addon parses chat/combat strings to infer casts.

**Risk:** localization failures and inaccurate timing/identity.

**Preferred direction:** use verified structured cast APIs,
`UNIT_CASTEVENT`, or another authoritative enhanced event.

------------------------------------------------------------------------

### KP-05 --- Fuzzy Name Targeting

**Problem:** partial-name targeting can select the wrong
player/pet/entity.

**Preferred direction:** use `TargetUnit(guid)` when GUID identity
exists, or verified exact-name targeting.

------------------------------------------------------------------------

### KP-06 --- Hostile Name as Unit Token

**Problem:** arbitrary hostile player names are treated as safe unit
tokens.

**Risk:** invalid queries and possible client/UI noise.

**Preferred direction:** retain authoritative GUID/unit-token state from
enhanced events and visibility APIs.

------------------------------------------------------------------------

### KP-07 --- Obsolete Compatibility Libraries

**Problem:** Ace-era/Babble/Dongle-style libraries are retained only to
compensate for missing 2006 functionality.

**Preferred direction:** replace their obsolete role with direct
native/enhanced APIs, then remove the dead dependency.

Do not remove a library merely because it is old if it still provides
unique required behavior.

------------------------------------------------------------------------

### KP-08 --- Manual Table Wipe

**Problem:**

``` lua
for k in pairs(t) do
    t[k] = nil
end
```

is retained as a compatibility mechanism.

**Preferred direction:** use verified `table.wipe(t)` in the enhanced
environment.

------------------------------------------------------------------------

### KP-09 --- Obsolete Lua Forms

When ClassicAPI's transpiler support is verified, prefer enhanced forms
such as:

``` lua
#t
a % b
```

over obsolete compatibility constructs such as:

``` lua
table.getn(t)
math.mod(a, b)
```

------------------------------------------------------------------------

## 2. Event and State Patterns

### KP-10 --- 1.12.1 Event Parameter Shadowing

**Problem:** a handler is modernized to parameters named `self`,
`event`, `arg1`, etc. without verifying how the 1.12.1 caller invokes
it.

**Risk:** local parameters can shadow global `event` / `arg1` values
with `nil`, breaking initialization or event handling.

**Action:** - inspect registration style - inspect XML invocation if
present - preserve the verified callback convention - test
initialization after changes

Do not blindly apply modern Retail handler signatures.

------------------------------------------------------------------------

### KP-11 --- Event Fanout Across Many Frames

**Problem:** dozens of unit frames each independently register the same
high-frequency event.

**Risk:** repeated dispatch and duplicated work.

**Preferred direction:** where the event model permits it, centralize
registration and route to relevant state/frame through a direct lookup.

Do not centralize merely for aesthetics if the event is cold or the
existing design is already efficient.

The same amplification occurs when each item completion or native slot update
refreshes every slot. Coalesce presentation invalidations into one pending
callback with the union of affected views. Read current identity, contents and
visibility when it runs; do not retain a slot payload that may already be stale.
Clear pending flags before refreshing so reentrant invalidation schedules a
subsequent pass. Preserve immediate input/native work that cannot safely defer.
Test a completion burst, view closure, target change and reentrant completion.

Also trace independent owners of the same event. A narrow indicator event must
not trigger a whole-view health/power/aura refresh through a second consumer.
Assign one owner for the affected state, and test both handler orders. Separate
presentation reflow from authoritative reads when only geometry changes; reuse
the current identity-scoped snapshot, with roster/aura changes still invalidating
it. Initialization helpers used by settings must not rebuild once before sizing
and again after sizing. Verify final visible state and subsequent source events,
not merely fewer calls.


------------------------------------------------------------------------

### KP-12 --- Stale Rows After Roster Shrink

**Problem:** a fixed-capacity UI updates active rows but fails to hide
rows above the new count.

**Symptom:** ghost players remain visible.

**Fix:** explicitly invalidate/hide the inactive tail when active count
decreases.

------------------------------------------------------------------------

### KP-13 --- Unbounded Sort Buffer

**Problem:** a preallocated/reused entity buffer contains stale entries
but is sorted as if every slot is active.

**Risk:** ghost entries or incorrect ordering.

**Preferred options:** - maintain an explicit active count - compact the
active range - sort active indices - use bounded insertion logic for
genuinely small lists

------------------------------------------------------------------------

### KP-14 --- Target/Focus Lifecycle Coupling

**Problem:** target changes accidentally clear or mutate independent
focus state.

**Fix:** give target and focus separate ownership/lifecycles unless
product behavior intentionally links them.

------------------------------------------------------------------------

### KP-15 --- Double Toggle State

**Problem:** both a click handler and visibility callback invert the
same state.

**Symptom:** frame opens and immediately closes or becomes
desynchronized.

**Fix:** maintain one authoritative visibility state transition.

------------------------------------------------------------------------

## 3. Performance Patterns

### KP-16 --- Generic OnUpdate Polling

**Problem:** `OnUpdate` is used as a timer or generic state polling
engine.

**Preferred direction:** use authoritative events or `C_Timer` for
periodic work.

**Exception:** retain `OnUpdate` for genuinely frame-rate-dependent
rendering, animation, dragging, interpolation, or similar behavior.

Separate state sampling, countdown text, layout and animation; they need not
share one cadence. Event-only code is incorrect when the chosen events do not
cover live state changes. Verify event coverage before removing reconciliation.
When periodic sampling remains necessary, reuse an appropriate owned ticker and
share pass-wide snapshots instead of rereading the same target for each member.
Preserve optional providers' semantics; a current-target fallback cannot observe
every enemy's aggro. A correctness repair may add sampling without improving cost.

------------------------------------------------------------------------

### KP-17 --- Hidden UI Still Doing Work

**Problem:** a ticker/render routine continues expensive scanning while
its entire UI is hidden.

**Preferred direction:** add a cheap visibility/lifecycle gate when
hidden state makes the work unnecessary.

Do not gate background state that must remain authoritative while
hidden.

When no consumers or background state obligations remain, cancel the owned ticker
instead of repeatedly waking it to return. Reconcile state when the view reopens.
Hiding a presentation container must not stop a foreign controller that owns
expiry, input or native animation; inspect ownership before moving or hiding
native frames.

------------------------------------------------------------------------

### KP-18 --- Redundant UI Mutation

**Problem:** hot code repeatedly calls:

``` text
SetText
SetValue
SetMinMaxValues
SetStatusBarColor
SetTexture
SetAlpha
ClearAllPoints
SetPoint
```

with values that have not changed.

**Risk:** unnecessary layout/render invalidation and C/Lua calls.

**Preferred direction:** diff-cache meaningful hot-path values.

Distinguish addon decoration from the native updater. Apply invariant crops or
layout when the owned object changes; refresh item quality on identity/inventory
invalidation. Keep native countdown, flashing, expiry and tooltip behavior. For
properties another owner can change, compare live state or invalidate after its
write; a cached desired value alone does not prove the property is still applied.

Validate numeric enum values against the provider's contract before caching or
coloring them. Lua truthiness accepts unknown rarity `-1`; valid poor quality
`0` must stay authoritative. Use exact-item metadata for an unknown result and
neutral presentation while data remains unavailable. If a cached decoration
depends on late metadata, retain only its pending item identity and invalidate
on relevant completion. Re-read the current slot/owner before repainting: the
original item may have moved. Test unknown native and metadata values, valid
zero, unrelated completion and replacement before completion.

Do not add elaborate caches to cold code.

------------------------------------------------------------------------

### KP-19 --- Allocation Churn in Hot Paths

Watch for repeated: - temporary tables - closures - formatted strings -
scratch arrays - repeated hierarchy packing

inside high-frequency combat/ticker/render paths.

Move reusable state outside the hot path when measurement/structure
justifies it.

Consumers in one synchronous refresh can share an authoritative snapshot.
Choose the cache lifetime explicitly. Do not extend a refresh-local remaining-time
snapshot across ticks without a verified clock/invalidation contract. Inventory
caches need relevant invalidation. Prune expired correlation state only when its
lifecycle proves it cannot be needed by a delayed confirmation. Bounded cleanup
must also define what remains retained.

------------------------------------------------------------------------

### KP-20 --- Inline Ticker Closure

**Pattern:**

``` lua
C_Timer.NewTicker(interval, function()
    ...
end)
```

This is not inherently wrong.

It becomes a concern when tickers are repeatedly created in a
hot/reentrant path and therefore repeatedly allocate closures.

Prefer stable callbacks for persistent/recreated high-frequency timers.

------------------------------------------------------------------------

### KP-21 --- Hierarchy Packing

**Problem:**

``` lua
{ parent:GetChildren() }
{ frame:GetRegions() }
```

creates temporary tables.

In frequently executed hierarchy scans, prefer an allocation-conscious
traversal strategy.

First reduce discovery frequency; see KP-57. At load time, readability may
matter more. Allocation advice is not permission to traverse an unsafe native
tree or substitute child enumeration for region inspection. A Lua `pcall`
cannot recover from a native access violation. Inspect the relevant lifetime
and ownership constraints before changing traversal.

------------------------------------------------------------------------

## 4. UI Interaction and Layout Patterns

### Preferred settings theme

Use the dark plum and lavender style of the GearRack settings hub as the default
for addon-owned configuration. The user approved its native rendering on
2026-10-05. Apply it during requested UI work; preserve native game frames and
useful controls rather than reskinning unrelated interfaces.

| Element | RGBA color |
| --- | --- |
| Panel background | `0.055, 0.045, 0.075, 0.97` |
| Panel border | `0.55, 0.43, 0.72, 1` |
| Title and accent | `0.78, 0.65, 1, 1` |
| Button background | `0.14, 0.10, 0.20, 1` |
| Button border | `0.42, 0.33, 0.54, 1` |
| Button hover | `0.25, 0.18, 0.35, 1` |
| Checkbox label | `0.92, 0.90, 1, 1` |

- Use a nearly opaque panel, a thin muted lavender border and flat dark plum
  buttons. Native `Interface\\Buttons\\WHITE8X8` backdrops and
  `Interface\\Tooltips\\UI-Tooltip-Border` edges need no extra artwork. Reference
  edge sizes are 12 for the panel and 8 for buttons, with 4/2 pixel insets.
- Start compact: a 360 UI-pixel panel, 20 pixel content margins, paired 156 by
  32 buttons and an 8 pixel column gap. Scale the layout to the content; constrain
  text and check it at supported UI scales instead of forcing these dimensions.
- Use `GameFontNormalLarge` for the lavender title, `GameFontHighlight` for
  button text and `GameFontHighlightSmall` for short white help text. Keep native
  checkmarks and close controls. Give related rows consistent spacing and align
  their labels; leave room for wrapped help without covering the next control.
- Organize around player tasks, with short action buttons above visibility and
  behavior choices. Label checkboxes by their visible result and put secondary
  details beside the option. The theme does not prescribe reset or recovery
  buttons; choose controls using the settings guidance in KP-44.
- Hover feedback belongs in `OnEnter`/`OnLeave`; static settings need no polling
  or `OnUpdate`. Hide the hub when opening a separate editor so its higher strata
  cannot cover that editor. Retain drag, close, Escape and native input behavior.

This is a visual preference, not evidence of correctness or performance. Verify
entry, live changes, persistence, reset, text fit and input in the native client.

------------------------------------------------------------------------

### KP-22 --- Missing Right-Click Registration

**Symptom:** right-click handler exists but never fires.

**Check:**

``` lua
button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
```

when both click types are required.

Inspect the deployed XML and delegated native handler as well. A native global
handler may take no arguments and read `this`/`arg1`; do not replace it with a
Retail-style `self, button` assumption. List row IDs may be category-local indices,
not physical display rows or stable content IDs. Preserve the original click
chain and model those distinctions in tests.

------------------------------------------------------------------------

### KP-23 --- Compound Row Input Ownership

**Problem:** child frames, including status bars, intercept input intended for a
compound parent button, or a row's drag gesture competes with its click action.

**Preferred direction:** disable mouse interaction on non-interactive
children and let the parent own the full visible click surface. If dragging
with the same mouse button disrupts that action, use a dedicated header or
drag handle.

Apply mouse disabling only to children that can actually intercept input.
Test click and drag behavior separately.

------------------------------------------------------------------------

### KP-24 --- Same-Layer Occlusion

**Problem:** background and foreground textures rely on creation order
while sharing an unsuitable draw layer.

**Preferred direction:** use deliberate `BACKGROUND`, `BORDER`,
`ARTWORK`, and `OVERLAY` placement plus frame levels where needed.

------------------------------------------------------------------------

### KP-25 --- Dynamic Text Collision

**Problem:** multiple variable-width fields use hardcoded offsets.

**Symptom:** HP, time, tags, and names overlap.

**Preferred direction:** chain dynamic fields relative to each other and
constrain the flexible field.

For compact PvP rows, prefer compact time formats such as:

``` text
0s
15s
2m
```

rather than verbose prose.

------------------------------------------------------------------------

### KP-26 --- Static Third-Party XML Anchor

**Problem:** XML hardcodes `relativeTo` a frame belonging to an optional
addon.

**Risk:** load-time warnings/failures when that addon is absent.

**Preferred direction:** create/re-anchor dynamically after verifying
the external frame exists.

------------------------------------------------------------------------

### KP-27 --- Title-Bar Alignment by Guessing

**Problem:** custom buttons use arbitrary pixel offsets beside standard
Blizzard controls.

**Preferred direction:** anchor to the neighboring standard control's
centerline where appropriate.

Also verify: - texture scaling - hitbox separation -
normal/pushed/highlight states - appropriate highlight artwork

------------------------------------------------------------------------

## 5. Cooldown Patterns

### KP-28 --- Cooldown Text Parent / 3D Model Occlusion

The old v2 prompt documented a case where cooldown text parented
directly beneath a cooldown model could render incorrectly.

Preferred architecture for that affected pattern:

``` lua
local parent = cooldown:GetParent()
local textFrame = CreateFrame("Frame", nil, parent)
textFrame:SetAllPoints(cooldown)
textFrame:SetFrameStrata(parent:GetFrameStrata() or "MEDIUM")
textFrame:SetFrameLevel(parent:GetFrameLevel() + 5)
```

Treat this as a known workaround for affected FrameXML/cooldown
implementations, not a universal requirement for every custom cooldown
widget.

------------------------------------------------------------------------

### KP-29 --- Cooldown Clock Drift / Epoch-Wrap Confusion

The old prompt documented a bug where arbitrary forward-time thresholds
could misclassify ordinary clock drift as a 32-bit millisecond epoch
wrap.

Safer conceptual order:

1.  compute ordinary remaining time directly
2.  detect true wrap only under conditions that actually indicate wrap
3.  clamp small forward drift
4.  test login/reload and long-uptime cases

Do not introduce wrap arithmetic without evidence that the affected API
uses that clock representation.

------------------------------------------------------------------------

### KP-30 --- Active Cooldowns Missing After Reload

**Problem:** addon hooks future cooldown updates but does not initialize
cooldowns already active at addon load.

**Fix:** after enabling the module, perform a focused initial sweep of
relevant visible/action buttons and initialize active cooldown state.

------------------------------------------------------------------------

## 6. Enhanced FrameXML Patterns

### KP-31 --- TargetFrame Duplicate Health Strings

The old prompt documents enhanced FrameXML distributions that may expose
multiple native target-health fontstrings, including:

``` text
TargetHPText
TargetHPPercText
TargetFrameHealthBarText
```

A replacement health-text addon can therefore accidentally display
duplicate values.

**Action for affected clients:** - inspect the live FrameXML objects
first - suppress only the native strings actually responsible - prevent
native update code from re-showing them if necessary - give replacement
fontstrings unique names

Do not assume every 1.12.1 distribution has these exact objects.

------------------------------------------------------------------------

### KP-32 --- Nameplate Class Color Reset

The old prompt documents hostile player nameplate health bars being
recolored by native reaction/combat updates after an addon applies class
colors.

**Symptom:** class color flashes, then resets to red/yellow.

Potential solution for affected implementation: - maintain verified
player identity - reapply class color after native mutation - use a
recursion/reentrancy guard if intercepting `SetStatusBarColor` - cache
the applied RGB values - never class-color NPCs/pets unless
intentionally designed

Nameplates are recyclable. Identity state must be invalidated when a
plate is reused.

------------------------------------------------------------------------

## 7. Targeting / Identity Patterns

### KP-33 --- GUID Identity Preferred Over Name Identity

When SuperWoW supplies stable GUID identity, prefer GUID-keyed state for
entities that can have ambiguous/reused names.

Names remain display data, not necessarily primary identity.

For equipment, an item template ID or link is not an exact-copy identity. Use a
verified item GUID when the feature promises a particular copy. An asynchronous
saved set also needs an owned snapshot of its accepted definition: an unchanged
set name does not prove unchanged contents or GUIDs.

------------------------------------------------------------------------

### KP-34 --- Nameplate Identity Recycling

Nameplates can be recycled as units enter/leave render range.

Never assume a frame permanently belongs to the same GUID/player.

Reset cached: - GUID - class - reaction - range - color - aura/cast
state

when ownership changes.

------------------------------------------------------------------------

## 8. Container Patterns

### KP-35 --- Reentrant / Manual Bag Sorting

The old v2 prompt documented problems caused by custom/manual sorting
loops being triggered repeatedly during bag changes.

Where current ClassicAPI supports native sorting:

``` lua
C_Container.SortBags()
C_Container.SortBankBags()
```

prefer it when its ordering meets the addon's requirements. In ClassicAPI
v1.15.13+, equipment-slot grouping is part of that ordering; see the
[canonical container contract](CLASSICAPI_MASTER_REFERENCE.md#equipment-slot-grouping-in-sortbags-v11513)
for its semantics and constraints. Different ordering requirements can still
justify addon logic using verified native movement APIs.

For bank operations, still verify the actual UI/state preconditions
required by the addon and client.

Use `BAG_UPDATE_DELAYED` to refresh container views after batched bag changes.
It can fire before the sort's placement phase and does not certify that a sort
has completed. Verify the relevant inventory state before publishing completion;
do not reenter sorting on each bag update.

------------------------------------------------------------------------

### KP-36 --- Cached/Offline Container State

Container addons can represent cached characters or bank views that are
not live engine inventories.

Never invoke live inventory mutation merely because a cached UI frame is
visible.

Distinguish display state from authoritative live container state.

------------------------------------------------------------------------

## 9. PvP Patterns

### KP-37 --- WSG Flag Message Attribution

For the recorded 1.12.1 WSG messages:

``` text
The Horde flag was picked up by <Player>!
```

the carrier is Alliance.

``` text
The Alliance flag was picked up by <Player>!
```

the carrier is Horde.

The named flag belongs to the opposing faction of the carrier.

------------------------------------------------------------------------

### KP-38 --- Battleground Assumption Drift

Do not import later-expansion battleground assumptions into the custom
enhanced Vanilla environment.

The old reference specifically records: - WSG - AB - Thorn Gorge - AV

and warns against assuming Eye of the Storm exists.

Keep content-specific rules separate from client/API rules.

------------------------------------------------------------------------

### KP-39 --- Scoreboard Return-Index Assumptions

**Problem:** hardcoded positional return indices are copied from another
client/version.

**Risk:** wrong statistics.

**Action:** verify the exact enhanced-client `GetBattlefieldScore`
contract before relying on positional fields.

------------------------------------------------------------------------

## 10. Miscellaneous Known Pitfalls

### KP-40 --- Global Iterator / Scratch Pollution

Keep loop variables and scratch state local.

Avoid accidental `_G` writes.

------------------------------------------------------------------------

### KP-41 --- Texture Layer Lost During Reset

When resetting/replacing textures, ensure the intended draw layer/frame
relationship remains correct.

A reset path can otherwise undo initialization-time layering.

------------------------------------------------------------------------

### KP-42 --- Hardcoded Historical Limits

Do not retain constants merely because stock Vanilla once used them if
the enhanced/content environment may extend the limit.

Where an authoritative query exists, prefer querying actual state.

Example from the old prompt: quest-log capacity assumptions.

------------------------------------------------------------------------

### KP-43 --- Unverified SuperWoW Version Arithmetic

Do not assume a version global is always numeric or encoded in a
particular arithmetic format.

Check presence/type and verify the actual version contract before
comparison.

------------------------------------------------------------------------

### KP-44 --- Player-Facing Developer Jargon

Normal player UI should describe the game action/result, not
implementation details.

Avoid exposing terms such as: - C++ - DLL - coroutine - hook - memory -
ClassicAPI

in ordinary player-facing messages unless the feature is explicitly a
developer/debugging interface.

Settings should name their checked result with concrete verbs: for example,
"Hide loot roll messages" instead of "Clean chat". State whether an action is
automatic and what is affected. Explain exclusions beside their selector so
players know whether checked entries remain visible or become hidden.
This is usability guidance, not a reason to delete useful controls blindly.

Check that intended player-configurable features have reachable controls, and
distinguish live edits from enable changes that require reload. Verify saved
refresh and defaults without resetting unrelated choices. Compute window bounds
in the same UI coordinate space as its parent; do not apply scale twice or force
a minimum taller than the available viewport. Check scroll ends and footer reach
at the user's scale. Headless geometry checks do not prove native pointer input,
text wrapping or contrast.


Before adding a control, inventory the current defaults, native/addon entry
points and settings that already produce its result. A new control needs a
distinct player task; do not duplicate layout or visibility choices with a bulk
shortcut merely because its implementation is easy. Choose sensible initial
defaults instead of making users repair them through an extra button.

Keep primary menus focused on frequent tasks and direct navigation. Recovery
actions are not mandatory menu furniture. Add them for a demonstrated need,
prefer the smallest affected scope, and keep them near that feature. A broad
data-wipe action needs an explicit product requirement, a clear scope and
confirmation; confirmation alone does not make it useful. Keep one-time
development or migration cleanup separate from runtime player controls. Preserve
supported controls unless their retirement is requested or their redundancy is verified;
when removing one, follow the workflow's complete feature-retirement guidance.

------------------------------------------------------------------------

### KP-45 --- Progressive Status Text for Near-Instant Operations

The old prompt discouraged messages such as:

``` text
Sorting...
Scanning...
Updating...
```

when the operation is effectively immediate.

Prefer concise completion feedback when appropriate:

``` text
Bags sorted.
```

This is UX guidance, not a correctness rule. Use progress messaging when
an operation genuinely takes observable time.

------------------------------------------------------------------------

### KP-46 --- Global API Clobbering

The old prompt records `_G.ClassicAPI` as a mirror that can provide a
stable reference to enhanced APIs when ordinary globals are overwritten.

Use this only where current ClassicAPI behavior verifies the mirror and
clobber resistance.

Do not wrap every global call defensively without evidence of a
conflict.

------------------------------------------------------------------------

### KP-47 --- Asynchronous Request Ownership

**Problem:** Event, timer, queue, or combat-deferred multi-stage operations
can be corrupted by duplicate, late, or out-of-order events.

**Action:**
- Assign explicit transaction ownership to the active request.
- Prevent duplicate or stale events from advancing newer requests.
- Keep transient runtime scratch state out of persistent `SavedVariables`.
- Publish completion only after authoritative runtime state verification.
- Define explicit success, abort, supersession, and timeout paths.
- Ensure transaction cleanup does not delete independent queued/manual work.
- Invalidate callbacks and timers belonging to superseded transactions.
- Test supersession, duplicate events, late events, timeout recovery, and retry safety.

Accept the latest explicit intent before suppressing duplicate work. Repeated
selection is reusable only while the active owner still represents that intent
and its accepted definition. Test A, then B, then A; edited definitions; exact
copies; and retry after a missing item returns. Preserve an already issued native
operation's ownership/deadline when it cannot be canceled safely; superseding
the requested result does not make the old completion belong to the new request.

Define priority between explicit selections and automatic queues for the affected
slots. Preserve independent slots and later manual choices; retain an existing
player choice about when automation resumes instead of silently changing it.

A modifier held across delayed dialogs is not fresh authorization after a
one-click request finishes or is canceled. Keep explicit selection identity and
suppression through delayed responses, until a defined manual/session transition.
Test cancellation, disable/re-enable and delayed menu return while the modifier
stays held. Ambiguous identity remains manual.

------------------------------------------------------------------------

### KP-48 --- Root Bindings.xml and Advisory Manifest Orphan Warnings

**Problem:** Static analysis flags `Bindings.xml` as an unreferenced runtime
file because it is not listed in the addon's `.toc`.

**Cause:** In WoW 1.12.1, root `Bindings.xml` is client-managed binding metadata
automatically discovered and loaded by the client engine. It is intentionally
not an ordinary TOC runtime entry.

**Action:**
- Never add root `Bindings.xml` to the TOC merely to silence an advisory orphan warning.
- For other unlisted Lua/XML files, inspect whether the file is client-managed,
  standalone tooling, dormant/dead code, or genuinely omitted runtime code before
  modifying the manifest.

------------------------------------------------------------------------

### KP-49 --- Enhanced Stack Availability vs Declared Addon Dependencies

**Problem:** Addon metadata or README files declare DLL dependencies simply
because the full enhanced stack is installed in the client.

**Action:**
- Distinguish between environment availability and actual addon dependency.
- An addon should declare dependencies only for components whose APIs it directly consumes.
- UnitXP SP3 may be documented as optional/recommended when core functionality works
  without it but verified distance, sight or client utilities improve it (see ENGINE_REFERENCE.md).
- DXVK is D3D9-to-Vulkan translation runtime infrastructure, never a Lua addon API or dependency.

Choose a replacement for its verified semantics, restrictions, lifecycle and
cost, not its newer name. Native aggregates suit count-only questions but do not
establish stack capacity or exact-copy identity. Structured aura fields can
replace scraping only when they preserve the required slot/filter semantics.
Likewise, a macro executor outside the native stop context may not preserve
`/stopmacro`. Do not substitute a partial equivalent or add another provider
beside an existing authoritative owner merely to increase DLL use.

------------------------------------------------------------------------

### KP-50 --- Obsolete Local Git Hooks and Release Discipline

**Problem:** Addon repositories may have obsolete local release/pre-commit hooks
(e.g. in `.git/hooks` or configured via `core.hooksPath`) referencing historical
tooling paths or frameworks that fail during release.

**Action:**
- Inspect `.git/hooks`, `git config --get core.hooksPath`, and any wrappers.
- Never use `git commit --no-verify` or `git push --no-verify` merely to bypass validation.
- Repair obsolete hook paths to the canonical VanillaForge linter:
  `C:\Users\Fostercare\Documents\VanillaForge\tools\vanillaforge_linter.py`
- Keep local `.git/hooks` modifications out of public addon commits.
- Rerun validation via the hook before completing a release.

------------------------------------------------------------------------

### KP-51 --- Performance Claim Discipline

**Problem:** Statically removing a known allocation (e.g. replacing a loop with `table.wipe`
or passing reusable tables) leads to unsubstantiated claims of "zero allocations" or "zero GC".

**Action:**
- Do not make absolute runtime performance claims without empirical profiling.
- Use narrow, evidence-matched statements such as "eliminated transient table allocation in this path."

Compare retained before/after source under the same controlled workload and
report the counted operation and model limits. API calls, internal traversal,
allocations and elapsed time are different measurements. Source counters prove
bounded work reductions, not native timing, frame pacing or freeze attribution.
Account for setup, deferred delivery and measurement instrumentation. When
reporting synthetic CPU/GC, separate trace/counter allocation from addon work
where practical, give sample spread and retain noisy results as noise. A lighter
fixture still includes mocks; it is not a native profiler calibration.


Profiler invocation counts include idle/throttle returns; fast growth can reflect
frame-rate callbacks rather than repeated scans. Inspect the measured body and
sampling overhead. Inclusive timings can overlap; positive net heap deltas do
not establish retained memory or leak ownership. Verify how hooks are removed:
closing a profiler window may leave instrumentation active. Compare an unhooked
session before attributing gameplay cost.

------------------------------------------------------------------------

### KP-52 --- Loss of Control Event Diffing & School Lockout Expiry

**Problem:** An addon attempts to track school lockout expiration by caching timestamps
from `LOSS_OF_CONTROL_ADDED` or `LOSS_OF_CONTROL_UPDATE` events.

**Cause:** In ClassicAPI, these events are triggered by a diff of which effects are
active. Re-interrupting an already-locked school extends its duration (`endMs`) without
firing either event.

**Action:**
- Do not cache school lockout expiration from event timestamps alone.
- Query `C_LossOfControl.GetSchoolLockout()` directly when the current duration or
  lockout state is needed.
- `GetSchoolLockout` queries internal `g_schoolLock` directly without Lua allocations or
  debuff scanning, making it suitable for per-frame or high-frequency polling.

------------------------------------------------------------------------

### KP-53 --- Macro Button Click Context in State Drivers and #showtooltip

**Problem:** A macro conditional `[button:N]` / `[btn:N]` behaves unexpectedly when
evaluated by a state driver or `#showtooltip`.

**Cause:** Outside an active user mouse click, there is no active click event for
`GetMouseButtonClicked()` to report.

**Action:**
- Outside a click context, `[button:N]` defaults to `"LeftButton"` (`1`).
- Design macros knowing that `#showtooltip` displays the resting state (button 1)
  at rest, matching standard client `Button:Click()` semantics.

------------------------------------------------------------------------

### KP-54 --- Macro Icon Out-of-Range Return Handling

**Problem:** Code calling `GetMacroIconInfo(index)` assumes `nil` is returned when
the index is out of bounds.

**Cause:** In the 1.12 client engine, `Script_GetMacroIconInfo` pushes `""` (empty string)
rather than `nil` for invalid or out-of-range indices.

**Action:**
- Check for `icon and icon ~= ""` rather than checking for `icon ~= nil` alone.

------------------------------------------------------------------------

### KP-55 --- Combat Swing & Weapon Delay Reconstruction

**Problem:** Addons scrape combat-log text (`CHAT_MSG_COMBAT_SELF_HITS`), hook spell
casts, poll inventory slots, or run high-frequency `OnUpdate` estimation loops to
reconstruct weapon swing timers, parry haste, extra attacks, and weapon-swap delays.

**Risk:** Localization fragility, chat-message latency, incorrect dual-wield
desynchronization tracking, parry-haste drift, and unnecessary Lua CPU and
garbage generation in combat hot paths.

**Action / Preferred Hierarchy:**
- Prefer authoritative `PLAYER_SWING` for weapon swing-reset and timing state
  (main-hand, off-hand, ranged).
- Use `C_SwingTimer` and `PLAYER_SWING_RANGE_UPDATE` only when swing-range state
  is actually required.
- Use `WEAPON_SLOT_CHANGED` when the addon independently needs to react to
  weapon-slot identity or equipment changes (slots 16, 17, 18).
- Do not reconstruct swing cadence from combat-log text, spell hooks, equipment
  polling, or high-frequency `OnUpdate` sampling when ClassicAPI v1.15.10+ provides
  the required state.
- Keep the pattern capability-based: register and consume only the specific
  events or APIs the addon's feature set actually requires.

------------------------------------------------------------------------

### KP-56 --- Tooltip Decoration Coexistence

**Problem:** Multiple addons add lines to the same tooltip; replacing a
`Set*` method or sharing duplicate state can lose original behavior or another
addon's lines depending on load order.

**Preferred direction:** For additive decoration, post-hook the relevant
tooltip methods where supported, leaving the original call and returns intact.
Keep each addon's duplicate guards on the tooltip under its own keys and clear
them when tooltip state resets. Read another addon's state only through a
narrow public query. Test repeated tooltip reuse and both addon load orders.

------------------------------------------------------------------------

### KP-57 --- Discovery in Interactive Paths

**Problem:** Repeating a client-wide global or frame scan whenever a menu opens
can stall clicks even when the eventual layout is small. A timer merely defers
that scan; it does not make the work cheaper.

**Preferred direction:** Discover at relevant lifecycle boundaries, coalesce
duplicate requests, and maintain a registry. Ordinary clicks and settings
refreshes should consume that registry. Observe later creation only where a
verified mechanism preserves the original API's arguments, returns and behavior;
provide explicit registration for objects outside discovery coverage.

Named globals, anchor heuristics and observed creation cannot guarantee discovery
of every pre-existing private anonymous frame. Document coverage and exclude
known system objects before native queries. Avoid unsafe engine enumeration to
make a universal-discovery claim. Measure scan/API-call counts separately from
actual client timing.

------------------------------------------------------------------------

## 11. Pattern Governance

This file should remain useful rather than becoming a landfill.

Before adding a new pattern:

1.  Verify the behavior.
2.  Search for an existing pattern with the same root cause.
3.  Extend/consolidate rather than duplicate.
4.  Keep project-specific quirks inside the affected project when they
    are not broadly reusable.
5.  Put machine-detectable, high-confidence hazards in the linter only
    when false-positive risk is acceptable.
6.  Remove or revise patterns invalidated by newer ClassicAPI/SuperWoW
    releases.
7.  Keep detailed API catalogs in `ENGINE_REFERENCE.md`, not here.

A bug being annoying is not sufficient reason to make it a global law.
