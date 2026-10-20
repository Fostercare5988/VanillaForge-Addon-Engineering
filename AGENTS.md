# VanillaForge Agent Entry Point

Read [CORE.md](CORE.md) at the start of every session. It is the default
working contract. Read the full [VANILLAFORGE_SYSTEM_PROMPT.md](VANILLAFORGE_SYSTEM_PROMPT.md)
only when asked for a Gate or Framework pass. Reread only if relevant context was
lost or changed.

Retrieve only what the task needs:

| Need | Reference |
| --- | --- |
| Required DLL stack and addon session start | [Target environment](docs/TARGET_ENVIRONMENT.md) |
| Local addon source and Git ownership | [Current installation correction](audit/OCTOWOW_CLIENT_BASELINE.md#current-installation-correction--19-october-2026) |
| Portfolio status and next work | [Portfolio record](audit/OCTOWOW_ADDON_IMPACT_MATRIX.md) (dated sections, newest first) |
| ClassicAPI capabilities | [API reference](CLASSICAPI_MASTER_REFERENCE.md) |
| SuperWoW, NamPower, UnitXP, DXVK, native UI | [Engine reference](ENGINE_REFERENCE.md) |
| Recurring hazards and solutions | [Known patterns](KNOWN_PATTERNS.md) |
| Broad addon work | [Workflow](docs/WORKFLOW.md) |
| Addon regression suites and how to run them | [Regression index](regressions/README.md#suite-index) |
| Release/reconciliation | [Release workflow](docs/RELEASE_WORKFLOW.md) |
| Reusable session starter | [Bootstrap](docs/AGENT_BOOTSTRAP.md) |
| Deployed OctoWoW evidence | [Dated baseline](audit/OCTOWOW_CLIENT_BASELINE.md), then relevant audit sections |

Use [TASK_TEMPLATE](agent/TASK_TEMPLATE.md) for substantial work,
[REVIEW_TEMPLATE](agent/REVIEW_TEMPLATE.md) for complex integration and
[UPSTREAM_AUDIT_TEMPLATE](agent/UPSTREAM_AUDIT_TEMPLATE.md) for upstream changes.
Scale procedure to scope; a focused fix does not require a full audit.

After substantial work, use the [retrospective](agent/RETROSPECTIVE_TEMPLATE.md)
to review notable lessons. Ordinary addon tasks propose lessons; authorized
framework maintenance reviews and promotes them. Refine existing canonical guidance
first. Run `python tools/check_framework_docs.py` when changing framework docs.
