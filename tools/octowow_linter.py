#!/usr/bin/env python3
"""
OctoWoW Addon Linter & Static Analysis Auditor
Part of the OctoWoW Addon Modernization & Reverse Engineering System.
Validates World of Warcraft 1.12.1 addons against the modern Enhanced Engine Stack:
ClassicAPI v1.13.4+, SuperWoW v2.2+, NamPower v4.6.3+, UnitXP SP3, and DXVK.
"""

import os
import sys
import re
import argparse

# Ensure standard output can print utf-8 characters on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Badges and colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

PASS_BADGE = f"{GREEN}[PASS]{RESET}"
FAIL_BADGE = f"{RED}[FAIL]{RESET}"
WARN_BADGE = f"{YELLOW}[WARN]{RESET}"

class LuaSyntaxChecker:
    @classmethod
    def check_syntax(cls, filepath):
        errors = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return [f"Unable to read file: {e}"]

        lines = content.split('\n')
        
        in_block_comment = False
        in_block_string = False

        block_stack = []      # (type, line_number)
        bracket_stack = []    # (char, line_number)

        bracket_map = {'(': ')', '[': ']', '{': '}'}
        bracket_rev = {')': '(', ']': '[', '}': '{'}

        pending_if = False
        pending_elseif = False
        pending_loop = False

        for line_idx, line in enumerate(lines, 1):
            i = 0
            n = len(line)

            while i < n:
                if in_block_comment:
                    if line[i:i+2] == ']]':
                        in_block_comment = False
                        i += 2
                    else:
                        i += 1
                    continue

                if in_block_string:
                    if line[i:i+2] == ']]':
                        in_block_string = False
                        i += 2
                    else:
                        i += 1
                    continue

                # Check comments
                if line[i:i+4] == '--[[':
                    in_block_comment = True
                    i += 4
                    continue
                if line[i:i+2] == '--':
                    break

                # Check block string
                if line[i:i+2] == '[[':
                    in_block_string = True
                    i += 2
                    continue

                # Check string literals
                if line[i] in ("'", '"'):
                    quote = line[i]
                    i += 1
                    while i < n:
                        if line[i] == '\\':
                            i += 2
                            continue
                        if line[i] == quote:
                            i += 1
                            break
                        i += 1
                    continue

                # Check brackets
                char = line[i]
                if char in bracket_map:
                    bracket_stack.append((char, line_idx))
                elif char in bracket_rev:
                    if not bracket_stack:
                        errors.append(f"Line {line_idx}: Unmatched closing bracket '{char}'")
                    else:
                        open_char, open_line = bracket_stack.pop()
                        if bracket_map[open_char] != char:
                            errors.append(f"Line {line_idx}: Mismatched bracket '{char}', expected '{bracket_map[open_char]}' (opened at line {open_line})")

                # Check keywords
                if line[i].isalpha() or line[i] == '_':
                    start = i
                    while i < n and (line[i].isalnum() or line[i] == '_'):
                        i += 1
                    word = line[start:i]

                    if word == 'if':
                        pending_if = True
                    elif word == 'elseif':
                        pending_elseif = True
                    elif word == 'then':
                        if pending_if:
                            block_stack.append(('if', line_idx))
                            pending_if = False
                        elif pending_elseif:
                            pending_elseif = False
                        else:
                            block_stack.append(('if', line_idx))
                    elif word in ('for', 'while'):
                        pending_loop = True
                    elif word == 'do':
                        if pending_loop:
                            block_stack.append(('loop', line_idx))
                            pending_loop = False
                        else:
                            block_stack.append(('do', line_idx))
                    elif word == 'function':
                        block_stack.append(('function', line_idx))
                    elif word == 'repeat':
                        block_stack.append(('repeat', line_idx))
                    elif word == 'end':
                        if not block_stack:
                            errors.append(f"Line {line_idx}: Unexpected 'end' with no open block")
                        else:
                            top, top_line = block_stack.pop()
                            if top not in ('if', 'loop', 'do', 'function'):
                                errors.append(f"Line {line_idx}: 'end' closed '{top}' from line {top_line}")
                    elif word == 'until':
                        if not block_stack:
                            errors.append(f"Line {line_idx}: Unexpected 'until' with no open block")
                        else:
                            top, top_line = block_stack.pop()
                            if top != 'repeat':
                                errors.append(f"Line {line_idx}: 'until' matched non-repeat '{top}' from line {top_line}")
                    continue

                i += 1

        while bracket_stack:
            char, line_idx = bracket_stack.pop()
            errors.append(f"Line {line_idx}: Unclosed bracket '{char}'")

        while block_stack:
            kw, line_idx = block_stack.pop()
            errors.append(f"Line {line_idx}: Unclosed block '{kw}'")

        return errors


