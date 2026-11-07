#!/usr/bin/env python3
"""The game checks: what an audit could not prove outside the game, until the
player answers it in game.

Open checks come from two places, rebuilt on every run:
  * `UNVERIFIED` notes in the maintained addons' Lua (the addons with a suite in
    regressions/), with the comment lines that continue them;
  * the items under "In-game checks" in .private/audit-<Addon>-<date>.md
    (a heading that says "closed" is skipped).
A check whose text names a `/run` line carries it, so the game can run it.

The answers live in .private/game-checks.json. They arrive through !ErrorLog:
`push` (game closed) writes the open checks into its saved data, `/check` in
game shows them one by one, runs their `/run` line and records ok or bad with a
note, and `pull` reads the answers back. `close` records an answer given here.

  python -B tools/game_checks.py [--addon NAME]   open checks, by addon
  python -B tools/game_checks.py push              pull, then send the open ones
  python -B tools/game_checks.py pull              read the answers from the game
  python -B tools/game_checks.py close ID ok|bad [note]
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".private"
LEDGER = PRIVATE / "game-checks.json"
REGRESSIONS = ROOT / "regressions"
CLIENT = Path(r"C:\Users\Fostercare\Desktop\OctoWoW")
RENAMED = {"MikScrollingBattleText": "FostercareBattleText"}
BEGIN = "-- VanillaForge game checks: begin"
END = "-- VanillaForge game checks: end"
RUN = re.compile(r"`(/(?:run|script) [^`]+)`|(/(?:run|script) .+)$")


def check_id(addon, text):
    return hashlib.sha1((addon + "\n" + " ".join(text.split())).encode("utf-8")).hexdigest()[:8]


# The game's fonts draw plain Latin text; the notes' typography becomes ASCII.
PLAIN = str.maketrans({"→": "->", "←": "<-", "—": "-", "–": "-", "‘": "'", "’": "'",
                       "“": '"', "”": '"', "…": "...", "×": "x", "≥": ">=", "≤": "<="})


def make(addon, where, text):
    text = " ".join(text.translate(PLAIN).split()).encode("ascii", "replace").decode("ascii")
    m = RUN.search(text)
    run = m and (m.group(1) or m.group(2).rstrip(". ")).strip()
    if run and "<" in run:  # a placeholder such as <id>: the player fills it in
        run = None
    return {"id": check_id(addon, text), "addon": addon, "where": where, "text": text, "run": run}


def maintained(addons_dir, regressions=REGRESSIONS):
    """Installed folders of the addons that have a regression suite."""
    suites = {p.name.lower() for p in regressions.iterdir() if p.is_dir() and any(p.glob("test_*.py"))}
    return sorted(d for d in Path(addons_dir).iterdir() if d.is_dir() and d.name.lstrip("!").lower() in suites)


def code_checks(folder):
    """Each UNVERIFIED comment and the comment lines that continue it."""
    found = []
    for path in sorted(Path(folder).rglob("*.lua")):
        lines = path.read_text("utf-8", "replace").splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            at = line.find("--")
            if at >= 0 and "UNVERIFIED" in line[at:]:
                parts, j = [line[line.index("UNVERIFIED", at):].strip()], i + 1
                while j < len(lines) and lines[j].strip().startswith("--") and lines[j].strip("- \t"):
                    parts.append(lines[j].strip()[2:].strip())
                    j += 1
                rel = path.relative_to(folder).as_posix()
                found.append(make(Path(folder).name, "%s:%d" % (rel, i + 1), " ".join(parts)))
                i = j
            else:
                i += 1
    return found


def audit_checks(private=PRIVATE):
    """The items under each audit's "In-game checks" heading."""
    found = []
    for path in sorted(private.glob("audit-*.md")):
        m = re.match(r"audit-(.+?)-\d{4}-\d{2}-\d{2}", path.stem)
        if not m:
            continue
        addon = RENAMED.get(m.group(1), m.group(1))
        section = None
        for n, line in enumerate(path.read_text("utf-8", "replace").splitlines(), 1):
            if line.startswith("#"):
                heading = line.lstrip("#").strip().lower()
                section = [] if heading.startswith("in-game check") and "closed" not in heading else None
                continue
            if section is None:
                continue
            item = re.match(r"\s{0,3}(?:\d+\.|[-*])\s+(.*)", line)
            if item:
                section.append([n, item.group(1)])
                found.append(section[-1])
                found[-1].append((addon, path.name))
            elif line.startswith(" ") and line.strip() and section:
                section[-1][1] += " " + line.strip()
    return [make(addon, "%s:%d" % (name, n), text) for n, text, (addon, name) in found]


def collect(addons_dir, private=PRIVATE, regressions=REGRESSIONS):
    checks = audit_checks(private)
    for folder in maintained(addons_dir, regressions):
        checks += code_checks(folder)
    unique = {}
    for c in checks:
        unique.setdefault(c["id"], c)
    return list(unique.values())


def load_ledger(path=LEDGER):
    return json.loads(path.read_text("utf-8")) if path.is_file() else {}


def save_ledger(ledger, path=LEDGER):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record(ledger, check_id_, verdict, note="", when=None, who="", output=None):
    ledger[check_id_] = {"verdict": verdict, "note": note or "", "when": when or datetime.date.today().isoformat(),
                         "who": who or "", **({"output": output} if output else {})}


