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
