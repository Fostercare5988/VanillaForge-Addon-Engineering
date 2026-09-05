#!/usr/bin/env python3
"""
OctoWoW Addon Linter & Heuristic Static Analysis Scanner (v2.0)
Part of the OctoWoW Addon Modernization & Reverse Engineering Framework.
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
DIM = "\033[2m"
RESET = "\033[0m"

PASS_BADGE = f"{GREEN}[PASS]{RESET}"
FAIL_BADGE = f"{RED}[FAIL]{RESET}"
WARN_BADGE = f"{YELLOW}[WARN]{RESET}"
INFO_BADGE = f"{CYAN}[INFO]{RESET}"


class HeuristicStructuralScanner:
    """
    Performs fast heuristic structural scanning of Lua source files.
    Note: This is a lexical/structural scanner designed to catch unmatched blocks,
    brackets, and syntax traps early—not a full Lua compiler or AST parser.
    """
    @classmethod
    def check_structure(cls, filepath):
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
    """
    Audits WoW 1.12.1 addon files against OctoWoW v2 standards.
    Supports severity classification: ERROR, WARNING, and INFO.
    Supports inline suppressions: -- octowow-ignore: <RULE_ID> or all
    """
    def __init__(self, global_ignores=None):
        self.global_ignores = set(r.upper() for r in (global_ignores or []))

    def _is_suppressed(self, line, rule_id):
        if 'ALL' in self.global_ignores or rule_id.upper() in self.global_ignores:
            return True
        ignore_match = re.search(r'--\s*octowow-ignore:\s*([a-zA-Z0-9_\-,\s]+)', line, re.IGNORECASE)
        if ignore_match:
            rules = [r.strip().upper() for r in ignore_match.group(1).split(',')]
            if 'ALL' in rules or rule_id.upper() in rules:
                return True
        return False

    def audit_file(self, filepath):
        errors = []
        warnings = []
        infos = []

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                raw_lines = f.readlines()
        except Exception as e:
            return [f"Cannot read file: {e}"], [], []

        # 1. Heuristic Structural & Syntax Scan
        structural_errors = HeuristicStructuralScanner.check_structure(filepath)
        for err in structural_errors:
            errors.append(f"[STRUCTURAL ERROR] {err}")

        for idx, line in enumerate(raw_lines, 1):
            stripped = line.strip()
            is_comment = stripped.startswith('--')

            # 2. Rule A1: Bare colon method lookup (f:GetScript ...)
            if not self._is_suppressed(line, "A1") and not is_comment:
                bare_colon = re.search(r'[\(\s]([a-zA-Z0-9_]+):([a-zA-Z0-9_]+)\s*(?:and|\)|==|~=)', line)
                if bare_colon and not re.search(r':\w+\s*\(', line):
                    match_text = bare_colon.group(0).strip()
                    if not match_text.endswith('(') and ':' in match_text:
                        errors.append(f"[Rule A1 - Fatal Colon Method] Line {idx}: Bare colon lookup '{match_text}' will crash Lua parser. Use 'f.Method and f:Method()' instead.")

            # 3. Rule B10: Obsolete 2006 Table Wipe Fallback
            if not self._is_suppressed(line, "B10") and not is_comment:
                if re.search(r'for\s+\w+\s+in\s+(?:pairs|__pairs)\s*\(\s*\w+\s*\)\s*do\s+\w+\[\w+\]\s*=\s*nil', line):
                    warnings.append(f"[Rule B10 - Obsolete Wipe Loop] Line {idx}: 2006 manual nil wipe detected. Use native C++ 'table.wipe(t)'.")

            # 4. Rule B3 / AP-01: Tooltip Scraping for Auras
            if not self._is_suppressed(line, "AP-01") and not is_comment:
                if re.search(r'SetUnit(?:De)?buff|SetPlayerBuff', line) and re.search(r'[tT]ooltip', line):
                    warnings.append(f"[Rule B3 / AP-01 - Tooltip Scraping] Line {idx}: Aura tooltip scraping detected. Use ClassicAPI C_UnitAuras.")
                elif re.search(r'(?:TooltipScan|ScanTooltip|ScanningTooltip)', line):
                    warnings.append(f"[Rule B3 / AP-01 - Tooltip Scraping] Line {idx}: Hidden scan tooltip detected. Use native ClassicAPI / SuperWoW APIs.")

            # 5. Rule D1: Table Instantiations in Iterations / Hierarchy calls
            if not self._is_suppressed(line, "D1") and not is_comment:
                if re.search(r'\{\s*(?:[a-zA-Z0-9_]+:)?GetChildren\(\)\s*\}', line):
                    warnings.append(f"[Rule D1 - Hierarchy Table Churn] Line {idx}: '{{ parent:GetChildren() }}' allocates memory. Use register recursion.")
                if re.search(r'\{\s*(?:[a-zA-Z0-9_]+:)?GetRegions\(\)\s*\}', line):
                    warnings.append(f"[Rule D1 - Hierarchy Table Churn] Line {idx}: '{{ f:GetRegions() }}' allocates memory. Use register recursion.")

            # 6. Style - Redundant 144Hz notation
            if not self._is_suppressed(line, "STYLE") and not is_comment:
                if '144Hz+' in line or '144Hz/240Hz+' in line:
                    infos.append(f"[Style - Marketing Phrase] Line {idx}: '144Hz+' notation detected. Use clean 'DXVK' or 'DXVK Vulkan'.")

            # 7. Rule H2: Foreign Locale Spaghetti & Bloat Check
            FOREIGN_TERMS = [
                r'\b(?:KRIEGER|JÄGER|JAEGER|SCHURKE|PRIESTER|SCHAMANE|MAGIER|HEXENMEISTER)\b',
                r'\b(?:GUERRIER|CHASSEUR|VOLEUR|PRÊTRE|PRETRE|CHAMAN|DÉMONISTE|DEMONISTE)\b',
                r'\b(?:GUERRERO|CAZADOR|PÍCARO|PICARO|SACERDOTE|CHAMÁN|BRUJO|DRUIDA)\b',
                r'\b(?:Kriegshymnen|Goulet|Auge|Oeil)\b',
            ]
            if not self._is_suppressed(line, "H2") and not is_comment:
                if re.search(r'GetLocale\(\)\s*==\s*["\'](deDE|frFR|esES|ruRU|zhCN|zhTW|koKR)["\']', line):
                    warnings.append(f"[Rule H2 - Foreign Locale Condition] Line {idx}: Foreign locale condition detected. Maintain English standard.")
                for pattern in FOREIGN_TERMS:
                    if re.search(pattern, line, re.IGNORECASE):
                        warnings.append(f"[Rule H2 - Foreign Localization Bloat] Line {idx}: Non-English term detected in '{stripped[:60]}...'. Enforce English only.")
                        break

            # 8. Rule A3 / A4: Obsolete Lua 5.0 Constructs
            if not self._is_suppressed(line, "A3") and not is_comment:
                if re.search(r'\btable\.getn\s*\(', line):
                    warnings.append(f"[Rule A3 - Legacy table.getn] Line {idx}: 'table.getn(t)' detected. Use modern '#' length operator.")
            if not self._is_suppressed(line, "A4") and not is_comment:
                if re.search(r'\bmath\.mod\s*\(', line):
                    warnings.append(f"[Rule A4 - Legacy math.mod] Line {idx}: 'math.mod(a, b)' detected. Use modern '%' modulo operator.")

            # 9. Rule B0: Obsolete 2006 Libraries
            if not self._is_suppressed(line, "B0") and not is_comment:
                for lib in ('AceLibrary', 'Babble-Spell', 'Babble-Zone', 'Dongle', 'Dewdrop-2.0', 'Tablet-2.0'):
                    if lib in line:
                        warnings.append(f"[Rule B0 - Obsolete Library Bloat] Line {idx}: Legacy 2006 library '{lib}' detected. Modernize with ClassicAPI / NamPower.")

            # 10. AP-09 / Rule C11: Same-Layer Background/Icon Occlusion Risk
            if not self._is_suppressed(line, "C11") and not is_comment:
                if re.search(r'CreateTexture\s*\(\s*nil\s*,\s*["\']OVERLAY["\']\s*\)', line) and re.search(r'(?:[Bb]g|[Bb]ackground)\b', line):
                    warnings.append(f"[Rule C11 - Same-Layer Occlusion Risk] Line {idx}: Background texture created on 'OVERLAY' layer. Place in 'BACKGROUND' or 'BORDER'.")

            # 11. AP-24: Verbose Time Strings in Compact Rows
            if not self._is_suppressed(line, "AP-24") and not is_comment:
                if '"Just now"' in line or "'Just now'" in line:
                    warnings.append(f"[Anti-Pattern 24 - Verbose Time String] Line {idx}: 'Just now' string detected in row formatter. Use compact '0s' / 'now'.")

            # 12. AP-16: Naive table.sort on fixed buffer
            if not self._is_suppressed(line, "AP-16") and not is_comment:
                if re.search(r'\btable\.sort\s*\(\s*(?:roster|buffer|enemies|units)\s*[,|\)]', line) and not 'active' in line.lower():
                    warnings.append(f"[Anti-Pattern 16 - Unbounded Buffer Sort] Line {idx}: 'table.sort' detected on entity buffer. Use bounded active sort.")

        return errors, warnings, infos

    def audit_addon_dir(self, dir_path):
        results = {}
        total_errors = 0
        total_warnings = 0
        total_infos = 0

        # Check for Rule B1 Startup Guard in entry files
        has_startup_guard = False
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
                    readme_warnings.append("[Style - Redundant Marketing] README.md contains '144Hz+'. Change to clean 'DXVK'.")
                if 'Eye of the Storm' in rm:
                    readme_warnings.append("[Rule H2 - Invalid BG] README.md contains 'Eye of the Storm'. Replace with 'Thorn Gorge'.")
                if 'OctoWoW' in rm or '-Octo' in rm or '[Octo]' in rm:
                    readme_warnings.append("[Rule H2 - Octo Branding Leak] README.md contains 'Octo' branding. Keep GitHub addon repos neutral.")

        # Check TOC file for Octo branding leaks
        for f in os.listdir(dir_path):
            if f.endswith('.toc'):
                with open(os.path.join(dir_path, f), 'r', encoding='utf-8', errors='replace') as tf:
                    tc = tf.read()
                    if 'OctoWoW' in tc or '[Octo]' in tc or '-Octo' in tc:
                        readme_warnings.append(f"[Rule H2 - Octo Branding Leak] '{f}' contains 'Octo' branding in metadata. Keep GitHub addon repos neutral.")

        # Check Rule H7: Locales directory bloat
        locales_dir = os.path.join(dir_path, 'Locales')
        if os.path.isdir(locales_dir):
            readme_warnings.append("[Rule H7 - Legacy Locales Directory] Addon contains legacy 'Locales/' folder. Consolidate into 'Localization.lua'.")

        # Scan all Lua files
        for root, _, files in os.walk(dir_path):
            for f in sorted(files):
                if re.search(r'localization\.(de|fr|es|ru|zh|kr|cn)\.lua', f, re.IGNORECASE) or re.search(r'(deDE|frFR|ruRU|zhCN)\.lua', f, re.IGNORECASE):
                    rel = os.path.relpath(os.path.join(root, f), dir_path)
                    readme_warnings.append(f"[Rule H2 - Foreign Locale File] '{rel}' is redundant foreign locale bloat.")
                if f.endswith('.lua'):
                    filepath = os.path.join(root, f)
                    rel = os.path.relpath(filepath, dir_path)
                    errs, warns, infs = self.audit_file(filepath)
                    results[rel] = (errs, warns, infs)
                    total_errors += len(errs)
                    total_warnings += len(warns)
                    total_infos += len(infs)

        return results, has_startup_guard, readme_warnings, total_errors, total_warnings, total_infos


def main():
    parser = argparse.ArgumentParser(description="OctoWoW Addon Linter & Heuristic Static Analysis Scanner (v2.0)")
    parser.add_argument("target", help="Path to Lua file or AddOn directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors (exit code 1 on warnings)")
    parser.add_argument("--ignore", nargs="*", default=[], help="Global rules to suppress (e.g. --ignore A3 D1)")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"{RED}[ERROR] Target path does not exist: {target}{RESET}")
        sys.exit(1)

    auditor = OctoWoWAuditor(global_ignores=args.ignore)

    if os.path.isfile(target):
        print(f"\n{BOLD}{CYAN}=== Scanning File: {os.path.basename(target)} ==={RESET}\n")
        errors, warnings, infos = auditor.audit_file(target)
        if errors:
            for err in errors:
                print(f"  {RED}✖ {err}{RESET}")
        if warnings:
            for warn in warnings:
                print(f"  {YELLOW}⚠ {warn}{RESET}")
        if infos:
            for inf in infos:
                print(f"  {CYAN}ℹ {inf}{RESET}")
        if not errors and not warnings:
            print(f"  {GREEN}✔ Clean scan. Zero errors or warnings!{RESET}")
        
        exit_code = 1 if errors or (args.strict and warnings) else 0
        sys.exit(exit_code)

    elif os.path.isdir(target):
        print(f"\n{BOLD}{CYAN}=== Auditing Addon: {os.path.basename(target)} ==={RESET}\n")
        results, has_guard, readme_warnings, total_errors, total_warnings, total_infos = auditor.audit_addon_dir(target)

        if has_guard:
            print(f"  {PASS_BADGE} Startup Guard: Present & Validated (CLASSIC_API_VERSION & SUPERWOW_VERSION)")
        else:
            print(f"  {FAIL_BADGE} Startup Guard: MISSING! Addon must guard CLASSIC_API_VERSION & SUPERWOW_VERSION")
            total_errors += 1

        if readme_warnings:
            for rw in readme_warnings:
                print(f"  {WARN_BADGE} Addon Structure: {rw}")
                total_warnings += 1
        else:
            print(f"  {PASS_BADGE} Addon Structure: README.md and files comply with clean standards")

        print(f"\n{BOLD}File Diagnostics:{RESET}")
        for rel_file, (errors, warnings, infos) in results.items():
            if errors:
                print(f"  {FAIL_BADGE} {rel_file}:")
                for err in errors:
                    print(f"      - {err}")
            elif warnings:
                print(f"  {WARN_BADGE} {rel_file}:")
                for warn in warnings:
                    print(f"      - {warn}")
            else:
                print(f"  {PASS_BADGE} {rel_file}")

        print("\n" + "=" * 60)
        if total_errors == 0 and total_warnings == 0:
            print(f"{BOLD}{GREEN}ALL PASSED: 100% compliant with OctoWoW v2 specifications!{RESET}\n")
            sys.exit(0)
        elif total_errors == 0:
            print(f"{BOLD}{YELLOW}PASSED: Zero critical errors ({total_warnings} advisory warning(s)).{RESET}\n")
            sys.exit(1 if args.strict else 0)
        else:
            print(f"{BOLD}{RED}FAILED: {total_errors} critical error(s) and {total_warnings} warning(s) detected.{RESET}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