def open_checks(checks, ledger):
    return [c for c in checks if c["id"] not in ledger]


# The game's side -------------------------------------------------------------------

def saved_files(wtf):
    return sorted(Path(wtf).glob("Account/*/SavedVariables/!ErrorLog.lua"))


def lua_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def without_block(text):
    return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\r?\n?", "", text, flags=re.S)


def write_checks(path, checks, today=None):
    """Put the checks into !ErrorLog's saved data, in place, keeping the file's endings."""
    raw = path.read_bytes() if path.is_file() else b""
    crlf = b"\r\n" in raw
    text = without_block(raw.decode("utf-8", "replace").replace("\r\n", "\n"))
    rows = []
    for c in checks:
        fields = ["id = %s" % lua_string(c["id"]), "addon = %s" % lua_string(c["addon"]),
                  "where = %s" % lua_string(c["where"]), "text = %s" % lua_string(c["text"])]
        if c.get("run"):
            fields.append("run = %s" % lua_string(c["run"]))
        rows.append("\t{ " + ", ".join(fields) + " },")
    block = "\n".join([BEGIN + " (tools/game_checks.py push, %s)" % (today or datetime.date.today().isoformat()),
                       "ErrorLog_DB = ErrorLog_DB or {}", "ErrorLog_DB.checks = {"] + rows + ["}", END]) + "\n"
    if text and not text.endswith("\n"):
        text += "\n"
    text += block
    data = (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")
    with open(path, "r+b" if path.is_file() else "wb") as f:   # in place: the file keeps its permissions
        f.seek(0)
        f.write(data)
        f.truncate()


def read_answers(path):
    """The answered checks in !ErrorLog's saved data: [{id, verdict, note, at, who, output}]."""
    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        raise SystemExit("pull needs lupa (pip install lupa) to read the saved data")
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(path.read_text("utf-8", "replace"))
    checks = lua.eval("type(ErrorLog_DB) == 'table' and ErrorLog_DB.checks")
    answers = []
    if checks:
        for _, c in checks.items():
            if c["verdict"]:
                answers.append({k: c[k] for k in ("id", "verdict", "note", "at", "who", "output") if c[k] is not None})
    return answers


def game_running():
    if sys.platform != "win32":
        return False
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WoW.exe", "/NH"], capture_output=True, text=True).stdout
    return "wow.exe" in out.lower()


def pull(wtf, ledger):
    got = 0
    for path in saved_files(wtf):
        for a in read_answers(path):
            if a["id"] not in ledger:
                record(ledger, a["id"], a["verdict"], a.get("note"), a.get("at"), a.get("who"), a.get("output"))
                got += 1
    return got


# Command line -------------------------------------------------------------------------

def show(checks, ledger, addon=None):
    out = []
    rows = [c for c in open_checks(checks, ledger) if not addon or c["addon"].lower() == addon.lower()]
    by_addon = {}
    for c in rows:
        by_addon.setdefault(c["addon"], []).append(c)
    out.append("%d open game checks%s." % (len(rows), " for " + addon if addon else ""))
    for name in sorted(by_addon):
        out.append("\n## %s (%d)" % (name, len(by_addon[name])))
        for c in by_addon[name]:
            out.append("- [%s] %s (%s)%s" % (c["id"], c["text"], c["where"], "  run: " + c["run"] if c["run"] else ""))
    bad = [(i, v) for i, v in ledger.items() if v["verdict"] == "bad"]
    if bad and not addon:
        out.append("\n## Answered bad (%d): fix these" % len(bad))
        known = {c["id"]: c for c in checks}
        for i, v in bad:
            c = known.get(i, {})
            out.append("- [%s] %s: %s (%s)" % (i, c.get("addon", "?"), v["note"], c.get("text", "check no longer listed")))
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", default="list", choices=("list", "push", "pull", "close"))
    parser.add_argument("args", nargs="*")
    parser.add_argument("--addon")
    parser.add_argument("--client", type=Path, default=CLIENT)
    args = parser.parse_args(argv)
    addons_dir, wtf = args.client / "Interface" / "AddOns", args.client / "WTF"
    checks, ledger = collect(addons_dir), load_ledger()
    if args.command == "close":
        if len(args.args) < 2 or args.args[1] not in ("ok", "bad"):
            parser.error("close ID ok|bad [note]")
        if args.args[0] not in {c["id"] for c in checks}:
            parser.error("no open check has the id %s" % args.args[0])
        record(ledger, args.args[0], args.args[1], " ".join(args.args[2:]), who="terminal")
        save_ledger(ledger)
        print("Recorded %s: %s." % (args.args[0], args.args[1]))
        return 0
    if args.command in ("pull", "push"):
        got = pull(wtf, ledger)
        save_ledger(ledger)
        print("%d answer(s) read from the game." % got)
    if args.command == "push":
        if game_running():
            print("WoW is running: it would overwrite the saved data at logout. Close the game and push again.")
            return 1
        rows = open_checks(checks, ledger)
        files = saved_files(wtf)
        for path in files:
            write_checks(path, rows)
        print("%d open check(s) sent to %d account(s). In game: /check" % (len(rows), len(files)))
        return 0
    print(show(checks, ledger, args.addon))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
