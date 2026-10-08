# VanillaForge Decision Log

Record durable framework-level decisions whose rationale would otherwise be lost. This is not a changelog, chat transcript or addon diary.

## Format
```text
## YYYY-MM-DD — Decision
Status: ACTIVE | SUPERSEDED
Decision:
Reason:
Evidence:
Consequences:
Supersedes: <optional>
```

## 2026-09-16 — Framework knowledge is repository-owned
Status: ACTIVE

Decision: VanillaForge repository files are the durable engineering source of truth. AI chat history is supporting context, not required state.

Reason: Agents, providers and sessions change. A repository contract is portable.

Evidence: The [contract's learning policy](../VANILLAFORGE_SYSTEM_PROMPT.md#framework-learning) establishes repository reference separation; `AGENTS.md` supplies the entry point.

Consequences: Fresh agents enter through `AGENTS.md` and retrieve canonical references selectively.

## 2026-09-16 — Agent learning is review-gated
Status: ACTIVE

Decision: Retrospectives may propose framework lessons but agents do not automatically rewrite VanillaForge from individual task experience.

Reason: One-off incidents and false correlations make poor universal rules.

Evidence: The [learning policy](../VANILLAFORGE_SYSTEM_PROMPT.md#framework-learning) governs deliberate framework maintenance and lesson promotion.

Consequences: Lessons pass generality, evidence, recurrence, importance and duplication review before promotion.

## 2026-09-16 — Retrieval beats mandatory context loading
Status: ACTIVE

Decision: Companion references are loaded when relevant rather than injected into every task.

Reason: Large fixed context costs more and may over-constrain exploration.

Evidence: The [learning policy](../VANILLAFORGE_SYSTEM_PROMPT.md#framework-learning) requires selective reference retrieval.

Consequences: `AGENTS.md` routes context; the system prompt is the active contract and detailed references are retrieved on demand.

## 2026-09-19 — Custom content provenance beats external inference
Status: ACTIVE

Decision: For server-specific or custom-content spell behavior, talents, and mechanics, agents must verify semantics against deployed client/server source files, local DBC/MPQ data, or in-client inspection rather than inferring from Retail or later-expansion databases.

Reason: Custom servers frequently rebalance, redesign, or introduce spells and talents sharing identical names or icons with Retail spells, but having completely different values, durations, or mechanics (e.g. Blackjack).

Evidence: The [evidence policy](../VANILLAFORGE_SYSTEM_PROMPT.md#evidence-and-apis) and `ENGINE_REFERENCE.md` §2 establish custom-content provenance.

Consequences: Agents do not assume custom content shares Retail/Wrath tuning based on matching spell names or icons; deployed data and DBC inspection take precedence.

## 2026-09-21 — Tone and Technical Neutrality
Status: ACTIVE

Decision: Prohibit unsubstantiated marketing superlatives (`enterprise-grade`, `zero-latency`, `zero-bloat`, `ultra-optimized`, `military-grade`, `best-in-class`), developer implementation meta-jargon in player UI, and progressive waiting ellipses (`...`) for discrete actions across public addon code and documentation.

Reason: Addon documentation and user-facing notifications must communicate verified, neutral engineering facts rather than speculative marketing hype or internal C++ engine plumbing details.

Evidence: The [UI policy](../VANILLAFORGE_SYSTEM_PROMPT.md#performance-and-ui) formalizes the standard; linter rules C14 (UI strings) and H9 (`README.md`) enforce marketing-language checks.

Consequences: Code reviews, agent prompts, and automated static scans reject marketing hyperbole and developer meta-jargon in favor of concise, technical descriptions.

## 2026-09-21 — Complete Upstream Snapshot Tracking and Audit Process
Status: ACTIVE

Decision: Track reference commits and file SHAs across all four enhanced-stack dependencies (`classicapi`, `superwow`, `nampower`, `unitxp_sp3`) in `UPSTREAM_VERSIONS.json`, and standardize upstream release audits using `agent/UPSTREAM_AUDIT_TEMPLATE.md`.

Reason: Eliminate unmonitored blind spots across upstream dependencies and ensure that upstream updates, header drift, or release provenance changes follow a disciplined, repeatable audit and reconciliation workflow.

Evidence: `UPSTREAM_VERSIONS.json` contains 40-character commit hashes and file SHAs for all tracked headers/docs; `tests/test_upstream_check.py` regression-tests the schema; `agent/UPSTREAM_AUDIT_TEMPLATE.md` provides the standardized audit procedure referenced by `AGENTS.md`, `README.md`, and `upstream-check.yml`.

Consequences: Upstream dependency drift alerts route directly to the audit template, keeping framework documentation and linter rules synchronized with verified upstream evidence.

## 2026-09-24 — Independent ownership across addon portfolios
Status: ACTIVE

Decision: Keep each addon responsible for a coherent feature area and its mutable state. Use narrow optional public contracts for cross-addon integration when independent installation is intended; extract shared code only when substantial repeated behavior justifies the dependency.

Reason: Shared engine APIs and small helper overlap do not establish shared state ownership. Hidden load-order and mutable-internal dependencies make otherwise independent addons fragile.

Evidence: Multi-addon reviews found narrow read-only integration queries and composable tooltip post-hooks. The [scope policy](../VANILLAFORGE_SYSTEM_PROMPT.md#scope-and-implementation) records state ownership boundaries.

Consequences: Architecture reviews identify the owner of each mutable state and verify optional integration without assuming another addon is installed or loaded first.

## 2026-09-27 — Widget-aware UI validation and modifier event ordering
Status: ACTIVE

Decision: Preserve native widget method boundaries in UI mocks and validate
settings entry/refresh/toggle/reset. Record ClassicAPI's modifier-event bitmap
ordering in its canonical API reference.

Evidence: A reported native Slider:Enable crash was reproduced when the addon
mock stopped supplying Button methods to Slider widgets. Archived 1.12.1
OptionsFrame.lua uses separate slider appearance helpers. ClassicAPI's pinned
Modifier.cpp updates its own bitmap and fires before engine key dispatch;
regressions reproduce missed Ctrl+Shift when a handler reads stale native state.

Promotion gate: Both observations are general, verified, likely to recur and
material to UI correctness. Existing API-verification guidance was insufficiently
specific about permissive mocks and this event's ordering. ENGINE_REFERENCE.md
§12.9, docs/WORKFLOW.md §6 and CLASSICAPI_MASTER_REFERENCE.md §75 are sufficient;
no new Known Pattern or speculative linter rule is needed. Lexical variable
names alone cannot safely establish a widget's type or event execution order.

Consequences: Agents verify widget types and input event timing rather than
using mock success as capability proof. In-game verification remains separate.

## 2026-10-01 — Upstream Capability Displacement Review
Status: ACTIVE

Decision: New or materially improved upstream capabilities must be systematically evaluated against existing mechanisms across the maintained addon portfolio before the upstream enhancement is considered fully exploited.

Reason: Without deliberate displacement review, addons accumulate historical dependencies, redundant workarounds, polling loops, and custom caches even after authoritative, superior primitives become available upstream.

Evidence: ClassicAPI, SuperWoW, NamPower, and UnitXP SP3 evolve continuously, frequently adding primitives (e.g. `UnitSpellHaste`, `C_Item`, `UnitInLineOfSight`) that render older provider queries or client-side workarounds obsolete.

Consequences: Upstream baseline adoption and addon modernization remain separate, bounded engineering phases. Every upstream release audit must populate a capability displacement review matrix. Verified replacements trigger bounded subsystem modernization, eliminating dead fallback branches and dropping unneeded DLL dependency declarations from individual addons without affecting the global client stack.

## 2026-10-04 — Reviewed addon polish lessons and deployed UI ownership
Status: ACTIVE

Decision: Refine canonical guidance for lifecycle discovery (KP-57), reversible
foreign-frame ownership (engine §12.11), official content identity, clear settings,
complete feature retirement and separate verification of downloadable releases.
Replace D1's unconditional recursion advice with frequency/safety guidance.

Evidence: AutoLazy v1.0.0 at `23b0d361a46d0b2f44eaaa91d506c7fa7c8d70da`
was inspected read-only. Its [reconciliation](../audit/OCTOWOW_ADDON_IMPACT_MATRIX.md#2-autolazy-v100-reconciliation-2026-10-04)
retains prior 102-model-test and public ZIP evidence; [dated MPQ evidence](../audit/OCTOWOW_FRAMEXML_CAPABILITIES.md#6-minimap-integration-evidence-2026-10-04)
records radio/LFT provenance and native uncertainty. ClassicAPI's pinned official
API documentation confirms roll identity independently of custom content.
The new D1 advice regression failed against old wording; all 57 framework tests
passed after correction. These are source/model results, not native safety proof.

Consequences: Generality, evidence, recurrence, importance and existing coverage
were reviewed. Addon catalogs/adapters stay with the addon; the reported native
crash theory remains a deployment precaution. Baselines and other addons were
unchanged. The separate lesson report was consolidated into these evidence owners.

## 2026-10-04 — Consolidate startup and improve existing knowledge first
Status: ACTIVE

Decision: Keep a small authoritative contract and routing-only entry point.
Give policy, procedures, technical details and dated evidence distinct owners.
Use one assistant-neutral starter. Review lessons through the existing
[retrospective](../agent/RETROSPECTIVE_TEMPLATE.md#framework-lesson), preferring
no change, refinement or retirement before a new reference.

Reason: Duplicated mandatory instructions increased context cost and obscured
where future corrections belonged. Self-improvement needs reviewed correction,
not an accumulating diary.

Evidence: The [documentation checker](../tools/check_framework_docs.py) and its
nine regression cases validate budgets and local links. The complete framework
suite passes all 66 tests; audit-index and diff checks also pass.

Consequences: The read-only documentation checker enforces startup word budgets
and checks local links in CI. Technical references remain uncapped. Ordinary addon
work proposes lessons; deliberate maintenance authorizes promotion. Historical
evidence keeps its original verification scope.

## 2026-10-05 — Review control usefulness before applying a theme
Status: ACTIVE

Decision: Refine existing settings guidance in KP-44 and the compact contract.
Retire the preferred theme's prescribed reset placement; styling does not
prescribe recovery features. Reuse current defaults and controls, prioritize
frequent tasks and add scoped recovery only for a demonstrated need.

Evidence: The user requested removal of GearRack's bulk weapon-show and broad
data-wipe actions after approving its theme and Bar layout. Source inspection
found a second legacy wipe route and permissive reset parsing. Retirement
regressions fail before removal and pass afterward. This is verified usability
feedback and source behavior, not a claim about every addon's reset needs.

Consequences: Existing supported controls remain subject to requested scope.
The lesson is general and likely to recur when menus are assembled from visual
templates. Existing feature-retirement guidance was sufficient; no new reference
or keyword-based linter rule was added. Startup/link checks and all 66 framework
tests pass using a writable workspace for test temporary files.

## 2026-10-08 — Complete performance passes and clean runtime/release boundaries
Status: ACTIVE

Decision: Refine existing patterns for burst fan-out, lifecycle and native UI
ownership. The workflow requires complete module dispositions and comparable
source-operation evidence. A read-only audit command gathers load closure,
hashes, review sites and scoped lint; explicit test execution remains separate
from human review and native performance verification.

Evidence: The private maintained collection's
`validation/ft-menu-bars-2026-10-08/mod-refresh-operation-counts.json` compares
actual before/after module source in identical Lua fixtures: 19 inspect callbacks
caused 361 link reads before coalescing and 19 afterward; 64 item completions
caused 64 bag refreshes before and one afterward. Eight lifecycle/ownership
regressions pass. GearRack's 12 new priority regressions cover repeated accepted
sets and exact item copies; six expose old-source defects. These are controlled
source results, not native timing or dungeon-freeze attribution.

Promotion review: The mechanisms are recurring, material and source-verified.
Existing guidance needed concrete fan-out, current-view, reentrancy and accepted
intent detail, so existing pattern owners were refined. Addon-specific numbers
and original evidence remain private. The audit command has a distinct recurring
purpose and regression coverage; lexical sites never become automatic defects.

Consequences: Clean public addons contain runtime files and player guides when
requested; private development evidence and useful recovery remain outside the
active game. Existing player settings survive, speculative migration scaffolding
is avoided, and required legal notices remain. The dated client baseline now
distinguishes its earlier snapshot from the current active installation.

## 2026-10-08 — Refresh ownership, pending metadata and reachable controls
Status: ACTIVE

Decision: Refine KP-11, KP-18, KP-44 and KP-51 in the existing known-pattern owner.
No new mandatory document, startup rule or lexical linter heuristic was added.

Evidence: FostercareTweaks' private `validation/ft-lead-audit-2026-10-08` retains
the actual before/after source, both-order event and pooled-member regressions,
negative-rarity/zero/pending-item completion cases and five-page bounds checks.
All 319 source tests pass; eleven new behavioral cases reject preceding source.
Comparable 40-member fixtures remove mark-event health/power/aura rescans and
halve the dimension-edit roster rebuild. CPU/GC samples include counted/light
instrumentation comparisons. Native appearance, input, PvP accuracy and frame
pacing remain unverified; source counts do not diagnose dungeon freezes.

Promotion review: Repeated owners can duplicate work even after each handler is
individually batched. Numeric unknown values and late metadata can invalidate a
cached decoration without an inventory event. Settings can be described but
unreachable or exceed UI-coordinate bounds. These are general, material,
source-verified mechanisms; existing patterns covered adjacent concerns but
needed these explicit counterexamples. The user authorized this promotion.
The addon retains its specific numbers/tests/recovery and release record.

Consequences: Prefer a narrow presentation path with current-owner invalidation;
exercise handler orders, zero/unknown values and late completion before claiming
an optimization is complete. Reuse the existing native-widget and old-source
regression workflow. Publication and native acceptance stay separate decisions.

## 2026-10-08 — Correct unsupported UnitXP command examples
Status: ACTIVE

Decision: Replace unverified historical examples in ENGINE_REFERENCE.md with
the pinned build-90 dispatcher's actual distance/sight and notification commands.
Remove UnitXP from the health-provider list and annotate the dated portfolio
matrix without recertifying unrelated addons.

Evidence: `dllmain.cpp` at `cedbf4b59776567db954ce38f681af1cbb9f0e1c`
implements distanceBetween/inSight and notify, with fallback to native UnitXP for
unrecognized commands. It has no health/maxhealth/distance/los command branches.
Current MSBT and AutoBG protected health probes are source observations for their
next bounded audits, not evidence that those APIs exist or that native cost was
measured. Startup/link checks and framework regressions cover this publication.