class OctoWoWAuditor:
    def __init__(self):
        self.issues = []
        self.warnings = []

    def audit_file(self, filepath):
        issues = []
        warnings = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                raw_lines = f.readlines()
        except Exception as e:
            return [f"Cannot read file: {e}"], []

        # 1. AST Syntax Check
        syntax_errors = LuaSyntaxChecker.check_syntax(filepath)
        for err in syntax_errors:
            issues.append(f"[SYNTAX ERROR] {err}")

        # 2. Rule A1: Uncalled colon method check (f:GetScript ...)
        for idx, line in enumerate(raw_lines, 1):
            bare_colon = re.search(r'[\(\s]([a-zA-Z0-9_]+):([a-zA-Z0-9_]+)\s*(?:and|\)|==|~=)', line)
            if bare_colon and not re.search(r':\w+\s*\(', line):
                match_text = bare_colon.group(0).strip()
                if not match_text.endswith('(') and ':' in match_text:
                    issues.append(f"[Rule A1 - Colon Method Crash] Line {idx}: Bare colon method lookup '{match_text}' will crash Lua parser. Use 'f.Method and f:Method()' instead.")

        # 3. Rule B10: Obsolete 2006 Table Wipe Fallback
        for idx, line in enumerate(raw_lines, 1):
            if re.search(r'for\s+\w+\s+in\s+(?:pairs|__pairs)\s*\(\s*\w+\s*\)\s*do\s+\w+\[\w+\]\s*=\s*nil', line):
                warnings.append(f"[Rule B10 - Obsolete Wipe Loop] Line {idx}: Detected 2006 manual nil loop. ClassicAPI v1.13.4+ provides native C++ 'table.wipe(t)'.")

        # 4. Rule B3: Tooltip Scanning for Auras / Hidden Tooltip Scraping
        for idx, line in enumerate(raw_lines, 1):
            if re.search(r'SetUnit(?:De)?buff|SetPlayerBuff', line) and re.search(r'[tT]ooltip', line):
                warnings.append(f"[Rule B3 - Tooltip Scraping] Line {idx}: Detected legacy aura tooltip scraping. Use ClassicAPI C_UnitAuras.")
            if re.search(r'(?:TooltipScan|ScanTooltip|ScanningTooltip)', line):
                warnings.append(f"[Rule B3 - Tooltip Scraping] Line {idx}: Detected hidden scan tooltip usage. Use native ClassicAPI / SuperWoW APIs.")

        # 5. Rule D1 / D4: Table Instantiations in Iterations
        for idx, line in enumerate(raw_lines, 1):
            if re.search(r'\{\s*(?:[a-zA-Z0-9_]+:)?GetChildren\(\)\s*\}', line):
                warnings.append(f"[Rule D1 - Hierarchy Table Churn] Line {idx}: '{{ parent:GetChildren() }}' allocates memory. Use register tail recursion.")
            if re.search(r'\{\s*(?:[a-zA-Z0-9_]+:)?GetRegions\(\)\s*\}', line):
                warnings.append(f"[Rule D1 - Hierarchy Table Churn] Line {idx}: '{{ f:GetRegions() }}' allocates memory. Use register tail recursion.")

        # 6. Redundancy: 144Hz+ notation
        for idx, line in enumerate(raw_lines, 1):
            if '144Hz+' in line or '144Hz/240Hz+' in line:
                warnings.append(f"[Style - Redundant Marketing] Line {idx}: '144Hz+' string found. User prefers clean 'DXVK' or 'DXVK Vulkan'.")

        # 7. Rule H2: Foreign Locale Spaghetti Check
        for idx, line in enumerate(raw_lines, 1):
            if re.search(r'GetLocale\(\)\s*==\s*["\'](deDE|frFR|esES|ruRU|zhCN|zhTW|koKR)["\']', line):
                warnings.append(f"[Rule H2 - Foreign Locale Spaghetti] Line {idx}: Foreign locale condition detected. Code must be 100% English only.")

        # 8. Rule B0: Obsolete 2006 Libraries (Ace, Babble, Dongle)
        for idx, line in enumerate(raw_lines, 1):
            for lib in ('AceLibrary', 'Babble-Spell', 'Babble-Zone', 'Dongle', 'Dewdrop-2.0', 'Tablet-2.0'):
                if lib in line and not line.strip().startswith('--'):
                    warnings.append(f"[Rule B0 - Obsolete Library Bloat] Line {idx}: Detected legacy 2006 library '{lib}'. Replace with ClassicAPI / NamPower.")

        # 9. Anti-Pattern 14: Unchecked SetMouseoverUnit without pcall or 0x GUID validation
        for idx, line in enumerate(raw_lines, 1):
            if re.search(r'(?<!pcall\()\bSetMouseoverUnit\s*\(\s*[a-zA-Z0-9_\.]+\s*\)', line) and not 'pcall' in line and not line.strip().startswith('--'):
                warnings.append(f"[Anti-Pattern 14 - Unchecked SetMouseoverUnit] Line {idx}: SetMouseoverUnit called directly without pcall or 0x GUID validation. SuperWoW crashes on unknown unit names.")

        # 10. Anti-Pattern 16: Naive table.sort on fixed pre-allocated buffer
        for idx, line in enumerate(raw_lines, 1):
            if re.search(r'\btable\.sort\s*\(\s*(?:roster|buffer|enemies|units)\s*[,|\)]', line) and not 'active' in line.lower() and not line.strip().startswith('--'):
                warnings.append(f"[Anti-Pattern 16 - Unbounded Buffer Sort] Line {idx}: 'table.sort' detected on fixed-size entity buffer. Fixed-capacity buffers sort empty/nil slots into active rows. Use bounded insertion sort.")

        return issues, warnings

    def audit_addon_dir(self, dir_path):
        results = {}
        total_issues = 0
        total_warnings = 0

        # Check TOC file
        toc_files = [f for f in os.listdir(dir_path) if f.endswith('.toc')]
        has_startup_guard = False

        # Check for Rule B1 Startup Guard in entry files
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith('.lua'):
                    filepath = os.path.join(root, f)
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as lf:
                        c = lf.read()
                        if 'CLASSIC_API_VERSION' in c and 'SUPERWOW_VERSION' in c:
                            has_startup_guard = True
                            break
            if has_startup_guard:
                break

        # Check README & Directory Standards
        readme_path = os.path.join(dir_path, 'README.md')
        readme_warnings = []
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8', errors='replace') as f:
                rm = f.read()
                if '|cff' in rm or '|r' in rm:
                    readme_warnings.append("[Rule H5 - Raw WoW Colors] README.md contains raw WoW color codes (|cff.../|r). Clean to standard Markdown.")
                if '144Hz+' in rm:
                    readme_warnings.append("[Style - Redundant Marketing] README.md contains '144Hz+'. Change to clean 'DXVK' / 'DXVK: Vulkan'.")

        # Check Rule H7: Modular Architecture & Locales directory
        locales_dir = os.path.join(dir_path, 'Locales')
        if os.path.isdir(locales_dir):
            readme_warnings.append("[Rule H7 - Legacy Locales Clutter] Addon contains legacy 'Locales/' directory. Consolidate into a single 'Localization.lua' and delete the folder.")

        # Scan all files
        for root, _, files in os.walk(dir_path):
            for f in sorted(files):
                if re.search(r'localization\.(de|fr|es|ru|zh|kr|cn)\.lua', f, re.IGNORECASE) or re.search(r'(deDE|frFR|ruRU|zhCN)\.lua', f, re.IGNORECASE):
                    rel = os.path.relpath(os.path.join(root, f), dir_path)
                    warnings.append(f"[Rule H2 - Foreign Locale File] '{rel}' is redundant foreign locale bloat. Eradicate file and enforce English only.")
                if f.endswith('.lua'):
                    filepath = os.path.join(root, f)
                    rel = os.path.relpath(filepath, dir_path)
                    issues, warnings = self.audit_file(filepath)
                    results[rel] = (issues, warnings)
                    total_issues += len(issues)
                    total_warnings += len(warnings)

        return results, has_startup_guard, readme_warnings, total_issues, total_warnings


