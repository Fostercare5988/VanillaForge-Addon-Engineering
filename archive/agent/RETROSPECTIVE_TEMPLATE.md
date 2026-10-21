# VanillaForge Retrospective Template

Use after substantial work. Keep only lessons that change future decisions;
do not archive the conversation or create a report file for routine success.
Keep addon-specific facts with the addon. Use the fields relevant to the task.

## Task
- Addon/repository:
- Task class:
- Objective:
- Result:

## Useful Feedback
- What evidence or check resolved the problem:
- Rework or unnecessary exploration, and its cause:
- What a future task should do differently:

## Framework Lesson
1. Find the canonical owner and inspect existing coverage: contract for policy,
   references for APIs, `KNOWN_PATTERNS.md` for recurring hazards, linter/tests for
   machine-checkable rules, and audits for versioned source or deployment evidence.
2. A candidate must be general, verified, likely to recur and important. If any
   condition fails, keep it as project knowledge or an unresolved investigation.
   Existing adequate coverage means no change; missing detail or incorrect
   guidance can justify refinement even when the subject is already covered.
3. Choose **no change**, **merge/refine**, **replace/retire**, or **new reference**.
   Prefer improving the owner. A new file requires a distinct recurring purpose,
   not merely a new task or another copy of a rule.
4. Promote only in deliberately reviewed, authorized framework maintenance.
   Ordinary addon work may propose a candidate; it must not modify the framework
   automatically.
5. When promoting, remove superseded active guidance and repair affected links.
   Retain pinned historical evidence and its original verification scope. Add a
   meaningful regression when the lesson is machine-checkable, then validate
   affected docs/tools. Keep any decision-log entry concise; do not mirror the
   lesson across the contract, router and workflows.

## Framework Lesson Candidate
```text
FRAMEWORK LESSON CANDIDATE
Observation:
Evidence: <source/test/runtime; revision or deployment; confidence>
Confidence: SOURCE-VERIFIED | EMPIRICALLY VERIFIED
Why general:
Likely recurrence:
Canonical owner and existing coverage:
Outcome: no change | merge/refine | replace/retire | new reference
Proposed correction and superseded guidance to remove:
Validation: <meaningful regression or source/runtime check>
```

An unverified observation is an investigation, not a promoted engineering rule.
