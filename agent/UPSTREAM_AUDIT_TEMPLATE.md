# VanillaForge Upstream Audit Template

Use when an upstream enhanced-stack component (ClassicAPI, SuperWoW, NamPower, UnitXP SP3, DXVK) releases an update, drifts in commit/blob SHA, or requires reconciliation against VanillaForge contracts.

```text
UPSTREAM AUDIT:
component: ClassicAPI | SuperWoW | NamPower | UnitXP SP3 | DXVK
repository: <owner/repo>
trigger: check_upstream.py alert | manual release audit | user request

SNAPSHOT TRANSITION:
previous reference version: <version/tag>
previous reference commit: <sha>
new upstream version: <version/tag>
new upstream commit: <sha>
release date / tag object: <timestamp/tag>

UPSTREAM DRIFT ANALYSIS:
1. Source / Header Drift:
   - modified tracked files (e.g. docs/API.md, Vanilla1121_functions.h, SCRIPTS.md)
   - new API symbols / C_ namespace additions
   - deprecated or removed APIs
   - changed function signatures or return contracts
2. Behavioral / Runtime Fixes:
   - client bug fixes (FrameXML, C++ engine hooks, sound, rendering)
   - event payload changes or new event registrations
   - combat log / unit token / GUID handling fixes
3. Binary / Distribution Artifacts:
   - DLL asset name, size, SHA256
   - loader requirements (e.g. DXVK d3d9.dll, SuperWoW launcher)

VANILLAFORGE IMPACT ASSESSMENT:
1. Knowledge Base Drift:
   - CLASSICAPI_MASTER_REFERENCE.md updates required: YES / NO
   - ENGINE_REFERENCE.md updates required: YES / NO
   - KNOWN_PATTERNS.md updates required: YES / NO
2. Static Analysis / Linter Drift:
   - tools/vanillaforge_linter.py rule updates required: YES / NO
   - new anti-patterns or retired legacy workarounds:
3. Baseline Policy:
   - does framework minimum version advance? YES / NO
   - reason (mandatory capability vs. optional optimization):
4. Addon Ecosystem Impact:
   - affected addons in local workspace:
   - breaking changes identified:
   - obsolete 2006 workarounds made redundant:

RECONCILIATION & EXECUTION:
1. Synchronize reference documentation with source evidence.
2. Update UPSTREAM_VERSIONS.json (version, commit SHA, file SHAs, asset hashes).
3. Update tools/vanillaforge_linter.py if machine-checkable rules changed.
4. Run validation:
   - python -m unittest discover tests
   - python tools/check_upstream.py --verbose
   - python tools/vanillaforge_linter.py <AddonPath>
5. If binary/DLL was upgraded in the game client, remind that /reload is insufficient;
   a full WoW.exe process restart is required (§15).

REPORT:
- upstream version drift summary
- documentation/reference updates made
- linter/framework changes made
- UPSTREAM_VERSIONS.json updated
- test & validation results
```

## Evidence Discipline
Never update framework documentation based on memory or modern retail assumptions. All upstream API additions must be verified against upstream source code, C++ headers (`.h`), official release notes, or empirical runtime testing with `/dump` and `/etrace`.
