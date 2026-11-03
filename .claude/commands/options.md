Put the settings of the addon $ARGUMENTS, at
C:\Users\Fostercare\Desktop\OctoWoW\Interface\AddOns\$ARGUMENTS,
into AddOn Options the way FostercareTweaks 1.15 does: its window keeps two
columns, and every page is also a category under the addon in Game Menu >
AddOn Options, one column at full size. Follow VANILLAFORGE.md. One addon only.

The pattern and its rules: templates/ForgeUI/README.md, "Pages and AddOn
Options". The full example: FostercareTweaks Settings.lua (Feature, Slider,
Hint, the watched-aura and bar-row blocks, UI.Book). Read both before starting;
do not redesign them.

1. git fetch/status in the addon and VanillaForge. Stop if not clean and level.
2. Read the addon's settings files completely and its regression tests that
   touch settings. If it has no ForgeUI window yet, move it to ForgeUI first
   (templates/ForgeUI/README.md, "Adopting it") and keep every SavedVariables key.
3. Copy templates/ForgeUI/ForgeLayout.lua unchanged into the addon, after
   ForgeUI.lua in the TOC (a new file: the game must be restarted, say so). If
   its ForgeUI.lua differs from the template, keep the addon's palette; report
   any other difference instead of changing it.
4. Rebuild each page as sections: every control made at (0, 0) and handed to the
   layout (layout:Heading, :Switch, :Slider, :Hint, :Button, :Footer), right-
   column items with UI.R. Lists, grids, rows and cards become blocks with
   place(x, y, width) that fit 440+ (two columns) and about 320 (one). Syncs set
   values and visibility only; Refresh ends with book:Place(tab). Replace the
   old AddOn Options entry with UI.Book. Keep every widget name, label, tooltip
   and behaviour; the window should look the same within a few pixels.
5. A single-page window: one category with the addon's name, same rules.
6. Tests (regressions/$ARGUMENTS; load ForgeLayout.lua in the harness): every
   page is a category under the addon; a category borrows its page and gives it
   back; in AddOn Options every page is one column (no control right of the
   margin, none sharing a line) and back in the window two columns again; the
   window closes AddOn Options. The FostercareTweaks tests are the pattern
   (test_settings_2026_10_25.py, SettingsWindow). Existing tests that read old
   coordinates or helper names are updated, not deleted.
7. tools/audit_addon.py --run-tests: tests pass, 0 lint errors; read every
   warning (A4, A6 and D2 are leads to fix or suppress with a reason).
8. Update the addon's README, user guide and CLAUDE.md (where its settings are);
   bump the minor version; regressions/README.md (count and one line). Commit
   and push both repos (standing order).

Finish with the in-game checks: each page in AddOn Options readable at full
size, nothing cut off, scrolls to the end, no text running into the next
control; the window unchanged; a game restart because of the new file.
