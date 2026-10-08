#!/usr/bin/env python3
"""Read-only source inventory. Sites are review candidates, never performance proof."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
from bisect import bisect_left
import hashlib
import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path, PureWindowsPath

from vanillaforge_linter import HeuristicStructuralScanner as Scanner, VanillaForgeAuditor

LIMITS = {"files": 1024, "edges": 8192, "file_bytes": 2_000_000, "total_bytes": 32_000_000,
          "depth": 64, "sites_per_module": 500, "lint_records_per_kind": 100}
SCENARIOS = ["login/reload and persistence", "combat enter/leave and mob deaths",
             "loot and inventory/equipment bursts", "aura and roster changes",
             "inspect/target/nameplate changes", "hidden/reopened UI and optional integrations"]
CALLS = {
    "events": r"RegisterEvent|UnregisterEvent|RegisterAllEvents|UnregisterAllEvents",
    "callbacks": r"SetScript|HookScript",
    "timers": r"C_Timer\.(?:After|NewTimer|NewTicker)|ScheduleEvent|ScheduleRepeatingEvent",
    "enhanced_api_sites": r"C_[A-Za-z_]\w*\.[A-Za-z_]\w*|UnitXP",
    "reads_scans": r"GetItemInfo|GetInventoryItem\w*|GetContainerItem\w*|NotifyInspect|InspectUnit|"
                  r"UnitBuff|UnitDebuff|GetPlayerBuff\w*|EnumerateFrames|GetChildren|UnitExists|UnitGUID|"
                  r"C_UnitAuras\.[A-Za-z_]\w*",
    "ui_writes": r"SetText|SetTexture|SetPoint|ClearAllPoints|SetVertexColor|SetAlpha|"
                 r"SetWidth|SetHeight|SetSize|SetValue|Show|Hide",
}
PATTERNS = {kind: re.compile(r"(?<![\w])(" + names + r")\s*\(") for kind, names in CALLS.items()}
HANDLER = re.compile(r"<(On\w+|Binding)\b[^>]*>(.*?)</\1\s*>", re.S)
ARGUMENT = re.compile(r"\s*(['\"])([^'\"\n]*)\1\s*(?=[,)])")


def inside(path, root):
    return path == root or root in path.parents


def lua_sites(text, first_line=1):
    code, comments = Scanner.mask_lua(text)
    code, comments = "".join(code), "".join(comments)
    newlines = [match.start() for match in re.finditer("\n", code)]
    sites = []
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(code):
            site = {"kind": kind, "api": match[1], "line": first_line + bisect_left(newlines, match.start())}
            if kind in {"events", "callbacks"} or match[1] == "UnitXP":
                argument = ARGUMENT.match(comments, match.end())
                site["argument"] = argument[2] if argument else None
                site["dynamic_argument"] = argument is None and not match[1].endswith("AllEvents")
                if argument and argument[2] == "OnUpdate":
                    site["kind"] = "on_update"
            sites.append(site)
    return sites


def source_sites(text, suffix):
    if suffix == ".lua":
        sites = lua_sites(text)
    else:
        visible = "".join(Scanner.mask_xml(text)[0])
        newlines = [match.start() for match in re.finditer("\n", visible)]
        sites = []
        for match in HANDLER.finditer(visible):
            line = bisect_left(newlines, match.start()) + 1
            sites.append({"kind": "on_update" if match[1] == "OnUpdate" else "xml_handler",
                          "api": match[1], "line": line})
            body = re.sub(r"<!\[CDATA\[|\]\]>", lambda m: " " * len(m[0]), match[2])
            sites.extend(lua_sites(html.unescape(body), bisect_left(newlines, match.start(2)) + 1))
    return sorted(sites, key=lambda site: (site["line"], site["kind"], site["api"]))


def audit(addon, toc_name=None):
    addon = Path(addon).resolve()
    if not addon.is_dir():
        raise ValueError("Addon directory does not exist")
    tocs = [addon / toc_name] if toc_name else sorted(addon.glob("*.toc"))
    if not tocs:
        raise ValueError("No root TOC found; use --toc for an explicit manifest")
    report = {"format": 1, "addon": str(addon), "limits": LIMITS, "graph": [], "modules": [],
              "graph_errors": [], "tests": {"status": "not_run"},
              "review": {"status": "pending", "scenarios": SCENARIOS,
                         "api_provider_semantics_and_cost": "pending", "measured_baseline_and_after": "pending"},
              "limitations": ["Lexical sites and lint are candidates, not defect or performance proof.",
                              "No Lua compilation, dynamic load discovery, API equivalence or native gameplay verification.",
                              "TOC/XML source closure only; referenced media and dependencies need separate review.",
                              "No code, configuration or runtime changes; optional tests execute local Python when requested."]}
    visited, active, total = set(), set(), 0
    auditor = VanillaForgeAuditor()

    def walk(base, name, owner, depth=0):
        nonlocal total
        if len(report["graph"]) + len(report["graph_errors"]) >= LIMITS["edges"]:
            raise ValueError("Source graph edge limit exceeded")
        if PureWindowsPath(name).is_absolute() or PureWindowsPath(name).drive:
            report["graph_errors"].append(f"{owner}: absolute reference rejected: {name}")
            return
        path = (base / name.replace("\\", "/")).resolve()
        if not inside(path, addon):
            report["graph_errors"].append(f"{owner}: reference escapes addon: {name}")
            return
        relative = path.relative_to(addon).as_posix()
        report["graph"].append({"from": owner, "to": relative})
        if path in active:
            report["graph_errors"].append(f"{owner}: load cycle: {relative}")
            return
        if path in visited:
            return
        if depth > LIMITS["depth"] or len(visited) >= LIMITS["files"]:
            raise ValueError("Source graph depth/file limit exceeded")
        if not path.is_file():
            report["graph_errors"].append(f"{owner}: missing file: {relative}")
            return
        if path.stat().st_size > LIMITS["file_bytes"]:
            raise ValueError(f"File size limit exceeded: {relative}")
        data = path.read_bytes()
        total += len(data)
        if total > LIMITS["total_bytes"]:
            raise ValueError("Source graph total size limit exceeded")
        visited.add(path)
        active.add(path)
        text, suffix = data.decode("utf-8-sig", errors="replace"), path.suffix.lower()
        module = {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                  "review_status": "pending", "review_fields": ["ownership/lifecycle", "frequency/fanout",
                  "identity/invalidation", "API capability alternatives", "UI delta writes", "cleanup/integration"]}
        if suffix in {".lua", ".xml", ".toc"}:
            lint = (auditor.audit_toc_file(str(path), str(addon))[:3] if suffix == ".toc"
                    else auditor.audit_file(str(path)))
            module["lint"] = {kind: {"count": len(items), "records": items[:LIMITS["lint_records_per_kind"]]}
                              for kind, items in zip(("errors", "warnings", "infos"), lint)}
        if suffix in {".lua", ".xml"}:
            sites = source_sites(text, suffix)
            module.update(sites=sites[:LIMITS["sites_per_module"]], site_count=len(sites),
                          sites_truncated=len(sites) > LIMITS["sites_per_module"])
        report["modules"].append(module)
        if suffix == ".toc":
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    walk(addon, line, relative, depth + 1)
        elif suffix == ".xml":
            try:
                if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
                    raise ValueError("DTD/entity declarations are unsupported")
                for element in ET.fromstring(text).iter():
                    if element.tag.split("}")[-1] in {"Include", "Script"}:
                        name = element.get("file", element.get("File"))
                        if name:
                            walk(path.parent, name, relative, depth + 1)
            except (ET.ParseError, ValueError) as error:
                report["graph_errors"].append(f"{relative}: XML parse error: {error}")
        active.remove(path)

    for toc in tocs:
        walk(addon, str(toc.relative_to(addon)), "TOC")
    bindings = addon / "Bindings.xml"
    if bindings.is_file():
        walk(addon, bindings.name, "client-managed bindings")
    report["module_count"] = len(report["modules"])
    report["review"]["pending_modules"] = len(report["modules"])
    report["status"] = "source_checks_failed" if report["graph_errors"] or any(
        module.get("lint", {}).get("errors", {}).get("count") for module in report["modules"]) else "human_review_pending"
    return report


def run_tests(start, pattern, timeout):
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(start), "-p", pattern, "-v"]
    result = {"command": command, "timeout_seconds": timeout}
    if not start.is_dir():
        return dict(result, status="failed", reason="Test directory does not exist", tests_run=0)
    try:
        completed = subprocess.run(command, cwd=start.parent, capture_output=True, text=True,
                                   errors="replace", timeout=timeout, check=False)
        output = completed.stdout + completed.stderr
        matches = re.findall(r"^Ran (\d+) tests? in ", output, re.M)
        count = int(matches[-1]) if matches else 0
        return dict(result, status="passed" if completed.returncode == 0 and count > 0 else "failed",
                    tests_run=count, returncode=completed.returncode, output_tail=output[-16000:],
                    reason=None if count else "No unittest summary with a nonzero test count")
    except subprocess.TimeoutExpired:
        return dict(result, status="timeout", tests_run=None)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addon", type=Path)
    parser.add_argument("--toc", help="Explicit root TOC filename; otherwise inspect all root *.toc files")
    parser.add_argument("--output", type=Path, help="JSON destination outside addon; default stdout")
    parser.add_argument("--run-tests", action="store_true", help="Execute local Python unittest discovery explicitly")
    parser.add_argument("--test-start", type=Path, help="Test directory; default <addon>/tests")
    parser.add_argument("--test-pattern", default="test*.py")
    parser.add_argument("--test-timeout", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        addon = args.addon.resolve()
        if args.output and inside(args.output.resolve(), addon):
            raise ValueError("Output must be outside the addon directory")
        if not 0 < args.test_timeout <= 600:
            raise ValueError("Test timeout must be > 0 and <= 600 seconds")
        if not args.run_tests and (args.test_start or args.test_pattern != "test*.py"):
            raise ValueError("Test options require --run-tests")
        report = audit(addon, args.toc)
        if args.run_tests:
            report["tests"] = run_tests((args.test_start or addon / "tests").resolve(),
                                        args.test_pattern, args.test_timeout)
        output = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        if args.output:
            args.output.resolve().write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return int(report["status"] == "source_checks_failed" or report["tests"]["status"] in {"failed", "timeout"})
    except (OSError, ValueError) as error:
        print(f"Audit failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
