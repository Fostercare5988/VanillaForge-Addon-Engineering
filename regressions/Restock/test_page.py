"""The page in ClassicAPI's Settings window and /restock (spec 4.4, tests 1 and 7):
a number row per target in play order, the defaults are Claude's targets, using a row
changes what is bought, Defaults puts each back, the slash command opens the page, a
non-rogue has nothing, old keys are swept and the learned poisons kept. Also what listens
at rest, and which globals the addon makes. First login, odd saved data.
"""
import unittest
import wowkit
from rs_env import load, CLAUDE, MOCK, ROOT

PAGE = "settingsWindow.find('Restock')"
DEFAULTS = {"keepInstant": 20, "keepDissolvent": 0, "keepCrippling": 10, "keepMindNumbing": 0, "keepDeadly": 20,
            "keepCorrosive": 0, "keepWound": 0, "keepAgitating": 0, "keepFlashPowder": 20}


def rows(lua):
    return lua.eval(f'''(function()
        local out = {{}}
        for _, r in ipairs({PAGE}.layout.rows) do out[#out + 1] = r:GetName() end
        return table.concat(out, '|')
    end)()''')


def stocked(lua):
    lua.execute("poisonVendor(); sells(5140)")


class Page(unittest.TestCase):
    def test_the_rows_in_play_order(self):
        self.assertEqual(rows(load()), "Poisons to carry|Instant Poison|Dissolvent Poison|Crippling Poison|"
                         "Mind-numbing Poison|Deadly Poison|Corrosive Poison|Wound Poison|Agitating Poison|"
                         "Reagents|Flash Powder")

    def test_the_rows_are_number_boxes_with_claudes_defaults(self):
        lua = load()
        self.assertEqual(lua.eval(f"{PAGE}.layout.rows[2].template"), "ClassicAPISettingsNumberBoxControlTemplate")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"RestockDB.{key}"), value, key)
            self.assertEqual(lua.eval(f"Settings.GetSetting('Restock_{key}'):GetDefaultValue()"), value, key)

    def test_a_row_changes_what_is_bought_and_defaults_put_it_back(self):
        lua = load(CLAUDE)
        stocked(lua)
        lua.execute("settingsWindow.use('Restock_keepDeadly', 0); settingsWindow.use('Restock_keepInstant', 0);"
                    " settingsWindow.use('Restock_keepCrippling', 0); settingsWindow.use('Restock_keepFlashPowder', 0)")
        lua.execute("openVendor()")
        self.assertEqual(lua.eval("#purchases"), 0)
        self.assertEqual(lua.eval("#chat"), 0)
        lua.execute(f"settingsWindow.defaults({PAGE})")
        for key, value in DEFAULTS.items():
            self.assertEqual(lua.eval(f"RestockDB.{key}"), value, key)
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("bought(5140)"), 20)

    def test_odd_numbers_are_read_as_whole_numbers_from_zero(self):
        lua = load(CLAUDE + " RestockDB.keepInstant = -5; RestockDB.keepDeadly = 'abc'; RestockDB.keepCrippling = 2.7;"
                   " RestockDB.keepFlashPowder = 0")
        stocked(lua)
        lua.execute("openVendor(); finish()")
        self.assertEqual(lua.eval("bought(8923)"), 6)  # 2 Crippling Poison, 3 Essence each
        self.assertEqual(lua.eval("bought(5173)"), 0)
        self.assertEqual(lua.eval("bought(8924)"), 0)

    def test_the_slash_command_opens_the_page(self):
        lua = load()
        self.assertEqual(lua.eval("SLASH_RESTOCK1"), "/restock")
        lua.execute("SlashCmdList.RESTOCK('')")
        self.assertEqual(lua.eval("settingsWindow.opened:GetName()"), "Restock")

    def test_a_non_rogue_has_no_page_no_command_and_no_events(self):
        lua = load("", "playerClass = 'WARRIOR'")
        self.assertIsNone(lua.eval(f"{PAGE}"))
        self.assertIsNone(lua.eval("SLASH_RESTOCK1"))
        self.assertIsNone(lua.eval("SlashCmdList.RESTOCK"))
        self.assertEqual(lua.eval("listening()"), "")

    def test_old_keys_are_swept_and_the_learned_poisons_kept(self):
        lua = load(CLAUDE.replace("RestockDB = {", "RestockDB = { KeepFlashPowder = true, Ranks = {}, Recipes = {},"
                                  " keepWound = 3,"))
        for key in ("KeepFlashPowder", "Ranks", "Recipes"):
            self.assertIsNone(lua.eval(f"RestockDB.{key}"), key)
        self.assertEqual(lua.eval("RestockDB.keepWound"), 3)
        self.assertEqual(lua.eval("RestockDB.poisons['Deadly Poison'].rank"), 4)

    def test_a_bad_poisons_value_is_replaced(self):
        lua = load("RestockDB = { poisons = 5 }")
        self.assertEqual(lua.eval("type(RestockDB.poisons)"), "table")


class AtRest(unittest.TestCase):
    def test_what_listens_and_no_timer(self):
        lua = load(CLAUDE)
        lua.execute('fire("ZONE_CHANGED_NEW_AREA") fire("PLAYER_ENTERING_WORLD") step(5) step(5)')
        self.assertEqual(lua.eval("listening()"), "MERCHANT_CLOSED,MERCHANT_SHOW,TRADE_SKILL_SHOW")
        self.assertEqual(lua.eval("liveTimers()"), 0)

    def test_the_only_globals(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("before = { __addon_ns = true, event = true }; for k in pairs(_G) do before[k] = true end")
        wowkit.load_addon(lua, ROOT, "Restock")
        lua.execute('fire("VARIABLES_LOADED") fire("PLAYER_LOGIN") fire("PLAYER_ENTERING_WORLD")')
        made = lua.eval("(function() local out = {} for k in pairs(_G) do if not before[k] then out[#out + 1] = k end end"
                        " table.sort(out) return table.concat(out, ',') end)()")
        self.assertEqual(made, "RestockDB,SLASH_RESTOCK1")

    def test_without_classicapi_one_error_and_nothing_else(self):
        lua = wowkit.runtime()
        lua.execute(MOCK)
        lua.execute("CLASSIC_API_VERSION = nil")
        with self.assertRaises(Exception) as caught:
            wowkit.load_addon(lua, ROOT, "Restock")
        self.assertIn("Restock needs ClassicAPI.", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
