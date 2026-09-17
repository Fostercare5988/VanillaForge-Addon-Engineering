# Enhanced WoW 1.12.1 Engine Reference

> Reference companion to `VANILLAFORGE_SYSTEM_PROMPT.md`.
>
> This file documents the **non-ClassicAPI engine stack**, client/runtime boundaries,
> and cross-component selection rules. Detailed ClassicAPI knowledge belongs in
> [`CLASSICAPI_MASTER_REFERENCE.md`](CLASSICAPI_MASTER_REFERENCE.md) and should not be duplicated here.
>
> **Canonical enhanced-client baseline**
>
> - World of Warcraft 1.12.1, Build 5875, `Interface: 11200`
> - ClassicAPI v1.15.10+
> - SuperWoW v2.2+
> - NamPower v4.6.2+
> - UnitXP SP3 v90+
> - DXVK runtime
> - VanillaFixes / compatible DLL loader where required
>
> The full stack may be assumed to be installed in the target environment.
> An individual addon should only consume or declare the components it actually uses.

---

## 1. Purpose and Authority

This reference exists so an AI coding assistant does not need to rediscover the
enhanced-client architecture for every addon task.

Use the following authority order when facts conflict:

1. current source / official documentation for the relevant component
2. `CLASSICAPI_MASTER_REFERENCE.md` for ClassicAPI
3. this engine reference
4. `KNOWN_PATTERNS.md`
5. historical framework notes
6. generic knowledge about later WoW clients

Never infer an API merely because a similarly named API exists in Retail, Classic Era,
Wrath, another DLL, or another private-client ecosystem.

### Verification labels

When adding detailed API knowledge to this file, prefer one of:

- **SOURCE-VERIFIED**: confirmed in current official source/documentation
- **EMPIRICALLY VERIFIED**: confirmed in the target client
- **HISTORICAL / VERIFY BEFORE USE**: preserved from older framework knowledge but not rechecked

Do not silently promote historical notes to source-verified facts.

---

## 2. Client Runtime vs Server Content

The addon runtime target is:

```text
WoW.exe 1.12.1
Build 5875
Interface 11200
```

A deployment-specific server/content revision may change quests, zones, items,
battlegrounds, spells, balance, or other server content. It does **not** imply a newer
Lua VM, FrameXML generation, or Retail API.

Therefore:

- client/API decisions target 1.12.1 Build 5875 plus verified DLL extensions
- content-specific behavior may depend on the server revision
- never gate client API logic on a server content version number
- never assume a later content number supplies a later Blizzard addon API

---

## 3. Stack Architecture

Think about the enhanced client in layers:

```text
Addon Lua / XML
      |
      +-- ClassicAPI -------- modern/backported Lua & WoW API surface
      |
      +-- SuperWoW ---------- GUID identity, targeting, structured client events,
      |                       client/UI extensions
      |
      +-- NamPower ---------- casting/queueing, spell/DBC and additional native APIs
      |
      +-- UnitXP SP3 -------- telemetry, LOS/distance and client/window utilities
      |
WoW.exe 1.12.1 Build 5875
      |
      +-- VanillaFixes / DLL loading & client fixes
      |
      +-- DXVK -------------- D3D9 -> Vulkan runtime translation
```

The stack is **available**, but availability is not the same thing as addon dependency.

### Dependency rule

An addon should use a component when it gives a real improvement in:

- correctness
- authoritative identity/state
- performance
- safety
- architectural simplicity

Do not call NamPower or UnitXP merely to make an addon appear "more enhanced."

DXVK is never a Lua addon API dependency.

---

## 4. ClassicAPI Boundary

ClassicAPI is the primary modern API/backport layer.

Do **not** maintain a second ClassicAPI function catalog here.

For ClassicAPI capabilities, signatures, namespaces, events, modern script arguments,
Lua 5.1 compatibility, macro behavior, focus/nameplate tokens, timers, `C_Item`,
`C_UnitAuras`, `C_Spell`, `C_NamePlate`, `C_Container`, secure-style helpers, and
debugging tools, read:

