LINKAGE = 'maksforge.gunner_hud'
FONT_SIZE_MIN = 10
FONT_SIZE_MAX = 24

FIELDS = (
    ('enabled', ('enabled',)),
    ('aimTimer', ('aimTimer', 'enabled')),
    ('autoreloaderLine', ('autoreloaderLine',)),
    ('magazineLine', ('magazineLine',)),
    ('aresLine', ('aresLine',)),
    ('reloadChatLine', ('reloadChatLine',)),
    ('hideWhenFull', ('hideWhenFull',)),
    ('fontSize', ('fontSize',)),
)


def _tooltip(header, body):
    return '{HEADER}%s{/HEADER}{BODY}%s{/BODY}' % (header, body)


def _normalized(name, value):
    if name == 'fontSize':
        return int(round(value))
    return bool(value)


def _parent(settings, path):
    for key in path[:-1]:
        settings = settings[key]
    return settings


def window_values(settings):
    values = dict((name, _parent(settings, path)[path[-1]]) for name, path in FIELDS)
    values['fontSize'] = min(FONT_SIZE_MAX, max(FONT_SIZE_MIN, values['fontSize']))
    return values


def store(settings, values):
    shown = window_values(settings)
    changed = False
    for name, path in FIELDS:
        if name not in values:
            continue
        value = _normalized(name, values[name])
        if value != shown[name]:
            _parent(settings, path)[path[-1]] = value
            changed = True
    return changed


def register(settings, on_change):
    try:
        from gui.modsSettingsApi import g_modsSettingsApi, templates
    except ImportError:
        return False

    def callback(linkage, new_values):
        if linkage == LINKAGE:
            on_change(new_values)

    values = window_values(settings)
    shown = g_modsSettingsApi.setModTemplate(LINKAGE, _template(templates, values), callback) or {}
    # The API keeps its own saved values while the template is unchanged, and config.json has the last word.
    if any(shown.get(name) != value for name, value in values.items()):
        g_modsSettingsApi.updateModSettings(LINKAGE, values)
    return True


def _template(templates, values):
    return {
        'modDisplayName': 'Gunner HUD',
        'enabled': values['enabled'],
        'column1': [
            templates.createLabel('Next to the crosshair'),
            templates.createCheckbox(
                'Autoreloader shell times', 'autoreloaderLine', values['autoreloaderLine'],
                tooltip=_tooltip('Autoreloader shell times',
                                 'The load time of every shell, the shells left and their potential damage '
                                 'on autoreloader tanks.')),
            templates.createCheckbox(
                'Autoloader magazine', 'magazineLine', values['magazineLine'],
                tooltip=_tooltip('Autoloader magazine',
                                 'The shells left and their potential damage on tanks whose whole magazine '
                                 'reloads at once.')),
            templates.createCheckbox(
                'Ares heat', 'aresLine', values['aresLine'],
                tooltip=_tooltip('Ares heat',
                                 'How long an Ares gun needs to cool down and the damage left before it locks.')),
            templates.createCheckbox(
                'Hide when full', 'hideWhenFull', values['hideWhenFull'],
                tooltip=_tooltip('Hide when full',
                                 'Hides the line while the magazine is full or an Ares gun is cold.')),
            templates.createSlider(
                'Text size', 'fontSize', values['fontSize'], FONT_SIZE_MIN, FONT_SIZE_MAX, 1,
                tooltip=_tooltip('Text size', 'Size of the line and of the aim timer\'s numbers.')),
        ],
        'column2': [
            templates.createCheckbox(
                'Aim timer', 'aimTimer', values['aimTimer'],
                tooltip=_tooltip('Aim timer',
                                 'A bar to the right of the crosshair with the seconds until the gun is fully '
                                 'aimed. On the Type 71 line it also counts down the dual accuracy cooldown.')),
            templates.createCheckbox(
                'Magazine status in the reload command', 'reloadChatLine', values['reloadChatLine'],
                tooltip=_tooltip('Magazine status in the reload command',
                                 'In an autoreloader, the reload quick command sends one team chat line with '
                                 'the whole magazine instead of the game\'s own command.')),
        ],
    }
