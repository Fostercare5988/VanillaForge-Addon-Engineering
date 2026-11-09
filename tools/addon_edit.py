"""Byte-safe edits of addon files, for audits and fixes.

Why it exists: addon files mix line endings (most are CRLF, some LF, a few both),
the editors and shells that are handy for patching either rewrite the endings or
collapse the doubled backslash of a Lua path (a path written with one backslash
per separator is read by Lua 5.0 with the separators dropped, so the texture or
font is never found; KNOWN_PATTERNS KP-60). These helpers read a file, work on
LF text, and write it back with the file's own endings and in place (never
replacing the file, so its permissions stay). A file with both endings is edited
as it is: the old text is matched with LF or with CRLF endings, and the new text
takes the endings of the text it replaces, so no other line changes.

Use it from a small script, one file per call, and write replacement text that
contains backslashes with the placeholder @@, which becomes two backslashes:

    import sys; sys.path.insert(0, "tools")
    from addon_edit import sub, cut, regex
    sub(path, 'SetFont("Fonts@@FRIZQT__.TTF", 9)', ...)

Every helper asserts how many places it changed, so a patch that no longer
matches fails instead of passing silently.
"""
import re

BACKSLASH = chr(92)
MIXED = "mixed"


def read(path):
    """(text, endings): LF text and True/False for CRLF/LF, or the raw text and
    MIXED for a file with both endings."""
    with open(path, "rb") as handle:
        raw = handle.read().decode("utf-8")
    crlf = raw.count("\r\n")
    if crlf and crlf != raw.count("\n"):
        return raw, MIXED
    return raw.replace("\r\n", "\n"), crlf > 0


def write(path, text, endings):
    if endings is True:
        text = text.replace("\n", "\r\n")
    with open(path, "r+b") as handle:   # in place: the file keeps its permissions
        handle.seek(0)
        handle.write(text.encode("utf-8"))
        handle.truncate()


def _fix(text):
    return text.replace("@@", BACKSLASH * 2)


def _crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def _variant(text, old, count, path):
    """In a mixed file: the form of `old` (LF or CRLF endings) found `count` times."""
    forms = [form for form in {old, _crlf(old)} if text.count(form) == count]
    assert len(forms) == 1, "%s: expected %d of %r with one kind of line ending" % (path, count, old[:70])
    return forms[0]


def _crlf_at(text, a, old):
    """Whether the text replaced at `a` ends its lines with CRLF: its own line
    breaks say so, or else the end of the line it sits on."""
    if "\n" in old:
        return "\r\n" in old
    end = text.find("\n", a + len(old))
    return end > 0 and text[end - 1] == "\r"


def sub(path, old, new, count=1):
    """Replace `old` (exactly `count` times) with `new`."""
    text, endings = read(path)
    old, new = _fix(old), _fix(new)
    if endings == MIXED:
        old = _variant(text, old, count, path)
        if _crlf_at(text, text.index(old), old):
            new = _crlf(new)
        write(path, text.replace(old, new), endings)
        return
    found = text.count(old)
    assert found == count, "%s: expected %d, found %d for %r" % (path, count, found, old[:70])
    write(path, text.replace(old, new), endings)


def cut(path, start, end, new=""):
    """Replace from the first `start` to the first `end` after it, both included."""
    text, endings = read(path)
    start, end, new = _fix(start), _fix(end), _fix(new)
    if endings == MIXED:
        start = _variant(text, start, text.count(start) or text.count(_crlf(start)), path)
        a = text.index(start)
        end = end if end in text[a:] else _crlf(end)
        b = text.index(end, a) + len(end)
        if _crlf_at(text, a, text[a:b]):
            new = _crlf(new)
        write(path, text[:a] + new + text[b:], endings)
        return
    a = text.index(start)
    b = text.index(end, a) + len(end)
    write(path, text[:a] + new + text[b:], endings)


def regex(path, pattern, new, count=1, flags=re.S):
    """Regular-expression replace, asserting the number of matches. In a mixed
    file the pattern sees the raw endings: write \\r?\\n for a line break."""
    text, endings = read(path)
    result, n = re.subn(pattern, _fix(new), text, flags=flags)
    assert n == count, "%s: expected %d, matched %d for %r" % (path, count, n, pattern[:70])
    write(path, result, endings)
