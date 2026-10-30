# ClassicAPI Master Reference for WoW 1.12.1

> Local AI knowledge base for ClassicAPI.
>
> Purpose: let coding assistants design and modernize WoW 1.12.1 addons against ClassicAPI without needing to browse GitHub for ordinary API discovery.
>
> Source basis: `brues-code/ClassicAPI`, default branch `master`, official `README.md`, official `docs/API.md`, and selected implementation/source references.
>
> Pinned version: `classicapi.reference_version` in [UPSTREAM_VERSIONS.json](UPSTREAM_VERSIONS.json), always the latest release; VanillaForge supports nothing older. Release notes by version: [v1.17.0 to v1.17.3](#v1170-to-v1173-api-and-behavior-contracts), [v1.17.4 to v1.17.8](#v1174-to-v1178-api-and-behavior-contracts), [v1.17.9 to v1.17.10](#v1179-to-v11710-api-and-behavior-contracts), [v1.17.11](#v11711-api-and-behavior-contracts) and [v1.17.12 to v1.18.5](#v11712-to-v1185-api-and-behavior-contracts).
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
v1.17.11 -> 11711
v1.18.5 -> 11805
```

Older stamps, for reading old code:

```text
v1.15.8 -> 11508
v1.15.9 -> 11509
v1.15.10 -> 11510
v1.15.11 -> 11511
v1.15.12 -> 11512
v1.15.13 -> 11513
v1.15.14 -> 11514
v1.15.15 -> 11515
v1.15.16 -> 11516
v1.16.0 -> 11600
v1.17.0 -> 11700
v1.17.3 -> 11703
v1.17.4 -> 11704
v1.17.5 -> 11705
v1.17.6 -> 11706
v1.17.7 -> 11707
v1.17.8 -> 11708
v1.17.9 -> 11709
v1.17.10 -> 11710
v1.17.11 -> 11711
v1.17.12 -> 11712
v1.17.13 -> 11713
v1.18.0 -> 11800
v1.18.5 -> 11805
```

The VanillaForge support baseline is the latest release, pinned in
`UPSTREAM_VERSIONS.json`. No other file names it.

Do not assume a future version's new API exists solely because a similarly named Retail API exists.

[SOURCE-VERIFIED] `CLASSIC_API_VERSION` identifies a build's version stamp, not
the complete loaded DLL stack. The pinned [version publisher](https://github.com/brues-code/ClassicAPI/blob/99de63755bdc368cf8d35ce3a09dc46dafc20930/src/api/Version.cpp)
sets this global at startup and on `/reload`. Unstamped developer builds use
`99999999` so minimum-version comparisons pass; see the pinned
[build configuration](https://github.com/brues-code/ClassicAPI/blob/99de63755bdc368cf8d35ce3a09dc46dafc20930/CMakeLists.txt).
That sentinel does not prove a published release or all capabilities of any
later stable version. Record artifact/source identity separately, and verify
the consumed API and its behavior on the loaded target.

Versions live in one place. Only `UPSTREAM_VERSIONS.json` names a DLL
version. Addons check that ClassicAPI is loaded
(`type(CLASSIC_API_VERSION) == "number"`), never a number, and their TOC,
README and file headers say "ClassicAPI" without one (since 2026-10-30;
the player always runs the latest release). A comment may say when a
feature arrived ("UNIT_AURA_DELTA (1.17.10)"): that stays true. A new
release is taken with `python -B tools/upgrade_dll.py`, which shows what
changed, pins it, and lists the leads in every addon; the hole finder
reports any addon that names a version again.

ClassicAPI is one required component of VanillaForge's full enhanced environment;
its version global does not establish that SuperWoW, NamPower and UnitXP SP3 are
loaded. See [the engine stack](ENGINE_REFERENCE.md#3-stack-architecture) for
environment requirements and provider selection.

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

[SOURCE-VERIFIED] The toggle is global and can be disabled after startup.
Record `GetModernScriptArgs()` when verifying the target client; a sufficient
`CLASSIC_API_VERSION` alone does not establish its current value. When the
toggle is off, native zero-argument dispatch is restored. Inspect the active
setting and the actual registration/call path before adopting positional
handlers, and account for the effect on other addons before changing it.
See the pinned [script-argument contract](https://github.com/brues-code/ClassicAPI/blob/7ccbbaaf68bcde6b29b71806981d0338e0577189/docs/API.md#setmodernscriptargsenable--getmodernscriptargs).
Since 1.17.9, frame methods work as handlers, clicks get `down`, enter and
leave get `motion`, and `event` is restored per handler; see
[Script handler arguments (1.17.9)](#script-handler-arguments-1179).

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
[the release-range audit](archive/docs/CLASSICAPI_1.15.12_AUDIT.md).

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

[SOURCE-VERIFIED] The pinned [TOC selector](https://github.com/brues-code/ClassicAPI/blob/7ccbbaaf68bcde6b29b71806981d0338e0577189/src/addons/FlavorToc.cpp)
tries `<Name>_Turtle.toc` only when its own Turtle detector is active, then
`<Name>_ClassicAPI.toc`, then `<Name>.toc`. It deliberately does not select
`_Vanilla`, `_Classic`, `_Mainline` or other later-client flavors. Do not infer
the active flavor from server ancestry; inspect the actual target and selected
manifest. The linter's directory audit checks target Interface metadata for
the base, `_ClassicAPI` and `_Turtle` candidates without simulating runtime
selection. An explicit TOC-file audit validates that selected file against
Interface 11200.

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

A physical `Interface/AddOns/!!!ClassicAPI/` copy overrides the embedded files only
when it holds an empty `.classicapi-dev` file or has a newer `## Version:` (1.18.0+).
The player installs only the DLL; there is no addon folder to copy.

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

Plate alpha follows vanilla rules, not the 1.17 inherited-alpha model; see
[Nameplate alpha (1.17.8)](#nameplate-alpha-1178).

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

[SOURCE-VERIFIED] Since 1.17.9 a `GameTooltipTemplate` tooltip has no line limit
(1.17.0 to 1.17.8: a fixed 60). It keeps the stock 30 line pairs and, when an
added line takes the last pair, builds the next `TextLeftN` / `TextRightN`, so
one spare pair always exists. Do not assume `TextLeftN` exists beyond
`NumLines() + 1`, and do not create lines yourself.

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
macro change in v1.15.12; see the [full audit](archive/docs/CLASSICAPI_1.15.12_AUDIT.md)
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
GetCurrentChatEvent   -- 1.17.3
```

Since 1.17.0 every `CHAT_MSG_*` event also carries `arg11` (lineID) and `arg12`
(sender GUID). See [v1.17 chat](#chat-arguments-and-getcurrentchatevent).

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
C_EquipmentSet.PickupEquipmentSet
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
GameTooltip:GetUnit
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
IsDualWielding
OffhandHasWeapon
```

`OffhandHasWeapon()` returns `1` / `nil` (engine) and `IsDualWielding()` `true` /
`false` (1.17.10); see [Small changes (1.17.10)](#small-changes-11710).

This namespace should be checked before implementing tooltip-based item metadata extraction.

[SOURCE-VERIFIED] The pinned [v1.15.16 API reference](https://github.com/brues-code/ClassicAPI/blob/7ccbbaaf68bcde6b29b71806981d0338e0577189/docs/API.md)
documents `GetLootRollItemID(rollID)` as reading the engine's active roll list,
using the same item ID as `GetLootRollItemLink` without parsing a string. It can
return nil when no matching roll exists. Prefer a verified direct ID accessor
for exact content rules; it identifies the active item but does not supply or
validate a server-specific item catalog. Verify names and content rules separately.

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
- Before v1.15.14, an unmodified icon loader with no loose disk icons listed only `Ability_*`/`Spell_*` icons. The previously recorded count of 746 is a historical example, not a portable count or a current baseline invariant. v1.15.14 explicitly adds the question mark as described below.
- Putting custom `INV_*.blp` files directly into `Interface\Icons\` allows them to enter the engine's list via pass 3 after restarting the client.
- The ~5,226 `INV_*` icons shipped inside MPQs are rejected by pass 1 prefix filtering. ClassicAPI hooks all three enumeration callbacks at their entry point, capturing these archive item icons into a separate list for `GetMacroItemIcons`.
- `GetMacroIconInfo(index)` returns `""` (empty string) rather than `nil` when queried with an out-of-bounds index.
- Call `GetNumMacroIcons()` before iterating `GetMacroIconInfo(index)`; do not assume the latter initializes the list. The four ClassicAPI append-to-table enumerators above also call `EnsureLoaded()` when the engine count is zero. This loading behavior predates v1.15.14.

### Question-mark icon availability (v1.15.14+)

[SOURCE-VERIFIED] On initial loading of an empty engine icon list, ClassicAPI
seeds `INV_Misc_QuestionMark`, lets the original loader sort and deduplicate,
then moves the question mark to internal index 0 (Lua `GetMacroIconInfo(1)`).
This makes the `?` selectable in the native macro picker without an additional
icon-injection workaround. It enables the existing `#showtooltip` / `#show`
dynamic-icon rule; it does not make explicitly selected non-question-mark icons
dynamic. `GetMacroInfo` still reports the stored choice, while
`C_Macro.GetMacroIcon` reports the currently displayed icon.

The synthetic seed bypasses the capture hook, so it is not falsely classified
as a loose disk icon. The four append-to-table enumerators keep their existing
source/category contracts; first-entry behavior applies to the engine list,
not to each of those four tables. Other MPQ `INV_*` icons still require the
item enumerator. Existing copies of the question mark are intended to collapse
through the engine's adjacent deduplication.

Engineering implication: counts and numeric icon positions can change with this
release or client assets. Resolve against the current enumeration rather than
persisting an index as cross-version icon identity. The existing out-of-bounds
empty-string rule remains valid (KP-54). There are no new Lua functions or events.

Evidence: [pinned icon-loader source](https://github.com/brues-code/ClassicAPI/blob/7707127d5f1293ed9f1c15bd1e13e4b37254bf3d/src/macro/Icons.cpp)
and [display-icon rule](https://github.com/brues-code/ClassicAPI/blob/7707127d5f1293ed9f1c15bd1e13e4b37254bf3d/src/macro/IconPath.cpp).
[UNVERIFIED - TEST FIRST] Picker display, duplicate suppression with custom assets
and hook coexistence require client testing; this is not a local empirical claim
or an unconditional guarantee across every patched client.

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

### Shared unit APIs in the full DLL stack

[SOURCE-VERIFIED] ClassicAPI's `UnitGUID(unit)` returns a 64-bit hexadecimal
string such as `"0xF13000059A002553"`, rather than a later client's prefixed
GUID format. GUID input and GUID output are different contracts. Its
[token resolver](https://github.com/brues-code/ClassicAPI/blob/7ccbbaaf68bcde6b29b71806981d0338e0577189/src/unit/TokenExtensions.cpp)
adds raw `0x...` GUID input only when `SuperWoWhook.dll` is absent; when that
module is loaded, it defers GUID parsing to SuperWoW. Thus GUID-aware `UnitX`
calls do not prove which DLL is loaded. Retain the required environment stack
and verify component-specific runtime evidence separately.

[SOURCE-VERIFIED] ClassicAPI's `UnitPosition(unit)` returns
`posY, posX, posZ, instanceID`: west, north, height and the current `Map.dbc`
ID. It reads visible units without a party/raid restriction and returns nil
when a recognized unit has no known position. Invalid unit tokens can error.
The pinned [API contract](https://github.com/brues-code/ClassicAPI/blob/7ccbbaaf68bcde6b29b71806981d0338e0577189/docs/API.md#unitpositionunit)
explicitly warns that SuperWoW registers a global `UnitPosition` with a
different return shape: the last registrant wins. Do not unpack the global
using ClassicAPI's documented shape solely because ClassicAPI is present.
Verify the live shape on the actual combined stack before using its coordinates.
The pinned [implementation](https://github.com/brues-code/ClassicAPI/blob/7ccbbaaf68bcde6b29b71806981d0338e0577189/src/unit/Position.cpp)
also registers `C_PlayerInfo.UnitPosition`; that alias does not establish the
shape or ownership of the global function. [UNVERIFIED - TEST FIRST] for the
active OctoWoW client's registration order and runtime results.

---

## 70. Unit Auras — `C_UnitAuras`

This is a major modernization API.

Table/data access:

```lua
C_UnitAuras.GetAuraDataByIndex
C_UnitAuras.GetAuraDataByAuraInstanceID
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
- Since 1.17.0 the order is sorted, not slot order: see [v1.17 auras](#auras).
- Since 1.17.10 `AuraData.auraInstanceID` is a stable identity for one
  application; key caches by it. See
  [`UNIT_AURA_DELTA`](#aura-instance-ids-and-unit_aura_delta-11710).

### Aura Presence, Timing and Refresh

[SOURCE-VERIFIED] In [v1.15.15 aura data enrichment](https://github.com/brues-code/ClassicAPI/blob/71805db62f1e8a154477033dc1f50960c535af8b/src/aura/Data.cpp),
remote-unit timing depends on observed application/cast state. A missing or
elapsed cached expiration can yield `expirationTime == 0` while the aura is
still reported. Zero means no known expiration, not proof of removal or a
permanent aura. Retain the reported icon without inventing a duration.

[SOURCE-VERIFIED] [Observed reapplications](https://github.com/brues-code/ClassicAPI/blob/71805db62f1e8a154477033dc1f50960c535af8b/src/aura/Source.cpp)
can refresh cached timing and signal `UNIT_AURA` even when the spell/slot is
unchanged. Refresh from the API on the relevant unit event; resolve unit aliases
with `UnitIsUnit()` where appropriate. Change the cooldown when timing changes,
but leave an unchanged sweep running. See `ENGINE_REFERENCE.md` §12.10.

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
  - **Only while attacking (1.17.0):** a cast reset fires the event only while auto-attack is on. A buff cast out of melee no longer reports a swing.
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

### Modifier event state ordering

[SOURCE-VERIFIED] At the v1.15.15 reference commit, `MODIFIER_STATE_CHANGED`
provides `key, down` (`LSHIFT`, `RSHIFT`, `LCTRL`, `RCTRL`, `LALT`, `RALT`;
numeric 1/0). ClassicAPI updates its modifier bitmap before firing the event
from a thread message hook, before the engine dispatches that key message.
The left/right modifier queries read this updated bitmap.

For a combined shortcut inside this event, use
`IsLeftShiftKeyDown() or IsRightShiftKeyDown()` and
`IsLeftControlKeyDown() or IsRightControlKeyDown()` as needed. Native merged
`IsShiftKeyDown()` / `IsControlKeyDown()` read a different state path and must
not be assumed current at this event boundary. Re-query both sides on each
transition; releasing one side must not relock while the other remains held.
Focus regain also reconciles the bitmap and emits changed transitions.

Source: [Modifier.cpp](https://github.com/brues-code/ClassicAPI/blob/71805db62f1e8a154477033dc1f50960c535af8b/src/input/Modifier.cpp)
(blob `7071459ca029f220881208df1d3cec10c0b3849f`). This is source verification;
specific keyboard/focus behavior still requires in-client testing.

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
UNIT_SPELLCAST_INTERRUPTIBLE       -- 1.17.0, target and focus only
UNIT_SPELLCAST_NOT_INTERRUPTIBLE   -- 1.17.0, target and focus only
```

1.17.0 changed when `FAILED` and `INTERRUPTED` fire; see
[v1.17 spellcast](#spellcast-events).

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

## 88. Debug Tools

From 1.18.0 the DLL embeds the debug tools as `ClassicAPI_DebugTools`, a hidden,
always-enabled addon that loads the first time one of its commands runs. Nothing
is installed and nothing loads until then, so in-game checks may use them:

```text
/dump <expr>      a value, tables and all returns
/etrace           event trace window
/fstack           frames under the cursor (1.18.0: highlight, anchors, source file)
/tinspect <expr>  table inspector
/luaerrors
```

`!ErrorLog` (`/err`, `/lag`) stays the tool for errors and frame time.

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
3. Print a function result with `/run print(...)`.
4. Verify events and payloads with a small `/run` frame that prints `event, arg1, ...`.
5. Inspect current `docs/API.md` or source only when needed.

Examples:

```text
/run print(C_Item.GetItemInfoInstant(6948))
/run print(C_UnitAuras.UnitAura("target", 1))
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

For hits, misses, heals, aura changes, interrupts, dispels and deaths, prefer
`COMBAT_LOG_EVENT_UNFILTERED` (1.17.0) or the NamPower spell events over
parsing `CHAT_MSG_COMBAT_*` / `CHAT_MSG_SPELL_*` text. See
[v1.17 combat log](#combat-log).

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
release: v1.17.11 (tag commit 317539dbd8aa9e9cd7a23441c0e355bb85c7e2ab)
commit:  317539dbd8aa9e9cd7a23441c0e355bb85c7e2ab
branch:  master
```

Official source files used as primary reference (v1.17.11):

```text
README.md (blob: 0e9caaa69eab05385d058b8404768b9bb33c33a8)
docs/API.md (blob: fb0bfad60bb898eca5e862df8f85b104f2dbcd84)
commit messages v1.17.8...v1.17.11 (behaviour API.md leaves out)
src/frame/Alpha.cpp (at abd5367, the nameplate alpha rules)
```

Source files read for earlier snapshots (v1.15.16, commit 7ccbbaaf):

```text
src/macro/Icons.cpp (blob: 5ad755eaf93c13bc4fea5e353f6ea40fea23e964)
src/macro/IconPath.cpp (blob: 40cd511660c76ec48ec8e22c96fad58c5cf1e7c2)
src/Offsets.h (blob: 9e10fb5f691d18aa23c1e1e90756da84042a08e9)
src/macro/ShowTooltip.cpp (blob: 24a8aa1158c5c93754b10e4d263c3dd6a90047e0)
src/table/Length.cpp (blob: 5c3f9dfdbedd34ae016caefd038e3003facf6b28)
src/cvar/Temp.cpp (blob: 3810691c26dc7e91ca2af75ad615c7e32945d58f)
src/container/SortBags.cpp (blob: b6d77b3b7bc6e8a9b2361fa4bfbcf1d2117acf7a)
src/nameplate/Events.cpp (blob: cebb4ac06c43f85dd907f74cd19b908bbd540897)
src/api/Version.cpp (blob: 33c3ea05a268203cc96c0056557a497a141843a1)
CMakeLists.txt (blob: 830adb8a01e930faa3016184faface04b67b8ff6)
src/unit/TokenExtensions.cpp (blob: 1bb9fa98dc16defa0e8a8c75d8ef96225b87b61f)
src/unit/Position.cpp (blob: 156568032d2a419a7d3fedc006b3d7651bc9d975)
Earlier verified source knowledge retained (Swing.cpp, SwingRange.cpp, Equipment.cpp, Data.cpp, Custom.cpp, Offsets.h)
```

The v1.15.12 API reference blob was:

```text
0ab67379ec55e5e9ebe92595b40611cc5d482164
```

The v1.15.14 release makes the question-mark icon the first engine macro icon
and selectable without a separate icon-injection workaround. No API signatures,
event payloads, bag sorting or Lua table semantics change in this release. See
[the v1.15.14 audit](archive/docs/CLASSICAPI_1.15.14_AUDIT.md) for the full one-commit range,
independently verified provenance and runtime requirements.

The v1.15.13 release added:

- `C_CVar.SetTempCVar` and `C_CVar.RemoveTempCVar` (session-only CVar overrides without `Config.wtf` persistence)
- Baganator-style equipment slot grouping in `C_Container.SortBags()` and `C_Container.SortBankBags()`
- Nameplate announcement retries while prerequisites remain unmet (no new event payloads)

The complete three-commit `v1.15.12...v1.15.13` range, release/DLL provenance,
review corrections and runtime requirements are recorded in
[the v1.15.13 audit](archive/docs/CLASSICAPI_1.15.13_AUDIT.md).
The [earlier audit](archive/docs/CLASSICAPI_1.15.12_AUDIT.md) retains v1.15.10 through
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
CombatLogGetCurrentEventInfo
CreateFrame("Cooldown")
region:CreateAnimationGroup
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
COMBAT_LOG_EVENT_UNFILTERED
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
/run print(...)
/err, /lag   (!ErrorLog)
```

---

## 107. Final Rule

Before writing a workaround for a limitation commonly associated with stock WoW 1.12.1, search this reference.

ClassicAPI exists specifically to make many of those limitations obsolete.


## v1.15.15 source-verified addon contracts
[SOURCE-VERIFIED] GameTooltip:GetUnit() returns (name, unitToken) or nothing when no unit is shown. SetUnit retains its input token; world hover uses mouseover; unit-attribute frames retain their token, including offline/far group members. Binding exists before OnTooltipSetUnit. GetUnitGUID remains (name, guid) and now resolves roster/name-cache names without a live object. Same-GUID world hover while an existing SetUnit tooltip stays visible can retain the earlier token. Tokens are mutable; use GUID identity for retained references.

[SOURCE-VERIFIED] C_EquipmentSet.PickupEquipmentSet(setID) puts a native set on the cursor; unknown IDs do nothing. GetCursorInfo and GetActionInfo return "equipmentset", setName; the second value is a name, not a numeric ID. CURSOR_CHANGED reports Enum.UICursorType.EquipmentSet. Action clicks fire WEAR_EQUIPMENT_SET(setID); the event alone does not equip. The bundled EquipmentManager checks item locks and casting, then calls UseEquipmentSet. Do not add duplicate equip handlers.

Set action placements persist in the per-character native equipment-set file, not addon SavedVariables or server action type. Rename/save repaint buttons; deleting a set clears its buttons. Native sets do not automatically import addon outfit schemas. Item/spell trackers must classify type before inferring identity from icons.
[UNVERIFIED - TEST FIRST] Verify tooltip tokens/events for live/offline roster units and action pickup/place/swap/use/delete/relogin. No local runtime verification is claimed. See [v1.15.15 audit](archive/docs/CLASSICAPI_1.15.15_AUDIT.md).

## v1.15.16 source-verified addon contracts
[SOURCE-VERIFIED] Compatibility-only release; no new public Lua API symbols, events, or return signature changes. Bundled `!!!ClassicAPI` compatibility module `AddOns/!!!ClassicAPI/Util/AddOnCompat.lua` intercepts `Turtle_GroupUI` via `EventUtil.ContinueOnAddOnLoaded` and wraps the global `GroupFrame_ToggleMovement(state)` function. Under modern script dispatch, frame buttons pass the widget (`self`) as the first argument to `OnClick`; this wrapper sanitizes any non-numeric `state` argument to `nil` before calling the original function, preventing an arithmetic error (`1 - state` at `Turtle_GroupUI.lua:409`). See [v1.15.16 audit](archive/docs/CLASSICAPI_1.15.16_AUDIT.md).

## v1.16.0 source-verified API and behavior contracts
[SOURCE-VERIFIED] The pinned [v1.16.0 API reference](https://github.com/brues-code/ClassicAPI/blob/99de63755bdc368cf8d35ce3a09dc46dafc20930/docs/API.md) documents `C_QuestLog.GetInfo(index)` as a row-info table which does not contain completion state. `C_QuestLog.GetQuestLogTitle(index)` returns a modern row tuple; `isComplete` is `1` for complete, `-1` for failed, and `nil` otherwise. Its third value is `suggestedGroup` (always `0` here), unlike the legacy global `GetQuestLogTitle` third-value quest tag.

[SUPERSEDED in 1.17] In 1.16.0, `CreateFrame("Cooldown", ...)` was a Model, `SetReverse` / `SetDrawEdge` changed nothing and XML could not create it. 1.17.0 and 1.17.1 changed all three; see [v1.17 Cooldown](#native-cooldown-frame-1171).

[SOURCE-VERIFIED] `GameTooltip:AddTexture` inserts an icon only on an eligible line and returns success/failure. `HookScript` forwards the same script arguments to both handlers; `hooksecurefunc` runs its callback after the original, forwards arguments, and preserves original return values. Macro APIs accept names as well as indexes. For an unknown name, `GetMacroInfo` returns nils, `PickupMacro` / `DeleteMacro` do nothing, and `EditMacro` changes no macro and returns the first empty slot or 0. `string.trim` and `string.join` are also documented.

This release adds 4.3.4-era API coverage plus behavior fixes across frames, tooltips, hooks, XML, nameplate/unit events, quest-log behavior and Lua compatibility. See the [v1.16.0 audit](archive/docs/CLASSICAPI_1.16.0_AUDIT.md) for upstream provenance, deployment evidence and portfolio displacement candidates. In-game behavior remains unverified locally.

## v1.17.0 to v1.17.3 API and behavior contracts

[SOURCE-VERIFIED] From the pinned
[v1.17.3 API reference](https://github.com/brues-code/ClassicAPI/blob/b5aed30a5db5ef033dd9a6619d8f74310787c4c9/docs/API.md)
and the `v1.16.0...v1.17.3` commit messages. Grep `.private/upstream/classicapi/docs/API.md`
for full payloads. 1.17.1 to 1.17.3 are small: native Cooldown drawing (1.17.1),
the AddOn Options button (1.17.2), tooltip spell IDs, gossip POI and
`GetCurrentChatEvent` (1.17.3). [UNVERIFIED - TEST FIRST] Nothing here has been
checked in game on OctoWoW yet.

### Combat log

`COMBAT_LOG_EVENT_UNFILTERED` fires once per combat event the client receives
(the area near you). `COMBAT_LOG_EVENT` fires only for events that pass the
combat log filter. The `CHAT_MSG_COMBAT_*` / `CHAT_MSG_SPELL_*` text lines
still fire unchanged.

- Values 1 to 11, the same for every subevent: `timestamp` (Unix seconds with
  milliseconds), `subevent`, `hideCaster`, `sourceGUID`, `sourceName`,
  `sourceFlags`, `sourceRaidFlags`, `destGUID`, `destName`, `destFlags`,
  `destRaidFlags`. Then a prefix: none for `SWING_`, `UNIT_` and `PARTY_KILL`;
  `environmentalType` for `ENVIRONMENTAL_`; and `spellId, spellName, spellSchool`
  for `SPELL_`, `SPELL_PERIODIC_`, `RANGE_`, `DAMAGE_SHIELD` and `DAMAGE_SPLIT`.
  Then a suffix: for example, `_DAMAGE` gives
  `amount, overkill, school, resisted, blocked, absorbed, critical, glancing, crushing, isOffHand`
  and `_MISSED` gives `missType, isOffHand[, amountMissed]`.
- Read the values from the handler's `arg1`... globals (`arg1` = timestamp,
  `arg2` = subevent) or from `CombatLogGetCurrentEventInfo()`, which returns
  values only while the handler runs.
- `missType`: `MISS`, `RESIST`, `DODGE`, `PARRY`, `BLOCK`, `EVADE`, `IMMUNE`,
  `DEFLECT`, `ABSORB` or `REFLECT`. `critical`, `glancing`, `crushing` and
  `isOffHand` are `1` or `nil`. `resisted`, `blocked` and `absorbed` are `nil`
  when 0. Heal `absorbed` is always 0.
- Not provided: `ENCHANT_APPLIED`, `ENCHANT_REMOVED`, and the `MAINTANK` /
  `MAINASSIST` flag bits. `SPELL_CAST_FAILED` is for your own casts only.
  `SPELL_CAST_START` has no target, and a spell with a cast time gets no
  `SPELL_CAST_SUCCESS`. Dose `amount` is the stack count after the change.
- Before 1.17.10: `overkill` and `overhealing` are always 0;
  `SPELL_AURA_REFRESH`, `SPELL_SUMMON` and `SPELL_CREATE` do not fire;
  `DAMAGE_SHIELD`, `SPELL_DISPEL` and `SPELL_DISPEL_FAILED` have `spellId` 0;
  `SPELL_INSTAKILL` has no source. From 1.17.10 see
  [Combat log additions](#combat-log-additions-11710).
- Some servers send no `SPELL_INTERRUPT` for an interrupt that also deals
  damage (Pummel, Kick, Earth Shock). [UNVERIFIED - TEST FIRST] on OctoWoW.
- Flags are `COMBATLOG_OBJECT_*` globals (each group has a `_MASK`).
  `CombatLog_Object_IsA(flags, COMBATLOG_FILTER_ME)` tests them. For "is it me?"
  in a hot path, comparing `sourceGUID` with a cached `UnitGUID("player")` is
  cheaper.
- **Shared state hazard:** `CombatLogAddFilter` / `CombatLogResetFilter` and the
  kept entries (`CombatLogSetRetentionTime`, `CombatLogClearEntries`) are global
  to the client and persist across `/reload`. An addon must not change them.
  Register `COMBAT_LOG_EVENT_UNFILTERED` and filter in Lua.
- **Hot path:** it fires for every nearby hit. Register it only while a feature
  needs it. Test the subevent and GUID first and return early. Do not build
  tables or concatenate strings per event.
- Provider choice: NamPower's spell events (`SPELL_DAMAGE_EVENT_*`,
  `AURA_CAST_*`, `BUFF_ADDED_*`...) already give IDs for spells and auras. The
  combat log adds swing and ranged misses (`missType`), environmental damage,
  damage shields, dispels, interrupts and deaths in one stream. Pick by what the
  feature needs and by cost.

### Native Cooldown frame (1.17.1)

`CreateFrame("Cooldown", name, parent, "CooldownFrameTemplate")` is a native
CSimpleFrame that draws its own sweep, flash and edge. `SetCooldown(start, duration)`
takes seconds (`GetTime()` base). `SetReverse` and `SetDrawEdge` now render.
`drawEdge` applies from the next `SetCooldown`. XML `<Cooldown reverse= drawEdge=>`
works. `CooldownFrame_SetTimer(cd, start, duration, enable)` calls
`SetCooldown`, or hides the frame when a value is not above 0.
`CooldownFrameTemplate` makes the frame fill its parent and start hidden. A new
frame that is shown before `SetCooldown` hides itself after one second.
The later clients' methods arrived in 1.17.9: see
[Cooldown API (1.17.9)](#cooldown-api-1179).

**Displacement:** `CreateFrame("Model", ..., "CooldownFrameTemplate")` and XML
`<Model inherits="CooldownFrameTemplate">` are still the old 1.12 Model sweep,
with a Model's per-frame cost. Change the frame type to `Cooldown` and keep
the calls. Model-only methods (`SetModel`, `SetSequenceTime`...) do not exist on
a Cooldown.

### Animation

`region:CreateAnimationGroup([name [, template]])` on frames, textures and font
strings, and `<Animations>` in XML. Animation types: `Alpha`, `Translation`,
`Scale`, `Rotation`, `Path` (with `ControlPoint`). A group has `Play([reverse])`,
`Stop`, `Finish`, `SetLooping("NONE"|"REPEAT"|"BOUNCE")` and the scripts
`OnPlay`, `OnStop`, `OnFinished(self, requested)`, `OnLoop` and `OnUpdate`.
Animations with the same order play together. A group updates once per frame,
after its frame's `OnUpdate`, and does not advance while the frame is hidden.
After the end, progress returns to 0 and `IsDone` is false; use `OnFinished`.
`SetMaxAnimFramerate` caps the update rate. Use this instead of Lua `OnUpdate`
for fades, slides, pulses and spins.

### Interface Options

`InterfaceOptions_AddCategory(panel)` (with `panel.name`, and optionally `parent`,
`okay`, `cancel`, `default`, `refresh`) and
`InterfaceOptionsFrame_OpenToCategory(panelOrName)`. The window opens from the
**AddOn Options** button in the game menu. Okay and Cancel call every panel's
`okay` / `cancel`, and Escape counts as Cancel. ClassicAPI lists its own
settings there (soft targeting, cast settings, player cache).

### Spellcast events

- `INTERRUPTED` vs `FAILED` now follows the failure reason. Only
  `SPELL_FAILED_INTERRUPTED` / `_COMBAT` give `INTERRUPTED`. Line of sight,
  a dead target at the end of the cast, and casting while moving give `FAILED`.
  A failed in-flight cast reports that cast's GUID, then `STOP`.
- `UNIT_SPELLCAST_INTERRUPTIBLE` / `_NOT_INTERRUPTIBLE` (`unit`) fire only for
  `target` and `focus`, when the interruptible state flips mid-cast. Read the
  starting value from `C_Spell.UnitCastingInfo` / `UnitChannelInfo` at `START`.
- Channels flagged to hide the channel bar fire no channel events.

### Auras

- C_UnitAuras walks a unit's auras in 4.3.4's sorted order: first auras that
  the player (or a unit the player owns) cast, then auras the player could
  apply, then the rest. Each group is in slot order. Every index and slot walk
  (`UnitAura`, `GetAuraSlots`, by-ID and by-name lookups,
  `GameTooltip:SetUnitAura`) uses it, so their indices agree. **Never pass a
  C_UnitAuras index to stock `UnitBuff` / `UnitDebuff` / `GetPlayerBuff` /
  `CancelPlayerBuff`**, which still count in slot order.
- New filters: `RAID`, `CANCELABLE`, `NOT_CANCELABLE`. Filter tokens ignore
  case. `PLAYER` also counts totems, guardians and charmed units that the
  player owns.
- Position 8 `isStealable` is now real. Position 13 `castByPlayer` is the player
  only; pets no longer count (`isFromPlayerOrPlayerPet` in AuraData keeps them).
- `duration` and `expirationTime` are both set or both `0`. A permanent player
  aura no longer reports a stale expiry left in its slot.

### Chat arguments and GetCurrentChatEvent

Every `CHAT_MSG_*` event has `arg11` = lineID (the same for every frame;
`0` for `CHAT_MSG_TEXT_EMOTE`) and `arg12` = the sender GUID. The GUID is `""`
for non-players, system messages and GMs. Use lineID to act once per line.
`GetCurrentChatEvent()` (1.17.3) returns the event name and `arg1` to `arg12`
of the chat event that is running, even when another hook changed the
globals. It returns nothing outside a chat event.

### Changed returns and behavior

- `GameTooltip:SetHyperlinkCompareItem` returns `1` or `nil`, no longer a slot
  count. Stat deltas show only when a comparison tooltip is passed.
- `GameTooltip:SetSpellByID` / `AddSpellByID(spellID [, isPet [, showSubtext]])`
  (1.17.3): the rank is hidden unless `showSubtext` is set. They return `1` when
  the cooldown line shows, and a bad ID raises an error.
- `GetActionInfo` returns nothing for an empty slot, a dead macro button or
  an unknown tag. It never reports a dead macro as `"item"`.
- `PLAYER_SWING` cast resets fire only while auto-attacking.
- `C_Item.GetWeaponEnchantInfo` / `GetItemTempEnchantInfo`: time left counts
  down. `GetSpellInfo` / `C_Spell.GetSpellInfo`: effective cost and cast time
  (rage in whole points); passives have a cast time of 0.
- `C_Item.GetItemCount` uses the engine's search: it counts equipped bags and
  the keyring and skips broken items. With the bank flag, it reads the bank
  even when the bank is closed. Flags `"0"` are false.
- Totems: `GetTotemInfo` / `GetTotemTimeLeft` / `GetTotemDuration` use whole
  seconds and raise an error for a slot outside 1 to 4.
- `PLAYER_EQUIPMENT_CHANGED` comes after `ITEM_LOCK_CHANGED`.
  `UPDATE_INVENTORY_DURABILITY` fires on every recompute, including at login
  and for bag items.
- `NAME_PLATE_CREATED` passes the frame positionally as well as in `arg1`.
- `setfenv` returns the function; `getfenv` reads only a metatable
  `__environment` field (5.1 rules).
- `C_GossipInfo` (1.17.3) answers only after the greeting has resolved.
  `SelectOptionByIndex` skips hidden options.
- `GetCursorInfo` returns `"petaction"` and `"pet", index`. A dragged action
  or auction item returns the plain item-ID link.
- `UnitInLineOfSight` traces like the server. `UnitIsInMyGuild` follows 4.3.4.

### New API in brief

`strmatch`; `C_CVar.SetCVar`; `GetBindingByKey`;
`C_AddOns.GetAddOnInterfaceVersion`; `GetNumGossipAvailableQuests` /
`GetNumGossipActiveQuests`; `C_GossipInfo.GetPoiForUiMapID` / `GetPoiInfo`
with `DYNAMIC_GOSSIP_POI_UPDATED`; `C_MapExplorationInfo.GetExploredAreaIDsAtPosition`
with `MAP_EXPLORATION_UPDATED`; `PLAYER_AVG_ITEM_LEVEL_READY`;
`UnitSelectionColor` / `UnitSelectionType`; `InteractUnit`; `IsTargetLoose`;
`SetUnitCursorTexture`; `PlaySoundFile(file [, channel])`, `StopSound`;
GameTooltip `SetAnchorType`, `IsUnit`, `GetMinimumWidth`, `GetPadding`,
`ANCHOR_TOP` / `ANCHOR_BOTTOM`; StatusBar `SetReverseFill`, `SetFillStyle`,
`SetRotatesTexture`, `SetColorFill`, desaturation; FontString `SetWordWrap`,
`SetIndentedWordWrap`, `GetFontHeight` / `SetFontHeight`, `GetFieldSize`;
Button `SetEnabled`, `RegisterForMouse`, `SetMotionScriptsWhileDisabled`;
Slider and EditBox `Enable` / `Disable` / `IsEnabled`; Frame
`SetPropagateKeyboardInput`, `GetBoundsRect`, `SetDontSavePosition`;
`OnEnable` / `OnDisable` / `OnMinMaxChanged` scripts and
`OnTextChanged(self, userInput)`; XML `mixin=`, `method=`, `<KeyValues>`,
`inherits="A, B"` and `CreateFrame(type, name, parent, template, id)`;
PlayerModel / DressUpModel methods; `GetItemStats(link [, statTable])` with
per-school spell damage.

**Soft targeting** (`softenemy`, `softfriend`, `softinteract`, `any*` tokens,
`PLAYER_SOFT_*_CHANGED`) is off unless the player sets `SoftTargetEnemy` /
`SoftTargetFriend` to 2 or 3. With it on, a spell cast with no target goes to
the soft unit. That is a gameplay choice: an addon may read the tokens but must
not turn the CVars on by itself.

## v1.17.4 to v1.17.8 API and behavior contracts

[SOURCE-VERIFIED] From the pinned
[v1.17.8 API reference](https://github.com/brues-code/ClassicAPI/blob/0d19deaee0fe19cf6735a7789870d45b787fbfee/docs/API.md),
the `v1.17.3...v1.17.8` commit messages and, for nameplate alpha,
[`src/frame/Alpha.cpp`](https://github.com/brues-code/ClassicAPI/blob/abd5367533acf19291a7a5aa64472d5e56cf9619/src/frame/Alpha.cpp). Grep `.private/upstream/classicapi/docs/API.md`
for full payloads. [UNVERIFIED - TEST FIRST] Nothing here has been checked in
game on OctoWoW yet.

### Profiling (1.17.4)

Per-addon memory and CPU, as in later clients:

- `UpdateAddOnMemoryUsage()` then `GetAddOnMemoryUsage(index or "name")`: Lua
  KB per addon, counted at the last update. Each update recounts all memory;
  never call it every frame. Objects from an XML template belong to the addon
  that defines the template. Blizzard addons, unknown names and unloaded addons
  give `0`; an index outside `1..GetNumAddOns()` raises an error.
- CPU needs the `scriptProfile` CVar at `1`, read when the UI loads
  (`/console scriptProfile 1` then `/reload`). It slows every Lua call; turn it
  on only to measure. With it off the CPU functions return `0`.
- `UpdateAddOnCPUUsage()` then `GetAddOnCPUUsage(index or "name")` (ms).
  `GetFunctionCPUUsage(func [, includeSubroutines])` and
  `GetFrameCPUUsage(frame [, includeChildren])` return ms and call count.
  `GetEventCPUUsage([event])` returns ms and event count for all events; the
  `event` argument has no effect, and the count rises even with profiling off.
  `GetScriptCPUUsage()` counts nested scripts twice. `ResetCPUUsage()` zeroes
  times and counts, not memory.
- Developer aids: `_classicapi_LuaHeapAudit()` and `_classicapi_GcTagOf(value)`
  (owning addon name, `nil` for game code, a hex string for `/run` code).
- 1.17.7 also adds the `TOTAL_MEM_*_ABBR` and `ADDON_MEM_*_ABBR` strings.

Use: `!ErrorLog`'s per-addon CPU and memory report can read these instead of
estimating. It must not turn `scriptProfile` on by itself; the player does.

### Soft interact highlight (1.17.4)

The `softinteract` object glows like the mouseover object while it can be used
right now. No API; README now lists soft interact, enemy and friend as one
"Soft targeting" row. The rules in the 1.17.3 section still hold.

### Player name cache (1.17.5)

- `C_PlayerCache.SetScanEnabled` and `C_PlayerCache.IsScanEnabled` are
  **removed**, with the visible-object sweep. Turning the cache on with
  `C_PlayerCache.SetEnabled(true)` now copies every player the engine already
  knows from this session. The setting moved to its own options subcategory.
- `C_PlayerCache.GetPlayerInfoByName` adds a step after the friends list: the
  engine's session name cache (chat senders, group members, players seen).
  It works with the persistent cache off. Every step now ignores case.

### Binding modifiers (1.17.6)

Modifier keys of the bound key are hidden only while a `SPELL`, `ITEM`,
`MACRO` or `CLICK` binding runs. A binding that runs Lua sees them again:
a handler on `SHIFT-E` gets `1` from `IsShiftKeyDown()`. This reverts the
1.17.0 rule that hid them for every binding.

### Small changes (1.17.7)

- `FlashClientIcon([briefly])`: flashes the taskbar button; does nothing while
  WoW has focus. No argument: until focused. Truthy: three flashes. Returns
  nothing. This replaces `UnitXP("notify", "taskbarIcon")` for addons that
  guard `11707`.
- `SpellHasRange` / `C_Spell.SpellHasRange` use the engine's own min/max range,
  so range bonuses count. Self-cast spells return false.
- Spell links that Turtle's chat link handler would drop (such as
  `spell:<id>:0` from `GetSpellLink`) now reach `SetItemRef`. There is one
  `SetItemRef` override left to chain.

### Nameplate alpha (1.17.8)

Default nameplates, and every frame parented under one at any depth, are
exempt from the 1.17 rule that frame alpha multiplies into children
(`frame:GetEffectiveAlpha`). Inside a plate the vanilla rules hold again:

- `plate:SetAlpha(a)` copies `a` down to the plate's child frames, except a
  child that has called `SetAlpha` itself (any value, `1` included): that
  child keeps its own alpha, absolute, and no later engine fade overwrites it.
  Regions (textures, font strings) still draw at the plate's alpha.
- `GetAlpha()` on a plate or anything under it returns the drawn byte
  (`n/255`), as vanilla does, not the remembered own alpha.
- A plate's own fade writes resolve through two new CVars:
  `nameplateNotSelectedAlpha` (default `0.5`) replaces the engine's dimmed
  write (non-target plates), `nameplateSelectedAlpha` (default `1`) its full
  write (the target). At the defaults nothing changes. The substitution is by byte: an addon's `plate:SetAlpha(1)`
  (255) also becomes `nameplateSelectedAlpha`, and `SetAlpha(0.5)` (127)
  becomes `nameplateNotSelectedAlpha`. Writes to the plate's children are
  never substituted.

The CVars are the player's: an addon may read them but should not change them
for the player. [UNVERIFIED - TEST FIRST] Whether the engine writes the plate
fade every frame or only when the target changes is not documented.

## v1.17.9 to v1.17.10 API and behavior contracts

[SOURCE-VERIFIED] From the pinned
[v1.17.10 API reference](https://github.com/brues-code/ClassicAPI/blob/9daf3960c48d42f01b5f8cc38d98b157dfcac934/docs/API.md)
and the `v1.17.8...v1.17.10` commit messages, which also describe changes the
API reference leaves out. Grep `.private/upstream/classicapi/docs/API.md` for
full method tables and payloads. [UNVERIFIED - TEST FIRST] Nothing here has
been checked in game on OctoWoW yet.

### Cooldown API (1.17.9)

Native `Cooldown` frames (see [Native Cooldown frame](#native-cooldown-frame-1171))
get the later clients' methods:

- Timing: `SetCooldown(start, duration [, modRate])`,
  `SetCooldownDuration(duration [, modRate])`,
  `SetCooldownFromExpirationTime(expirationTime, duration [, modRate])`,
  `Clear()` (hides with no flash and no `OnCooldownDone`), `Pause` / `Resume`,
  `SetPaused` / `IsPaused`. `GetCooldownTimes()` returns milliseconds; once the
  sweep ends it reports the flash (`start` = end time, `duration` =
  1000 × `modRate`), and `0, 0` after `Clear()`. `modRate` scales the flash and
  `GetCooldownDisplayDuration`, not the sweep.
- Look: `SetDrawSwipe`, `SetDrawBling` (off: hide at the end with no flash),
  `SetSwipeColor`, `SetEdgeColor`, `SetSwipeTexture` / `SetEdgeTexture` /
  `SetBlingTexture`, `SetRotation`. XML: `drawSwipe`, `drawBling`, `rotation`
  (degrees), `<SwipeTexture>`, `<EdgeTexture>`, `<BlingTexture>`.
- `OnCooldownDone` runs once when the sweep ends, before the flash. It does not
  run for `Clear()` or a cooldown of duration `0`.
- Countdown numbers: every `Cooldown` has a countdown font string
  (`GetCountdownFontString`, FRIZQT 16 outline, centred). It shows only while
  the player's `countdownForCooldowns` CVar is `1` (default `0`), never during
  the flash, and only for cooldowns longer than `SetMinimumCountdownDuration`
  (ms of the full duration, default `2000`). Per frame:
  `SetHideCountdownNumbers`, `SetCountdownAbbrevThreshold` (default 120 s),
  `SetCountdownMillisecondsThreshold` (default 0: whole seconds).
- `CooldownFrame_Set(cd, start, duration, enable [, forceShowDrawEdge, modRate])`,
  `CooldownFrame_Clear(cd)` and `CooldownFrame_SetDisplayAsPercentage(cd, pct)`
  join `CooldownFrame_SetTimer`. `Set`, `Clear` and `SetTimer` also take the
  stock buttons' indicator Models and run the 1.12 timer for them.

Use: on a native frame, `cd:Clear()` replaces `CooldownFrame_SetTimer(cd, 0, 0, 0)`,
and an aura or item timer that knows its end time calls
`SetCooldownFromExpirationTime`. An addon that draws its own countdown text over
cooldowns can let the native numbers do it, but `countdownForCooldowns` is the
player's setting, like the nameplate alpha CVars: read it, never set it. An
addon that keeps its own numbers calls `SetHideCountdownNumbers(true)` on its
frames, so the two never overlap when the player turns the CVar on.
[UNVERIFIED - TEST FIRST] The stock action buttons are indicator Models, which
have no countdown font string, so the CVar should add no numbers to them.

### Script handler arguments (1.17.9)

These extend [4.4](#44-modern-script-handler-arguments):

- A C function given to `SetScript`, such as a frame method, gets the
  positional arguments: `f:SetScript("OnDragStart", f.StartMoving)` works.
  Before 1.17.9 it raised "Attempt to find 'this' in non-table object".
- `OnClick`, `PreClick` and `PostClick` run as `(self, button, down)`;
  `OnEnter` and `OnLeave` as `(self, motion)`. `down` is true on a press and
  false on a release (for `button:Click(name, down)`, the given value).
  `motion` is true when the mouse moved, false when the frame moved, showed or
  hid under a still cursor. **Hazard:** a handler that declared a parameter in
  that position and expected nil now gets a boolean. A handler that declares no
  parameters keeps vanilla's globals.
- `event` is saved before and restored after each `OnEvent` handler, so a
  handler that assigns the `event` global no longer changes it for the next
  listener. Off while `SetModernScriptArgs(false)`.
- More than 19 values reach a handler (`arg20`...). The old `this` / `argN`
  values are read with `rawget`, so a strict-globals `__index` on `_G` no longer
  runs for them.

### Small changes (1.17.9)

- `ItemHasRange(item)` (`1` / `nil`, as 3.3.5) and `C_Item.ItemHasRange(item)`
  (`true` / `false`): whether the item's on-use spell has a minimum or maximum
  range. An uncached item reads as having none and fires no load.
  `C_Item.IsItemInRange` already returns `nil` for a rangeless item.
- Tooltip lines: no limit any more; see [13](#13-tooltip-capacity).
- Textures: a freed NPOT texture no longer enters the recycle pools (a freed
  48x48 could be handed to the next 32x32 request), and textures from 1x1 to
  7x7 load (the minimum was 8 px).

### Aura instance IDs and `UNIT_AURA_DELTA` (1.17.10)

- Every `AuraData` has `auraInstanceID`: one number for one application on one
  unit. It stays through stacks and refreshes, is new when the aura goes and
  comes back, and is never reused. It is `nil` for an aura that is not in the
  unit's aura list (a group member out of range, an aura only the cast cache
  knows). `C_LossOfControl` CC entries carry it too.
- `C_UnitAuras.GetAuraDataByAuraInstanceID(unit, id [, buf])` returns the aura
  with that ID, or `nil`. With `buf` it fills and returns `buf` and makes no
  table. It clears `sourceUnit` and `sourceGUID` when the aura has none, but
  leaves other keys of `buf` as they were: use one `buf` per purpose.
- `UNIT_AURA_DELTA(unitTarget, updateInfo)` is a ClassicAPI event with the
  modern `UNIT_AURA` payload: `isFullUpdate`, `addedAuraInstanceIDs`,
  `updatedAuraInstanceIDs`, `removedAuraInstanceIDs` (each `nil` when empty;
  all three `nil` when `isFullUpdate`). `UNIT_AURA` itself does not change.
  - It fires once per unit and token per frame, so a burst arrives as one
    event; a unit that is both `target` and `party1` fires once for each.
  - Every fire reuses the same four tables: they are valid only during the
    handler. Copy a list to keep it.
  - It gives changes, not the start state. Read all the auras when you
    register, on `isFullUpdate`, and whenever a token starts naming another
    unit (`PLAYER_TARGET_CHANGED`, a nameplate token, a roster change): a
    token that only gets a new unit fires nothing.
  - Timing-only refreshes are reported as updated; a refresh the client cannot
    see fires nothing. With no listener, no lists are built.
  - [UNVERIFIED - TEST FIRST] Whether `RegisterUnitEvent` filters it is not
    documented.

Use: an aura display that rereads every aura of the unit on each `UNIT_AURA`
can keep an `auraInstanceID` to button map and touch only the changed IDs,
reading each with the `buf` form. Instance IDs are also the stable key that
[aura indices](#aura-slot-compaction-and-index-instability) are not.

### Player aura timing and loss of control (1.17.10)

- For `unit == "player"`, `AuraData.duration` is the duration the server
  applied (`SMSG_UPDATE_AURA_DURATION`), with diminishing returns and the
  caster's talents. Before, it was the base or cast-cache estimate. Other units
  are unchanged.
- `C_LossOfControl` CC entries take `startTime`, `timeRemaining` and
  `duration` from the same server timer that `GetPlayerBuffTimeLeft` reads.
  They are `nil` only when the debuff has no timer. Before, they were `nil`
  unless ClassicAPI saw the applying cast, and had no diminishing returns.

### Combat log additions (1.17.10)

These correct the 1.17.0 limits in [Combat log](#combat-log):

- `SPELL_AURA_REFRESH` (`auraType`): an aura's duration started again while
  the aura stays. Every refresh of your own auras; on another unit only when
  the client saw the cast. Nothing at login or on a zone change.
- `SPELL_SUMMON` (a unit: pet, totem) and `SPELL_CREATE` (a game object, such
  as a fishing bobber). A spell the game hides from the log (the mage portals)
  fires no event except `SPELL_CAST_FAILED`.
- `overkill` is the damage above the target's health (0 when it lives);
  `overhealing` the heal above its missing health. Both are 0 when the target
  is out of view or the server sends its health as a percentage, which most
  servers do outside your group. [UNVERIFIED - TEST FIRST] What OctoWoW sends
  for units outside the group.
- `DAMAGE_SHIELD` names its spell (Thorns, Fire Shield, Retribution Aura) when
  the shield's owner is in view and has exactly one damage-shield aura of that
  school. Otherwise `spellId` is 0 and `spellName` `nil`, as before.
- `DAMAGE_SHIELD_MISSED` with `missType` `"IMMUNE"` now fires for immune
  targets, with the mapping 3.3.5 and 4.3.4 use: the commit's live check was a
  Fireball on an immune target. Do not read this subevent as "a damage shield
  missed".
- `SPELL_DISPEL` and `SPELL_DISPEL_FAILED` name the dispelling spell when its
  cast was seen (Dispel Magic, Purge). A dispel from an aura (Abolish Poison)
  keeps `spellId` 0.
- `SPELL_INSTAKILL` has a source when the cast was seen.

### Small changes (1.17.10)

- `IsDualWielding()` (`true` / `false`): the player can dual wield and has a
  weapon in the off hand; `false` until the off-hand item is cached.
- `OffhandHasWeapon()` is the engine's own function again: `1` for a
  weapon-class off-hand item, else `nil`. ClassicAPI's earlier override
  returned `true` / `false`, so `OffhandHasWeapon() == 1` was always false
  under 1.17.9 and earlier. Test its truth, never compare it.
- `UnitIsFeignDeath(unit)` reads the dynamic flag `UNIT_DYNFLAG_DEAD`, as 3.3.5
  does. Before, it read a unit flag that vmangos-based servers never set, so it
  was always false there. [UNVERIFIED - TEST FIRST] On OctoWoW, while
  feigning: `/run print(UnitIsFeignDeath("player"))`.
- Edit box history: a sent line goes to the end of the history ring, so
  browsing and then sending no longer overwrites older lines. A line equal to
  the newest one is not added again.
- Equipment sets: a right-click drops a held set, with the drop sound.
- Custom events no longer take engine event slots that the engine fires by
  number. Before, the fifth custom event shared slot 6 with
  `ADDON_LIST_UPDATE` and could fire with it.

## v1.17.11 API and behavior contracts

Source: the pinned
[v1.17.11 API reference](https://github.com/brues-code/ClassicAPI/blob/317539dbd8aa9e9cd7a23441c0e355bb85c7e2ab/docs/API.md)
and the `v1.17.10...v1.17.11` commit messages (four commits, released
2026-10-27). Guard: `11711`.

### String helpers (1.17.11)

Four Blizzard string globals the base library lacked:

- `strlenutf8(s)`: characters, not bytes (`strlen` counts bytes).
- `strcmputf8i(a, b)`: case-insensitive compare; only the sign of the number
  means anything (negative: `a` first, `0`: equal). The fold covers ASCII,
  Latin-1 `à`..`þ`, `œ` and Cyrillic. It makes no strings, so a sort
  comparator `function(a, b) return strcmputf8i(a, b) < 0 end` replaces
  `string.lower(a) < string.lower(b)`, which builds two strings on every
  comparison.
- `strsplittable(sep, str [, pieces])`: `strsplit` returned as one array; no
  stack limit. Replaces `{ strsplit(sep, str) }` and gmatch loops that only
  fill a table.
- `strconcat(...)` / `string.concat(...)`: joins its arguments like `..`;
  numbers convert, anything else is an error, no arguments gives `""`.

### Fixes (1.17.11)

- `C_EquipmentSet.GetItemLocations`: an item in the main bank is
  `BANK | inventorySlot` (`BankButtonIDToInvSlotID`: bank slot N is
  inventory slot 39 + N; slot 3 is `0x40002A`). Before, it was
  `BANK | bankSlot` (`0x400003`), so the shared helpers read the paperdoll
  instead of the bank. The main bank has 24 slots.
- Cooldown `SetReverse(true)`: the sweep starts empty and becomes full. At the
  end it stays full while the flash plays, then the frame hides. Before, the
  icon showed bright for the frames between the client-side end and the aura's
  removal.
- `PlaySoundFile`: the docs no longer name a file count. The client caps how
  many files play at once (SuperWoW's `UncapSounds` lifts the cap; 16 played
  at once in a probe); at the cap the call returns `false`. A file holds its
  place until it ends, also while fading.

## v1.17.12 to v1.18.5 API and behavior contracts

Source: the pinned
[v1.18.5 API reference](https://github.com/brues-code/ClassicAPI/blob/c965e4911726f9cedd6354ecd856d92a0b203831/docs/API.md)
and the `v1.17.11...v1.18.5` commit messages (eight releases, 2026-10-27 to
2026-10-30). Guard: `11805`. Search the pinned docs for a name before using it;
this section lists only what changes how VanillaForge addons are written.

### Fixes that retire workarounds

- **Range answers know the target** (1.18.0). `C_Spell.IsSpellInRange` and
  `C_Item.IsItemInRange` return `nil` for a unit the spell cannot be cast on:
  a heal on an enemy, a damage spell on a friend, the wrong creature type, a
  dead unit for anything but a resurrect. A pet spell measures to the pet, a
  resurrect on a ghost to its corpse. Line of sight is still not checked. A
  `UnitCanAttack` / `UnitIsFriend` test written only to make a range answer
  meaningful can go; `nil` means "no answer", so colour only `true`/`false`.
  Self-range spells (Hearthstone, totems) return `nil`, not `false`.
- **Spell ranges include talents** (1.17.13). `GetSpellInfo` and
  `C_Spell.GetSpellInfo` report `minRange`/`maxRange` through the engine:
  range talents, spell mods, the ranged-weapon scale; `0`/`0` for melee. Code
  that adds talent yards itself now counts them twice.
- **`isOnGCD`** (1.17.13). `C_Spell.GetSpellCooldown(spell)` sets
  `isOnGCD = true` when the reported start and duration are the global
  cooldown. Replaces `duration <= 1.5` guesses (a rogue's GCD is 1 s).
- **Player aura durations after login** (1.18.0). Auras already on the
  character at login reported the time left as their full duration; they now
  report the base duration (or the remaining time where a caster modifier
  stretched it). Remove any re-learning of totals after login.
- **Loot** (1.17.13). An unanswered loot request no longer blocks all looting
  until relog; every loot sender refuses while mounted.
- **Loss of control** (1.18.0). A spell that grants immunity to the effect is
  not reported as locked: a druid's forms while polymorphed.
- **Region scale** (1.18.0). A texture or font string on a hidden frame has
  its frame's scale at once; `GetLeft`/`GetRect` on hidden regions are right.

### Retail functions now native (1.18.0 to 1.18.2)

Use these instead of loops, scans or own helpers:

| Job | Function |
| --- | --- |
| Active stance-bar index | `GetShapeshiftForm([requireForm])`: 0 when none; replaces a `GetShapeshiftFormInfo` loop. Identify a form with `GetShapeshiftFormID()` |
| Cancel one of your auras | `CancelUnitBuff("player", index [, filter])`: index in `C_UnitAuras.GetAuraDataByIndex` order, not `UnitBuff` order; only right-click-cancelable auras |
| Cast a rank by ID | `CastSpellByID(spellID [, unit])`: target unchanged |
| Run macro text | `RunMacroText(text [, button])`, `GetRunningMacro()`, `GetMacroBody(macro)` |
| Group | `InviteUnit`, `UninviteUnit`, `PromoteToLeader` |
| Money words | `GetCoinText(copper [, sep])`: "12 Gold, 34 Silver"; there is no compact `1g 50s` form |
| Base cooldown | `GetSpellBaseCooldown(spellID)` in ms, talents excluded |
| Item state | `IsCurrentItem`, `IsEquippedItemType`, `IsDressableItem`, `IsHelpfulItem`, `IsHarmfulItem` |
| Spell kind | `IsAttackSpell`, `IsAutoRepeatSpell`, `IsConsumableSpell` |
| Player | `IsLoggingOut`, `IsPlayerInWorld`, `IsChatAFK`, `IsChatDND`, `GetCritChance`, `GetRangedCritChance`, `GetMaxPlayerLevel`, `GetExpansionLevel` |
| PvP flag | `SetPVP`, `GetPVPDesired`, `GetPVPTimer`, `IsPVPTimerRunning`, event `PVP_TIMER_UPDATE` |
| Resurrection | `UnitHasIncomingResurrection`, `INCOMING_RESURRECT_CHANGED`; `C_DeathInfo.GetSelfResurrectOptions` / `UseSelfResurrectOption`, `SELF_RES_SPELL_CHANGED` |
| Bags | `C_Container.SetItemSearch`, `IsContainerFiltered`, `INVENTORY_SEARCH_UPDATE`; `GetContainerItemInfo`'s `isFiltered` is now real |
| Other | `GetNumGossipOptions`, `GetBuybackItemLink`, `CanCancelAuction`, `AddOrRemoveFriend`, `Expand/CollapseAllFactionHeaders`, `SendSystemMessage`, `ConsoleAddMessage`, `GetTickTime`, `CanBeRaidTarget`, `IsItemAction`, `IsPetAttackAction`, `IsAtStableMaster`, `GetMouseButtonName`, F13 to F24 keys, `SetBagPortraitTexture`, `SetInventoryPortraitTexture` |

Completed-quest functions (`QueryQuestsCompleted`, `GetQuestsCompleted`,
`C_QuestLog.IsQuestFlaggedCompleted`, `QUEST_QUERY_COMPLETE`) exist only on a
Turtle-lineage client or server; do not use them without checking the active
server profile.

### Frames and UI kits (1.18.0 to 1.18.5)

- Mouse: `SetMouseClickEnabled` / `SetMouseMotionEnabled` separately,
  `SetPropagateMouseClicks` / `SetPropagateMouseMotion`, `IsMouseMotionFocus`.
  A frame that needs hover but must pass clicks through no longer needs a
  second overlay frame.
- Layout: `SetClipsChildren`, `SetUsingParentLevel`, `SetAlphaGradient`,
  `DesaturateHierarchy`, `fontstring:SetTextToFit`, `region:SetToDefaults`,
  `GetScaledRect`, `GetPointByName`, `ClearPoint`, `AdjustPointsOffset`;
  `GetWidth`/`GetHeight`/`GetSize` take `ignoreRect`.
- XML: `intrinsic` frame types, `<Scripts>` `inherit="prepend"/"append"`,
  `<Anchor>` `relativeKey` and `x`/`y`, `parentArray`, atlases.
- Retail kits in `!!!ClassicAPI`: `BackdropTemplate`, ScrollBox with the
  Classic Era scroll bar, `Blizzard_Menu` (`MenuUtil`, `DropdownButton`),
  `EventFrame`/`EventButton`/`EventEditBox`, `LayoutFrame`, `SOUNDKIT`
  constants. A 1.12 frame still has `SetBackdrop` natively; the template
  matters only to code written for retail. Replacing `UIDropDownMenu` with
  `Blizzard_Menu` is a rewrite, not a cleanup: do it only when a dropdown is
  being rebuilt anyway, and check it in game.
- ScrollingMessageFrame: `GetMessageInfo`, `BackFillMessage`, scroll offset,
  `SetInsertMode` (including TOP), `AddOnDisplayRefreshedCallback`.
- `GameTooltip:SetFrameStack(showHidden, showRegions, highlightIndexChanged)`,
  `region:GetDebugName`, `region:GetSourceLocation`.
- `securecall`, `securecallfunction`, `secureexecuterange`.
- Edit boxes: caret, selection and clicks follow tall inline icons (1.18.4).
