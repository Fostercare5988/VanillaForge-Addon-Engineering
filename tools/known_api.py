#!/usr/bin/env python3
"""Which names exist: the client's own, and what the DLL docs describe.

    python -B tools/known_api.py "<addon folder>"

The linter asks this for every function an addon calls and every event it
registers (rules K1 and K2). A name is known when it appears in

  - the local copy of the DLL maintainers' docs (.private/upstream), without
    the files that list what does not exist on this client (upstream's
    TODO.md, the 3.3.5 and Turtle API lists),
  - the client's own FrameXML (.private/framexml), or
  - the addon itself (a function, local, field or frame it defines).

This is "grep the docs for the exact name first" (VANILLAFORGE.md section 1
rule 4) done by a tool. It catches a name that was made up, or taken from a
later client. It does not prove a signature: a name the docs only mention
still passes, so a spec cites the doc heading of each call.

A call into another addon is a connection, and is not in any doc: mark the
line `-- vanillaforge-ignore: K1` and say there which addon it is.

Both copies are made by tools/fetch_upstream_docs.py and
tools/extract_framexml.py. Without them nothing is checked.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".private" / "upstream"
FRAMEXML = ROOT / ".private" / "framexml"

# Docs that list functions this client does not have.
NOT_THIS_CLIENT = {"todo.md", "blizzardscriptapi_3.3.5.md", "turtlescriptapi.md"}
TEXT_SUFFIXES = {".md", ".txt", ".lua", ".xml", ".toc", ".cpp", ".h"}

IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
WORD = re.compile(IDENT)
KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if", "in", "local",
            "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"}
# Lua 5.0's library and ClassicAPI's 5.1 backports; the docs name most of them,
# and no doc is needed to know they exist.
LUA = set("""assert collectgarbage dofile error gcinfo getfenv getmetatable ipairs loadstring next pairs pcall
print rawequal rawget rawset select setfenv setmetatable tonumber tostring type unpack xpcall string table math
bit byte char dump find format gfind gmatch gsub len lower match rep reverse sub upper concat foreach foreachi
getn insert maxn remove setn sort wipe abs acos asin atan atan2 ceil cos deg exp floor fmod frexp huge ldexp log
log10 max min mod modf pi pow rad random randomseed sin sqrt tan band bor bxor bnot lshift rshift arshift date
time difftime debugstack getglobal setglobal strsub strlen strfind strlower strupper strrep strbyte strchar
strmatch strtrim strsplit strjoin strconcat tinsert tremove tContains this event self arg1 arg2 arg3 arg4 arg5
arg6 arg7 arg8 arg9 _G""".split())

BARE_CALL = re.compile(r"(?<![\w.:])(%s)\s*\(" % IDENT)
DOTTED_CALL = re.compile(r"(?<![\w.:])(%s(?:\s*\.\s*%s)+)\s*\(" % (IDENT, IDENT))
METHOD_CALL = re.compile(r":\s*(%s)\s*\(" % IDENT)
EVENT_USE = re.compile(r"""(?:\bRegister\w*Event\w*\s*\(\s*|\bevent\s*[=~]=\s*)["']([A-Z][A-Z0-9_]*_[A-Z0-9_]+)["']""")
XML_SCRIPT = re.compile(r"<(On[A-Za-z]+)(?:\s[^>]*)?>(.*?)</\1>", re.S)
IGNORE = re.compile(r"vanillaforge-ignore:\s*([A-Za-z0-9_\-,\s]+)", re.I)


def words_of(folder: Path, skip=frozenset()) -> set[str]:
    found: set[str] = set()
    if not folder.is_dir():
        return found
    for path in folder.rglob("*"):
        if path.suffix.lower() in TEXT_SUFFIXES and path.name.lower() not in skip and path.is_file():
            found.update(WORD.findall(path.read_text("utf-8", errors="replace")))
    return found


class KnownAPI:
    """The names the client and the DLL docs know."""

    def __init__(self, upstream: Path = UPSTREAM, framexml: Path = FRAMEXML):
        self.names = words_of(upstream, NOT_THIS_CLIENT) | words_of(framexml)
        self.loaded = bool(self.names)
        self.names |= LUA

    def __contains__(self, name: str) -> bool:
        return name in self.names


def mask_lua(text: str) -> tuple[str, str]:
    """(code, with_strings): comments blanked in both, strings blanked in the
    first. Lengths and newlines stay, so offsets give line numbers."""
    code, keep = list(text), list(text)
    i, n = 0, len(text)

    def blank(start, end, strings):
        for j in range(start, end):
            if text[j] != "\n":
                code[j] = " "
                if not strings:
                    keep[j] = " "

    while i < n:
        c = text[i]
        if c == "-" and text.startswith("--", i):
            m = re.match(r"--\[(=*)\[", text[i:])
            if m:
                close = text.find("]" + m.group(1) + "]", i)
                end = n if close < 0 else close + len(m.group(1)) + 2
            else:
                end = text.find("\n", i)
                end = n if end < 0 else end
            blank(i, end, False)
            i = end
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            blank(i + 1, min(j, n), True)
            i = j + 1
        elif c == "[" and re.match(r"\[(=*)\[", text[i:]):
            level = re.match(r"\[(=*)\[", text[i:]).group(1)
            close = text.find("]" + level + "]", i)
            end = n if close < 0 else close + len(level) + 2
            blank(i + len(level) + 2, max(i, end - len(level) - 2), True)
            i = end
        else:
            i += 1
    return "".join(code), "".join(keep)


def defined_names(code: str, with_strings: str) -> set[str]:
    """Every name a piece of Lua defines: locals, parameters, loop variables,
    functions, and anything assigned (globals, fields, table keys)."""
    names: set[str] = set()
    for m in re.finditer(r"\blocal\s+function\s+(%s)" % IDENT, code):
        names.add(m.group(1))
    for m in re.finditer(r"\bfunction\s+(%s(?:\s*[.:]\s*%s)*)\s*\(" % (IDENT, IDENT), code):
        names.update(WORD.findall(m.group(1)))
    for m in re.finditer(r"\bfunction\b[^(\n]*\(([^)]*)\)", code):
        names.update(WORD.findall(m.group(1)))
    for m in re.finditer(r"\bfor\s+([\w\s,]+?)\s+(?:in\b|=)", code):
        names.update(WORD.findall(m.group(1)))
    for m in re.finditer(r"\blocal\s+(?!function\b)(%s(?:\s*,\s*%s)*)[ \t]*(?:=[ \t]*([^\n]*))?" % (IDENT, IDENT), code):
        left = WORD.findall(m.group(1))
        right = [part.strip() for part in (m.group(2) or "").split(",")]
        for index, name in enumerate(left):
            # `local GetTime = GetTime` keeps the game's function under its own
            # name: it defines nothing, and its calls are still checked.
            if not (index < len(right) and right[index] == name):
                names.add(name)
    # Everything else that is assigned: globals, fields, table keys. The local
    # declarations were read above (and their kept globals left out).
    rest = re.sub(r"\blocal\s+(?!function\b)%s(?:\s*,\s*%s)*" % (IDENT, IDENT), lambda m: " " * len(m.group(0)), code)
    for m in re.finditer(r"(%s)[ \t]*=(?!=)" % IDENT, rest):
        names.add(m.group(1))
    # Globals made by name: a named frame, _G["X"] = ..., setglobal("X", ...).
    for m in re.finditer(r"""\bCreateFrame\s*\(\s*["'][^"']*["']\s*,\s*["'](%s)["']""" % IDENT, with_strings):
        names.add(m.group(1))
    for m in re.finditer(r"""(?:\b_G\s*\[\s*|\bsetglobal\s*\(\s*)["'](%s)["']""" % IDENT, with_strings):
        names.add(m.group(1))
    return names - KEYWORDS


def lua_parts(path: Path) -> list[tuple[int, str]]:
    """(offset line, Lua text) of a file: the whole of a .lua, the script
    bodies of an .xml."""
    text = path.read_text("utf-8", errors="replace")
    if path.suffix.lower() == ".lua":
        return [(0, text)]
    text = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return [(text.count("\n", 0, m.start(2)), m.group(2)) for m in XML_SCRIPT.finditer(text)]


def addon_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in (".lua", ".xml") and p.is_file()
                  and ".git" not in p.parts)


def addon_names(folder: Path) -> set[str]:
    names: set[str] = set()
    for path in addon_files(folder):
        for _, text in lua_parts(path):
            names |= defined_names(*mask_lua(text))
        if path.suffix.lower() == ".xml":
            names.update(re.findall(r'\bname="(%s)"' % IDENT, path.read_text("utf-8", errors="replace")))
    for toc in folder.glob("*.toc"):
        for line in toc.read_text("utf-8", errors="replace").splitlines():
            m = re.match(r"##\s*SavedVariables(?:PerCharacter)?\s*:\s*(.*)", line, re.I)
            if m:
                names.update(WORD.findall(m.group(1)))
    return names


def suppressed(line: str, rule: str) -> bool:
    m = IGNORE.search(line)
    return bool(m) and bool({"ALL", rule} & {r.strip().upper() for r in m.group(1).split(",")})


def check_file(path: Path, own: set[str], known: KnownAPI) -> list[tuple[str, int, str]]:
    """(rule, line, name) for each call and event of a file that nothing knows."""
    findings: list[tuple[str, int, str]] = []
    for offset, text in lua_parts(path):
        code, with_strings = mask_lua(text)
        raw_lines = text.splitlines()
        seen: set[tuple[str, str]] = set()

        def report(rule, position, name):
            line = code.count("\n", 0, position)
            if (rule, name) in seen or (line < len(raw_lines) and suppressed(raw_lines[line], rule)):
                return
            seen.add((rule, name))
            findings.append((rule, offset + line + 1, name))

        for m in BARE_CALL.finditer(code):
            name = m.group(1)
            if name in KEYWORDS or name in own or name in known:
                continue
            if re.search(r"\bfunction\s*$", code[max(0, m.start() - 12):m.start()]):
                continue
            report("K1", m.start(), name)
        for m in DOTTED_CALL.finditer(code):
            parts = WORD.findall(m.group(1))
            if parts[0] in own or parts[0] in KEYWORDS:
                continue
            # A table nothing knows may be a frame named at run time or another
            # addon's; only a C_ namespace is certainly meant as the game's.
            if parts[0] not in known:
                if parts[0].startswith("C_"):
                    report("K1", m.start(), ".".join(parts))
                continue
            if any(part not in known and part not in own for part in parts[1:]):
                report("K1", m.start(), ".".join(parts))
        for m in METHOD_CALL.finditer(code):
            if m.group(1) not in own and m.group(1) not in known:
                report("K1", m.start(), ":" + m.group(1))
        for m in EVENT_USE.finditer(with_strings):
            if m.group(1) not in known:
                report("K2", m.start(), m.group(1))
    return findings


MESSAGES = {
    "K1": "[Rule K1 - Unknown API] Line {line}: '{name}' is in no DLL doc and not in the client. Grep the docs "
          "for the real name; mark a call into another addon '-- vanillaforge-ignore: K1'.",
    "K2": "[Rule K2 - Unknown Event] Line {line}: '{name}' is in no DLL doc and not in the client's event list.",
}


def check_addon(folder, known: KnownAPI | None = None, ignores=()) -> dict[str, list[str]]:
    """Messages per file (relative path), empty when the doc copies are missing."""
    folder = Path(folder)
    known = known or KnownAPI()
    if not known.loaded:
        return {}
    ignores = {rule.upper() for rule in ignores}
    own = addon_names(folder)
    result: dict[str, list[str]] = {}
    for path in addon_files(folder):
        messages = [MESSAGES[rule].format(line=line, name=name) for rule, line, name in check_file(path, own, known)
                    if rule not in ignores and "ALL" not in ignores]
        if messages:
            result[str(path.relative_to(folder))] = messages
    return result


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.split("\n\n", 1)[0], file=sys.stderr)
        return 2
    known = KnownAPI()
    if not known.loaded:
        print("known_api: no doc copies; run tools/fetch_upstream_docs.py and tools/extract_framexml.py",
              file=sys.stderr)
        return 2
    result = check_addon(argv[0], known)
    for name, messages in result.items():
        for message in messages:
            print(f"{name}: {message}")
    print(f"{sum(map(len, result.values()))} unknown name(s) in {len(result)} file(s)")
    return 1 if result else 0


if __name__ == "__main__":
    sys.exit(main())
