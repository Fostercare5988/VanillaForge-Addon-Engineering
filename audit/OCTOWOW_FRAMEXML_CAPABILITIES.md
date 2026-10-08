# OctoWoW FrameXML & XML Implementation Baseline

> **Reverse-Engineered UI Architecture of the Authoritative OctoWoW Client**
> Based on byte-level diffs against stock Blizzard WoW 1.12.1 `patch.MPQ` and effective files in `patch-4.mpq` / `patch-5.mpq`.

---

## 1. Effective FrameXML Load Precedence

WoW 1.12.1 loads MPQ archives sequentially. Patches override earlier archives; loose files on disk override MPQs. In the deployed OctoWoW environment:

| FrameXML Subsystem File | Effective Source MPQ | File Size (Bytes) | SHA256 Checksum | Stock Status |
| :--- | :--- | :--- | :--- | :--- |
| **`FrameXML.toc`** | `patch-5.mpq` | 3,693 | `551119c1893633d8c42fb6f16f6946e06e261f9e8fbdaab05ebceec1ff3c9c98` | **Heavily Extended** (Adds LFT, OctoCalendar, Locale, AIO, ShopUI; merges Sound/UIOptions into modern Options) |
| **`GlobalStrings.lua`** | `patch-5.mpq` | 312,863 | `6bb6dd6006be7af38fa439985a47550173f55279e2f279298f13c9985a26ec2a` | **Modified & Extended** (Adds Hardcore, LFT, cursor looting, and custom title strings) |
| **`ChatFrame.lua`** | `patch-4.mpq` | 72,017 | `2371fd8216a8b06eeb0f8f3aa0ced74e07d3bb4e3fba27d5c7bcfb89cc9b124f` | **Modified** (Sticky channels, Hardcore chat, Shift/Alt scroll speed, `PLAYER_LOGIN` dock selection) |
| **`ChatFrame.xml`** | `patch-4.mpq` | 3,672 | `98db0d338fd97a63bcea7f0e0c0c04904d262990da12d5952cf30f4f2ac96e2b` | **Modified** (EditBox & button anchoring tweaks) |
| **`LootFrame.lua`** | `patch-4.mpq` | 11,825 | `9464df009e6ef4e2701a52bfb5293c97b9f72c851de0f74fc93e87ae4becb03d` | **Modified** (Class-grouped Master Loot candidate dropdowns, custom gold backdrops) |
| **`LootFrame.xml`** | `patch-4.mpq` | 14,735 | `df44c8d4675c702cd3255dcf1c09c375c99de4d852a7dd950d65f0117475d217` | **Modified** (GroupLoot dropdown close on mouse-up) |
| **`QuestFrame.lua`** | `patch-4.mpq` | 21,328 | `546efb3238d46d6cd3cc4d03e9d817507e41ba4d1203a3418a9f15f9f486748f` | **Modified** (Confirmation popup when quest completion requires money) |
| **`QuestFrame.xml`** | `patch.MPQ` | 35,494 | `23635b2ca881b75f81e2c0c0fb55c6c50173b2e76f61c0ea8e91be5f0a7d1832` | **Stock 1.12.1** |
| **`GossipFrame.lua`** | `patch-4.mpq` | 4,090 | `ec61b2531e750e3d3c676b09a625e88883f591abefd278fb180478a97e23de34` | **Cleaned** (Replaces `getglobal` with `_G` lookup table) |
| **`GossipFrame.xml`** | `patch.MPQ` | 16,154 | `dae744fd7f7eb35660cd2f2c617c9f62e4211c49fa3c2aac4d9743532b791765` | **Stock 1.12.1** |
| **`UIParent.lua`** | `patch-4.mpq` | 63,478 | `9ad1082fa46d02bc4fb7ee2d9f0509d171cb6b3a5c1a5440a1fef786ad4a28cc` | **Modified** (Wide QuestLogFrame `width=690`, snap grid size 2, modernized window slots) |
| **`UIParent.xml`** | `patch.MPQ` | 1,813 | `f6264c5f016eb96095e789278fd083f8d2ddc407099fe3ce7223f873b3303139` | **Stock 1.12.1** |
| **`QuestLogFrame.lua`** | `patch-5.mpq` | 27,658 | `39bdfaf250eca7320ac5d0eca48ee422a1f55f8ab3bbdcae227ec854671f9d0c` | **Heavily Modified** (Supports dual-pane wide layout, quest tracking buttons, level indicators) |

---

## 2. Chat Subsystem Deep Dive

