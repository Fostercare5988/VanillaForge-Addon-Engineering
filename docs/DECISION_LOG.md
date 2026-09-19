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
