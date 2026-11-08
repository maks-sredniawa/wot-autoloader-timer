from gui.mods.gambiter import g_guiFlash
from gui.mods.gambiter.flash import COMPONENT_ALIGN, COMPONENT_EVENT, COMPONENT_TYPE

from . import gun_cooling, schedule

ALIAS = 'maksforgeAutoloaderTimer'
SEPARATOR = '   '

_SHADOW = {'color': 0x000000, 'alpha': 0.8, 'blurX': 2, 'blurY': 2, 'strength': 2, 'quality': 2}


def format_segments(slots, settings):
    colors = settings['colors']
    loaded = sum(1 for slot in slots if slot.state == schedule.LOADED)
    count = '%d/%d' % (loaded, len(slots))
    if loaded == len(slots):
        times = [('%.1f' % time, colors['shellTime']) for time in sorted(slot.own_time for slot in slots)]
        return times + [(count, colors['loaded'])]
    segments = []
    for slot in slots:
        if slot.state == schedule.LOADING:
            segments.append(('%.1f' % max(0.0, slot.ready_in), colors['loading']))
        elif slot.state == schedule.QUEUED:
            segments.append(('%.1f' % max(0.0, slot.ready_in), colors['queued']))
    return segments + [(count, colors['count'])]


def format_cooling(status, settings):
    colors = settings['colors']
    if status.state == gun_cooling.LOCKED:
        return [('LOCKED %.1f' % status.seconds, colors['loading'])]
    is_cold = status.state == gun_cooling.COLD
    segments = [] if is_cold else [('%.1f' % status.seconds, colors['shellTime'])]
    if status.potential_damage is not None:
        segments.append(('%d' % status.potential_damage, colors['loaded'] if is_cold else colors['count']))
    return segments


class PanelView(object):

    def __init__(self, settings, on_moved):
        self._settings = settings
        self._on_moved = on_moved
        self._shown = None
        self._anchor = (0, 0)
        props = {
            'text': '',
            'isHtml': True,
            'visible': False,
            'alignX': COMPONENT_ALIGN.CENTER,
            'alignY': COMPONENT_ALIGN.CENTER,
            'glowfilter': _SHADOW,
            'drag': True,
        }
        props.update(self._position())
        g_guiFlash.createComponent(ALIAS, COMPONENT_TYPE.LABEL, props)
        COMPONENT_EVENT.UPDATED += self._on_component_updated

    def destroy(self):
        COMPONENT_EVENT.UPDATED -= self._on_component_updated
        g_guiFlash.deleteComponent(ALIAS)

    def show(self, segments):
        text = self._html(segments) if segments else None
        if text == self._shown:
            return
        self._shown = text
        if text is None:
            g_guiFlash.updateComponent(ALIAS, {'visible': False})
        else:
            g_guiFlash.updateComponent(ALIAS, {'text': text, 'visible': True})

    def hide(self):
        self.show(None)

    def set_anchor(self, x, y):
        if (x, y) == self._anchor:
            return
        self._anchor = (x, y)
        g_guiFlash.updateComponent(ALIAS, self._position())

    def _position(self):
        return {'x': self._anchor[0] + self._settings['x'], 'y': self._anchor[1] + self._settings['y']}

    def _html(self, segments):
        parts = ["<font color='#%s'>%s</font>" % (color, text) for text, color in segments]
        separator = "<font color='#%s'>%s</font>" % (self._settings['colors']['count'], SEPARATOR)
        return "<font face='$FieldFont' size='%d'>%s</font>" % (self._settings['fontSize'], separator.join(parts))

    def _on_component_updated(self, alias, props):
        if alias != ALIAS or 'x' not in props or 'y' not in props:
            return
        self._settings['x'] = int(props['x']) - self._anchor[0]
        self._settings['y'] = int(props['y']) - self._anchor[1]
        self._on_moved()
