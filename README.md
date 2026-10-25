# VanillaForge

A small framework for building and modernizing lean, modern World of Warcraft
1.12.1 addons on the enhanced client: ClassicAPI, SuperWoW, NamPower and
UnitXP SP3. It works for any server; each server's game data comes from its own
[profile](servers/).

We audit, clean, refactor and improve: every line earns its place, the DLLs come
first, and connections between addons are visible and deliberate. VanillaForge
does not only guard against mistakes; it hunts for what can be done better.

**Start with [VANILLAFORGE.md](VANILLAFORGE.md).** It is the whole contract.

## What is here

| Part | Purpose |
| --- | --- |
| [VANILLAFORGE.md](VANILLAFORGE.md) | The contract: target, rules, how addons are written, how work is checked |
| [servers/](servers/) | One profile per server: identity, trusted data sources, known differences |
| [CLASSICAPI_MASTER_REFERENCE.md](CLASSICAPI_MASTER_REFERENCE.md) | ClassicAPI functions, events and Lua backports |
| [ENGINE_REFERENCE.md](ENGINE_REFERENCE.md) | SuperWoW, NamPower, UnitXP and native UI behaviour |
| [KNOWN_PATTERNS.md](KNOWN_PATTERNS.md) | Recurring hazards and their fixes |
| [regressions/](regressions/README.md) | Behaviour tests for the maintained addons |
| `templates/ForgeUI/` | The shared settings look |
| `tools/` | Hole finder, linter, audit and test runner, FrameXML extractor, upstream doc fetcher and checker |
| `tools/replacements.json` | Old ways a DLL now does better; grows with every audit |
| [archive/](archive/README.md) | Earlier workflows and audits, for history |

## Commands

Run from this folder. Python 3; regression tests also need `lupa`.

```text
python -B tools/find_holes.py "<addon folder>"
python -B tools/audit_addon.py "<addon folder>" --run-tests --test-start regressions/<Addon> --output "<report.json>"
python -B tools/vanillaforge_linter.py "<addon folder>"
python -B tools/extract_framexml.py --client "<client folder>" --all
python -B tools/fetch_upstream_docs.py
python -B tools/check_upstream.py
python -B -m unittest discover -s tests -p "test_*.py"
```

Maintained by [Fostercare5988](https://github.com/Fostercare5988).
