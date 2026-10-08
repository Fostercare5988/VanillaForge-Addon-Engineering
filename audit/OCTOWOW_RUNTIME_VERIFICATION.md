# OctoWoW Runtime Verification Checklist

> **Bounded In-Game Verification Requirements (Post-Static Audit)**
> Focused client/server checks after static and Lua-model validation. These are
> verification scenarios, not a claim that the current addon has a known defect.

---

## 1. Minimal Runtime Verification Items

| Verification Item | Subsystem / Addon | Why Static Analysis Cannot Prove It | Recommended In-Game Verification Procedure |
| :--- | :--- | :--- | :--- |
| **1. Server Packet Rate Pacing on Repeatable Turn-Ins** | Quest Automation (`AutoLazy`) | Client FrameXML allows immediate consecutive calls to `SelectActiveQuest` and `CompleteQuest`, but server-side packet handlers on `play.octowow.st` may drop or reject turn-in requests submitted faster than network round-trip time. | Turn in a batch of 5+ repeatable items (e.g. Minion's Scourgestones or Argent Dawn tokens) using Shift-Click in AutoLazy; confirm server acknowledges all turn-ins without stalling or packet dropping. |
| **2. Condensed Roll Winner Chat Formatting** | Group Loot (`AutoLazy`) | Both standard winner strings (`LOOT_ROLL_WON`) and condensed roll strings (`LOOT_ROLL_WON_NO_SPAM_NEED` / `GREED`) are compiled into `GlobalStrings.lua`. The server determines which string template to fill and send over `CHAT_MSG_LOOT`. | Execute a dungeon or group roll with 2+ players rolling Need and Greed; observe whether chat displays the condensed format `Player won: [Item] (Need - 95)` or standard two-line output. |
| **3. Tel'Abim Banana NPC Dialog Execution** | Custom Content (`AutoLazy`) | The source supports gossip quest IDs and exact native greeting titles, but dialog selection and server responses require gameplay proof. | Manually accept the intended quest, then use Shift-click with its officially verified ingredients (the small rule uses 3x item 60954 and 1x item 11176). Verify selection/turn-in in the actual dialog; verify available quests remain manual and multiple reward choices behave as configured. |
| **4. Auction Query Pacing Boundary** | Native Stack (`AuctionQueryThrottle.dll`) | `AuctionQueryThrottle.dll` intercepts `QueryAuctionItems` at the binary level, but the exact delay window (e.g. 250ms vs 500ms) enforced before server disconnect depends on server antispam thresholds. | Perform a full auction scan with an auction addon; verify zero disconnects under heavy catalog queries. |
| **5. Minimap Ownership, Menus and Restoration** | Launcher integrations (`AutoLazy`, ItemRack, deployed Radio/LFT) | Lua regressions do not prove native pointer lifetimes, input ordering or rendering. Radio/LFT have client-owned handlers. | Open/close the tray repeatedly, including after normal minimap context-menu use; verify tooltips, left/right clicks and child menus. Exclude/re-include ItemRack, change an owner's normal setting while docked, and disable collapse; verify native position, visibility and layering return. Do not invoke unsafe enumeration to test the reported crash. |
| **6. Exact Loot Rules and Interaction Cost** | Group loot / tray (`AutoLazy`) | Direct IDs and Lua API-call counters establish modeled behavior, not real server outcomes or CPU/GPU timing. | Check a listed item in its configured dungeon, an unlisted item and a wrong-dungeon case; confirm ordinary loot and winner lines remain visible. Check tray opening after delayed addon initialization and a zone transition. Describe responsiveness observationally unless actual client profiling was performed. |
