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
   UI hooks: globals exist in the target client/verified extension; event and render callers inspected.
4. Performance: coverage accounts for loaded modules; trace trigger fan-out,
   cardinality and shared consumers. Hot-path churn/polling justified; counters
   use comparable fixtures and include deferred/provider work. Claims match evidence.
5. Persistence: scratch state, migrations, SavedVariables coherence.
6. UI/load graph: TOC, root Bindings.xml, layout churn.
7. Validation: targeted/full tests, linter, runtime clearly separated from static.
   UI regressions: faithful methods/hooks and native redraw side effects; new test fails the faulty revision where practical.
8. Repository: final diff, artifacts, affected docs/version/dependencies, exact status.

For framework maintenance, also verify canonical ownership, source/version scope,
removal of superseded active guidance, valid links, and meaningful regressions for
machine-checkable lessons. Preserve historical evidence; avoid duplicated policy.

RETURN:
A. PASS/FAIL by section
B. defects with location
C. runtime verification required
D. exact validation
E. READY or FIXES REQUIRED

Do not edit during REVIEW ONLY.
```
