# OctoWoW Runtime Verification Checklist

> **Bounded In-Game Verification Requirements (Post-Static Audit)**
> Focused client/server checks after static and Lua-model validation. These are
> verification scenarios, not a claim that the current addon has a known defect.

---

## Current acceptance pass (2026-10-12)

Use only `client-2026-10-10` and record the addon commit/settings for each result.
The [current portfolio](OCTOWOW_ADDON_IMPACT_MATRIX.md#current-portfolio--12-october-2026) separates current publication and
source validation from these uncompleted native checks.

1. Fully restart after native DLL updates. Confirm the expected extension versions
   and active D3D9/Vulkan path in the new session; a file hash or loader list is
   insufficient.
2. Compare a repeatable route with the same scene, settings, addons and duration:
   town idle, crowded combat, loot/equipment bursts and a raid/battleground. Keep
   frame-time evidence and Lua profiling separate; investigate one owner at a time.
3. Enable FostercareNameplates deliberately and test repeated target changes,
   deaths/despawns and crowded plates. Check casts, text, scaling and toggles.
   Verify FostercareTweaks' target castbar independently.
4. Test AutoLazy's Shift-right-click against one selected repeatable quest,
   multiple rewards, repeated clicks, NPC changes, cancellation and delayed server
   replies. Confirm accepting a new quest stays manual.
5. Open/reopen FostercareAuras, import old/new formats, swap targets and equipment,
   then log out/in. Check appearance and settings persistence. Exercise BigWigs'
   manual version query and `/frbuff`, unresolved combat names and SuperAPI item
   charges when the relevant condition occurs.

6. For FostercareAuras 1.0.1-local, change bag contents/equipment in quick succession
   and confirm item trackers reach the final state. Show/hide grouped icons during
   an active slide, including removing an icon, then reopen the editor. Check
   final spacing and animation completion. Exercise any custom function that
   requests a condition refresh; verify its dependent tracker updates afterward.
   These repairs passed actual-source Lua regressions, not native gameplay.

These are pending acceptance scenarios, not assertions that a current defect
exists. Earlier rows below keep their original addon names and source scope.

## 1. Minimal Runtime Verification Items

| Verification Item | Subsystem / Addon | Why Static Analysis Cannot Prove It | Recommended In-Game Verification Procedure |
| :--- | :--- | :--- | :--- |
| **1. Server Packet Rate Pacing on Repeatable Turn-Ins** | Quest Automation (`AutoLazy`) | Client FrameXML allows immediate consecutive calls to `SelectActiveQuest` and `CompleteQuest`, but server-side packet handlers on `play.octowow.st` may drop or reject turn-in requests submitted faster than network round-trip time. | Turn in a batch of 5+ repeatable items (e.g. Minion's Scourgestones or Argent Dawn tokens) using Shift-Click in AutoLazy; confirm server acknowledges all turn-ins without stalling or packet dropping. |
| **2. Condensed Roll Winner Chat Formatting** | Group Loot (`AutoLazy`) | Both standard winner strings (`LOOT_ROLL_WON`) and condensed roll strings (`LOOT_ROLL_WON_NO_SPAM_NEED` / `GREED`) are compiled into `GlobalStrings.lua`. The server determines which string template to fill and send over `CHAT_MSG_LOOT`. | Execute a dungeon or group roll with 2+ players rolling Need and Greed; observe whether chat displays the condensed format `Player won: [Item] (Need - 95)` or standard two-line output. |
| **3. Tel'Abim Banana NPC Dialog Execution** | Custom Content (`AutoLazy`) | The source supports gossip quest IDs and exact native greeting titles, but dialog selection and server responses require gameplay proof. | Manually accept the intended quest, then use Shift-click with its officially verified ingredients (the small rule uses 3x item 60954 and 1x item 11176). Verify selection/turn-in in the actual dialog; verify available quests remain manual and multiple reward choices behave as configured. |
| **4. Auction Query Pacing Boundary** | Native Stack (`AuctionQueryThrottle.dll`) | `AuctionQueryThrottle.dll` intercepts `QueryAuctionItems` at the binary level, but the exact delay window (e.g. 250ms vs 500ms) enforced before server disconnect depends on server antispam thresholds. | Perform a full auction scan with an auction addon; verify zero disconnects under heavy catalog queries. |
| **5. Minimap Ownership, Menus and Restoration** | Launcher integrations (`AutoLazy`, ItemRack, deployed Radio/LFT) | Lua regressions do not prove native pointer lifetimes, input ordering or rendering. Radio/LFT have client-owned handlers. | Open/close the tray repeatedly, including after normal minimap context-menu use; verify tooltips, left/right clicks and child menus. Exclude/re-include ItemRack, change an owner's normal setting while docked, and disable collapse; verify native position, visibility and layering return. Do not invoke unsafe enumeration to test the reported crash. |
| **6. Exact Loot Rules and Interaction Cost** | Group loot / tray (`AutoLazy`) | Direct IDs and Lua API-call counters establish modeled behavior, not real server outcomes or CPU/GPU timing. | Check a listed item in its configured dungeon, an unlisted item and a wrong-dungeon case; confirm ordinary loot and winner lines remain visible. Check tray opening after delayed addon initialization and a zone transition. Describe responsiveness observationally unless actual client profiling was performed. |
