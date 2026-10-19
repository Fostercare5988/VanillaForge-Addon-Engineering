# VanillaForge

Engineering guidance, API references, and validation tools for modernizing
OctoWoW addons on the enhanced World of Warcraft 1.12.1 client. Framework
version **3.1**.

Start with [AGENTS.md](AGENTS.md). The authoritative engineering contract is
[VANILLAFORGE_SYSTEM_PROMPT.md](VANILLAFORGE_SYSTEM_PROMPT.md); retrieve detailed
references only when the task needs them.

## Target

**WoW 1.12.1 · Build 5875 · Interface 11200**

| Component | Environment baseline |
| --- | --- |
| [ClassicAPI](https://github.com/brues-code/ClassicAPI) | v1.16.0+ (all maintained addons) |
| [SuperWoW](https://github.com/balakethelock/SuperWoW) | v2.2+ |
| [NamPower](https://github.com/Emyrk/nampower) | v4.6.2+ |
| [UnitXP SP3](https://github.com/brues-code/UnitXP_SP3) | v90+ |
| [DXVK](https://github.com/doitsujin/dxvk) / [VanillaFixes](https://github.com/hannesmann/vanillafixes) | Runtime / loader infrastructure |

Verify the active installation against this supported baseline. Every maintained
addon requires ClassicAPI v1.16.0+; other minimum versions follow the capabilities
each addon consumes.
DXVK is never a Lua API or addon dependency. Server content revisions do not
change the underlying client/API generation.

## Find what you need

| Question | Read |
| --- | --- |
| Start or resume an engineering task | [Agent bootstrap](docs/AGENT_BOOTSTRAP.md) |
| Implement or modernize an addon | [Workflow](docs/WORKFLOW.md) |
| Prepare or publish a release | [Release workflow](docs/RELEASE_WORKFLOW.md) |
| Find a ClassicAPI capability | [ClassicAPI reference](CLASSICAPI_MASTER_REFERENCE.md) |
| Check native extensions or FrameXML semantics | [Engine reference](ENGINE_REFERENCE.md) |
| Investigate a recurring hazard | [Known patterns](KNOWN_PATTERNS.md) |
| Inspect the deployed OctoWoW client | [Dated client baseline](audit/OCTOWOW_CLIENT_BASELINE.md) |
| Find maintained projects, current status and next priorities | [Current portfolio](audit/OCTOWOW_ADDON_IMPACT_MATRIX.md#current-portfolio--12-october-2026) |
| Review the fresh MSBT findings and reproduce them | [MSBT audit](audit/MSBT_2026-10-12_AUDIT.md) |
| Review reusable lessons | [Retrospective](agent/RETROSPECTIVE_TEMPLATE.md#framework-lesson) and [decision log](docs/DECISION_LOG.md) |
| Audit an upstream release | [Upstream audit template](agent/UPSTREAM_AUDIT_TEMPLATE.md) |

[Task](agent/TASK_TEMPLATE.md) and [review](agent/REVIEW_TEMPLATE.md) templates
support substantial work. Small fixes need only the relevant inspection and checks.

## Validate

Core Python tools use the standard library. From this repository:

```text
python -B tools/vanillaforge_linter.py "<addon-path>"
python -B tools/audit_addon.py "<addon-path>" --output "<private-report.json>"
python -B tools/check_audit_index.py
python -B tools/check_framework_docs.py
python -B -m unittest discover -s tests -p "test_*.py" -v
```

For a quick view of every installed Git project, without hashing game archives:

```text
python -B tools/octowow_client_manifest.py --addons-only --output .private/portfolio-status.json
```

Add `--verify-remotes` to read current origin branch heads over the network.
This does not fetch, commit or push. Cached tracking refs are labeled separately.
Use the full manifest command when DLLs, loader configuration or client patches
change. Reports must stay outside the active game directory.

The linter is heuristic. Tests and static checks do not establish in-game behavior;
report remaining runtime checks explicitly. Native DLL changes require a full
client restart; `/reload` reloads Lua, FrameXML, and addons.

The audit command collects loaded modules, hashes, candidate event/query/UI sites
and scoped lint in one report. Add `--run-tests` for local Python unittest suites.
Use `--test-start` for external tests; the runner passes the selected addon path
as `VANILLAFORGE_ADDON_ROOT`. The [installed-addon regressions](regressions/README.md)
keep behavioral replays outside runtime packages; those tests require `lupa`.
Add `--compare <previous-report.json>` to identify changed source/load graphs
without transferring previous review approval or overwriting its evidence.
It does not execute Lua, measure native cost or mark human review complete.
Use the [complete performance/polish pass](docs/WORKFLOW.md#complete-performance-and-polish-pass)
to turn that inventory into verified repairs. Keep reports and recovery outside
the active game; public addon packages contain runtime files and player guides.

## Maintain the knowledge

Improve the existing canonical owner before adding guidance. Preserve verified
evidence, retire superseded advice, and keep addon-specific facts with the addon.
Lesson promotion is deliberate framework maintenance, guided by the
[retrospective](agent/RETROSPECTIVE_TEMPLATE.md#framework-lesson).

[UPSTREAM_VERSIONS.json](UPSTREAM_VERSIONS.json) records reference versions and
source provenance. To check upstream drift (network access required):

```text
python -B tools/check_upstream.py
```

The current ClassicAPI audit is selected by `classicapi.reference_version`.
Historical audits retain evidence for older releases; consult them selectively.
After adding an audit or changing the reference version, regenerate its index:

```text
python -B tools/check_audit_index.py --write
python -B tools/check_audit_index.py
```

<!-- BEGIN CLASSICAPI AUDIT INDEX -->
<!-- Generated by tools/check_audit_index.py from UPSTREAM_VERSIONS.json and docs/CLASSICAPI_*_AUDIT.md. -->

| Audit | Status |
| --- | --- |
| [v1.16.0 audit](docs/CLASSICAPI_1.16.0_AUDIT.md) | Current reference |
| [v1.15.16 audit](docs/CLASSICAPI_1.15.16_AUDIT.md) | Historical release audit |
| [v1.15.15 audit](docs/CLASSICAPI_1.15.15_AUDIT.md) | Historical release audit |
| [v1.15.14 audit](docs/CLASSICAPI_1.15.14_AUDIT.md) | Historical release audit |
| [v1.15.13 audit](docs/CLASSICAPI_1.15.13_AUDIT.md) | Historical release audit |
| [v1.15.12 audit](docs/CLASSICAPI_1.15.12_AUDIT.md) | Historical release audit |

<!-- END CLASSICAPI AUDIT INDEX -->

Maintained by [Fostercare5988](https://github.com/Fostercare5988) at
[VanillaForge-Addon-Engineering](https://github.com/Fostercare5988/VanillaForge-Addon-Engineering).