```text
CLASSICAPI_MASTER_REFERENCE.md
```

Important consequence for older framework rules:

ClassicAPI currently supports modern positional frame-script arguments and enables them
by default for handlers that declare parameters. Legacy globals remain available.
Therefore, old blanket rules that treat every `(self, event, ...)` handler as invalid
are obsolete. The actual registration/call path still matters, especially for legacy
XML or manually invoked handlers.

---

## 5. SuperWoW

**Baseline:** v2.2+  
**Role:** identity, targeting, structured events, and additional client/UI behavior.

Official SuperWoW describes itself as a 1.12.1 launcher/mod that fixes client bugs and
expands the Lua API.

### 5.1 GUID-aware unit access

**HISTORICAL / VERIFY EDGE CASES BEFORE USE**

The framework records SuperWoW support for GUID strings in enhanced unit-function paths.

Conceptual examples:

```lua
UnitName(guid)
UnitClass(guid)
```

Use GUID identity where names are ambiguous or unit-token lifetime is unstable.

Do not assume an arbitrary unrelated API accepts a GUID just because a `UnitX`
function does.

### 5.2 Direct targeting

**HISTORICAL / LONG-STANDING SUPERWOW API**

```lua
TargetUnit(guid)
TargetByName(name, true)
SetMouseoverUnit(guid)
```

Preferred identity order when targeting a known entity:

1. authoritative live unit token when it represents the intended entity
2. authoritative GUID
3. exact-name targeting when GUID is unavailable
4. never fuzzy substring targeting as a compatibility fallback

The historical framework records the second argument to `TargetByName` as exact
whole-name targeting.

### 5.3 `UNIT_CASTEVENT`

**SOURCE-VERIFIED in current SuperWoW feature documentation**

SuperWoW exposes:

```text
UNIT_CASTEVENT
```

Documented payload:

```text
arg1 = casterGUID
arg2 = targetGUID
arg3 = event type
arg4 = spell ID
arg5 = cast duration
```

Documented event types include:

```text
START
CAST
FAIL
CHANNEL
MAINHAND
OFFHAND
```

This is useful when an addon needs GUID-oriented cast/swing information that is not
better represented by ClassicAPI's modern `UNIT_SPELLCAST_*` and `C_Spell` APIs.

Do not automatically choose `UNIT_CASTEVENT` merely because it exists. Select the event
source whose semantics best match the task.

### 5.4 `RAW_COMBATLOG`

**SOURCE-VERIFIED in current SuperWoW feature documentation**

SuperWoW exposes:

```text
RAW_COMBATLOG
```

Documented payload:

```text
arg1 = original event name
arg2 = raw event text containing GUIDs
```

Use structured/native event data before localized human-readable combat-log parsing.

If `RAW_COMBATLOG` itself still requires parsing for a specific task, keep that parsing
narrow and based on its documented raw format rather than localized UI text.

### 5.5 Other SuperWoW behavior

SuperWoW has additional client behavior and CVars that may change between releases.

Do not copy its entire feature wiki into this framework. For a task that depends on a
specialized SuperWoW feature not recorded here, verify that feature once and promote it
here only if it is broadly reusable.

---

## 6. NamPower

**Baseline:** v4.6.2+  
**Role:** casting/queueing and a large native API surface.

NamPower is installed in the canonical environment but should be treated as an
**opt-in addon dependency**.

Current upstream documentation contains separate:

```text
README.md
SCRIPTS.md
EVENTS.md
DBC_FIELDS.md
UNIT_FIELDS.md
```

This is important: NamPower is broader than the small list preserved by the old v2
prompt.

### 6.1 Spell queue / quickcast

**SOURCE-VERIFIED**

NamPower provides client-side spell queuing and quickcasting behavior controlled by
`NP_*` CVars.

Examples documented upstream include:

