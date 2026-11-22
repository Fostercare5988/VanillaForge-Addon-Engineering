"""The Poisons window teaches the addon (spec K6, tests 2): a rank and recipe are learned,
a higher rank replaces a lower one, a window with the high rank hidden never moves a poison
down, a header, an unknown row and another profession's window learn nothing, a changed
recipe at the same rank is saved, and an uncached reagent saves nothing half-read.
"""
import unittest
from rs_env import load

DUST, VIAL, ESSENCE = 8924, 8925, 8923


def poison(lua, name):
    return lua.eval(f"(function() local p = RestockDB.poisons['{name}']; if not p then return nil end"
                    " local out = {} for id, n in pairs(p.reagents) do out[#out + 1] = id .. '=' .. n end"
                    " table.sort(out) return p.item .. ':' .. p.rank .. ':' .. table.concat(out, ',') end)()")


class Learn(unittest.TestCase):
    def test_a_first_login_with_no_poisons_learns_rank_item_and_recipe(self):
        lua = load()
        lua.execute(f"recipe('Instant Poison VI', 8928, {{{DUST}, 4}}, {{{VIAL}, 1}}); openWindow()")
        self.assertEqual(poison(lua, "Instant Poison"), "8928:6:8924=4,8925=1")

    def test_no_numeral_is_rank_one_and_the_rank_reads_roman(self):
        lua = load()
        lua.execute(f"recipe('Wound Poison', 10918, {{2930, 1}}); recipe('Deadly Poison IV', 8985, {{5173, 5}});"
                    f" recipe('Mind-numbing Poison III', 9186, {{{ESSENCE}, 2}}); openWindow()")
        self.assertEqual(poison(lua, "Wound Poison"), "10918:1:2930=1")
        self.assertEqual(poison(lua, "Deadly Poison"), "8985:4:5173=5")
        self.assertEqual(poison(lua, "Mind-numbing Poison"), "9186:3:8923=2")

    def test_a_higher_rank_replaces_a_lower_one(self):
        lua = load()
        lua.execute(f"recipe('Deadly Poison IV', 8985, {{5173, 5}}); openWindow(); skills = {{}};"
                    f" recipe('Deadly Poison V', 20844, {{5173, 7}}, {{{VIAL}, 1}}); openWindow()")
        self.assertEqual(poison(lua, "Deadly Poison"), "20844:5:5173=7,8925=1")

    def test_a_hidden_high_rank_never_moves_a_poison_down(self):
        lua = load()
        lua.execute(f"recipe('Deadly Poison V', 20844, {{5173, 7}}); openWindow(); skills = {{}};"
                    f" recipe('Deadly Poison IV', 8985, {{5173, 5}}); openWindow()")
        self.assertEqual(poison(lua, "Deadly Poison"), "20844:5:5173=7")

    def test_a_changed_recipe_at_the_same_rank_is_saved(self):
        lua = load()
        lua.execute(f"recipe('Deadly Poison IV', 8985, {{5173, 5}}); openWindow(); skills = {{}};"
                    f" recipe('Deadly Poison IV', 8985, {{5173, 6}}, {{{VIAL}, 1}}); openWindow()")
        self.assertEqual(poison(lua, "Deadly Poison"), "8985:4:5173=6,8925=1")

    def test_headers_other_rows_and_other_windows_learn_nothing(self):
        lua = load()
        lua.execute("skills = { { 'Instant Poison', 'header' }, { 'Anesthetic Poison II', 'optimal', 1, { { 5, 1 } } },"
                    " { 'Elixir of Agility', 'optimal', 2, { { 5173, 1 } } }, { nil, 'optimal' } }; openWindow()")
        self.assertEqual(lua.eval("next(RestockDB.poisons)"), None)

    def test_an_uncached_reagent_or_a_missing_item_saves_nothing(self):
        lua = load()
        lua.execute(f"recipe('Wound Poison', 10918, {{2930, 1}}, {{nil, 1}}); recipe('Crippling Poison II', nil, {{{ESSENCE}, 3}});"
                    " recipe('Instant Poison VI', 8928); openWindow()")
        self.assertEqual(lua.eval("next(RestockDB.poisons)"), None)

    def test_a_lost_row_does_not_cost_the_others(self):
        lua = load()
        lua.execute(f"recipe('Wound Poison', 10918, {{nil, 1}}); recipe('Deadly Poison IV', 8985, {{5173, 5}}); openWindow()")
        self.assertIsNone(poison(lua, "Wound Poison"))
        self.assertEqual(poison(lua, "Deadly Poison"), "8985:4:5173=5")


if __name__ == "__main__":
    unittest.main()
