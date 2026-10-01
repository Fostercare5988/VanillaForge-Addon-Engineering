# OctoWoW Runtime Verification Checklist

> **Bounded In-Game Verification Requirements (Post-Static Audit)**
> This document lists ONLY behaviors that cannot be mathematically or statically proven from client binaries, MPQs, and FrameXML.

---

## 1. Minimal Runtime Verification Items

| Verification Item | Subsystem / Addon | Why Static Analysis Cannot Prove It | Recommended In-Game Verification Procedure |
| :--- | :--- | :--- | :--- |
| **1. Server Packet Rate Pacing on Repeatable Turn-Ins** | Quest Automation (`AutoLazy`) | Client FrameXML allows immediate consecutive calls to `SelectActiveQuest` and `CompleteQuest`, but server-side packet handlers on `play.octowow.st` may drop or reject turn-in requests submitted faster than network round-trip time. | Turn in a batch of 5+ repeatable items (e.g. Minion's Scourgestones or Argent Dawn tokens) using Shift-Click in AutoLazy; confirm server acknowledges all turn-ins without stalling or packet dropping. |
| **2. Condensed Roll Winner Chat Formatting** | Group Loot (`AutoLazy`) | Both standard winner strings (`LOOT_ROLL_WON`) and condensed roll strings (`LOOT_ROLL_WON_NO_SPAM_NEED` / `GREED`) are compiled into `GlobalStrings.lua`. The server determines which string template to fill and send over `CHAT_MSG_LOOT`. | Execute a dungeon or group roll with 2+ players rolling Need and Greed; observe whether chat displays the condensed format `Player won: [Item] (Need - 95)` or standard two-line output. |
| **3. Tel'Abim Banana NPC Dialog Execution** | Custom Content (`AutoLazy`) | `AutoLazy.lua` now statically supports both `GOSSIP_SHOW` (exact `questID`) and `QUEST_GREETING` (exact normalized `questTitle`). In-game verification is only needed to observe which dialog frame the custom OctoWoW NPC opens and verify smooth single-click completion without UI hitching. | Interact with the Tel'Abim Banana NPC with 3 bananas + 1 elixir in inventory; verify automated selection and turn-in execute correctly in either dialog branch. |
| **4. Auction Query Pacing Boundary** | Native Stack (`AuctionQueryThrottle.dll`) | `AuctionQueryThrottle.dll` intercepts `QueryAuctionItems` at the binary level, but the exact delay window (e.g. 250ms vs 500ms) enforced before server disconnect depends on server antispam thresholds. | Perform a full auction scan with an auction addon; verify zero disconnects under heavy catalog queries. |
