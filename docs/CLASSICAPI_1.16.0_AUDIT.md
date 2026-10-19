# ClassicAPI v1.16.0 integration audit

Date: 2026-10-19. User-requested framework baseline refresh and shared addon support floor.

## Provenance

- Official release: <https://github.com/brues-code/ClassicAPI/releases/tag/v1.16.0>
- Complete comparison: <https://github.com/brues-code/ClassicAPI/compare/v1.15.16...v1.16.0>
- Published 2026-10-18T22:18:18Z. Annotated tag object `65d499000ddb6d11e1eda15b463aaeb13f92e67e` points to commit `99de63755bdc368cf8d35ce3a09dc46dafc20930`.
- GitHub reports the commit signature verified. The annotated tag itself is unsigned; local verification could not establish the signer because the public key is unavailable.
- Release DLL asset 654614703: 1,512,448 bytes; SHA-256 `ae88fc0461b58eff37171e10015ddaf8c27b1f428794c4ff927429389fc2535b`.
- Downloaded DLL bytes matched the published size and SHA-256 before installation.
- Official README blob `52363d11d206393ce96fe4a9a21b1703ee885eab`; `docs/API.md` blob `f29534e77618bc68a0286f781202b156ea66fb19`.
- The full range contains 49 commits and changes 129 files (+11,911 / -4,394 lines). The release notes are not the complete change list; the comparison and tagged source were reviewed.
- On 19 October, `check_upstream.py` found default branch `master` six commits ahead at `fdae686cc9f32ea231b830dba3b54aab2b3b9b52`. Those later commits add event-trace arguments, chat sender/line IDs, XML template lists and frame IDs, XML `<Cooldown>`, and console features. They are untagged follow-up work and are deliberately excluded from this v1.16.0 baseline.

## Change summary

The release adds broad 4.3.4-era API and behavior coverage. Material API additions include:

- `C_QuestLog.GetInfo` and `C_QuestLog.GetQuestLogTitle`; the latter supplies the quest completion value and full modern-style row tuple. `GetInfo` returns row metadata but does not report completion.
- Native `CreateFrame("Cooldown")` frames with `SetCooldown`, `SetReverse` / `GetReverse`, and `SetDrawEdge` / `GetDrawEdge`. The API reference explicitly says reverse and edge flags are stored but do not alter the rendered sweep, and XML cannot create this type.
- `GameTooltip:AddTexture`, full/spell/quest hyperlink support, tooltip item/spell/game-object accessors, and frame-stack display.
- Macro functions `GetMacroInfo`, `EditMacro`, `PickupMacro`, and `DeleteMacro` accept names as well as indexes. Unknown names yield nils for `GetMacroInfo`, a no-op for pickup/delete, and the first empty slot (or 0) from `EditMacro`.
- `string.trim`, `string.join`, additional Lua 5.1 coroutine support, and shared string metatable behavior.
- Addon XML handler argument support, script argument forwarding, frame attributes, more modern click/key binding behavior, and additional targeting/binding APIs.

Behavioral and engine fixes include child frame-level propagation, effective alpha multiplication, ScrollFrame child clipping, frame clamping, corrected `HookScript` argument forwarding, `hooksecurefunc` semantics aligned to 4.3.4, tooltip hyperlink handling, relative XML script paths, and add-on index rebuilding on reload. Other fixes cover unit/nameplate events and lookup performance, chat bubble positioning, inline-icon layout, quest log behavior, CVar results, and several initialization/compatibility edge cases. See the complete comparison for every commit.

No local in-game runtime claim is made for these APIs or behavior changes.

## VanillaForge policy and deployment

- VanillaForge reference and environment baseline advance to ClassicAPI v1.16.0+.
- The maintainer explicitly sets v1.16.0+ as the common minimum for all 16 maintained addon repositories. This is a support policy, not a claim that every addon consumes a v1.16.0 API.
- All 16 TOCs now carry `X-ClassicAPI-Min-Version: 1.16.0`, declare `!!!ClassicAPI`, and include a startup version guard at `11600` (existing guard or new `ClassicAPIRequirement.lua`). Their READMEs and installation requirements were updated as well.
- No addon feature refactors were performed. Package versions remain unchanged.
- The installed `ClassicAPI.dll` in `C:\Users\Fostercare\Desktop\client-2026-10-10` matches the published v1.16.0 asset hash. The prior v1.15.16 DLL is retained outside the game at `VanillaForge\\.private\\ClassicAPI-v1.16.0-upgrade-2026-10-19\\ClassicAPI-v1.15.16.dll` with its original hash verified.
- No game process was running during installation. The replacement must be loaded by a full client restart; `/reload` is insufficient. In-game load and addon startup guards remain unverified.

## Portfolio capability-displacement review

This is a source search for bounded follow-up work, not authorization to refactor addon behavior.

| Addon / area | Current mechanism | v1.16.0 candidate | Classification and follow-up |
| --- | --- | --- | --- |
| ActionBarProfiles | Macro APIs are called with indexes | Macro functions now also accept names | Review whether name-based profile lookup can simplify a concrete path while preserving slot selection and pickup behavior. Runtime validation required; no dependency change. |
| AtlasLoot search | Local `strtrim` helper | `string.trim` | Candidate for comparison; retain until whitespace and invalid-input semantics are checked against current helper. |
| FostercareTweaks, GearRack, FostercareAuras, AutoLazy, AtlasLoot/BigWigs libraries | Existing `hooksecurefunc` / `HookScript` call sites | Argument and post-call semantics are clarified/aligned with 4.3.4 | Audit call-site expectations during the next addon review; source release alone does not prove existing code needs changes. |
| FostercareTweaks cooldown numbers | Hooks `CooldownFrame_SetTimer` to render its own numeric labels | Native Cooldown frame supplies a sweep | RETAIN for now: the native sweep does not provide the addon's numeric label behavior. Possible use for a separately created sweep needs a distinct requirement. |
| Quest, tooltip, clamp, inline-icon, and XML additions | No confirmed direct maintained-addon overlap in the scoped search | New API surface | No confirmed displacement candidate; re-search if addon work touches these responsibilities. |

No obsolete workaround or provider DLL was removed in this baseline update. No `KNOWN_PATTERNS.md` change is needed.

## Changed-source references

| Source | v1.16.0 blob / reference | Review |
| --- | --- | --- |
| `README.md` | `52363d11d206393ce96fe4a9a21b1703ee885eab` | Release overview and API index |
| `docs/API.md` | `f29534e77618bc68a0286f781202b156ea66fb19` | Signatures, return contracts and behavior notes. In this tag, Cooldown is Lua-created; later master adds XML `<Cooldown>`. |
| DLL | Asset 654614703; 1,512,448 bytes; SHA above | Downloaded bytes matched asset digest |

## Validation

Framework metadata and README audit index were updated for v1.16.0. Every maintained addon's TOC, README and runtime guard were reconciled to the shared minimum. Static and framework checks are recorded in the task result. Native runtime behavior and first-launch guard behavior remain unverified until the client is restarted and tested in-game.
