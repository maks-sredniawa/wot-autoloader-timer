from __future__ import division

import BigWorld
from PlayerEvents import g_playerEvents
from debug_utils import LOG_CURRENT_EXCEPTION
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider

from . import config, gun_cooling, schedule
from .view import PanelView, format_cooling, format_magazine, format_segments

TICK_SECONDS = 0.1


class AutoloaderTimer(object):
    _sessionProvider = dependency.descriptor(IBattleSessionProvider)

    def __init__(self):
        self._settings = config.load()
        self._view = None
        self._callback_id = None
        self._crosshair = None
        self._factor = 1.0

    def start(self):
        if not self._settings['enabled']:
            return
        self._view = PanelView(self._settings, self._on_moved)
        g_playerEvents.onAvatarReady += self._on_avatar_ready
        g_playerEvents.onAvatarBecomeNonPlayer += self._on_avatar_left

    def stop(self):
        g_playerEvents.onAvatarReady -= self._on_avatar_ready
        g_playerEvents.onAvatarBecomeNonPlayer -= self._on_avatar_left
        self._cancel_tick()
        self._unfollow_crosshair()
        if self._view is not None:
            self._view.destroy()
            self._view = None

    @property
    def settings(self):
        return self._settings

    def _on_moved(self):
        config.save(self._settings)

    def _on_avatar_ready(self):
        self._factor = 1.0
        self._cancel_tick()
        self._follow_crosshair()
        self._tick()

    def _on_avatar_left(self):
        self._cancel_tick()
        self._unfollow_crosshair()
        if self._view is not None:
            self._view.hide()

    def _cancel_tick(self):
        if self._callback_id is not None:
            BigWorld.cancelCallback(self._callback_id)
            self._callback_id = None

    def _tick(self):
        self._callback_id = BigWorld.callback(TICK_SECONDS, self._tick)
        try:
            self._render()
        except Exception:
            LOG_CURRENT_EXCEPTION()
            self._view.hide()

    def _render(self):
        self._view.show(self._segments())

    def _crosshair_events(self, crosshair):
        return (crosshair.onCrosshairPositionChanged, crosshair.onCrosshairSizeChanged,
                crosshair.onCrosshairScaleChanged, crosshair.onCrosshairViewChanged)

    def _follow_crosshair(self):
        self._unfollow_crosshair()
        crosshair = self._sessionProvider.shared.crosshair
        if crosshair is None:
            return
        self._crosshair = crosshair
        for event in self._crosshair_events(crosshair):
            event += self._on_crosshair_changed
        self._on_crosshair_changed()

    def _unfollow_crosshair(self):
        if self._crosshair is None:
            return
        for event in self._crosshair_events(self._crosshair):
            event -= self._on_crosshair_changed
        self._crosshair = None

    def _on_crosshair_changed(self, *_):
        try:
            self._view.set_anchor(*self._crosshair_offset(self._crosshair))
        except Exception:
            LOG_CURRENT_EXCEPTION()

    def _crosshair_offset(self, crosshair):
        scale = max(crosshair.getScaleFactor(), 1.0)
        width, height = crosshair.getSize()
        x, y = crosshair.getDisaredPosition()
        return (int(x - width / scale / 2), int(y - height / scale / 2))

    def _segments(self):
        slots = self.slots()
        if slots is None:
            return self._no_autoreload_segments()
        if self._settings['hideWhenFull'] and all(slot.state == schedule.LOADED for slot in slots):
            return None
        return format_segments(slots, self._settings, schedule.shell_damage(self._sessionProvider.shared.ammo))

    def _no_autoreload_segments(self):
        ammo = self._sessionProvider.shared.ammo
        if ammo is not None and ammo.getGunSettings().isRegularClip:
            return self._magazine_segments(ammo)
        return self._cooling_segments()

    def _magazine_segments(self, ammo):
        if ammo.getCurrentShellCD() is None:
            return None
        shells_total, shells_in_clip = ammo.getCurrentShells()
        if shells_in_clip < 0 or max(shells_total, shells_in_clip) <= 0:
            return None
        clip_size = ammo.getGunSettings().clip.size
        if self._settings['hideWhenFull'] and shells_in_clip == clip_size:
            return None
        return format_magazine(shells_in_clip, clip_size, schedule.shell_damage(ammo), self._settings)

    def _cooling_segments(self):
        status = gun_cooling.read_status(self._sessionProvider.shared.ammo)
        if status is None or (self._settings['hideWhenFull'] and status.state == gun_cooling.COLD):
            return None
        return format_cooling(status, self._settings)

    def slots(self):
        ammo = self._sessionProvider.shared.ammo
        if ammo is None:
            return None
        gun = ammo.getGunSettings()
        if not gun.hasAutoReload() or ammo.getCurrentShellCD() is None:
            return None
        shells_total, shells_in_clip = ammo.getCurrentShells()
        if shells_total < 0 or shells_in_clip < 0:
            return None
        clip_size = gun.clip.size
        reload_times = gun.autoReload.reloadTime
        current_left = self._current_shell_time_left(ammo, reload_times, clip_size, shells_in_clip)
        return schedule.build_schedule(clip_size, shells_in_clip, shells_total, reload_times, self._factor, current_left)

    def _current_shell_time_left(self, ammo, reload_times, clip_size, shells_in_clip):
        clip_state = ammo.getPartiallyReloadingClipState()
        if clip_state.isReloading() and clip_state.getBaseValue() > 0:
            self._factor = schedule.reload_factor(reload_times, clip_size, 0.0, clip_state.getBaseValue(), shells_in_clip)
            return clip_state.getTimeLeft()
        gun = ammo.getGunSettings()
        if ammo.getShellChangeTime() > 0 and gun.hasShellChangeFactor():
            empty_magazine_time = ammo.getShellChangeTime() / gun.getShellChangeFactor()
            self._factor = schedule.factor_from_empty_magazine_time(reload_times, empty_magazine_time)
        gun_state = ammo.getGunReloadingState()
        if shells_in_clip == 0 and gun_state.isReloading():
            return gun_state.getTimeLeft()
        return schedule.shell_load_time(reload_times, clip_size, shells_in_clip, self._factor)
