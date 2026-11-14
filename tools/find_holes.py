#!/usr/bin/env python3
"""Find the holes in one addon: what is unused, stale, hidden or done better by a DLL.

Reads the addon next to every other installed addon, the game's own code
(.private/framexml, from extract_framexml.py --all), the DLL docs
(.private/upstream, from fetch_upstream_docs.py) and every character's saved
settings. Every finding is a lead for the audit questions in VANILLAFORGE.md
section 4, not a verdict: read the code before acting.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
import json
import re
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".private" / "upstream"
FRAMEXML = ROOT / ".private" / "framexml"
REGRESSIONS = ROOT / "regressions"
WOTLK_CATALOG = UPSTREAM / "classicapi" / "docs" / "BlizzardScriptAPI_3.3.5.md"
MEDIA = {".tga", ".blp", ".ttf", ".mp3", ".wav", ".ogg"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# A global worth checking: CamelCase (functions, frames, tables). ALL_CAPS
# constants and lowercase Lua/stdlib names are left out on purpose.
CAMEL = re.compile(r"^(?:C_[A-Za-z0-9_]+|[A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*)$")


# Reading Lua ---------------------------------------------------------------

LUA_TOKEN = re.compile(r"--\[(=*)\[.*?\]\1\]|--[^\n]*|\[(=*)\[.*?\]\2\]"
                       r"|\"(?:\\.|[^\"\\\n])*\"?|'(?:\\.|[^'\\\n])*'?", re.S)
BLANK = re.compile(r"[^\n]")


def strip_lua(text, keep_strings=False):
    """Lua source with comments (and strings, unless kept) blanked; newlines stay."""
    def blank(match):
        token = match.group(0)
        if token.startswith("--"):
            return BLANK.sub(" ", token)
        if keep_strings:
            return token
        if token[0] in "\"'":
            return token[0] + BLANK.sub(" ", token[1:-1]) + token[-1] if len(token) > 1 else token
        return BLANK.sub(" ", token)
    return LUA_TOKEN.sub(blank, text)


def line_of(newlines, position):
    return bisect_left(newlines, position) + 1


TABLE_KEY = re.compile(r"\s*=(?!=)")


def global_uses(code):
    """(name, line) for identifiers that are not fields (no '.' or ':' before)
    and not keys in a table constructor ({ Name = ... })."""
    newlines = [m.start() for m in re.finditer("\n", code)]
    depth = brace_depth(code)
    for match in IDENT.finditer(code):
        j = match.start() - 1
        while j >= 0 and code[j] in " \t":
            j -= 1
        if j >= 0 and code[j] in ".:" and not (code[j] == "." and j > 0 and code[j - 1] == "."):
            continue
        if TABLE_KEY.match(code, match.end()) and depth(match.start()) > 0:
            continue
        yield match.group(0), line_of(newlines, match.start())


def local_names(code):
    names = set()
    for m in re.finditer(r"\blocal\s+function\s+([A-Za-z_]\w*)", code):
        names.add(m.group(1))
    for m in re.finditer(r"\blocal\s+((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)", code):
        names.update(x.strip() for x in m.group(1).split(","))
    for m in re.finditer(r"\bfunction\b[^(]*\(([^)]*)\)", code):
        names.update(x.strip() for x in m.group(1).split(",") if x.strip() and x.strip() != "...")
    for m in re.finditer(r"\bfor\s+((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)\s+in\b", code):
        names.update(x.strip() for x in m.group(1).split(","))
    for m in re.finditer(r"\bfor\s+([A-Za-z_]\w*)\s*=", code):
        names.add(m.group(1))
    return names


# Globals the game sets for every script handler.
HANDLER_GLOBALS = {"this", "self", "event", "arg", "_G"} | {"arg%d" % i for i in range(1, 10)}


def brace_depth(code):
    """depth(position): how many table constructors are open there."""
    opens = [m.start() for m in re.finditer(r"\{", code)]
    closes = [m.start() for m in re.finditer(r"\}", code)]
    return lambda position: bisect_left(opens, position) - bisect_left(closes, position)


def assigned_names(code):
    """Names a Lua file assigns or defines as functions that it never declares
    local. Fields inside table constructors ({ name = 1 }) are not assignments."""
    local, depth = local_names(code), brace_depth(code)
    names = set()
    for m in re.finditer(r"^[ \t]*function\s+([A-Za-z_]\w*)\s*[(]", code, re.M):
        names.add(m.group(1))
    for m in re.finditer(r"^[ \t]*((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)\s*=(?!=)", code, re.M):
        if depth(m.start()) <= 0:
            names.update(x.strip() for x in m.group(1).split(","))
    return names - local - HANDLER_GLOBALS


def global_defs(code):
    """Globals a Lua file defines (not local, not a field)."""
    names = assigned_names(code)
    for m in re.finditer(r"^[ \t]*function\s+([A-Za-z_]\w*)\s*[.:]", code, re.M):
        names.add(m.group(1))
    for m in re.finditer(r"\b_G\s*\[\s*[\"']([A-Za-z_]\w*)[\"']\s*\]\s*=|\b_G\.([A-Za-z_]\w*)\s*=", code):
        names.add(m.group(1) or m.group(2))
    # Named frames: CreateFrame("Type", "Name", ...) makes a global.
    for m in re.finditer(r"CreateFrame\s*\(\s*[\"']\w+[\"']\s*,\s*[\"']([A-Za-z_]\w*)[\"']", code):
        names.add(m.group(1))
    # Named regions: frame:CreateTexture("Name") and CreateFontString("Name") make globals too.
    for m in re.finditer(r":\s*Create(?:Texture|FontString)\s*\(\s*[\"']([A-Za-z_]\w*)[\"']", code):
        names.add(m.group(1))
    # Numbered names built from a prefix ("AlwaysUpFrame" .. n): "Prefix*".
    for m in re.finditer(r"[\"']([A-Za-z_]\w*)[\"']\s*\.\.", code):
        names.add(m.group(1) + "*")
    return names - HANDLER_GLOBALS


def numbered(name, defined):
    m = re.match(r"^([A-Za-z_]\w*?)\d+$", name)
    return bool(m) and m.group(1) + "*" in defined


# Children a template gives every frame that inherits it ("$parentTextLeft1").
TEMPLATE_SUFFIXES = set()
# Per virtual frame: the suffixes of its $parent children, and the template it
# inherits; per file, the frames that inherit a template.
TEMPLATE_CHILDREN, TEMPLATE_PARENT = {}, {}


def template_suffixes(template, seen=None):
    """The $parent children a frame inheriting `template` gets, its own templates' too."""
    seen = seen or set()
    if template in seen:
        return set()
    seen.add(template)
    found = set(TEMPLATE_CHILDREN.get(template, ()))
    for parent in TEMPLATE_PARENT.get(template, ()):
        found |= template_suffixes(parent, seen)
    return found