### 2.1 Sticky Channels & Channel Extensions
In `ChatFrame.lua`:
- `ChatTypeInfo["OFFICER"] = { sticky = 1 };` (Stock was 0)
- `ChatTypeInfo["WHISPER"] = { sticky = 1 };` (Stock was 0)
- `ChatTypeInfo["CHANNEL"] = { sticky = 1 };` (Stock was 0)
- `ChatTypeInfo["RAID_WARNING"] = { sticky = 1 };` (Stock was 0)
- `ChatTypeInfo["HARDCORE"] = { sticky = 1 };` (OctoWoW addition)
- `ChatTypeGroup["HARDCORE"] = { "CHAT_MSG_HARDCORE" };`
- `ChannelMenuChatTypeGroups` includes `HARDCORE` and `SYSTEM`.

### 2.2 Mouse Scroll Acceleration
`ChatFrame.lua` implements native fast scrolling in `ChatFrame_OnMouseWheel`:
- Standard wheel scroll: 1 line.
- `Alt + Wheel`: scrolls 4 lines at a time.
- `Shift + Wheel`: executes `this:ScrollToTop()` or `this:ScrollToBottom()`.

### 2.3 Loot Message Routing (`CHAT_MSG_LOOT`)
Line 1452 of `ChatFrame.lua`:
```lua
if ( type == "SYSTEM" or type == "TEXT_EMOTE" or type == "SKILL" or type == "LOOT" or type == "MONEY" ) then
    this:AddMessage(arg1, info.r, info.g, info.b, info.id);
```
**Key Architecture Findings:**
1. When `event == "CHAT_MSG_LOOT"`, `type` is derived as `strsub(event, 10)` -> `"LOOT"`.
2. Unlike player chat (which undergoes formatting via `CHAT_<TYPE>_GET`), `CHAT_MSG_LOOT` arrives from the C++ client engine as a **completely formatted text string** in `arg1`.
3. Lua FrameXML performs **zero parsing or text transformation** on loot messages; it passes `arg1` directly into `ChatFrame:AddMessage`.
4. Therefore, any addon attempting to filter, clean, or condense roll chat **must intercept the message before or at `ChatFrame_OnEvent`**.

---

## 3. Group Loot Subsystem Deep Dive

### 3.1 Roll Frames
In `LootFrame.lua`:
- Roll dialogs remain `GroupLootFrame1`, `GroupLootFrame2`, `GroupLootFrame3`, `GroupLootFrame4`.
- Triggered by event `START_LOOT_ROLL` (`arg1` = rollID, `arg2` = rollTime).
- Cancelled by `CANCEL_LOOT_ROLL` (`arg1` = rollID).
- Roll timer bar continuously updates via `GetLootRollTimeLeft(rollID)`.

### 3.2 Master Loot Customization
OctoWoW replaces Blizzard's numbered raid group dropdown (Group 1, Group 2...) with class-grouped menus:
- Candidates are indexed into `GroupRoster[classToken]`.
- Candidates are displayed under class headers (`RAID_CLASS_COLORS[classToken]`) and sorted alphabetically.
- Offline members are detected and disabled via `IsRaidMemberOffline(player)`.

### 3.3 Deployed Loot GlobalStrings
In `GlobalStrings.lua`:
- Need: `LOOT_ROLL_NEED = "%s has selected Need for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Need Self: `LOOT_ROLL_NEED_SELF = "You have selected Need for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Greed: `LOOT_ROLL_GREED = "%s has selected Greed for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Greed Self: `LOOT_ROLL_GREED_SELF = "You have selected Greed for: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Pass: `LOOT_ROLL_PASSED = "%s passed on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Pass Self: `LOOT_ROLL_PASSED_SELF = "You passed on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Roll Result: `LOOT_ROLL_ROLLED = "%s rolls a %d on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Roll Result Self: `LOOT_ROLL_ROLLED_SELF = "You roll a %d on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Roll Need: `LOOT_ROLL_ROLLED_NEED = "Need Roll - %d for %s|Hitem:%d:%d:%d:%d|h[%s]|h%s by %s";`
- Roll Need Self: `LOOT_ROLL_ROLLED_NEED_SELF = "You roll a %d (Need) on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Roll Greed: `LOOT_ROLL_ROLLED_GREED = "Greed Roll - %d for %s|Hitem:%d:%d:%d:%d|h[%s]|h%s by %s";`
- Roll Greed Self: `LOOT_ROLL_ROLLED_GREED_SELF = "You roll a %d (Greed) on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Start: `LOOT_ROLL_START = "Rolling started on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- All Passed: `LOOT_ROLL_ALL_PASSED = "Everyone passed on: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Winner: `LOOT_ROLL_WON = "%s won: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Winner Self: `LOOT_ROLL_YOU_WON = "You won: %s|Hitem:%d:%d:%d:%d|h[%s]|h%s";`
- Condensed Winner Need: `LOOT_ROLL_WON_NO_SPAM_NEED = "%1$s won: %3$s|Hitem:%4$d:%5$d:%6$d:%7$d|h[%8$s]|h%9$s |cff818181(Need - %2$d)|r";`
- Condensed Winner Greed: `LOOT_ROLL_WON_NO_SPAM_GREED = "%1$s won: %3$s|Hitem:%4$d:%5$d:%6$d:%7$d|h[%8$s]|h%9$s |cff818181(Greed - %2$d)|r";`
- Condensed Winner Need Self: `LOOT_ROLL_YOU_WON_NO_SPAM_NEED = "You won: %2$s|Hitem:%3$d:%4$d:%5$d:%6$d|h[%7$s]|h%8$s |cff818181(Need - %1$d)|r";`
- Condensed Winner Greed Self: `LOOT_ROLL_YOU_WON_NO_SPAM_GREED = "You won: %2$s|Hitem:%3$d:%4$d:%5$d:%6$d|h[%7$s]|h%8$s |cff818181(Greed - %1$d)|r";`

