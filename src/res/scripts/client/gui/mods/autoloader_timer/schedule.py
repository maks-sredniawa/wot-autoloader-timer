from __future__ import division

LOADED = 'loaded'
LOADING = 'loading'
QUEUED = 'queued'
NO_AMMO = 'no_ammo'


class Slot(object):
    __slots__ = ('number', 'state', 'own_time', 'ready_in')

    def __init__(self, number, state, own_time=0.0, ready_in=0.0):
        self.number = number
        self.state = state
        self.own_time = own_time
        self.ready_in = ready_in

    def __eq__(self, other):
        return (self.number, self.state, round(self.own_time, 3), round(self.ready_in, 3)) == \
               (other.number, other.state, round(other.own_time, 3), round(other.ready_in, 3))

    def __repr__(self):
        return 'Slot(%d, %s, %.2f, %.2f)' % (self.number, self.state, self.own_time, self.ready_in)


def shell_damage(ammo):
    return ammo.getGunSettings().getShellDescriptor(ammo.getCurrentShellCD()).armorDamage[0]


def shell_load_time(reload_times, clip_size, shells_in_clip, factor):
    """Seconds to load the next shell when `shells_in_clip` are already loaded.

    The game stores autoreload times with the shell that fills the magazine first,
    so the shell loaded into an empty magazine is the last entry.
    """
    index = clip_size - 1 - shells_in_clip
    index = max(0, min(index, len(reload_times) - 1))
    return reload_times[index] * factor


def factor_from_empty_magazine_time(reload_times, empty_magazine_time):
    return empty_magazine_time / reload_times[-1]


def reload_factor(reload_times, clip_size, first_base_time, base_time, shells_in_clip):
    if first_base_time > 0:
        return first_base_time / reload_times[-1]
    if base_time > 0:
        return base_time / shell_load_time(reload_times, clip_size, shells_in_clip, 1.0)
    return 1.0


def build_schedule(clip_size, shells_in_clip, shells_total, reload_times, factor, current_left):
    loadable = min(clip_size, max(shells_total, shells_in_clip))
    slots = []
    ready_in = 0.0
    for number in range(1, clip_size + 1):
        own_time = shell_load_time(reload_times, clip_size, number - 1, factor)
        if number <= shells_in_clip:
            slots.append(Slot(number, LOADED, own_time))
            continue
        if number > loadable:
            slots.append(Slot(number, NO_AMMO, own_time))
            continue
        if number == shells_in_clip + 1:
            ready_in = current_left
            slots.append(Slot(number, LOADING, own_time, ready_in))
        else:
            ready_in += own_time
            slots.append(Slot(number, QUEUED, own_time, ready_in))
    return slots


def full_in(slots):
    pending = [slot.ready_in for slot in slots if slot.state in (LOADING, QUEUED)]
    return pending[-1] if pending else 0.0
