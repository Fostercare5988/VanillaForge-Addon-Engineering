# ForgeUI

The AutoLazy 1.2 options layout as a drop-in kit: a floating rounded card with a
soft shadow, a segmented tab track, sliding switches, radio dots and pill
buttons. Approved by the user on 2026-10-20 as the house style for addon
settings.

## Files

| File | Purpose |
| --- | --- |
| `ForgeUI.lua` | Palettes, shapes and widgets, exported as `ns.UI`. |
| `Media/Disc.tga` | White disc; every rounded shape is a tinted nine-slice of it. |
| `Media/Shadow.tga` | Soft shadow disc for the card. |
| `Media/Close.tga` | Close glyph. |
| `Example.lua` | A two-tab window showing the layout grid. Not shipped. |

## Adopting it in an addon

1. Copy `ForgeUI.lua` and the `Media` folder into the addon folder.
2. List `ForgeUI.lua` in the TOC before any file that uses it. Media paths are
   built from the addon folder name, so nothing needs renaming.
3. In the GUI files, `local addonName, ns = ...` and `local UI = ns.UI`.
4. Give every named frame the addon's prefix (`MyAddon_...`).
5. Replace any locale layer and old skin code; keep SavedVariables keys.
6. Run the linter and check the window in game at your UI scales.

## Palette

Set `PALETTE` at the top of `ForgeUI.lua`. `Ember` is the standard for every
addon we work on: a warm mid-grey surface with orange headings, controls and
peach text, as shipped in AutoLazy 1.2. `Teal` and `Plum` (the original AutoLazy
colors) are kept only for reference. A palette needs these roles:

| Role | Used for |
| --- | --- |
| `surface` | Card fill, radio center. |
| `edge` | Thin rim around the card, accent color at about 0.40 alpha. |
| `track` | Tab track behind ghost buttons. |
| `control` | Unselected buttons and switch tracks. |
| `selected` | Active tab, selected list entry, switch track when on. |
| `accent` | Radio ring and dot when on. |
| `knob` | Switch knob when off (white when on). |
| `heading` | Title, section headings, unfonted labels. |
| `text` | Switch labels, button text on fills. |
| `hint` | Version, help lines, inactive tabs, off radio rings, close glyph. |

Keep white text readable on `selected`, and keep `hint` legible on `surface`.

## Layout grid

All values are UI pixels in a 500-wide window.

- **Card:** radius 14; shadow 12 out, 3 down. DIALOG strata, draggable, clamped,
  closes on Escape. The top is pinned after a drag so tabs of different height
  grow downward.
- **Title:** `GameFontNormalLarge` at (26, -18) in `heading`; version beside it in
  `GameFontDisableSmall`. Close glyph 22x22 at (-14, -14).
- **Tabs:** track at (24, -48), 30 high, full width minus 48, radius 15. Ghost
  pills 24 high, 3 inset, 1 apart, `GameFontHighlight`. Each tab sets its own
  window height.
- **Content:** first heading at y -98 with tabs (-56 without). Left margin 28,
  second column at 264, action buttons at 300 with width 172 (ending 28 from the
  right edge).
- **Rows:** switch rows 36 apart; dense pages may use 26. A dependent switch
  indents to x 44 and dims while its parent is off. List rows 26 high, 28 apart,
  faint `row` band with a 4 outset.
- **Sliders:** `UI.Slider` puts the label and value on one line over a 6-high
  rounded track with an accent knob; blocks stack 42 apart. Show saved values
  with `UI.SetSlider` so a refresh never writes settings.
- **Choices:** `UI.Segmented` is the tab track at any size, for a small set of
  exclusive choices (a bracket, a mode).
- **Footer:** buttons anchored BOTTOMLEFT at (28, 18); pager text centered 50 up.
- **Buttons:** one button per job. Previews are a single toggle that shows every
  movable frame, filled while on; one reset covers all positions. No Close
  button: the close glyph and Escape do that. Sound checks belong to the preview
  or sit as a small ghost "Play" beside their setting, not as extra test buttons.
- **Text:** headings are small capitals (`GameFontNormalSmall`) in `heading`;
  help lines `GameFontDisableSmall` in `hint`; detail goes in tooltips.
- **Disabled:** controls dim to 0.4 alpha and disable. Use `UI.Sync(widget,
  value, enabled)` from each page's refresh.

## Behavior notes

- Widgets repaint only on state change; nothing polls. Refresh pages from
  settings changes and `OnShow`.
- Handlers use `self or this or widget`, so they work with modern script
  arguments on or off.
- A native checkbutton toggles itself before `OnClick`. For radio groups, set
  the setting and repaint every choice with `UI.SetCheck`.
- Shapes compare colors by table identity, so palettes are chosen at copy time,
  not switched live.
