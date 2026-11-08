from __future__ import division

import math

from constants import TEMPERATURE_GUN_STATE
from items.vehicle_mechanics_types import VehicleMechanicKeys
from vehicles.mechanics.mechanic_helpers import getMechanicFromMechanicsParams, getPlayerVehicleMechanicComponent

from . import schedule

LOCKED = 'locked'
WARM = 'warm'
COLD = 'cold'


class GunStatus(object):
    __slots__ = ('state', 'seconds', 'potential_damage')

    def __init__(self, state, seconds=0.0, potential_damage=None):
        self.state = state
        self.seconds = seconds
        self.potential_damage = potential_damage


def shots_until_lock(temperature, lock_temperature, heating_per_shot):
    return max(0, int(math.ceil((lock_temperature - temperature) / heating_per_shot)))


def _seconds_until_cold(temperature, params):
    if temperature.state == TEMPERATURE_GUN_STATE.HEATING:
        return params.coolingDelay + temperature.currentTemperature / params.coolingPerSec
    return temperature.getCoolingTime(0.0)


def _potential_damage(ammo, temperature):
    if ammo.getCurrentShellCD() is None:
        return None
    gun = ammo.getGunSettings()
    shots = shots_until_lock(temperature.currentTemperature,
                             getMechanicFromMechanicsParams(gun.mechanicsParams, VehicleMechanicKeys.OVERHEAT_GUN).tempOverheatOnThreshold,
                             getMechanicFromMechanicsParams(gun.mechanicsParams, VehicleMechanicKeys.TEMPERATURE_GUN).heatingPerShot)
    shells_left = ammo.getCurrentShells()[0]
    if shells_left >= 0:
        shots = min(shots, shells_left)
    return int(round(shots * schedule.shell_damage(ammo)))


def read_status(ammo):
    if ammo is None:
        return None
    overheat = getPlayerVehicleMechanicComponent(VehicleMechanicKeys.OVERHEAT_GUN)
    temperature = getPlayerVehicleMechanicComponent(VehicleMechanicKeys.TEMPERATURE_GUN)
    if overheat is None or temperature is None:
        return None
    overheat_state = overheat.getMechanicState()
    temperature_state = temperature.getMechanicState()
    if overheat_state.isOverheated:
        return GunStatus(LOCKED, overheat_state.overheatTimeLeft(temperature_state))
    seconds = _seconds_until_cold(temperature_state, temperature.getComponentParams())
    state = WARM if seconds > 0 else COLD
    return GunStatus(state, max(0.0, seconds), _potential_damage(ammo, temperature_state))
