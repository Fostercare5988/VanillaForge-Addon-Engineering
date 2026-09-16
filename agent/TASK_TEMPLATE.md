# VanillaForge Task Template

```text
TASK TYPE:
architecture discovery | modernization audit | bounded implementation |
bug fix | integration review | release/reconciliation | framework maintenance

OBJECTIVE:
<one concrete outcome>

REPOSITORY:
<path/repository>

KNOWN VERIFIED STATE:
<reusable facts; durable repository artifact or audit/review document; applicable commit/revision>

READ:
- AGENTS.md
- VANILLAFORGE_SYSTEM_PROMPT.md
- <only relevant references>

DO NOT REPEAT:
<completed discovery/audit/research; artifact/document and applicable commit/revision>

SCOPE:
<files/modules/subsystem>

OUT OF SCOPE:
<boundaries>

INVARIANTS:
- <must remain true>

EVIDENCE / API QUESTIONS:
- <requires verification>

VALIDATION:
- <tests>
- <linter>
- <repo checks>
- <runtime checks>

STOP CONDITION:
<exact stopping point>

GIT AUTHORIZATION:
none | commit only | commit + push

REPORT:
- files changed
- behavior changed
- validation
- unresolved runtime verification
- git status
```

## Context Budget Rule
Do not load a reference merely because it exists. Start with contract + task state, then retrieve deeper knowledge for a concrete uncertainty, API decision or relevant pattern.
