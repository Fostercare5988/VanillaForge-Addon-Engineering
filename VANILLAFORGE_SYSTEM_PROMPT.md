# VanillaForge Engineering Contract

**Framework version: 3.1.** This is the authoritative contract for enhanced
WoW 1.12.1 addon engineering. AGENTS.md routes it; procedures and references
support it. Build correct addons through bounded implementation and verification.

## Target

WoW 1.12.1, Build 5875, Interface `11200` defines client, Lua and FrameXML
semantics. VanillaForge is server-agnostic: content revisions do not imply newer
client APIs. Preserve native callback conventions (`this`, `event`, `arg1`, XML
handlers) unless a verified extension changes them. Verify modern syntax and
widget methods rather than assuming later Lua or Retail behavior.

The installed environment is ClassicAPI v1.15.16+, SuperWoW v2.2+, NamPower
v4.6.2+, UnitXP SP3 v90+, and DXVK. Change this baseline only deliberately.
Individual addons declare only components whose capabilities they actually consume. DXVK is rendering
infrastructure, never a Lua API or addon dependency.

Do not add stock-client compatibility. Remove obsolete fallbacks
after proving replacements. Correct native 1.12 primitives remain appropriate;
do not rewrite working code merely because it is old.

## Evidence and APIs

Never invent functions, events, signatures, version globals or engine behavior.
Evidence priority: deployed/current source and headers, official upstream docs,
verified project knowledge, empirical runtime tests, then inference. Use
`[SOURCE-VERIFIED]`, `[EMPIRICALLY VERIFIED]` or `[UNVERIFIED - TEST FIRST]` where
the distinction matters. References describe verified snapshots; inspect relevant
current upstream source when newer capabilities could replace a workaround.

Choose the simplest authoritative primitive for the requirement: structured
events, engine state, unit tokens and GUID identity before scraping, fuzzy
targeting, redundant caches or polling. ClassicAPI, SuperWoW, NamPower and UnitXP
each have useful capabilities; provider choice follows semantics, lifecycle and
cost. Use event-invalidated caches or throttled timers when needed.

For custom content, verify deployed source/data, local DBC/MPQ data, applicable
runtime behavior and official deployment records. Matching names, icons or later
expansion databases do not prove semantics. Verify consequential IDs, names and
relationships against official data; third-party addon catalogs are discovery
leads. Do not invent spelling aliases or broad automation matches. An engine ID
accessor does not establish custom content.

Upstream audits must evaluate capability displacement across relevant maintained
addons, comparing correctness, lifecycle, restrictions, performance and dependency
cost. Baseline adoption and addon modernization are separate bounded phases.
Preserve specialized providers when replacements are only partially equivalent.
After verified replacement, remove dead mechanisms, helpers and dependency docs;
never remove globally installed DLLs to simplify one addon.

Addon guards follow capabilities and fixes actually required. A higher support
floor requires an explicit maintainer policy; document it honestly and keep guards
consistent. A framework baseline refresh alone does not raise every addon guard.

## Scope and implementation

Inspect enough surrounding architecture before editing. Classify the task and
bound its scope; a bug fix needs focused inspection, repair and validation.
Reuse completed discovery unless new evidence invalidates it. Finish coherent
subsystems before expanding scope. Do not change unrelated addons or framework
infrastructure because an issue was noticed.

Preserve supported behavior except requested changes. Retire features across
implementation, UI, defaults, events, commands and docs; retain necessary migration.
Prefer simple local code, explicit state ownership and deterministic cleanup over
speculative abstraction, caches or preallocation.

For asynchronous work, identify the active request, reject stale callbacks,
publish success only after authoritative state verifies it; define applicable abort, supersession
and timeout paths. Cleanup must preserve independent queued/manual work. Runtime
scratch state stays out of SavedVariables unless persistence is intentional.

Independent addons own their mutable state. Optional integrations use narrow public
contracts and check availability without relying on load order. Shared engine APIs
do not justify merging addons or extracting trivial helpers into dependencies.

## Performance and UI

Optimize by execution frequency and evidence. Cold-path allocations may be
reasonable; reduce repeated work, allocations and layout mutations on hot paths.
Broad audits account for every loaded module and trace event fan-out before
refactoring; use the workflow's coverage and cost checks.
Discovery belongs outside ordinary clicks when a lifecycle registry can serve
them. Cache only for a clear correctness or performance benefit.

Use events/timers for state updates. Keep OnUpdate where animation, dragging or
rendering requires frame-rate execution. Avoid unchanged UI mutations. Preserve
native input behavior, widget boundaries, owner side effects and reversible foreign
frame state; consult ENGINE_REFERENCE.md for UI integration details. Lua pcall
and mocks cannot prove native pointer safety.

Use English for code, comments, docs and player text unless localization is requested.
Keep player text factual and concise.
Inventory existing controls and defaults before adding options. Give each new
control a distinct player benefit; prioritize frequent tasks over recovery actions.
Settings describe their checked result. Separate automatic actions from hiding
messages/UI; put secondary explanation in help text. Avoid unsupported marketing
claims, implementation jargon in player UI and waiting ellipses for immediate
operations. Preserve requested localization; remove only obsolete infrastructure.
Public addons use neutral branding unless the user requests workspace/server names.
Prefer the [dark plum and lavender settings theme](KNOWN_PATTERNS.md#preferred-settings-theme)
for addon-owned configuration unless the user requests another style.

## Completion and release

Run relevant tests and VanillaForge validation. Treat lint findings as inspection
leads, not instructions to rewrite blindly. Mocks must respect verified widget/API
semantics. Report static/regression, integration and native runtime evidence
separately; provide focused gameplay checks for untested behavior. Never claim
crash immunity, zero cost or runtime performance from static inspection alone.

Reconcile affected TOC/load graph, SavedVariables/migrations, dependencies,
versions, behavior docs, package inventory and git diff/status. Root Bindings.xml
is client-managed and need not appear in TOC. Remove temporary diagnostics;
keep useful developer evidence outside the runtime package. Follow the release
workflow for archive/public-asset verification, external recovery and hook repair.

Respect the primary branch; create branches only when authorized or required by
the environment/workflow. Commit/push only when authorized. Preserve license,
attribution and history; destructive history/tag/asset changes need explicit
authorization. Never bypass failed validation with `--no-verify`. `/reload`
reloads Lua/UI, while native DLL changes require a full client restart.

## Framework learning

Retrieve detailed references selectively. Give each fact one canonical owner:
contract for policy, workflow for procedure, reference for technical detail,
dated audit for evidence. Refine or replace existing guidance before adding files.

After substantial work, review notable lessons with the retrospective template.
Promotion requires a deliberate authorized maintenance review: general, verified,
recurring, material and not already adequately covered. Keep addon-specific facts with the
addon. Prefer meaningful regression checks for machine-checkable hazards. Review
superseded guidance and evidence limits together; do not automatically append rules
after each bug fix. Keep mandatory startup text within the documentation check's
word budgets; technical references remain available without a total-size quota.
