# ClassicAPI Master Reference for WoW 1.12.1

> Local AI knowledge base for ClassicAPI.
>
> Purpose: let coding assistants design and modernize WoW 1.12.1 addons against ClassicAPI without needing to browse GitHub for ordinary API discovery.
>
> Source basis: `brues-code/ClassicAPI`, default branch `master`, official `README.md`, official `docs/API.md`, and selected implementation/source references.
>
> Snapshot baseline used by VanillaForge: **ClassicAPI v1.15.13+**.
>
> IMPORTANT: ClassicAPI is actively developed. This document is a local snapshot, not a claim that future versions cannot add or change functionality. If installed ClassicAPI is newer and a task depends on newly added behavior not present here, inspect the installed/current source and update this reference deliberately.

---

## 1. What ClassicAPI Is

ClassicAPI is a DLL for the World of Warcraft 1.12.1 client.

Its purpose is to backport a large part of the modern WoW addon API and much of Lua 5.1 behavior into the 1.12 client so addons written for later clients can run with substantially less compatibility code.

The official project documentation currently describes:

- **550+ Lua functions**
- **50+ events**
- roughly **60 API groups / namespaces**
- substantial Lua 5.1 compatibility
- modernized addon loading
- modern macro parsing
- modern unit tokens such as focus and nameplates
- a bundled synthetic `!!!ClassicAPI` addon with Blizzard-style helper libraries
- a built-in API documentation browser

ClassicAPI registers APIs through the client engine's Lua registration path rather than requiring each addon to ship a Lua compatibility library.

---

## 2. Versioning

ClassicAPI exposes:

```lua
CLASSIC_API_VERSION
INTERFACE_VERSION
```

Build-time ClassicAPI version encoding follows:

```text
X*10000 + Y*100 + Z
```

Therefore:

```text
v1.15.8 -> 11508
v1.15.9 -> 11509
v1.15.10 -> 11510
v1.15.11 -> 11511
v1.15.12 -> 11512
v1.15.13 -> 11513
```

The VanillaForge framework baseline is:

```text
ClassicAPI v1.15.13+
```

Do not assume a future version's new API exists solely because a similarly named Retail API exists.

This environment/reference baseline does not mandate `MIN_CLASSIC_API=11513` in
every addon. Declare the minimum required by the capabilities and semantic fixes
the addon actually consumes.

---

## 3. AI Usage Rules

When this file is available:

1. Search this file before inventing a workaround.
2. Prefer an API documented here over legacy Vanilla scraping/polling techniques when it solves the same requirement cleanly.
3. Do not browse GitHub merely to rediscover an API already documented here.
4. If an exact return signature matters and this document does not provide it, use the in-game `/classicapi` browser or inspect current `docs/API.md`.
5. Never infer a ClassicAPI function from Retail naming alone.
6. Distinguish:
   - engine/global API
   - `C_*` namespace API
   - bundled `!!!ClassicAPI` Lua helper
   - GlueXML-only API
   - console command
   - event
7. Prefer low-allocation APIs in combat hot paths.
8. Remember that ClassicAPI enhances a WoW 1.12.1 client. It does not turn the client into Wrath, Classic Era, or Retail wholesale.

---

# PART I — MAJOR CLIENT BEHAVIORS

## 4. Lua 5.1 Compatibility Layer

ClassicAPI backports substantial Lua 5.1 behavior to the underlying 1.12 Lua 5.0 environment.

### 4.1 Rewritten syntax

Documented rewritten syntax includes:

```lua
#table
a % b
...
0xFF
[=[ leveled long string ]=]
```

Addon files can use modern addon vararg form:

```lua
local addonName, addonTable = ...
```

### 4.2 String methods

Strings can resolve methods through the `string` table:

```lua
("asd"):upper()
("%d gold"):format(n)
msg:match("^!(%w+)")
```

### 4.3 Upvalue limit

ClassicAPI raises supported function upvalues toward Lua 5.1 behavior.

The official README documents support for up to 60 upvalues rather than Vanilla Lua 5.0's much smaller limit.

### 4.4 Modern script-handler arguments

Modern positional frame-script arguments are supported and enabled by default for handlers that declare parameters.

Examples:

```lua
frame:SetScript("OnClick", function(self, button)
end)

frame:SetScript("OnEvent", function(self, event, ...)
end)

frame:SetScript("OnMouseWheel", function(self, delta)
end)
```

ClassicAPI keeps legacy globals such as:

```lua
this
event
arg1
```

available as well.

Configuration:

```lua
SetModernScriptArgs(enable)
GetModernScriptArgs()
```

This changes one of the most important assumptions from stock 1.12: with ClassicAPI's default modern handler mode, modern positional event signatures are supported.

Do not carry forward old framework rules that categorically prohibit `(self, event, ...)` without first considering ClassicAPI's active script-argument behavior.

### 4.5 Lua/library backports

The official reference includes Lua/library compatibility such as:

```lua
collectgarbage
coroutine.create
coroutine.resume
coroutine.running
coroutine.status
coroutine.wrap
coroutine.yield

CreateFromMixins
Mixin
select

math.fmod
math.huge
math.modf

string.gmatch
string.match
string.reverse
```

and other helpers documented under the official Lua section.

### 4.6 Table lengths and weak values

[SOURCE-VERIFIED] ClassicAPI v1.15.12's `src/table/Length.cpp` hooks the stored-length
reader used by `table.getn`, `table.insert`, `table.remove`, `table.concat`,
`table.sort`, `table.foreachi`, and `unpack`. For ordinary tables whose stored final
slot is nil, it can heal the answer to a border. A border is not necessarily the
highest populated index in a sparse table.

The existing contracts remain: explicit numeric `t.n` preserves the count;
two-argument `table.insert(t, nil)` marks an intentional trailing nil reservation
(positional nil insertion does not); `table.setn` remains supported. A populated
stored final slot keeps the original length. Healing is a read-time answer, not
a write-back of the stored count.

**New in v1.15.12:** when the metatable's raw string `__mode` contains `"v"`
(including `"v"` and `"kv"`), the reader preserves the stored length even if the
stored final slot is nil. GC can clear weak values without any writer changing
the length; that nil therefore does not prove stale writer state. This exception
precedes the trailing-nil mark and border healing. Weak keys alone (`"k"`) do not
qualify. It does not make the length a count of live entries, and it does not keep
weak values alive.

This fixes the documented Compost-2.0 recycling case: GC clears slots 1 and 3 of
a three-slot weak-value pool while slot 2 remains live. Previously, healing could
return border 0, making `table.remove(cache, 2)` return no value and the caller
fail with `table index is nil`. The stored length now remains 3 so removal can
return the live value.

Do not mechanically replace `table.getn` with `#` or remove `table.setn` in code
that depends on these contracts. The transpiled `#` uses a separate border path;
the weak-value exception here concerns the stored-length reader.

