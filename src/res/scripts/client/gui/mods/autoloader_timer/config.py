import codecs
import copy
import json
import os

from debug_utils import LOG_CURRENT_EXCEPTION

CONFIG_DIR = os.path.join('mods', 'configs', 'autoloader_timer')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')
VIEW_POSITION_KEYS = ('sniper', 'strategic')

DEFAULTS = {
    'enabled': True,
    'x': 0,
    'y': 60,
    'fontSize': 14,
    'hideWhenFull': False,
    'reloadChatLine': True,
    'aimTimer': {
        'enabled': True,
        'x': 150,
        'y': 0,
        'sniper': {'x': 120, 'y': 60},
        'strategic': {'x': 180, 'y': 70},
    },
    'colors': {
        'count': 'D8D8D8',
        'loaded': 'C7FE48',
        'loading': 'FCAF1A',
        'queued': 'D8D8D8',
        'shellTime': 'A8A8A8',
    },
}


def _merged(defaults, loaded):
    result = copy.deepcopy(defaults)
    for key, value in loaded.items():
        if key in defaults and isinstance(defaults[key], dict) and isinstance(value, dict):
            result[key] = _merged(defaults[key], value)
        elif key in defaults:
            result[key] = value
        elif key in VIEW_POSITION_KEYS and isinstance(value, dict) and 'x' in value and 'y' in value:
            result[key] = {'x': value['x'], 'y': value['y']}
    return result


def load():
    try:
        if os.path.isfile(CONFIG_PATH):
            with codecs.open(CONFIG_PATH, 'r', 'utf-8-sig') as f:
                return _merged(DEFAULTS, json.load(f))
        save(DEFAULTS)
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return _merged(DEFAULTS, {})


def save(settings):
    try:
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with codecs.open(CONFIG_PATH, 'w', 'utf-8') as f:
            json.dump(settings, f, indent=4, sort_keys=True)
    except Exception:
        LOG_CURRENT_EXCEPTION()