def inherited_names(instances):
    """Names of the template children of each (frame, templates) pair."""
    names = set()
    for frame, templates in instances:
        for template in templates:
            names |= {frame + s for s in template_suffixes(template)}
    return names


def from_template(name, defined):
    """A template child of a defined frame, or of such a child (a scroll frame's
    ScrollBar, then the ScrollBar's ScrollUpButton)."""
    for s in TEMPLATE_SUFFIXES:
        if len(s) < len(name) and name.endswith(s):
            parent = name[:-len(s)]
            if parent in defined or from_template(parent, defined):
                return True
    return False


def xml_names(text, instances=None):
    """Frame names an XML file creates, with $parent expanded where it can be.
    Frames that inherit a template go into `instances` (inherited_names)."""
    names, stack, virtual = set(), [], set()
    for m in re.finditer(r"<(/?)(\w+)([^>]*?)(/?)>", text):
        closing, tag, attrs, selfclosing = m.groups()
        if closing:
            if stack:
                stack.pop()
            continue
        name = re.search(r'\bname="([^"]+)"', attrs)
        name = name.group(1) if name else None
        if name and re.match(r"^\$parent[A-Za-z]\w{2,}$", name):
            TEMPLATE_SUFFIXES.add(name[7:])
        # $parent is the frame named in parent="X" when there is one, as in the client.
        explicit = re.search(r'\bparent="([^"]+)"', attrs)
        explicit = explicit.group(1) if explicit else None
        if name and "$parent" in name:
            parent = explicit or next((p for p in reversed(stack) if p), None)
            if parent in virtual and name.startswith("$parent"):
                TEMPLATE_CHILDREN.setdefault(parent, set()).add(name[7:])
            name = name.replace("$parent", parent) if parent else None
        inherits = re.search(r'\binherits="([^"]+)"', attrs)
        inherits = [t.strip() for t in inherits.group(1).split(",")] if inherits else []
        if name and re.search(r'\bvirtual="true"', attrs):
            virtual.add(name)
            if inherits:
                TEMPLATE_PARENT[name] = inherits
        elif name and inherits and instances is not None:
            instances.append((name, inherits))
        if name:
            names.add(name)
        if not selfclosing:
            stack.append(name or explicit)
    return names