```text
NP_QueueCastTimeSpells
NP_QueueInstantSpells
NP_QuickcastTargetingSpells
NP_SpellQueueWindowMs
NP_TargetingQueueWindowMs
```

Do not write addon logic that fights NamPower's casting queue unless the addon is
explicitly responsible for casting behavior and the interaction has been tested.

### 6.2 Native Lua functions

**SOURCE-VERIFIED at category level**

NamPower's current `SCRIPTS.md` documents a substantial custom Lua API rather than one
or two helpers.

Examples include inventory/equipment, spell, unit, utility, and client-state functions.

A documented version helper is:

```lua
GetNampowerVersion()
```

which returns:

```text
major, minor, patch
```

Historical framework knowledge also records:

```lua
GetSpellNameAndRankForId(...)
```

Before using a NamPower function not explicitly documented in this file, consult the
local/upstream NamPower `SCRIPTS.md` and then add only reusable knowledge here.

### 6.3 Events

NamPower has dedicated upstream `EVENTS.md` documentation.

For event-driven addon design:

1. prefer the event source with the clearest authoritative semantics
2. avoid duplicate subscriptions to ClassicAPI, SuperWoW, and NamPower for the same
   state unless reconciliation is actually needed
3. document which component owns the state

### 6.4 Dependency rule

Do not add NamPower as an addon requirement merely because the client has it installed.

Use it when its queueing, spell intelligence, DBC/native data, event behavior, or other
documented API provides a measurable benefit.

---

## 7. UnitXP SP3

**Baseline:** v90+  
**Role:** telemetry and selected client/window utilities.

UnitXP SP3 is installed in the canonical environment but is an **opt-in addon
dependency**.

### 7.1 Historical telemetry API

**HISTORICAL / VERIFY EXACT CURRENT SEMANTICS**

The framework records:

```lua
UnitXP("health", unit)
UnitXP("maxhealth", unit)
UnitXP("distance", unit)
UnitXP("distanceBetween", unit1, unit2)
UnitXP("los", unit)
```

Use UnitXP when its telemetry semantics materially improve the addon.

Do not automatically replace a simpler authoritative ClassicAPI primitive such as a
direct unit-position/range/LOS API unless UnitXP provides information or behavior the
task specifically needs.

### 7.2 Client/window utilities

**HISTORICAL / VERIFY BEFORE USE**

```lua
FlashClientIcon()
SetClientWindowForeground()
```

These are OS/client-window utilities, not ordinary gameplay state APIs.

### 7.3 Documented project role

UnitXP SP3 project documentation describes capabilities including:

- line-of-sight checks
- distance measurement
- nameplate occlusion improvements
- background notifications
- camera/client utilities
- FPS limiting
- Lua debugging facilities

Treat the DLL and its companion addon as separate concerns when a feature depends on
Lua-side support.

---

## 8. DXVK

**Role:** Direct3D 9 to Vulkan translation/runtime layer.

DXVK is **not a Lua API**.

Rules:

- never invent DXVK Lua functions
- never list DXVK as an addon API dependency
- never require an addon to "call DXVK"
- do not blame ordinary frame strata/layering bugs on DXVK without evidence

DXVK matters indirectly because the client may run at high and variable frame rates.

### UI/per-frame implication

Any legitimate `OnUpdate` animation/interpolation should be frame-rate independent:

```lua
elapsed
```

must be part of the calculation where movement/fades/timing depend on time.

Avoid:

```text
move 1 pixel per frame
fade by fixed alpha per frame
timer = timer + fixed assumed frame duration
```

This is a rendering correctness rule, not a DXVK API integration.

---

## 9. VanillaFixes / Loader Boundary

VanillaFixes is commonly used to load DLL extensions and provide client fixes.

For addon architecture:

- do not expose VanillaFixes as a Lua dependency unless a verified addon-visible API is
  actually consumed
- distinguish "required to boot/load the enhanced runtime" from "required by this
  addon"
