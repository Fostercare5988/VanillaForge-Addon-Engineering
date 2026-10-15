# VanillaForge target environment

Start here to understand what VanillaForge requires. The full API references are
for specific engineering questions; they are not a startup reading assignment.

## Required client and DLL stack

The target is **OctoWoW client revision `2026.10.10`**, listed on the
[official site](https://octowow.st/) on 15 October 2026, using WoW
`1.12.1.5875` and Interface `11200`. The date identifies the OctoWoW distribution;
it does not change the underlying Lua/API generation. The expected server pointer
is `play.octowow.st`. A realmlist file establishes configuration, not a successful
connection to that server or a particular content revision.

**All four modern API DLLs are mandatory for VanillaForge users:** ClassicAPI,
SuperWoW, NamPower and UnitXP SP3. NamPower 4.6.2 and UnitXP SP3 v89 remain
supported. Prefer reviewed current stable releases. The
supported minimums and pinned upstream provenance live in
[UPSTREAM_VERSIONS.json](../UPSTREAM_VERSIONS.json); client/server identity and
required filenames live in [TARGET_ENVIRONMENT.json](../TARGET_ENVIRONMENT.json).
An addon guards the providers and capabilities it actually consumes. This keeps
its requirements honest while preserving the framework's required environment.
Reference releases 4.6.3 and 90 do not raise those supported minimums. Verify a
consumed API on the minimum build; any feature needing a newer build needs an
explicit capability/version requirement and a deliberate support decision.
TOC addon dependency fields do not install or load native DLLs. DXVK and
VanillaFixes are rendering/loader infrastructure, not Lua addon dependencies.

Two provenance details matter when interpreting "updated":

- NamPower's official `v4.6.3` release still reports runtime version `4.6.2`.
  The runtime number cannot distinguish these releases; use the published asset
  identity when a release-specific fix matters. Unreleased source fixes are
  separate from the published binary.
- The dated local UnitXP file and the official build-90 release have different
  hashes and sizes. A remembered build label does not establish release identity.
  ClassicAPI development builds may also publish a deliberately high version
  number. Use version, artifact/source provenance and consumed capabilities together.

See the [engine reference](../ENGINE_REFERENCE.md) for source pins and exact
runtime detection semantics. A newer upstream release is a review trigger, not
permission to invent its APIs or silently change supported minimums.

## Start an addon session

1. Identify the actual client root, launch path, selected server and addon source
   checkout. Record distribution revision evidence separately from engine version.
   A folder named `client-2026-10-10` is not proof of its contents. The personal
   paths in [dated installation evidence](../audit/OCTOWOW_CLIENT_BASELINE.md)
   are historical observations, not defaults for another computer.
2. Run the read-only file/configuration preflight. Keep output outside the game:

   ```text
   python -B tools/octowow_client_manifest.py --client "<client-root>" --check-environment --output "<private-client-report.json>"
   python -B tools/audit_addon.py "<client-root>/Interface/AddOns/<addon>" --client "<client-root>" --output "<private-addon-report.json>"
   ```

   Missing, old or unidentified requirements block the environment check.
   `checks_passed` concerns inspected files and configuration; runtime stays pending.
   For a complete client inventory, omit `--check-environment`. Archive hashing
   and scoped FrameXML inspection cost more than the lightweight preflight.
   For multiple TOC flavors, use the addon's audit `--toc <selected-file.toc>`;
   default discovery inventories all root TOCs and does not prove live selection.
3. Before relying on a native capability in game, verify the restarted session's
   provider versions/provenance, required functions, return shapes, relevant CVars
   and event payloads. DLL changes require a full client restart. Record results
   against that client and addon revision. A loader list, version global, old log
   or Lua mock alone cannot establish the whole stack's current runtime behavior.
4. Inspect the affected deployed FrameXML/DBC/MPQ files and relevant server data.
   Record source archive/path/hash and unresolved precedence or extraction gaps.
   Account for loose overrides and custom patches; a partial archive scan is not
   proof of the effective client UI. Test affected server interactions on that realm.

Source-only addon review remains useful when a game is unavailable. An audit
without `--client` explicitly leaves the environment unchecked; it must not be
reported as deployment or gameplay acceptance. Repository-only framework
maintenance needs no installed game or client download. Its tests use fixtures.

An unidentified DLL is an evidence gap, not a new minimum-version policy.
In particular, UnitXP v89 stays supported even when its binary lacks an ordinal
PE version or an available upstream digest. Establish its source/release identity
before accepting that environment; do not prescribe a v90 upgrade solely to make
the static checker green.

## Choose providers by the task

| Responsibility | First source to inspect | Boundary to verify |
| --- | --- | --- |
| Structured item, aura, gossip, spell, nameplate and timer APIs | [ClassicAPI reference](../CLASSICAPI_MASTER_REFERENCE.md) and pinned stable source | Exact return fields, lifecycle, callback mode, loaded version and per-function support |
| Extended unit/GUID behavior, combat and native hooks | SuperWoW sections of the [engine reference](../ENGINE_REFERENCE.md) | Overlapping globals and final registered implementation; presence of one shared global does not identify its provider |
| Structured combat/spell events, queueing and native unit/DBC queries | NamPower sections of the [engine reference](../ENGINE_REFERENCE.md) | Payload/flags, aura removal versus stack change, relevant CVars, published versus unreleased fixes |
| Native sight, distance, camera and notification commands | UnitXP sections of the [engine reference](../ENGINE_REFERENCE.md) | Exact command/subcommand support in the selected fork/build; unsupported names may fall through to original UnitXP |
| Client UI, widgets, scripts and custom server content | Selected client files and official OctoWoW data | Native 1.12 callback conventions, patched UI ownership, actual IDs/locales and server acknowledgements |

ClassicAPI and SuperWoW both register `UnitPosition` with different return shapes.
Confirm the active shape before unpacking values. Similarly, a DLL's support for
modern script arguments does not mean that mode is enabled. API choice follows
verified semantics and cost; installing all providers does not justify duplicate
queries, redundant caches, polling or compatibility fallbacks.

The official [client improvements](https://octowow.st/client-interface-improvements)
describe a larger quest log, calendar, profession UI and group finder, among other
changes. These identify integration surfaces, not executable signatures. Turtle
ancestry, later WoW databases and matching names/icons cannot certify OctoWoW
content IDs or packet behavior. Verify custom content against the official
[database](https://octowow.st/db/), applicable deployed data and runtime results.

## Keep evidence current

When the distribution, server, patches, loader settings or required DLLs change,
refresh affected evidence and repeat the relevant acceptance scenarios. Keep
source equality and environment equality separate. An unchanged addon hash does
not carry forward a previous native-runtime verdict.

Use [the workflow](WORKFLOW.md) for implementation and
[runtime verification](../audit/OCTOWOW_RUNTIME_VERIFICATION.md) for acceptance.
The historical audits remain useful within their recorded revision and scope.