def call_args(code, start):
    """The top-level argument texts of a call whose '(' ends just before start."""
    args, depth, begin = [], 0, start
    for i in range(start, len(code)):
        c = code[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                args.append(code[begin:i].strip())
                return args
            depth -= 1
        elif c == "," and depth == 0:
            args.append(code[begin:i].strip())
            begin = i + 1
    return args


def helper_frame_names(codes):
    """Names that reach CreateFrame through the addon's own helpers, such as
    UI.Button("MyAddonClose", ...) or a panel maker that passes its first argument
    on as the frame's name. A helper is followed through further helpers."""
    funcs = []
    for code in codes:
        heads = list(re.finditer(r"^[ \t]*(?:local[ \t]+)?function[ \t]+([A-Za-z_][\w.]*)[ \t]*\(([^)]*)\)", code, re.M))
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(code)
            funcs.append((m.group(1), [p.strip() for p in m.group(2).split(",")], code[m.end():end]))

    def calls(code, fname):
        for m in re.finditer(r"(?<![\w.:])" + re.escape(fname) + r"[ \t]*\(", code):
            yield call_args(code, m.end())

    namers, changed = {"CreateFrame": 1}, True
    while changed:
        changed = False
        for name, params, body in funcs:
            if name in namers:
                continue
            for fname, index in list(namers.items()):
                hit = next((a[index] for a in calls(body, fname) if index < len(a) and a[index] in params), None)
                if hit:
                    namers[name], changed = params.index(hit), True
                    break
    # Children a helper names after its name argument: name .. "Close".
    suffixed = defaultdict(set)
    for name, params, body in funcs:
        for fname, index in namers.items():
            for a in calls(body, fname):
                m = index < len(a) and re.fullmatch(r"([A-Za-z_]\w*)\s*\.\.\s*[\"'](\w+)[\"']", a[index])
                if m and m.group(1) in params:
                    suffixed[name].add((params.index(m.group(1)), m.group(2)))
    names = set()
    for code in codes:
        for fname, index in namers.items():
            for a in calls(code, fname):
                m = index < len(a) and re.fullmatch(r"[\"']([A-Za-z_]\w*)[\"']", a[index])
                if m:
                    names.add(m.group(1))
                    names |= {m.group(1) + s for i, s in suffixed.get(fname, ()) if i == index}
    return names


# One addon ------------------------------------------------------------------

class Addon:
    def __init__(self, folder: Path):
        self.folder, self.name = folder, folder.name
        self.toc = next(iter(sorted(folder.glob("*.toc"))), None)
        self.meta, self.loaded = {}, []
        if self.toc:
            for line in self.toc.read_text("utf-8", "replace").splitlines():
                m = re.match(r"##\s*([\w-]+)\s*:\s*(.*)", line)
                if m:
                    self.meta[m.group(1).lower()] = m.group(2).strip()
                elif line.strip() and not line.startswith("#"):
                    self.loaded.append(line.strip().replace("\\", "/"))
        self.loaded = self._follow_xml(self.loaded)
        self.files = {}
        for rel in self.loaded:
            path = folder / rel
            if path.is_file():
                self.files[rel] = path.read_text("utf-8", "replace")
        self.defs = set()
        instances = []
        for rel, text in self.files.items():
            if rel.lower().endswith(".lua"):
                self.defs |= global_defs(strip_lua(text, True))
            elif rel.lower().endswith(".xml"):
                self.defs |= xml_names(text, instances)
                for script in re.findall(r"<(On\w+)>(.*?)</\1>", text, re.S):
                    self.defs |= global_defs(strip_lua(script[1], True))
        self.defs |= helper_frame_names([strip_lua(t, True) for r, t in self.files.items()
                                         if r.lower().endswith(".lua")])
        self.defs |= inherited_names(instances)
        self.saved = set(re.split(r"[,\s]+", self.meta.get("savedvariables", "")) +
                         re.split(r"[,\s]+", self.meta.get("savedvariablespercharacter", ""))) - {""}
        self.defs |= self.saved

    def _follow_xml(self, entries):
        result, queue = [], list(entries)
        while queue:
            rel = queue.pop(0)
            if rel in result:
                continue
            result.append(rel)
            path = self.folder / rel
            if rel.lower().endswith(".xml") and path.is_file():
                base = str(Path(rel).parent).replace("\\", "/")
                for m in re.finditer(r'<(?:Script|Include)\s+file="([^"]+)"',
                                     path.read_text("utf-8", "replace")):
                    child = m.group(1).replace("\\", "/")
                    queue.append(child if base in ("", ".") else base + "/" + child)
        return result

    def declared(self, other):
        deps = " ".join(self.meta.get(k, "") for k in ("dependencies", "requireddeps", "optionaldeps", "dep"))
        return other.lower() in [d.lower() for d in re.split(r"[,\s]+", deps) if d]

    def lua(self):
        return [(rel, text) for rel, text in self.files.items() if rel.lower().endswith(".lua")]


# What the game and the DLLs define ---------------------------------------------

ENGINE_CATALOGS = ("BlizzardScriptAPI.md", "TurtleScriptAPI.md")


def known_names():
    """(game, docs, wotlk, files): the game's own globals (engine catalog and
    FrameXML), every word in the DLL docs, and the WotLK catalog's names."""
    game, docs, sources = set(), set(), []
    for path in UPSTREAM.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".md", ".cpp", ".h", ".hpp", ".lua") and path != WOTLK_CATALOG:
            words = set(IDENT.findall(path.read_text("utf-8", "replace")))
            if path.name in ENGINE_CATALOGS:
                game |= words
            else:
                docs |= words
            sources.append(path)
    for path in FRAMEXML.rglob("*"):
        if path.suffix.lower() == ".lua":
            game |= global_defs(strip_lua(path.read_text("latin-1"), True))
        elif path.suffix.lower() == ".xml":
            text = path.read_text("latin-1")
            game |= xml_names(text)
            for script in re.findall(r"<(On\w+)>(.*?)</\1>", text, re.S):
                game |= global_defs(strip_lua(script[1], True))
    wotlk = set(IDENT.findall(WOTLK_CATALOG.read_text("utf-8", "replace"))) if WOTLK_CATALOG.is_file() else set()
    return game, docs, wotlk, len(sources)


