# OctoWoW

## Identity

- Realmlist: `play.octowow.st` (realms C'Thun, N'Zoth, Y'Shaarj)
- Website: https://octowow.st/
- Server patch: custom 1.18.1 content on the 1.12.1 client (build 5875, Interface 11200)
- Client distribution: revision 2026.10.31 (patch-4, patch-5 and patch-O dated
  2026-10-31; the previous revision was 2026.10.10, listed on 15 October 2026),
  started through `VanillaFixes.exe` with DXVK
- Language: English (enUS) only

## Where game data comes from

1. In game: `/run` checks against the live client and server.
2. The OctoWoW database: https://octowow.st/db/ (items, spells, NPCs, quests).
3. The official client change list: https://octowow.st/client-interface-improvements

Do not trust for this server:

- **Turtle WoW data.** OctoWoW shares some ancestry, but that proves neither its
  content nor its IDs.
- **Blizzard Classic, Classic Era, Season of Discovery and Wowhead.** A later
  client, with different spells, items, numbers and rules.
- Third-party addon catalogs and spell tables. They are leads to check, not facts.

## Known differences from stock 1.12

- The client adds a larger quest log, a calendar, a profession UI and a group
  finder, among other changes (official change list). These show which UI
  surfaces exist, not their function names or signatures. **Unverified** beyond that.
- Battleground rules, spells, items and talents may differ from vanilla 1.12.
  Check every number against the database or in game.
- Source-verified 2026-11-01 (client FrameXML, patch-4.mpq, via
  `tools/extract_framexml.py`): the world map has a windowed mode. The map's
  minimize and maximize buttons call `WorldMapFrame_Minimize`/`_Maximize`
  (detail scale 0.7, draggable, Escape closes), and the choice is saved per
  account as `WORLDMAP_WINDOWED` (`RegisterForSave`).

## Facts learned while building addons

- 2026-10-21, measured in play: a battleground invite runs out after about
  80 seconds (one ran out at 79 s). AutoBG auto-enter tops out at 78 seconds.
- 2026-10-21, confirmed in play on Y'Shaarj: an Arathi Basin base takes 60 seconds
  to capture, an Alterac Valley tower or graveyard 5 minutes, and a Warsong Gulch
  flag returns 23 seconds after a capture. Every PvP trinket has a 3-minute cooldown.
- 2026-10-26, confirmed by the player: an Alterac Valley mine timer of 5 minutes
  from "The <faction> has taken the <mine>! Its supplies will now be used for
  reinforcements!" (as BigWigs counts it) is right on OctoWoW.
- 2026-10-21, from the database: the PvP trinket spells are 52317 (Insignia, all
  crowd control) and 5579, 23273, 23274, 23276, 23277 (the Immune ... effects).
  10793, 10795 and 10796 are mounts; 8342 is Defibrillate; 23133 and 23134 are
  engineering summons; 32612 does not exist. Vanish casts 1856/1857 apply auras
  11327/11329.
- 2026-10-27, seen in AutoBG's saved Spy stats: battlegrounds are cross-realm and
  name players from another realm "Name-Realm" ("Mayve-NZ" in Alterac Valley).
  Name matching must handle the suffix.
- 2026-11-13, seen in play: on a Cross-Faction battleground a teammate of the
  other faction showed in AutoBG's enemy list, so on mixed teams your faction is
  not the side you play on. Which side that is shows in the match (a group
  member carrying a flag or claiming a base); AutoBG learns it there
  (`AutoBG_MySide`). Unverified: whether `UnitFactionGroup("player")` or the
  scoreboard's faction column follow the side or the real faction.
- Source-verified 2026-11-13 (client FrameXML BattlefieldFrame.lua:325): the
  client knows an invite's time left, `GetBattlefieldPortExpiration(i)` in ms,
  so the ~80 s invite window is only the slider's bound, not a timing rule.
- 2026-11-14, from the database (?spells=-4, Racial Traits): the racials used in
  a fight and their cooldowns. Perception 20600 180 s, Stoneform 20594 180 s,
  Shadowmeld 20580 60 s, Escape Artist 20589 90 s, Blood Fury 20572 120 s, Will
  of the Forsaken 7744 150 s, War Stomp 20549 150 s, Berserking 20554, 26296,
  26297 (by power type) 180 s. Shadowmeld, War Stomp and Will of the Forsaken
  differ from vanilla. Custom: Spiritwalk 52926 (racial, 180 s, 12 s invisible;
  race not stated).
- Unverified: one spirit healer wave every 30 seconds for the whole
  battleground (as on MaNGOS cores). AutoBG's respawn bar and its dead enemy
  rows count to it.
- Unverified: Arathi Basin resource ticks. AutoBG learns what each base count
  earns from the score in play (`AutoBG_Settings.ABTicks`) and uses the vanilla
  ticks, marked `~`, until then.
- Source-verified 2026-11-03 (client 2026.10.31 FrameXML): the battlemaster window
  lists two reserved instance numbers after First Available, `OCTO_BG_ROW_XF_ID`
  9001 (Cross-Faction) and `OCTO_BG_ROW_FX_ID` 9002 (Factioned); a pick is joined
  by its list index, and the queue status reports the number (9000 labels First
  Available). `OctoBGQueueName(map, id)` names the queue. The client announces it
  can draw them with ".owl caps 1" at each loading screen. Arenas
  (Turtle_ArenaUI.lua, unchanged since 2026.10.10): `JoinArenaQueue(0)` Skirmish,
  1-3 Rated 2v2/3v3/5v5, `LeaveArenaQueue()`; one arena queue at a time, status
  map `ARENA`. New `OctoBGQueueCounts`: queue counts on the minimap tooltip,
  hardcore realm only (CHAT_MSG_ADDON prefix OCTO_BGQ).