Evidence: [v1.15.12 source/docs commit](https://github.com/brues-code/ClassicAPI/commit/fde3beca9dba18e7327802eb094b5bff81f39d47).
The maintainer reports in-game verification of the three-slot case and disappearance
of Compost errors in that commit. That is **upstream-reported empirical evidence**,
not Niko-local or VanillaForge runtime verification. [UNVERIFIED - TEST FIRST]
for reproduction in the user's installed client. Full provenance is in
[the release-range audit](docs/CLASSICAPI_1.15.12_AUDIT.md).

---

## 5. Modern Addon Loading

ClassicAPI adds modernized addon discovery and loading behavior.

### 5.1 Retail-like `/reload`

`/reload` can pick up:

- new addon directories
- new files added to TOCs
- metadata changes
- new SavedVariables metadata
- removed addons

without restarting the client.

### 5.2 Multi-flavor TOCs

ClassicAPI itself supports upstream flavor naming that may include server-specific
filenames. These are **ClassicAPI feature examples**, not VanillaForge branding or a
requirement that VanillaForge projects use those names.

Supported flavor filenames include:

```text
<Name>_ClassicAPI.toc
<Name>_Turtle.toc
```

ClassicAPI can process modern-style multi-flavor addon layouts.

### 5.3 Multiple Interface versions

A TOC may contain a comma-separated interface list and remain loadable when it includes the 1.12 interface version:

```text
11200
```

### 5.4 Conditional TOC lines

Documented conditional/path mechanisms include concepts equivalent to:

```text
[AllowLoadGameType]
[AllowLoadTextLocale]
[AllowLoad]
[Family]
[Game]
[TextLocale]
```

### 5.5 SavedVariables loaded first

ClassicAPI supports modern `LoadSavedVariablesFirst` behavior for addons that declare it.

### 5.6 Flavor-specific keybindings

Supported flavor binding files include:

```text
Bindings_ClassicAPI.xml
Bindings_Turtle.xml
```

---

## 6. Bundled `!!!ClassicAPI` Addon

ClassicAPI embeds a synthetic addon named:

```text
!!!ClassicAPI
```

It provides Lua-side helper libraries and compatibility utilities expected by modern Blizzard code.

Documented examples include:

```text
CallbackRegistryMixin
EventRegistry
ColorMixin
CreateColor
Item
ItemLocation
MathUtil
TableUtil
EventUtil
SecureCmdOptionParse
```

The bundled addon is automatically available when the DLL is loaded.

It can be queried by name:

```lua
IsAddOnLoaded("!!!ClassicAPI")
GetAddOnInfo("!!!ClassicAPI")
```

and can be referenced by dependency metadata.

A local physical `Interface/AddOns/!!!ClassicAPI/` copy can override the embedded files for development.

---

## 7. Built-in API Discovery

ClassicAPI includes an in-game API browser:

```text
/classicapi
```

Programmatic API documentation access:

```lua
C_APIDocumentation.GetSystems()
C_APIDocumentation.GetSystem(system)
```

Diagnostic helper:

```lua
_classicapi_UndocumentedAPI()
```

Use `/classicapi` when an exact current signature or return structure is needed and this snapshot is incomplete.

---

# PART II — MODERN CLIENT FEATURES

## 8. Focus

ClassicAPI implements a persistent focus target.

```lua
FocusUnit(unit)
ClearFocus()
```

Unit tokens:

```text
focus
focustarget
```

Event:

```text
PLAYER_FOCUS_CHANGED
```

Predefined bindings:

```text
FOCUSTARGET
TARGETFOCUS
```

Focus tokens work through the modernized UnitX path.

---

## 9. Nameplates

ClassicAPI provides event-driven modern nameplates.

Important namespace:

```lua
C_NamePlate
```

Common functions include:

```lua
C_NamePlate.GetNamePlates()
C_NamePlate.GetNamePlateForUnit(unit)
C_NamePlate.GetNamePlateForGUID(guid)
```

Unit tokens:

```text
nameplate1
nameplate2
...
```

Events:

```text
NAME_PLATE_CREATED
NAME_PLATE_UNIT_ADDED
NAME_PLATE_UNIT_REMOVED
```

Nameplate unit tokens participate in UnitX calls and unit events.

This is the preferred architecture over WorldFrame child scraping when the addon needs authoritative nameplate identity.

**Delivery Resilience (v1.15.13+):** [SOURCE-VERIFIED]
The dispatcher records a frame as announced only after it issues
`NAME_PLATE_CREATED`. A new GUID's `NAME_PLATE_UNIT_ADDED` waits for that frame's
announcement and a claimed ADDED event slot. If these conditions are not met,
the GUID receives no token slot or observers and is omitted from the announced
snapshot, allowing another attempt on a later tick while the plate remains visible.
This also avoids emitting REMOVED for a deferred ADDED that was never issued.
An unclaimed event slot does not by itself prove event-table exhaustion, and a
retry does not guarantee delivery on the next tick or successful addon handling.

Evidence: [nameplate fix](https://github.com/brues-code/ClassicAPI/commit/fa7d71435feabde2c5a08e9175321ca614b6449a).
The upstream maintainer explicitly reports that the dropped-slot case was not
verified in game. [UNVERIFIED - TEST FIRST] for that failure-path reproduction;
source verification is not local runtime verification. Event names/payloads are unchanged.

---

## 10. Raid Marker Unit Tokens

ClassicAPI adds:

```text
mark1
mark2
...
mark8
```

These resolve to the units carrying raid-target markers.

They support UnitX calls and unit-event routing.

Suffix chaining is documented, for example:

```text
mark1target
```

---

## 11. Inline Textures and Atlas Markup

ClassicAPI supports inline texture and atlas markup in text rendering:

```text
|T...|t
|A...|a
```

String measurements account for inline graphics.

---

## 12. Texture Size / Shape

ClassicAPI removes traditional power-of-two texture restrictions documented for the base client.

Arbitrary texture dimensions/shapes are supported subject to GPU limits.

---

## 13. Tooltip Capacity

ClassicAPI raises the standard GameTooltip line ceiling documented by the project from the stock limit to a larger modernized capacity.

This applies to GameTooltipTemplate-derived tooltips.

---

# PART III — MACROS AND SECURE-LIKE BEHAVIOR

## 14. Modern Macro Conditions

ClassicAPI expands `[conditions]` and `@unit` behavior across many slash commands.

Examples:

```text
/cast [@mouseover,harm][] Fireball
/cast [@player] GroundSpell
```

Supported concepts include:

```text
@mouseover
@player
@cursor
target=Name
```

Supported conditions include standard macro conditionals:
`[combat]`, `[nocombat]`, `[stealth]`, `[mounted]`, `[swimming]`, `[indoors]`,
`[outdoors]`, `[stance:N]` / `[form:N]`, `[mod:shift|ctrl|alt]`, `[pet:name]`,
`[button:N]` / `[btn:N]`, `[actionbar:N]`, and the ClassicAPI extension `[known:spellID|name]`.

#### `[button:N]` / `[btn:N]` Click-Context Evaluation (v1.15.9+)

`[button:N]` reads the mouse button of the click the macro is executing inside, matching what `GetMouseButtonClicked()` returns.

- **Button Numbers**: Follows modern API ordering — `1` (Left), `2` (Right), `3` (Middle), `4` (Button4), `5` (Button5). This is deliberately distinct from the 1.12 engine's internal bitmask (where 2 is middle); that bitmask never reaches Lua.
- **Button Names**: Case-insensitive string names match their numeric equivalents (`[button:rightbutton]` is identical to `[button:2]`; `[button:leftbutton]` is `[button:1]`).
- **Resting / Non-Click Context**: When evaluated outside an active mouse click (such as during a state-driver poll or during the periodic re-evaluation behind a macro's `#showtooltip` display), `[button:N]` answers as `"LeftButton"` (`1`). This ensures `#showtooltip` displays the resting left-button icon at rest and matches the engine's default `Button:Click()`.
- **Call Chain**: The click context reliably survives through `OnClick` -> attribute macro -> `EXECUTE_CHAT_LINE` -> `SlashCmdList` -> `SecureCmdOptionParse`.

### 14.1 `#showtooltip`

Supported:

```text
#showtooltip
#show
```

ClassicAPI can dynamically resolve:

- icon
- tooltip
- cooldown
- range
- usability
- auto-repeat glow

API for addon-controlled macro display:

```lua
C_Macro.SetMacroDisplay(...)
C_Macro.GetMacroIcon(...)
```

[SOURCE-VERIFIED] The established display contract remains: `#showtooltip` supplies
the resolved tooltip, whereas `#show` keeps the macro-name tooltip; a chosen icon
stays chosen, and a question-mark icon follows the resolution. `GetMacroInfo`
returns the stored icon; `C_Macro.GetMacroIcon` returns the displayed icon. Explicit
spell IDs can display unlearned spells (unusable); the bare directive derives its
answer from cast/use lines. Unknown foreign conditions are left to their owning
macro addon. `C_Macro.SetMacroDisplay(slot, value)` publishes an external answer;
`false` claims an unmatched display and `nil` releases ownership. These are
pre-v1.15.11 behaviors, not new APIs in this refresh.

**Spell-unlearn cleanup (v1.15.11+, retained in v1.15.12):** [SOURCE-VERIFIED]
the engine's spell-unlearn sweep must not remove a managed macro from an action-bar
slot merely because its display cache names the unlearned spell. Such removal
would otherwise be sent to the server and persist; this concerns the action-bar
placement, not deletion of the saved macro definition.

The fix covers both ClassicAPI-managed directives (`#showtooltip` / `#show`, with
parsed options and no foreign conditions) and externally published displays.
It temporarily hides their primary-spell caches from the sweep, prevents reentrant
`ACTIONBAR_SLOT_CHANGED` readers from repopulating those caches mid-sweep, then
restores them without an extra repaint. Subsequent directive evaluation catches
up with changed spell knowledge. External publishers still own updating their
published answer.

A bare managed `#showtooltip` macro also survives when its own `/cast` spell is
unlearned; this deliberately differs from stock cleanup. Unmanaged macros retain
stock behavior; a macro without a directive is protected only if externally
managed. This is not a blanket promise that every macro survives every removal.

Evidence: [v1.15.11 macro source and offsets](https://github.com/brues-code/ClassicAPI/commit/452f3c14fc3270420355edecd82e27868fc19d63).
The complete range contains this one macro implementation commit and no further
macro change in v1.15.12; see the [full audit](docs/CLASSICAPI_1.15.12_AUDIT.md)
for the earlier macro lineage and unchanged KP-53/KP-54 contracts.

### 14.2 Conditional slash-command families

Documented command families include:

Casting:

```text
/cast
/use
/castsequence
/castrandom
/userandom
/stopcasting
/stopmacro
/cancelaura
/cancelform
/dismount
```

Targeting:

```text
/target
/targetexact
/cleartarget
/targetlasttarget
/targetlastenemy
/targetenemy
/targetfriend
/targetenemyplayer
/targetfriendplayer
/targetparty
/targetraid
/assist
/follow
/focus
/clearfocus
/startattack
/stopattack
```

Equipment:

```text
/equip
/equipslot
/equipset
```

Action bars:

```text
/changeactionbar
/swapactionbar
/click
```

Pet:

```text
/petattack
/petfollow
/petstay
/petpassive
/petdefensive
/petaggressive
/petautocaston
/petautocastoff
/petautocasttoggle
```

### 14.3 Secure-style helpers

Documented API includes:

```lua
SecureCmdOptionParse(...)
RegisterStateDriver(...)
UnregisterStateDriver(...)
RegisterAttributeDriver(...)
UnregisterAttributeDriver(...)
RegisterUnitWatch(...)
UnregisterUnitWatch(...)
UnitWatchRegistered(...)
SecureButton_GetAttribute(...)
SecureButton_GetUnit(...)
```

Frame attributes:

```lua
frame:SetAttribute(...)
frame:SetAttributeNoHandler(...)
frame:ClearAttribute(...)
frame:GetAttribute(...)
```

Button scripts:

```text
PreClick
PostClick
```

---

# PART IV — FUNCTION / NAMESPACE CATALOG

The following is the official capability inventory exposed by the project documentation snapshot.

Exact signatures and return values should be obtained from the detailed section in `docs/API.md` or `/classicapi` when not stated here.

---

## 15. Action

```lua
GetActionInfo
```

Additional source-confirmed action helpers include modernized action state functions in the implementation, but use the official API browser for exact current exposure.

---

## 16. AddOns — `C_AddOns`

```lua
C_AddOns.DoesAddOnExist
C_AddOns.GetAddOnLocalTable
C_AddOns.GetAddOnName
C_AddOns.GetAddOnNotes
C_AddOns.GetAddOnOptionalDependencies
C_AddOns.GetAddOnSecurity
C_AddOns.GetAddOnTitle
C_AddOns.IsAddOnLoadable
C_AddOns.IsAddOnLoaded
C_AddOns.LoadAddOn
```

---

## 17. APIDocumentation — `C_APIDocumentation`

```lua
C_APIDocumentation.GetSystem
C_APIDocumentation.GetSystems
```

Plus:

```text
/classicapi
_classicapi_UndocumentedAPI()
```

---

## 18. Auction House — `C_AuctionHouse`

```lua
C_AuctionHouse.PostItem
```

---

## 19. Aura Utilities — `AuraUtil`

```lua
AuraUtil.ForEachAura
AuraUtil.FindAura
AuraUtil.FindAuraByName
AuraUtil.UnpackAuraData
```

For performance-sensitive aura scanning, `AuraUtil.ForEachAura` supports a zero-allocation path when used without packed aura-table construction.

---

## 20. Bindings

```lua
SetBindingSpell
SetBindingItem
SetBindingMacro
SetBindingClick

SetOverrideBinding
SetOverrideBindingSpell
SetOverrideBindingItem
SetOverrideBindingMacro
SetOverrideBindingClick
ClearOverrideBindings
```

---

## 21. Chat

```lua
GetCurrentChatGUID
```

---

## 22. Chat Bubbles — `C_ChatBubbles`

```lua
C_ChatBubbles.GetAllChatBubbles
```

---

## 23. Class

```lua
FillLocalizedClassList
```

---

## 24. Class Color — `C_ClassColor`

```lua
C_ClassColor.GetClassColor
```

---

## 25. Color Utilities — `C_ColorUtil`

```lua
C_ColorUtil.ConvertRGBToHSV
C_ColorUtil.ConvertHSVToRGB
C_ColorUtil.ConvertHSVToHSL
C_ColorUtil.ConvertHSLToHSV
C_ColorUtil.ConvertHSLToRGB
C_ColorUtil.GenerateTextColorCode
C_ColorUtil.WrapTextInColor
C_ColorUtil.WrapTextInColorCode
```

---

## 26. Combat

```lua
InCombatLockdown
StartAttack
StopAttack
```

---

## 27. Console

```lua
CalculateStringEditDistance
ConsoleEcho
ConsoleExec
ConsoleGetAllCommands
ConsoleGetColorFromType
ConsoleGetFontHeight
ConsoleIsActive
ConsolePrintAllMatchingCommands
SetConsoleKey
```

Developer-console commands:

```text
ExportInterfaceFiles code
ExportInterfaceFiles art
ExportDBCFiles
ExportSoundFiles [subpath]
```

---

## 28. CVars — `C_CVar`

```lua
C_CVar.AreCVarsLoaded
C_CVar.DoesCVarExist
C_CVar.GetCVarBitfield
C_CVar.GetCVarBool
C_CVar.GetCVarInfo
C_CVar.RemoveTempCVar
C_CVar.SetCVarBitfield
C_CVar.SetTempCVar
```

### Temporary Session CVars (v1.15.13+)

ClassicAPI v1.15.13 introduces non-persistent session CVar manipulation:

```lua
C_CVar.SetTempCVar(name, value)
C_CVar.RemoveTempCVar(name)
```

**Semantics & Implementation:** [SOURCE-VERIFIED]

- **Temporary value:** The setter requests a non-persistent change and records the
  live value before the first temporary set. That snapshot is not necessarily the
  value currently saved on disk. The config-writer hook substitutes the snapshot
  for an active override's live value during serialization, then restores the
  temporary value in memory.
- **Repeated sets and removal:** Repeated temporary sets preserve the first
  snapshot while the override still matches. Removal restores that snapshot only
  if the live value still equals the recorded temporary value; otherwise it drops
  the record without restoring. Removing an untracked valid CVar is a no-op.
- **Replacement detection:** Ordinary `SetCVar` is not hooked to clear ownership.
  A different live value is detected on a later temporary set, removal, or config
  write. The next temporary set then snapshots that replacement; removal/writing
  discards the old override record. A `SetCVar` writing the **same string** as the
  temporary value is indistinguishable from the override and does not release it.
  Do not rely on that call to make the temporary value permanent. For an explicit
  persistent change, remove the override first and then call `SetCVar`.
- **Arguments/returns:** Both functions return nothing. A nil temporary value
  becomes an empty string. Unknown or read-only CVars raise errors as with
  `SetCVar`; callbacks can normalize the value, and the implementation records
  the value that actually landed.
- **Scope/ownership:** Storage is process-global and both functions are available
  in game and on Glue/login screens. This is one override record per CVar, not a
  stack of independent addon owners. Coordinate overlapping users and remove an
  override when its owning mode ends; do not infer that `/reload` resets it.

Evidence: [temporary-CVar source](https://github.com/brues-code/ClassicAPI/blob/v1.15.13/src/cvar/Temp.cpp).
These are source-verified semantics; persistence and callback behavior still need
target-client testing before claiming [EMPIRICALLY VERIFIED].

---

## 29. Cursor

```lua
GetCursorInfo
```

---

## 30. Containers — `C_Container`

```lua
C_Container.AutoStoreItem
C_Container.CalculateTotalNumberOfFreeBagSlots
C_Container.GetBackpackAutosortDisabled
C_Container.GetBankAutosortDisabled
C_Container.GetContainerFreeSlots
C_Container.GetContainerItemCharges
C_Container.GetContainerItemDurability
C_Container.GetContainerItemEquipmentSetInfo
C_Container.GetContainerItemID
C_Container.GetContainerItemInfo
C_Container.GetContainerItemQuestInfo
C_Container.GetContainerItemRepairCost
C_Container.GetContainerNumFreeSlots
C_Container.GetItemCooldown
C_Container.GetSortBagsRightToLeft
C_Container.HasContainerItem
C_Container.IsContainerItemOpenable
C_Container.MoveItem
C_Container.PlayerHasHearthstone
C_Container.SetBackpackAutosortDisabled
C_Container.SetBankAutosortDisabled
C_Container.SetSortBagsRightToLeft
C_Container.SortBags
C_Container.SortBankBags
C_Container.SwapItems
C_Container.UseHearthstone
GetItemCooldown
```

Modernization use cases:

- replace manual sorting engines
- avoid cursor-driven Lua swap loops
- use delayed/batch container events
- obtain direct IDs/info without tooltip scraping

### Equipment Slot Grouping in SortBags (v1.15.13+)

[SOURCE-VERIFIED] The existing `C_Container.SortBags()` and
`C_Container.SortBankBags()` gain a new ordering; their signatures are unchanged.
Non-poor weapons/armor now share one gear category instead of four quality tiers.
Poor-quality gear remains junk. Category order is hearthstone, gear, consumables,
reagents, trade goods, quest items, other items by quality, then junk; junk fills
from the opposite end of the general-bag space.

Within gear, comparison is **item class -> inventory-type slot rank -> subclass ->
quality descending -> name -> stack count descending -> item ID**. Weapons sort
before armor because class precedes slot rank. Within armor, shields/held-offhands
precede head, shoulder, back, chest/robe, wrist, hands, waist, legs and feet;
neck, rings and trinkets follow feet, then shirt/tabard. Quality only orders items
after slot rank and subclass agree: a helm group is not globally highest-quality-first.

The exact source rank table (inventory-type IDs, in ascending priority) is:

```text
17, 13, 21, 14, 23, 26, 22, 15, 25, 24, 27, 28,
1, 3, 16, 5, 20, 9, 10, 6, 7, 8,
2, 11, 12, 4, 19, 18, 0
```

Unknown inventory types rank after these. This table applies within item class;
it is not a single global equipment-slot sequence. Upstream attributes the rank
order to Baganator, but the full sorting policy remains ClassicAPI's own.

**Integration constraints:** Both calls take no arguments and return nothing.
Sorting combines stacks and places items across server updates; it is not an
immediate completion contract. A call while the merge phase is pending is ignored,
including a competing bank/bag sort. Bank moves require the bank to be open.
Items with missing data stay pinned; bank stack merging also needs cached stack
limits. A later explicit sort can place items after their data arrives. Specialty
bags, excluded bags, and the configured fill direction still affect placement.

`BAG_UPDATE_DELAYED` is a batched view-refresh signal, **not a sort-completion
event**. The Lua event fires before the C++ bag-update subscribers, including the
one that may start placement after merging. Do not announce success or complete
an addon transaction on the first such event; verify the relevant inventory state
if a completion claim is needed. Do not start another sort on every bag update.

Prefer this implementation when its policy meets the addon's requirements. If a
different ordering is required, the verified native movement primitives
`C_Container.SwapItems`, `C_Container.MoveItem`, and `C_Container.AutoStoreItem`
can support it. This release alone does not establish that every bag addon can
discard its custom ordering or classification.

Evidence: [sorting source](https://github.com/brues-code/ClassicAPI/blob/v1.15.13/src/container/SortBags.cpp),
[bag-update dispatcher](https://github.com/brues-code/ClassicAPI/blob/v1.15.13/src/bag/UpdateDelayed.cpp).

---

## 31. Creature — `C_CreatureInfo`

```lua
C_CreatureInfo.GetCreatureID
C_CreatureInfo.GetCreatureInfoByID
C_CreatureInfo.RequestLoadCreatureByID
C_CreatureInfo.GetRaceInfo
C_CreatureInfo.GetClassInfo
C_CreatureInfo.GetCreatureFamilyInfo
C_CreatureInfo.GetCreatureFamilyIDs
C_CreatureInfo.GetFactionInfo
C_CreatureInfo.GetCreatureTypeInfo
C_CreatureInfo.GetCreatureTypeIDs
```

---

## 32. Currency — `C_CurrencyInfo`

```lua
GetCoinTextureString
C_CurrencyInfo.GetCoinTextureString
```

---

## 33. Encoding — `C_EncodingUtil`

```lua
C_EncodingUtil.CompressString
C_EncodingUtil.DecompressString
C_EncodingUtil.EncodeBase64
C_EncodingUtil.DecodeBase64
C_EncodingUtil.EncodeHex
C_EncodingUtil.DecodeHex
C_EncodingUtil.SerializeJSON
C_EncodingUtil.DeserializeJSON
C_EncodingUtil.SerializeCBOR
C_EncodingUtil.DeserializeCBOR
```

---

## 34. Equipment Sets — `C_EquipmentSet`

```lua
C_EquipmentSet.CanUseEquipmentSets
C_EquipmentSet.ClearIgnoredSlotsForSave
C_EquipmentSet.CreateEquipmentSet
C_EquipmentSet.DeleteEquipmentSet
C_EquipmentSet.EquipmentSetContainsLockedItems
C_EquipmentSet.GetEquipmentSetID
C_EquipmentSet.GetEquipmentSetIDs
C_EquipmentSet.GetEquipmentSetInfo
C_EquipmentSet.GetIgnoredSlots
C_EquipmentSet.GetItemIDs
C_EquipmentSet.GetItemLocations
C_EquipmentSet.GetNumEquipmentSets
C_EquipmentSet.IgnoreSlotForSave
C_EquipmentSet.IsSlotIgnoredForSave
C_EquipmentSet.ModifyEquipmentSet
C_EquipmentSet.SaveEquipmentSet
C_EquipmentSet.UnignoreSlotForSave
C_EquipmentSet.UseEquipmentSet
```

Related events:

```text
EQUIPMENT_SETS_CHANGED
EQUIPMENT_SWAP_PENDING
EQUIPMENT_SWAP_FINISHED
```

---

## 35. Events — `C_EventUtils`

```lua
C_EventUtils.IsEventValid
GetFramesRegisteredForEvent
```

ClassicAPI also improves/adds event coverage. See the dedicated event catalog later in this document.

---

## 36. Expansion

```lua
ClassicExpansionAtLeast
ClassicExpansionAtMost
GetClassicExpansionLevel
```

---

## 37. Faction / Reputation — `C_Reputation`

```lua
C_Reputation.GetFactionDataByID
C_Reputation.GetFactionDataByIndex
C_Reputation.GetFactionStandings
C_Reputation.GetLastStandingChange
C_Reputation.GetWatchedFactionData
C_Reputation.IsFactionActive
C_Reputation.IsFactionActiveByID
C_Reputation.IsFactionInactive
C_Reputation.SetFactionActive
C_Reputation.SetFactionActiveByID
C_Reputation.SetFactionInactive
C_Reputation.SetFactionInactiveByID
C_Reputation.SetSelectedFaction
C_Reputation.SetSelectedFactionByID
C_Reputation.SetWatchedFactionByID
C_Reputation.ToggleFactionAtWar
C_Reputation.ToggleFactionAtWarByID

GetFactionIDByIndex
GetFactionInfoByID
GetFactionParentID
```

---

## 38. Focus

```lua
ClearFocus
FocusUnit
```

---

## 39. Frame / Region / FontString / Texture / EditBox

General region/frame helpers:

```lua
region:SetPoint("point")
region:SetSize
region:GetSize
region:IsMouseOver
region:GetRect
region:IsDragging

GetMouseFoci

frame:SetShown
frame:SetResizeBounds
frame:HookScript
frame:IsEventRegistered
frame:RegisterUnitEvent
frame:GetEffectiveAlpha
```

Frame attributes and secure-style support:

```lua
frame:SetAttribute
frame:SetAttributeNoHandler
frame:ClearAttribute
frame:GetAttribute
```

Modern script argument controls:

```lua
SetModernScriptArgs
GetModernScriptArgs
```

FontString:

```lua
fontstring:GetStringHeight
fontstring:GetUnboundedStringWidth
fontstring:GetWrappedWidth
fontstring:GetNumLines
fontstring:GetLineHeight
fontstring:IsTruncated
fontstring:SetMaxLines
fontstring:GetMaxLines
fontstring:SetFormattedText
fontstring:SetRotation
fontstring:GetRotation
```

Texture:

```lua
texture:SetRotation
texture:GetRotation
texture:SetVertexOffset
texture:GetVertexOffset
texture:SetColorTexture
texture:SetAtlas
texture:GetAtlas
texture:ResetTexCoord
texture:SetSpriteSheetCell
texture:SetDesaturation
texture:GetDesaturation
texture:SetMask

frame:CreateMaskTexture
texture:AddMaskTexture
texture:RemoveMaskTexture
texture:GetNumMaskTextures
texture:GetMaskTexture
```

EditBox:

```lua
editBox:SetCursorPosition
editBox:GetCursorPosition
editBox:GetUTF8CursorPosition
editBox:ClearHighlightText
editBox:HasFocus
editBox:HasText
editBox:SetHighlightColor
editBox:GetHighlightColor
editBox:ClearHistory
```

Buttons:

```lua
button:RegisterForClicks("AnyUp", "AnyDown", ...)
GetClickFrame
```

Script types include:

```text
OnAttributeChanged
PreClick
PostClick
```

---

## 40. Friend List — `C_FriendList`

```lua
C_FriendList.GetFriendInfo
C_FriendList.GetFriendInfoByIndex
C_FriendList.GetNumFriends
C_FriendList.GetNumOnlineFriends
C_FriendList.GetNumWhoResults
C_FriendList.GetWhoInfo
C_FriendList.IsFriend
C_FriendList.IsIgnored
C_FriendList.IsIgnoredByGuid
C_FriendList.IsWhoQueryPending
C_FriendList.SendWhoQueryByName
C_FriendList.SetFriendNotes
C_FriendList.SetFriendNotesByIndex
```

---

## 41. Game Objects — `C_GameObjectInfo`

```lua
C_GameObjectInfo.GetGameObjectInfoByID
C_GameObjectInfo.RequestLoadGameObjectByID
ClosestGameObjectPosition
```

---

## 42. Glue

```lua
C_Glue.IsOnGlueScreen
```

Additional glue-state APIs are documented separately below.

---

## 43. Gossip — `C_GossipInfo`

```lua
C_GossipInfo.CloseGossip
C_GossipInfo.GetActiveQuests
C_GossipInfo.GetAvailableQuests
C_GossipInfo.GetNumActiveQuests
C_GossipInfo.GetNumAvailableQuests
C_GossipInfo.GetNumOptions
C_GossipInfo.GetOptions
C_GossipInfo.GetText
C_GossipInfo.SelectActiveQuest
C_GossipInfo.SelectAvailableQuest
C_GossipInfo.SelectOption
C_GossipInfo.SelectOptionByIndex
```

---

## 44. GameTooltip

```lua
GameTooltip:AddSpellByID
GameTooltip:GetGameObject
GameTooltip:GetItem
GameTooltip:GetOwner
GameTooltip:GetSpell
GameTooltip:GetUnitGUID
GameTooltip:HasGameObject
GameTooltip:HasItem
GameTooltip:HasSpell
GameTooltip:HasUnit
GameTooltip:IsEquippedItem
GameTooltip:SetEquipmentSet
GameTooltip:SetHyperlinkCompareItem
GameTooltip:SetInventoryItemByID
GameTooltip:SetItemByGUID
GameTooltip:SetItemByID
GameTooltip:SetSpellByID
GameTooltip:SetTalentByID
GameTooltip:SetTotem
GameTooltip:SetUnitAura
```

Tooltip scripts:

```text
OnTooltipSetItem
OnTooltipSetSpell
OnTooltipSetUnit
OnTooltipSetGameObject
```

---

## 45. Hooks

```lua
hooksecurefunc
```

---

## 46. Input

```lua
GetMouseButtonClicked
IsLeftAltKeyDown
IsLeftControlKeyDown
IsLeftShiftKeyDown
IsModifierKeyDown
IsMouseButtonDown
IsRightAltKeyDown
IsRightControlKeyDown
IsRightShiftKeyDown
```

---

## 47. Instance

```lua
GetInstanceInfo
```

---

## 48. Item — `C_Item`

ClassicAPI has a broad modern item API.

Documented functions include:

```lua
C_Item.DoesItemExist
C_Item.DoesItemExistByID
C_Item.EquipItemByName
C_Item.GetCurrentItemLevel
C_Item.GetDetailedItemLevelInfo
C_Item.GetEnchantInfo
C_Item.GetItemCount
C_Item.GetItemFamily
C_Item.GetItemGUID
C_Item.GetItemIcon
C_Item.GetItemIconByID
C_Item.GetItemID
C_Item.GetItemInfo
C_Item.GetItemInfoInstant
C_Item.GetItemInventorySlotInfo
C_Item.GetItemInventorySlotKey
C_Item.GetItemInventoryType
C_Item.GetItemInventoryTypeByID
C_Item.GetItemLink
C_Item.GetItemLocation
C_Item.GetItemMaxStackSize
C_Item.GetItemMaxStackSizeByID
C_Item.GetItemName
C_Item.GetItemNameByID
C_Item.GetItemQuality
C_Item.GetItemQualityByID
C_Item.GetItemSellPrice
C_Item.GetItemSellPriceByID
C_Item.GetItemSetID
C_Item.GetItemSetIDByID
C_Item.GetItemSetInfo
C_Item.GetItemSpell
C_Item.GetItemStatDelta
C_Item.GetItemStats
C_Item.GetItemClassInfo
C_Item.GetItemSubClassInfo
C_Item.GetItemTempEnchantInfo
C_Item.GetItemUniqueness
C_Item.GetItemUniquenessByID
C_Item.GetStackCount
C_Item.GetWeaponEnchantInfo
C_Item.IsBound
C_Item.IsConsumableItem
C_Item.IsEquippableItem
C_Item.IsEquippedItem
C_Item.IsItemDataCached
C_Item.IsItemDataCachedByID
C_Item.IsItemGUIDInInventory
C_Item.IsItemInRange
C_Item.IsItemOpenable
C_Item.IsLocked
C_Item.LockItem
C_Item.LockItemByGUID
C_Item.PickupItem
C_Item.RequestLoadItemData
C_Item.RequestLoadItemDataByID
C_Item.UnlockAllItems
C_Item.UnlockItem
C_Item.UseAtCursor
C_Item.UseAtUnit
C_Item.UseItemByName
```

Additional ID/data accessors include:

```lua
GetAuctionItemID
GetAuctionSellItemID
GetAverageItemLevel
GetCraftReagentItemID
GetInboxItemID
GetInventoryItemDurability
GetInventoryItemID
GetInventoryItemsForSlot
GetInventoryItemRepairCost
GetItemClassInfo
GetItemIcon
GetItemSubClassInfo
GetLootRollItemID
GetLootSlotItemID
GetMerchantItemID
GetQuestItemID
GetQuestLogItemID
GetTradePlayerItemID
GetTradeSkillItemID
GetTradeSkillReagentItemID
GetTradeTargetItemID
OffhandHasWeapon
```

This namespace should be checked before implementing tooltip-based item metadata extraction.

---

## 49. Loot — `C_Loot`

```lua
C_Loot.GetNearbyLootableUnits
C_Loot.GetLastScanResults
C_Loot.IsScanInProgress
C_Loot.LootAllCorpses
C_Loot.LootUnit
C_Loot.LootUnitItem
C_Loot.ScanNearbyLoot
```

Related event:

```text
LOOT_SCAN_COMPLETED
```

---

## 50. Loot History — `C_LootHistory`

```lua
C_LootHistory.GetNumItems
C_LootHistory.GetItem
C_LootHistory.GetPlayerInfo
C_LootHistory.Clear
```

Related events:

```text
LOOT_HISTORY_ROLL_CHANGED
LOOT_HISTORY_ROLL_COMPLETE
LOOT_HISTORY_FULL_UPDATE
```

---

## 51. Loss of Control — `C_LossOfControl`

```lua
C_LossOfControl.GetActiveLossOfControlData(index)
C_LossOfControl.GetActiveLossOfControlDataCount()
C_LossOfControl.GetSchoolLockout([filterMask])
```

### `C_LossOfControl.GetSchoolLockout([filterMask])` (v1.15.9+)

Returns the school-interrupt lockout state directly without building the full
active effect list:

```lua
local lockedMask, secondsRemaining = C_LossOfControl.GetSchoolLockout([filterMask])
```

- **`lockedMask`** (`number`): Bitwise OR of all currently locked spell schools,
  shaped as `1 << schoolIndex` (physical=1, holy=2, fire=4, nature=8, frost=16,
  shadow=32, arcane=64). Returns `0` when no school is locked. Multiple schools
  can be locked concurrently (each `SMSG_SPELL_COOLDOWN` batch locks one).
- **`secondsRemaining`** (`number` or `nil`): Time in seconds until all schools in
  `lockedMask` are clear (the lockout ending last). Returns `nil` when `lockedMask == 0`.
- **`filterMask`** (`number`, optional): Narrows the scan to specified schools
  (e.g. `C_LossOfControl.GetSchoolLockout(4)` queries Fire alone). Omitted or `0`
  evaluates all schools.

**Performance & Architecture:**
`GetSchoolLockout` reads internal `g_schoolLock` tick pairs directly:
- Allocates zero Lua tables (unlike `GetActiveLossOfControlData`).
- Skips the 16-slot debuff/aura scan that `GetActiveLossOfControlData` executes.
- Efficient enough to call per-frame inside macro conditionals or combat timers.

**Event Diffing Behavior:**
`LOSS_OF_CONTROL_ADDED` and `LOSS_OF_CONTROL_UPDATE` fire only when the set of
active effects changes. Re-locking an already-locked school extends its duration
(`endMs`) without firing either event. Always query remaining time directly rather
than caching expiry on event timestamps.

Related events:

```text
LOSS_OF_CONTROL_ADDED
LOSS_OF_CONTROL_UPDATE
```

Useful for PvP CC / school lockout addons.

---

## 52. Macro — `C_Macro`

```lua
C_Macro.GetMacroIcon
C_Macro.SetMacroDisplay
C_Macro.CreateMacro
C_Macro.EditMacro
```

Global macro icon enumeration helpers:

```lua
GetMacroIcons(iconList)
GetMacroItemIcons(itemList)
GetLooseMacroIcons(iconList)
GetLooseMacroItemIcons(itemList)
```

### Macro Icon Enumeration Architecture (v1.15.9+)

ClassicAPI categorizes macro icons across two dimensions:
1. **Origin**: `loose` (custom icons placed by the user on disk in `Interface\Icons\`) vs `mpq` (shipped inside the client MPQ archives).
2. **Category**: `Spell` (basenames beginning with `Ability_*` or `Spell_*`) vs `Item` (basenames beginning with `INV_*`).

**Engine Loader & Filter Details:**
- The engine's internal icon loader (`FUN_LOAD_MACRO_ICONS`) runs three passes:
  - **Pass 1** (MPQ archive walk): Prefix-filtered for `Ability_*` / `Spell_*`.
  - **Pass 2** (Disk walk): Prefix-filtered for `Ability_*` / `Spell_*` in `<basePath>\Interface\Icons\`.
  - **Pass 3** (Disk walk): Extension-only filter (`.blp`/`.tga`) for `Interface\Icons\`.
- In a stock client install, disk folder `Interface\Icons\` is empty, so pass 3 discovers nothing. Consequently, the engine's built-in array (`GetNumMacroIcons() == 746`) contains only `Ability_*`/`Spell_*` icons.
- Putting custom `INV_*.blp` files directly into `Interface\Icons\` allows them to enter the engine's list via pass 3 after restarting the client.
- The ~5,226 `INV_*` icons shipped inside MPQs are rejected by pass 1 prefix filtering. ClassicAPI hooks all three enumeration callbacks at their entry point, capturing these archive item icons into a separate list for `GetMacroItemIcons`.
- `GetMacroIconInfo(index)` returns `""` (empty string) rather than `nil` when queried with an out-of-bounds index.
- Only `GetNumMacroIcons()` triggers the engine's lazy icon array build (gated on `count == 0`).

Also inspect `/classicapi` for the complete current Macro namespace.

---

## 53. Map — `C_Map`

ClassicAPI provides modern map/world coordinate and waypoint support.

Known capabilities from the project include APIs for:

- player map position
- map metadata
- conversion between map and world coordinates
- user waypoints

Event:

```text
USER_WAYPOINT_UPDATED
```

Use `/classicapi` for the complete current map function list and exact signatures.

---

## 54. Sound — `C_Sound`

Documented/known capabilities include APIs for:

- playing SoundKit IDs
- playing item sounds
- vocal error sounds
- sound options
- querying scaled volume
- recent sound files
- muting/unmuting sound files

Known names from current project knowledge include:

```lua
C_Sound.PlaySound
C_Sound.PlayItemSound
C_Sound.PlayVocalErrorSound
C_Sound.PlaySoundWithOptions
C_Sound.GetSoundScaledVolume
C_Sound.GetRecentSoundFiles
MuteSoundFile
UnmuteSoundFile
```

Event:

```text
SOUNDKIT_FINISHED
```

Inspect the current API browser for exact signatures.

---

## 55. Spell — `C_Spell`

This is one of the largest and most useful modernization areas.

```lua
C_Spell.DoesSpellExist
C_Spell.GetSchoolString
C_Spell.GetSpellInfo
C_Spell.GetSpellName
C_Spell.GetSpellTexture
C_Spell.GetSpellLink
C_Spell.GetSpellDescription
C_Spell.GetSpellMechanicByID
C_Spell.GetSpellEffectInfo
C_Spell.GetSpellEffectMechanics
C_Spell.GetSpellDispelType
C_Spell.GetSpellRadius
C_Spell.GetSpellPowerCost
C_Spell.GetSpellReagents
C_Spell.GetSpellCastCount
C_Spell.GetSpellSubtext
C_Spell.IsSpellPassive
C_Spell.IsSpellUsable
C_Spell.GetSpellCooldown
C_Spell.GetSpellLossOfControlCooldown
C_Spell.IsCurrentSpell
C_Spell.IsSelfBuff
C_Spell.SpellHasRange
C_Spell.IsSpellInRange
C_Spell.IsAutoAttackSpell
C_Spell.IsRangedAutoAttackSpell
C_Spell.IsNextMeleeSpell
C_Spell.ResetsMeleeSwing
C_Spell.IsSpellHarmful
C_Spell.IsSpellHelpful
C_Spell.CastAtCursor
C_Spell.CastAtUnit
C_Spell.CancelSpellByID
C_Spell.UnitCastingInfo
C_Spell.CastingInfo
C_Spell.UnitChannelInfo
C_Spell.ChannelInfo
C_Spell.GetSpellLevelInfo
```

Global helpers:

```lua
GetSpellInfo
GetSpellLink
IsPassiveSpell
IsPlayerSpell
CanDualWield
IsSpellKnown
GetSpellBonusDamage
GetSpellBonusHealing
IsUsableSpell
SpellHasRange
IsHarmfulSpell
IsHelpfulSpell
GetSpellSchool
CastSpellNoToggle
CancelSpellByName
GetSpellRequiredTargetLevel
```

For castbar modernization, prefer:

```lua
C_Spell.UnitCastingInfo(unit)
C_Spell.UnitChannelInfo(unit)
```

plus `UNIT_SPELLCAST_*` events where appropriate.

---

## 56. SpellBook — `C_SpellBook`

```lua
FindSpellBookSlotByID
C_SpellBook.GetSpellBookItemInfo
C_SpellBook.GetNumSpellBookSkillLines
C_SpellBook.GetSpellBookSkillLineInfo
C_SpellBook.GetSpellBookItemSkillLineIndex
C_SpellBook.GetSkillLineIndexByID
C_SpellBook.GetSpellBookItemCastCount
C_SpellBook.GetSpellBookItemLossOfControlCooldownInfo
C_SpellBook.GetSpellBookItemLossOfControlCooldownDuration
C_SpellBook.IsClassTalentSpellBookItem
C_SpellBook.ContainsAnyDisenchantSpell
C_SpellBook.GetSpellLevelLearned
C_SpellBook.GetCurrentLevelSpells
C_SpellBook.GetPlayerSpellsByAura
C_SpellBook.GetSkillLineName
C_SpellBook.GetSkillLineRank
C_SpellBook.GetSpellSkillLine
C_SpellBook.IsAutoAttackSpellBookItem
C_SpellBook.IsRangedAutoAttackSpellBookItem
```

---

## 57. State

```lua
IsMounted
Dismount
IsStealthed
IsFalling
IsSwimming
IsIndoors
IsOutdoors
IsAssistingRitual
IsInGroup
IsInRaid
GetMirrorTimerInfo
GetMirrorTimerProgress
GetShapeshiftFormID
CancelShapeshiftForm
GetSheathState
```

---

## 58. Swing Timer — `C_SwingTimer`

`[EMPIRICALLY VERIFIED]` for range check and 2D geometry; `[SOURCE-VERIFIED]` for API contract.

Reports auto-attack range state for melee and ranged weapons against the current target.

```lua
C_SwingTimer.EnableRangeCheck(swingType, enable)
C_SwingTimer.IsTargetWithinSwingRange(swingType)
```

- `EnableRangeCheck(swingType, enable)`: Turns `PLAYER_SWING_RANGE_UPDATE` dispatching on or off for `swingType` (`Enum.PlayerSwingType`). Seeds internal range state without an immediate event fire. Call `IsTargetWithinSwingRange` once after enabling to read the baseline state.
- `IsTargetWithinSwingRange(swingType)`: Returns `true` (in range), `false` (out of range), or `nil` (no check possible).
- **Critical Semantic:** A `nil` return occurs when there is no target, the target cannot be attacked, or no weapon is equipped for that swing type. `nil` must **never** be treated as out of range. Auto-attacks apply strictly to `"target"`.

---

## 59. System

```lua
GetPhysicalScreenSize
CopyToClipboard
```

---

## 60. Talent

```lua
GetTalentSpellID
GetTalentIDByIndex
```

---

## 61. Targeting

```lua
GetPlayerFacing
TargetDirectionEnemy
TargetDirectionFriend
TargetNearest
TargetNearestEnemyPlayer
TargetNearestFriendPlayer
```

---

## 62. Taxi Map — `C_TaxiMap`

```lua
C_TaxiMap.GetTaxiNodesForMap
C_TaxiMap.GetAllTaxiNodes
C_TaxiMap.GetTaxiPaths
C_TaxiMap.GetTaxiPathWaypoints
C_TaxiMap.GetTaxiRoute
```

---

## 63. Texture — `C_Texture`

```lua
C_Texture.GetAtlasInfo
C_Texture.GetAtlasExists
C_Texture.GetAtlasID
C_Texture.GetAtlasElementID
C_Texture.GetAtlasElements
C_Texture.RegisterAtlas
```

Also:

```lua
texture:SetAtlas(...)
texture:GetAtlas()
texture:SetSpriteSheetCell(...)
```

Atlas markup is supported in text.

---

## 64. Time — `C_Timer` / `C_DateAndTime`

Timers:

```lua
C_Timer.After
C_Timer.NewTimer
C_Timer.NewTicker
```

Time:

```lua
GetServerTime
GetTimeCached

C_DateAndTime.AdjustTimeByDays
C_DateAndTime.AdjustTimeByMinutes
C_DateAndTime.CompareCalendarTime
C_DateAndTime.GetCalendarTimeFromEpoch
C_DateAndTime.GetCurrentCalendarTime
C_DateAndTime.GetSecondsUntilDailyReset
C_DateAndTime.GetServerTimeLocal
```

This should be checked before writing custom timer queues or home-grown server-time synchronization.

---

## 65. Totems

```lua
GetTotemInfo
GetTotemTimeLeft
GetTotemDuration
TargetTotem
```

Event:

```text
PLAYER_TOTEM_UPDATE
```

---

## 66. Tracking

```lua
GetNumTrackingTypes
GetTrackingInfo
SetTracking
```

---

## 67. TradeSkillUI — `C_TradeSkillUI`

```lua
C_TradeSkillUI.GetTradeSkillListLink
C_TradeSkillUI.GetCraftListLink
C_TradeSkillUI.GetTradeSkillListRecipes
```

---

## 68. UIColor — `C_UIColor`

```lua
C_UIColor.GetColors
```

---

## 69. Unit

Identity/token helpers:

```lua
UnitGUID
UnitTokenFromGUID
UnitTokenFromName
IsUnitToken
```

Identity/metadata:

```lua
UnitSubName
UnitCreatureFamilyID
UnitCreatureTypeID
UnitCreatureID
UnitClassBase
UnitRaceBase
UnitOwnerGUID
UnitCreatedBySpell
```

Movement/spatial:

```lua
GetUnitSpeed
UnitInRange
UnitDistanceSquared
UnitPosition
UnitInLineOfSight
ClosestUnitPosition
```

State:

```lua
UnitIsAFK
UnitIsDND
UnitIsFeignDeath
UnitIsInMyGuild
UnitIsPossessed
UnitIsMinion
UnitIsPet
UnitIsOtherPlayersPet
UnitStandState
```

Health/power:

```lua
UnitHealthMissing
UnitPower
UnitPowerMax
UnitPowerMissing
UnitPowerType
```

Spell:

```lua
UnitSpellHaste
UnitSpellTargetName
```

ClassicAPI should be consulted before adding custom GUID-to-token registries, distance approximations, or legacy UnitX wrappers.

---

## 70. Unit Auras — `C_UnitAuras`

This is a major modernization API.

Table/data access:

```lua
C_UnitAuras.GetAuraDataByIndex
C_UnitAuras.GetBuffDataByIndex
C_UnitAuras.GetDebuffDataByIndex
C_UnitAuras.GetAuraDataBySlot
C_UnitAuras.GetUnitAuraBySpellID
C_UnitAuras.GetPlayerAuraBySpellID
C_UnitAuras.GetAuraDataBySpellName
C_UnitAuras.GetUnitAuras
C_UnitAuras.GetAuraDispelTypeColor
```

Slot access:

```lua
C_UnitAuras.GetAuraSlots
```

Zero-allocation positional forms:

```lua
C_UnitAuras.UnitAura
C_UnitAuras.UnitAuraBySlot
C_UnitAuras.UnitBuff
C_UnitAuras.UnitDebuff
```

Duration helpers:

```lua
C_UnitAuras.RegisterComboDuration
C_UnitAuras.RegisterAuraDurationModifierByTrigger
```

Aura helpers:

```lua
AuraUtil.ForEachAura
AuraUtil.FindAura
AuraUtil.FindAuraByName
AuraUtil.UnpackAuraData
```

### Positional Return Signature Discipline

[SOURCE-VERIFIED] `C_UnitAuras.UnitAura`, `C_UnitAuras.UnitBuff`, `C_UnitAuras.UnitDebuff`, and `C_UnitAuras.UnitAuraBySlot` return values positionally in modern ClassicAPI order:

```lua
name, icon, count, dispelType, duration, expirationTime, source, isStealable, nameplateShowPersonal, spellId, canApplyAura, isBossDebuff, isCastByPlayer, nameplateShowAll, timeMod = C_UnitAuras.UnitAura(unit, index [, filter])
```

(The same positional return sequence applies to `C_UnitAuras.UnitBuff`, `C_UnitAuras.UnitDebuff`, and `C_UnitAuras.UnitAuraBySlot(unit, slot)`).

**Critical Contract Rules:**
- **No `rank` return:** ClassicAPI modern aura APIs do **not** return a `rank` string.
- **Unpack offset hazard:** Legacy 2.0/3.3.5 APIs returned `name, rank, icon, count...`. Assuming a legacy signature shifts position 4 (`dispelType`) into `count`, resulting in runtime Lua errors such as `attempt to compare number with string`.
- **No type shims:** Do NOT apply `tonumber` or type shims to mask shifted unpack arguments. Correct the unpack mapping to the canonical signature.

### Performance Note

The current ClassicAPI source explicitly documents the positional `C_UnitAuras.UnitAura` path as a no-table-allocation route.

For high-frequency aura scanning, this can be preferable to constructing a Lua table per aura.

This namespace should replace legacy hidden tooltip aura scanners.

### Aura Slot Compaction and Index Instability

Aura indices (`1, 2, ... N`) are compacting array positions, **not stable aura identities**.
- When an aura expires or is dispelled at index `k`, all higher-indexed auras immediately shift downward to fill the vacant index.
- Never assume an aura index or button frame remains bound to the same spell or aura instance across updates.
- Cooldown frames, OnUpdate scripts, and duration caches must never be keyed to transient array indices. Key cached active state by `(spellId, source)` or fully reset the button frame upon identity mismatch.

### Aura Filter Tokens

`C_UnitAuras` functions accepting a filter string (`"HELPFUL"`, `"HARMFUL"`, etc.) support:

- `HELPFUL` / `HARMFUL`: Filter buffs or debuffs by polarity.
- `PLAYER` / `!PLAYER`: `[EMPIRICALLY VERIFIED]` for player/pet inclusion; `[SOURCE-VERIFIED]` for attribution and cache semantics (`src/aura/Data.h`).
  - `PLAYER` matches only auras attributable to the local player or the player's pet (`PlayerGuid()` or `VAR_PET_GUID`), matching modern `AuraUtil.AuraFilters.Player`. Auras whose caster is unknown or unresolved (e.g. cache misses, or auras predating observation this session) are excluded. (In v1.15.9 and earlier, `PLAYER` tested only `PlayerGuid()`, which silently dropped pet auras such as Hunter pet Scorpid Poison because `SMSG_SPELL_GO` attributes pet casts to the pet's GUID).
  - `!PLAYER` is the strict complement: it matches auras attributable to other casters AND any aura whose caster is unknown or unresolved due to missing cache attribution. Because unobserved casts lack caster data, `!PLAYER` must **not** be treated as proof that an aura was cast by a confirmed third party.
- `DISPELLABLE` / `!DISPELLABLE`: Filter by whether the aura can be dispelled, purged, or stolen.
- `CROWD_CONTROL` / `!CROWD_CONTROL`: Filter by crowd-control mechanic flags.

---

## 71. Voice Chat / Text-to-Speech

```lua
C_VoiceChat.GetTtsVoices
C_VoiceChat.GetRemoteTtsVoices
C_VoiceChat.SpeakText
C_VoiceChat.StopSpeakingText

C_TTSSettings.GetSpeechRate
C_TTSSettings.GetSpeechVolume
C_TTSSettings.GetSpeechVoiceID
C_TTSSettings.GetVoiceOptionName
C_TTSSettings.SetSpeechRate
C_TTSSettings.SetSpeechVolume
C_TTSSettings.SetVoiceOption
C_TTSSettings.SetVoiceOptionByName
C_TTSSettings.SetDefaultSettings
C_TTSSettings.RefreshVoices
```

Related events:

```text
VOICE_CHAT_TTS_PLAYBACK_STARTED
VOICE_CHAT_TTS_PLAYBACK_FINISHED
VOICE_CHAT_TTS_PLAYBACK_FAILED
VOICE_CHAT_TTS_VOICES_UPDATE
```

### Event Reservation Stability Note

- `VOICE_CHAT_TTS_VOICES_UPDATE`: `[SOURCE-VERIFIED]` In `src/event/Custom.cpp` (commit `6812771a896f8c7b3b5c97686c518266085f2d8f`), the custom event reservation ceiling `MAX_RESERVED` was raised from 64 to 96, removing the reservation-ceiling overflow condition. ClassicAPI v1.15.9 had 63 reservations (under the 64-slot ceiling). During development toward v1.15.10, the addition of the two swing events brought the count to 65 (60 file-scope plus 5 lazy TTS reservations on clients without VanillaTTS), causing the 65th reservation (`VOICE_CHAT_TTS_VOICES_UPDATE`) to exceed the 64-slot ceiling (`Slot()` stayed -1 and `Fire()` no-opped). Raising `MAX_RESERVED` to 96 resolved this overflow and accommodates subsequent additions (66 reservations in v1.15.10 after `WEAPON_SLOT_CHANGED`).

---

## 72. XML Utilities — `C_XMLUtil`

```lua
C_XMLUtil.DoesTemplateExist
C_XMLUtil.GetTemplateInfo
C_XMLUtil.GetTemplates
```

---

# PART V — EVENT CATALOG

The official README snapshot documents the following ClassicAPI-added or enhanced events.

## 73. Inventory / Equipment

```text
BAG_NEW_ITEMS_UPDATED
BAG_UPDATE_DELAYED
ITEM_DATA_LOAD_RESULT
PLAYER_EQUIPMENT_CHANGED
UPDATE_INVENTORY_DURABILITY
EQUIPMENT_SETS_CHANGED
EQUIPMENT_SWAP_PENDING
EQUIPMENT_SWAP_FINISHED
HEARTHSTONE_BOUND
WEAPON_SLOT_CHANGED
```

### `WEAPON_SLOT_CHANGED` event

- **Status:** `[UNVERIFIED - TEST FIRST]` Built and deployed upstream; not verified in-game.
- **Payload:** *(none)*
- **Semantics:** Fires when the item in weapon slot 16 (main hand), 17 (off hand), or 18 (ranged) changes (equip, unequip, swap).
- **Coalescing:** Coalesced on `WorldTick` to at most one fire per frame. A single action changing two weapon slots (e.g. equipping a 2H weapon replacing 1H + off-hand) fires the event once.
- **Relic Exemption:** Slot 18 is exempted for classes with a relic slot (Paladin, Shaman, Druid) via live check of `ChrClasses.dbc` (`OFF_CHRCLASSES_RELIC_SLOT`). Relic swaps never trigger the event.
- **System:** Filed under `PaperDollInfo` as a `UniqueEvent`. Prefer this over filtering `PLAYER_EQUIPMENT_CHANGED` in Lua across 19 slots when only weapon changes matter.

---

## 74. Combat / Swing Events

```text
PLAYER_SWING
PLAYER_SWING_RANGE_UPDATE
```

### `PLAYER_SWING` event

- **Status:** `[EMPIRICALLY VERIFIED]` for swing detection, extra attacks coalescing, cast-time resets, dual-wield, and melee range gating. `[UNVERIFIED - TEST FIRST]` for Turtle WoW Slam override.
- **Payload:** `swingDuration, swingType`
  - `swingDuration` (number): seconds from now until the next swing of this type.
  - `swingType` (`Enum.PlayerSwingType`): `0` (`MainHand`), `1` (`OffHand`), `2` (`Ranged`).
- **Semantics:**
  - Fires each time an attack timer resets: landed white hit (`SMSG_ATTACKERSTATEUPDATE`), on-next-swing ability replacement (Heroic Strike, Maul via `SPELL_ATTR_ON_NEXT_SWING`), non-triggered cast-time spell interrupt (`SPELL_INTERRUPT_FLAG_AUTOATTACK`), ranged autorepeat wind-up (`SMSG_SPELL_GO` with `SPELL_ATTR_EX2_AUTOREPEAT_FLAG` minus cast time), fresh melee attack-start (`SMSG_ATTACKSTART` off-hand, gated by melee range), weapon swaps in combat, and parry haste.
  - **Coalescing:** Coalesced on `WorldTick` to at most once per swing type per frame. Multiple hits at the exact same moment (e.g. Windfury, Sword Specialization) collapse into one event with the latest remaining time.
  - **Parry Haste:** Cuts delay to 20% of unhasted delay if remaining time was between 20% and 60%, or subtracts 40% if > 60%. Left alone if < 20%.
  - **Range Gating:** Does not fire on attack-start if declared while out of melee range; fires only once in reach.
  - **Turtle WoW Slam Override:** Registers 11 player-castable Slam ranks (`1464`, `8820`, `11430`, `11604`, `11605`, `45599`, `45960`, `45961`, `45963`, `45964`, `53214`) because Turtle WoW's server resets swing timers on Slam despite client `Spell.dbc` attributes.

### `PLAYER_SWING_RANGE_UPDATE` event

- **Status:** `[EMPIRICALLY VERIFIED]` for 2D melee range geometry and attack-start range gate.
- **Payload:** `swingType, isInRange, checksRange`
  - `swingType` (`Enum.PlayerSwingType`): `0` (`MainHand`), `1` (`OffHand`), `2` (`Ranged`).
  - `isInRange`: `1` when target is in range, `nil` when out of range (ignore if `checksRange` is `nil`).
  - `checksRange`: `1` when range check was possible, `nil` when not possible (no target, untargetable, no weapon).
- **Semantics:**
  - Fires on `WorldTick` when the current target enters or leaves range for a swing type enabled via `C_SwingTimer.EnableRangeCheck`.
  - **Melee Geometry:** Computes pure 2D distance (X/Y plane) via `Combat::Swing::InMeleeRange`, reading engine reach constants `VAR_MELEE_REACH_LEEWAY` and `VAR_MELEE_REACH_MIN` to match server reach rules and ignore terrain Z-axis elevation.
  - **Ranged Geometry:** Uses full 3D distance via `Spell::Range::PlayerVsUnit`.

---

## 75. Input / Cursor

```text
CURSOR_CHANGED
GLOBAL_MOUSE_DOWN
GLOBAL_MOUSE_UP
MODIFIER_STATE_CHANGED
PLAYER_STARTED_LOOKING
PLAYER_STOPPED_LOOKING
PLAYER_STARTED_MOVING
PLAYER_STOPPED_MOVING
PLAYER_STARTED_TURNING
PLAYER_STOPPED_TURNING
```

---

## 76. Faction / Quest

```text
FACTION_STANDING_CHANGED
QUEST_ACCEPTED
QUEST_DATA_LOAD_RESULT
QUEST_REMOVED
QUEST_TURNED_IN
```

---

## 77. Loot

```text
LOOT_HISTORY_ROLL_CHANGED
LOOT_HISTORY_ROLL_COMPLETE
LOOT_HISTORY_FULL_UPDATE
LOOT_SCAN_COMPLETED
```

---

## 78. Loss of Control

```text
LOSS_OF_CONTROL_ADDED
LOSS_OF_CONTROL_UPDATE
```

> **Event Diffing Behavior**: These events fire when the active set of loss-of-control
> effects changes. Re-locking an already-locked school (e.g. via an interrupt while
> already locked) extends `endMs` without firing either event. Do not rely on caching
> expiration time from event timestamps; query `C_LossOfControl.GetSchoolLockout()`
> directly when current status is needed.

---

## 79. Nameplate / Focus

```text
NAME_PLATE_CREATED
NAME_PLATE_UNIT_ADDED
NAME_PLATE_UNIT_REMOVED
PLAYER_FOCUS_CHANGED
```

---

## 80. Spellcast Events

```text
UNIT_SPELLCAST_SENT
UNIT_SPELLCAST_START
UNIT_SPELLCAST_STOP
UNIT_SPELLCAST_DELAYED
UNIT_SPELLCAST_SUCCEEDED
UNIT_SPELLCAST_INTERRUPTED
UNIT_SPELLCAST_FAILED
UNIT_SPELLCAST_FAILED_QUIET
UNIT_SPELLCAST_CHANNEL_START
UNIT_SPELLCAST_CHANNEL_UPDATE
UNIT_SPELLCAST_CHANNEL_STOP
UNIT_SPELLCAST_RETICLE_TARGET
UNIT_SPELLCAST_RETICLE_CLEAR
```

The official README snapshot documents payloads containing combinations of:

```text
unit
target
castGUID
spellID
spellName
rank
```

Use `/classicapi` for exact current payload order if implementation depends on it.

---

## 81. Misc Events

```text
LEARNED_SPELL_IN_SKILL_LINE
PLAYER_TOTEM_UPDATE
SOUNDKIT_FINISHED
UNIT_FACTION
UPDATE_MOUSEOVER_UNIT
UPDATE_SHAPESHIFT_FORM
USER_WAYPOINT_UPDATED
```

---

# PART VI — GLOBALS AND ENUMS

## 82. Version Globals

```lua
CLASSIC_API_VERSION
INTERFACE_VERSION
```

---

## 83. Expansion Constants

```text
LE_EXPANSION_LEVEL_CURRENT
LE_EXPANSION_CLASSIC
...
```

The official documentation includes later expansion enum constants for compatibility even though the runtime client remains 1.12.1.

---

## 84. Enums

Documented enum families include:

```text
Enum.AddOnSecurityStatus
Enum.PowerType
Enum.InventoryType
Enum.ItemClass
Enum.ItemQuality
Enum.PlayerSwingType
Enum.UICursorType
Enum.SpellBookSpellBank
Enum.SpellBookItemType
```

`Enum.PlayerSwingType`:
- `MainHand = 0`: Main-hand melee weapon.
- `OffHand = 1`: Off-hand melee weapon.
- `Ranged = 2`: Ranged weapon (bow, gun, crossbow, wand).

Use `/classicapi` for exact values when numeric identity matters.

---

# PART VII — GLUEXML / LOGIN-SCREEN API

## 85. Account Storage

GlueXML-only:

```lua
SaveAccount(name, password)
DeleteAccount(name)
GetSavedAccounts()
LoginWithSavedAccount(name)
```

The official documentation states that saved credentials use Windows Credential Manager / DPAPI, scoped per realmlist.

Plaintext password is not returned to Lua by `LoginWithSavedAccount`.

These APIs are not ordinary in-world addon APIs.

---

## 86. Character List

GlueXML-only:

```lua
GetSavedCharacterOrder(realm)
SetSavedCharacterOrder(realm, order)
```

---

## 87. Glue-State Mirrored Functions

The project documentation also mirrors selected helpers onto the glue Lua state, including:

```lua
GetCVar
SetCVar
RegisterCVar
GetCVarDefault
C_CVar.GetCVarBool

C_Glue.IsFirstLoadThisSession
C_Glue.IsOnGlueScreen

RunScript
IsLoggedIn
```

Keep GlueXML and in-world addon design separate.

---

# PART VIII — DEBUGGING / DEVELOPMENT

## 88. DebugTools Companion

The repository includes a DebugTools addon providing:

```text
/dump
/etrace
/framestack
/fstack
/luaerrors
/scripterrors
```

Useful globals include:

```lua
print(...)
setprinthandler(func)
getprinthandler()
tostringall(...)
```

---

## 89. Recommended Verification Workflow

For an uncertain ClassicAPI behavior:

1. Search this document.
2. Use `/classicapi`.
3. Use `/dump` to inspect a function result.
4. Use `/etrace` to verify events and payloads.
5. Inspect current `docs/API.md` or source only when needed.

Examples:

```text
/dump C_APIDocumentation.GetSystems()
/dump C_Item.GetItemInfoInstant(6948)
/dump C_UnitAuras.GetUnitAuras("target")
```

---

# PART IX — MODERNIZATION DECISION GUIDE

## 90. Replace Legacy Tooltip Aura Scanning

Prefer:

```lua
C_UnitAuras.*
AuraUtil.*
```

over:

```text
hidden GameTooltip scanning
localized aura text parsing
```

---

## 91. Replace Combat-Log String Castbars

Prefer:

```lua
C_Spell.UnitCastingInfo
C_Spell.UnitChannelInfo
UNIT_SPELLCAST_*
```

when they provide the needed source of truth.

---

## 92. Replace Fake Focus

Prefer:

```lua
FocusUnit
ClearFocus
focus
focustarget
```

---

## 93. Replace Nameplate WorldFrame Scraping

Prefer:

```lua
C_NamePlate.*
NAME_PLATE_*
nameplateN
```

---

## 94. Replace Manual Bag Sorting

Prefer:

```lua
C_Container.SortBags
C_Container.SortBankBags
BAG_UPDATE_DELAYED
```

when appropriate.

ClassicAPI v1.15.13 adds equipment-slot grouping to its existing native sorter.
Use it when that ordering meets the addon's requirements; consult
[the container contract](#equipment-slot-grouping-in-sortbags-v11513) for the exact
ordering, asynchronous behavior and bank/data constraints. `BAG_UPDATE_DELAYED`
can refresh the view but does not certify completion of a sort.

---

## 95. Replace Manual Item Metadata Scraping

Check:

```lua
C_Item.*
C_Container.*
```

before scraping item tooltips.

---

## 96. Replace Manual Timers

Check:

```lua
C_Timer.After
C_Timer.NewTimer
C_Timer.NewTicker
```

before implementing an `OnUpdate` timer queue.

---

## 97. Replace Home-Grown Spell Metadata Tables

Check:

```lua
C_Spell.*
C_SpellBook.*
```

before duplicating spell DBC metadata in Lua.

---

## 98. Replace Manual Range / Position Helpers

Check:

```lua
UnitInRange
UnitDistanceSquared
UnitPosition
UnitInLineOfSight
ClosestUnitPosition
```

before adding approximate range hacks.

Remember that UnitXP may still be preferable when the addon specifically needs UnitXP's separate telemetry semantics.

---

# PART X — IMPORTANT CAVEATS

## 99. ClassicAPI Is Not Retail

A Retail function name is not proof that ClassicAPI implements it.

Use only:
- this reference
- `/classicapi`
- official docs
- current source
- empirical verification

---

## 100. Bundled Lua Helpers vs DLL Functions

Some functionality comes from the embedded `!!!ClassicAPI` addon rather than a direct C++ Lua binding.

For addon authors this may be operationally transparent, but it matters when diagnosing load order or implementation details.

---

## 101. Hot-Path Choice Matters

Modern API does not automatically mean the table-returning form is the fastest form.

Example: `C_UnitAuras` provides both table-returning and positional APIs.

For high-frequency scanning, prefer the documented zero-allocation path where appropriate.

---

## 102. Do Not Preserve Obsolete Vanilla Workarounds by Default

When ClassicAPI provides an authoritative replacement, old compatibility mechanisms should normally be deleted rather than retained behind fallback branches in enhanced-client-only addons.

Examples:

```text
tooltip scanners
fake focus
combat-log regex castbars
Lua timer engines
manual nil wipes
manual item metadata parsers
WorldFrame nameplate scraping
```

Furthermore, if an addon intentionally declares a hard enhanced-client capability floor, do not preserve fallback branches whose only purpose is supporting runtimes below that floor, unless they serve another verified supported configuration. Addons that enforce a specific enhanced floor should consume its verified primitives directly without defensive fallback layers.

---

# PART XI — REFERENCE MAINTENANCE

## 103. Source Snapshot

This document was built from the official repository:

```text
brues-code/ClassicAPI
release: v1.15.13
commit:  fa7d71435feabde2c5a08e9175321ca614b6449a
branch:  master
```

Official source files used as primary reference:

```text
README.md (blob: db401f0578060c3aa52364d533bbced570235fea)
docs/API.md (blob: 23794ac2e8335aae7957d80f5ccecd4228ea34f0)
src/macro/ShowTooltip.cpp (blob: 24a8aa1158c5c93754b10e4d263c3dd6a90047e0)
src/table/Length.cpp (blob: 5c3f9dfdbedd34ae016caefd038e3003facf6b28)
src/cvar/Temp.cpp (blob: 3810691c26dc7e91ca2af75ad615c7e32945d58f)
src/container/SortBags.cpp (blob: b6d77b3b7bc6e8a9b2361fa4bfbcf1d2117acf7a)
src/nameplate/Events.cpp (blob: cebb4ac06c43f85dd907f74cd19b908bbd540897)
Earlier verified source knowledge retained (Swing.cpp, SwingRange.cpp, Equipment.cpp, Data.cpp, Custom.cpp, Offsets.h)
```

The v1.15.12 API reference blob was:

```text
0ab67379ec55e5e9ebe92595b40611cc5d482164
```

The v1.15.13 release adds:

- `C_CVar.SetTempCVar` and `C_CVar.RemoveTempCVar` (session-only CVar overrides without `Config.wtf` persistence)
- Baganator-style equipment slot grouping in `C_Container.SortBags()` and `C_Container.SortBankBags()`
- Nameplate announcement retries while prerequisites remain unmet (no new event payloads)

The complete three-commit `v1.15.12...v1.15.13` range, release/DLL provenance,
review corrections and runtime requirements are recorded in
[the v1.15.13 audit](docs/CLASSICAPI_1.15.13_AUDIT.md).
The [earlier audit](docs/CLASSICAPI_1.15.12_AUDIT.md) retains v1.15.10 through
v1.15.12 provenance; its macro and weak-table knowledge remains valid.

---

## 104. Refresh Protocol

When updating this master reference:

1. Fetch current `README.md`.
2. Fetch current `docs/API.md`.
3. Compare the API.md blob SHA with the snapshot above.
4. Review changed API sections.
5. Update:
   - namespace inventory
   - events
   - Lua compatibility behavior
   - macro behavior
   - modern client features
   - caveats
6. Do not copy unfinished TODO items into the active API catalog.
7. Increment the local document revision/date if your repository tracks revisions.

---

## 105. Authority Order for AI

When sources disagree:

1. current ClassicAPI source implementation
2. current `docs/API.md`
3. current ClassicAPI README
4. this local master reference
5. older VanillaForge/framework notes
6. general WoW/Retail knowledge

Never allow old framework notes to override newer ClassicAPI behavior.

---

# PART XII — QUICK LOOKUP

## 106. Most Important Modernization APIs

For general addon modernization, check these first:

```text
C_Timer
C_UnitAuras
AuraUtil
C_Spell
C_SpellBook
C_Item
C_Container
C_NamePlate
C_Map
C_Texture
C_Macro
C_LossOfControl
C_EquipmentSet
C_Reputation
C_SwingTimer
C_AddOns
C_APIDocumentation
```

Important globals:

```text
FocusUnit
ClearFocus
UnitGUID
UnitTokenFromGUID
UnitTokenFromName
UnitPosition
UnitDistanceSquared
UnitInLineOfSight
hooksecurefunc
InCombatLockdown
table.wipe
GetServerTime
```

Important modern events:

```text
UNIT_SPELLCAST_*
NAME_PLATE_*
PLAYER_FOCUS_CHANGED
PLAYER_SWING
PLAYER_SWING_RANGE_UPDATE
WEAPON_SLOT_CHANGED
BAG_UPDATE_DELAYED
LOSS_OF_CONTROL_*
ITEM_DATA_LOAD_RESULT
QUEST_DATA_LOAD_RESULT
SOUNDKIT_FINISHED
```

Important developer tools:

```text
/classicapi
/dump
/etrace
/framestack
/luaerrors
```

---

## 107. Final Rule

Before writing a workaround for a limitation commonly associated with stock WoW 1.12.1, search this reference.

ClassicAPI exists specifically to make many of those limitations obsolete.