def doc_text():
    return "\n".join(p.read_text("utf-8", "replace") for p in UPSTREAM.rglob("*.md") if p != WOTLK_CATALOG)


# Checks ----------------------------------------------------------------------

def ghosts(addon, everyone, game, docs, wotlk):
    """CamelCase globals used, in Lua and in XML scripts, that nothing defines: not this
    addon, another installed addon, the game's code or any DLL doc."""
    defined = game | docs
    for other in everyone:
        defined |= other.defs
    found = defaultdict(list)
    for rel, text in addon.lua():
        code = strip_lua(text)
        local = local_names(code)
        for name, line in global_uses(code):
            if (CAMEL.match(name) and name not in defined and name not in local
                    and not from_template(name, defined) and not numbered(name, defined)):
                found[name].append("%s:%d" % (rel, line))
    # The functions XML scripts call (OnClick, OnShow, ...) are read like Lua: a renamed or
    # removed function leaves a button that errors only when it is clicked.
    for rel, text in addon.files.items():
        if rel.lower().endswith(".xml"):
            for _, body in re.findall(r"<(On\w+)>(.*?)</\1>", text, re.S):
                code = strip_lua(body)
                local = local_names(code)
                for name, _line in global_uses(code):
                    if (CAMEL.match(name) and name not in defined and name not in local
                            and not from_template(name, defined) and not numbered(name, defined)):
                        found[name].append("%s (script)" % rel)
    return [{"name": n, "where": w[:3], "uses": len(w),
             "note": "exists only in the WotLK 3.3.5 client" if n in wotlk else ""}
            for n, w in sorted(found.items())]


def connections(addon, everyone, game):
    """Globals one installed addon defines and another reads, in both directions.
    Names the game itself defines are shared ground, not a connection."""
    def reads(a):
        used = defaultdict(list)
        for rel, text in a.lua():
            code = strip_lua(text)
            local = local_names(code)
            for name, line in global_uses(code):
                # Deliberate globals are capitalized; lowercase ones are leaks (see leaks()).
                if name not in local and re.search(r"[A-Z]", name) and name not in game:
                    used[name].append("%s:%d" % (rel, line))
        return used
    links = []
    mine = reads(addon)
    for other in everyone:
        if other is addon:
            continue
        for name in sorted(set(mine) & other.defs - addon.defs):
            links.append({"reader": addon.name, "owner": other.name, "name": name,
                          "where": mine[name][:2], "declared": addon.declared(other.name)})
        theirs = reads(other)
        for name in sorted(set(theirs) & addon.defs - other.defs):
            links.append({"reader": other.name, "owner": addon.name, "name": name,
                          "where": theirs[name][:2], "declared": other.declared(addon.name)})
    return links


def leaks(addon, game):
    """Lowercase globals the addon creates by assigning without 'local'. Any
    other addon can overwrite them, and they overwrite other addons' too."""
    found = defaultdict(list)
    for rel, text in addon.lua():
        code = strip_lua(text)
        for name in assigned_names(code):
            # "_acc = 0" leaks as surely as "acc = 0".
            plain = name.lstrip("_")
            if plain and plain[0].islower() and name not in addon.saved and name not in game:
                m = re.search(r"^[ \t]*(?:function\s+)?" + re.escape(name) + r"\b", code, re.M)
                found[name].append("%s:%d" % (rel, code.count("\n", 0, m.start()) + 1 if m else 0))
    return [{"name": n, "where": w[:2]} for n, w in sorted(found.items())]


def media_referenced(path, rel, code_text):
    """A media file is used when its name is in the code, or when its folder
    is and every part of its name is a quoted string there: a path built from
    parts, such as "Textures\\Nodes\\" .. kind .. "_" .. side."""
    if re.search(re.escape(path.stem), code_text, re.I):
        return True
    if "/" not in rel:
        return False
    folder = rel.rsplit("/", 1)[0]
    if not re.search(r"[\\/]+".join(re.escape(p) for p in folder.split("/")) + r"[\\/]", code_text, re.I):
        return False
    parts = [p for p in re.split(r"[_\-. ]", path.stem) if p]
    return all(re.search(r"[\"']" + re.escape(p) + r"[\"']", code_text, re.I) for p in parts)


def unused_files(addon):
    findings = []
    code_text = "\n".join(addon.files.values()) + "\n" + (addon.toc.read_text("utf-8", "replace") if addon.toc else "")
    loaded = {rel.lower() for rel in addon.loaded}
    for path in sorted(addon.folder.rglob("*")):
        rel = path.relative_to(addon.folder).as_posix()
        if not path.is_file() or rel.split("/")[0] in (".git", "docs", "tests") or rel.startswith("."):
            continue
        suffix = path.suffix.lower()
        if suffix in (".lua", ".xml") and rel.lower() not in loaded and path.name.lower() != "bindings.xml":
            findings.append({"file": rel, "why": "not loaded by the TOC"})
        elif suffix in MEDIA and not media_referenced(path, rel, code_text):
            findings.append({"file": rel, "why": "nothing refers to it"})
    for rel, text in addon.lua():
        head = strip_lua(text)
        if re.search(r"^\s*if\s+true\s+then\s+return\s+end", head, re.M):
            findings.append({"file": rel, "why": "returns before doing anything (if true then return end)"})
    return findings


