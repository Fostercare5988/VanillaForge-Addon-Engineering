# OctoWoW

## Identity

- Realmlist: `play.octowow.st` (realms C'Thun, N'Zoth, Y'Shaarj)
- Website: https://octowow.st/
- Server patch: custom 1.18.1 content on the 1.12.1 client (build 5875, Interface 11200)
- Client distribution: revision 2026.10.10, listed on the website on 15 October 2026,
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

## Facts learned while building addons

- 2026-10-21: how long a battleground invite stays open is **unverified**.
  AutoBG assumes at most 120 seconds, enters 5 seconds early, and saves a
  shorter window (`AutoBG_Settings.InviteWindow`) if an invite runs out.
