# VanillaForge

## Enhanced WoW 1.12.1 Addon Engineering Framework

[![WoW](https://img.shields.io/badge/WoW-1.12.1%20Build%205875-blue.svg)](https://github.com/Fostercare5988/VanillaForge-Addon-Engineering)
[![ClassicAPI](https://img.shields.io/badge/ClassicAPI-v1.15.12%2B-brightgreen.svg)](https://github.com/brues-code/ClassicAPI)
[![SuperWoW](https://img.shields.io/badge/SuperWoW-v2.2%2B-green.svg)](https://github.com/balakethelock/SuperWoW)
[![Framework](https://img.shields.io/badge/VanillaForge-v3.1-informational.svg)](VANILLAFORGE_SYSTEM_PROMPT.md)

A local knowledge base, system prompt, and static-analysis toolkit for building and
modernizing addons specifically for an **enhanced World of Warcraft 1.12.1 client**.

The framework is designed for AI coding assistants and human developers working with a
known modern client-extension stack. It deliberately avoids preserving compatibility
with an unmodified 2006 client when a verified enhanced primitive provides a better
solution.

---

## Target Environment

The client/API target is always:

```text
World of Warcraft 1.12.1
Build 5875
Interface 11200
```

VanillaForge is server-agnostic. A deployment-specific server/content revision may
change content, but it does not turn the underlying client into a later Blizzard API
generation. Server names and content revisions belong to deployment/project context,
not to the framework identity.

### Canonical enhanced stack

| Component | Baseline | Role |
| --- | --- | --- |
| [ClassicAPI](https://github.com/brues-code/ClassicAPI) | **v1.15.12+** | Modern/backported WoW API, Lua compatibility, events, unit tokens, secure-style helpers, timers and modern client behavior |
| [SuperWoW](https://github.com/balakethelock/SuperWoW) | **v2.2+** | GUID-aware identity/targeting, structured events and additional client/UI extensions |
| [NamPower](https://github.com/Emyrk/nampower) | **v4.6.2+** | Spell queue/quickcast behavior plus native spell, unit, DBC and event APIs |
| [UnitXP SP3](https://github.com/brues-code/UnitXP_SP3) | **v90+** | Raw telemetry, distance/LOS and selected client/window utilities |
| [DXVK](https://github.com/doitsujin/dxvk) | Runtime | Direct3D 9 to Vulkan translation; **not a Lua addon API** |
| [VanillaFixes](https://github.com/hannesmann/vanillafixes) | Runtime/loader | Client fixes and common DLL-loading infrastructure |

The whole stack may be assumed present in the target environment, but an individual
addon should only consume or declare a component when it actually uses that component's
capabilities.

This is the framework's current environment baseline. An addon's minimum ClassicAPI
version follows the capabilities and fixes it consumes; this refresh does not require
every existing addon to set `MIN_CLASSIC_API=11512`. See the
[v1.15.10 through v1.15.12 audit](docs/CLASSICAPI_1.15.12_AUDIT.md) for provenance,
semantic changes, and runtime checks.

---

## Repository Layout

```text
.
├── VANILLAFORGE_SYSTEM_PROMPT.md
├── CLASSICAPI_MASTER_REFERENCE.md
├── ENGINE_REFERENCE.md
├── KNOWN_PATTERNS.md
├── README.md
└── tools/
    └── vanillaforge_linter.py
```

### `VANILLAFORGE_SYSTEM_PROMPT.md`

The compact active engineering contract.

It defines:

- target environment
- capability-first development
- no stock-client compatibility fallbacks
- scope and completion discipline
- performance principles
- verification requirements
- Git/public-addon discipline
- when to consult the reference knowledge

This is the file to give an AI as the primary system/instruction prompt.

### `CLASSICAPI_MASTER_REFERENCE.md`

The local ClassicAPI knowledge base.

It exists so an AI does **not** need to browse the ClassicAPI repository for ordinary
API discovery.

It covers, among other things:

- Lua 5.1 compatibility and source rewriting
- modern positional frame-script arguments
- modern addon loading
- the bundled `!!!ClassicAPI` addon
- `/classicapi`
- focus, nameplate and raid-marker unit tokens
- macro conditions and secure-style helpers
- `C_Timer`
- `C_UnitAuras` / `AuraUtil`
- `C_Spell` / `C_SpellBook`
- `C_Item`
- `C_Container`
- `C_NamePlate`
- `C_Map`
- `C_Texture`
- `C_LossOfControl`
- events, globals and enums
- GlueXML APIs
- modernization guidance

For ClassicAPI questions, this file is the framework's primary local reference.

### `ENGINE_REFERENCE.md`

Documents everything that should **not** be duplicated in the ClassicAPI master:

- WoW 1.12.1 client/runtime boundaries
- SuperWoW
- NamPower
- UnitXP SP3
- DXVK
- VanillaFixes / loader boundary
- cross-stack API selection
- FrameXML/UI engineering notes
- runtime diagnostics
- dependency documentation rules

### `KNOWN_PATTERNS.md`

Reusable engineering pitfalls and verified patterns extracted from real addon work.

Examples include:

- tooltip scraping
- repeated aura scans
- faux focus
- fuzzy targeting
- event/callback mistakes
- cooldown edge cases
- nameplate lifecycle problems
- PvP-specific state handling

Patterns are reference material, not mandatory ceremony.

### `tools/vanillaforge_linter.py`

A lightweight heuristic scanner for machine-detectable hazards.

The linter is a **floor, not a ceiling**. A clean scan is useful evidence, not proof
that an addon is correct at runtime.

---

## Core Engineering Model

### Enhanced-client only

Do not write fallback branches merely so an addon still works on an unmodified stock
1.12.1 client.

If the target stack supplies a better authoritative primitive, use it.

That does **not** mean every original 1.12.1 API is obsolete. Fundamental client APIs
remain valid when they are still the correct primitive.

The distinction is:

```text
valid native primitive       -> keep/use it
obsolete compatibility hack  -> remove it when enhanced stack replaces it
```

### Capability-first

Use a stack component when it materially improves:

- correctness
- performance
- safety
- identity/state authority
- architectural simplicity

Do not create artificial dependencies merely to demonstrate stack usage.

### Event-driven before polling

Prefer authoritative events and direct state APIs over periodic polling.

`OnUpdate` remains appropriate for work that genuinely belongs to the render frame,
such as:

- animation
- interpolation
- dragging
- continuously rendered visual transitions

### Structured data before scraping

Prefer structured APIs/events over:

- hidden tooltip scanning
- localized combat-log regexes
- fuzzy name matching
- WorldFrame child scraping
- duplicated spell/item metadata tables

---

## ClassicAPI Changes Old 1.12 Assumptions

ClassicAPI currently backports a large modern API surface and much of Lua 5.1 behavior.
Its official project documentation describes **550+ Lua functions and 50+ events**.

One especially important rule for old addon ports:

> ClassicAPI supports modern positional frame-script arguments and enables them by
> default for handlers that declare parameters, while legacy globals remain available.

Therefore, a modern handler such as:

```lua
frame:SetScript("OnEvent", function(self, event, ...)
    -- ...
end)
```

is not automatically invalid merely because the base executable is 1.12.1.

The real invocation path still matters for XML handlers, direct calls, custom
dispatchers, and legacy code. Consult `CLASSICAPI_MASTER_REFERENCE.md` instead of
applying old blanket rules.

---

## Cross-Stack Examples

### Cast tracking

Depending on the task, authoritative sources may include:

```text
ClassicAPI UNIT_SPELLCAST_*
ClassicAPI C_Spell.UnitCastingInfo / UnitChannelInfo
SuperWoW UNIT_CASTEVENT
NamPower documented cast/event APIs
```

Do not subscribe to all of them by default. Choose the source whose semantics match the
required identity and timing.

### Unit identity

Prefer authoritative unit tokens and GUIDs over names.

Useful enhanced primitives include:

```text
ClassicAPI focus / nameplateN / markN
ClassicAPI UnitTokenFromGUID
SuperWoW GUID-aware unit paths
SuperWoW structured GUID events
```

### Auras

Prefer:

```text
C_UnitAuras
AuraUtil
```

over hidden tooltip scanning.

### Timers

Prefer:

```text
C_Timer.After
C_Timer.NewTimer
C_Timer.NewTicker
```

for asynchronous/periodic work when no authoritative event exists.

Do not replace legitimate per-frame animation with a timer simply to eliminate
`OnUpdate`.

---

## Using the Framework with an AI

Recommended context order:

1. provide `VANILLAFORGE_SYSTEM_PROMPT.md`
2. provide the addon/repository being worked on
3. let the AI consult only the relevant reference files
4. use `CLASSICAPI_MASTER_REFERENCE.md` for ClassicAPI questions
5. use `ENGINE_REFERENCE.md` for SuperWoW/NamPower/UnitXP/runtime questions
6. use `KNOWN_PATTERNS.md` when the subsystem matches a known edge case

Do **not** dump every reference file into every tiny prompt unless the model/tool cannot
read files on demand. The whole point of splitting the old monolith was to stop paying
the context cost of nameplate, cooldown, bag, PvP and engine trivia simultaneously.

### Agentic environments

When the AI has filesystem/terminal access, it should inspect the actual addon,
implement the scoped task, and run relevant static checks.

### Chat-only environments

Provide the relevant addon files and reference material. The AI must not pretend it ran
commands, edited the local repository, tested in-game, or pushed commits when it could
not actually do so.

---

## Static Validation

Run:

```bash
python tools/vanillaforge_linter.py <addon-path>
```

Optional strict mode:

```bash
python tools/vanillaforge_linter.py --strict <addon-path>
```

The scanner should be treated as heuristic static analysis.

After meaningful addon changes, perform an in-client smoke test where practical:

```text
/reload
/luaerrors 1
```

Useful deeper diagnostics include:

```text
/classicapi
/dump
/etrace
/framestack
```

Never describe an addon as runtime-verified unless it was actually tested.

---

## Knowledge Maintenance

The framework is intentionally split into layers.

Do not automatically modify the system prompt or linter for every bug fixed in an
addon.

Promote knowledge only when it is:

- verified
- reusable across projects
- likely to recur
- important enough to justify permanent context
- placed in the correct layer

Use this placement rule:

```text
global engineering instruction  -> VANILLAFORGE_SYSTEM_PROMPT.md
ClassicAPI fact/API             -> CLASSICAPI_MASTER_REFERENCE.md
other engine/DLL fact           -> ENGINE_REFERENCE.md
reusable implementation pitfall -> KNOWN_PATTERNS.md
machine-detectable hazard       -> tools/vanillaforge_linter.py
project-specific quirk          -> keep it in that project
```

This keeps the framework useful instead of allowing it to become an archaeological
site of every bug ever encountered.

---

## Public Addon Neutrality

VanillaForge is the framework name, but public end-addons should normally
be described neutrally as addons for:

```text
World of Warcraft 1.12.1 Enhanced Client
```

or, when dependency information is useful:

```text
Enhanced WoW 1.12.1 client using ClassicAPI / SuperWoW
```

Do not leak VanillaForge branding, current-server branding, or other internal workspace
context into public addon titles, TOCs, READMEs, release notes, issue titles, or commit
messages unless explicitly intended.

---

## Design Goal

The framework does not aim to make 2006 addon code merely *look* modern.

It aims to produce addons engineered for the enhanced 1.12.1 client that actually
exists in the target environment:

- authoritative state
- deterministic lifecycle
- minimal hot-path work
- no obsolete compatibility baggage
- no invented APIs
- no unnecessary DLL dependencies
- focused verification
- finished engineering work before framework ceremony

> **Use the smallest set of verified enhanced primitives that produces the simplest,
> most correct implementation.**

---

## Maintainer

Maintained by [Fostercare5988](https://github.com/Fostercare5988).

Repository:
`Fostercare5988/VanillaForge-Addon-Engineering`