---

## 4. Quest & Gossip Subsystem Deep Dive

### 4.1 UI Panel Slot Conflict
In `UIParent.lua`:
```lua
UIPanelWindows["GossipFrame"] = { area = "left", pushable = 0 };
UIPanelWindows["QuestFrame"]  = { area = "left", pushable = 0 };
```
Because both frames share slot `area = "left"` with `pushable = 0`, presenting `QuestFrame` **automatically hides `GossipFrame`**.

### 4.2 State Transition Architecture

```text
               +--------------------------------------+
               |           NPC Interaction            |
               +--------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v (Gossip text or options)                          v (Quests only)
  +--------------+                                    +--------------+
  | GOSSIP_SHOW  |                                    |QUEST_GREETING|
  +--------------+                                    +--------------+
         |                                                   |
         | Uses: C_GossipInfo.*                              | Uses: GetNumActiveQuests()
         | (has questID, gossipOptionID)                     |       GetActiveTitle(i)
         |                                                   |       GetNumAvailableQuests()
         |                                                   |       GetAvailableTitle(i)
         |                                                   | (Title strings only; NO questID!)
         | SelectGossipAvailableQuest(id)                    |
         | SelectGossipActiveQuest(id)                       | SelectActiveQuest(index)
         |                                                   | SelectAvailableQuest(index)
         +-------------------------+-------------------------+
                                   |
                                   v (Server response)
                       +-----------------------+
                       | QUEST_DETAIL (Accept) |
                       | QUEST_PROGRESS (Turn) |
                       +-----------------------+
                                   |
                                   v (Complete click)
                       +-----------------------+
                       |    QUEST_COMPLETE     |
                       | (GetQuestReward(...)) |
                       +-----------------------+
                                   |
                                   v
                       +-----------------------+
                       |    QUEST_FINISHED     |
                       |  (CloseQuest/Cleanup) |
                       +-----------------------+
```

### 4.3 Gossip vs Greeting API Contrast
1. **`GOSSIP_SHOW`**:
   - Deployed ClassicAPI exposes `C_GossipInfo`:
     - `C_GossipInfo.GetActiveQuests()` -> returns table with `.questID`, `.title`, `.isComplete`.
     - `C_GossipInfo.GetAvailableQuests()` -> returns table with `.questID`, `.title`.
     - `C_GossipInfo.GetOptions()` -> returns table with `.gossipOptionID`, `.name`.
   - Native legacy APIs `GetGossipAvailableQuests()` and `GetGossipActiveQuests()` return title/level pairs, but **no questID**.
2. **`QUEST_GREETING`**:
   - Used when an NPC offers direct quest selections without a gossip dialog.
   - **`C_GossipInfo` data is NOT populated during `QUEST_GREETING`**; `C_GossipInfo.GetAvailableQuests()` returns an empty table.
   - FrameXML and addons must use legacy native APIs: `GetNumActiveQuests()`, `GetActiveTitle(i)`, `SelectActiveQuest(i)`, `GetNumAvailableQuests()`, `GetAvailableTitle(i)`, `SelectAvailableQuest(i)`.
   - These native greeting calls do not supply a quest ID. That does not prove
     that no enhanced accessor could exist. When no verified ID accessor covers
     this dialog, use exact, officially verified titles and distinguish similar quests.