- do not invent addon calls merely because the executable/runtime component is present

---

## 10. Cross-Stack Capability Selection

Do not use a rigid "newest DLL always wins" ladder.

Choose the **best verified primitive for the required semantics**.

### 10.1 Identity

Prefer:

```text
live authoritative unit token
    -> authoritative GUID
    -> exact name only when identity is otherwise unavailable
```

Useful sources may include:

```text
ClassicAPI focus/nameplate/mark tokens
ClassicAPI UnitTokenFromGUID
SuperWoW GUID-aware unit paths
SuperWoW structured GUID events
```

### 10.2 Cast tracking

Potential sources:

```text
ClassicAPI UNIT_SPELLCAST_*
ClassicAPI C_Spell.UnitCastingInfo / UnitChannelInfo
SuperWoW UNIT_CASTEVENT
NamPower documented cast/event APIs
```

Choose based on:

- whether GUID identity is required
- whether hostile/non-target units are represented
- event coverage
- timing semantics
- whether swing information is required
- whether the source is authoritative for the entity being tracked

Do not subscribe to all sources and merge them by default.

### 10.3 Auras

Prefer ClassicAPI structured aura APIs first when they expose the needed state:

```text
C_UnitAuras
AuraUtil
```

Do not fall back to hidden tooltip parsing in enhanced-client-only addons merely for
stock compatibility.

### 10.4 Health

Possible sources:

```text
ordinary UnitHealth/UnitHealthMax on authoritative tokens
ClassicAPI enhanced unit APIs
SuperWoW GUID-aware UnitX paths
UnitXP raw telemetry
```

Use UnitXP only when its raw/uncapped or other telemetry semantics are actually needed.

### 10.5 Distance / LOS

Potential sources include:

```text
ClassicAPI UnitInRange
ClassicAPI UnitDistanceSquared
ClassicAPI UnitPosition
ClassicAPI UnitInLineOfSight
UnitXP distance / distanceBetween / los
```

Select by required precision and unit availability. Do not stack several measurements
without a reason.

### 10.6 Combat log

Prefer structured event/API data over localized combat-log text.

Potential sources:

```text
ClassicAPI modern spellcast events
SuperWoW UNIT_CASTEVENT
SuperWoW RAW_COMBATLOG
NamPower documented events
```

Localized chat/combat text should be a content-specific last resort, not a stock-client
compatibility mechanism.

---

## 11. Event and Callback Semantics

The underlying client is still WoW 1.12.1, but enhanced components can deliberately
change callback/event behavior.

ClassicAPI currently supports modern positional script-handler arguments by default
for handlers that declare parameters while retaining legacy globals.

Therefore, when modifying a handler:

1. identify who invokes it
2. identify whether it is a frame script, XML body, direct Lua function call, or custom
   dispatcher
3. identify whether ClassicAPI modern dispatch applies
4. preserve the actual signature of that call path
5. test initialization and event payloads when behavior is uncertain

Never "modernize" a callback solely from visual resemblance to modern WoW code.

---

## 12. FrameXML / UI Reference

These are client/UI engineering principles, not DLL APIs.

### 12.1 Click registration

When a button requires multiple mouse buttons, register them explicitly where needed:

```lua
button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
```

ClassicAPI also provides expanded `RegisterForClicks` behavior. See the ClassicAPI
master reference for the current supported forms.

### 12.2 Compound rows

When a parent button owns interaction, child regions/frames should not accidentally
steal mouse input.

Apply this based on actual frame type and ownership, not mechanically.

### 12.3 Draw ordering

For textures, use explicit draw layers where ordering matters:

```text
BACKGROUND
BORDER
ARTWORK
OVERLAY
```

For separate frames, also consider:

```text
parenting
frame strata
frame level
```

### 12.4 Dynamic text

For variable-width labels sharing a row, anchor relationships are usually more robust
than independent hard-coded offsets.

