from debug_utils import LOG_CURRENT_EXCEPTION, LOG_ERROR

_timer = None
_reload_chat_installed = False


def init():
    global _timer
    try:
        import gui.mods.gambiter  # noqa: F401
    except ImportError:
        LOG_ERROR('[gunner_hud] GUIFlash (gambiter.guiflash) is not installed; the mod is disabled.')
        return
    try:
        from gui.mods.gunner_hud.timer import GunnerHud
        _timer = GunnerHud()
        _timer.start()
        _sync_reload_chat()
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return
    _register_settings_window()


def fini():
    if _timer is not None:
        _timer.stop()


def _reload_chat_wanted():
    return _timer.settings['enabled'] and _timer.settings['reloadChatLine']


def _sync_reload_chat():
    global _reload_chat_installed
    if _reload_chat_installed or not _reload_chat_wanted():
        return
    from gui.mods.gunner_hud import reload_chat
    reload_chat.install(_timer.slots, _reload_chat_wanted)
    _reload_chat_installed = True


def _register_settings_window():
    try:
        from gui.mods.gunner_hud import settings_window
        settings_window.register(_timer.settings, _on_window_change)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def _on_window_change(values):
    try:
        from gui.mods.gunner_hud import config, settings_window
        if not settings_window.store(_timer.settings, values):
            return
        config.save(_timer.settings)
        _timer.apply_settings()
        _sync_reload_chat()
    except Exception:
        LOG_CURRENT_EXCEPTION()