### 4.4 Transition Session Handover
When `SelectGossipAvailableQuest` or `SelectGossipActiveQuest` is called:
- The server causes `GossipFrame` to close, firing `GOSSIP_CLOSED`.
- Asynchronously, `QUEST_DETAIL` or `QUEST_PROGRESS` fires and opens `QuestFrame`.
- Do not treat the old panel's closure as proof that the selected quest
  transaction ended. Preserve explicit handoff ownership across the transition
  and invalidate stale callbacks. A bounded timeout may provide cleanup, but
  AutoLazy's 0.5-second choice is not a universal engine timing guarantee;
  packet ordering and pacing still require runtime verification.

---

## 5. OctoWoW Custom Subsystems in FrameXML

1. **Wide Quest Log**:
   - `QuestLogFrame` is rebuilt as a dual-pane frame (`area = "doublewide"`, `width = 690`) in `patch-5.mpq`.
   - Built-in quest level display and tracking checkboxes.
2. **Looking For Team (`LFT`)**:
   - In `Interface\FrameXML\LFT\LFT.lua` (57,813 bytes).
   - In-game automated group finder with role selection and dungeon queue tracking.
3. **OctoCalendar**:
   - In `Interface\FrameXML\OctoCalendar\` (49,003 bytes core).
   - Event creation, guild event permissions, holiday announcements, and event mail reminders.
4. **All-In-One (`AIO`) Framework**:
   - In `Interface\FrameXML\AIO\AIO.lua` (44,598 bytes).
   - Server-to-client UI synchronization pipeline with embedded `Smallfolk` serializer, `lualzw` compression, and message queue.
5. **Turtle Shop UI**:
   - In `Interface\FrameXML\Turtle_ShopUI\`.
   - Custom in-game donation/cosmetic rewards browser with model preview.
6. **War Mode System**:
   - In `OctoWarModeOffer` and `OctoWowWarModeConfirm`.
   - World PvP bonus XP toggle and confirmation UI.

---

## 6. Minimap integration evidence (2026-10-04)

Targeted read-only MPQ inspection confirms the following deployed source files;
this is not a new full native-stack audit. `FrameXML.toc` still matches the
baseline SHA256 above and loads `OctoRadioPlaceholder\OctoRadioPlaceholder.lua`.

| Source | Archive | SHA256 |
| --- | --- | --- |
| `OctoRadioPlaceholder\OctoRadioPlaceholder.lua` | `patch-5.mpq` | `db1042b3cb989084b6704f22763af1f19862d3a9de30665ac18a17c694a666cf` |
| `LFT\LFT.lua` | `patch-5.mpq` | `ba562c02687de7f8d87f45a989e80e42fa73ef212a65ceca202dd88f7dffd4ce` |
| `LFT\LFT.xml` | `patch-4.mpq` | `5de2be9961ec0e6afdf5ed4eac607b1d337740b2607c7ad8040951bf11e26fa2` |
| `Minimap.lua` | `patch-4.mpq` | `d2b752df8cfa8dcd64ce95020ca315efaa0d5cb30504fbf6dd724414f2357ecd` |
| `UIDropDownMenu.lua` | `patch-4.mpq` | `847cdae056abd6897e3919f716eac7007a0c232981be4acf1e1d40b1912ccc0c` |

[SOURCE-VERIFIED] OctoRadio uses `EBC_Minimap`, supplied by the base radio addon.
It replaces that button's click/tooltip scripts (lines 428-436), anchors the
`UIParent`-owned `OctoRadioMenu` to it (lines 322-334), and suppresses the legacy
`EBCMinimapDropdown` (lines 409-413). Do not replace these deployed handlers with
assumed upstream radio behavior or discover its menu as another launcher.

[SOURCE-VERIFIED] `LFTMinimapButton` is parented to `Minimap` in the deployed XML.
LFT installs/removes its own eye-animation `OnUpdate` handler and has native
tooltip/menu paths. Hiding or relocating its launcher must preserve those paths;
do not unregister LFT events or replace its scripts to suppress an icon.

[UNVERIFIED - TEST FIRST] AutoLazy's development report described an Error #132
after minimap child enumeration near context-menu use. The reported native
address and dangling-pointer explanation were not independently reproduced or
established by this inspection. Keep the precaution for this deployment: do not
use `Minimap:GetChildren()` or engine-wide frame enumeration for launcher
discovery. `pcall` and a userdata/type check do not validate a native pointer's
lifetime or recover from a native access violation. This report is not a claim
that every `GetChildren()` call on every frame is unsafe.

AutoLazy now uses lifecycle discovery, incremental creation observation and
explicit registration, preserving foreign parents. Its Lua tests cannot prove
native safety, input ordering, full discovery coverage or actual CPU/GPU cost.
The [addon reconciliation](OCTOWOW_ADDON_IMPACT_MATRIX.md#2-autolazy-v100-reconciliation-2026-10-04)
records implementation, prior model tests and release evidence separately.
