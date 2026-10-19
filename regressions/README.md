# Installed-addon regressions

These tests preserve repaired behavior outside the game folder. They read the
selected installed addon; they do not contain a second addon checkout or install
anything. The core framework tests under `tests/` remain independent of a game
installation. Addon-specific replays require Python and `lupa` with `lupa.lua51`.

Run from VanillaForge, replacing the addon path with the maintained checkout:

```text
python -B tools/audit_addon.py "<AddOns>/FostercareAuras" --run-tests --test-start regressions/FostercareAuras --output .private/auras-current.json
```

The audit runner supplies `VANILLAFORGE_ADDON_ROOT` to the test process and records
the selected source path, exact command and nonzero test count. Tests fail when
run directly without that source selection. For direct unittest execution, set
that environment variable explicitly. A test suite must actually use the supplied
path; setting an environment variable alone cannot verify an unrelated harness.

Use `--compare <previous-audit.json>` to list changed, added, removed and identical
loaded modules and load-graph changes. Preserve the previous report. Matching
source supports selective reuse of earlier review; it does not transfer review
approval or establish matching DLLs, settings, test coverage or native behavior.

## FostercareAuras

Eleven actual-source regressions cover bag changes with an intervening snapshot,
equipment/bag ordering, 200-event invalidation bursts, reentrant ability/aura/custom
evaluation, ongoing slides, removed frames and foreign global state. Six delivery
and three slide tests fail the preceding installed source for the intended defects.
The other two tests preserve existing slide and deferred-reflow behavior.

The harness executes complete selected Lua function/event bodies with explicit
state and widget mocks. It uses Lua 5.1 and does not prove WoW Lua 5.0/native widget
semantics, appearance, frame times or gameplay. Native acceptance stays with the
[current runtime checklist](../audit/OCTOWOW_RUNTIME_VERIFICATION.md#current-acceptance-pass-2026-10-12).

## MikScrollingBattleText

Ten regressions cover the six [MSBT audit](../audit/MSBT_2026-10-12_AUDIT.md)
findings repaired in MSBT 1.0.1: aura stack decreases (F1), Notification row font
owner (F2), disabled-state game-damage CVar (F3), color-picker profile ownership
(F4), external 0-255 message colors through the installed BigWigs caller (F5) and
the mana-gain baseline on enable (F6). Eight fail on the preceding installed
source; two picker controls pass on both. They reuse the audit replay harness, so
the client's MPQs must be readable and the adjacent BigWigs checkout present:

```text
python -B tools/audit_addon.py "<AddOns>/MikScrollingBattleText" --run-tests --test-start regressions/MikScrollingBattleText --output .private/msbt-current.json
```

The audit reproductions in `audit/replays/msbt-2026-10-12` now fail by design on
1.0.1; they remain historical demonstrations of the defects.
## FostercareTweaks

Eighteen regressions cover the 2026-10-19 private audit
repairs in FostercareTweaks 1.3.1.
- P2-1: the raid buff switches on a profile with no saved count.
- P2-2: suppressing and restoring Blizzard frames. Native event sets are taken from
  the deployed FrameXML OnLoad code.
- P3-1 to P3-4: operation counts for raid and modern-frame text, badge geometry and
  player aura rescans.
- P3-5 and P3-6: castbar and reagent fan-out.

Fourteen fail on the 1.3.0 source for the intended reason. The other four are
controls that pass on both. They run complete selected functions or module files
with counting widget mocks, under Lua 5.1. They do not prove native widget
behavior, real event payloads or frame times.

```text
python -B tools/audit_addon.py "<AddOns>/FostercareTweaks" --run-tests --test-start regressions/FostercareTweaks --output .private/fct-current.json
```
