from __future__ import division

import BigWorld
from PlayerEvents import g_playerEvents
from debug_utils import LOG_CURRENT_EXCEPTION, LOG_NOTE
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider

from . import aim, config, gun_cooling, schedule
from .aim_view import AimBarView
from .view import PanelView, format_cooling, format_magazine, format_segments

TICK_SECONDS = 0.1


class GunnerHud(object):
    _sessionProvider = dependency.descriptor(IBattleSessionProvider)

    def __init__(self):
        self._settings = config.load()
        self._view = None
        self._aim_view = None
        self._cooldown = aim.CooldownTracker()
        self._last_accurate_mode = None
        self._shell_counts = {}
        self._watched_ammo = None
        self._callback_id = None
        self._crosshair = None
        self._factor = 1.0

    def start(self):
        if not self._settings['enabled'] or self._view is not None:
            return
        self._view = PanelView(self._settings, self._on_moved)
        self._sync_aim_view()
        g_playerEvents.onAvatarReady += self._on_avatar_ready
        g_playerEvents.onAvatarBecomeNonPlayer += self._on_avatar_left

    def apply_settings(self):
        if not self._settings['enabled']:
            self.stop()
            return
        self.start()
        self._sync_aim_view()

    def _sync_aim_view(self):
        wanted = self._settings['aimTimer']['enabled']
        if wanted and self._aim_view is None:
            self._aim_view = AimBarView(self._settings, self._on_moved)
            if self._crosshair is not None:
                self._on_crosshair_changed()
        elif not wanted and self._aim_view is not None:
            self._aim_view.destroy()
            self._aim_view = None

    def stop(self):
        if self._view is None:
            return
        g_playerEvents.onAvatarReady -= self._on_avatar_ready
        g_playerEvents.onAvatarBecomeNonPlayer -= self._on_avatar_left
        self._cancel_tick()
        self._unfollow_crosshair()
        self._unwatch_shots()
        self._view.destroy()
        self._view = None
        if self._aim_view is not None:
            self._aim_view.destroy()
            self._aim_view = None

    @property
    def settings(self):
        return self._settings

    def _on_moved(self):
        config.save(self._settings)

    def _on_avatar_ready(self):
        self._factor = 1.0
        self._cooldown.reset()
        self._last_accurate_mode = None
        self._cancel_tick()
        self._follow_crosshair()
        self._watch_shots()
        self._tick()

    def _on_avatar_left(self):
        self._cancel_tick()
        self._unfollow_crosshair()
        self._unwatch_shots()
        if self._view is not None:
            self._view.hide()
        if self._aim_view is not None:
            self._aim_view.hide()

    def _cancel_tick(self):
        if self._callback_id is not None:
            BigWorld.cancelCallback(self._callback_id)
            self._callback_id = None

    def _tick(self):
        self._callback_id = BigWorld.callback(TICK_SECONDS, self._tick)
        try:
            self._view.show(self._segments())
        except Exception:
            LOG_CURRENT_EXCEPTION()
            self._view.hide()
        if self._aim_view is not None:
            try:
                self._aim_view.show(self._aim_status())
            except Exception:
                LOG_CURRENT_EXCEPTION()
                self._aim_view.hide()

    def _watch_shots(self):
        self._unwatch_shots()
        ammo = self._sessionProvider.shared.ammo
        if ammo is None:
            return
        self._watched_ammo = ammo
        self._shell_counts = {}
        ammo.onShellsUpdated += self._on_shells_updated

    def _unwatch_shots(self):
        if self._watched_ammo is not None:
            self._watched_ammo.onShellsUpdated -= self._on_shells_updated
            self._watched_ammo = None

    def _on_shells_updated(self, shell_cd, quantity, *_):
        previous = self._shell_counts.get(shell_cd)
        self._shell_counts[shell_cd] = quantity
        if previous is not None and quantity < previous:
            self._cooldown.shot(BigWorld.time())

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
            x, y = self._crosshair_offset(self._crosshair)
            view_id = self._crosshair.getViewID()
            self._view.set_anchor(x, y, view_id)
            if self._aim_view is not None:
                self._aim_view.set_anchor(x, y, view_id)
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
        if not self._settings['autoreloaderLine']:
            return None
        if self._settings['hideWhenFull'] and all(slot.state == schedule.LOADED for slot in slots):
            return None
        return format_segments(slots, self._settings, schedule.shell_damage(self._sessionProvider.shared.ammo))

    def _no_autoreload_segments(self):
        ammo = self._sessionProvider.shared.ammo
        if ammo is not None and ammo.getGunSettings().isRegularClip:
            return self._magazine_segments(ammo)
        return self._cooling_segments()

    def _magazine_segments(self, ammo):
        if not self._settings['magazineLine'] or ammo.getCurrentShellCD() is None:
            return None
        shells_total, shells_in_clip = ammo.getCurrentShells()
        if shells_in_clip < 0 or max(shells_total, shells_in_clip) <= 0:
            return None
        clip_size = ammo.getGunSettings().clip.size
        if self._settings['hideWhenFull'] and shells_in_clip == clip_size:
            return None
        return format_magazine(shells_in_clip, clip_size, schedule.shell_damage(ammo), self._settings)

    def _cooling_segments(self):
        if not self._settings['aresLine']:
            return None
        status = gun_cooling.read_status(self._sessionProvider.shared.ammo)
        if status is None or (self._settings['hideWhenFull'] and status.state == gun_cooling.COLD):
            return None
        return format_cooling(status, self._settings)

    def _aim_status(self):
        player = BigWorld.player()
        rotator = getattr(player, 'gunRotator', None)
        if rotator is None or not player.isVehicleAlive:
            return None
        # Private game state, as in XVM's aim timer. The game's own "ideal" circle includes the movement
        # penalty, so the best circle is rebuilt from the gun's dispersion and the stationary multiplier.
        current, ideal, _, hot_ideal = rotator._VehicleGunRotator__dispersionAngles
        if min(current, ideal, hot_ideal) <= 0:
            return None
        stationary_multiplier, aiming_time = player._PlayerAvatar__dispersionInfo[0], player._PlayerAvatar__dispersionInfo[5]
        gun = player._PlayerAvatar__getDetailedVehicleDescriptor().gun
        best = gun.shotDispersionAngle * stationary_multiplier
        if 'dualAccuracy' not in gun.tags:
            return aim.aim_status(current, best, aiming_time)
        # On dual accuracy guns the base dispersion is the cooled one; the after-shot value is the hot one.
        factor = gun.shotDispersionAngle / gun.dualAccuracy.afterShotDispersionAngle
        return aim.aim_status(current, best / factor, aiming_time, self._dual_accuracy(gun, ideal, hot_ideal, factor))

    def _dual_accuracy(self, gun, ideal, hot_ideal, factor):
        active = aim.accurate_mode_active(ideal, hot_ideal, factor)
        if active != self._last_accurate_mode:
            self._last_accurate_mode = active
            LOG_NOTE('[gunner_hud] accurate mode %s (ideal %.4f, hot ideal %.4f, factor %.3f, base delay %.2f)'
                     % ('on' if active else 'off', ideal, hot_ideal, factor, gun.dualAccuracy.coolingDelay))
        cooldown = self._cooldown.update(active, BigWorld.time(), gun.dualAccuracy.coolingDelay)
        return aim.DualAccuracy(active, factor, cooldown)

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
