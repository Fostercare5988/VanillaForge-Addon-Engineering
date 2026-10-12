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
