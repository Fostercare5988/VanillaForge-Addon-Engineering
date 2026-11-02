"""Byte-safe edits of addon files, for audits and fixes.

Why it exists: addon files mix line endings (most are CRLF, some LF), the editors
and shells that are handy for patching either rewrite the endings or collapse the
doubled backslash of a Lua path (a path written with one backslash per separator
is read by Lua 5.0 with the separators dropped, so the texture or font is never
found; KNOWN_PATTERNS KP-60). These helpers
read a file, work on LF text, and write it back with the file's own endings and in
place (never replacing the file, so its permissions stay).

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


def read(path):
    """(text with LF endings, True when the file uses CRLF)."""
    raw = open(path, "rb").read().decode("utf-8")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write(path, text, crlf):
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(path, "r+b") as handle:   # in place: the file keeps its permissions
        handle.seek(0)
        handle.write(text.encode("utf-8"))
        handle.truncate()


def _fix(text):
    return text.replace("@@", BACKSLASH * 2)


def sub(path, old, new, count=1):
    """Replace `old` (exactly `count` times) with `new`."""
    text, crlf = read(path)
    old, new = _fix(old), _fix(new)
    found = text.count(old)
    assert found == count, "%s: expected %d, found %d for %r" % (path, count, found, old[:70])
    write(path, text.replace(old, new), crlf)


def cut(path, start, end, new=""):
    """Replace from the first `start` to the first `end` after it, both included."""
    text, crlf = read(path)
    start, end, new = _fix(start), _fix(end), _fix(new)
    a = text.index(start)
    b = text.index(end, a) + len(end)
    write(path, text[:a] + new + text[b:], crlf)


def regex(path, pattern, new, count=1, flags=re.S):
    """Regular-expression replace, asserting the number of matches."""
    text, crlf = read(path)
    result, n = re.subn(pattern, _fix(new), text, flags=flags)
    assert n == count, "%s: expected %d, matched %d for %r" % (path, count, n, pattern[:70])
    write(path, result, crlf)
