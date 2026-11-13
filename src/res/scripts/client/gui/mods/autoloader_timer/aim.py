from __future__ import division

import math

AIMING = 'aiming'
ACCURATE = 'accurate'
AIMED = 'aimed'

AIMED_BELOW_SECONDS = 0.05
_MEASURED_DELAY_LIMIT = 2.0


class DualAccuracy(object):
    __slots__ = ('active', 'factor', 'cooldown')

    def __init__(self, active, factor, cooldown=None):
        self.active = active
        self.factor = factor
        self.cooldown = cooldown


class AimStatus(object):
    __slots__ = ('phase', 'fill', 'percent', 'seconds', 'limit', 'locked', 'cooldown')

    def __init__(self, phase, fill, percent, seconds, limit=None, locked=False, cooldown=None):
        self.phase = phase
        self.fill = fill
        self.percent = percent
        self.seconds = seconds
        self.limit = limit
        self.locked = locked
        self.cooldown = cooldown


def seconds_to_aim(current, ideal, aiming_time):
    if current <= ideal or ideal <= 0 or aiming_time <= 0:
        return 0.0
    return aiming_time * math.log(current / ideal)


def _ratio(ideal, current):
    if current <= 0:
        return 1.0
    return max(0.0, min(1.0, ideal / current))


def accurate_mode_active(ideal, accurate_ideal, factor):
    # The game shrinks its ideal circle to the accurate one only while the mode is on.
    return accurate_ideal > ideal * (1 + factor) / 2


def aim_status(current, stationary_best, aiming_time, dual=None):
    accurate_ideal = stationary_best * dual.factor if dual is not None else stationary_best
    ideal = accurate_ideal if dual is not None and dual.active else stationary_best
    seconds = seconds_to_aim(current, ideal, aiming_time)
    aimed = seconds < AIMED_BELOW_SECONDS
    if aimed:
        current = ideal
    if dual is None:
        percent = _ratio(ideal, current)
        return AimStatus(AIMED if aimed else AIMING, percent, percent, seconds)
    fill = _ratio(accurate_ideal, current)
    percent = fill / dual.factor
    if dual.active:
        phase = AIMED if aimed else ACCURATE
        return AimStatus(phase, fill, percent, seconds, limit=dual.factor)
    return AimStatus(AIMED if aimed else AIMING, min(fill, dual.factor), percent, seconds,
                     limit=dual.factor, locked=True, cooldown=dual.cooldown)


class CooldownTracker(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self._was_active = None
        self._since = None
        self._measured = None

    def update(self, active, now, base_delay):
        was_active, self._was_active = self._was_active, active
        if active:
            if was_active is False and self._since is not None:
                self._remember(now - self._since, base_delay)
            self._since = None
            return None
        if was_active:
            self._since = now
        if self._since is None:
            return None
        delay = self._measured if self._measured is not None else base_delay
        return max(0.0, delay - (now - self._since))

    def _remember(self, measured, base_delay):
        if 0 < measured < base_delay * _MEASURED_DELAY_LIMIT:
            self._measured = measured
