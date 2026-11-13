import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'res', 'scripts', 'client', 'gui', 'mods'))

from autoloader_timer.aim import (ACCURATE, AIMED, AIMING, CooldownTracker, DualAccuracy, aim_status,
                                  seconds_to_aim)


class SecondsToAimTest(unittest.TestCase):

    def test_circle_twice_the_ideal_needs_aiming_time_times_ln2(self):
        self.assertAlmostEqual(seconds_to_aim(0.4, 0.2, 2.0), 2.0 * math.log(2))

    def test_circle_at_ideal_is_aimed(self):
        self.assertEqual(seconds_to_aim(0.2, 0.2, 2.0), 0.0)

    def test_bad_data_reads_as_aimed(self):
        self.assertEqual(seconds_to_aim(0.4, 0.0, 2.0), 0.0)
        self.assertEqual(seconds_to_aim(0.4, 0.2, 0.0), 0.0)


class AimStatusTest(unittest.TestCase):

    def test_normal_gun_aiming(self):
        status = aim_status([0.4, 0.2, 0.4, 0.2], 2.0)
        self.assertEqual((status.phase, status.fill, status.percent, status.limit), (AIMING, 0.5, 0.5, None))
        self.assertFalse(status.locked)

    def test_normal_gun_aimed(self):
        status = aim_status([0.2, 0.2, 0.2, 0.2], 2.0)
        self.assertEqual((status.phase, status.fill, status.percent), (AIMED, 1.0, 1.0))

    def test_circle_one_percent_above_ideal_reads_as_fully_aimed(self):
        status = aim_status([0.202, 0.2, 0.202, 0.2], 2.0)
        self.assertEqual((status.phase, status.fill, status.percent), (AIMED, 1.0, 1.0))

    def test_accurate_mode_one_percent_above_ideal_reads_as_fully_aimed(self):
        status = aim_status([0.2424, 0.24, 0.2424, 0.24], 2.0, DualAccuracy(True, 0.6))
        self.assertEqual((status.phase, status.fill, status.percent), (AIMED, 1.0, 1.0))

    def test_cooling_gun_fills_up_to_the_hot_limit_and_counts_against_the_hot_circle(self):
        status = aim_status([0.5, 0.4, 0.5, 0.24], 2.0, DualAccuracy(False, 0.6, 3.1))
        self.assertEqual((status.phase, status.limit, status.cooldown), (AIMING, 0.6, 3.1))
        self.assertTrue(status.locked)
        self.assertAlmostEqual(status.fill, 0.48)
        self.assertAlmostEqual(status.percent, 0.8)

    def test_cooling_gun_aimed_stops_at_the_limit(self):
        status = aim_status([0.4, 0.4, 0.4, 0.24], 2.0, DualAccuracy(False, 0.6, 1.0))
        self.assertEqual(status.phase, AIMED)
        self.assertAlmostEqual(status.fill, 0.6)
        self.assertTrue(status.locked)

    def test_accurate_mode_aiming_is_cyan_phase_past_the_limit(self):
        status = aim_status([0.4, 0.24, 0.4, 0.24], 2.0, DualAccuracy(True, 0.6))
        self.assertEqual((status.phase, status.limit), (ACCURATE, 0.6))
        self.assertFalse(status.locked)
        self.assertAlmostEqual(status.fill, 0.6)

    def test_accurate_mode_aimed_is_the_best_shot(self):
        status = aim_status([0.24, 0.24, 0.24, 0.24], 2.0, DualAccuracy(True, 0.6))
        self.assertEqual((status.phase, status.fill, status.percent), (AIMED, 1.0, 1.0))


class CooldownTrackerTest(unittest.TestCase):

    def test_unknown_start_shows_no_countdown(self):
        self.assertIsNone(CooldownTracker().update(False, 10.0, 4.0))

    def test_counts_down_the_base_delay_from_the_switch_off(self):
        tracker = CooldownTracker()
        tracker.update(True, 9.0, 4.0)
        self.assertEqual(tracker.update(False, 10.0, 4.0), 4.0)
        self.assertEqual(tracker.update(False, 11.5, 4.0), 2.5)
        self.assertEqual(tracker.update(False, 20.0, 4.0), 0.0)

    def test_uses_the_measured_delay_after_one_full_cycle(self):
        tracker = CooldownTracker()
        tracker.update(True, 9.0, 4.0)
        tracker.update(False, 10.0, 4.0)
        self.assertIsNone(tracker.update(True, 13.5, 4.0))
        tracker.update(False, 20.0, 4.0)
        self.assertEqual(tracker.update(False, 21.0, 4.0), 2.5)

    def test_ignores_a_cycle_far_longer_than_the_base_delay(self):
        tracker = CooldownTracker()
        tracker.update(True, 0.0, 4.0)
        tracker.update(False, 1.0, 4.0)
        tracker.update(True, 30.0, 4.0)
        tracker.update(False, 40.0, 4.0)
        self.assertEqual(tracker.update(False, 41.0, 4.0), 3.0)

    def test_reset_forgets_the_measurement(self):
        tracker = CooldownTracker()
        tracker.update(True, 9.0, 4.0)
        tracker.update(False, 10.0, 4.0)
        tracker.update(True, 13.0, 4.0)
        tracker.reset()
        tracker.update(True, 0.0, 4.0)
        self.assertEqual(tracker.update(False, 1.0, 4.0), 4.0)


if __name__ == '__main__':
    unittest.main()
