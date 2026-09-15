# ClassicAPI Master Reference for WoW 1.12.1

> Local AI knowledge base for ClassicAPI.
>
> Purpose: let coding assistants design and modernize WoW 1.12.1 addons against ClassicAPI without needing to browse GitHub for ordinary API discovery.
>
> Source basis: `brues-code/ClassicAPI`, default branch `master`, official `README.md`, official `docs/API.md`, and selected implementation/source references.
>
> Snapshot baseline used by VanillaForge: **ClassicAPI v1.15.8+**.
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
```

The VanillaForge framework baseline is:

```text
ClassicAPI v1.15.8+
```

Do not assume a future version's new API exists solely because a similarly named Retail API exists.

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
C_CVar.SetCVarBitfield
```

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
C_LossOfControl.GetActiveLossOfControlData
C_LossOfControl.GetActiveLossOfControlDataCount
C_LossOfControl.GetSchoolLockout
```

Related events:

```text
LOSS_OF_CONTROL_ADDED
LOSS_OF_CONTROL_UPDATE
```

Useful for PvP CC / school lockout addons.

---

## 52. Macro — `C_Macro`

Important documented capabilities include:

```lua
C_Macro.GetMacroIcon
C_Macro.SetMacroDisplay
```

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

## 58. System

```lua
GetPhysicalScreenSize
CopyToClipboard
```

---

## 59. Talent

```lua
GetTalentSpellID
GetTalentIDByIndex
```

---

## 60. Targeting

```lua
GetPlayerFacing
TargetDirectionEnemy
TargetDirectionFriend
TargetNearest
TargetNearestEnemyPlayer
TargetNearestFriendPlayer
```

---

## 61. Taxi Map — `C_TaxiMap`

```lua
C_TaxiMap.GetTaxiNodesForMap
C_TaxiMap.GetAllTaxiNodes
C_TaxiMap.GetTaxiPaths
C_TaxiMap.GetTaxiPathWaypoints
C_TaxiMap.GetTaxiRoute
```

---

## 62. Texture — `C_Texture`

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

## 63. Time — `C_Timer` / `C_DateAndTime`

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

## 64. Totems

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

## 65. Tracking

```lua
GetNumTrackingTypes
GetTrackingInfo
SetTracking
```

---

## 66. TradeSkillUI — `C_TradeSkillUI`

```lua
C_TradeSkillUI.GetTradeSkillListLink
C_TradeSkillUI.GetCraftListLink
C_TradeSkillUI.GetTradeSkillListRecipes
```

---

## 67. UIColor — `C_UIColor`

```lua
C_UIColor.GetColors
```

---

## 68. Unit

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

## 69. Unit Auras — `C_UnitAuras`

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

### Performance note

The current ClassicAPI source explicitly documents the positional `C_UnitAuras.UnitAura` path as a no-table-allocation route.

For high-frequency aura scanning, this can be preferable to constructing a Lua table per aura.

This namespace should replace legacy hidden tooltip aura scanners.

---

## 70. Voice Chat / Text-to-Speech

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

---

## 71. XML Utilities — `C_XMLUtil`

```lua
C_XMLUtil.DoesTemplateExist
C_XMLUtil.GetTemplateInfo
C_XMLUtil.GetTemplates
```

---

# PART V — EVENT CATALOG

The official README snapshot documents the following ClassicAPI-added or enhanced events.

## 72. Inventory / Equipment

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
```

---

## 73. Input / Cursor

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

## 74. Faction / Quest

```text
FACTION_STANDING_CHANGED
QUEST_ACCEPTED
QUEST_DATA_LOAD_RESULT
QUEST_REMOVED
QUEST_TURNED_IN
```

---

## 75. Loot

```text
LOOT_HISTORY_ROLL_CHANGED
LOOT_HISTORY_ROLL_COMPLETE
LOOT_HISTORY_FULL_UPDATE
LOOT_SCAN_COMPLETED
```

---

## 76. Loss of Control

```text
LOSS_OF_CONTROL_ADDED
LOSS_OF_CONTROL_UPDATE
```

---

## 77. Nameplate / Focus

