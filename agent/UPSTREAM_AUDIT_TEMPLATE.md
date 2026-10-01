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

PORTFOLIO CAPABILITY DISPLACEMENT REVIEW:
For every new or materially changed public capability in the upstream release:
1. Responsibility & Provider Query:
   - What responsibility does this capability provide?
   - Do any maintained addons solve that responsibility through another mechanism?
   - Which provider or mechanism do they currently use?
   - Can the new primitive fully or partially replace it?
2. Target Mechanism Search:
   - older ClassicAPI mechanisms or multi-call patterns
   - NamPower APIs
   - UnitXP APIs
   - SuperWoW APIs
   - native Vanilla 1.12 workarounds
   - OnUpdate polling
   - string, tooltip, or combat-log parsing
   - duplicated state or custom Lua caches
   - custom reimplementations of upstream primitives
3. Displacement Classification:
   - REPLACE: new primitive is fully semantically equivalent/superior; existing mechanism should be retired.
   - RETAIN: existing provider/mechanism provides distinct, necessary semantics not matched by the new API.
   - PARTIAL REPLACEMENT: new primitive covers a subset; hybrid or specialized path remains necessary.
   - NO OVERLAP: no maintained addon exercises this responsibility.
   - RUNTIME VERIFICATION REQUIRED: semantic equivalence cannot be established from source alone.

Candidate Displacement Matrix:
| Addon | Responsibility | Current Mechanism | Provider | Candidate Replacement | Classification | Dependency Impact | Runtime Test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <addon> | <responsibility> | <call/pattern> | <provider> | <new primitive> | REPLACE / RETAIN / PARTIAL / NO OVERLAP / VERIFY | <dll removed or none> | <test plan or N/A> |

Candidate Detail:
- candidate: <addon> - <responsibility>
- semantic equivalence evidence: <source/docs citation>
- expected benefit: <correctness / determinism / performance / simplicity / dependency reduction>
- dependency impact: <removes provider DLL dependency from addon / no change>
- minimum version impact: <requires raising MIN_CLASSIC_API / unchanged>
- runtime validation required: <in-game test plan>
- NOTE: The upstream audit identifies and records candidates. Do NOT modify addon repositories during framework audit/refresh tasks unless explicitly commissioned.

RECONCILIATION & EXECUTION:
1. Synchronize reference documentation with source evidence.
2. Update UPSTREAM_VERSIONS.json (version, commit SHA, file SHAs, asset hashes).
3. For ClassicAPI, save the release audit as docs/CLASSICAPI_<reference_version>_AUDIT.md.
   Regenerate README's audit index: python tools/check_audit_index.py --write.
   Current/historical status is derived from JSON and audit filenames; preserve
   earlier source evidence rather than marking all older knowledge SUPERSEDED.
4. Update tools/vanillaforge_linter.py if machine-checkable rules changed.
5. Record portfolio capability displacement candidates for subsequent bounded addon tasks.
6. Run validation:
   - python -m unittest discover tests
   - python tools/check_audit_index.py
   - python tools/check_upstream.py --verbose
   - python tools/vanillaforge_linter.py <AddonPath>
7. If binary/DLL was upgraded in the game client, remind that /reload is insufficient;
   a full WoW.exe process restart is required (§15).

REPORT:
- upstream version drift summary
- documentation/reference updates made
- portfolio capability displacement candidates identified
- linter/framework changes made
- UPSTREAM_VERSIONS.json updated
- test & validation results
```

## Evidence Discipline
Never update framework documentation based on memory or modern retail assumptions. All upstream API additions must be verified against upstream source code, C++ headers (`.h`), official release notes, or empirical runtime testing with `/dump` and `/etrace`.