### 12.5 ESC-closeable frames

Appropriate named dialog/options frames may use:

```lua
tinsert(UISpecialFrames, "MyAddonOptionsFrame")
```

### 12.6 Title-bar controls

When matching existing controls:

- anchor relative to a known sibling
- align centerlines rather than eyeballing offsets
- size normal/pushed/highlight textures consistently
- verify frame level and draw layer
- keep hit rectangles aligned with the visual control

Exact Blizzard texture paths are project-specific, not universal framework rules.

---

## 13. Runtime Diagnostics

The enhanced environment provides useful diagnostics, including ClassicAPI's bundled
tools.

Common tools:

```text
/reload
/luaerrors 1
/etrace
/dump
/framestack
/fstack
/classicapi
```

Use them to verify:

- initialization
- event flow
- callback arguments
- unit-token behavior
- API return values
- frame ownership
- strata/frame levels
- hidden Lua errors

Never claim runtime verification unless it was actually performed.

---

## 14. PvP / Content Boundary

Content-specific knowledge does not belong in the generic engine API catalog unless it
changes client behavior.

One currently documented deployment context records these battlegrounds:

```text
Warsong Gulch   10v10
Arathi Basin    15v15
Thorn Gorge     15v15
Alterac Valley  40v40
```

Treat battleground availability as deployment-specific content. Do not infer later-expansion battlegrounds from generic WoW knowledge.

### WSG flag-message semantics

Historical framework knowledge records:

```text
"The Horde flag was picked up by <Player>!"
```

means the carrier is Alliance, because the message names the captured flag.

Conversely:

```text
"The Alliance flag was picked up by <Player>!"
```

means the carrier is Horde.

This is content knowledge. Load it only for relevant PvP work.

---

## 15. Dependency Documentation Standard

Separate these concepts in addon documentation.

### Client environment

What the user's enhanced client normally contains.

Example:

```text
Enhanced WoW 1.12.1 client stack
```

### Hard addon dependency

A component whose API the addon actually invokes and without which the addon cannot
operate correctly.

### Optional enhancement

A component the addon detects/uses for additional capability but can operate without,
when such optional behavior is intentionally part of the design.

### Runtime infrastructure

Components such as DXVK or a DLL loader that are part of the client environment but are
not addon APIs.

Never write:

```text
Requires DXVK because the addon uses DXVK APIs
```

There are no such addon APIs in this framework.

---

## 16. Verification and Maintenance

This file should stay much smaller than the ClassicAPI master reference.

When new reusable engine knowledge is discovered:

1. verify it against current source/docs or in-client behavior
2. add it to the correct component section
3. include exact function/event names only when verified
4. avoid copying entire upstream READMEs
5. do not duplicate ClassicAPI catalog material
6. move project-specific bugs to the project or `KNOWN_PATTERNS.md`
7. keep uncertain historical knowledge explicitly labeled

The goal is a durable local map of the enhanced engine, not a museum containing every
sentence ever written about WoW DLLs.

---

## 17. Quick Decision Checklist

Before implementing an enhanced-client feature:

1. Is this client behavior or server/content behavior?
2. Does `CLASSICAPI_MASTER_REFERENCE.md` already provide the primitive?
3. Do I need GUID identity or SuperWoW-specific event semantics?
4. Does NamPower provide a casting/DBC/native primitive that materially improves this?
5. Does UnitXP provide telemetry that the ordinary unit APIs cannot provide adequately?
6. Am I accidentally treating DXVK or the DLL loader as a Lua API?
7. Am I subscribing to duplicate event sources without a reason?
8. Am I preserving a 2006 fallback solely for stock-client compatibility?
9. Is the exact function/event signature verified?
10. Can the implementation be simpler while remaining authoritative?

The desired architecture is not "use every DLL."

It is:

> **Use the smallest set of verified enhanced primitives that gives the most correct,
> deterministic, and efficient implementation for WoW 1.12.1 Build 5875.**
