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

Evidence: `VANILLAFORGE_SYSTEM_PROMPT.md` §18 establishes repository reference separation; `AGENTS.md` supplies the Agent Layer entry point.

Consequences: Fresh agents enter through `AGENTS.md` and retrieve canonical references selectively.

## 2026-09-16 — Agent learning is review-gated
Status: ACTIVE

Decision: Retrospectives may propose framework lessons but agents do not automatically rewrite VanillaForge from individual task experience.

Reason: One-off incidents and false correlations make poor universal rules.

Evidence: `VANILLAFORGE_SYSTEM_PROMPT.md` §17 governs deliberate framework maintenance and lesson promotion.

Consequences: Lessons pass generality, evidence, recurrence, importance and duplication review before promotion.

## 2026-09-16 — Retrieval beats mandatory context loading
Status: ACTIVE

Decision: Companion references are loaded when relevant rather than injected into every task.

Reason: Large fixed context costs more and may over-constrain exploration.

Evidence: `VANILLAFORGE_SYSTEM_PROMPT.md` §18 requires selective reference retrieval.

Consequences: `AGENTS.md` routes context; the system prompt is the active contract and detailed references are retrieved on demand.

## 2026-09-19 — Custom content provenance beats external inference
Status: ACTIVE

Decision: For server-specific or custom-content spell behavior, talents, and mechanics, agents must verify semantics against deployed client/server source files, local DBC/MPQ data, or in-client inspection rather than inferring from Retail or later-expansion databases.

Reason: Custom servers frequently rebalance, redesign, or introduce spells and talents sharing identical names or icons with Retail spells, but having completely different values, durations, or mechanics (e.g. Blackjack).

Evidence: `VANILLAFORGE_SYSTEM_PROMPT.md` §6 and `ENGINE_REFERENCE.md` §2 establish the custom-content evidence priority.

Consequences: Agents do not assume custom content shares Retail/Wrath tuning based on matching spell names or icons; deployed data and DBC inspection take precedence.

## 2026-09-21 — Tone and Technical Neutrality (§14b)
Status: ACTIVE

Decision: Prohibit unsubstantiated marketing superlatives (`enterprise-grade`, `zero-latency`, `zero-bloat`, `ultra-optimized`, `military-grade`, `best-in-class`), developer implementation meta-jargon in player UI, and progressive waiting ellipses (`...`) for discrete actions across public addon code and documentation.

Reason: Addon documentation and user-facing notifications must communicate verified, neutral engineering facts rather than speculative marketing hype or internal C++ engine plumbing details.

Evidence: `VANILLAFORGE_SYSTEM_PROMPT.md` §14b formalizes the standard; `tools/vanillaforge_linter.py` enforces Rule C14/§14b (UI strings) and Rule H9/§14b (`README.md`).

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

Evidence: Recent multi-addon architecture and integration reviews found working read-only queries for optional frame and equipment coordination, while addon-owned tooltip decorators compose through post-hooks. `VANILLAFORGE_SYSTEM_PROMPT.md` §11 records the resulting boundary rule.

Consequences: Architecture reviews identify the owner of each mutable state and verify optional integration without assuming another addon is installed or loaded first.