def stale_notes(addon, docs):
    findings = []
    for rel, text in addon.files.items():
        for number, line in enumerate(text.splitlines(), 1):
            if "UNVERIFIED" not in line or not re.search(r"not in the|not documented|not in VanillaForge", line):
                continue
            # API-shaped names only: C_X.Y, CamelCase functions, EVENT_NAMES.
            names = [n for n in re.findall(r"[A-Za-z_][\w.]*\w", line)
                     if n not in ("UNVERIFIED", "VanillaForge") and len(n) >= 6
                     and (n.startswith("C_") or re.match(r"^[A-Z][a-z]+[A-Z]\w*$", n)
                          or re.match(r"^[A-Z]+(?:_[A-Z]+)+$", n))]
            covered = [n for n in names if n in docs]
            if covered:
                findings.append({"where": "%s:%d" % (rel, number), "covered": covered})
    return findings


# A guard that reads a DLL's version number instead of checking that it is loaded.
DLL_VERSION_GUARD = re.compile(
    r"CLASSIC_API_VERSION\s*(?:<|>=?)\s*(\w+)|(?:MIN_CLASSIC_API|local\s+minimum)\s*=\s*(\d{5})\b"
    r"|(tostring\s*\(\s*SUPERWOW_VERSION\b|=\s*GetNampowerVersion\s*\(\s*\))")


def version_drift(addon):
    # Only UPSTREAM_VERSIONS.json names a DLL version; guards check that each is loaded.
    findings = []
    for key, value in addon.meta.items():
        if re.fullmatch(r"x-[\w-]+-min-version", key):
            findings.append({"where": "%s (%s)" % (addon.toc.name, key), "found": value})
    for rel, text in addon.lua():
        for m in DLL_VERSION_GUARD.finditer(text):
            findings.append({"where": "%s:%d" % (rel, text.count("\n", 0, m.start()) + 1),
                             "found": m.group(1) or m.group(2) or m.group(3)})
    return findings


def saved_settings(addon, wtf):
    """Switches off for every character, and saved keys no code reads."""
    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        return {"error": "lupa is not installed"}
    if not addon.saved or not wtf.is_dir():
        return {}
    code = "\n".join(text for _, text in addon.files.items())
    values = defaultdict(list)  # (table, key) -> values per character
    characters = 0
    for path in wtf.glob("Account/*/**/SavedVariables/%s.lua" % addon.name):
        lua = LuaRuntime(unpack_returned_tuples=True)
        try:
            lua.execute(path.read_text("utf-8", "replace"))
        except Exception:
            continue
        characters += 1
        for table in addon.saved:
            data = lua.globals()[table]
            if lua.eval("type")(data) != "table":
                continue
            for key, value in data.items():
                if isinstance(key, str):
                    values[(table, key)].append(value)
                    if lua.eval("type")(value) == "table":
                        for sub, subvalue in value.items():
                            if isinstance(sub, str) and lua.eval("type")(subvalue) != "table":
                                values[(table + "." + key, sub)].append(subvalue)
    def named(key):
        return re.search(r"(?<![\w])" + re.escape(key) + r"(?![\w])", code)

    def data_key(key):
        return "'" in key or "|" in key or re.search(r" of \S", key)
    missing, total = defaultdict(int), defaultdict(int)
    for table, key in values:
        if data_key(key):
            continue
        total[table] += 1
        if not named(key):
            missing[table] += 1
    # Only a nested table can be data: the saved table itself holds the settings.
    data_tables = {t for t in total if "." in t and missing[t] >= 3 and missing[t] * 2 >= total[t]}
    off, stale = [], []
    for (table, key), seen in sorted(values.items()):
        if data_key(key) or data_key(table) or table in data_tables:
            continue
        if not named(key):
            stale.append({"table": table, "key": key, "characters": len(seen)})
        elif characters > 1 and len(seen) == characters and all(v in (0, False) for v in seen):
            off.append({"table": table, "key": key, "characters": len(seen)})
    return {"characters": characters, "off_everywhere": off, "not_in_code": stale}


MOCK_DEF = re.compile(r"^[ \t]*(?:function[ \t]+(C_\w+\.\w+|[A-Za-z_]\w*)[ \t]*\(|([A-Za-z_]\w*)[ \t]*=[ \t]*function\b)", re.M)


