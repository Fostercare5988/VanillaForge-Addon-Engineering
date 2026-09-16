# VanillaForge Integration Review Template

Use after complex/multi-phase changes. Review only unless edits are explicitly authorized.

```text
REVIEW TYPE:
final integration | state-machine | release | regression

OBJECTIVE:
Verify the integrated result, not merely individual patches.

SCOPE:
<files/subsystems>

VERIFY:
1. Correctness: intended behavior, safe error/cancellation paths.
2. Ownership: stale/duplicate events, supersession, deferred work, published state.
3. APIs: verified primitives, authoritative state, dependencies match consumption.
4. Performance: hot-path churn/polling justified; claims match evidence.
5. Persistence: scratch state, migrations, SavedVariables coherence.
6. UI/load graph: TOC, root Bindings.xml, layout churn.
7. Validation: targeted/full tests, linter, runtime clearly separated from static.
8. Repository: final diff, artifacts, affected docs/version/dependencies, exact status.

RETURN:
A. PASS/FAIL by section
B. defects with location
C. runtime verification required
D. exact validation
E. READY or FIXES REQUIRED

Do not edit during REVIEW ONLY.
```
