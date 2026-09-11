#!/usr/bin/env python3
"""
OctoWoW Universal AI Contract & Pre-Commit Hook Installer
Deploys CLAUDE.md, AGENTS.md, and .git/hooks/pre-commit to all active addons.
Guarantees any AI assistant (Claude, Antigravity, Cursor) respects the master prompt.
"""

import os
import sys

ADDONS = [
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\FosterFrames",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\AutoBG",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\AutoLazy",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\Bagnon",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\MikScrollingBattleText",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\TWThreat",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\TrinketMenu",
    r"C:\Users\Fostercare\Desktop\Niko2\Interface\AddOns\BattlegroundTargets"
]

CONTRACT_CONTENT = """# Mandatory AI Directives for OctoWoW Addon Development

Before analyzing, refactoring, editing, or committing code in this repository:

1. **Master Authority**:
   Strictly read and follow the master directives in:
   `c:/Users/Fostercare/Documents/System Prompts/OCTOWOW_SYSTEM_PROMPT.md`

2. **Mandatory Client Extension Stack**:
   All addons strictly require and leverage:
   - **ClassicAPI v1.15.0+** (v1.14.0+ baseline: C++ timers, native table.wipe, C_UnitAuras, C_Container native coroutine sorting, modern EditBox API, C_Map, C_Texture)
   - **SuperWoW v2.2+** (Direct GUID targeting TargetUnit(guid), SetMouseoverUnit)
   - **NamPower v4.6.3+** (Zero-latency spell queue, binary combat log packets)
   - **UnitXP SP3 v89+** (Final release: Uncapped 3D Euclidean distances and real HP integers)
   - **DXVK** (Vulkan frame pacing translation layer)
   - Never write 2006 legacy fallbacks, tooltip scans, or manual nil loops.

3. **Mandatory Automated Static Linter Gatekeeper**:
   Before every commit, run the automated auditor:
   `python "c:/Users/Fostercare/Documents/System Prompts/tools/octowow_linter.py" .`
   Every commit MUST pass with 0 issues and 0 warnings.

4. **Strict 100% English Standard (Rule H2)**:
   All code, comments, UI text, and documentation must be 100% English.
   Never preserve or write foreign localization (deDE, frFR, ruRU, zhCN) files or conditionals.

5. **Single Branch Git Standardization**:
   Strictly maintain and push to 1 single branch (main or master). Never create extraneous branches.

6. **Continuous Learning Protocol (Rule H6)**:
   When resolving any new bug or edge-case, immediately record the anti-pattern in OCTOWOW_SYSTEM_PROMPT.md (Part I) and add a test in tools/octowow_linter.py.
"""

HOOK_CONTENT = """#!/bin/sh
echo "Running OctoWoW Linter pre-commit audit..."
python "c:/Users/Fostercare/Documents/System Prompts/tools/octowow_linter.py" .
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "[BLOCKED] Commit rejected: OctoWoW Linter detected issues! Fix them before committing."
    exit 1
fi
"""

def main():
    print("=== Deploying OctoWoW AI Contracts & Git Hooks ===\n")
    succeeded = 0
    for addon_path in ADDONS:
        name = os.path.basename(addon_path)
        if not os.path.isdir(addon_path):
            print(f"[SKIP] Directory not found: {addon_path}")
            continue

        # Write CLAUDE.md
        claude_path = os.path.join(addon_path, "CLAUDE.md")
        with open(claude_path, "w", encoding="utf-8") as f:
            f.write(CONTRACT_CONTENT)

        # Write AGENTS.md
        agents_path = os.path.join(addon_path, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write(CONTRACT_CONTENT)

        # Install pre-commit hook - only possible if this is actually a git repo
        git_hooks_dir = os.path.join(addon_path, ".git", "hooks")
        hook_installed = os.path.isdir(git_hooks_dir)
        if hook_installed:
            hook_file = os.path.join(git_hooks_dir, "pre-commit")
            with open(hook_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(HOOK_CONTENT)

        succeeded += 1
        if hook_installed:
            print(f"[SUCCESS] Installed AI contracts (CLAUDE.md, AGENTS.md) and pre-commit hook in: {name}")
        else:
            print(f"[PARTIAL] Installed AI contracts (CLAUDE.md, AGENTS.md) in: {name} — no .git/hooks found, pre-commit hook NOT installed")

    print(f"\n{succeeded}/{len(ADDONS)} addons fortified with AI contracts — check any [SKIP] or [PARTIAL] lines above before assuming full coverage.")

if __name__ == "__main__":
    main()