def stale_mocks(addon, everyone, game, docs, regressions=REGRESSIONS):
    """Global functions the addon's regression suite mocks that nothing has.

    A mock for a name the game, the DLL docs and every installed addon lack,
    and that the suite itself never calls, stands in for code that is gone
    (a deleted function, a renamed API): the test then proves less than it says.
    """
    suite = regressions / addon.name.lstrip("!")
    if not suite.is_dir():
        return []
    texts = {p.name: p.read_text("utf-8", "replace") for p in sorted(suite.glob("*.py"))}
    shared = "\n".join(p.read_text("utf-8", "replace") for p in sorted(regressions.glob("*.py")))
    known = game | docs
    for other in everyone:
        for text in other.files.values():
            known |= set(IDENT.findall(text))
    found = {}
    for name, text in texts.items():
        for m in MOCK_DEF.finditer(text):
            full = m.group(1) or m.group(2)
            key = full.split(".")[-1] if full.startswith("C_") else full
            if key in known or not CAMEL.match(key):
                continue
            entry = found.setdefault(full, {"name": full, "where": [], "defs": 0})
            entry["where"].append("%s:%d" % (name, text.count("\n", 0, m.start()) + 1))
            entry["defs"] += 1
    everything = "\n".join(texts.values()) + "\n" + shared
    stale = []
    for full, entry in sorted(found.items()):
        uses = len(re.findall(r"(?<![\w.:])" + re.escape(full) + r"\b", everything))
        if uses <= entry["defs"]:
            stale.append({"name": full, "where": entry["where"]})
    return stale


def replacements(addon):
    entries = json.loads((ROOT / "tools" / "replacements.json").read_text("utf-8"))["entries"]
    findings = []
    for entry in entries:
        pattern = re.compile(entry["pattern"])
        # "unless": a file that already does it the better way is not a lead.
        unless = re.compile(entry["unless"]) if entry.get("unless") else None
        hits = []
        for rel, text in addon.lua():
            code = strip_lua(text, keep_strings=True)
            if unless and unless.search(code):
                continue
            hits += ["%s:%d" % (rel, code.count("\n", 0, m.start()) + 1) for m in pattern.finditer(code)]
        if hits:
            findings.append({"id": entry["id"], "where": hits[:3], "hits": len(hits),
                             "finding": entry["finding"], "better": entry["better"], "source": entry["source"]})
    return findings


TICKER = re.compile(r"C_Timer\.NewTicker\s*\(")
ON_UPDATE = re.compile(r"""(?:SetScript|HookScript)\s*\(\s*["']OnUpdate["']\s*,(?!\s*nil\b)""")
ON_UPDATE_OFF = re.compile(r"""SetScript\s*\(\s*["']OnUpdate["']\s*,\s*nil\b""")


def repeating_work(addon):
    """Every repeating timer and OnUpdate handler: each must say what it waits for.

    `stops` tells whether the same file ever cancels a ticker or clears an
    OnUpdate. One that never stops runs while nothing changes; one that does may
    still run longer than it needs to. Both are questions (section 4), not verdicts.
    """
    findings = []
    for rel, text in addon.files.items():
        if rel.lower().endswith(".lua"):
            code = strip_lua(text, keep_strings=True)
            kinds = (("ticker", TICKER, re.compile(r":Cancel\s*\(")), ("OnUpdate", ON_UPDATE, ON_UPDATE_OFF))
        elif rel.lower().endswith(".xml"):
            code = text
            kinds = (("XML OnUpdate", re.compile(r"<OnUpdate\b"), ON_UPDATE_OFF),)
        else:
            continue
        for kind, start, stop in kinds:
            stops = bool(stop.search(code))
            for m in start.finditer(code):
                findings.append({"kind": kind, "where": "%s:%d" % (rel, code.count("\n", 0, m.start()) + 1),
                                 "stops": stops})
    return findings


def stock_frame_work(framexml=FRAMEXML):
    """The game's own per-frame work: {function: {"xml", "lua", "family"}} for each
    function an <OnUpdate> or <OnUpdateModel> of FrameXML calls. Its family is
    what shares its prefix (ActionButton_OnUpdate: ActionButton_Update,
    ActionButton1): the functions of its Lua file and the frames of its XML."""
    defined, functions = {}, {}
    for path in framexml.rglob("*.lua"):
        names = set(re.findall(r"^function\s+([A-Za-z_]\w*)\s*\(", path.read_text("latin-1"), re.M))
        functions[path] = names
        for name in names:
            defined[name] = path
    work = {}
    for path in framexml.rglob("*.xml"):
        text = path.read_text("latin-1")
        bodies = re.findall(r"<(OnUpdate|OnUpdateModel)>(.*?)</\1>", text, re.S)
        if not bodies:
            continue
        frames = set(re.findall(r'\bname="([A-Za-z_]\w*)"', text))
        for _, body in bodies:
            for name in set(re.findall(r"\b([A-Z][A-Za-z0-9]*_\w+)\s*\(", body)):
                lua = defined.get(name)
                if not lua:
                    continue
                prefix = name.split("_")[0]
                entry = work.setdefault(name, {"xml": set(), "lua": lua.name, "family": set()})
                entry["xml"].add(path.name)
                entry["family"] |= {n for n in functions[lua] | frames
                                    if n != name and n.startswith(prefix)}
    return work


