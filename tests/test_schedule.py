import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'res', 'scripts', 'client', 'gui', 'mods'))

from gunner_hud.schedule import (LOADED, LOADING, NO_AMMO, QUEUED, Slot, build_schedule, full_in,
                                       reload_factor, shell_load_time)

RINOCERONTE_LIKE = (12.0, 13.0, 15.0)


class ShellLoadTimeTest(unittest.TestCase):

    def test_empty_magazine_uses_last_entry(self):
        self.assertEqual(shell_load_time(RINOCERONTE_LIKE, 3, 0, 1.0), 15.0)

    def test_shell_that_fills_magazine_uses_first_entry(self):
        self.assertEqual(shell_load_time(RINOCERONTE_LIKE, 3, 2, 1.0), 12.0)

    def test_factor_scales_time(self):
        self.assertAlmostEqual(shell_load_time(RINOCERONTE_LIKE, 3, 1, 0.9), 11.7)

    def test_short_table_is_clamped(self):
        self.assertEqual(shell_load_time((10.0,), 4, 0, 1.0), 10.0)


class ReloadFactorTest(unittest.TestCase):

    def test_prefers_first_shell_base_time(self):
        self.assertAlmostEqual(reload_factor(RINOCERONTE_LIKE, 3, 13.5, 99.0, 0), 0.9)

    def test_falls_back_to_current_shell_base_time(self):
        self.assertAlmostEqual(reload_factor(RINOCERONTE_LIKE, 3, 0.0, 11.7, 1), 0.9)

    def test_defaults_to_one(self):
        self.assertEqual(reload_factor(RINOCERONTE_LIKE, 3, 0.0, 0.0, 1), 1.0)


class BuildScheduleTest(unittest.TestCase):

    def test_one_shell_loaded_two_pending(self):
        slots = build_schedule(3, 1, 30, RINOCERONTE_LIKE, 1.0, 4.0)
        self.assertEqual(slots, [
            Slot(1, LOADED, 15.0),
            Slot(2, LOADING, 13.0, 4.0),
            Slot(3, QUEUED, 12.0, 16.0),
        ])
        self.assertEqual(full_in(slots), 16.0)

    def test_empty_magazine(self):
        slots = build_schedule(3, 0, 30, RINOCERONTE_LIKE, 1.0, 15.0)
        self.assertEqual([s.ready_in for s in slots], [15.0, 28.0, 40.0])

    def test_full_magazine_keeps_each_shell_load_time(self):
        slots = build_schedule(3, 3, 30, RINOCERONTE_LIKE, 0.9, 0.0)
        self.assertEqual([s.state for s in slots], [LOADED] * 3)
        self.assertEqual([round(s.own_time, 2) for s in slots], [13.5, 11.7, 10.8])
        self.assertEqual(full_in(slots), 0.0)

    def test_running_out_of_ammo(self):
        slots = build_schedule(3, 0, 2, RINOCERONTE_LIKE, 1.0, 15.0)
        self.assertEqual([s.state for s in slots], [LOADING, QUEUED, NO_AMMO])
        self.assertEqual(full_in(slots), 28.0)


if __name__ == '__main__':
    unittest.main()
