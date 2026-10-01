# OctoWoW Addon Impact & Capability Displacement Matrix

> **Cross-Addon Audit for the VanillaForge Maintained Addon Portfolio**
> Evaluated against deployed ClassicAPI v1.15.16, SuperWoW 2.2, NamPower 4.6.2, UnitXP SP3 Build 90, and OctoWoW FrameXML.

---

## 1. Portfolio Capability Matrix

| Addon | Native Client APIs | ClassicAPI Namespaces | SuperWoW / NamPower / UnitXP | FrameXML Hooks | Displacement Candidates | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FostercareTweaks** | Standard UI, unit frame, action bar | `C_Item`, `C_Map`, `C_MerchantFrame`, `C_NamePlate`, `C_Spell`, `hooksecurefunc`, `table.wipe` | `UnitGUID` (SuperWoW), `UnitXP` (UnitXP) | UnitFrame, TargetFrame, ActionBars | Custom junk selling already in `C_MerchantFrame.SellAllJunkItems()`; custom vendor prices in `C_Item.GetItemSellPrice()` | **REPLACE** (vendor/junk helpers), **RETAIN** (custom UI styling) |
| **ItemRack** | Inventory, bags, equipment slots, paperdoll | `C_Container.*` (`GetContainerItemDurability`, `GetContainerItemID`, `HasContainerItem`, `SwapItems`), `C_Item.*` (`EquipItemByName`, `GetEnchantInfo`, `GetItemData`, `GetItemID`, `GetItemName`, `GetItemTempEnchantInfo`), `hooksecurefunc`, `table.wipe` | None declared | PaperdollFrame, CharacterFrame | Custom bag scanning loops replaced by `C_Container` and `C_Item` | **RETAIN** (already modernized on ClassicAPI; robust) |
| **AutoBG** | Battleground map, scoreboard, chat | `C_Timer.*` (`After`, `NewTicker`, `NewTimer`), `C_UnitAuras.*` (`GetAuraDataByIndex`, `GetAuraDataBySlot`, `GetAuraSlots`), `hooksecurefunc`, `table.wipe` | `SpellInfo`, `UnitGUID` (SuperWoW), `NamPower` (cast events), `UnitXP` | BattlefieldFrame, WorldStateScoreFrame | Custom timer ticker loops replaced by `C_Timer`; aura scanning by `C_UnitAuras` | **RETAIN** (high-performance combat hotpath; correctly leverages NamPower/SuperWoW) |
| **Bagnon** | Bags, bank, inventory events | `C_Container.*` (`CalculateTotalNumberOfFreeBagSlots`, `GetBackpackAutosortDisabled`, `GetBankAutosortDisabled`, `GetContainerItemID`, `GetContainerNumFreeSlots`, `GetSortBagsRightToLeft`, `SortBags`), `hooksecurefunc`, `table.wipe` | None declared | ContainerFrame, BankFrame | Legacy slot iteration replaced by `C_Container.SortBags()` and container helper APIs | **RETAIN** (fully displaced legacy bag iteration with modern C_Container) |
| **AutoLazy** | Loot, quest, gossip, chat | `C_GossipInfo.*` (all quest/option methods), `C_Item.GetItemCount`, `C_Timer.After`, `table.wipe` | `UnitGUID` (optional fallback) | `ChatFrame_OnEvent` (for `CHAT_MSG_LOOT`), `LootFrame` | Legacy `GetGossipAvailableQuests` parsing replaced by `C_GossipInfo`; custom bag counter replaced by `C_Item.GetItemCount` | **RETAIN** (cleanly modernized on ClassicAPI v1.15.15+; verified against v1.15.16) |
| **TrinketMenu** | Inventory slots, item cooldowns | `C_Container.GetContainerItemID`, `C_Item.EquipItemByName`, `C_Timer.*`, `hooksecurefunc`, `table.wipe` | None declared | UI action bars | Legacy equip item logic replaced by `C_Item.EquipItemByName` | **RETAIN** (stable bounded footprint) |
| **MikScrollingBattleText** | Combat log, unit events, animations | `C_Timer.After`, `C_Timer.NewTicker`, `table.wipe` | `SpellInfo`, `UnitGUID` (SuperWoW), `GetNampowerVersion`, `NamPower` (spells), `UnitXP` | CombatTextFrame | Custom frame ticker replaced by `C_Timer`; combat log parsing uses NamPower high-precision events | **RETAIN** (critically optimized for 1.12.1 combat throughput) |
| **TWThreat** | Addon messages, combat log, party/raid | `table.wipe` | `SendAddonMessage` (SuperWoW extended bandwidth) | None | Threat broadcast utilizes extended channel throughput | **RETAIN** (essential raid utility; no overlap with client UI) |

---

## 2. AutoLazy Post-Modernization Static Verification Deep Dive

Baseline Commit: `3c545b84c235b60c54eeac703d24affe0311ccfd`
Author: `Fostercare5988`
Message: `fix(autolazy): align loot filtering and quest fallback with OctoWoW`

### Detailed Finding per Area:

#### A. Clean Roll Chat (`ChatFrame_OnEvent` Interception)
- **Deployed Architecture**:
  - `ChatFrame.lua` line 1452: When `event == "CHAT_MSG_LOOT"`, the engine passes pre-formatted string `arg1` straight into `this:AddMessage(arg1, ...)`.
  - AutoLazy wraps `ChatFrame_OnEvent(event)`: checks `if event == "CHAT_MSG_LOOT" and arg1` then calls `ShouldSuppressLootMessage(arg1)`.
  - Evaluated: **[STATICALLY VERIFIED]**. The hook location is authoritative and intercepts all Blizzard chat frame outputs before rendering.