def stock_per_frame(addon, work=None):
    """The game's per-frame work on frames this addon takes over: a stock OnUpdate
    runs every frame on a shown frame whether or not anything changed. Each hit
    is a question (section 4, question 6): can an event, a native widget or a
    script set only while needed do it? `names` says the addon names the
    per-frame function itself (it may already handle it)."""
    work = stock_frame_work() if work is None else work
    code = {rel: strip_lua(text, keep_strings=True) if rel.lower().endswith(".lua") else text
            for rel, text in addon.files.items() if rel.lower().endswith((".lua", ".xml"))}
    findings = []
    for name, entry in sorted(work.items()):
        touched, names = [], False
        for rel, text in code.items():
            if re.search(r"\b%s\b" % re.escape(name), text):
                names = True
            for m in IDENT.finditer(text):
                if m.group(0) in entry["family"] and len(touched) < 3 \
                        and all(t[0] != m.group(0) for t in touched):
                    touched.append((m.group(0), "%s:%d" % (rel, text.count("\n", 0, m.start()) + 1)))
        if touched:
            findings.append({"function": name, "xml": sorted(entry["xml"]), "lua": entry["lua"],
                             "touched": touched, "names": names})
    return findings


def piecemeal_cleanup(addon):
    """Saved keys cleared one line each (`Saved["Old"] = nil`): a retired switch
    that needs its own line is forgotten once the line goes. One sweep at load
    that clears every key nothing owns does it for all (KNOWN_PATTERNS KP-64)."""
    findings = []
    for rel, text in addon.lua():
        code = strip_lua(text, keep_strings=True)
        for table in addon.saved:
            pattern = r"\b%s\s*(?:\[\s*[\"']([^\"']+)[\"']\s*\]|\.(\w+))\s*=\s*nil\b" % re.escape(table)
            for m in re.finditer(pattern, code):
                findings.append({"key": m.group(1) or m.group(2), "table": table,
                                 "where": "%s:%d" % (rel, code.count("\n", 0, m.start()) + 1)})
    return findings if len(findings) >= 2 else []


# Report ----------------------------------------------------------------------

def unreferenced_functions(addon, everyone=()):
    """Global functions the addon defines and nothing in its Lua, XML or TOC, or in
    another installed addon, mentions again."""
    stripped = {rel: strip_lua(text, keep_strings=True) for rel, text in addon.lua()}
    # The client loads Bindings.xml itself (no TOC line); its bodies call our globals.
    bindings = addon.folder / "Bindings.xml"
    extra = [bindings.read_text("utf-8", "replace")] if bindings.is_file() else []
    everything = "\n".join(list(stripped.values()) + extra +
                           [t for r, t in addon.files.items() if not r.lower().endswith(".lua")])
    others = [o for o in everyone if o.folder != addon.folder]

    def others_use(name):
        pattern = re.compile(r"\b%s\b" % re.escape(name))
        return any(pattern.search(text) for o in others for _, text in o.files.items())
    findings = []
    for rel, code in stripped.items():
        for m in re.finditer(r"^function\s+([A-Za-z_]\w*)\s*\(", code, re.M):
            name = m.group(1)
            if name in HANDLER_GLOBALS or name.startswith(("SLASH_", "BINDING_")):
                continue
            if len(re.findall(r"\b%s\b" % re.escape(name), everything)) <= 1 and not others_use(name):
                findings.append({"name": name, "where": "%s:%d" % (rel, code.count(chr(10), 0, m.start()) + 1)})
    return findings


def duplicate_functions(addon, min_lines=6):
    """Function bodies that repeat exactly (names and whitespace ignored). Same-indent end closes a body."""
    seen, findings = {}, []
    for rel, text in addon.lua():
        lines = strip_lua(text).split("\n")
        for i, line in enumerate(lines):
            m = re.match(r"^(\s*)(?:local\s+)?function\b[^\n]*\)\s*$", line)
            if not m:
                continue
            for j in range(i + 1, len(lines)):
                if re.match(r"^%send\b" % m.group(1), lines[j]) and not lines[j].startswith(m.group(1) + " "):
                    body = [x.strip() for x in lines[i + 1:j] if x.strip()]
                    if len(body) >= min_lines:
                        seen.setdefault("\n".join(body), []).append("%s:%d" % (rel, i + 1))
                    break
    for where in seen.values():
        if len(where) > 1:
            findings.append({"where": where})
    return findings