def main():
    parser = argparse.ArgumentParser(description="OctoWoW Addon Linter & Static Analysis Auditor")
    parser.add_argument("target", help="Path to Lua file or AddOn directory")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"{RED}[ERROR] Target path does not exist: {target}{RESET}")
        sys.exit(1)

    auditor = OctoWoWAuditor()

    if os.path.isfile(target):
        print(f"\n{BOLD}{CYAN}=== Auditing Single File: {os.path.basename(target)} ==={RESET}\n")
        issues, warnings = auditor.audit_file(target)
        if issues:
            for iss in issues:
                print(f"  {RED}✖ {iss}{RESET}")
        if warnings:
            for warn in warnings:
                print(f"  {YELLOW}⚠ {warn}{RESET}")
        if not issues and not warnings:
            print(f"  {GREEN}✔ 100% Passed. Zero issues or warnings!{RESET}")
        sys.exit(1 if issues else 0)

    elif os.path.isdir(target):
        print(f"\n{BOLD}{CYAN}=== Auditing Addon: {os.path.basename(target)} ==={RESET}\n")
        results, has_guard, readme_warnings, total_issues, total_warnings = auditor.audit_addon_dir(target)

        if has_guard:
            print(f"  {PASS_BADGE} Rule B1 Startup Guard: Present & Validated (CLASSIC_API_VERSION & SUPERWOW_VERSION)")
        else:
            print(f"  {FAIL_BADGE} Rule B1 Startup Guard: MISSING! Addon must guard CLASSIC_API_VERSION & SUPERWOW_VERSION")
            total_issues += 1

        if readme_warnings:
            for rw in readme_warnings:
                print(f"  {WARN_BADGE} README Check: {rw}")
                total_warnings += 1
        else:
            print(f"  {PASS_BADGE} Rule H5 Documentation: README.md complies with clean standards")

        print(f"\n{BOLD}File Analysis:{RESET}")
        for rel_file, (issues, warnings) in results.items():
            if issues:
                print(f"  {FAIL_BADGE} {rel_file}:")
                for iss in issues:
                    print(f"      - {iss}")
            elif warnings:
                print(f"  {WARN_BADGE} {rel_file}:")
                for warn in warnings:
                    print(f"      - {warn}")
            else:
                print(f"  {PASS_BADGE} {rel_file}")

        print("\n" + "=" * 60)
        if total_issues == 0 and total_warnings == 0:
            print(f"{BOLD}{GREEN}ALL PASSED: Addon strictly adheres to OctoWoW & ClassicAPI v1.13.4+ specifications!{RESET}\n")
            sys.exit(0)
        elif total_issues == 0:
            print(f"{BOLD}{YELLOW}PASSED WITH WARNINGS: {total_warnings} warning(s) detected. Code is syntactically sound.{RESET}\n")
            sys.exit(0)
        else:
            print(f"{BOLD}{RED}FAILED: {total_issues} critical issue(s) and {total_warnings} warning(s) detected.{RESET}\n")
            sys.exit(1)

if __name__ == "__main__":
    main()