```text
NAME_PLATE_CREATED
NAME_PLATE_UNIT_ADDED
NAME_PLATE_UNIT_REMOVED
PLAYER_FOCUS_CHANGED
```

---

## 78. Spellcast Events

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

## 79. Misc Events

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

## 80. Version Globals

```lua
CLASSIC_API_VERSION
INTERFACE_VERSION
```

---

## 81. Expansion Constants

```text
LE_EXPANSION_LEVEL_CURRENT
LE_EXPANSION_CLASSIC
...
```

The official documentation includes later expansion enum constants for compatibility even though the runtime client remains 1.12.1.

---

## 82. Enums

Documented enum families include:

```text
Enum.AddOnSecurityStatus
Enum.PowerType
Enum.InventoryType
Enum.ItemClass
Enum.ItemQuality
Enum.UICursorType
Enum.SpellBookSpellBank
Enum.SpellBookItemType
```

Use `/classicapi` for exact values when numeric identity matters.

---

# PART VII — GLUEXML / LOGIN-SCREEN API

## 83. Account Storage

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

## 84. Character List

GlueXML-only:

```lua
GetSavedCharacterOrder(realm)
SetSavedCharacterOrder(realm, order)
```

---

## 85. Glue-State Mirrored Functions

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

## 86. DebugTools Companion

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

## 87. Recommended Verification Workflow

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

## 88. Replace Legacy Tooltip Aura Scanning

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

## 89. Replace Combat-Log String Castbars

Prefer:

```lua
C_Spell.UnitCastingInfo
C_Spell.UnitChannelInfo
UNIT_SPELLCAST_*
```

when they provide the needed source of truth.

---

## 90. Replace Fake Focus

Prefer:

```lua
FocusUnit
ClearFocus
focus
focustarget
```

---

## 91. Replace Nameplate WorldFrame Scraping

Prefer:

```lua
C_NamePlate.*
NAME_PLATE_*
nameplateN
```

---

## 92. Replace Manual Bag Sorting

Prefer:

```lua
C_Container.SortBags
C_Container.SortBankBags
BAG_UPDATE_DELAYED
```

when appropriate.

---

## 93. Replace Manual Item Metadata Scraping

Check:

```lua
C_Item.*
C_Container.*
```

before scraping item tooltips.

---

## 94. Replace Manual Timers

Check:

```lua
C_Timer.After
C_Timer.NewTimer
C_Timer.NewTicker
```

before implementing an `OnUpdate` timer queue.

---

## 95. Replace Home-Grown Spell Metadata Tables

Check:

```lua
C_Spell.*
C_SpellBook.*
```

before duplicating spell DBC metadata in Lua.

---

## 96. Replace Manual Range / Position Helpers

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

## 97. ClassicAPI Is Not Retail

A Retail function name is not proof that ClassicAPI implements it.

Use only:
- this reference
- `/classicapi`
- official docs
- current source
- empirical verification

---

## 98. Bundled Lua Helpers vs DLL Functions

Some functionality comes from the embedded `!!!ClassicAPI` addon rather than a direct C++ Lua binding.

For addon authors this may be operationally transparent, but it matters when diagnosing load order or implementation details.

---

## 99. Hot-Path Choice Matters

Modern API does not automatically mean the table-returning form is the fastest form.

Example: `C_UnitAuras` provides both table-returning and positional APIs.

For high-frequency scanning, prefer the documented zero-allocation path where appropriate.

---

## 100. Do Not Preserve Obsolete Vanilla Workarounds by Default

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

---

# PART XI — REFERENCE MAINTENANCE

## 101. Source Snapshot

This document was built from the official repository:

```text
brues-code/ClassicAPI
branch: master
```

Official source files used as primary reference:

```text
README.md
docs/API.md
selected src/ implementation files
```

At document creation, the official API reference file observed had blob SHA:

```text
7290a5c9158f736cf7136b23b66178648b57a9c1
```

This is useful for deciding whether the upstream reference changed.

---

## 102. Refresh Protocol

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

## 103. Authority Order for AI

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

## 104. Most Important Modernization APIs

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

## 105. Final Rule

Before writing a workaround for a limitation commonly associated with stock WoW 1.12.1, search this reference.

ClassicAPI exists specifically to make many of those limitations obsolete.