- **Pattern Match Evaluation**:
  - `ROLL_FORMAT_KEYS` in `AutoLazy.lua`:
    - All 14 intermediate roll format keys (`LOOT_ROLL_START`, `LOOT_ROLL_NEED`, `LOOT_ROLL_NEED_SELF`, `LOOT_ROLL_GREED`, `LOOT_ROLL_GREED_SELF`, `LOOT_ROLL_PASSED`, `LOOT_ROLL_PASSED_SELF`, `LOOT_ROLL_ROLLED`, `LOOT_ROLL_ROLLED_SELF`, `LOOT_ROLL_ROLLED_NEED`, `LOOT_ROLL_ROLLED_NEED_SELF`, `LOOT_ROLL_ROLLED_GREED`, `LOOT_ROLL_ROLLED_GREED_SELF`, `LOOT_ROLL_ALL_PASSED`): **[STATICALLY VERIFIED]** (exact matches in deployed `GlobalStrings.lua`).
    - Intermediate Numeric Roll Suppression: Intermediate numeric roll values (`LOOT_ROLL_ROLLED`, `LOOT_ROLL_ROLLED_SELF`, `LOOT_ROLL_ROLLED_NEED`, `LOOT_ROLL_ROLLED_NEED_SELF`, `LOOT_ROLL_ROLLED_GREED`, `LOOT_ROLL_ROLLED_GREED_SELF`) and roll start messages (`LOOT_ROLL_START`) ARE intermediate group roll chatter and are correctly included in the suppression table.
    - Purged Obsolete/Dead Keys: `LOOT_ROLL_PASS` (stock key is `LOOT_ROLL_PASSED`) and `LOOT_ROLL_PENDING` (only `ERR_LOOT_ROLL_PENDING` exists in GlobalStrings, routing to UIErrorsFrame / `CHAT_MSG_SYSTEM`, never `CHAT_MSG_LOOT`) have been completely purged from `ROLL_FORMAT_KEYS`.
    - Native Winner Lines Unsuppressed: `LOOT_ROLL_WON`, `LOOT_ROLL_YOU_WON`, and condensed winner variants (`LOOT_ROLL_WON_NO_SPAM_*`, `LOOT_ROLL_YOU_WON_NO_SPAM_*`): **[STATICALLY VERIFIED]** (Omitted from suppression so Blizzard's native winner announcement is rendered directly without custom reconstruction).

#### B. `C_GossipInfo` Usage in `ProcessGossip()`
- AutoLazy invokes:
  `C_GossipInfo.GetActiveQuests()`, `C_GossipInfo.GetAvailableQuests()`, `C_GossipInfo.GetOptions()`, `C_GossipInfo.SelectActiveQuest()`, `C_GossipInfo.SelectAvailableQuest()`, `C_GossipInfo.SelectOption()`, `C_GossipInfo.SelectOptionByIndex()`.
- Deployed Client: `ClassicAPI.dll` v1.15.16 exports all of these C_GossipInfo methods.
- Evaluated: **[STATICALLY VERIFIED]**.

#### C. `QUEST_GREETING` Distinct Handling in `ProcessGreeting()`
- AutoLazy handles `QUEST_GREETING` separately using native APIs:
  `GetNumActiveQuests()`, `GetActiveTitle()`, `SelectActiveQuest()`, `GetNumAvailableQuests()`, `GetAvailableTitle()`, `SelectAvailableQuest()`.
- Deployed FrameXML audit confirms that during `QUEST_GREETING`, `QuestFrameGreetingPanel` consumes these exact APIs, while `C_GossipInfo` tables are unpopulated.
- Evaluated: **[STATICALLY VERIFIED]**.

#### D. `GOSSIP_CLOSED` & Session Handover
- In `AutoLazy.lua`, `GOSSIP_CLOSED` sets a 0.5s timer (`C_Timer.After(0.5, ...)`) before terminating `questSessionActive`.
- FrameXML audit proves `UIPanelWindows["GossipFrame"]` and `UIPanelWindows["QuestFrame"]` collide in `area = "left"`, causing `GossipFrame` to hide synchronously when `QuestFrame` opens during quest selection.
- Evaluated: **[STATICALLY VERIFIED]**. The grace window is necessary and architecturally correct.

#### E. `C_Item.GetItemCount`
- AutoLazy calls `C_Item.GetItemCount(req.item)` for inventory count calculations.
- Deployed `ClassicAPI.dll` v1.15.16 exports `C_Item.GetItemCount`.
- Evaluated: **[STATICALLY VERIFIED]**.

#### F. Custom Tel'Abim Banana Rules
- AutoLazy specifies `questID = 40739` / `questTitle = "the tel'abim banana transmutation"` (requires 3 item 60954, 1 item 11176) and `questID = 40740` / `questTitle = "tel'abim banana transmutations!"` (requires 15 item 60954, 5 item 11176).
- Verified against OctoWoW database (`https://octowow.st/db/?item=60954` = Tel'Abim Banana).
- Evaluated: **[STATICALLY VERIFIED]** for both `GOSSIP_SHOW` path (exact numeric `questID` match) and `QUEST_GREETING` path (exact normalized title string fallback; no fuzzy or generic alias conflation between the 3+1 and 15+5 quests).

#### G. Dependency Cleanliness
- AutoLazy TOC declares only `## Interface: 11200` and `## X-ClassicAPI-Min-Version: 1.15.15`.
- No hard SuperWoW, NamPower, or UnitXP dependencies are declared.
- `UnitGUID` is invoked defensively with `(UnitGUID and (UnitGUID("npc") or ...))`.
- Evaluated: **[STATICALLY VERIFIED]**.