def report(results, out):
    def section(title, items, line):
        out.append("\n## %s (%d)" % (title, len(items)))
        for item in items:
            out.append("- " + line(item))
    section("Unused", results["unused_files"], lambda f: "%s: %s" % (f["file"], f["why"]))
    s = results["saved_settings"]
    if s.get("error"):
        out.append("\n## Settings\n- skipped: " + s["error"])
    elif s:
        section("Off for every character (%d characters)" % s["characters"], s["off_everywhere"],
                lambda f: "%s[%r]" % (f["table"], f["key"]))
        section("Saved but no code reads it", s["not_in_code"], lambda f: "%s[%r] on %d character(s)"
                % (f["table"], f["key"], f["characters"]))
    section("Global functions nothing refers to", results["unreferenced_functions"],
            lambda f: "%s at %s" % (f["name"], f["where"]))
    section("Function bodies that repeat", results["duplicate_functions"], lambda f: ", ".join(f["where"]))
    section("Repeating work (what does each wait for? cheap is no reason to run)", results["repeating_work"],
            lambda f: "%s at %s%s" % (f["kind"], f["where"], "" if f["stops"] else "  [never stopped in this file]"))
    section("The game's per-frame work it takes over (FrameXML OnUpdate; does it need to run?)",
            results["stock_per_frame"], lambda f: "%s (%s, %s): touches %s%s" % (
                f["function"], ", ".join(f["xml"]), f["lua"],
                ", ".join("%s at %s" % t for t in f["touched"]),
                "  [the addon names it: check it is handled]" if f["names"] else ""))
    section("Saved keys cleared one line each (one sweep clears them all)", results["piecemeal_cleanup"],
            lambda f: "%s[%r] at %s" % (f["table"], f["key"], f["where"]))
    section("A DLL does it now", results["replacements"], lambda f: "%s (%d at %s)\n  %s\n  Better: %s\n  Source: %s"
            % (f["id"], f["hits"], ", ".join(f["where"]), f["finding"], f["better"], f["source"]))
    section("Connections between addons", results["connections"], lambda f: "%s reads %s's %s at %s%s"
            % (f["reader"], f["owner"], f["name"], ", ".join(f["where"]), "" if f["declared"] else "  [not declared in the TOC]"))
    section("Leaked globals (assigned without local)", results["leaks"],
            lambda f: "%s at %s" % (f["name"], ", ".join(f["where"])))
    section("Ghost names (defined nowhere)", results["ghosts"], lambda f: "%s, %d use(s) at %s%s"
            % (f["name"], f["uses"], ", ".join(f["where"]), ("  [" + f["note"] + "]") if f["note"] else ""))
    section("Stale notes (the docs cover them)", results["stale_notes"],
            lambda f: "%s: %s" % (f["where"], ", ".join(f["covered"])))
    section("Names a DLL version (only UPSTREAM_VERSIONS.json may)", results["version_drift"], lambda f: "%s: %s" % (f["where"], f["found"]))
    section("Mocks for names nothing has (its regression suite)", results["stale_mocks"],
            lambda f: "%s at %s" % (f["name"], ", ".join(f["where"])))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addon", type=Path)
    parser.add_argument("--addons", type=Path, help="Installed AddOns folder; default the addon's parent")
    parser.add_argument("--wtf", type=Path, help="Client WTF folder; default <client>/WTF beside Interface")
    parser.add_argument("--json", type=Path, help="Also write the findings as JSON")
    parser.add_argument("--override", type=Path, action="append", default=[],
                        help="Another copy of an installed addon to read in its place (e.g. an older checkout)")
    args = parser.parse_args(argv)
    folder = args.addon.resolve()
    addons_dir = (args.addons or folder.parent).resolve()
    wtf = (args.wtf or addons_dir.parent.parent / "WTF").resolve()
    missing = [p for p in (UPSTREAM, FRAMEXML) if not p.is_dir()]
    if missing:
        print("Missing %s. Run tools/fetch_upstream_docs.py and tools/extract_framexml.py --all first."
              % ", ".join(str(p) for p in missing), file=sys.stderr)
        return 2
    game, docs, wotlk, doc_count = known_names()
    everyone = [Addon(d) for d in sorted(addons_dir.iterdir())
                if d.is_dir() and not d.name.startswith("Blizzard_") and any(d.glob("*.toc"))]
    # The addon under audit and any overrides replace installed addons of the same name.
    addon = None
    for path in [folder] + [p.resolve() for p in args.override]:
        copy = next((a for a in everyone if a.folder.resolve() == path), None) or Addon(path)
        everyone = [a for a in everyone if a.name.lower() != copy.name.lower()] + [copy]
        addon = addon or copy
    results = {
        "addon": addon.name,
        "unused_files": unused_files(addon),
        "saved_settings": saved_settings(addon, wtf),
        "unreferenced_functions": unreferenced_functions(addon, everyone),
        "duplicate_functions": duplicate_functions(addon),
        "repeating_work": repeating_work(addon),
        "stock_per_frame": stock_per_frame(addon),
        "piecemeal_cleanup": piecemeal_cleanup(addon),
        "replacements": replacements(addon),
        "connections": connections(addon, everyone, game),
        "leaks": leaks(addon, game),
        "ghosts": ghosts(addon, everyone, game, docs, wotlk),
        "stale_notes": stale_notes(addon, doc_text()),
        "version_drift": version_drift(addon),
        "stale_mocks": stale_mocks(addon, everyone, game, docs),
    }
    out = ["# Holes in %s" % addon.name,
           "Read against %d installed addons, the game's code and %d DLL doc files. Leads, not verdicts."
           % (len(everyone), doc_count)]
    report(results, out)
    print("\n".join(out))
    if args.json:
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
