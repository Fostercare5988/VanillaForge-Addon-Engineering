#!/usr/bin/env python3
"""
VanillaForge Addon Linter & Heuristic Static Analysis Scanner (v3.1)
Part of the VanillaForge Enhanced WoW 1.12.1 Addon Engineering Framework.
Targets World of Warcraft 1.12.1 Build 5875 / Interface 11200 with an enhanced-client baseline:
ClassicAPI v1.15.10+, SuperWoW v2.2+, NamPower v4.6.2+, UnitXP SP3 v90+, and DXVK runtime.
The full environment may be installed, but individual addons only depend on components they actually consume.
"""

import os
import sys
import re
import argparse
from pathlib import Path

LINTER_VERSION = "3.1"
MIN_CLASSIC_API = 11510  # ClassicAPI v1.15.10


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
    Supports Lua 5.1/ClassicAPI leveled long brackets ([=[ ... ]=], [==[ ... ]==]).
    """
    LONG_BRACKET_OPEN = re.compile(r'\[(=*)\[')

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
        block_level = 0  # number of '=' in the currently-open long bracket

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
                if in_block_comment or in_block_string:
                    closer = ']' + ('=' * block_level) + ']'
                    if line[i:i + len(closer)] == closer:
                        i += len(closer)
                        in_block_comment = False
                        in_block_string = False
                        block_level = 0
                    else:
                        i += 1
                    continue

                # Long-bracket comment: --[[ ... ]]  /  --[=[ ... ]=]  / etc.
                if line[i:i + 2] == '--':
                    m = cls.LONG_BRACKET_OPEN.match(line, i + 2)
                    if m:
                        in_block_comment = True
                        block_level = len(m.group(1))
                        i = m.end()
                        continue
                    break  # plain '--' line comment: rest of the line is a comment

                # Long-bracket string: [[ ... ]]  /  [=[ ... ]=]  / etc.
                m = cls.LONG_BRACKET_OPEN.match(line, i)
                if m:
                    in_block_string = True
                    block_level = len(m.group(1))
                    i = m.end()
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


class VanillaForgeAuditor:
    """
    Audits enhanced WoW 1.12.1 addon files against VanillaForge v3 standards.
    ERROR is reserved for high-confidence structural/correctness failures.
    WARNING marks strong modernization hazards; INFO marks contextual design smells.
    Supports inline suppressions: -- vanillaforge-ignore: <RULE_ID> or all.
    Legacy octowow-ignore/linter-ignore/engine-ignore forms remain accepted.
    """
    def __init__(self, global_ignores=None):
        self.global_ignores = set(r.upper() for r in (global_ignores or []))

    def _is_suppressed(self, line, rule_id):
        if 'ALL' in self.global_ignores or rule_id.upper() in self.global_ignores:
            return True
        ignore_match = re.search(r'--\s*(?:vanillaforge|octowow|linter|engine)-ignore:\s*([a-zA-Z0-9_\-,\s]+)', line, re.IGNORECASE)
        if not ignore_match:
            ignore_match = re.search(r'<!--\s*(?:vanillaforge|octowow|linter|engine)-ignore:\s*([a-zA-Z0-9_\-,\s]+)\s*-->', line, re.IGNORECASE)
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

        # 1. Heuristic Structural & Syntax Scan (Lua only)
        if filepath.endswith('.lua'):
            structural_errors = HeuristicStructuralScanner.check_structure(filepath)
            for err in structural_errors:
                errors.append(f"[STRUCTURAL ERROR] {err}")

        current_button_name = ""
        for idx, line in enumerate(raw_lines, 1):
            stripped = line.strip()
            is_comment = stripped.startswith('--') or stripped.startswith('<!--') or stripped.startswith('-->')

            if filepath.endswith('.xml'):
                btn_match = re.search(r'<(?:Button|CheckButton)\b[^>]*\bname\s*=\s*["\']([^"\']+)["\']', line)
                if btn_match:
                    current_button_name = btn_match.group(1)
                elif '</Button>' in line or '</CheckButton>' in line:
                    current_button_name = ""

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
                    warnings.append(f"[Rule B10 - Obsolete Wipe Loop] Line {idx}: 2006 manual nil wipe detected. Use ClassicAPI 'table.wipe(t)'.")

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

            # 7. Localization policy
            # VanillaForge v3 does not treat localization support as a defect.
            # Remove unused localization only when project scope explicitly calls for it.

            # 8. Rule A3 / A4: Obsolete Lua 5.0 Constructs
            if not self._is_suppressed(line, "A3") and not is_comment:
                if re.search(r'\btable\.getn\s*\(', line):
                    warnings.append(f"[Rule A3 - Legacy table.getn] Line {idx}: 'table.getn(t)' detected. Use modern '#' length operator.")
                if re.search(r'\btable\.setn\s*\(', line):
                    warnings.append(f"[Rule A3 - Legacy table.setn] Line {idx}: 'table.setn(t, n)' is obsolete Lua 5.0 code. Use direct array assignment or native table sizing.")
            if not self._is_suppressed(line, "A4") and not is_comment:
                if re.search(r'\bmath\.mod\s*\(', line):
                    warnings.append(f"[Rule A4 - Legacy math.mod] Line {idx}: 'math.mod(a, b)' detected. Use modern '%' modulo operator.")

            # 9. Rule B0: Obsolete 2006 Libraries
            if not self._is_suppressed(line, "B0") and not is_comment:
                for lib in ('AceLibrary', 'Babble-Spell', 'Babble-Zone', 'Dongle', 'Dewdrop-2.0', 'Tablet-2.0'):
                    if lib in line:
                        warnings.append(f"[Rule B0 - Obsolete Library Bloat] Line {idx}: Legacy 2006 library '{lib}' detected. Modernize with ClassicAPI / NamPower.")

            # 10. AP-09 / Rule C11: Same-Layer Background/Icon Occlusion Risk & Child Mouse Interception
            if not self._is_suppressed(line, "C11") and not is_comment:
                if re.search(r'CreateTexture\s*\(\s*nil\s*,\s*["\']OVERLAY["\']\s*\)', line) and re.search(r'(?:[Bb]g|[Bb]ackground)\b', line):
                    infos.append(f"[Rule C11 - Same-Layer Occlusion Risk] Line {idx}: Background texture created on 'OVERLAY' layer. Place in 'BACKGROUND' or 'BORDER'.")
            if not self._is_suppressed(line, "AP-09") and not is_comment:
                if re.search(r'\b(?:bar|statusbar|icon|cooldown)\w*:EnableMouse\s*\(\s*true\s*\)', line, re.IGNORECASE):
                    infos.append(f"[Rule C3 / AP-09 - Child Mouse Interception] Line {idx}: Child element explicitly enabled mouse. Only parent Button should receive clicks to prevent dead zones.")

            # 11. AP-24: Verbose Time Strings in Compact Rows
            if not self._is_suppressed(line, "AP-24") and not is_comment:
                if '"Just now"' in line or "'Just now'" in line:
                    warnings.append(f"[Anti-Pattern 24 - Verbose Time String] Line {idx}: 'Just now' string detected in row formatter. Use compact '0s' / 'now'.")

            # 12. AP-16: Naive table.sort on fixed buffer
            if not self._is_suppressed(line, "AP-16") and not is_comment:
                if re.search(r'\btable\.sort\s*\(\s*(?:roster|buffer|enemies|units)\s*[,|\)]', line) and not 'active' in line.lower():
                    infos.append(f"[Anti-Pattern 16 - Unbounded Buffer Sort] Line {idx}: 'table.sort' detected on entity buffer. Use bounded active sort.")

            # 13. AP-22: Inline Closures in High-Frequency Tickers
            if not self._is_suppressed(line, "AP-22") and not is_comment:
                if re.search(r'C_Timer\.NewTicker\s*\([^,]+,\s*function\b', line):
                    infos.append(f"[Anti-Pattern 22 - Inline Ticker Closure] Line {idx}: Inline closure passed to C_Timer.NewTicker. Bind a static function or method to avoid GC churn.")

            # 14. Event callback signatures
            # VanillaForge v3 intentionally does not lint `(self, event, ...)` as an
            # error. ClassicAPI supports modern positional frame-script arguments.
            # XML bodies, direct calls, and custom dispatchers remain context-sensitive.

            # 15. AP-27: Legacy Manual Bag Sort Loops / Reentrant Container Sorting
            if not self._is_suppressed(line, "AP-27") and not is_comment:
                if re.search(r'PickupContainerItem\s*\(', line) and re.search(r'for\s+\w+\s*=', line):
                    warnings.append(f"[Anti-Pattern 27 - Legacy Manual Bag Sort Loop] Line {idx}: Manual item pickup loop detected. Use native C_Container.SortBags() / SortBankBags() coroutine.")

            # 16. Rule C13 / AP-28: Title-Bar Action Button Standards & Highlight Trap
            if not self._is_suppressed(line, "C13") and not self._is_suppressed(line, "AP-28") and not is_comment:
                # Detect ButtonHilight-Square on window chrome / title bar action buttons
                if 'ButtonHilight-Square' in line:
                    if re.search(r'(?:Sort|Title|Header|Close|Settings|Options)', current_button_name, re.IGNORECASE) or 'Frame.xml' in filepath:
                        infos.append(f"[Rule C13 / AP-28 - Chrome Highlight Mismatch] Line {idx}: 'ButtonHilight-Square' detected on '{current_button_name or 'window chrome'}'. Window chrome buttons must use soft circular highlights ('UI-Panel-MinimizeButton-Highlight' or 'UI-Common-MouseHilight').")

                # In XML, detect custom button textures defined without setAllPoints="true"
                if filepath.endswith('.xml') and re.search(r'<(?:Normal|Pushed|Highlight)Texture\b[^>]*file\s*=\s*["\'][^"\']*(?:assets|AddOns)[^"\']*["\']', line):
                    if 'setAllPoints="true"' not in line and "setAllPoints='true'" not in line:
                        infos.append(f"[Rule C13 / AP-28 - Unscaled Texture Crop Risk] Line {idx}: Custom texture file defined without 'setAllPoints=\"true\"'. In WoW 1.12.1 FrameXML, omitting setAllPoints causes unscaled top-left pixel crops.")

                # In XML, detect static TOPRIGHT offset guessing relative to CloseButton
                if re.search(r'relativeTo\s*=\s*["\']\$parentCloseButton["\']', line) and re.search(r'relativePoint\s*=\s*["\']TOPRIGHT["\']', line):
                    infos.append(f"[Rule C13 / AP-28 - Title-Bar Offset Guessing] Line {idx}: Static TOPRIGHT offset guessing detected for close button sibling. Anchor using 'point=\"CENTER\" relativeTo=\"$parentCloseButton\" relativePoint=\"CENTER\"' with y=\"0\" per Rule C13.")

            # 17. Rule C14 / AP-29: In-Game Notification Tone & Developer Meta-Jargon
            if not self._is_suppressed(line, "C14") and not self._is_suppressed(line, "AP-29") and not is_comment:
                # Check for developer implementation jargon in player messages / localizations
                if re.search(r'(?:AddMessage|UIErrorsFrame|Print|L\["[^"]+"\]\s*=|L\[\'[^\']+\'\]\s*=).*["\'][^"\']*\b(?:C\+\+|coroutine)\b', line, re.IGNORECASE) or re.search(r'["\'][^"\']*\b(?:via C\+\+|with C\+\+|C\+\+ engine|via ClassicAPI C\+\+)\b', line, re.IGNORECASE):
                    warnings.append(f"[Rule C14 / AP-29 - Developer Meta-Jargon in UI] Line {idx}: Developer meta-jargon ('C++', 'coroutine') detected in user-facing text. Communicate state changes cleanly without implementation details.")
                # Check for progressive waiting ellipsis in UI messages (e.g. "Sorting bags...", "Scanning...")
                if re.search(r'["\'](?:Sorting|Cleaning|Filtering|Processing)(?:\s+bags|\s+items|\s+bank)?\.\.\.["\']', line, re.IGNORECASE):
                    warnings.append(f"[Rule C14 / AP-29 - Progressive Ellipsis in UI] Line {idx}: Progressive waiting ellipsis detected in player-facing string. Modern client actions must use instant past-tense confirmations (e.g. 'Bags sorted.').")

            # 18. Rule C15 / AP-31: Zero-Thrash Event-Driven Modernization (Layout & Render Thrashing)
            if not self._is_suppressed(line, "C15") and not self._is_suppressed(line, "AP-31") and not is_comment:
                if re.search(r':ClearAllPoints\s*\(\s*\)', line) and re.search(r':SetPoint\s*\(', line):
                    infos.append(f"[Rule C15 / AP-31 - Layout Thrashing] Line {idx}: Inline ClearAllPoints + SetPoint detected. Cache anchor offsets and mutate points only on state diffs to avoid C++ UI frame tree recalculations.")

        return errors, warnings, infos

    @staticmethod
    def _normalize_toc_entry(entry):
        """Normalize a TOC runtime entry to the host platform."""
        return entry.replace('\\', os.sep).replace('/', os.sep)

    def audit_toc_file(self, toc_path, addon_dir):
        """Audit a WoW TOC as a first-class addon manifest."""
        errors, warnings, infos = [], [], []
        declared = set()

        try:
            with open(toc_path, 'r', encoding='utf-8', errors='replace') as tf:
                raw_lines = tf.readlines()
        except Exception as e:
            return [f"[TOC Read Error] Cannot read manifest: {e}"], [], [], declared

        dependency_fields = {
            'dependencies', 'dependency', 'requireddeps', 'requireddep',
            'optionaldeps', 'optionaldep'
        }
        addon_abs = os.path.abspath(addon_dir)

        for idx, raw_line in enumerate(raw_lines, 1):
            stripped = raw_line.strip()
            if not stripped:
                continue

            if stripped.startswith('##'):
                meta = re.match(r'^##\s*([^:]+)\s*:\s*(.*)$', stripped)
                if meta:
                    key = meta.group(1).strip().lower()
                    value = meta.group(2).strip()
                    if key in dependency_fields and re.search(r'\bdxvk\b', value, re.IGNORECASE):
                        warnings.append(
                            f"[Rule H8 - Invalid Addon Dependency] Line {idx}: "
                            "DXVK appears in TOC dependency metadata. DXVK is runtime/rendering "
                            "infrastructure, not a Lua addon dependency."
                        )
                continue

            if stripped.startswith('#'):
                continue

            # Conservative manifest validation: Lua/XML are known runtime entries.
            if not re.search(r'\.(?:lua|xml)$', stripped, re.IGNORECASE):
                continue

            normalized = self._normalize_toc_entry(stripped)
            declared_path = os.path.abspath(os.path.normpath(os.path.join(addon_dir, normalized)))
            rel = os.path.normcase(os.path.relpath(declared_path, addon_dir))
            declared.add(rel)

            try:
                inside_addon = os.path.commonpath([addon_abs, declared_path]) == addon_abs
            except ValueError:
                inside_addon = False

            if not inside_addon:
                errors.append(
                    f"[TOC Manifest Error] Line {idx}: Runtime entry escapes addon root: '{stripped}'"
                )
            elif not os.path.isfile(declared_path):
                errors.append(
                    f"[TOC Manifest Error] Line {idx}: Declared runtime file does not exist: '{stripped}'"
                )

        return errors, warnings, infos, declared

    def audit_addon_dir(self, dir_path):
        results = {}
        total_errors = 0
        total_warnings = 0
        total_infos = 0

        # Optional dependency/startup guard inspection.
        # VanillaForge v3 does NOT require every addon to guard every installed DLL.
        # Environment availability is not the same thing as per-addon dependency.
        has_startup_guard = False
        outdated_guard = False
        for root, _, files in os.walk(dir_path):
            for f in files:
                if not f.endswith('.lua'):
                    continue
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8', errors='replace') as lf:
                    c = lf.read()
                if 'CLASSIC_API_VERSION' in c or 'MIN_CLASSIC_API' in c:
                    has_startup_guard = True
                    m = re.search(r'MIN_CLASSIC_API\s*=\s*(\d+)', c)
                    if m and int(m.group(1)) < MIN_CLASSIC_API:
                        outdated_guard = True

        # Check README & Directory Standards
        readme_path = os.path.join(dir_path, 'README.md')
        readme_warnings = []
        if outdated_guard:
            readme_warnings.append("[Dependency Guard - Outdated ClassicAPI Minimum] Addon uses MIN_CLASSIC_API < 11510. VanillaForge baseline is ClassicAPI v1.15.10+ (11510).")
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8', errors='replace') as f:
                rm = f.read()
                if '|cff' in rm or '|r' in rm:
                    readme_warnings.append("[Rule H5 - Raw WoW Colors] README.md contains raw WoW color codes (|cff.../|r). Clean to standard Markdown.")
                if '144Hz+' in rm:
                    readme_warnings.append("[Style - Redundant Marketing] README.md contains '144Hz+'. Change to clean 'DXVK'.")
                if 'VanillaForge' in rm or '-Octo' in rm or '[Octo]' in rm:
                    readme_warnings.append("[Branding - Legacy Server/Framework Name] README.md contains legacy 'Octo' branding. Keep public addon repositories server-neutral unless intentional.")
                if re.search(r'(?:prerequisite|requirement|dependency|dependencies).*?(dxvk)', rm, re.IGNORECASE):
                    readme_warnings.append("[Rule H8 - Gratuitous DLL Requirement] README.md lists 'DXVK' as an addon dependency. DXVK is a client rendering translation layer, not an addon API requirement. Remove it.")

        # Project structure diagnostics. Kept intentionally conservative.
        structure_warnings = []

        # Treat root TOC files as first-class addon manifests.
        declared_runtime_files = set()
        toc_files = sorted(
            f for f in os.listdir(dir_path)
            if f.lower().endswith('.toc') and os.path.isfile(os.path.join(dir_path, f))
        )
        for f in toc_files:
            toc_path = os.path.join(dir_path, f)
            toc_errors, toc_warnings, toc_infos, declared = self.audit_toc_file(toc_path, dir_path)
            declared_runtime_files.update(declared)

            with open(toc_path, 'r', encoding='utf-8', errors='replace') as tf:
                tc = tf.read()
            if 'VanillaForge' in tc or '[Octo]' in tc or '-Octo' in tc:
                toc_warnings.append(
                    "[Branding - Legacy Server/Framework Name] TOC contains internal "
                    "framework/server branding. Keep public addon metadata server-neutral unless intentional."
                )

            results[f] = (toc_errors, toc_warnings, toc_infos)
            total_errors += len(toc_errors)
            total_warnings += len(toc_warnings)
            total_infos += len(toc_infos)

        # Reverse manifest integrity is advisory. Unlisted runtime-looking files
        # can be intentional, so never turn this into an automatic ERROR.
        # Root Bindings.xml is client-managed binding metadata in WoW 1.12.1
        # and is intentionally not an ordinary TOC runtime entry.
        excluded_roots = {
            'test', 'tests', 'tool', 'tools', 'script', 'scripts',
            'example', 'examples', 'docs', 'doc', '.git', '.github'
        }
        if toc_files:
            for root, _, files in os.walk(dir_path):
                rel_root = os.path.relpath(root, dir_path)
                parts = [] if rel_root == '.' else [p.lower() for p in Path(rel_root).parts]
                if any(part in excluded_roots for part in parts):
                    continue
                for f in files:
                    if not f.lower().endswith(('.lua', '.xml')):
                        continue
                    filepath = os.path.join(root, f)
                    rel = os.path.normcase(os.path.relpath(filepath, dir_path))
                    if (
                        os.path.normcase(os.path.abspath(root))
                        == os.path.normcase(os.path.abspath(dir_path))
                        and f.lower() == 'bindings.xml'
                    ):
                        continue
                    if rel not in declared_runtime_files:
                        structure_warnings.append(
                            f"[Possible Orphan Runtime File] '{os.path.relpath(filepath, dir_path)}' "
                            "is not referenced by a root TOC. This may be intentional; inspect before changing."
                        )

        # Scan all Lua and XML files
        for root, _, files in os.walk(dir_path):
            for f in sorted(files):
                if f.endswith('.lua') or f.endswith('.xml'):
                    filepath = os.path.join(root, f)
                    rel = os.path.relpath(filepath, dir_path)
                    errs, warns, infs = self.audit_file(filepath)
                    results[rel] = (errs, warns, infs)
                    total_errors += len(errs)
                    total_warnings += len(warns)
                    total_infos += len(infs)

        return results, has_startup_guard, readme_warnings, structure_warnings, total_errors, total_warnings, total_infos


def main():
    parser = argparse.ArgumentParser(description="VanillaForge Addon Linter & Heuristic Static Analysis Scanner (v3.1)")
    parser.add_argument("target", help="Path to Lua file or AddOn directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors (exit code 1 on warnings)")
    parser.add_argument("--ignore", nargs="*", default=[], help="Global rules to suppress (e.g. --ignore A3 D1)")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"{RED}[ERROR] Target path does not exist: {target}{RESET}")
        sys.exit(1)

    auditor = VanillaForgeAuditor(global_ignores=args.ignore)

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
        results, has_guard, readme_warnings, structure_warnings, total_errors, total_warnings, total_infos = auditor.audit_addon_dir(target)

        if has_guard:
            print(f"  {INFO_BADGE} Dependency Guard: ClassicAPI guard detected; configured minimum inspected")
        else:
            print(f"  {INFO_BADGE} Dependency Guard: None detected (optional; dependencies are capability-driven)")

        if readme_warnings:
            for rw in readme_warnings:
                print(f"  {WARN_BADGE} README Check: {rw}")
                total_warnings += 1
        else:
            print(f"  {PASS_BADGE} Documentation: No high-confidence README hazards detected")

        if structure_warnings:
            for sw in structure_warnings:
                print(f"  {WARN_BADGE} Structure Check: {sw}")
                total_warnings += 1

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
            print(f"{BOLD}{GREEN}CLEAN STATIC SCAN: no detected errors or warnings.{RESET}\n")
            sys.exit(0)
        elif total_errors == 0:
            print(f"{BOLD}{YELLOW}STATIC SCAN PASSED: Zero detected errors ({total_warnings} advisory warning(s)).{RESET}\n")
            sys.exit(1 if args.strict else 0)
        else:
            print(f"{BOLD}{RED}STATIC SCAN FAILED: {total_errors} error(s) and {total_warnings} warning(s) detected.{RESET}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
