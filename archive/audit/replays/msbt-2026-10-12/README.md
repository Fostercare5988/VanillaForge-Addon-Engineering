# MSBT audit reproductions — 12 October 2026

These scripts reproduce the six defects and operation counts in the
[dated audit](../../MSBT_2026-10-12_AUDIT.md). They read installed addon source;
they do not patch addons, launch the game, change settings, or upload anything.

**A successful reproduction confirms existing faulty behavior. It is not a
passing desired-behavior regression or a claim that MSBT is fixed.** The audited
MSBT revision is `92bb79b2bbdf33eacf3610fe5eac5f35821e3421`. After repairs, convert
these observations to desired-behavior regressions before using them as a gate.

## Run

Requirements: Python, `lupa.lua51`, the selected installed MSBT checkout, the
adjacent installed BigWigs checkout, and the OctoWoW client's native Data archives.
The original audit used ClassicAPI 1.15.16, SuperWoW 2.2, NamPower 4.6.2, and
Interface 11200. This program mocks their Lua-facing methods; it does not load DLLs.

From VanillaForge:

```powershell
$env:VANILLAFORGE_ADDON_ROOT = '<client>\Interface\AddOns\MikScrollingBattleText'
python -B audit\replays\msbt-2026-10-12\audit_replays.py
python -B audit\replays\msbt-2026-10-12\inventory.py
python -B audit\replays\msbt-2026-10-12\extract_native.py
```

The source selection is required. `MSBT_AUDIT_SOURCE` is accepted as the original
local replay's alternative selector. Output defaults to
`.private/msbt-audit-current`; set `MSBT_AUDIT_OUTPUT` for another external folder.
Outputs inside the selected game directory are rejected. No private recovered
checkout or fixture directory is needed.

The native reference helper reads the selected client's MPQs in the manifest's
declared archive order. It extracts GlobalStrings layers and the relevant menu,
color-picker, panel, and widget-template references into temporary storage. Those
files are removed when Python exits; native source is not included in this Git
repository. JSON output records their source archives and SHA-256 identities.
This extraction order is a source fixture, not proof of runtime archive loading.

## Evidence and limits

- `audit_replays.py` executes the complete current MSBT Lua modules and actual
  button/checkbox callbacks, plus selected deployed color-picker callbacks and
  the installed BigWigs message handler. Assertions confirm the six recorded
  defects and relevant positive controls. It records unchanged source hashes.
- `inventory.py` discovers the current TOC/XML closure with VanillaForge's audit
  tool, compiles Lua/XML scripts in Lua 5.1, resolves addon callback names and
  checks addon media references. It does not certify native assets or appearance.
- `extract_native.py` records the extracted references' provenance without
  publishing Blizzard source or modifying the client.

The mock methods are explicit. The runner adapts Lua 5.0 generic table iteration
for execution in Lua 5.1. Widget allocation, pointer safety, native input/layout,
color clamping, actual combat payload delivery and frame times remain unverified.
The public reproductions do not include or replace the original 49-test local
baseline suite. See the audit for the exact distinction and in-game acceptance.

The recorded [results](../../evidence/msbt-2026-10-12/replay-results.json) preserve
the six failures and operation counts; [inventory](../../evidence/msbt-2026-10-12/inventory.json)
and [native provenance](../../evidence/msbt-2026-10-12/native-provenance.json)
record the publication replay's inputs. Local machine paths in snapshots use
placeholders; hashes and observed values are unchanged.
